from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from database.connection import get_db
from middleware.auth import get_current_user
from bson import ObjectId
from datetime import datetime, timedelta
import os
import shutil
import random
import string
from twilio.rest import Client as TwilioClient
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

router = APIRouter(prefix="/providers", tags=["Providers"])

@router.get("/")
async def get_providers(limit: int = 20):
    db = get_db()
    providers = await db.users.find({"role": "provider"}).limit(limit).to_list(length=limit)
    for p in providers:
        p["_id"] = str(p["_id"])
        p.pop("password", None)
    return providers

@router.get("/{provider_id}")
async def get_provider(provider_id: str):
    db = get_db()
    try:
        try:
            query = {"_id": ObjectId(provider_id)} if len(provider_id) == 24 else {"_id": provider_id}
        except Exception:
            query = {"_id": provider_id}
            
        query["role"] = "provider"
        provider = await db.users.find_one(query)
        
        if not provider:
            provider = await db.users.find_one({"csv_provider_id": provider_id, "role": "provider"})
            
        if provider:
            provider["_id"] = str(provider["_id"])
            provider.pop("password", None)
        return provider
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        raise HTTPException(status_code=500, detail=error_msg)

@router.post("/onboard")
async def onboard_provider(data: dict, current_user: dict = Depends(get_current_user)):
    db = get_db()
    
    # Calculate QuickServe Score
    score = 85 # Default base score
    if data.get("documents"): score += 5
    if data.get("portfolio"): score += 5
    if data.get("ai_bot_settings"): score += 5
    
    update_data = {
        "onboarded": True,
        "base_location": data.get("location"),
        "service_area": {
            "type": data.get("service_area_type"),
            "radius": data.get("radius"),
            "polygon": data.get("polygon_points")
        },
        "specializations": data.get("categories"),
        "hourly_rate": data.get("hourly_rate"),
        "emergency_rate": data.get("emergency_rate"),
        "ai_bot_settings": data.get("ai_bot_settings"),
        "quickserve_score": score,
        "launch_plan_generated": True,
        "updated_at": datetime.utcnow()
    }
    
    await db.users.update_one(
        {"_id": ObjectId(current_user["sub"])},
        {"$set": update_data}
    )
    
    return {"status": "success", "score": score}

@router.get("/search")
async def search_providers(lat: float, lng: float, category: str = None):
    db = get_db()
    
    # 1. Find providers nearby using base_location (radius search)
    # This is a broad filter
    query = {
        "role": "provider",
        "onboarded": True,
    }
    if category:
        query["specializations"] = category
        
    providers = await db.users.find(query).to_list(length=100)
    
    matched_providers = []
    user_point = [lng, lat]
    
    for p in providers:
        service_area = p.get("service_area", {})
        area_type = service_area.get("type", "radius")
        
        is_match = False
        
        if area_type == "radius":
            # Haversine formula for distance
            from math import radians, cos, sin, asin, sqrt
            def haversine(lon1, lat1, lon2, lat2):
                lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
                dlon = lon2 - lon1 
                dlat = lat2 - lat1 
                a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                c = 2 * asin(sqrt(a)) 
                r = 3956 # Miles
                return c * r
            
            base_loc = p.get("base_location", {"lat": 0, "lng": 0})
            dist = haversine(lng, lat, base_loc["lng"], base_loc["lat"])
            if dist <= service_area.get("radius", 5):
                is_match = True
                p["distance"] = round(dist, 2)
        
        elif area_type == "polygon":
            # Point-in-polygon algorithm
            polygon = service_area.get("polygon", [])
            if polygon:
                n = len(polygon)
                inside = False
                p1x, p1y = polygon[0][1], polygon[0][0] # lng, lat
                for i in range(n + 1):
                    p2x, p2y = polygon[i % n][1], polygon[i % n][0]
                    if lat > min(p1y, p2y):
                        if lat <= max(p1y, p2y):
                            if lng <= max(p1x, p2x):
                                if p1y != p2y:
                                    xints = (lat - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                                if p1x == p2x or lng <= xints:
                                    inside = not inside
                    p1x, p1y = p2x, p2y
                if inside:
                    is_match = True
                    p["distance"] = 0 # Inside polygon
        
        if is_match:
            p["_id"] = str(p["_id"])
            p.pop("password", None)
            matched_providers.append(p)
            
    # Sort by distance or rating
    matched_providers.sort(key=lambda x: x.get("distance", 0))
    
    return matched_providers

@router.get("/earnings")
async def get_earnings(current_user: dict = Depends(get_current_user)):
    db = get_db()
    payments = await db.payments.find({"provider_id": current_user["sub"], "status": "completed"}).to_list(length=1000)
    total = sum(p.get("amount", 0) for p in payments)
    return {"total_earnings": total, "payment_count": len(payments)}

@router.put("/availability")
async def update_availability(availability: dict, current_user: dict = Depends(get_current_user)):
    db = get_db()
    await db.provider_availability.update_one(
        {"provider_id": current_user["sub"]},
        {"$set": availability},
        upsert=True
    )
    return {"status": "updated"}


@router.post("/verify/upload-docs")
async def upload_provider_docs(files: list[UploadFile] = File(...), current_user: dict = Depends(get_current_user)):
    db = get_db()
    provider_id = current_user["sub"]
    base_dir = os.path.join(os.path.dirname(__file__), "..", "uploads", "providers", provider_id)
    os.makedirs(base_dir, exist_ok=True)

    saved = []
    for f in files:
        dest_path = os.path.join(base_dir, f.filename)
        with open(dest_path, "wb") as out:
            shutil.copyfileobj(f.file, out)

        doc = {
            "provider_id": provider_id,
            "filename": f.filename,
            "path": dest_path,
            "status": "pending",
            "uploaded_at": datetime.utcnow()
        }
        await db.provider_documents.insert_one(doc)
        saved.append({"filename": f.filename, "status": "pending"})

    # bump quickserve score slightly for providing docs
    await db.users.update_one({"_id": ObjectId(provider_id)}, {"$inc": {"quickserve_score": 3}})

    return {"status": "ok", "uploaded": saved}


def _gen_code(length: int = 6):
    return "".join(random.choices(string.digits, k=length))


@router.post("/verify/request-otp")
async def request_phone_otp(current_user: dict = Depends(get_current_user)):
    db = get_db()
    provider_id = current_user["sub"]
    code = _gen_code(6)
    record = {
        "provider_id": provider_id,
        "type": "phone",
        "code": code,
        "verified": False,
        "expires_at": datetime.utcnow() + timedelta(minutes=10),
        "created_at": datetime.utcnow()
    }
    await db.provider_verifications.insert_one(record)
    # Send SMS via Twilio (requires env vars TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM)
    try:
        tw_sid = os.getenv("TWILIO_ACCOUNT_SID")
        tw_token = os.getenv("TWILIO_AUTH_TOKEN")
        tw_from = os.getenv("TWILIO_FROM")
        to_number = current_user.get("phone")
        if tw_sid and tw_token and tw_from and to_number:
            client = TwilioClient(tw_sid, tw_token)
            client.messages.create(body=f"Your QuickServe verification code: {code}", from_=tw_from, to=to_number)
            return {"status": "otp_sent"}
        else:
            # For local/testing when env not set, return OTP so tests can continue
            return {"status": "otp_sent", "otp": code}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.post("/verify/check-otp")
async def check_phone_otp(payload: dict, current_user: dict = Depends(get_current_user)):
    code = payload.get("code")
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="code required")

    db = get_db()
    provider_id = current_user["sub"]
    rec = await db.provider_verifications.find_one({"provider_id": provider_id, "type": "phone", "code": code})
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="otp not found")
    if rec.get("expires_at") and rec["expires_at"] < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="otp expired")

    await db.provider_verifications.update_one({"_id": rec["_id"]}, {"$set": {"verified": True, "verified_at": datetime.utcnow()}})
    await db.users.update_one({"_id": ObjectId(provider_id)}, {"$set": {"verified_phone": True}})
    return {"status": "verified"}


@router.post("/verify/request-email")
async def request_email_verification(current_user: dict = Depends(get_current_user)):
    db = get_db()
    provider_id = current_user["sub"]
    token = _gen_code(24)
    rec = {"provider_id": provider_id, "type": "email", "token": token, "verified": False, "expires_at": datetime.utcnow() + timedelta(hours=2), "created_at": datetime.utcnow()}
    await db.provider_verifications.insert_one(rec)
    # Send verification email via SendGrid (requires SENDGRID_API_KEY and SENDGRID_FROM_EMAIL)
    try:
        sg_key = os.getenv("SENDGRID_API_KEY")
        from_email = os.getenv("SENDGRID_FROM_EMAIL") or "noreply@quickserve.local"
        base = os.getenv("BASE_URL") or "http://localhost:8000"
        verify_link = f"{base}/providers/verify/email-callback?token={token}"
        if sg_key:
            message = Mail(
                from_email=from_email,
                to_emails=current_user.get("email"),
                subject="QuickServe Email Verification",
                html_content=f"<p>Please verify your email by clicking <a href=\"{verify_link}\">here</a>.</p>"
            )
            sg = SendGridAPIClient(sg_key)
            sg.send(message)
            return {"status": "email_sent"}
        else:
            # fallback for local/testing
            return {"status": "email_sent", "token": token, "verify_link": verify_link}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.get("/verify/email-callback")
async def email_callback(token: str):
    db = get_db()
    rec = await db.provider_verifications.find_one({"type": "email", "token": token})
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="token not found")
    if rec.get("expires_at") and rec["expires_at"] < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="token expired")
    await db.provider_verifications.update_one({"_id": rec["_id"]}, {"$set": {"verified": True, "verified_at": datetime.utcnow()}})
    await db.users.update_one({"_id": ObjectId(rec["provider_id"])}, {"$set": {"verified_email": True}})
    return {"status": "verified"}


@router.get("/verify/status")
async def verification_status(current_user: dict = Depends(get_current_user)):
    db = get_db()
    provider_id = current_user["sub"]
    docs = await db.provider_documents.find({"provider_id": provider_id}).to_list(length=50)
    ver = await db.provider_verifications.find({"provider_id": provider_id}).to_list(length=50)
    user = await db.users.find_one({"_id": ObjectId(provider_id)})
    return {"documents": docs, "verifications": ver, "user": {"verified_phone": user.get("verified_phone"), "verified_email": user.get("verified_email"), "verified_by_admin": user.get("verified_by_admin")}}


# Admin endpoints
@router.get("/admin/verifications")
async def list_pending_verifications(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin only")
    db = get_db()
    pending_docs = await db.provider_documents.find({"status": "pending"}).to_list(length=200)
    pending_ver = await db.provider_verifications.find({"verified": False}).to_list(length=200)
    return {"pending_docs": pending_docs, "pending_verifications": pending_ver}


@router.put("/admin/verifications/{provider_id}/approve")
async def approve_provider(provider_id: str, current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin only")
    db = get_db()
    await db.users.update_one({"_id": ObjectId(provider_id)}, {"$set": {"verified_by_admin": True, "verified_at": datetime.utcnow()}})
    await db.provider_documents.update_many({"provider_id": provider_id}, {"$set": {"status": "approved"}})
    await db.provider_verifications.update_many({"provider_id": provider_id}, {"$set": {"verified": True}})
    return {"status": "approved"}


@router.put("/admin/verifications/{provider_id}/reject")
async def reject_provider(provider_id: str, reason: dict, current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin only")
    db = get_db()
    await db.users.update_one({"_id": ObjectId(provider_id)}, {"$set": {"verified_by_admin": False, "rejection_reason": reason.get("reason"), "verified_at": datetime.utcnow()}})
    await db.provider_documents.update_many({"provider_id": provider_id}, {"$set": {"status": "rejected"}})
    return {"status": "rejected"}
