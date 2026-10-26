import streamlit as st

from core.db import PER_VISITOR
from services import actions as svc
from services.actions import ActionError
from ui.components import chips, session


def wipe() -> None:
    """Button callback: delete the data, then forget what this browser session remembered."""
    with session() as db:
        svc.delete_all_data(db)
    for key in ("job_ids", "prep", "run_id", "chat"):
        st.session_state.pop(key, None)
    st.session_state["upload_n"] = st.session_state.get("upload_n", 0) + 1  # a new key empties the uploader
    st.session_state["del_sure"] = False
    st.session_state["deleted"] = True


st.title("Resume")
st.caption("Upload once. CareerPilot extracts your profile and uses it for matching and drafts.")
if st.session_state.pop("deleted", False):
    st.success("All your data was deleted.", icon="🗑️")

with session() as db:
    data = svc.get_profile(db)
    file = st.file_uploader("Resume (PDF, DOCX or TXT)", type=["pdf", "docx", "txt"], key=f"upload_{st.session_state.get('upload_n', 0)}")
    if st.button("Analyse resume", type="primary", disabled=file is None):
        try:
            with st.spinner("Analysing your resume…"):
                svc.save_resume(db, file.name, file.getvalue())
            st.rerun()
        except ActionError as exc:
            st.error(str(exc))

    if data:
        left, right = st.columns([2, 1], gap="large")
        with left:
            st.subheader(data.get("name") or "Candidate")
            st.caption(" · ".join(x for x in [data.get("email"), data.get("phone"), data.get("current_location")] if x))
            st.write(data.get("summary", ""))
            st.markdown("**Skills detected**")
            st.markdown(chips(data.get("skills", []), "blue"), unsafe_allow_html=True)
            m1, m2 = st.columns(2)
            m1.metric("Experience", f"{data.get('experience_years', 0):g} years")
            m2.metric("Level", data.get("seniority", ""))
            st.caption("Target roles: " + ", ".join(data.get("target_roles", [])))
            g1, g2 = st.columns(2)
            g1.markdown("**Strengths**\n\n" + "\n".join("- " + s for s in data.get("strengths", [])))
            g2.markdown("**Gaps to close**\n\n" + "\n".join("- " + s for s in data.get("gaps", [])))
        with right:
            st.metric("ATS readiness", f"{data.get('ats_score', 0)}/100")
            st.markdown("**How to improve**")
            for tip in data.get("suggestions", []):
                st.write("• " + tip)

    with st.expander("🗑️ Delete my data"):
        st.write("Your data is private to this browser session and is deleted automatically after a few hours. You can also delete it now."
                 if PER_VISITOR else "Shared mode: every visitor of this app can see this data. Delete it when you are finished.")
        st.checkbox("I understand this cannot be undone", key="del_sure")
        st.button("Delete everything", type="primary", disabled=not st.session_state.get("del_sure"), on_click=wipe)
