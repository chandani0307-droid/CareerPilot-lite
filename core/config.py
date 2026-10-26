"""Central configuration. Everything comes from environment variables / .env — never hardcode keys."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")


def _list(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


def _bool(value: str, default: bool = False) -> bool:
    if value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    app_name: str = "CareerPilot AI"
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL") or f"sqlite:///{ROOT_DIR / 'careerpilot.db'}")

    # AI (optional): a free Gemini key switches the app from templates to real AI
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    gemini_model: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))

    # Jobs
    job_providers: list[str] = field(default_factory=lambda: _list(os.getenv("JOB_PROVIDERS", "remotive,remoteok,arbeitnow,rss,adzuna")))
    job_rss_feeds: list[str] = field(default_factory=lambda: _list(os.getenv("JOB_RSS_FEEDS", "https://weworkremotely.com/categories/remote-programming-jobs.rss")))
    adzuna_app_id: str = field(default_factory=lambda: os.getenv("ADZUNA_APP_ID", ""))
    adzuna_app_key: str = field(default_factory=lambda: os.getenv("ADZUNA_APP_KEY", ""))
    adzuna_countries: list[str] = field(default_factory=lambda: _list(os.getenv("ADZUNA_COUNTRIES", "in,gb,us")))
    mock_fallback: bool = field(default_factory=lambda: _bool(os.getenv("MOCK_JOBS_FALLBACK", "true"), True))
    http_timeout: float = field(default_factory=lambda: float(os.getenv("HTTP_TIMEOUT", "8")))

    # Email (optional): without SMTP the app opens a mailto draft instead
    smtp_host: str = field(default_factory=lambda: os.getenv("SMTP_HOST", ""))
    smtp_port: int = field(default_factory=lambda: int(os.getenv("SMTP_PORT", "587")))
    smtp_user: str = field(default_factory=lambda: os.getenv("SMTP_USER", ""))
    smtp_password: str = field(default_factory=lambda: os.getenv("SMTP_PASSWORD", ""))
    smtp_from: str = field(default_factory=lambda: os.getenv("SMTP_FROM", ""))

    # Privacy: every visitor gets a private database file that is deleted after a few hours
    per_visitor_data: bool = field(default_factory=lambda: _bool(os.getenv("PER_VISITOR_DATA", "true"), True))
    visitor_ttl_hours: float = field(default_factory=lambda: float(os.getenv("VISITOR_TTL_HOURS", "6")))

    @property
    def smtp_configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_user and self.smtp_password)


settings = Settings()
