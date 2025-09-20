# Dynamic Carpark Analytics 🚗📊

End-to-end **ETL + Dashboard** for monitoring Auckland carpark availability.

---

## 🔎 What this project does
- **Extract**: Scrapes live carpark availability data from Auckland Transport’s public endpoint (Civic, Downtown, Victoria Street, Ronwood, Toka Puia).  
- **Transform**: Normalises records, maps them to known capacities, and computes occupancy metrics.  
- **Load**: Saves structured data into:
  - `data/latest.csv` (snapshot)  
  - `data/history.csv` (time-series log for trends)  
- **Visualise**: Builds an R Markdown dashboard (`output/index.html`) showing:
  - Occupancy % trends  
  - Available spaces over time  
  - Faceted comparisons by carpark  
- **Automate**: GitHub Actions runs ETL + dashboard hourly and deploys to **GitHub Pages**.

---

## 🌐 Live Dashboard
The latest dashboard is published automatically here:  
👉 [View Dashboard on GitHub Pages](https://crystal941.github.io/dynamic-carpark-analytics/)

---

## 🛠 Run locally
Clone and install dependencies:

```bash
git clone https://github.com/crystal941/dynamic-carpark-analytics.git
cd dynamic-carpark-analytics

# Python setup
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run ETL
python scripts/etl.py

# Build dashboard (requires R + rmarkdown)
Rscript scripts/build_dashboard.R
```

Output will be in `output/index.html`.

---

## ⚙️ CI/CD Workflow
- Every push to `main` triggers the pipeline.  
- A scheduled job runs **hourly** (top of the hour, UTC).  
- Workflow steps:
  1. Run Python ETL to update `latest.csv` and `history.csv`.  
  2. Render dashboard via R Markdown.  
  3. Deploy static site + CSVs to the `gh-pages` branch.  

---

## 📂 Repo Structure
```
data/               # CSV data (latest + history)
scripts/            # ETL + dashboard build scripts
output/             # Rendered dashboard for GitHub Pages
.github/workflows/  # CI/CD workflow definition
```

---

## 🚀 Tech Stack
- **Python**: `requests`, `pandas`, `beautifulsoup4` (ETL pipeline)  
- **R**: `rmarkdown`, `ggplot2`, `dplyr`, `lubridate` (visualisation)  
- **CI/CD**: GitHub Actions, scheduled hourly builds  
- **Hosting**: GitHub Pages  
