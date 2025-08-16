import requests
import sqlite3
from time import sleep

DB_FILE = "bssid_data.db"

PK_LAT_MIN, PK_LAT_MAX = 23.5, 37.3
PK_LON_MIN, PK_LON_MAX = 60.9, 77.0

WIGLE_USERNAME = "AIDb37e0fbe2fc5b7f2c0fa142fd8cc5d74"
WIGLE_API_KEY = "7592eead20215d3fb0788308620fa8fe"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bssid_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bssid TEXT UNIQUE NOT NULL,
            lat REAL,
            lon REAL,
            accuracy REAL,
            timestamp TEXT,
            processed INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def save_bssids_to_db(bssids):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    for bssid, lat, lon in bssids:
        try:
            cur.execute("""
                INSERT OR IGNORE INTO bssid_data (bssid, lat, lon, processed)
                VALUES (?, ?, ?, 0)
            """, (bssid, lat, lon))
        except Exception as e:
            print(f"Error inserting {bssid}: {e}")
    conn.commit()
    conn.close()

def fetch_wigle_bssids(lat_min, lat_max, lon_min, lon_max, max_results=1000):
    url = "https://api.wigle.net/api/v2/network/search"
    headers = {
        "Accept": "application/json",
    }
    params = {
        "latrange1": lat_min,
        "latrange2": lat_max,
        "longrange1": lon_min,
        "longrange2": lon_max,
        "resultsPerPage": 100,   # max per Wigle API page
        "freenet": "false",
        "paynet": "false",
        "ssid": "",              # no SSID filter
        "first": 0,
    }

    bssids = []
    total_fetched = 0

    while total_fetched < max_results:
        response = requests.get(url, auth=(WIGLE_USERNAME, WIGLE_API_KEY), headers=headers, params=params)
        if response.status_code != 200:
            print(f"Wigle API error: {response.status_code} {response.text}")
            break

        data = response.json()
        results = data.get("results", [])
        if not results:
            break

        for entry in results:
            bssid = entry.get("netid")
            lat = float(entry.get("trilat", 0))
            lon = float(entry.get("trilong", 0))
            bssids.append((bssid, lat, lon))
            total_fetched += 1
            if total_fetched >= max_results:
                break

        params["first"] += len(results)
        print(f"Fetched {total_fetched} BSSIDs from Wigle...")
        sleep(1)  # be polite, avoid hammering API

    return bssids

if __name__ == "__main__":
    init_db()
    bssids = fetch_wigle_bssids(PK_LAT_MIN, PK_LAT_MAX, PK_LON_MIN, PK_LON_MAX, max_results=5000)
    save_bssids_to_db(bssids)
    print(f"Seeded {len(bssids)} BSSIDs into DB.")
