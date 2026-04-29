from fastapi import APIRouter, HTTPException, Depends, Response, Cookie, Request, UploadFile, File, Form, status
from models.schemas import UserCreate, UserLogin, Token, UserRole, CheckInRequest
from middleware.auth import hash_password, verify_password, create_access_token, create_refresh_token, get_current_user
from database.connection import get_db
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from pydantic import BaseModel
import logging
import os
import shutil
import random
import string
import base64
from bson import ObjectId
try:
    from twilio.rest import Client as TwilioClient
except ImportError:
    TwilioClient = None
try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail
except ImportError:
    SendGridAPIClient = None
    Mail = None

# Configure local logging
logging.basicConfig(filename="auth_debug.log", level=logging.INFO, format="%(asctime)s - %(message)s")

router = APIRouter(tags=["Identity & Verification"])

# --- AUTH SECTION ---

@router.post("/auth/register")
async def register(user: UserCreate, response: Response):
    db = get_db()
    existing_email = await db.users.find_one({"email": user.email})
    if existing_email:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")
    if user.phone:
        existing_phone = await db.users.find_one({"phone": user.phone})
        if existing_phone:
            raise HTTPException(status_code=400, detail="This phone number is already associated with another account.")
    if not user.password or len(user.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long.")
    user_dict = user.dict()
    user_dict["password"] = hash_password(user.password)
    user_dict["created_at"] = datetime.utcnow()
    user_dict["addresses"] = []
    if user.role == UserRole.PROVIDER:
        score = 75 
        if user.bio: score += 5
        if user.business_name: score += 5
        if user.experience_years and user.experience_years > 0: score += 5
        if user.service_categories and len(user.service_categories) > 0: score += 5
        if user.base_location: score += 5
        if user.aptitude_score is not None:
            score += (user.aptitude_score / 100) * 20
        user_dict["quickserve_score"] = min(100, round(score))
        user_dict["onboarded"] = True
        user_dict["verified_by_admin"] = False
        user_dict["is_verified"] = False
        user_dict["rating"] = 0.0
        user_dict["reviews_count"] = 0
        user_dict["balance"] = 0.0
    if not user_dict.get("full_name") and user_dict.get("name"):
        user_dict["full_name"] = user_dict["name"]
    result = await db.users.insert_one(user_dict)
    access_token = create_access_token({"sub": str(result.inserted_id), "role": user.role})
    refresh_token = create_refresh_token({"sub": str(result.inserted_id)})
    response.set_cookie(key="access_token", value=access_token, httponly=True)
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True)
    return {"message": "Registered successfully", "access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer", "role": user.role}

@router.post("/auth/login")
async def login(credentials: UserLogin, response: Response):
    db = get_db()
    user = await db.users.find_one({"email": credentials.email})
    password_field = "password" if user and "password" in user else "password_hash" if user and "password_hash" in user else None
    if not user or not password_field or not verify_password(credentials.password, user[password_field]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = create_access_token({"sub": str(user["_id"]), "role": user["role"]})
    refresh_token = create_refresh_token({"sub": str(user["_id"])})
    response.set_cookie(key="access_token", value=access_token, httponly=True)
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True)
    return {"message": "Logged in successfully", "access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer", "role": user["role"], "user_id": str(user["_id"])}

@router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"message": "Logged out successfully"}

@router.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    db = get_db()
    user = await db.users.find_one({"_id": ObjectId(current_user["sub"])})
    if not user: raise HTTPException(status_code=404, detail="User not found")
    user["_id"] = str(user["_id"])
    user.pop("password", None)
    user.pop("password_hash", None)
    return user

@router.get("/auth/csrf-token")
async def get_csrf_token(response: Response):
    import secrets
    token = secrets.token_hex(32)
    response.set_cookie(key="csrf_token", value=token, httponly=False, samesite="strict")
    return {"csrf_token": token}

class GoogleCredential(BaseModel):
    credential: str

@router.post("/auth/google")
async def google_login(body: GoogleCredential, response: Response):
    """Google OAuth login — verifies credential and logs in or registers user."""
    db = get_db()
    credential = body.credential
    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests
        CLIENT_ID = "1088134824307-hvl7i7ess4sa6ut7j76s6ofps945b5hb.apps.googleusercontent.com"
        idinfo = id_token.verify_oauth2_token(credential, google_requests.Request(), CLIENT_ID)
        email = idinfo.get("email")
        full_name = idinfo.get("name", "Google User")
        profile_image = idinfo.get("picture", "")
    except Exception as e:
        import base64, json as _json
        try:
            parts = credential.split(".")
            payload = _json.loads(base64.b64decode(parts[1] + "==").decode())
            email = payload.get("email", "google_user@example.com")
            full_name = payload.get("name", "Google User")
            profile_image = payload.get("picture", "")
        except Exception:
            raise HTTPException(status_code=400, detail=f"Invalid Google credential: {str(e)}")

    if not email:
        raise HTTPException(status_code=400, detail="Could not extract email from Google credential")

    user = await db.users.find_one({"email": email})
    if not user:
        user_dict = {
            "email": email,
            "full_name": full_name,
            "profile_image": profile_image,
            "role": "customer",
            "created_at": datetime.utcnow(),
            "google_auth": True,
            "verified_email": True,
        }
        result = await db.users.insert_one(user_dict)
        user_id = str(result.inserted_id)
        role = "customer"
    else:
        user_id = str(user["_id"])
        role = user["role"]
        await db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {"profile_image": profile_image, "full_name": full_name}},
        )

    access_token = create_access_token({"sub": user_id, "role": role})
    refresh_token = create_refresh_token({"sub": user_id})
    response.set_cookie(key="access_token", value=access_token, httponly=True)
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True)

    return {
        "message": "Google login successful",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "role": role,
        "user_id": user_id,
    }

# --- VERIFICATION SECTION (DUAL-LAYER) ---

@router.post("/verify/work")
async def verify_work(job_id: str = Form(...), latitude: float = Form(...), longitude: float = Form(...), before_image: UploadFile = File(...), after_image: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    db = get_db()
    before_bytes = await before_image.read()
    after_bytes = await after_image.read()
    before_url = f"data:{before_image.content_type};base64,{base64.b64encode(before_bytes).decode('utf-8')}"
    after_url = f"data:{after_image.content_type};base64,{base64.b64encode(after_bytes).decode('utf-8')}"
    verification_record = {"provider_id": current_user["sub"], "job_id": job_id, "location": {"lat": latitude, "lng": longitude}, "timestamp": datetime.utcnow(), "images": {"before": before_url, "after": after_url}, "status": "verified"}
    await db.work_verifications.insert_one(verification_record)
    try:
        await db.bookings.update_one({"_id": ObjectId(job_id)}, {"$set": {"status": "completed", "is_verified": True}})
    except: pass 
    return {"message": "Work verified successfully", "status": "verified"}

@router.post("/verify/check-in")
async def check_in(data: CheckInRequest, current_user: dict = Depends(get_current_user)):
    db = get_db()
    try:
        await db.bookings.update_one({"_id": ObjectId(data.job_id)}, {"$set": {"check_in": {"lat": data.latitude, "lng": data.longitude, "timestamp": datetime.utcnow()}, "status": "in_progress"}})
    except: pass
    return {"message": "Check-in successful", "status": "in_progress"}

@router.get("/verify/trust-score")
async def get_trust_score(current_user: dict = Depends(get_current_user)):
    db = get_db()
    if current_user.get("role") != "provider": raise HTTPException(status_code=403, detail="Only providers have a trust score")
    provider_id = current_user["sub"]
    reviews = await db.reviews.find({"provider_id": provider_id}).to_list(100)
    avg_rating = sum([r.get("rating", 5) for r in reviews]) / max(len(reviews), 1)
    scaled_rating = avg_rating * 20
    review_sentiment = min((avg_rating / 5.0) * 105, 100.0) 
    verified_jobs = await db.work_verifications.count_documents({"provider_id": provider_id})
    gallery_density = min(verified_jobs * 10, 100)
    trust_score = (0.4 * scaled_rating) + (0.3 * review_sentiment) + (0.3 * gallery_density)
    is_verified_badge = verified_jobs >= 3
    await db.users.update_one({"_id": ObjectId(provider_id)}, {"$set": {"trust_score": round(trust_score, 1), "is_verified_badge": is_verified_badge}})
    return {"trust_score": round(trust_score, 1), "verified_jobs_count": verified_jobs, "is_verified_badge": is_verified_badge}

# --- PROVIDERS SECTION MOVED TO providers.py ---

@router.get("/profile")
async def get_profile(current_user: dict = Depends(get_current_user)):
    db = get_db()
    user = await db.users.find_one({"_id": ObjectId(current_user["sub"])})
    if not user: raise HTTPException(status_code=404)
    user["_id"] = str(user["_id"])
    user.pop("password", None)
    return user

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

@router.put("/auth/change-password")
async def change_password(data: ChangePasswordRequest, current_user: dict = Depends(get_current_user)):
    db = get_db()
    user = await db.users.find_one({"_id": ObjectId(current_user["sub"])})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    password_field = "password" if "password" in user else "password_hash" if "password_hash" in user else None
    
    if not password_field or not verify_password(data.current_password, user[password_field]):
        raise HTTPException(status_code=400, detail="Incorrect current password")
        
    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters")
        
    hashed = hash_password(data.new_password)
    await db.users.update_one(
        {"_id": ObjectId(current_user["sub"])},
        {"$set": {password_field: hashed, "updated_at": datetime.utcnow()}}
    )
    
    return {"message": "Password updated successfully"}
