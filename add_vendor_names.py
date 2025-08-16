# #!/usr/bin/env python3
# import sqlite3
# import requests
# import time

# DB_FILE = "bssid_data_main.db"
# API_URL = "https://api.macvendors.com/"  # MAC address vendor lookup API

# def ensure_vendor_column():
#     conn = sqlite3.connect(DB_FILE)
#     cur = conn.cursor()
#     try:
#         cur.execute("ALTER TABLE bssid_data ADD COLUMN vendor TEXT")
#         conn.commit()
#         print("[INFO] Added 'vendor' column.")
#     except sqlite3.OperationalError:
#         print("[INFO] 'vendor' column already exists.")
#     conn.close()

# def get_vendor(mac):
#     try:
#         r = requests.get(API_URL + mac, timeout=5)
#         if r.status_code == 200:
#             return r.text.strip()
#     except Exception as e:
#         print(f"[ERROR] Vendor lookup failed for {mac}: {e}")
#     return None

# def update_vendors():
#     conn = sqlite3.connect(DB_FILE)
#     cur = conn.cursor()
#     cur.execute("SELECT id, bssid FROM bssid_data WHERE vendor IS NULL OR vendor = ''")
#     rows = cur.fetchall()
#     print(f"[INFO] Found {len(rows)} BSSIDs missing vendor info.")

#     for row_id, bssid in rows:
#         vendor = get_vendor(bssid)
#         if vendor:
#             cur.execute("UPDATE bssid_data SET vendor = ? WHERE id = ?", (vendor, row_id))
#             conn.commit()
#             print(f"[INFO] {bssid} → {vendor}")
#         else:
#             print(f"[WARN] Could not find vendor for {bssid}")
#         time.sleep(1)  # avoid hammering API

#     conn.close()
#     print("[INFO] Vendor update complete.")

# if __name__ == "__main__":
#     ensure_vendor_column()
#     update_vendors()



#!/usr/bin/env python3
import sqlite3
import requests

DB_FILE = "bssid_data_main.db"
API_URL = "https://api.macvendors.com/"  # MAC address vendor lookup API

def ensure_vendor_column():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    try:
        cur.execute("ALTER TABLE bssid_data ADD COLUMN vendor TEXT")
        conn.commit()
        print("[INFO] Added 'vendor' column.")
    except sqlite3.OperationalError:
        print("[INFO] 'vendor' column already exists.")
    conn.close()

def get_vendor(mac):
    try:
        r = requests.get(API_URL + mac, timeout=3)
        if r.status_code == 200:
            return r.text.strip()
    except Exception as e:
        print(f"[ERROR] Vendor lookup failed for {mac}: {e}")
    return None

def update_vendors(batch_size=20):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT id, bssid FROM bssid_data WHERE vendor IS NULL OR vendor = ''")
    rows = cur.fetchall()
    print(f"[INFO] Found {len(rows)} BSSIDs missing vendor info.")

    updates = []
    for row_id, bssid in rows:
        vendor = get_vendor(bssid)
        if vendor:
            updates.append((vendor, row_id))
            print(f"[INFO] {bssid} → {vendor}")
        else:
            print(f"[WARN] Could not find vendor for {bssid}")

        # Commit in batches
        if len(updates) >= batch_size:
            cur.executemany("UPDATE bssid_data SET vendor = ? WHERE id = ?", updates)
            conn.commit()
            updates.clear()

    # Commit any remaining updates
    if updates:
        cur.executemany("UPDATE bssid_data SET vendor = ? WHERE id = ?", updates)
        conn.commit()

    conn.close()
    print("[INFO] Vendor update complete.")

if __name__ == "__main__":
    ensure_vendor_column()
    update_vendors()
