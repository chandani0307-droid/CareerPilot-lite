# CareerPilot AI (Compact): Python-only version, about half the code

The same agentic job-search assistant, **without web development**, written in the smallest readable form so it can be typed live in class. No React, no FastAPI, no HTML/CSS/JavaScript. The whole app is Python, and the screens are built with [Streamlit](https://streamlit.io).

**Stack:** Streamlit · LangGraph · LangChain · SQLAlchemy (SQLite, PostgreSQL-ready) · free job APIs

## Run it (5 minutes)

Requirements: **Python 3.10+** only (no Node.js).

```bash
cd careerpilot-lite
python -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # Windows: copy .env.example .env   (all keys are optional)
streamlit run app.py
```

Open http://localhost:8501, go to **Resume**, upload `sample_resume.txt`, then open **Agent** and press **Run agent**.

No API key is needed: without one the app uses offline templates and sample jobs. For real AI drafts, put a free Gemini key (https://aistudio.google.com/apikey) in `.env` as `GEMINI_API_KEY`.

## How the project is organised

| Folder / file | What it does | Teaches |
|---|---|---|
| `app.py` | Entry point: page setup, sidebar, navigation, Dashboard | Streamlit app structure |
| `pages/` | One file per screen (Jobs, Resume, Agent, Applications, Outreach, Interview, Analytics) | Building UI in Python |
| `ui/components.py` | Reusable widgets: job card, score badge, approval card | Reusable UI code |
| `ui/chat.py` | AI Career Assistant in the sidebar | Chat with `st.session_state` |
| `core/` | `config.py` reads `.env`; `db.py` connects the database | Config and secrets |
| `models/tables.py` | Database tables as Python classes | SQLAlchemy ORM |
| `services/actions.py` | Every user operation as a function (upload, search, approve) | Clean service layer |
| `services/analytics.py` | Numbers for charts | Aggregation |
| `services/skills.py`, `resume_parser.py`, `matching.py` | Skill detection, resume analysis, explainable match score | Plain Python and regex |
| `services/llm.py`, `writer.py`, `interview.py`, `fallbacks.py` | AI drafting with offline fallbacks | Prompts, validation |
| `services/jobs/` | Free job sources, merging, sample jobs | APIs and RSS |
| `agents/graph.py` | The 7-agent LangGraph workflow | Agentic AI |
| `tests/` | Offline unit tests: `pytest` | Testing |

### The agent workflow
`Planner → Job Scout → Matcher → Resume & Cover Letter Writer → Outreach Agent → Interview Coach → Approval Gate`

Agents only **read, score and draft**. A draft becomes an external action only when you click **Approve & run** and confirm. That is the single place in the code that can send or open anything (`approve_action` in `services/actions.py`).

## Streamlit tips for beginners
- Streamlit **re-runs the page from top to bottom on every click.** Data you want to keep between clicks goes in `st.session_state`.
- Every button inside a loop needs a unique `key=`.
- `with session() as db:` opens a database connection and closes it at the end.

## Deploy for free (Streamlit Community Cloud)
1. Push this folder to a GitHub repo.
2. At https://share.streamlit.io choose the repo and set the main file to `app.py`.
3. Under **Settings → Secrets**, add keys in TOML form, e.g. `GEMINI_API_KEY = "..."`. Top-level secrets are available as environment variables.
4. The free tier resets local files on restart, so SQLite data can disappear. For permanent data, set `DATABASE_URL` to a free hosted PostgreSQL and add `psycopg[binary]` to `requirements.txt`.

## Privacy: every visitor gets their own data
When you share the link, each visitor starts with an **empty app**. Their resume, jobs, drafts and applications are stored in a private file (`data/visitor_<id>.db`) that belongs to their browser session only. Nobody else can see it, and the file is deleted automatically after `VISITOR_TTL_HOURS` (default 6) hours without changes. Refreshing the page starts a new, empty session.

- `PER_VISITOR_DATA=true` (default): private data per visitor. Use this when you share or deploy the app.
- `PER_VISITOR_DATA=false`: one shared database, so your data survives a page refresh. Use this only on your own laptop. The sidebar then shows a "Shared mode" warning.
- This mode needs SQLite. With PostgreSQL (`DATABASE_URL=postgresql...`) the app falls back to shared mode, so add real login first.

You can also erase your own data at any time: **Resume → Delete my data**. For SQLite the file is compacted afterwards so deleted rows are really erased.

## Tests
```bash
pytest
```

## Limits
- Single user, no login. Add authentication before sharing a public deployment.
- Scanned (image-only) PDFs are not OCR'd. Use a text PDF or DOCX.
- Free job APIs have thin India coverage. Add the Adzuna key (`ADZUNA_APP_ID`, `ADZUNA_APP_KEY`) for better results. Listings marked **Sample listing** are placeholders.
- HR emails are never guessed. Enter the recipient yourself, or set `HUNTER_API_KEY` for lookups.
