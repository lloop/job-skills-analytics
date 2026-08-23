# Job Skills Analytics

Collect job postings, store their skill tags in SQLite, and explore how skills co-occur
through an interactive D3 network graph.

## Project layout

- `scraper/`: Browser setup, posting parsing, scraping orchestration, and persistence.
- `database/`: Canonical SQLite schema (`schema.sql`) and `DatabaseManager` query layer.
- `visualization/`: Flask app and D3 exporter for the skill co-occurrence network.
- `config.py`: Site profiles, selectors, pagination settings, and the database path.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
playwright install chromium
```

## Usage

Scrape postings (the database and its schema are created automatically):

```bash
python main.py --limit 5 --max-pages 1
```

Serve the skill network dashboard at http://localhost:5000:

```bash
python -m visualization.app
```

Or export the graph as static files under `output/`:

```bash
python -m visualization.d3_exporter
```

## Tests and linting

```bash
pytest
ruff check .
```

## Data model

All components share the schema in `database/schema.sql`: `postings` (deduplicated by URL),
`skills` (unique lowercase names), and the `posting_skills` join table. Skill co-occurrence
is scored with the Jaccard index over postings.

## Adding a job board

Add a `SiteConfig` entry to `SITE_CONFIGS` in `config.py` and point `ACTIVE_SITE` at it.
The initial profile is `remoteok`, targeting `https://remoteok.com/remote-dev-jobs`.
