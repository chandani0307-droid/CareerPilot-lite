import streamlit as st
from sqlalchemy import select

from agents.graph import run_agent
from models.tables import AgentRun
from services import actions as svc
from ui.components import REGION, action_card, session

PIPELINE = ["Planner", "Job Scout", "Matcher", "Cover Letter Writer", "Outreach Agent", "Interview Coach", "Approval Gate"]
ICON = {"done": "✅", "waiting": "🟡", "blocked": "⛔", "failed": "⛔"}

st.title("Agent workspace")
st.caption("Seven agents work as one LangGraph workflow. They only draft. You approve everything that goes out.")

with session() as db:
    profile = svc.get_profile(db)
    left, right = st.columns([1, 2], gap="large")
    with left:
        with st.container(border=True):
            query = st.text_input("Search focus (optional)", placeholder="Defaults to your target roles")
            region = st.selectbox("Region", list(REGION), format_func=REGION.get)
            location = st.text_input("City or country (optional)")
            top_k = st.select_slider("Prepare the top N jobs", [1, 2, 3, 5], value=3)
            run = st.button("▶ Run agent", type="primary", use_container_width=True, disabled=not profile)
            if not profile:
                st.caption("Upload your resume first (Resume page).")
    if run:
        with st.spinner("Agents are working…"):
            result = run_agent(db, {"goal": "Find and prepare the best jobs", "query": query, "region": region, "location": location, "top_k": top_k})
        st.session_state["run_id"] = result.id

    with right:
        st.subheader("Workflow")
        last = db.get(AgentRun, st.session_state["run_id"]) if "run_id" in st.session_state else db.scalar(select(AgentRun).order_by(AgentRun.id.desc()).limit(1))
        if not last:
            st.info("No runs yet. Press Run agent.")
        else:
            steps = {t["agent"]: t for t in last.trace}
            for name in PIPELINE:
                s = steps.get(name)
                st.markdown(f"{ICON.get(s['status'], '⚪') if s else '⚪'} **{name}**  \n{s['message'] if s else 'Skipped'}")
            for t in last.trace:
                if t["agent"] == "Orchestrator":
                    st.error(t["message"])

    st.divider()
    pending = svc.list_actions(db, "pending")
    st.subheader(f"🛡️ Approval queue ({len(pending)})")
    if not pending:
        st.info("Nothing is waiting for approval. Run the agent to create drafts.")
    cols = st.columns(2)
    for i, act in enumerate(pending):
        with cols[i % 2]:
            action_card(db, act, key="queue")
