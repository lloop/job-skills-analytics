# Job Skills Analytics

Collect job postings, extract technology skills, and store the results in SQLite for analysis.

## Project layout

- `scraper/`: Browser setup, posting parsing, and scraping orchestration.
- `analytics/`: Skill extraction from job descriptions.
- `database/`: SQLite schema and persistence helpers.
- `config.py`: Search terms, locations, pagination settings, and site profiles.
- `app.py`: Optional dashboard entry point.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

Initialize the database with `database/schema.sql` before running a pipeline.

The initial site profile is `remoteok`, targeting `https://remoteok.com/remote-dev-jobs`.
Add another `SiteConfig` entry to `SITE_CONFIGS` when configuring a new job board.
