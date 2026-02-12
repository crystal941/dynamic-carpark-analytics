#!/usr/bin/env python3
import os, time, re, json, unicodedata
from datetime import datetime, timezone
from urllib.parse import urlencode
import requests
import pandas as pd
from bs4 import BeautifulSoup

AT_ENDPOINT = "https://at.govt.nz/umbraco/Surface/ParkingAvailabilitySurface/ParkingAvailabilityResult"
CARPARK_IDS = ["civic", "victoria st"]
CATEGORY = "short-term"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CarparkAnalytics/1.0)",
    "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
    "Referer": "https://at.govt.nz/parking/"
}

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)
OUTPUT_LATEST = os.path.abspath(os.path.join(DATA_DIR, "latest.csv"))
OUTPUT_HISTORY = os.path.abspath(os.path.join(DATA_DIR, "history.csv"))

# ---------- name normalisation / aliases ----------
def _norm(s: str) -> str:
    s = (s or "").strip()
    s = " ".join(s.split())
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s.lower()

ALIASES = {
    _norm("Victoria St"): "Victoria Street",
    _norm("Victoria Street"): "Victoria Street",
    _norm("Civic"): "Civic",
    _norm("Downtown"): "Downtown",
    _norm("Ronwood"): "Ronwood",
    _norm("Toka Puia"): "Toka Puia",
}
IGNORE_CARPARKS = {"albert street"}  # lowercased, after _norm
STOP_COLLECTING = {_norm("Downtown")}  # add a do-not-collect set and filter during normalization

def canonical_name(raw_name: str) -> str:
    k = _norm(raw_name)
    if k in IGNORE_CARPARKS:
        return "__IGNORE__"
    return ALIASES.get(k, (raw_name or "").strip())

# ---------- capacity lookup ----------
def load_capacity_lookup() -> dict:
    path = os.path.join(DATA_DIR, "capacity_lookup.csv")
    cap = {}
    if not os.path.exists(path):
        return cap
    import csv
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = (row.get("carpark") or "").strip()
            total = row.get("total_spaces")
            try:
                total_i = int(str(total).strip())
            except Exception:
                total_i = None
            if name and total_i:
                cap[name] = total_i
    return cap

# ---------- fetch + parse ----------
def _cache_bust():
    return {"t": datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")}

def fetch_raw():
    params = {"carparkIdParam": ", ".join(CARPARK_IDS), "categoryParam": CATEGORY, **_cache_bust()}
    url = AT_ENDPOINT + "?" + urlencode(params, doseq=True)
    print(f"[INFO] Fetching: {url}")
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    raw_path = os.path.join(DATA_DIR, f"raw_{int(time.time())}.html")
    with open(raw_path, "w", encoding="utf-8", errors="ignore") as f:
        f.write(resp.text)
    return resp.text, resp.headers.get("Content-Type", "")

def try_parse_json(resp_text: str):
    txt = resp_text.strip()
    if txt.startswith("{") or txt.startswith("["):
        try:
            return json.loads(txt)
        except Exception:
            return None
    # try embedded object
    obj_start, obj_end = txt.find("{"), txt.rfind("}")
    if obj_start != -1 and obj_end > obj_start:
        try:
            return json.loads(txt[obj_start:obj_end+1])
        except Exception:
            pass
    # try embedded array
    arr_start, arr_end = txt.find("["), txt.rfind("]")
    if arr_start != -1 and arr_end > arr_start:
        try:
            return json.loads(txt[arr_start:arr_end+1])
        except Exception:
            pass
    return None

def parse_html_table(resp_text: str):
    soup = BeautifulSoup(resp_text, "html.parser")
    rows = []
    for row in soup.select(".divTable .divTableRow"):
        cells = [c.get_text(strip=True) for c in row.select(".divTableCell")]
        if len(cells) < 3:
            continue
        carpark, option, available = cells[0], cells[1], cells[2]

        # skip unwanted (e.g., Albert Street)
        if _norm(carpark) in IGNORE_CARPARKS:
            print(f"[INFO] Skipping row for: {carpark}")
            continue

        # coerce available
        try:
            available_i = int(re.sub(r"[^\d]", "", available))
        except Exception:
            available_i = None

        rows.append({
            "carpark": carpark,
            "parking_option": option,
            "available_spaces": available_i
        })
    return rows

# ---------- main run ----------
def run():
    ts_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    body, content_type = fetch_raw()

    rows = []
    data = None
    if "application/json" in content_type.lower():
        data = try_parse_json(body)
    if data is None:
        data = try_parse_json(body)

    if isinstance(data, list):
        for rec in data:
            rows.append({
                "carpark": rec.get("carParkName") or rec.get("name") or "",
                "parking_option": rec.get("category") or rec.get("parkingOption") or "",
                "available_spaces": rec.get("availableSpaces") or rec.get("available") or None
            })
    elif isinstance(data, dict):
        for key in ("data", "results", "items", "carParks", "CarParks", "Result"):
            if key in data and isinstance(data[key], list):
                for rec in data[key]:
                    rows.append({
                        "carpark": rec.get("carParkName") or rec.get("name") or "",
                        "parking_option": rec.get("category") or rec.get("parkingOption") or "",
                        "available_spaces": rec.get("availableSpaces") or rec.get("available") or None
                    })
                break

    if not rows:
        rows = parse_html_table(body)

    capacity = load_capacity_lookup()

    # normalise & enrich
    norm_rows = []
    for r in rows:
        raw_name = r.get("carpark", "")
        canon = canonical_name(raw_name)
        if canon == "__IGNORE__":
            continue
        if _norm(canon) in STOP_COLLECTING:
            continue
        available = r.get("available_spaces")
        total = capacity.get(canon)  # may be None

        occupancy = None
        if total not in (None, 0) and available not in (None, ""):
            try:
                occupancy = round((int(total) - int(available)) / int(total), 4)
            except Exception:
                occupancy = None

        norm_rows.append({
            "timestamp_utc": ts_utc,
            "carpark": canon,
            "available_spaces": available,
            "total_spaces": total,
            "occupancy": occupancy,
            "status": "",
            "parking_option": r.get("parking_option", ""),
            "source_last_updated": ""
        })

    df = pd.DataFrame(norm_rows)
    df.to_csv(OUTPUT_LATEST, index=False)

    if os.path.exists(OUTPUT_HISTORY):
        old = pd.read_csv(OUTPUT_HISTORY)
        combined = pd.concat([old, df], ignore_index=True)
    else:
        combined = df
    combined.to_csv(OUTPUT_HISTORY, index=False)

    print(f"[OK] Wrote {OUTPUT_LATEST} ({len(df)} rows)")
    print(f"[OK] Updated {OUTPUT_HISTORY} ({len(combined)} total rows)")

if __name__ == "__main__":
    run()
