"""
fix_coordinates.py
==================
Corrects the lat/lng for all CSV-imported services in MongoDB.
The original CSV had completely wrong coordinates (e.g., Mumbai at lat=32, lng=85).
This script sets every service's lat/lng to the correct city-center ± small random variance.

Run once:  python fix_coordinates.py
"""

import asyncio
import random
from database.connection import connect_db, close_db, get_db

# Correct city centers for all cities present in the dataset
CITY_COORDS = {
    # Major CSV cities — all common spellings/aliases included
    "Mumbai":        (19.0760,  72.8777),
    "Delhi":         (28.6139,  77.2090),
    "New Delhi":     (28.6139,  77.2090),
    "Bangalore":     (12.9716,  77.5946),
    "Bengaluru":     (12.9716,  77.5946),   # alternate spelling
    "Chennai":       (13.0827,  80.2707),
    "Hyderabad":     (17.3850,  78.4867),
    "Pune":          (18.5204,  73.8567),
    "Kolkata":       (22.5726,  88.3639),
    "Calcutta":      (22.5726,  88.3639),
    "Jaipur":        (26.9124,  75.7873),
    "Ahmedabad":     (23.0225,  72.5714),
    "Surat":         (21.1702,  72.8311),
    "Lucknow":       (26.8467,  80.9462),
    "Kanpur":        (26.4499,  80.3319),
    "Nagpur":        (21.1458,  79.0882),
    "Indore":        (22.7196,  75.8577),
    "Bhopal":        (23.2599,  77.4126),
    "Patna":         (25.5941,  85.1376),
    "Agra":          (27.1767,  78.0081),
    "Vadodara":      (22.3072,  73.1812),
    "Baroda":        (22.3072,  73.1812),
    "Coimbatore":    (11.0168,  76.9558),
    "Kochi":         (9.9312,   76.2673),
    "Cochin":        (9.9312,   76.2673),
    "Visakhapatnam": (17.6868,  83.2185),
    "Vizag":         (17.6868,  83.2185),
    "Bhubaneswar":   (20.2961,  85.8245),
    "Guwahati":      (26.1445,  91.7362),
    "Chandigarh":    (30.7333,  76.7794),
    "Ludhiana":      (30.9010,  75.8573),
    "Amritsar":      (31.6340,  74.8723),
    "Rajkot":        (22.3039,  70.8022),
    "Meerut":        (28.9845,  77.7064),
    "Nashik":        (20.0059,  73.7898),
    "Nasik":         (20.0059,  73.7898),
    "Faridabad":     (28.4089,  77.3178),
    "Ghaziabad":     (28.6692,  77.4538),
    "Noida":         (28.5355,  77.3910),
    "Thane":         (19.2183,  72.9781),
    "Navi Mumbai":   (19.0330,  73.0297),
    "Gurugram":      (28.4595,  77.0266),   # was missing
    "Gurgaon":       (28.4595,  77.0266),
    "Aurangabad":    (19.8762,  75.3433),   # was missing
    "Dehradun":      (30.3165,  78.0322),   # was missing
    "Haridwar":      (29.9457,  78.1642),   # was missing
    "Gaya":          (24.7955,  84.9994),   # was missing
    "Bhagalpur":     (25.2425,  86.9842),   # was missing
    "Dhanbad":       (23.7957,  86.4304),   # was missing
    "Bokaro":        (23.6693,  86.1511),   # was missing
    "Bilaspur":      (22.0796,  82.1391),   # was missing
    "Bhilai":        (21.2090,  81.4285),   # was missing
    "Durg":          (21.1904,  81.2849),   # was missing
    "Cuttack":       (20.4625,  85.8830),   # was missing
    "Jagdalpur":     (19.0778,  82.0364),   # was missing
    "Raipur":        (21.2514,  81.6296),
    "Ranchi":        (23.3441,  85.3096),
    "Manali":        (32.2432,  77.1892),
    "Mapusa":        (15.5957,  73.8091),
    "Margao":        (15.2993,  73.9862),
    "Panaji":        (15.4909,  73.8278),
    "Muzaffarpur":   (26.1209,  85.3647),
    "Puri":          (19.8135,  85.8312),
    "Ratnagiri":     (16.9902,  73.3120),
    "Rishikesh":     (30.0869,  78.2676),
    "Rourkela":      (22.2604,  84.8536),
    "Sambalpur":     (21.4669,  83.9756),
    "Sangli":        (16.8524,  74.5815),
    "Satara":        (17.6805,  74.0183),
    "Una":           (31.4685,  76.2708),
    "Korba":         (22.3595,  82.7501),
    "Jalandhar":     (31.3260,  75.5762),
    "Jamshedpur":    (22.8046,  86.2029),
    "Kolhapur":      (16.7050,  74.2433),
    "Varanasi":      (25.3176,  82.9739),
    "Allahabad":     (25.4358,  81.8463),
    "Prayagraj":     (25.4358,  81.8463),
    "Jodhpur":       (26.2389,  73.0243),
    "Udaipur":       (24.5854,  73.7125),
    "Kota":          (25.2138,  75.8648),
    "Ajmer":         (26.4499,  74.6399),
    "Jammu":         (32.7266,  74.8570),
    "Srinagar":      (34.0837,  74.7973),
    "Shimla":        (31.1048,  77.1734),
    "Jalandhar":     (31.3260,  75.5762),
    "Tiruchirappalli":(10.7905, 78.7047),
    "Trichy":        (10.7905,  78.7047),
    "Madurai":       (9.9252,   78.1198),
    "Salem":         (11.6643,  78.1460),
    "Thiruvananthapuram": (8.5241, 76.9366),
    "Trivandrum":    (8.5241,   76.9366),
    "Kozhikode":     (11.2588,  75.7804),
    "Calicut":       (11.2588,  75.7804),
    "Thrissur":      (10.5276,  76.2144),
    "Vijayawada":    (16.5062,  80.6480),
    "Guntur":        (16.3067,  80.4365),
    "Warangal":      (17.9784,  79.5941),
    "Mangalore":     (12.9141,  74.8560),
    "Hubli":         (15.3647,  75.1240),
    "Mysore":        (12.2958,  76.6394),
    "Mysuru":        (12.2958,  76.6394),
    "Belgaum":       (15.8497,  74.4977),
    "Belagavi":      (15.8497,  74.4977),
    "Solapur":       (17.6805,  75.9064),
    "Kolhapur":      (16.7050,  74.2433),
    "Amravati":      (20.9374,  77.7796),
    "Nanded":        (19.1383,  77.3210),
    "Jamshedpur":    (22.8046,  86.2029),
    "Asansol":       (23.6834,  86.9820),
    "Siliguri":      (26.7271,  88.3953),
    "Durgapur":      (23.5204,  87.3119),
    "Tirunelveli":   (8.7139,   77.7567),
    "Vellore":       (12.9165,  79.1325),
    "Erode":         (11.3410,  77.7172),
    "Tiruppur":      (11.1085,  77.3411),
    "Gwalior":       (26.2183,  78.1828),
    "Jabalpur":      (23.1815,  79.9864),
    "Ujjain":        (23.1765,  75.7885),
    "Bhiwandi":      (19.2813,  73.0632),
    "Saharanpur":    (29.9680,  77.5552),
    "Gorakhpur":     (26.7606,  83.3732),
    "Bikaner":       (28.0229,  73.3119),
    "Aligarh":       (27.8974,  78.0880),
    "Bareilly":      (28.3670,  79.4304),
    "Moradabad":     (28.8389,  78.7769),
    "Mysore":        (12.2958,  76.6394),
}

# Small lat/lng variance to scatter providers within city (±0.05 degrees ≈ ±5.5 km)
VARIANCE = 0.05


async def fix():
    await connect_db()
    db = get_db()

    total_updated = 0
    not_found_cities = set()

    # Process city-by-city for efficiency
    cities = await db.services.distinct("city", {"is_csv_imported": True})
    print(f"Found {len(cities)} cities in CSV-imported services.")

    for city in cities:
        coords = CITY_COORDS.get(city)
        if not coords:
            not_found_cities.add(city)
            # Use a default India center for unknown cities
            coords = (20.5937, 78.9629)

        center_lat, center_lng = coords

        # Fetch all service IDs for this city
        cursor = db.services.find(
            {"city": city, "is_csv_imported": True},
            {"_id": 1}
        )
        docs = await cursor.to_list(length=None)

        if not docs:
            continue

        # Bulk-update each doc with a jittered coordinate
        ops = []
        from pymongo import UpdateOne
        for doc in docs:
            jitter_lat = center_lat + random.uniform(-VARIANCE, VARIANCE)
            jitter_lng = center_lng + random.uniform(-VARIANCE, VARIANCE)
            ops.append(UpdateOne(
                {"_id": doc["_id"]},
                {"$set": {"latitude": round(jitter_lat, 6), "longitude": round(jitter_lng, 6)}}
            ))

        if ops:
            result = await db.services.bulk_write(ops)
            total_updated += result.modified_count
            print(f"  [{city}] Updated {result.modified_count} services → center ({center_lat}, {center_lng})")

    print(f"\n✅ Done. Total updated: {total_updated}")
    if not_found_cities:
        print(f"⚠️  Cities not in CITY_COORDS (used India default): {sorted(not_found_cities)}")

    await close_db()


if __name__ == "__main__":
    asyncio.run(fix())
