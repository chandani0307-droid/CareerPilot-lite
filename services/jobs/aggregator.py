"""Fan out to every enabled provider in parallel, classify region, dedupe, and fall back to sample jobs."""
from __future__ import annotations

import hashlib
import re
from concurrent.futures import ThreadPoolExecutor

from core.config import settings
from .mock_jobs import mock_jobs
from .providers import PROVIDERS, linkedin_people_search

INDIA_WORDS = ["india", "bengaluru", "bangalore", "hyderabad", "pune", "mumbai", "delhi", "gurgaon", "gurugram", "noida", "chennai", "kolkata", "ahmedabad", "guwahati", "jaipur", "kochi", "coimbatore", "indore", "chandigarh"]
REMOTE_WORDS = ["remote", "anywhere", "worldwide", "work from home", "wfh"]


def classify_region(location: str) -> str:
    loc = (location or "").lower()
    if any(w in loc for w in INDIA_WORDS):
        return "india"
    if any(w in loc for w in REMOTE_WORDS):
        return "remote"
    return "abroad"


def job_id(job: dict) -> str:
    key = (job.get("url") or "") or f"{job.get('title')}|{job.get('company')}|{job.get('location')}"
    return hashlib.sha1(key.encode()).hexdigest()[:16]


def _relevant(job: dict, tokens: set[str]) -> bool:
    if not tokens:
        return True
    hay = " ".join([job["title"], " ".join(job.get("tags") or []), job.get("description", "")[:600]]).lower()
    return any(t in hay for t in tokens)


def search_jobs(queries: list[str], region: str = "all", location: str = "", limit: int = 40) -> tuple[list[dict], dict]:
    """Return (jobs, report). report lists per-provider counts so the UI can show what was live vs sample."""
    queries = [q for q in (queries or []) if q.strip()][:3] or [""]
    names = [n for n in settings.job_providers if n in PROVIDERS]
    tasks = [(n, q) for n in names for q in (queries if n in {"remotive", "adzuna"} else queries[:1])]
    report: dict[str, int] = {n: 0 for n in names}
    raw: list[dict] = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for (name, _), result in zip(tasks, pool.map(lambda t: PROVIDERS[t[0]](t[1], 20), tasks)):
            report[name] += len(result)
            raw.extend(result)

    tokens = {t for q in queries for t in re.findall(r"[a-z0-9+#.]+", q.lower()) if len(t) > 2 and t not in {"and", "the", "developer", "engineer"}} or \
             {t for q in queries for t in re.findall(r"[a-z0-9+#.]+", q.lower()) if len(t) > 2}

    def keep(j: dict) -> bool:
        if region != "all" and j["region"] != region:
            return False
        if location and location.lower() not in j["location"].lower():
            return False
        return True

    jobs: dict[str, dict] = {}
    for j in raw:
        if not j.get("title") or not j.get("url") or not _relevant(j, tokens):
            continue
        j["region"] = classify_region(j["location"])
        if keep(j):
            jobs.setdefault(job_id(j), j)

    live = len(jobs)
    if settings.mock_fallback and live < 8:
        for j in mock_jobs():
            if keep(j) and (live == 0 or _relevant(j, tokens) or not tokens):
                jobs.setdefault(job_id(j), j)
        report["mock"] = len(jobs) - live
    out = []
    for jid, j in list(jobs.items())[: max(limit, 1) * 2]:
        j["id"] = jid
        j["linkedin_url"] = linkedin_people_search(j["company"])
        out.append(j)
    report["live_total"] = live
    return out, report
