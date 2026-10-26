"""Offline tests for the pure-Python core (no network, no API keys)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services import fallbacks
from services.jobs.aggregator import classify_region
from services.jobs.mock_jobs import mock_jobs
from services.matching import score_job
from services.resume_parser import analyze_heuristic
from services.skills import extract_skills

RESUME = """Priya Sharma
priya.sharma@example.com | +91 98765 43210 | Bengaluru, India
linkedin.com/in/priya-sharma | github.com/priyas

Summary
Backend engineer with 4 years of experience building APIs.

Experience
Software Engineer, Acme Systems  2021 - Present
- Built FastAPI microservices on AWS with PostgreSQL and Docker, cutting latency by 35%
- Served 50k users; wrote pytest suites and CI/CD pipelines with GitHub Actions
- Built a RAG prototype with LangChain and LLMs

Education
B.Tech Computer Science, VIT University 2016 - 2020

Skills
Python, FastAPI, Django, PostgreSQL, Redis, Docker, AWS, Git, REST APIs, SQL, Kubernetes
Projects
Job tracker in React and TypeScript
"""


def test_skill_extraction():
    s = extract_skills(RESUME)
    for want in ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS", "LangChain", "React", "TypeScript"]:
        assert want in s, want
    assert "Java" not in s  # must not match JavaScript/other substrings


def test_resume_analysis():
    p = analyze_heuristic(RESUME)
    assert p["name"] == "Priya Sharma"
    assert p["email"] == "priya.sharma@example.com"
    assert p["current_location"] == "Bengaluru"
    assert p["experience_years"] == 4.0
    assert "Backend Engineer" in p["target_roles"]
    assert p["ats_score"] >= 60


def test_matching_prefers_relevant_job():
    p = analyze_heuristic(RESUME)
    jobs = {j["title"]: j for j in mock_jobs()}
    for j in jobs.values():
        j["region"] = j.get("region")
    good, _, _ = score_job(p, jobs["Python Backend Engineer"])
    bad, _, missing = score_job(p, jobs["Remote QA Automation Engineer"])
    assert good > bad and good >= 60
    assert score_job(p, jobs["Data Analyst"])[2]  # missing skills reported


def test_region_classification():
    assert classify_region("Pune, India") == "india"
    assert classify_region("Remote (Worldwide)") == "remote"
    assert classify_region("Berlin, Germany") == "abroad"


def test_fallback_drafts():
    p = analyze_heuristic(RESUME)
    job = mock_jobs()[0]
    assert "Nimbus Labs" in fallbacks.cover_letter(p, job)
    assert len(fallbacks.linkedin(p, job)) <= 300
