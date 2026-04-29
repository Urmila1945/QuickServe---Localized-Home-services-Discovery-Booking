from fastapi import APIRouter, Depends, HTTPException
from models.schemas import BookingCreate, BookingStatus
from database.connection import get_db
from middleware.auth import get_current_user
from datetime import datetime
from bson import ObjectId

router = APIRouter(prefix="/bookings", tags=["Bookings"])

@router.post("/")
async def create_booking(booking: BookingCreate, current_user: dict = Depends(get_current_user)):
    db = get_db()
    
    # 1. Check for existing booking (consolidated check)
    if booking.provider_id and booking.scheduled_time and booking.scheduled_date:
        # Check main bookings
        existing = await db.bookings.find_one({
            "provider_id": booking.provider_id,
            "scheduled_time": booking.scheduled_time,
            "scheduled_date": booking.scheduled_date,
            "status": {"$in": ["confirmed", "in_progress", "pending"]}
        })
        # Check slot_bookings too
        existing_slot = await db.slot_bookings.find_one({
            "provider_id": booking.provider_id,
            "time_slot": booking.scheduled_time,
            "date": booking.scheduled_date,
            "status": {"$not": {"$eq": "cancelled"}}
        })
        if existing or existing_slot:
            raise HTTPException(status_code=400, detail="Provider is unavailable for this specific date and time slot.")
    
    # 2. Get provider's base rate
    base_rate = 500
    if booking.provider_id:
        try:
            # Try as ObjectId first
            p_oid = ObjectId(booking.provider_id)
            provider = await db.users.find_one({"_id": p_oid})
        except:
            # Fallback for CSV or other string-based IDs
            provider = await db.users.find_one({"_id": booking.provider_id})
            
        if provider:
            base_rate = provider.get("hourly_rate") or provider.get("provider_profile", {}).get("base_rate") or 500
    
    now = datetime.utcnow()
    
    # 3. Parse scheduled time for price multipliers
    try:
        if booking.scheduled_time and booking.scheduled_date:
            sched_str = f"{booking.scheduled_date} {booking.scheduled_time}"
            if "T" in booking.scheduled_time or "Z" in booking.scheduled_time.upper():
                sched = datetime.fromisoformat(booking.scheduled_time.replace('Z', '+00:00'))
            else:
                sched = datetime.strptime(sched_str, "%Y-%m-%d %H:%M")
        else:
            sched = now
    except:
        sched = now

    # 4. Apply Multipliers (Rush, Weekend, Evening)
    hour = sched.hour
    multiplier = 1.0
    if 17 <= hour <= 21: multiplier *= 1.2 # Evening demand
    if sched.weekday() >= 5: multiplier *= 1.1 # Weekend
    if (sched - now).total_seconds() < 7200: multiplier *= 1.5 # Short notice (within 2h)
    
    # 4.5 Apply Repeat Customer Discount (10%)
    booking_dict = booking.dict()
    service_id = booking_dict.get("service_id")
    if service_id:
        past_booking = await db.bookings.find_one({
            "user_id": current_user["sub"],
            "service_id": service_id
        })
        if past_booking:
            multiplier *= 0.90  # 10% discount
            booking_dict["is_repeat_customer"] = True
            booking_dict["discount_applied"] = "10%"

    final_price = base_rate * multiplier
    
    # 5. Create Booking Document
    booking_dict["user_id"] = current_user["sub"]
    booking_dict["status"] = BookingStatus.CONFIRMED
    booking_dict["created_at"] = datetime.utcnow()
    booking_dict["final_price"] = round(final_price, 2)
    booking_dict["multiplier"] = multiplier
    
    result = await db.bookings.insert_one(booking_dict)
    return {"id": str(result.inserted_id), "_id": str(result.inserted_id), "status": "confirmed", "price": round(final_price, 2)}

@router.post("/emergency")
async def create_emergency_booking(booking: BookingCreate, current_user: dict = Depends(get_current_user)):
    db = get_db()
    booking_dict = booking.dict()
    booking_dict["user_id"] = current_user["sub"]
    booking_dict["status"] = BookingStatus.PENDING
    booking_dict["is_emergency"] = True
    booking_dict["created_at"] = datetime.utcnow()
    result = await db.bookings.insert_one(booking_dict)
    return {"id": str(result.inserted_id), "status": "emergency", "priority": "high"}

# NOTE: /history must be before /{booking_id} to avoid route conflict
@router.get("/history")
async def get_booking_history(current_user: dict = Depends(get_current_user)):
    db = get_db()
    bookings = await db.bookings.find({"user_id": current_user["sub"]}).sort("created_at", -1).to_list(length=50)
    for b in bookings:
        b["_id"] = str(b["_id"])
        b["id"] = b["_id"]
    return bookings

@router.get("/check-discount/{service_id}")
async def check_discount(service_id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    past_booking = await db.bookings.find_one({
        "user_id": current_user["sub"],
        "service_id": service_id
    })
    return {
        "is_repeat": bool(past_booking),
        "discount_pct": 10 if past_booking else 0
    }


@router.get("/")
async def get_bookings(current_user: dict = Depends(get_current_user)):
    db = get_db()
    # Support both "id" and "total" format used by frontend
    bookings = await db.bookings.find({"user_id": current_user["sub"]}).sort("created_at", -1).to_list(length=100)
    for b in bookings:
        b["_id"] = str(b["_id"])
        b["id"] = b["_id"]
    return {"bookings": bookings, "total": len(bookings)}

@router.get("/{booking_id}")
async def get_booking(booking_id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    try:
        # Try both formats for ID
        query = {"_id": ObjectId(booking_id)} if len(booking_id) == 24 else {"_id": booking_id}
        booking = await db.bookings.find_one(query)
    except:
        raise HTTPException(status_code=400, detail="Invalid booking ID format")
        
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    booking["_id"] = str(booking["_id"])
    booking["id"] = booking["_id"]
    return booking

@router.put("/{booking_id}/status")
async def update_booking_status(booking_id: str, status: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    await db.bookings.update_one({"_id": ObjectId(booking_id)}, {"$set": {"status": status}})
    return {"status": "updated"}

@router.delete("/{booking_id}")
async def cancel_booking(booking_id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    await db.bookings.update_one({"_id": ObjectId(booking_id)}, {"$set": {"status": "cancelled"}})
    return {"status": "cancelled"}
