"""Numbers for the Dashboard and Analytics pages."""
from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.tables import Action, Application, Job
from services.skills import extract_skills
from services.store import profile_data

STAGES = ["saved", "drafted", "applied", "interview", "offer"]


def summary(db: Session) -> dict:
    mine = set((profile_data(db) or {}).get("skills") or [])
    jobs = list(db.scalars(select(Job)))
    apps = Counter(a.status for a in db.scalars(select(Application)))
    demand, gaps = Counter(), Counter()
    for job in jobs:
        demand.update(set(extract_skills(f"{job.title} {' '.join(job.tags or [])} {job.description[:1500]}")))
        gaps.update(job.missing_skills or [])
    scores = [j.match_score for j in jobs]
    return {
        "jobs": len(jobs), "avg_match": round(sum(scores) / len(scores)) if scores else 0, "high_matches": sum(s >= 75 for s in scores),
        "applications": sum(apps.values()), "pending": sum(a.status == "pending" for a in db.scalars(select(Action))),
        "funnel": {stage: apps[stage] for stage in STAGES}, "by_region": dict(Counter(j.region for j in jobs)), "gaps": dict(gaps.most_common(8)),
        "demand": [{"skill": s, "count": c, "have": s in mine} for s, c in demand.most_common(10)],
    }
