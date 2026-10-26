"""Free job-source adapters. Each returns normalised dicts and NEVER raises (returns [] on failure).

Add a new source: write `fetch_x(query, limit) -> list[dict]` and register it in PROVIDERS.
Normalised keys: title, company, location, tags, salary, url, apply_url, description, source, posted_at
"""
from __future__ import annotations

import html
import logging
import re
import xml.etree.ElementTree as ET
from urllib.parse import quote_plus

import httpx

from core.config import settings

log = logging.getLogger("careerpilot.jobs")
HEADERS = {"User-Agent": "CareerPilotAI/1.0 (personal job search tool)"}


def _clean(text: str, limit: int = 4000) -> str:
    text = re.sub(r"<(script|style).*?</\1>", " ", text or "", flags=re.S | re.I)
    text = re.sub(r"<br\s*/?>|</p>|</li>", "\n", text, flags=re.I)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n", text)).strip()[:limit]


def _get(url: str, **params):
    with httpx.Client(timeout=settings.http_timeout, headers=HEADERS, follow_redirects=True) as c:
        r = c.get(url, params=params or None)
        r.raise_for_status()
        return r


def fetch_remotive(query: str, limit: int = 20) -> list[dict]:
    try:
        data = _get("https://remotive.com/api/remote-jobs", search=query or "developer", limit=limit).json()
        return [{
            "title": j.get("title", ""), "company": j.get("company_name", ""), "location": f"Remote ({j.get('candidate_required_location') or 'Worldwide'})",
            "tags": j.get("tags") or [], "salary": j.get("salary") or "", "url": j.get("url", ""), "apply_url": j.get("url", ""),
            "description": _clean(j.get("description", "")), "source": "remotive", "posted_at": (j.get("publication_date") or "")[:10],
        } for j in data.get("jobs", [])[:limit]]
    except Exception as exc:  # noqa: BLE001
        log.info("remotive unavailable: %s", exc)
        return []


def fetch_remoteok(query: str, limit: int = 20) -> list[dict]:
    try:
        data = _get("https://remoteok.com/api").json()
        out = []
        for j in data:
            if not isinstance(j, dict) or not j.get("position"):
                continue
            sal = f"${j['salary_min']:,}–${j['salary_max']:,}" if j.get("salary_min") and j.get("salary_max") else ""
            out.append({
                "title": j.get("position", ""), "company": j.get("company", ""), "location": f"Remote ({j.get('location') or 'Worldwide'})",
                "tags": j.get("tags") or [], "salary": sal, "url": j.get("url", ""), "apply_url": j.get("apply_url") or j.get("url", ""),
                "description": _clean(j.get("description", "")), "source": "remoteok", "posted_at": (j.get("date") or "")[:10],
            })
        return out
    except Exception as exc:  # noqa: BLE001
        log.info("remoteok unavailable: %s", exc)
        return []


def fetch_arbeitnow(query: str, limit: int = 20) -> list[dict]:
    try:
        data = _get("https://www.arbeitnow.com/api/job-board-api").json()
        return [{
            "title": j.get("title", ""), "company": j.get("company_name", ""),
            "location": ("Remote – " if j.get("remote") else "") + (j.get("location") or "Europe"),
            "tags": j.get("tags") or [], "salary": "", "url": j.get("url", ""), "apply_url": j.get("url", ""),
            "description": _clean(j.get("description", "")), "source": "arbeitnow", "posted_at": "",
        } for j in data.get("data", [])]
    except Exception as exc:  # noqa: BLE001
        log.info("arbeitnow unavailable: %s", exc)
        return []


def fetch_adzuna(query: str, limit: int = 20) -> list[dict]:
    if not (settings.adzuna_app_id and settings.adzuna_app_key):
        return []
    out: list[dict] = []
    for country in settings.adzuna_countries:
        try:
            data = _get(f"https://api.adzuna.com/v1/api/jobs/{country}/search/1", app_id=settings.adzuna_app_id, app_key=settings.adzuna_app_key,
                        what=query or "software developer", results_per_page=min(limit, 20), **{"content-type": "application/json"}).json()
            for j in data.get("results", []):
                sal = f"{int(j['salary_min']):,}–{int(j['salary_max']):,}" if j.get("salary_min") and j.get("salary_max") else ""
                out.append({
                    "title": _clean(j.get("title", ""), 200), "company": (j.get("company") or {}).get("display_name", ""),
                    "location": (j.get("location") or {}).get("display_name", "") + (", India" if country == "in" else ""),
                    "tags": [], "salary": sal, "url": j.get("redirect_url", ""), "apply_url": j.get("redirect_url", ""),
                    "description": _clean(j.get("description", "")), "source": f"adzuna-{country}", "posted_at": (j.get("created") or "")[:10],
                })
        except Exception as exc:  # noqa: BLE001
            log.info("adzuna %s unavailable: %s", country, exc)
    return out


def fetch_rss(query: str, limit: int = 20) -> list[dict]:
    out: list[dict] = []
    for feed in settings.job_rss_feeds:
        try:
            root = ET.fromstring(_get(feed).content)
            for item in root.iter("item"):
                raw_title = (item.findtext("title") or "").strip()
                company, title = "", raw_title
                if ":" in raw_title:  # "Company: Job title" (WeWorkRemotely style)
                    company, title = [s.strip() for s in raw_title.split(":", 1)]
                elif " at " in raw_title:
                    title, company = [s.strip() for s in raw_title.rsplit(" at ", 1)]
                link = (item.findtext("link") or "").strip()
                out.append({
                    "title": title, "company": company or "Unknown", "location": "Remote (Worldwide)", "tags": [], "salary": "",
                    "url": link, "apply_url": link, "description": _clean(item.findtext("description") or ""),
                    "source": "rss", "posted_at": (item.findtext("pubDate") or "")[:16],
                })
        except Exception as exc:  # noqa: BLE001
            log.info("rss %s unavailable: %s", feed, exc)
    return out[: limit * 2]


PROVIDERS = {"remotive": fetch_remotive, "remoteok": fetch_remoteok, "arbeitnow": fetch_arbeitnow, "adzuna": fetch_adzuna, "rss": fetch_rss}


def linkedin_people_search(company: str) -> str:
    return f"https://www.linkedin.com/search/results/people/?keywords={quote_plus('recruiter ' + company)}"
