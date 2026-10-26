import streamlit as st

from models.tables import Job
from services import actions as svc
from ui.components import REGION, job_card, session

st.title("Jobs")
st.caption("Live listings from free job boards, scored against your skills.")

with session() as db:
    with st.form("search"):
        c1, c2 = st.columns([3, 1])
        query = c1.text_input("Search", placeholder="Leave blank to search by your profile")
        location = c2.text_input("City or country")
        region = st.radio("Region", list(REGION), format_func=REGION.get, horizontal=True)
        min_score = st.slider("Minimum match", 0, 90, 0, 5)
        go = st.form_submit_button("Search jobs", type="primary")
    if go:
        with st.spinner("Searching job boards…"):
            rows, report = svc.search_and_store(db, query, region, location, 30)
        st.session_state["job_ids"] = [r.id for r in rows]
        if not svc.get_profile(db):
            st.warning("Upload a resume to get real match scores.")
    ids = st.session_state.get("job_ids")
    jobs = [db.get(Job, i) for i in ids] if ids else svc.list_jobs(db, region, min_score)
    jobs = [j for j in jobs if j and j.match_score >= min_score]
    if not jobs:
        st.info("No jobs yet. Press Search jobs. Sample jobs appear if no live source answers.")
    for job in jobs[:30]:
        job_card(db, job, key="jobs")
