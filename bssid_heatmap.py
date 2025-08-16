import sqlite3
import folium
from folium.plugins import HeatMap

# Connect to DB
conn = sqlite3.connect("bssid_data.db")
cursor = conn.cursor()

# Get all points
cursor.execute("SELECT lat, lon FROM bssid_data")
rows = cursor.fetchall()

# Filter out null/invalid coords
points = [(lat, lon) for lat, lon in rows if lat is not None and lon is not None]

print(f"Total points: {len(points)}")

# Center map on average location
avg_lat = sum(lat for lat, _ in points) / len(points)
avg_lon = sum(lon for _, lon in points) / len(points)
m = folium.Map(location=[avg_lat, avg_lon], zoom_start=5, tiles="OpenStreetMap")

# Add heatmap layer
HeatMap(points, radius=8, blur=15, min_opacity=0.4).add_to(m)

# Save map
m.save("bssid_heatmap.html")
print("Heatmap saved to bssid_heatmap.html")
