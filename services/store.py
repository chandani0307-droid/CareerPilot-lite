"""Small data-access helpers shared by routers and the agent graph."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models.tables import Action, Application, Job, Profile
from .matching import score_job

JOB_COLS = {c.name for c in Job.__table__.columns}


def get_profile_row(db: Session) -> Profile | None:
    return db.get(Profile, 1)


def profile_data(db: Session) -> dict | None:
    row = get_profile_row(db)
    return dict(row.data) if row and row.data else None


def upsert_jobs(db: Session, jobs: list[dict], profile: dict | None) -> list[Job]:
    out: list[Job] = []
    for j in jobs:
        score, reasons, missing = score_job(profile, j) if profile else (0, [], [])
        row = db.get(Job, j["id"])
        if row is None:
            limits = {"title": 300, "company": 200, "location": 200, "url": 1000, "apply_url": 1000, "linkedin_url": 1000, "salary": 100, "posted_at": 40, "source": 50}
            clean = {k: (v[: limits[k]] if k in limits and isinstance(v, str) else v) for k, v in j.items() if k in JOB_COLS}
            row = Job(**clean)
            db.add(row)
        row.match_score, row.match_reasons, row.missing_skills = score, reasons, missing
        out.append(row)
    db.commit()
    return out


def ensure_application(db: Session, job: Job, status: str = "saved", **fields) -> Application:
    app = db.scalar(select(Application).where(Application.job_id == job.id))
    if app is None:
        app = Application(job_id=job.id, title=job.title, company=job.company, url=job.apply_url or job.url, status=status, match_score=job.match_score)
        db.add(app)
    order = ["saved", "drafted", "applied", "interview", "offer"]
    if status in order and app.status in order and order.index(status) > order.index(app.status):
        app.status = status
    for k, v in fields.items():
        if v is not None:
            setattr(app, k, v)
    app.match_score = job.match_score
    db.commit()
    return app


def ensure_action(db: Session, type_: str, job: Job, run_id: int | None = None, status: str = "draft", **fields) -> Action:
    act = db.scalar(select(Action).where(Action.job_id == job.id, Action.type == type_, Action.status.in_(["draft", "pending"])))
    if act is None:
        act = Action(type=type_, job_id=job.id, title=f"{job.title} @ {job.company}", company=job.company, target_url=job.apply_url or job.url)
        db.add(act)
    for k, v in fields.items():
        if v is not None:
            setattr(act, k, v)
    act.status = status
    if run_id is not None:
        act.run_id = run_id
    db.commit()
    return act


def quick_stats(db: Session) -> dict:
    return {
        "jobs": db.scalar(select(func.count()).select_from(Job)) or 0,
        "high": db.scalar(select(func.count()).select_from(Job).where(Job.match_score >= 75)) or 0,
        "pending": db.scalar(select(func.count()).select_from(Action).where(Action.status == "pending")) or 0,
        "applications": db.scalar(select(func.count()).select_from(Application)) or 0,
    }


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
