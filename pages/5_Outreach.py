import streamlit as st

from services import actions as svc
from services.actions import ActionError
from ui.components import action_card, session

st.title("Outreach")
st.caption("HR emails, LinkedIn notes and cover letters. Every draft is editable and needs your approval.")

KINDS = [("email", "HR emails"), ("linkedin", "LinkedIn"), ("apply", "Cover letters")]

with session() as db:
    names = {j.id: f"{j.match_score}% · {j.title} @ {j.company}" for j in svc.list_jobs(db, min_score=1)}
    for tab, (kind, title) in zip(st.tabs([t for _, t in KINDS]), KINDS):
        with tab:
            c1, c2 = st.columns([4, 1], vertical_alignment="bottom")
            job_id = c1.selectbox("Draft for job", list(names), format_func=names.get, index=None, placeholder="Choose a job…", key=f"job_{kind}")
            if c2.button("✨ Generate", key=f"generate_{kind}", type="primary", disabled=not job_id, use_container_width=True):
                try:
                    with st.spinner("Writing your draft…"):
                        svc.draft_action(db, job_id, kind)
                    st.rerun()
                except ActionError as exc:
                    st.error(str(exc))
            drafts = [a for a in svc.list_actions(db, type=kind) if a.status != "rejected"]
            if not drafts:
                st.info("No drafts yet. Pick a job above, or run the agent.")
            for act in drafts:
                action_card(db, act, key=f"out_{kind}")
