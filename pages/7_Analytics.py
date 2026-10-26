import pandas as pd
import streamlit as st

from services import analytics
from ui.components import REGION, session

st.title("Analytics")
st.caption("Where your search stands and which skills matter most.")

with session() as db:
    a = analytics.summary(db)

numbers = [("Jobs scored", a["jobs"]), ("Average match", f"{a['avg_match']}%"), ("Strong matches", a["high_matches"]), ("Applications", a["applications"]), ("Awaiting approval", a["pending"])]
for col, (label, value) in zip(st.columns(5), numbers):
    col.metric(label, value)


def bar(title: str, data: dict) -> None:
    st.subheader(title)
    if data and any(data.values()):
        st.bar_chart(pd.DataFrame({"count": list(data.values())}, index=list(data.keys())))
    else:
        st.write("No data yet.")


left, right = st.columns(2, gap="large")
with left:
    bar("Application funnel", a["funnel"])
    bar("Jobs by region", {REGION.get(r, r): n for r, n in a["by_region"].items()})
with right:
    bar("Skill gaps (asked by jobs, missing from your profile)", a["gaps"])
    st.subheader("Most requested skills")
    if a["demand"]:
        df = pd.DataFrame(a["demand"])
        df["you have it"] = df["have"].map({True: "✅", False: "❌"})
        st.dataframe(df[["skill", "count", "you have it"]], hide_index=True, use_container_width=True)
    else:
        st.write("No job data yet.")
