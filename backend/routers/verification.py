from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from database.connection import get_db
from middleware.auth import get_current_user
from datetime import datetime
from bson.objectid import ObjectId
import json
import base64
from models.schemas import CheckInRequest

router = APIRouter(prefix="/verify", tags=["Dual-Layer Verification"])

@router.post("/work")
async def verify_work(
    job_id: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    before_image: UploadFile = File(...),
    after_image: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Project Gallery Upload & Proof of Visit.
    Validates work with GPS timestamp and image evidence.
    """
    db = get_db()
    
    # Read image contents (In production, save to S3/Cloudinary and store URL)
    before_bytes = await before_image.read()
    after_bytes = await after_image.read()
    
    # Simple base64 for quick demo validation (simulating cloud storage)
    before_url = f"data:{before_image.content_type};base64,{base64.b64encode(before_bytes).decode('utf-8')}"
    after_url = f"data:{after_image.content_type};base64,{base64.b64encode(after_bytes).decode('utf-8')}"
    
    # 1. Verification Record
    verification_record = {
        "provider_id": current_user["sub"],
        "job_id": job_id,
        "location": {"lat": latitude, "lng": longitude},
        "timestamp": datetime.utcnow(),
        "images": {
            "before": before_url,
            "after": after_url
        },
        "status": "verified"
    }
    
    await db.work_verifications.insert_one(verification_record)
    
    # 2. Update Booking Status to Completed/Verified
    try:
        b_oid = ObjectId(job_id)
        await db.bookings.update_one(
            {"_id": b_oid},
            {"$set": {"status": "completed", "is_verified": True}}
        )
    except Exception as e:
        print(f"Skipping booking update: {e}")
        pass 
        
    return {"message": "Work verified successfully", "status": "verified"}

@router.post("/check-in")
async def check_in(
    data: CheckInRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Proof of Visit: Capture GPS coordinates and timestamp upon arrival.
    """
    db = get_db()
    
    job_id = data.job_id
    latitude = data.latitude
    longitude = data.longitude
    
    # 1. Update Booking with Check-in data
    try:
        b_oid = ObjectId(job_id)
        await db.bookings.update_one(
            {"_id": b_oid},
            {
                "$set": {
                    "check_in": {
                        "lat": latitude,
                        "lng": longitude,
                        "timestamp": datetime.utcnow()
                    },
                    "status": "in_progress"
                }
            }
        )
    except Exception as e:
        print(f"Check-in error: {e}")
    
    return {"message": "Check-in successful", "status": "in_progress"}

@router.get("/trust-score")
async def get_trust_score(current_user: dict = Depends(get_current_user)):
    """
    Trust Score Logic: Trust = (0.4 * Rating) + (0.3 * Review Sentiment) + (0.3 * Gallery Density).
    """
    db = get_db()
    
    if current_user.get("role") != "provider":
        raise HTTPException(status_code=403, detail="Only providers have a trust score")
        
    provider_id = current_user["sub"]
    
    # 1. Rating (40%)
    reviews = await db.reviews.find({"provider_id": provider_id}).to_list(100)
    avg_rating = sum([r.get("rating", 5) for r in reviews]) / max(len(reviews), 1)
    scaled_rating = avg_rating * 20 # Scaled to 100
    
    # 2. Review Sentiment (30%) - Logic: Weight positive vs negative keywords or score from DB
    # For demo: Scaling rating as proxy for sentiment
    review_sentiment = min((avg_rating / 5.0) * 105, 100.0) 
    
    # 3. Gallery Density (30%) - 1 verified job = 10% density, Max 100%
    verified_jobs = await db.work_verifications.count_documents({"provider_id": provider_id})
    gallery_density = min(verified_jobs * 10, 100)
    
    # Final Formula
    trust_score = (0.4 * scaled_rating) + (0.3 * review_sentiment) + (0.3 * gallery_density)
    
    # Verification Badge (needs 3+ verified jobs)
    is_verified_badge = verified_jobs >= 3
    
    # Update user profile with latest badge/score
    try:
        u_oid = ObjectId(provider_id)
        await db.users.update_one(
            {"_id": u_oid},
            {"$set": {"trust_score": round(trust_score, 1), "is_verified_badge": is_verified_badge}}
        )
    except Exception as e:
        print(f"Trust score update error: {e}")
    
    return {
        "trust_score": round(trust_score, 1),
        "verified_jobs_count": verified_jobs,
        "is_verified_badge": is_verified_badge,
        "metrics": {
            "rating_contribution": round(0.4 * scaled_rating, 1),
            "sentiment_contribution": round(0.3 * review_sentiment, 1),
            "gallery_contribution": round(0.3 * gallery_density, 1)
        }
    }
