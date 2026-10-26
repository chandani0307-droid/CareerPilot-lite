"""AI Career Assistant in the sidebar."""
import streamlit as st

from core.db import session
from services import writer
from services.store import profile_data, quick_stats


def render_chat() -> None:
    history = st.session_state.setdefault("chat", [])
    with st.sidebar.expander("💬 Ask CareerPilot"):
        with st.container(height=240):
            for message in history:
                with st.chat_message(message["role"]):
                    st.write(message["content"])
        with st.form("chat_form", clear_on_submit=True):
            text = st.text_input("Message", placeholder="Ask about your career…", label_visibility="collapsed")
            sent = st.form_submit_button("Send", use_container_width=True)
        if sent and text.strip():
            history.append({"role": "user", "content": text.strip()})
            with session() as db, st.spinner("Thinking…"):
                reply = writer.assistant_reply(profile_data(db), history, quick_stats(db))
            history.append({"role": "assistant", "content": reply})
            st.rerun()
