"""Work Verification Router
- POST /verify-work        : submit before/after images + GPS
- POST /checkin            : GPS check-in at service site
- GET  /trust-score/{uid}  : weighted trust score
- GET  /gallery/{uid}      : list provider's work gallery
- GET  /checkins/{uid}     : list provider's check-in history
- GET  /badge/{uid}        : provider verification badge status
"""

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from database.connection import get_db
from middleware.auth import get_current_user
from bson import ObjectId
from datetime import datetime
from typing import Optional
import os, hashlib, uuid, shutil

router = APIRouter(prefix="/work-verification", tags=["Work Verification"])

UPLOAD_DIR = os.path.join("uploads", "work_gallery")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def _safe_filename(original: str) -> str:
    ext = os.path.splitext(original)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File type {ext} not allowed. Use JPG/PNG/WEBP.")
    return f"{uuid.uuid4().hex}{ext}"


async def _save_file(file: UploadFile, dest_dir: str) -> tuple[str, str]:
    """Save upload, return (relative_path, sha256_hash)."""
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 10 MB)")
    fname = _safe_filename(file.filename or "upload.jpg")
    path = os.path.join(dest_dir, fname)
    with open(path, "wb") as f:
        f.write(content)
    file_hash = hashlib.sha256(content).hexdigest()
    return path, file_hash


# ── POST /verify-work ─────────────────────────────────────────────────────────

@router.post("/verify-work")
async def verify_work(
    booking_id: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    notes: Optional[str] = Form(None),
    before_image: Optional[UploadFile] = File(None),
    after_image: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user),
):
    """
    Provider submits before/after images + GPS coordinates as proof of work.
    Stores evidence, computes trust score update.
    """
    if current_user.get("role") not in ("provider", "admin"):
        raise HTTPException(status_code=403, detail="Only providers can submit work evidence")

    db = get_db()
    provider_id = current_user["sub"]

    # Validate booking belongs to this provider
    try:
        booking = await db.bookings.find_one({"_id": ObjectId(booking_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid booking ID")
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if str(booking.get("provider_id", "")) != provider_id and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not your booking")

    dest = os.path.join(UPLOAD_DIR, provider_id)
    os.makedirs(dest, exist_ok=True)

    evidence: dict = {
        "provider_id": provider_id,
        "booking_id": booking_id,
        "latitude": latitude,
        "longitude": longitude,
        "notes": notes or "",
        "submitted_at": datetime.utcnow(),
        "images": [],
    }

    for label, upload in [("before", before_image), ("after", after_image)]:
        if upload and upload.filename:
            path, sha = await _save_file(upload, dest)
            evidence["images"].append({
                "label": label,
                "path": path,
                "sha256": sha,
                "uploaded_at": datetime.utcnow().isoformat(),
            })

    result = await db.work_evidence.insert_one(evidence)

    # Update booking with evidence reference
    await db.bookings.update_one(
        {"_id": ObjectId(booking_id)},
        {"$set": {"work_evidence_id": str(result.inserted_id), "evidence_submitted": True}},
    )

    # Recompute trust score
    trust = await _compute_trust(provider_id, db)
    await db.users.update_one(
        {"_id": ObjectId(provider_id)},
        {"$set": {"trust_score": trust}},
    )

    return {
        "status": "success",
        "evidence_id": str(result.inserted_id),
        "images_uploaded": len(evidence["images"]),
        "trust_score": trust,
        "message": "Work evidence submitted successfully",
    }


# ── POST /checkin ─────────────────────────────────────────────────────────────

@router.post("/checkin")
async def checkin(
    booking_id: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    current_user: dict = Depends(get_current_user),
):
    """Record provider GPS check-in at service site."""
    if current_user.get("role") not in ("provider", "admin"):
        raise HTTPException(status_code=403, detail="Only providers can check in")

    db = get_db()
    provider_id = current_user["sub"]

    record = {
        "provider_id": provider_id,
        "booking_id": booking_id,
        "latitude": latitude,
        "longitude": longitude,
        "checked_in_at": datetime.utcnow(),
    }
    result = await db.provider_checkins.insert_one(record)

    await db.bookings.update_one(
        {"_id": ObjectId(booking_id)},
        {"$set": {
            "checkin_lat": latitude,
            "checkin_lng": longitude,
            "checkin_time": datetime.utcnow(),
            "status": "in_progress",
        }},
    )

    return {
        "checkin_id": str(result.inserted_id),
        "checked_in_at": record["checked_in_at"].isoformat(),
        "message": "Check-in recorded",
    }


# ── GET /trust-score/{provider_id} ───────────────────────────────────────────

@router.get("/trust-score/{provider_id}")
async def get_trust_score(provider_id: str):
    """Public: compute and return weighted trust score for a provider."""
    db = get_db()
    trust = await _compute_trust(provider_id, db)
    return {"provider_id": provider_id, "trust_score": trust, "breakdown": await _trust_breakdown(provider_id, db)}


# ── GET /gallery/{provider_id} ────────────────────────────────────────────────

@router.get("/gallery/{provider_id}")
async def get_gallery(provider_id: str):
    """Public: list work evidence images for a provider."""
    db = get_db()
    docs = await db.work_evidence.find({"provider_id": provider_id}).sort("submitted_at", -1).limit(20).to_list(20)
    for d in docs:
        d["_id"] = str(d["_id"])
        if isinstance(d.get("submitted_at"), datetime):
            d["submitted_at"] = d["submitted_at"].isoformat()
    return {"gallery": docs, "total": len(docs)}


# ── GET /checkins/{provider_id} ───────────────────────────────────────────────

@router.get("/checkins/{provider_id}")
async def get_checkins(provider_id: str, current_user: dict = Depends(get_current_user)):
    """Provider/admin: list check-in history."""
    if current_user["sub"] != provider_id and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    db = get_db()
    docs = await db.provider_checkins.find({"provider_id": provider_id}).sort("checked_in_at", -1).limit(50).to_list(50)
    for d in docs:
        d["_id"] = str(d["_id"])
        if isinstance(d.get("checked_in_at"), datetime):
            d["checked_in_at"] = d["checked_in_at"].isoformat()
    return {"checkins": docs, "total": len(docs)}


# ── GET /badge/{provider_id} ──────────────────────────────────────────────────

@router.get("/badge/{provider_id}")
async def get_provider_badge(provider_id: str):
    """
    Public: return badge eligibility.
    Badge is awarded when provider has 3+ completed jobs with verified photos.
    """
    db = get_db()
    # Count bookings that have evidence submitted
    verified_jobs = await db.bookings.count_documents({
        "provider_id": provider_id,
        "status": "completed",
        "evidence_submitted": True,
    })
    trust = await _compute_trust(provider_id, db)
    badge_earned = verified_jobs >= 3
    return {
        "provider_id": provider_id,
        "badge_earned": badge_earned,
        "verified_jobs": verified_jobs,
        "jobs_needed": max(0, 3 - verified_jobs),
        "trust_score": trust,
    }


# ── Trust Score Logic ─────────────────────────────────────────────────────────
# Trust = (0.4 × Rating) + (0.3 × Review Sentiment) + (0.3 × Gallery Density)

async def _compute_trust(provider_id: str, db) -> float:
    breakdown = await _trust_breakdown(provider_id, db)
    score = (
        0.4 * breakdown["rating_component"]
        + 0.3 * breakdown["sentiment_component"]
        + 0.3 * breakdown["gallery_component"]
    )
    return round(min(100.0, max(0.0, score)), 1)


async def _trust_breakdown(provider_id: str, db) -> dict:
    # Rating component (0-100)
    try:
        user = await db.users.find_one({"_id": ObjectId(provider_id)})
    except Exception:
        user = None
    raw_rating = (user.get("rating", 0) if user else 0) or 0
    rating_component = (raw_rating / 5.0) * 100

    # Sentiment component: ratio of 4-5 star reviews (0-100)
    reviews = await db.reviews.find({"provider_id": provider_id}).to_list(500)
    if reviews:
        positive = sum(1 for r in reviews if r.get("rating", 0) >= 4)
        sentiment_component = (positive / len(reviews)) * 100
    else:
        sentiment_component = 50.0  # neutral default

    # Gallery density: each evidence doc = 10 points, capped at 100
    evidence_count = await db.work_evidence.count_documents({"provider_id": provider_id})
    gallery_component = min(100.0, evidence_count * 10)

    return {
        "rating_component": round(rating_component, 1),
        "sentiment_component": round(sentiment_component, 1),
        "gallery_component": round(gallery_component, 1),
        "evidence_count": evidence_count,
        "review_count": len(reviews),
        "raw_rating": raw_rating,
    }
