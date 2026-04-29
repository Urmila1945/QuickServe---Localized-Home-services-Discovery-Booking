from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from bson import ObjectId
from database.connection import get_db
from middleware.auth import get_current_user
from models.schemas import BookingCreate, ReviewCreate, ServiceCreate
import random
import uuid

router = APIRouter(tags=["Marketplace & Operations"])

# --- SERVICES SECTION ---

@router.get("/services/search")
async def search_services(q: Optional[str] = None, category: Optional[str] = None, city: Optional[str] = None, latitude: Optional[float] = None, longitude: Optional[float] = None, radius: float = Query(10.0), min_rating: float = Query(0.0), min_price: Optional[float] = None, max_price: Optional[float] = None, emergency: Optional[bool] = None, limit: int = Query(20, le=100)):
    db = get_db()
    query = {}
    if category: query["category"] = {"$regex": category, "$options": "i"}
    if city: query["city"] = {"$regex": city, "$options": "i"}
    if q: query["$or"] = [{"name": {"$regex": q, "$options": "i"}}, {"description": {"$regex": q, "$options": "i"}}, {"specialties": {"$regex": q, "$options": "i"}}]
    if emergency is not None: query["is_emergency"] = emergency
    query["rating"] = {"$gte": min_rating}
    if min_price is not None or max_price is not None:
        price_query = {}
        if min_price is not None: price_query["$gte"] = min_price
        if max_price is not None: price_query["$lte"] = max_price
        query["price_per_hour"] = price_query
    services = await db.services.find(query).limit(limit * 5).to_list(length=limit * 5)
    for s in services:
        s["_id"] = str(s["_id"])
        s["provider_id"] = str(s.get("provider_id", ""))
    services.sort(key=lambda x: x.get("rating", 0), reverse=True)
    return {"services": services[:limit], "total": len(services)}

@router.get("/services/categories")
async def get_categories():
    db = get_db()
    categories = await db.services.distinct("category")
    return [{"name": c, "id": c.lower().replace(" ", "_")} for c in categories]

@router.get("/services/{service_id}")
async def get_service(service_id: str):
    db = get_db()
    service = await db.services.find_one({"_id": ObjectId(service_id)})
    if service:
        service["_id"] = str(service["_id"])
        service["provider_id"] = str(service.get("provider_id", ""))
    return service

# --- BOOKINGS SECTION ---

@router.post("/bookings")
async def create_booking(booking: BookingCreate, current_user: dict = Depends(get_current_user)):
    db = get_db()
    booking_dict = booking.dict()
    booking_dict["customer_id"] = current_user["sub"]
    booking_dict["status"] = "pending"
    booking_dict["created_at"] = datetime.utcnow()
    result = await db.bookings.insert_one(booking_dict)
    return {"_id": str(result.inserted_id), **booking_dict}

@router.get("/bookings")
async def get_my_bookings(current_user: dict = Depends(get_current_user)):
    db = get_db()
    query = {"customer_id": current_user["sub"]} if current_user["role"] == "customer" else {"provider_id": current_user["sub"]}
    bookings = await db.bookings.find(query).to_list(length=100)
    for b in bookings:
        b["_id"] = str(b["_id"])
        b["service_id"] = str(b.get("service_id", ""))
    return bookings

# --- SLOTS SECTION ---

@router.get("/slots/available")
async def get_available_slots(provider_id: str, date: str):
    db = get_db()
    slots = await db.slots.find({"provider_id": provider_id, "date": date, "is_available": True}).to_list(length=100)
    for s in slots: s["_id"] = str(s["_id"])
    return slots

# --- PAYMENTS SECTION ---

@router.post("/payments/create-intent")
async def create_payment_intent(booking_id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    booking = await db.bookings.find_one({"_id": ObjectId(booking_id)})
    if not booking: raise HTTPException(status_code=404, detail="Booking not found")
    intent_id = str(uuid.uuid4())
    await db.payments.insert_one({"booking_id": booking_id, "amount": booking.get("amount", 0), "status": "pending", "intent_id": intent_id, "created_at": datetime.utcnow()})
    return {"intent_id": intent_id, "client_secret": "sk_test_" + intent_id}

@router.post("/payments/confirm")
async def confirm_payment(intent_id: str):
    db = get_db()
    await db.payments.update_one({"intent_id": intent_id}, {"$set": {"status": "completed", "completed_at": datetime.utcnow()}})
    payment = await db.payments.find_one({"intent_id": intent_id})
    if payment:
        await db.bookings.update_one({"_id": ObjectId(payment["booking_id"])}, {"$set": {"status": "confirmed"}})
    return {"status": "success"}

# --- REVIEWS SECTION ---

@router.post("/reviews")
async def create_review(review: ReviewCreate, current_user: dict = Depends(get_current_user)):
    db = get_db()
    review_dict = review.dict()
    review_dict["customer_id"] = current_user["sub"]
    review_dict["created_at"] = datetime.utcnow()
    result = await db.reviews.insert_one(review_dict)
    # Update provider overall rating
    reviews = await db.reviews.find({"provider_id": review.provider_id}).to_list(length=1000)
    avg = sum([r["rating"] for r in reviews]) / len(reviews)
    await db.users.update_one({"_id": ObjectId(review.provider_id)}, {"$set": {"rating": round(avg, 1), "reviews_count": len(reviews)}})
    return {"_id": str(result.inserted_id), **review_dict}

# --- TRACKING & HAIL ---

@router.post("/services/voice-hail")
async def process_voice_hail(payload: dict):
    text = payload.get("text", "").lower()
    service_type = "general"
    urgency = "normal"
    if any(word in text for word in ["urgent", "emergency", "now", "quick", "fast", "immediately"]):
        urgency = "high"
    if any(word in text for word in ["plumb", "leak", "water", "pipe", "drain"]): service_type = "plumber"
    elif any(word in text for word in ["electri", "power", "shock", "wire", "light"]): service_type = "electrician"
    elif any(word in text for word in ["clean", "maid", "sweep", "dust"]): service_type = "house cleaning"
    return {"service": service_type, "urgency": urgency}
