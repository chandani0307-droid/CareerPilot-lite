"""The LangGraph workflow:

    planner > scout > matcher > write > outreach > coach > gate

The agents only search, score and DRAFT. Every draft is saved as 'pending'; a human approves it on the page.
"""
import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from models.tables import AgentRun, Job
from services import writer
from services.actions import job_dict
from services.interview import generate
from services.jobs.aggregator import search_jobs
from services.store import ensure_action, ensure_application, profile_data, quick_stats, upsert_jobs


class State(TypedDict, total=False):
    run_id: int
    params: dict
    profile: dict
    queries: list[str]
    job_ids: list[str]
    top_ids: list[str]
    interview: dict
    pending: int
    stop: bool
    trace: Annotated[list[dict], operator.add]  # each agent adds its own line


def step(agent: str, message: str, status: str = "done") -> list[dict]:
    return [{"agent": agent, "status": status, "message": message}]


def build_graph(db: Session):
    def planner(state: State) -> dict:
        profile = profile_data(db)
        if not profile:
            return {"stop": True, "trace": step("Planner", "No resume found. Upload your resume first.", "blocked")}
        roles = [r.replace(" / ", " ") for r in (profile.get("target_roles") or [])[:2]]
        queries = [state["params"]["query"]] if state["params"].get("query") else roles or ["software developer"]
        return {"profile": profile, "queries": queries, "trace": step("Planner", f"Planned searches: {', '.join(queries)}")}

    def scout(state: State) -> dict:
        p = state["params"]
        jobs, report = search_jobs(state["queries"], p["region"], p["location"], 40)
        rows = upsert_jobs(db, jobs, state["profile"])
        return {"job_ids": [r.id for r in rows], "trace": step("Job Scout", f"Found {len(rows)} jobs ({report.get('live_total', 0)} live)")}

    def matcher(state: State) -> dict:
        rows = sorted((db.get(Job, i) for i in state["job_ids"]), key=lambda r: r.match_score, reverse=True)
        top = rows[: state["params"]["top_k"]]
        return {"top_ids": [r.id for r in top], "trace": step("Matcher", f"Scored {len(rows)} jobs. Top {len(top)} selected (best {top[0].match_score}%)")}

    def write(state: State) -> dict:
        for job_id in state["top_ids"]:
            job = db.get(Job, job_id)
            letter = writer.cover_letter(state["profile"], job_dict(job))
            ensure_application(db, job, "drafted", cover_letter=letter)
            ensure_action(db, "apply", job, state["run_id"], "pending", subject=f"Apply: {job.title}", body=letter)
        return {"trace": step("Cover Letter Writer", f"Drafted cover letters for {len(state['top_ids'])} jobs")}

    def outreach(state: State) -> dict:
        for job_id in state["top_ids"]:
            job = db.get(Job, job_id)
            info = job_dict(job)
            mail = writer.draft_email(state["profile"], info)
            ensure_action(db, "email", job, state["run_id"], "pending", recipient=job.hr_email, subject=mail["subject"], body=mail["body"])
            ensure_action(db, "linkedin", job, state["run_id"], "pending", target_url=job.linkedin_url, body=writer.draft_linkedin(state["profile"], info))
        return {"trace": step("Outreach Agent", f"Drafted HR emails and LinkedIn notes for {len(state['top_ids'])} jobs")}

    def coach(state: State) -> dict:
        job = db.get(Job, state["top_ids"][0])
        prep = generate(state["profile"], job.title, job.company, job.tags or [], job.description)
        return {"interview": {"job_id": job.id, "role": job.title, **prep}, "trace": step("Interview Coach", f"Prepared {len(prep['questions'])} questions for {job.title}")}

    def gate(state: State) -> dict:
        pending = quick_stats(db)["pending"]
        return {"pending": pending, "trace": step("Approval Gate", f"{pending} actions are waiting for your approval. Nothing has been sent.", "waiting")}

    graph = StateGraph(State)
    for name, fn in [("planner", planner), ("scout", scout), ("matcher", matcher), ("write", write), ("outreach", outreach), ("coach", coach), ("gate", gate)]:
        graph.add_node(name, fn)
    graph.set_entry_point("planner")
    graph.add_conditional_edges("planner", lambda s: "stop" if s.get("stop") else "go", {"stop": END, "go": "scout"})
    graph.add_conditional_edges("scout", lambda s: "go" if s["job_ids"] else "stop", {"stop": END, "go": "matcher"})
    for a, b in [("matcher", "write"), ("write", "outreach"), ("outreach", "coach"), ("coach", "gate"), ("gate", END)]:
        graph.add_edge(a, b)
    return graph.compile()


def run_agent(db: Session, params: dict) -> AgentRun:
    run = AgentRun(goal=params.get("goal", ""), params=params, status="running", trace=[], summary={})
    db.add(run)
    db.commit()
    try:
        final = build_graph(db).invoke({"run_id": run.id, "params": params, "trace": []})
        run.trace = final.get("trace", [])
        run.status = "blocked" if any(t["status"] == "blocked" for t in run.trace) else "waiting_approval"
        top = [db.get(Job, i) for i in final.get("top_ids", [])]
        run.summary = {"top": [{"title": j.title, "company": j.company, "score": j.match_score} for j in top], "interview": final.get("interview")}
    except Exception as exc:  # noqa: BLE001
        run.status = "failed"
        run.trace = [{"agent": "Orchestrator", "status": "failed", "message": f"{type(exc).__name__}: {exc}"}]
    db.commit()
    return run
