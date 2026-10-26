"""CareerPilot AI (compact). Run:  streamlit run app.py   (this file runs on every page view)"""
import streamlit as st

st.set_page_config(page_title="CareerPilot AI", page_icon="🧭", layout="wide")  # must be the first Streamlit call

from core.db import PER_VISITOR, init_db, session  # noqa: E402
from services import actions as svc  # noqa: E402
from services import analytics  # noqa: E402
from services.llm import llm  # noqa: E402
from ui.chat import render_chat  # noqa: E402
from ui.components import CSS, job_card  # noqa: E402

init_db()
st.markdown(CSS, unsafe_allow_html=True)


def dashboard() -> None:
    with session() as db:
        profile, stats = svc.get_profile(db), analytics.summary(db)
        st.title("Welcome to CareerPilot")
        st.caption("Your job search, run by a team of AI agents. You approve every step that leaves this app.")
        if not profile:
            st.info("Start with your resume.", icon="📄")
            st.page_link("pages/2_Resume.py", label="Upload resume", icon="⬆️")
            return
        if stats["pending"]:
            st.warning(f"{stats['pending']} drafts are waiting for your approval.", icon="🛡️")
            st.page_link("pages/3_Agent.py", label="Open the approval queue", icon="➡️")
        numbers = [("Jobs found", stats["jobs"]), ("Strong matches (75+)", stats["high_matches"]), ("Applications", stats["applications"]), ("ATS score", f"{profile.get('ats_score', 0)}/100")]
        for col, (label, value) in zip(st.columns(4), numbers):
            col.metric(label, value)
        st.subheader("Best matches right now")
        top = svc.list_jobs(db, min_score=1)[:3]
        if not top:
            st.info("No jobs yet. Run the agent from the Agent page.")
        for job in top:
            job_card(db, job, key="home")


nav = st.navigation([
    st.Page(dashboard, title="Dashboard", icon="🏠", default=True),
    st.Page("pages/1_Jobs.py", title="Jobs", icon="💼"),
    st.Page("pages/2_Resume.py", title="Resume", icon="📄"),
    st.Page("pages/3_Agent.py", title="Agent", icon="🤖"),
    st.Page("pages/4_Applications.py", title="Applications", icon="📋"),
    st.Page("pages/5_Outreach.py", title="Outreach", icon="✉️"),
    st.Page("pages/6_Interview.py", title="Interview", icon="🎓"),
    st.Page("pages/7_Analytics.py", title="Analytics", icon="📊"),
])

with st.sidebar:
    st.caption(f"🟢 AI: {llm.provider}" if llm.available else "⚪ Offline mode (templates). Add a Gemini key in .env for real AI.")
    st.caption("🛡️ Nothing is applied, emailed or messaged until you approve it.")
    st.caption("🔒 Your data is private to this browser session." if PER_VISITOR else "⚠️ Shared mode: everyone who opens this app sees the same data.")
render_chat()

nav.run()
