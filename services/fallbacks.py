"""Offline templates, used when there is no AI key or the AI call fails."""


def _name(p: dict) -> str:
    return (p.get("name") or "").strip() or "Candidate"


def _top(p: dict, n: int = 4) -> list[str]:
    return (p.get("skills") or [])[:n]


def profile_summary(p: dict) -> str:
    role = (p.get("target_roles") or ["software professional"])[0]
    return f"{role} with {p.get('experience_years') or 0:g} years of experience in {', '.join(_top(p, 5)) or 'software development'}."


def cover_letter(p: dict, job: dict) -> str:
    return (f"Dear Hiring Team at {job.get('company')},\n\n"
            f"I am excited to apply for the {job.get('title')} role. With {p.get('experience_years') or 'hands-on'} years of experience in "
            f"{', '.join(_top(p))}, I can contribute quickly to your team.\n\n"
            f"I would welcome the chance to discuss how I can help {job.get('company')}.\n\nSincerely,\n{_name(p)}")


def email(p: dict, job: dict) -> dict:
    return {"subject": f"{job.get('title')}: application from {_name(p)}",
            "body": f"Hi,\n\nI applied for the {job.get('title')} role at {job.get('company')} and wanted to reach out directly. "
                    f"I have experience with {', '.join(_top(p, 3))}. Could we have a short chat?\n\nBest regards,\n{_name(p)}"}


def linkedin(p: dict, job: dict) -> str:
    role = (p.get("target_roles") or ["engineer"])[0]
    return f"Hi! I'm a {role} ({', '.join(_top(p, 3))}) and applied for {job.get('title')} at {job.get('company')}. Would love to connect."[:300]


def chat(p: dict | None, text: str, stats: dict) -> str:
    t = text.lower()
    if not p:
        return "Upload your resume first (Resume page). Then I can summarise it, find jobs and draft applications."
    if "summar" in t or "resume" in t:
        return f"{profile_summary(p)} ATS score: {p.get('ats_score', 0)}/100."
    if "job" in t or "find" in t:
        return f"Open Agent and press Run agent. You have {stats.get('jobs', 0)} jobs saved and {stats.get('pending', 0)} drafts waiting for approval."
    if "interview" in t:
        return "Open Interview, choose a job, and I will prepare questions with answer tips."
    return "I can summarise your resume, find jobs, write drafts and prepare interviews. What would you like?"
