"""Transparent job↔profile scoring. Deterministic, explainable, no AI required."""
from __future__ import annotations

import re

from .skills import extract_skills

_STOP = {"senior", "sr", "junior", "jr", "lead", "staff", "principal", "the", "a", "of", "and", "remote", "i", "ii", "iii", "-", "/", "&", "–"}


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9+#.]+", (text or "").lower()) if t not in _STOP and len(t) > 1}


def score_job(profile: dict, job: dict) -> tuple[int, list[str], list[str]]:
    """Return (score 0-100, reasons, missing_skills)."""
    mine = set(profile.get("skills") or [])
    blob = " ".join([job.get("title", ""), " ".join(job.get("tags") or []), (job.get("description") or "")[:3000]])
    wanted = extract_skills(blob)
    overlap = [s for s in wanted if s in mine]
    missing = [s for s in wanted if s not in mine][:6]

    if wanted:
        coverage = len(overlap) / len(wanted)
        skill_c = 0.6 * coverage + 0.4 * min(1.0, len(overlap) / 5)
    else:
        skill_c = 0.3

    role_tokens = _tokens(" ".join(profile.get("target_roles") or []) + " " + (profile.get("headline") or "")) | {t.lower() for s in mine for t in re.findall(r"[A-Za-z0-9+#.]+", s)}
    title_tokens = _tokens(job.get("title", ""))
    shared = title_tokens & role_tokens
    title_c = min(1.0, len(shared) / max(1, len(title_tokens)) * 1.6) if title_tokens else 0.0

    pref = 0.0
    regions = profile.get("preferred_regions") or []
    if job.get("region") in regions:
        pref += 0.6
    locs = [l.lower() for l in (profile.get("preferred_locations") or [])]
    if any(l and l in (job.get("location") or "").lower() for l in locs):
        pref += 0.4

    years = float(profile.get("experience_years") or 0)
    title_low = (job.get("title") or "").lower()
    penalty = 0.0
    if years < 2 and re.search(r"senior|lead|principal|staff|head|manager|architect", title_low):
        penalty = 0.12
    elif years >= 6 and re.search(r"intern|junior|trainee|fresher|graduate", title_low):
        penalty = 0.12

    score = round(100 * (0.6 * skill_c + 0.3 * title_c + 0.1 * min(pref, 1.0) - penalty))
    score = max(5, min(98, score))

    reasons: list[str] = []
    if overlap:
        reasons.append(f"Matches {len(overlap)} of your skills: {', '.join(overlap[:5])}")
    if shared:
        reasons.append(f"Title aligns with your profile ({', '.join(sorted(shared)[:3])})")
    if job.get("region") in regions:
        reasons.append(f"In your preferred region ({job['region']})")
    if penalty:
        reasons.append("Seniority may not line up with your experience")
    if not reasons:
        reasons.append("Limited overlap with your listed skills")
    return score, reasons, missing
