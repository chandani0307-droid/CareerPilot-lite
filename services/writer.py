"""AI writing. Each function asks the AI first and falls back to the offline templates."""
from services import fallbacks
from services.llm import llm
from services.resume_parser import analyze_heuristic

SYS = "You are CareerPilot, an honest career coach. Never invent skills, employers or numbers. Be concise."


def _profile(p: dict) -> str:
    return (f"Name: {p.get('name')}\nExperience: {p.get('experience_years')} years\n"
            f"Skills: {', '.join(p.get('skills') or [])}\nTarget roles: {', '.join(p.get('target_roles') or [])}")


def _job(j: dict) -> str:
    return f"Title: {j.get('title')}\nCompany: {j.get('company')}\nTags: {', '.join(j.get('tags') or [])}\nDescription: {(j.get('description') or '')[:1500]}"


def analyze_resume(text: str, filename: str = "") -> dict:
    profile = analyze_heuristic(text, filename)
    data = llm.json(SYS, "Analyse this resume. JSON keys: summary (2 sentences, first person, facts only), strengths (3 strings), "
                         "gaps (3 strings), suggestions (4 resume improvements).\n\n" + text[:6000])
    if data:
        for key in ("summary", "strengths", "gaps", "suggestions"):
            if data.get(key):
                profile[key] = data[key]
        profile["ai_enhanced"] = True
    profile["summary"] = profile.get("summary") or fallbacks.profile_summary(profile)
    profile["strengths"] = profile.get("strengths") or [f"Hands-on with {s}" for s in profile["skills"][:3]]
    profile["gaps"] = profile.get("gaps") or ["Run a job search to see which skills you are missing"]
    return profile


def cover_letter(profile: dict, job: dict) -> str:
    text = llm.complete(SYS, "Write a 150-word cover letter. Plain text, no placeholders, signed with the candidate's name.\n\n" + _profile(profile) + "\n\n" + _job(job))
    return text or fallbacks.cover_letter(profile, job)


def draft_email(profile: dict, job: dict) -> dict:
    data = llm.json(SYS, 'Write a 90-word cold email to a recruiter. JSON: {"subject": "...", "body": "..."}. Plain text, signed with the candidate\'s name.\n\n'
                    + _profile(profile) + "\n\n" + _job(job))
    if data and data.get("subject") and data.get("body"):
        return {"subject": str(data["subject"]), "body": str(data["body"])}
    return fallbacks.email(profile, job)


def draft_linkedin(profile: dict, job: dict) -> str:
    text = llm.complete(SYS, "Write a LinkedIn connection note, max 280 characters, friendly, no hashtags. Output only the note.\n\n" + _profile(profile) + "\n\n" + _job(job))
    return (text or fallbacks.linkedin(profile, job)).strip()[:300]


def assistant_reply(profile: dict | None, history: list[dict], stats: dict) -> str:
    convo = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in history[-8:])
    text = llm.complete(SYS + " Answer in under 120 words and suggest a next step inside the app.",
                        f"CANDIDATE:\n{_profile(profile) if profile else 'No resume yet'}\n\nAPP STATS: {stats}\n\n{convo}")
    return text or fallbacks.chat(profile, history[-1]["content"], stats)
