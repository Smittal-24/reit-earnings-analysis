# REIT 5-Quarter Earnings Agent

On-demand Streamlit dashboard that tracks a watchlist of Indian listed REITs and analyzes
their last 5 reported quarters of earnings (presentations, transcripts, filings) to produce
a trend table, 6-area analysis, "what changed" summary, risks/catalysts, and an
investment-committee-ready summary — one REIT at a time, run whenever the user chooses.

No scheduled jobs — every run is triggered manually from the dashboard's Manual Run tab.

## Setup
1. `pip install -r requirements.txt`
2. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill in your
   Anthropic API key and a GitHub fine-grained personal access token (repo-scoped).
3. `streamlit run app.py`

## Structure
- `engine/` — standalone analysis engine (sections 7-10 of the build brief), unit-tested independently of data sourcing
- `data_fetch/` — pulls investor presentations/transcripts from REIT IR sites, NSE/BSE, Screener.in
- `extraction/` — turns raw documents into structured per-quarter metrics
- `storage/` — reads/writes the shared GitHub repo (watchlist, documents, structured data, history, workbook)
- `excel/` — openpyxl workbook logging (Quarterly Data Log, Analysis Log, Guidance Tracker)
- `reports/` — on-demand PDF/Word report generation
- `dashboard/` — Streamlit tab implementations
- `tests/` — fixture-based unit tests for the analysis engine