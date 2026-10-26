"""Regression tests for the job-specific interview generator (offline, no AI)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services.interview import generate

PROFILE = {"name": "Aarav Mehta", "skills": ["Python", "SQL", "Pandas", "Scikit-learn", "Machine Learning", "Statistics"], "experience_years": 3,
           "target_roles": ["Data Scientist"], "strengths": ["Hands-on with Python"]}
NOISY_TAGS = [".NET", "Android", "C++", "dotnet", "python", "sql"]
BAD = [".net", "android", "c++", "kotlin", "swift", "c#"]


def _blob(prep: dict) -> str:
    qs = " ".join(q["question"] + " " + q["tip"] for q in prep["questions"])
    return (qs + " " + " ".join(prep["technical_topics"] + prep["star_stories"] + prep["questions_to_ask"])).lower()


def test_no_offtopic_tech_for_data_roles():
    for role in ("Data Scientist", "Data Analyst"):
        text = _blob(generate(PROFILE, role, "Acme Analytics", NOISY_TAGS, "Build models. Experience with .NET, Android and C++ is a plus. Use Python and SQL."))
        for bad in BAD:
            assert bad not in text, (role, bad)


def test_different_jobs_get_different_prep():
    a = generate(PROFILE, "Data Scientist", "Acme Analytics", ["Python", "Scikit-learn"], "Build churn models and run experiments with Python.")
    b = generate(PROFILE, "Data Analyst", "Bharat Retail", ["SQL", "Power BI"], "Build dashboards and own weekly KPI reporting with SQL and Power BI.")
    qa, qb = {q["question"] for q in a["questions"]}, {q["question"] for q in b["questions"]}
    assert len(qa & qb) <= 2
    assert {q["tip"] for q in a["questions"]}.isdisjoint({q["tip"] for q in b["questions"]})
    assert "bharat retail" in _blob(b) and "acme analytics" in _blob(a)


def test_missing_skill_is_called_out_and_shape_is_stable():
    prep = generate(PROFILE, "Data Analyst", "Bharat Retail", ["SQL", "Power BI", "Tableau"], "Own dashboards in Power BI and Tableau.")
    assert "power bi" in _blob(prep) and "not on your resume" in _blob(prep)
    assert set(prep) >= {"questions", "technical_topics", "star_stories", "questions_to_ask"}
    assert all({"question", "type", "tip"} <= set(q) for q in prep["questions"]) and len(prep["questions"]) >= 8
