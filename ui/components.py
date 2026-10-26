"""Reusable Streamlit widgets: score badge, chips, job card and approval card."""
from __future__ import annotations

import html

import streamlit as st

from core.db import session  # noqa: F401  (pages import it from here)
from services import actions as svc
from services.actions import ActionError

CSS = """
<style>
.block-container {padding-top: 2rem; max-width: 1200px;}
.chip {display:inline-block; padding:2px 10px; margin:2px 4px 2px 0; border-radius:999px; font-size:12px; border:1px solid #E1E4EA; background:#fff;}
.chip.blue {background:#EEF3FF; color:#1F57E0;}
.chip.green {background:#E6F5EE; color:#178F63;}
.chip.amber {background:#FDF4E3; color:#9A6411;}
.chip.red {background:#FCEBEE; color:#D3455B;}
.score {display:inline-flex; align-items:center; justify-content:center; width:54px; height:54px; border-radius:50%; font-weight:700; font-size:17px; color:#fff;}
</style>
"""
REGION = {"all": "All regions", "india": "India", "abroad": "Abroad", "remote": "Remote"}
LABEL = {"email": "✉️ HR email", "linkedin": "🔗 LinkedIn note", "apply": "📨 Application"}
STATUS = {"draft": "Draft", "pending": "Needs your approval", "executed": "Approved", "rejected": "Rejected"}
TONE = {"pending": "amber", "executed": "green", "rejected": "red"}


def chips(items: list[str], tone: str = "") -> str:
    return "".join(f'<span class="chip {tone}">{html.escape(str(i))}</span>' for i in items)


def score_html(score: int) -> str:
    color = "#178F63" if score >= 75 else "#2D6BFF" if score >= 55 else "#E9A23B" if score >= 35 else "#A9B5C8"
    return f'<div class="score" style="background:{color}">{score}</div>'


def require_profile(db) -> dict:
    """Stop the page with a friendly message when no resume has been uploaded yet."""
    data = svc.get_profile(db)
    if not data:
        st.info("Upload your resume first. CareerPilot needs your skills to match jobs.")
        st.page_link("pages/2_Resume.py", label="Go to Resume", icon="📄")
        st.stop()
    return data


def job_card(db, job, key: str = "j") -> None:
    with st.container(border=True):
        c1, c2 = st.columns([1, 9], vertical_alignment="center")
        c1.markdown(score_html(job.match_score), unsafe_allow_html=True)
        c2.markdown(f"**{job.title}**  \n{job.company} · {job.location}" + (f" · {job.salary}" if job.salary else ""))
        sample = '<span class="chip amber">Sample listing</span>' if job.source == "mock" else ""
        st.markdown(sample + chips([REGION.get(job.region, job.region)] + list(job.tags or [])[:4]), unsafe_allow_html=True)
        for reason in (job.match_reasons or [])[:2]:
            st.caption("• " + reason)
        if job.missing_skills:
            st.caption("Missing: " + ", ".join(job.missing_skills[:4]))
        apply_col, save_col, mail_col, link_col = st.columns(4)
        if job.apply_url or job.url:
            apply_col.link_button("View & apply", job.apply_url or job.url, use_container_width=True)
        if save_col.button("★ Saved" if job.saved else "☆ Save", key=f"{key}_save_{job.id}", use_container_width=True):
            svc.toggle_save(db, job.id)
            st.rerun()
        for col, kind, label in ((mail_col, "email", "✉️ HR email"), (link_col, "linkedin", "🔗 LinkedIn")):
            if col.button(label, key=f"{key}_{kind}_{job.id}", use_container_width=True):
                try:
                    with st.spinner("Drafting…"):
                        svc.draft_action(db, job.id, kind)
                    st.toast("Draft created. Review it on the Outreach page.", icon="✅")
                except ActionError as exc:
                    st.error(str(exc))


def action_card(db, act, key: str = "a") -> None:
    """An editable draft. Nothing external happens until the user approves AND confirms."""
    k = f"{key}_{act.id}"
    locked = act.status in ("executed", "rejected")
    with st.container(border=True):
        st.markdown(f"**{LABEL[act.type]}** · {act.title}  \n" + chips([STATUS[act.status]], TONE.get(act.status, "")), unsafe_allow_html=True)
        recipient, subject = act.recipient, act.subject
        if act.type == "email":
            recipient = st.text_input("To (HR email)", act.recipient, key=f"to_{k}", disabled=locked, placeholder="hr@company.com")
            subject = st.text_input("Subject", act.subject, key=f"subject_{k}", disabled=locked)
        body = st.text_area("Message", act.body, key=f"body_{k}", height=200, disabled=locked, max_chars=300 if act.type == "linkedin" else None)
        result = act.result or {}
        if result.get("message"):
            st.success(result["message"])
        if result.get("url"):
            st.link_button("Open link", result["url"])
        if locked:
            return

        def save() -> None:
            svc.edit_action(db, act.id, recipient=recipient, subject=subject, body=body)

        a, b, c = st.columns(3)
        try:
            if act.status == "draft" and a.button("🛡️ Request approval", key=f"req_{k}", type="primary", use_container_width=True):
                save()
                svc.set_status(db, act.id, "pending")
                st.rerun()
            if act.status == "pending" and a.button("✅ Approve & run", key=f"ok_{k}", type="primary", use_container_width=True):
                save()
                st.session_state[f"confirm_{k}"] = True
                st.rerun()
            if b.button("💾 Save edits", key=f"save_{k}", use_container_width=True):
                save()
                st.toast("Saved", icon="💾")
            if c.button("✖ Reject", key=f"reject_{k}", use_container_width=True):
                svc.set_status(db, act.id, "rejected")
                st.rerun()
        except ActionError as exc:
            st.error(str(exc))

        if st.session_state.get(f"confirm_{k}"):
            st.warning("Approve this action? An email is sent only if SMTP is set up. LinkedIn and Apply give you a link to finish yourself.")
            yes, no = st.columns(2)
            if yes.button("Yes, approve", key=f"yes_{k}", type="primary", use_container_width=True):
                try:
                    svc.approve_action(db, act.id, confirm=True, recipient=recipient)
                    st.session_state.pop(f"confirm_{k}", None)
                    st.rerun()
                except ActionError as exc:
                    st.error(str(exc))
            if no.button("Cancel", key=f"cancel_{k}", use_container_width=True):
                st.session_state.pop(f"confirm_{k}", None)
                st.rerun()
