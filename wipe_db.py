import sqlite3

DB_FILE = "bssid_data.db"

def wipe_database():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("DELETE FROM bssid_data")
    conn.commit()
    conn.close()
    print("All data wiped from bssid_data table.")

if __name__ == "__main__":
    wipe_database()
