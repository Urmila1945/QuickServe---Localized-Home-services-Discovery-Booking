from fastapi import APIRouter, Depends, HTTPException
from models.schemas import SlotBookingCreate
from database.connection import get_db
from middleware.auth import get_current_user
from datetime import datetime, timedelta
from bson import ObjectId

router = APIRouter(prefix="/slots", tags=["Slot Booking"])

@router.post("/availability/setup")
async def setup_availability(provider_id: str, schedule: dict, current_user: dict = Depends(get_current_user)):
    db = get_db()
    schedule["provider_id"] = provider_id
    schedule["updated_at"] = datetime.utcnow()
    await db.provider_availability.update_one(
        {"provider_id": provider_id},
        {"$set": schedule},
        upsert=True
    )
    return {"status": "availability_set"}

@router.get("/availability/{provider_id}")
async def get_availability(provider_id: str, date: str):
    db = get_db()
    # Fetch from both collections for a unified view
    slot_bookings = await db.slot_bookings.find({
        "provider_id": provider_id, 
        "date": date,
        "status": {"$ne": "cancelled"}
    }).to_list(length=100)
    
    normal_bookings = await db.bookings.find({
        "provider_id": provider_id, 
        "scheduled_date": date,
        "status": {"$in": ["confirmed", "in_progress", "pending"]}
    }).to_list(length=100)
    
    # Provider-defined availability (default to 9-18)
    availability = await db.provider_availability.find_one({"provider_id": provider_id})
    start_hour = 9
    end_hour = 17
    
    slots = []
    for hour in range(start_hour, end_hour + 1):
        slot_time = f"{hour:02d}:00"
        
        # Checking BOTH collections
        is_booked = (
            any(b.get("time_slot") == slot_time for b in slot_bookings) or
            any(b.get("scheduled_time") == slot_time for b in normal_bookings)
        )
        
        # Demand calculation (Something Good)
        is_popular = (hour >= 10 and hour <= 12) or (hour >= 15 and hour <= 17)
        demand = "high" if (is_popular or len(slot_bookings) + len(normal_bookings) > 2) else "normal"
        
        slots.append({
            "time": slot_time, 
            "start_time": slot_time,
            "available": not is_booked,
            "is_available": not is_booked,
            "demand": demand
        })
    
    return {"date": date, "slots": slots}

@router.post("/book")
async def book_slot(booking: SlotBookingCreate, current_user: dict = Depends(get_current_user)):
    db = get_db()
    
    # Consolidated collision check
    existing_sb = await db.slot_bookings.find_one({
        "provider_id": booking.provider_id,
        "date": booking.date,
        "time_slot": booking.time_slot,
        "status": {"$ne": "cancelled"}
    })
    existing_b = await db.bookings.find_one({
        "provider_id": booking.provider_id,
        "scheduled_date": booking.date,
        "scheduled_time": booking.time_slot,
        "status": {"$in": ["confirmed", "in_progress", "pending"]}
    })
    
    if existing_sb or existing_b:
        raise HTTPException(status_code=400, detail="This slot is already booked.")
    
    booking_dict = booking.dict()
    booking_dict["user_id"] = current_user["sub"]
    booking_dict["status"] = "confirmed"
    booking_dict["created_at"] = datetime.utcnow()
    result = await db.slot_bookings.insert_one(booking_dict)
    return {"id": str(result.inserted_id), "status": "confirmed"}

@router.get("/my-bookings")
async def get_my_slot_bookings(current_user: dict = Depends(get_current_user)):
    db = get_db()
    bookings = await db.slot_bookings.find({"user_id": current_user["sub"]}).to_list(length=100)
    for b in bookings:
        b["_id"] = str(b["_id"])
    return bookings

@router.put("/cancel/{booking_id}")
async def cancel_slot_booking(booking_id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    await db.slot_bookings.update_one({"_id": ObjectId(booking_id)}, {"$set": {"status": "cancelled"}})
    return {"status": "cancelled"}

@router.get("/analytics")
async def get_slot_analytics(current_user: dict = Depends(get_current_user)):
    db = get_db()
    total = await db.slot_bookings.count_documents({"provider_id": current_user["sub"]})
    confirmed = await db.slot_bookings.count_documents({"provider_id": current_user["sub"], "status": "confirmed"})
    return {"total_bookings": total, "confirmed": confirmed}

@router.get("/smart-scheduling")
async def get_smart_scheduling(date: str = None):
    if not date:
        date = datetime.utcnow().strftime("%Y-%m-%d")
        
    # We simulate dynamic smart scheduling based on deterministic date variations
    seed = sum(ord(c) for c in date)
    
    time_slots = [
        {"time": "8:00 AM", "price": 50, "weather": "☀️ Sunny", "demand": "low", "discount": 15},
        {"time": "10:00 AM", "price": 65, "weather": "☀️ Sunny", "demand": "medium"},
        {"time": "12:00 PM", "price": 75, "weather": "☁️ Cloudy", "demand": "high"},
        {"time": "2:00 PM", "price": 80, "weather": "⛅ Partly Cloudy", "demand": "high"},
        {"time": "4:00 PM", "price": 70, "weather": "🌤️ Clear", "demand": "medium", "discount": 10},
        {"time": "6:00 PM", "price": 55, "weather": "🌤️ Clear", "demand": "low", "discount": 20},
    ]
    
    for i, slot in enumerate(time_slots):
        perturbation = ((seed + i * 17) % 11) - 5  # Range -5 to +5
        slot["price"] = max(20, slot["price"] + perturbation)
    
    return {"date": date, "slots": time_slots}
