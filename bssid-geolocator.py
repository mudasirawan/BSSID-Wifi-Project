#!/usr/bin/env python3
import logging
import argparse
import requests
import bssid_pb2
import sqlite3
import time
from datetime import datetime
import os
from urllib3.exceptions import InsecureRequestWarning

# Suppress SSL warnings for Apple API
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

logger = logging.getLogger("bssid-geolocator")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

DB_FILE = "bssid_data.db"
MAX_BSSIDS = 1000000  # limit to avoid infinite loops

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bssid_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bssid TEXT NOT NULL UNIQUE,
            lat REAL,
            lon REAL,
            accuracy REAL,
            timestamp TEXT,
            processed INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def get_db_row_count():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM bssid_data")
    count = cur.fetchone()[0]
    conn.close()
    return count

def save_to_db(locations):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    now = datetime.now().isoformat(timespec='seconds')
    inserted = 0
    updated = 0
    for loc in locations:
        bssid = loc[0]
        lat, lon = map(float, loc[1].split(","))
        accuracy = loc[3]
        try:
            cur.execute("""
                INSERT INTO bssid_data (bssid, lat, lon, accuracy, timestamp, processed)
                VALUES (?, ?, ?, ?, ?, 0)
                ON CONFLICT(bssid) DO UPDATE SET
                    lat=excluded.lat,
                    lon=excluded.lon,
                    accuracy=excluded.accuracy,
                    timestamp=excluded.timestamp
            """, (bssid, lat, lon, accuracy, now))
            if cur.rowcount == 1:
                inserted += 1
            else:
                updated += 1
        except Exception as e:
            logger.error(f"DB insert/update failed for {bssid}: {e}")
    conn.commit()
    conn.close()
    total = get_db_row_count()
    logger.info(f"DB save: Inserted {inserted}, Updated {updated}, Total rows now {total}")

def get_unprocessed_bssids():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT bssid FROM bssid_data WHERE processed = 0")
    rows = [r[0] for r in cur.fetchall()]
    conn.close()
    return rows

def mark_as_processed(bssid):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("UPDATE bssid_data SET processed = 1 WHERE bssid = ?", (bssid,))
    conn.commit()
    conn.close()

def geolocateApple(bssid):
    logger.info(f"Querying Apple API for {bssid}")
    data_bssid = f"\x12\x13\n\x11{bssid}\x18\x00\x20\00"
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': '*/*',
        "Accept-Charset": "utf-8",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "en-us",
        'User-Agent': 'locationd/1753.17 CFNetwork/711.1.12 Darwin/14.0.0'
    }
    data = "\x00\x01\x00\x05en_US\x00\x13com.apple.locationd\x00\x0a" + \
           "8.1.12B411\x00\x00\x00\x01\x00\x00\x00" + \
           chr(len(data_bssid)) + data_bssid

    try:
        r = requests.post('https://gs-loc.apple.com/clls/wloc', headers=headers, data=data, verify=False, timeout=10)
        r.raise_for_status()
    except Exception as e:
        logger.error(f"Error querying Apple API for {bssid}: {e}")
        return []

    bssidResponse = bssid_pb2.WiFiLocation()
    bssidResponse.ParseFromString(r.content[10:])

    neighbors = []
    for wifi in bssidResponse.wifi:
        paddedBSSID = ":".join("0"+x if len(x) == 1 else x for x in wifi.bssid.split(":"))
        lat = wifi.location.lat * 1e-8
        lon = wifi.location.lon * 1e-8
        channel = wifi.channel
        accuracy = wifi.location.hacc
        neighbors.append((paddedBSSID, f"{lat},{lon}", channel, accuracy))

    logger.info(f"Found {len(neighbors)} neighbors for {bssid}")
    return neighbors

def process_bssid(bssid):
    neighbors = geolocateApple(bssid)
    if not neighbors:
        mark_as_processed(bssid)
        return 0

    save_to_db(neighbors)
    mark_as_processed(bssid)
    return len(neighbors)

def main(args):
    logger.info(f"Using DB file: {os.path.abspath(DB_FILE)}")
    init_db()

    if not args.bssid:
        logger.error("Please provide a starting BSSID with -b")
        return

    # Seed starting BSSID if not in DB
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT bssid FROM bssid_data WHERE bssid = ?", (args.bssid,))
    if not cur.fetchone():
        cur.execute("INSERT INTO bssid_data (bssid, processed) VALUES (?, 0)", (args.bssid,))
        conn.commit()
    conn.close()

    processed_count = 0

    while processed_count < MAX_BSSIDS:
        unprocessed = get_unprocessed_bssids()
        if not unprocessed:
            logger.info("No more unprocessed BSSIDs left. Crawl complete.")
            break

        for bssid in unprocessed:
            logger.info(f"Processing {bssid} ({processed_count + 1}/{MAX_BSSIDS})")
            count = process_bssid(bssid)
            processed_count += 1
            time.sleep(1)  # API rate limit friendly delay

            if processed_count >= MAX_BSSIDS:
                logger.info(f"Reached max limit {MAX_BSSIDS}")
                break

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Recursive BSSID geolocator using Apple API")
    parser.add_argument("-b", "--bssid", help="Starting BSSID to begin recursive search", required=True)
    args = parser.parse_args()

    main(args)
