import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.india_spatial_service import IndiaSpatialService

cities = [
    ("Patna", 25.5941, 85.1376),
    ("Guwahati", 26.1445, 91.7362),
    ("Mumbai", 19.0760, 72.8777),
    ("Vijayawada", 16.5062, 80.6480),
    ("Nagpur", 21.1458, 79.0882),
    ("Ahmedabad", 23.0225, 72.5714),
]

print("==================================================")
print("VERIFYING TERRAIN & BASIN COVERAGE FOR ALL 6 TARGET CITIES")
print("==================================================")

for name, lat, lon in cities:
    b = IndiaSpatialService.get_river_basin(lat, lon)
    t = IndiaSpatialService.get_terrain_features(lat, lon)
    admin = IndiaSpatialService.get_administrative_entity(lat, lon)
    b_id = b["basin_id"] if b else "NONE"
    b_name = b["basin_name"] if b else "NONE"
    st = admin["state_name"] if admin else "NONE"
    dist = admin["district_name"] if admin else "NONE"

    print(f"\nCity: {name} ({lat:.4f}°N, {lon:.4f}°E)")
    print(f"  Admin: State={st}, District={dist}")
    print(f"  Basin: {b_id} ({b_name})")
    if t:
        print(f"  Terrain: Domain={t['domain_id']}")
        print(f"    Elevation: {t['elevation_m']} m")
        print(f"    Slope: {t['slope_deg']}°")
        print(f"    Distance to River: {t['distance_to_river_m']} m")
        print(f"    Landcover: Class {t['landcover_class']}")
        print(f"    Built-up Fraction: {t['built_up_fraction']}")
    else:
        print("  Terrain: FAILED (None)")
print("\n==================================================")

