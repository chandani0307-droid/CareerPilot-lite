import streamlit as st

from services import actions as svc
from services.actions import ActionError
from ui.components import session

STAGES = {"saved": "📌 Saved", "drafted": "📝 Drafted", "applied": "📨 Applied", "interview": "🎤 Interview", "offer": "🎉 Offer", "rejected": "✖️ Rejected"}


def move(app_id: int) -> None:
    with session() as db:
        svc.update_application(db, app_id, status=st.session_state[f"stage_{app_id}"])


st.title("Applications")
st.caption("Track every role from saved to offer.")

with session() as db:
    with st.expander("➕ Add application"):
        with st.form("add", clear_on_submit=True):
            title, company, url = st.text_input("Job title"), st.text_input("Company"), st.text_input("Job link")
            if st.form_submit_button("Add", type="primary"):
                try:
                    svc.create_application(db, title, company, url)
                    st.rerun()
                except ActionError as exc:
                    st.error(str(exc))
    apps = svc.list_applications(db)
    if not apps:
        st.info("No applications yet. Save a job from the Jobs page, or run the agent.")
        st.stop()
    for col, (stage, label) in zip(st.columns(len(STAGES)), STAGES.items()):
        items = [a for a in apps if a.status == stage]
        with col:
            st.markdown(f"**{label}** · {len(items)}")
            for a in items:
                with st.container(border=True):
                    st.markdown(f"**{a.title}**")
                    st.caption(a.company + (f" · {a.match_score}%" if a.match_score else ""))
                    st.selectbox("Stage", list(STAGES), index=list(STAGES).index(a.status), key=f"stage_{a.id}", format_func=STAGES.get,
                                 label_visibility="collapsed", on_change=move, args=(a.id,))
                    if a.cover_letter:
                        with st.expander("Cover letter"):
                            st.write(a.cover_letter)
                    if a.url:
                        st.link_button("Open job page", a.url, use_container_width=True)
                    if st.button("Delete", key=f"delete_{a.id}", use_container_width=True):
                        svc.delete_application(db, a.id)
                        st.rerun()
