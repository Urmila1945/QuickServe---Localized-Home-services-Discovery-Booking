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
