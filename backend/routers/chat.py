from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from database.connection import get_db
from middleware.auth import get_current_user
from datetime import datetime
from bson import ObjectId
from typing import List, Optional
from pydantic import BaseModel

router = APIRouter(prefix="/chat", tags=["In-App Chat"])

# Store active WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict = {}
    
    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket
    
    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
    
    async def send_message(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_json(message)

manager = ConnectionManager()

class ConversationCreate(BaseModel):
    participant_id: str
    booking_id: Optional[str] = None

class MessageCreate(BaseModel):
    conversation_id: str
    message: str
    message_type: Optional[str] = "text"

# Create or get conversation
@router.post("/conversations")
async def create_conversation(
    params: ConversationCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new conversation between customer and provider"""
    participant_id = params.participant_id
    booking_id = params.booking_id
    db = get_db()
    
    # Check if conversation already exists
    existing = await db.conversations.find_one({
        "participants": {"$all": [current_user["sub"], participant_id]}
    })
    
    if existing:
        existing["_id"] = str(existing["_id"])
        return existing
    
    # Create new conversation
    conversation = {
        "participants": [current_user["sub"], participant_id],
        "booking_id": booking_id,
        "created_at": datetime.utcnow(),
        "last_message_at": datetime.utcnow(),
        "unread_count": {current_user["sub"]: 0, participant_id: 0}
    }
    
    result = await db.conversations.insert_one(conversation)
    conversation["_id"] = str(result.inserted_id)
    
    return conversation

# Get user conversations
@router.get("/conversations")
async def get_conversations(current_user: dict = Depends(get_current_user)):
    """Get all conversations for current user"""
    db = get_db()
    
    conversations = await db.conversations.find({
        "participants": current_user["sub"]
    }).sort("last_message_at", -1).to_list(length=50)
    
    # Enrich with participant details and last message
    for conv in conversations:
        conv["_id"] = str(conv["_id"])
        
        # Get other participant
        other_id = [p for p in conv["participants"] if p != current_user["sub"]][0]
        try:
            other_query = {"_id": ObjectId(other_id)} if len(other_id) == 24 else {"_id": other_id}
            other_user = await db.users.find_one(other_query)
        except:
            other_user = None
            
        if other_user:
            conv["other_user"] = {
                "id": str(other_user["_id"]),
                "name": other_user.get("full_name") or other_user.get("name", "Unknown"),
                "profile_image": other_user.get("profile_image", "")
            }
        else:
            conv["other_user"] = {"id": other_id, "name": "User", "profile_image": ""}
        
        # Get last message
        last_msg = await db.messages.find_one(
            {"conversation_id": str(conv["_id"])},
            sort=[("timestamp", -1)]
        )
        if last_msg:
            conv["last_message"] = {
                "text": last_msg.get("message", ""),
                "timestamp": last_msg.get("timestamp")
            }
    
    return conversations

# Send message
@router.post("/messages")
async def send_message(
    params: MessageCreate,
    current_user: dict = Depends(get_current_user)
):
    """Send a message in a conversation"""
    db = get_db()
    conversation_id = params.conversation_id
    message = params.message
    message_type = params.message_type

    # Verify conversation exists and user is participant
    try:
        query = {"_id": ObjectId(conversation_id)} if len(conversation_id) == 24 else {"_id": conversation_id}
        conversation = await db.conversations.find_one(query)
    except:
        conversation = None
        
    if not conversation or current_user["sub"] not in conversation.get("participants", []):
        return {"error": "Conversation not found or access denied"}
    
    # Create message
    msg = {
        "conversation_id": conversation_id,
        "sender_id": current_user["sub"],
        "message": message,
        "message_type": message_type,
        "timestamp": datetime.utcnow(),
        "read": False
    }
    
    result = await db.messages.insert_one(msg)
    msg["_id"] = str(result.inserted_id)
    
    # Update conversation
    other_participant = [p for p in conversation["participants"] if p != current_user["sub"]][0]
    update_query = {"_id": ObjectId(conversation_id)} if len(conversation_id) == 24 else {"_id": conversation_id}
    await db.conversations.update_one(
        update_query,
        {
            "$set": {"last_message_at": datetime.utcnow()},
            "$inc": {f"unread_count.{other_participant}": 1}
        }
    )
    
    # Send real-time notification via WebSocket
    sender = await db.users.find_one({"_id": ObjectId(current_user["sub"])} if len(current_user["sub"]) == 24 else {"_id": current_user["sub"]})
    sender_name = sender.get("full_name", "Someone") if sender else "Someone"
    await manager.send_message(other_participant, {
        "type": "new_message",
        "conversation_id": conversation_id,
        "message": {**msg, "sender_name": sender_name}
    })
    
    return msg

# Get messages
@router.get("/messages/{conversation_id}")
async def get_messages(
    conversation_id: str,
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """Get messages from a conversation"""
    db = get_db()
    
    # Verify access
    try:
        query = {"_id": ObjectId(conversation_id)} if len(conversation_id) == 24 else {"_id": conversation_id}
        conversation = await db.conversations.find_one(query)
    except:
        conversation = None

    if not conversation or current_user["sub"] not in conversation.get("participants", []):
        return {"error": "Access denied"}
    
    # Get messages
    messages = await db.messages.find({
        "conversation_id": conversation_id
    }).sort("timestamp", -1).limit(limit).to_list(length=limit)
    
    for msg in messages:
        msg["_id"] = str(msg["_id"])
    
    # Mark as read
    await db.messages.update_many(
        {
            "conversation_id": conversation_id,
            "sender_id": {"$ne": current_user["sub"]},
            "read": False
        },
        {"$set": {"read": True}}
    )
    
    # Reset unread count
    update_query = {"_id": ObjectId(conversation_id)} if len(conversation_id) == 24 else {"_id": conversation_id}
    await db.conversations.update_one(
        update_query,
        {"$set": {f"unread_count.{current_user['sub']}": 0}}
    )
    
    return list(reversed(messages))

# Mark message as read
@router.put("/messages/{message_id}/read")
async def mark_as_read(message_id: str, current_user: dict = Depends(get_current_user)):
    """Mark a message as read"""
    db = get_db()
    
    await db.messages.update_one(
        {"_id": ObjectId(message_id)},
        {"$set": {"read": True}}
    )
    
    return {"status": "marked_as_read"}

# Delete message
@router.delete("/messages/{message_id}")
async def delete_message(message_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a message (soft delete)"""
    db = get_db()
    
    await db.messages.update_one(
        {"_id": ObjectId(message_id), "sender_id": current_user["sub"]},
        {"$set": {"deleted": True, "message": "[Message deleted]"}}
    )
    
    return {"status": "deleted"}

# Get unread count
@router.get("/unread-count")
async def get_unread_count(current_user: dict = Depends(get_current_user)):
    """Get total unread message count"""
    db = get_db()
    
    conversations = await db.conversations.find({
        "participants": current_user["sub"]
    }).to_list(length=100)
    
    total_unread = sum(
        conv.get("unread_count", {}).get(current_user["sub"], 0)
        for conv in conversations
    )
    
    return {"unread_count": total_unread}

# WebSocket endpoint for real-time chat
@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str, token: Optional[str] = None):
    """WebSocket connection for real-time messaging"""
    await manager.connect(user_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(user_id)
    except Exception:
        manager.disconnect(user_id)

# Quick replies / Templates
@router.get("/quick-replies")
async def get_quick_replies(current_user: dict = Depends(get_current_user)):
    """Get quick reply templates"""
    
    if current_user["role"] == "provider":
        return {
            "quick_replies": [
                "I'm on my way!",
                "I'll be there in 15 minutes",
                "Running 5 minutes late",
                "I've arrived at your location",
                "Service completed. Thank you!",
                "Could you please provide more details?",
                "I'll need to reschedule. Is tomorrow okay?"
            ]
        }
    else:
        return {
            "quick_replies": [
                "When will you arrive?",
                "Thank you!",
                "Please call me when you're nearby",
                "I need to reschedule",
                "Great service, thanks!",
                "Can you provide an estimate?",
                "Is this included in the price?"
            ]
        }

# Search conversations
@router.get("/search")
async def search_conversations(
    query: str,
    current_user: dict = Depends(get_current_user)
):
    """Search messages and conversations"""
    db = get_db()
    
    # Get user's conversations
    conversations = await db.conversations.find({
        "participants": current_user["sub"]
    }).to_list(length=100)
    
    conv_ids = [str(c["_id"]) for c in conversations]
    
    # Search messages
    messages = await db.messages.find({
        "conversation_id": {"$in": conv_ids},
        "message": {"$regex": query, "$options": "i"}
    }).limit(20).to_list(length=20)
    
    for msg in messages:
        msg["_id"] = str(msg["_id"])
    
    return {"results": messages, "count": len(messages)}
