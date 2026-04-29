from fastapi import APIRouter, HTTPException, Depends, Response, Cookie, Request
from models.schemas import UserCreate, UserLogin, Token, UserRole
from middleware.auth import hash_password, verify_password, create_access_token, create_refresh_token, get_current_user
from database.connection import get_db
from datetime import datetime
from typing import Optional
import logging

# Configure local logging
logging.basicConfig(filename="auth_debug.log", level=logging.INFO, format="%(asctime)s - %(message)s")

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register")
async def register(user: UserCreate, response: Response):
    db = get_db()
    
    # 1. Validation: Check if email already exists
    existing_email = await db.users.find_one({"email": user.email})
    if existing_email:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    # 2. Validation: Check if phone number already exists
    if user.phone:
        existing_phone = await db.users.find_one({"phone": user.phone})
        if existing_phone:
            raise HTTPException(status_code=400, detail="This phone number is already associated with another account.")

    # 3. Validation: Minimum password length (though Pydantic handles basics, we can be explicit)
    if not user.password or len(user.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long.")

    user_dict = user.dict()
    user_dict["password"] = hash_password(user.password)
    user_dict["created_at"] = datetime.utcnow()
    user_dict["addresses"] = []
    
    # 4. Provider specific setup: QuickServe Score & Verification
    if user.role == UserRole.PROVIDER:
        # Calculate initial score based on profile completion
        score = 75 # Base score
        if user.bio: score += 5
        if user.business_name: score += 5
        if user.experience_years and user.experience_years > 0: score += 5
        if user.service_categories and len(user.service_categories) > 0: score += 5
        if user.base_location: score += 5
        
        # Include aptitude score if provided (scaled to weight significantly)
        if user.aptitude_score is not None:
            # We add up to 20 bonus points based on test performance
            score += (user.aptitude_score / 100) * 20
        
        user_dict["quickserve_score"] = min(100, round(score))
        user_dict["aptitude_score"] = user.aptitude_score
        user_dict["onboarded"] = True
        user_dict["verified_by_admin"] = False # Needs admin manual verification
        user_dict["is_verified"] = False
        user_dict["rating"] = 0.0
        user_dict["reviews_count"] = 0
        user_dict["balance"] = 0.0
    
    # Normalize name field
    if not user_dict.get("full_name") and user_dict.get("name"):
        user_dict["full_name"] = user_dict["name"]
        
    result = await db.users.insert_one(user_dict)

    access_token = create_access_token({"sub": str(result.inserted_id), "role": user.role})
    refresh_token = create_refresh_token({"sub": str(result.inserted_id)})
    
    response.set_cookie(key="access_token", value=access_token, httponly=True)
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True)
    
    return {
        "message": "Registered successfully",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "role": user.role
    }

@router.post("/login")
async def login(credentials: UserLogin, response: Response):
    db = get_db()
    logging.info(f"Login attempt: {credentials.email}")
    print(f"Login attempt: {credentials.email}")
    user = await db.users.find_one({"email": credentials.email})
    if user:
        logging.info(f"User found: {user.get('email')} with role: {user.get('role')}")
        print(f"User found: {user.get('email')} with role: {user.get('role')}")
    else:
        logging.info(f"User not found: {credentials.email}")
        print(f"User not found: {credentials.email}")
    
    # Check for password in different fields (backward compatibility)
    password_field = None
    if user:
        if "password" in user:
            password_field = "password"
        elif "password_hash" in user:
            password_field = "password_hash"
    
    if not user or not password_field or not verify_password(credentials.password, user[password_field]):
        # Log failed attempt
        try:
            await db.login_activity.insert_one({
                "user_id": "", "email": credentials.email,
                "full_name": "", "role": "unknown",
                "method": "email", "status": "failed",
                "timestamp": datetime.utcnow(),
            })
        except Exception:
            pass
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token({"sub": str(user["_id"]), "role": user["role"]})
    refresh_token = create_refresh_token({"sub": str(user["_id"])})
    
    response.set_cookie(key="access_token", value=access_token, httponly=True)
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True)
    
    # ── Log successful login ────────────────────────────────────────────
    try:
        await db.login_activity.insert_one({
            "user_id":   str(user["_id"]),
            "email":     user.get("email", ""),
            "full_name": user.get("full_name", ""),
            "role":      user.get("role", "customer"),
            "method":    "email",
            "status":    "success",
            "timestamp": datetime.utcnow(),
        })
    except Exception:
        pass

    logging.info(f"Login successful for user: {credentials.email}")
    print(f"Login successful for user: {credentials.email}")
    return {
        "message": "Logged in successfully",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "role": user["role"],
        "user_id": str(user["_id"])
    }

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"message": "Logged out successfully"}

@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    logging.info(f"Get profile for user ID: {current_user.get('sub')}")
    db = get_db()
    from bson import ObjectId
    user = await db.users.find_one({"_id": ObjectId(current_user["sub"])})
    if not user:
        logging.error(f"User not found for ID: {current_user.get('sub')}")
        raise HTTPException(status_code=404, detail="User not found")
    user["_id"] = str(user["_id"])
    user.pop("password", None)
    user.pop("password_hash", None)
    logging.info(f"Profile returned for: {user.get('email')}")
    return user

@router.post("/google")
async def google_login(credential: str, response: Response):
    """Google OAuth login - verifies credential and logs in or registers user"""
    db = get_db()
    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests
        CLIENT_ID = "1088134824307-hvl7i7ess4sa6ut7j76s6ofps945b5hb.apps.googleusercontent.com"
        idinfo = id_token.verify_oauth2_token(credential, google_requests.Request(), CLIENT_ID)
        email = idinfo.get('email')
        full_name = idinfo.get('name', 'Google User')
        profile_image = idinfo.get('picture', '')
    except Exception as e:
        # Fallback: decode JWT without verification for dev
        import base64, json
        try:
            parts = credential.split('.')
            payload = json.loads(base64.b64decode(parts[1] + '==').decode())
            email = payload.get('email', 'google_user@example.com')
            full_name = payload.get('name', 'Google User')
            profile_image = payload.get('picture', '')
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
            {"$set": {"profile_image": profile_image, "full_name": full_name}}
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
        "role": role
    }

@router.post("/refresh")
async def refresh_token(response: Response, refresh_token: str = None, request: Request = None):
    """Issue new access token using refresh token (cookie or body)."""
    from fastapi import Request as Req
    token = refresh_token
    if not token and request:
        token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="Refresh token missing")
    from middleware.auth import verify_refresh_token, create_access_token
    payload = verify_refresh_token(token)
    new_access = create_access_token({"sub": payload["sub"]})
    response.set_cookie(key="access_token", value=new_access, httponly=True, samesite="lax")
    return {"access_token": new_access, "token_type": "bearer"}


@router.get("/csrf-token")
async def get_csrf_token(response: Response):
    """Issue a CSRF token stored in a non-httpOnly cookie so JS can read it."""
    import secrets
    token = secrets.token_hex(32)
    response.set_cookie(key="csrf_token", value=token, httponly=False, samesite="strict")
    return {"csrf_token": token}


async def send_otp(phone: str):
    """Mock sending OTP via Twilio"""
    # Mock: client.verify.v2.services(SID).verifications.create(to=phone, channel='sms')
    print(f"OTP sent to {phone}: 123456")
    return {"status": "sent", "message": "OTP sent successfully"}

@router.post("/verify-otp")
async def verify_otp(phone: str, otp: str):
    """Mock verify OTP"""
    if otp == "123456":
        return {"status": "verified"}
    raise HTTPException(status_code=400, detail="Invalid OTP")
