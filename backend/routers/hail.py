from fastapi import APIRouter, Depends
from database.connection import get_db
from middleware.auth import get_current_user
from datetime import datetime
from bson import ObjectId

router = APIRouter(prefix="/hail", tags=["Voice Hailing"])

@router.post("/broadcast")
async def broadcast_hail(service_type: str, location: dict, current_user: dict = Depends(get_current_user)):
    db = get_db()
    hail = {
        "user_id": current_user["sub"],
        "service_type": service_type,
        "location": location,
        "status": "active",
        "created_at": datetime.utcnow(),
        "responses": []
    }
    result = await db.hail_requests.insert_one(hail)
    return {"id": str(result.inserted_id), "status": "broadcasting", "radius": "0.2 miles"}

@router.get("/nearby")
async def get_nearby_hails(lat: float, lng: float, current_user: dict = Depends(get_current_user)):
    db = get_db()
    hails = await db.hail_requests.find({"status": "active"}).to_list(length=50)
    for h in hails:
        h["_id"] = str(h["_id"])
    return hails

@router.post("/{hail_id}/respond")
async def respond_to_hail(hail_id: str, eta: int, current_user: dict = Depends(get_current_user)):
    db = get_db()
    await db.hail_requests.update_one(
        {"_id": ObjectId(hail_id)},
        {"$push": {"responses": {"provider_id": current_user["sub"], "eta": eta, "timestamp": datetime.utcnow()}}}
    )
    return {"status": "response_sent"}

@router.put("/{hail_id}/accept")
async def accept_hail_response(hail_id: str, provider_id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    await db.hail_requests.update_one(
        {"_id": ObjectId(hail_id)},
        {"$set": {"status": "accepted", "selected_provider": provider_id}}
    )
    return {"status": "accepted", "provider_id": provider_id}

@router.get("/active")
async def get_active_hails(current_user: dict = Depends(get_current_user)):
    db = get_db()
    hails = await db.hail_requests.find({"user_id": current_user["sub"], "status": "active"}).to_list(length=10)
    for h in hails:
        h["_id"] = str(h["_id"])
    return hails

@router.get("/statistics")
async def get_hail_statistics(current_user: dict = Depends(get_current_user)):
    db = get_db()
    total = await db.hail_requests.count_documents({"user_id": current_user["sub"]})
    accepted = await db.hail_requests.count_documents({"user_id": current_user["sub"], "status": "accepted"})
    return {"total_hails": total, "accepted": accepted, "success_rate": (accepted/total*100) if total > 0 else 0}
