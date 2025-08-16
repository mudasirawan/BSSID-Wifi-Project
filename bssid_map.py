import sqlite3
import folium

# === Connect to your SQLite database ===
db_path = "bssid_data.db"  # Change if in another folder
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# === Fetch all rows ===
cursor.execute("SELECT bssid, lat, lon FROM bssid_data")
rows = cursor.fetchall()

print(f"Total rows fetched: {len(rows)}")

# === Create map centered on Pakistan ===
m = folium.Map(location=[30.3753, 69.3451], zoom_start=5, tiles="OpenStreetMap")

# === Add all points as red dots ===
for bssid, lat, lon in rows:
    if lat is None or lon is None:
        continue  # skip invalid coords
    try:
        folium.CircleMarker(
            location=[lat, lon],
            radius=2,
            color='red',
            fill=True,
            fill_opacity=0.6,
            popup=f"BSSID: {bssid}"
        ).add_to(m)
    except Exception as e:
        print(f"Skipping row {bssid} due to error: {e}")

# === Save map to HTML file ===
output_file = "bssid_map_all.html"
m.save(output_file)
print(f"Map saved to {output_file}")

conn.close()




