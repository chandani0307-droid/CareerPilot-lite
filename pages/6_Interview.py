import streamlit as st

from models.tables import Job
from services import actions as svc
from services.interview import generate
from ui.components import session

st.title("Interview prep")
st.caption("Questions, answer tips and stories for the job you choose.")

with session() as db:
    profile = svc.get_profile(db) or {}
    names = {j.id: f"{j.title} @ {j.company}" for j in svc.list_jobs(db, min_score=1)}
    job_id = st.selectbox("Job", list(names), format_func=names.get, index=None, placeholder="Choose a job…")
    role = st.text_input("…or type a role", disabled=bool(job_id))
    if st.button("✨ Generate prep", type="primary", disabled=not (job_id or role.strip())):
        with st.spinner("Preparing your interview sheet…"):
            job = db.get(Job, job_id) if job_id else None
            if job:
                skills = list(dict.fromkeys((job.tags or []) + (job.missing_skills or [])))
                st.session_state["prep"] = {"title": f"{job.title} · {job.company}", **generate(profile, job.title, job.company, skills, job.description)}
            else:
                st.session_state["prep"] = {"title": role.strip(), **generate(profile, role.strip(), "", (profile.get("skills") or [])[:5], "")}

    prep = st.session_state.get("prep")
    if prep:
        st.subheader(prep["title"])
        main, side = st.columns([2, 1], gap="large")
        with main:
            for i, q in enumerate(prep["questions"]):
                with st.expander(f"{i + 1}. {q['question']}", expanded=i == 0):
                    st.markdown(f"*{q['type']}*  \n**How to answer:** {q['tip']}")
        with side:
            for title, key in (("Topics to revise", "technical_topics"), ("STAR stories", "star_stories"), ("Questions to ask them", "questions_to_ask")):
                with st.container(border=True):
                    st.markdown(f"**{title}**")
                    for item in prep[key]:
                        st.write("• " + item)
