import csv
import os
from pathlib import Path

CSV_PATH = Path(__file__).parent / "local_services_india.csv"


def _safe_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value.strip().lstrip("'") if value else default)
    except (ValueError, AttributeError):
        return default


def _safe_int(value: str, default: int = 0) -> int:
    try:
        return int(float(value.strip().lstrip("'") if value else default))
    except (ValueError, AttributeError):
        return default


def load_csv_providers() -> list[dict]:
    """Read local_services_india.csv and return a list of provider dicts."""
    if not CSV_PATH.exists():
        print(f"[WARN] CSV file not found: {CSV_PATH}")
        return []

    providers = []
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                raw_email = (row.get("email") or "").strip().lstrip("'")
                raw_phone = (row.get("phone") or "").strip().lstrip("'")
                specialties_raw = (row.get("specialties") or "").strip()
                specialty_list = [s.strip() for s in specialties_raw.split(",") if s.strip()]
                verified_flag = (row.get("verified") or "0").strip() == "1"

                provider = {
                    "csv_provider_id": (row.get("provider_id") or "").strip(),
                    "full_name": (row.get("name") or "").strip(),
                    "email": raw_email,
                    "phone": raw_phone,
                    "category": (row.get("category") or "").strip(),
                    "city": (row.get("city") or "").strip(),
                    "address": (row.get("address") or "").strip(),
                    "latitude": _safe_float(row.get("latitude", "")),
                    "longitude": _safe_float(row.get("longitude", "")),
                    "rating": _safe_float(row.get("rating", "")),
                    "reviews_count": _safe_int(row.get("reviews_count", "")),
                    "price_per_hour": _safe_float(row.get("price_per_hour", "")),
                    "availability": (row.get("availability") or "Available").strip(),
                    "specialties": specialty_list,
                    "experience_years": _safe_int(row.get("experience_years", "")),
                    "is_verified": verified_flag,
                    "profile_image": (row.get("profile_image") or "").strip(),
                    "description": (row.get("description") or "").strip(),
                }
                if provider["csv_provider_id"] and provider["full_name"]:
                    providers.append(provider)
            except Exception as e:
                # Skip malformed rows silently
                continue

    return providers


def providers_to_services(providers: list[dict]) -> list[dict]:
    """Convert CSV provider rows into service listing documents for MongoDB."""
    services = []
    for p in providers:
        category_lower = p["category"].lower()
        service = {
            "csv_provider_id": p["csv_provider_id"],
            "provider_name": p["full_name"],
            "name": f"{p['category']} by {p['full_name']}",
            "category": category_lower,
            "city": p["city"],
            "address": p["address"],
            "latitude": p["latitude"],
            "longitude": p["longitude"],
            "rating": p["rating"],
            "reviews_count": p["reviews_count"],
            "price_per_hour": p["price_per_hour"],
            "availability": p["availability"],
            "specialties": p["specialties"],
            "experience_years": p["experience_years"],
            "verified": p["is_verified"],
            "profile_image": p["profile_image"],
            "description": p["description"],
            "phone": p["phone"],
            "email": p["email"],
            "is_csv_imported": True,
        }
        services.append(service)
    return services
