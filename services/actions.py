"""Everything the pages can do, as plain functions (no web API needed).

The ONLY function that touches the outside world is approve_action(), and it needs confirm=True.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.tables import Action, AgentRun, Application, Job, Profile
from services import writer
from services.jobs.aggregator import search_jobs
from services.mailer import send_or_link
from services.resume_parser import extract_text
from services.store import ensure_action, ensure_application, get_profile_row, profile_data, upsert_jobs, utcnow


class ActionError(Exception):
    """A friendly error message. The pages show it with st.error()."""


def job_dict(job: Job) -> dict:
    return {c.name: getattr(job, c.name) for c in Job.__table__.columns}


# ---------- resume and profile ----------
def save_resume(db: Session, filename: str, raw: bytes) -> dict:
    try:
        text = extract_text(filename, raw)
    except Exception as exc:  # noqa: BLE001
        raise ActionError(f"Could not read this file: {exc}")
    if len(text) < 80:
        raise ActionError("No readable text found. Upload a text-based PDF, DOCX or TXT file.")
    data = writer.analyze_resume(text, filename)
    row = get_profile_row(db) or Profile(id=1)
    row.filename, row.resume_text, row.data = filename, text, data
    db.add(row)
    db.commit()
    upsert_jobs(db, [job_dict(j) for j in db.query(Job).all()], data)  # re-score the jobs we already have
    return data


def get_profile(db: Session) -> dict | None:
    return profile_data(db)


def delete_resume(db: Session) -> None:
    row = get_profile_row(db)
    if row:
        db.delete(row)
    for job in db.query(Job).all():
        job.match_score, job.match_reasons, job.missing_skills = 0, [], []
    db.commit()


def delete_all_data(db: Session) -> None:
    for model in (Action, Application, AgentRun, Job, Profile):
        db.query(model).delete()
    db.commit()


# ---------- jobs ----------
def search_and_store(db: Session, query: str = "", region: str = "all", location: str = "", limit: int = 30):
    profile = profile_data(db)
    queries = [query] if query else []
    if not queries and profile:
        queries = [r.replace(" / ", " ") for r in (profile.get("target_roles") or [])[:2]]
    jobs, report = search_jobs(queries or ["software developer"], region, location, limit)
    rows = upsert_jobs(db, jobs, profile)
    rows.sort(key=lambda r: r.match_score, reverse=True)
    return rows[:limit], report


def list_jobs(db: Session, region: str = "all", min_score: int = 0) -> list[Job]:
    stmt = select(Job).where(Job.match_score >= min_score).order_by(Job.match_score.desc()).limit(200)
    if region != "all":
        stmt = stmt.where(Job.region == region)
    return list(db.scalars(stmt))


def toggle_save(db: Session, job_id: str) -> Job:
    job = db.get(Job, job_id)
    if not job:
        raise ActionError("Job not found.")
    job.saved = not job.saved
    db.commit()
    if job.saved:
        ensure_application(db, job, "saved")
    return job


# ---------- applications tracker ----------
def list_applications(db: Session) -> list[Application]:
    return list(db.scalars(select(Application).order_by(Application.updated_at.desc())))


def create_application(db: Session, title: str, company: str = "", url: str = "") -> Application:
    if not title.strip():
        raise ActionError("Job title is required.")
    app = Application(title=title.strip(), company=company.strip(), url=url.strip())
    db.add(app)
    db.commit()
    return app


def update_application(db: Session, app_id: int, **fields) -> Application:
    app = db.get(Application, app_id)
    if not app:
        raise ActionError("Application not found.")
    for key, value in fields.items():
        setattr(app, key, value)
    if fields.get("status") == "applied" and not app.applied_at:
        app.applied_at = utcnow()
    db.commit()
    return app


def delete_application(db: Session, app_id: int) -> None:
    app = db.get(Application, app_id)
    if app:
        db.delete(app)
        db.commit()


# ---------- drafts and the human-approval gate ----------
def list_actions(db: Session, status: str = "", type: str = "") -> list[Action]:
    stmt = select(Action).order_by(Action.updated_at.desc()).limit(200)
    if status:
        stmt = stmt.where(Action.status == status)
    if type:
        stmt = stmt.where(Action.type == type)
    return list(db.scalars(stmt))


def draft_action(db: Session, job_id: str, kind: str) -> Action:
    job, profile = db.get(Job, job_id), profile_data(db)
    if not job:
        raise ActionError("Job not found.")
    if not profile:
        raise ActionError("Upload a resume first.")
    info = job_dict(job)
    if kind == "email":
        mail = writer.draft_email(profile, info)
        return ensure_action(db, "email", job, status="draft", recipient=job.hr_email, subject=mail["subject"], body=mail["body"])
    if kind == "linkedin":
        return ensure_action(db, "linkedin", job, status="draft", target_url=job.linkedin_url, body=writer.draft_linkedin(profile, info))
    letter = writer.cover_letter(profile, info)
    ensure_application(db, job, "drafted", cover_letter=letter)
    return ensure_action(db, "apply", job, status="draft", subject=f"Apply: {job.title}", body=letter)


def _open_action(db: Session, action_id: int) -> Action:
    act = db.get(Action, action_id)
    if not act:
        raise ActionError("Action not found.")
    if act.status in ("executed", "rejected"):
        raise ActionError(f"This action is already {act.status}.")
    return act


def edit_action(db: Session, action_id: int, **fields) -> Action:
    act = _open_action(db, action_id)
    for key, value in fields.items():
        if value is not None:
            setattr(act, key, value)
    db.commit()
    return act


def set_status(db: Session, action_id: int, status: str) -> Action:
    """Used for 'request approval' (pending) and 'reject' (rejected)."""
    act = _open_action(db, action_id)
    act.status = status
    db.commit()
    return act


def approve_action(db: Session, action_id: int, confirm: bool = False, recipient: str | None = None) -> Action:
    """The ONLY code path that touches the outside world. Needs an explicit confirm=True from the page."""
    act = _open_action(db, action_id)
    if not confirm:
        raise ActionError("Explicit confirmation required.")
    if recipient is not None:
        act.recipient = recipient.strip()
    if act.type == "email":
        if not act.recipient:
            raise ActionError("Add the HR recipient email before approving.")
        try:
            act.result = send_or_link(act.recipient, act.subject, act.body)
        except Exception as exc:  # noqa: BLE001
            raise ActionError(f"Could not send email: {exc}")
    elif act.type == "linkedin":
        act.result = {"url": act.target_url, "message": "LinkedIn blocks automation, so open the link and paste your note. Your approval is recorded."}
    else:
        act.result = {"url": act.target_url, "message": "Open the apply page and submit with your cover letter."}
        app = db.scalar(select(Application).where(Application.job_id == act.job_id))
        if app:
            app.status, app.applied_at = "applied", utcnow()
    act.status = "executed"
    db.commit()
    return act
