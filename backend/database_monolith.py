from pydantic_settings import BaseSettings
from pydantic import BaseModel, EmailStr, Field, validator
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
import re, csv, os


# ── Source: config.py ──
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    APP_NAME: str = "QuickServe"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database
    MONGODB_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "quickserve"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Payment
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_PUBLISHABLE_KEY: Optional[str] = None
    UPI_ID: str = "quickserve@hdfc"
    
    # CORS — covers Vite's auto-port-increment (3000→3001→3002…) and HMR port
    CORS_ORIGINS: list = [
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:3001", "http://127.0.0.1:3001",
        "http://localhost:3002", "http://127.0.0.1:3002",
        "http://localhost:3003", "http://127.0.0.1:3003",
        "http://localhost:3004", "http://127.0.0.1:3004",
        "http://localhost:3005", "http://127.0.0.1:3005",
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:5174", "http://127.0.0.1:5174",
        "http://localhost:5175", "http://127.0.0.1:5175",
        "http://localhost:8080", "http://127.0.0.1:8080",
    ]
    
    class Config:
        env_file = ".env"

settings = Settings()

# ── Source: database/connection.py ──
from motor.motor_asyncio import AsyncIOMotorClient

client = None
db = None

async def connect_db():
    global client, db
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DATABASE_NAME]
    
    # helper for creating indexes to avoid stopping the whole process on conflict
    async def create_index(collection, *args, **kwargs):
        try:
            await collection.create_index(*args, **kwargs)
        except Exception as e:
            # Handle index conflict code 86 (IndexKeySpecsConflict) or other mismatches
            if "IndexKeySpecsConflict" in str(e) or "already exists with different options" in str(e):
                try:
                    # Try to find the name of the conflicting index and drop it
                    # Usually it is "field_1" for single field indexes
                    name = kwargs.get("name")
                    if not name and isinstance(args[0], str):
                        name = f"{args[0]}_1"
                    if name:
                        await collection.drop_index(name)
                        await collection.create_index(*args, **kwargs)
                        print(f"[OK] Re-created index with new options for {args[0]}")
                    else:
                        print(f"[WARN] Could not determine index name to drop for {args[0]}")
                except Exception as drop_error:
                    print(f"[ERROR] Failed to drop and recreate index: {drop_error}")
            elif "DuplicateKeyError" in str(e) or "E11000" in str(e):
                print(f"[ERROR] Cannot create unique index on {args[0]} because duplicate values exist: {e}")
            else:
                print(f"[WARN] Failed to create index for {args[0]}: {e}")

    # Create indexes for better performance on large datasets
    await create_index(db.users, "email", unique=True)
    await create_index(db.users, "role")
    await create_index(db.users, "city")
    
    await create_index(db.bookings, "status")
    await create_index(db.bookings, "customer_id")
    await create_index(db.bookings, "provider_id")
    await create_index(db.bookings, "created_at")
    
    await create_index(db.services, "category")
    await create_index(db.services, "city")
    await create_index(db.services, "is_csv_imported")
    
    print(f"[OK] Connected to MongoDB: {settings.DATABASE_NAME}")

async def close_db():
    global client
    if client:
        client.close()
        print("[DISCONNECTED] MongoDB connection closed")

def get_db():
    return db

# ── Source: database/csv_loader.py ──
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

# ── Source: models/schemas.py ──
from pydantic import BaseModel, EmailStr, Field, validator
import re
from typing import Optional, List
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    CUSTOMER = "customer"
    PROVIDER = "provider"
    ADMIN = "admin"

class BookingStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    name: Optional[str] = None
    phone: str
    role: UserRole = UserRole.CUSTOMER
    # Optional fields for enhanced profiles / providers
    age: Optional[int] = None
    gender: Optional[str] = None
    business_name: Optional[str] = None
    bio: Optional[str] = None
    experience_years: Optional[int] = None
    base_location: Optional[dict] = None  # {lat, lng}
    service_categories: Optional[List[str]] = None
    aptitude_score: Optional[int] = None
    hourly_rate: Optional[float] = None
    emergency_rate: Optional[float] = None

    @validator("password")
    def password_length(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters.")
        return v

    @validator("phone")
    def phone_format(cls, v):
        # Basic check for digits (at least 10)
        digits = re.sub(r'\D', '', v)
        if len(digits) < 10:
            raise ValueError("Phone number must contain at least 10 digits.")
        return v

    @validator("age")
    def min_age(cls, v):
        if v is not None and v < 18:
            raise ValueError("Must be 18 years or older.")
        if v is not None and v > 100:
            raise ValueError("Invalid age.")
        return v

    @property
    def display_name(self):
        return self.full_name or self.name or "User"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class ServiceCreate(BaseModel):
    name: str
    category: str
    description: str
    price: float
    duration: int
    location: dict

class BookingCreate(BaseModel):
    service_id: str
    provider_id: Optional[str] = None
    scheduled_time: Optional[str] = None
    scheduled_date: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    total_amount: Optional[float] = None
    location: Optional[dict] = None
    service_name: Optional[str] = None
    category: Optional[str] = None

class PaymentCreate(BaseModel):
    booking_id: str
    amount: float
    method: str = "stripe"

class ReviewCreate(BaseModel):
    booking_id: str
    provider_id: str
    rating: int = Field(ge=1, le=5)
    comment: str
    aspects: Optional[dict] = None

class SlotBookingCreate(BaseModel):
    provider_id: str
    service_id: str
    date: str
    time_slot: str
    notes: Optional[str] = None

class LoyaltyTransaction(BaseModel):
    user_id: str
    points: int
    type: str
    description: str

class ReferralCodeCreate(BaseModel):
    code: Optional[str] = None


class ProviderVerificationStatus(BaseModel):
    verified_phone: Optional[bool] = False
    verified_email: Optional[bool] = False
    verified_by_admin: Optional[bool] = False
    verified_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    quickserve_score: Optional[int] = None

class CheckInRequest(BaseModel):
    job_id: str
    latitude: float
    longitude: float

# --- Features Lab Schemas ---

class QueueJoin(BaseModel):
    service_type: str
    priority: str = "normal"

class SurgeCalculation(BaseModel):
    service_type: str
    location: Optional[dict] = {"lat": 12.97, "lng": 77.59}
    urgency: Optional[str] = "normal"

class MoodUpdate(BaseModel):
    mood: str
    energy_level: int
    availability_hours: int
    notes: Optional[str] = None

class AIProfileSetup(BaseModel):
    preferences: dict
    personality: str = "friendly"

class AIChatRequest(BaseModel):
    message: str
    context: Optional[dict] = None

class GamificationProgressUpdate(BaseModel):
    challenge_id: str
    progress: int

class PredictiveReminder(BaseModel):
    service_id: str
    date: str
    notes: Optional[str] = None

class CustomBundleCreate(BaseModel):
    services: List[str]
    bundle_name: str

class SwapOfferCreate(BaseModel):
    offering_service: str
    offering_hours: float
    seeking_service: str
    seeking_hours: float
    description: str
    location: dict

class EventCreate(BaseModel):
    event_type: str
    title: str
    description: str
    start_time: datetime
    category: str
    featured_providers: Optional[List[str]] = None
    entry_fee: Optional[float] = 0

class RouletteSpin(BaseModel):
    category: str
    bet_amount: Optional[float] = None

class QueueSkipRequest(BaseModel):
    payment_amount: float

class PriceDropNotificationRequest(BaseModel):
    service_type: str
    target_price: float

class MoodBasedPricingRequest(BaseModel):
    service_type: str
    provider_id: str
    base_price: float

class NeighborhoodBattleRequest(BaseModel):
    challenger_zip: str
    target_zip: str
    challenge_type: str

class BundleOptimizeRequest(BaseModel):
    services: List[str]
    max_budget: float
    timeframe_days: Optional[int] = 30

class EventBidRequest(BaseModel):
    service_id: str
    bid_amount: float

class EventShowcaseRequest(BaseModel):
    title: str
    description: str
    skills: List[str]

class EventRateRequest(BaseModel):
    rating: int
    feedback: str

class SwapRequestCreate(BaseModel):
    message: str
    proposed_schedule: dict

class SwapCompleteRequest(BaseModel):
    completion_proof: dict
    rating: int
    feedback: str

class ARPreviewGenerateRequest(BaseModel):
    space_id: str
    service_type: str
    preview_config: dict

class ARBookingRequest(BaseModel):
    preview_id: str
    provider_id: str
    scheduled_time: datetime
    notes: Optional[str] = None

class ARShareRequest(BaseModel):
    preview_id: str
    share_with: List[str]

class PredictiveScheduleRequest(BaseModel):
    services: List[str]
    max_budget: float
    preferred_days: List[str]
