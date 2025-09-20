
# Dynamic Carpark Analytics

End-to-end **ETL + dashboard** for Auckland carpark availability.

## What this does
- **Extract**: Pull availability JSON from AT endpoint (IDs: civic, downtown, victoria st).
- **Transform**: Normalize records, compute occupancy metrics, and append to a time-series CSV.
- **Load**: Save structured CSV to `data/latest.csv` and append historical data to `data/history.csv`.
- **Visualize**: Render an R Markdown dashboard to `output/index.html` (for GitHub Pages).
- **CI/CD**: On every push to `main`, GitHub Actions runs ETL + dashboard and deploys to Pages.

## Run locally
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/etl.py
Rscript scripts/build_dashboard.R
```
