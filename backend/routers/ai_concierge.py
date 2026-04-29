from fastapi import APIRouter, Depends
from database.connection import get_db
from middleware.auth import get_current_user
from datetime import datetime, timedelta
from typing import List, Optional, Dict
import json

router = APIRouter(prefix="/ai-concierge", tags=["AI Service Concierge"])

PERSONALITY_TYPES = {
    "professional": {
        "tone": "formal",
        "greeting": "Good day! I'm your professional service concierge.",
        "style": "efficient and detailed"
    },
    "friendly": {
        "tone": "casual",
        "greeting": "Hey there! I'm your friendly service buddy!",
        "style": "warm and conversational"
    },
    "minimalist": {
        "tone": "brief",
        "greeting": "Hi. Ready to help.",
        "style": "concise and direct"
    }
}

@router.post("/setup-profile")
async def setup_concierge_profile(
    preferences: Dict,
    personality: str = "friendly",
    current_user: dict = Depends(get_current_user)
):
    """Set up personalized AI concierge profile"""
    db = get_db()
    
    if personality not in PERSONALITY_TYPES:
        personality = "friendly"
    
    # Create AI profile
    ai_profile = {
        "user_id": current_user["sub"],
        "personality": personality,
        "preferences": preferences,
        "learning_data": {
            "service_patterns": {},
            "time_preferences": {},
            "budget_patterns": {},
            "provider_preferences": {}
        },
        "proactive_settings": {
            "suggest_services": preferences.get("proactive_suggestions", True),
            "schedule_reminders": preferences.get("schedule_reminders", True),
            "budget_alerts": preferences.get("budget_alerts", True),
            "seasonal_recommendations": preferences.get("seasonal_recommendations", True)
        },
        "created_at": datetime.utcnow(),
        "last_interaction": datetime.utcnow()
    }
    
    await db.ai_concierge_profiles.update_one(
        {"user_id": current_user["sub"]},
        {"$set": ai_profile},
        upsert=True
    )
    
    return {
        "message": f"AI Concierge configured with {personality} personality!",
        "greeting": PERSONALITY_TYPES[personality]["greeting"],
        "features_enabled": list(preferences.keys())
    }

from models.schemas import AIChatRequest, AIProfileSetup

@router.post("/chat")
async def chat_with_concierge(
    data: AIChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """Chat with AI concierge"""
    db = get_db()
    
    # Auto-setup profile if missing
    ai_profile = await db.ai_concierge_profiles.find_one({"user_id": current_user["sub"]})
    if not ai_profile:
        # Create a default profile
        ai_profile = {
            "user_id": current_user["sub"],
            "personality": "friendly",
            "preferences": {"proactive_suggestions": True},
            "learning_data": {},
            "proactive_settings": {
                "suggest_services": True,
                "schedule_reminders": True,
                "budget_alerts": True,
                "seasonal_recommendations": True
            },
            "created_at": datetime.utcnow(),
            "last_interaction": datetime.utcnow()
        }
        await db.ai_concierge_profiles.insert_one(ai_profile)
    
    message = data.message
    context = data.context
    
    # Process message and generate response
    response = await process_concierge_message(message, ai_profile, context, current_user, db)
    
    # Log conversation
    await db.concierge_conversations.insert_one({
        "user_id": current_user["sub"],
        "message": message,
        "response": response["text"],
        "intent": response.get("intent"),
        "actions_taken": response.get("actions", []),
        "timestamp": datetime.utcnow()
    })
    
    # Update last interaction
    await db.ai_concierge_profiles.update_one(
        {"user_id": current_user["sub"]},
        {"$set": {"last_interaction": datetime.utcnow()}}
    )
    
    return response

@router.get("/proactive-suggestions")
async def get_proactive_suggestions(current_user: dict = Depends(get_current_user)):
    """Get proactive service suggestions from AI concierge"""
    db = get_db()
    
    ai_profile = await db.ai_concierge_profiles.find_one({"user_id": current_user["sub"]})
    if not ai_profile or not ai_profile["proactive_settings"]["suggest_services"]:
        return {"suggestions": []}
    
    # Analyze user patterns
    suggestions = await generate_proactive_suggestions(current_user["sub"], ai_profile, db)
    
    return {
        "suggestions": suggestions,
        "personality_note": get_personality_note(ai_profile["personality"], "suggestions"),
        "generated_at": datetime.utcnow().isoformat()
    }

@router.post("/schedule-coordination")
async def coordinate_multi_service_schedule(
    services: List[Dict],
    preferences: Dict,
    current_user: dict = Depends(get_current_user)
):
    """AI-powered coordination of multiple services"""
    db = get_db()
    
    ai_profile = await db.ai_concierge_profiles.find_one({"user_id": current_user["sub"]})
    
    # Analyze and optimize schedule
    optimized_schedule = await optimize_service_schedule(services, preferences, ai_profile, db)
    
    # Create coordination plan
    coordination_plan = {
        "user_id": current_user["sub"],
        "services": services,
        "optimized_schedule": optimized_schedule,
        "preferences": preferences,
        "created_at": datetime.utcnow(),
        "status": "planned",
        "ai_confidence": optimized_schedule.get("confidence_score", 0.8)
    }
    
    result = await db.service_coordination.insert_one(coordination_plan)
    
    return {
        "coordination_id": str(result.inserted_id),
        "optimized_schedule": optimized_schedule,
        "ai_explanation": generate_schedule_explanation(optimized_schedule, ai_profile),
        "estimated_savings": optimized_schedule.get("cost_savings", 0)
    }

@router.get("/learning-insights")
async def get_learning_insights(current_user: dict = Depends(get_current_user)):
    """Get AI's learning insights about user preferences"""
    db = get_db()
    
    ai_profile = await db.ai_concierge_profiles.find_one({"user_id": current_user["sub"]})
    if not ai_profile:
        return {"error": "AI profile not found"}
    
    # Analyze user's booking history for patterns
    bookings = await db.bookings.find({
        "user_id": current_user["sub"]
    }).sort("created_at", -1).limit(50).to_list(length=50)
    
    insights = await analyze_user_patterns(bookings, ai_profile, db)
    
    return {
        "insights": insights,
        "learning_accuracy": calculate_learning_accuracy(ai_profile),
        "recommendations": generate_improvement_recommendations(insights)
    }

@router.post("/set-automation")
async def set_service_automation(
    automation_rules: List[Dict],
    current_user: dict = Depends(get_current_user)
):
    """Set up automated service booking rules"""
    db = get_db()
    
    # Validate automation rules
    validated_rules = []
    for rule in automation_rules:
        if validate_automation_rule(rule):
            validated_rules.append({
                **rule,
                "created_at": datetime.utcnow(),
                "status": "active",
                "executions": 0
            })
    
    # Store automation rules
    await db.service_automations.update_one(
        {"user_id": current_user["sub"]},
        {
            "$set": {
                "rules": validated_rules,
                "updated_at": datetime.utcnow()
            }
        },
        upsert=True
    )
    
    return {
        "message": f"{len(validated_rules)} automation rules configured",
        "rules": validated_rules,
        "next_execution": get_next_execution_time(validated_rules)
    }

@router.get("/dashboard")
async def get_concierge_dashboard(current_user: dict = Depends(get_current_user)):
    """Get AI concierge dashboard with all insights"""
    db = get_db()
    
    ai_profile = await db.ai_concierge_profiles.find_one({"user_id": current_user["sub"]})
    if not ai_profile:
        return {"error": "AI profile not found"}
    
    # Get various dashboard components
    recent_suggestions = await db.concierge_conversations.find({
        "user_id": current_user["sub"],
        "intent": "suggestion"
    }).sort("timestamp", -1).limit(5).to_list(length=5)
    
    active_automations = await db.service_automations.find_one({"user_id": current_user["sub"]})
    automation_count = len(active_automations.get("rules", [])) if active_automations else 0
    
    # Calculate efficiency metrics
    total_conversations = await db.concierge_conversations.count_documents({"user_id": current_user["sub"]})
    successful_bookings = await db.bookings.count_documents({
        "user_id": current_user["sub"],
        "booking_source": "ai_concierge"
    })
    
    efficiency_rate = (successful_bookings / max(total_conversations, 1)) * 100
    
    return {
        "ai_personality": ai_profile["personality"],
        "total_interactions": total_conversations,
        "successful_bookings": successful_bookings,
        "efficiency_rate": round(efficiency_rate, 1),
        "active_automations": automation_count,
        "recent_suggestions": recent_suggestions,
        "learning_progress": calculate_learning_progress(ai_profile),
        "next_proactive_check": datetime.utcnow() + timedelta(hours=6)
    }

async def process_concierge_message(message: str, ai_profile: Dict, context: Optional[Dict], current_user: Dict, db) -> Dict:
    """Process user message and generate AI response"""
    
    message_lower = message.lower()
    personality = ai_profile["personality"]
    
    # Intent detection
    intent = detect_intent(message_lower)
    
    response = {
        "text": "",
        "intent": intent,
        "actions": [],
        "suggestions": []
    }
    
    if intent == "booking_request":
        # Handle service booking request
        service_type = extract_service_type(message_lower)
        if service_type:
            providers = await db.users.find({
                "role": "provider",
                "specializations": service_type,
                "is_verified": True
            }).limit(3).to_list(length=3)
            
            response["text"] = format_response(
                f"I found {len(providers)} great {service_type} providers for you! Would you like me to show you the top-rated ones?",
                personality
            )
            response["actions"] = ["show_providers"]
            response["suggestions"] = [p["full_name"] for p in providers]
        else:
            response["text"] = format_response("What type of service are you looking for? I can help you find the perfect provider!", personality)
    
    elif intent == "schedule_query":
        # Handle schedule-related queries
        upcoming_bookings = await db.bookings.find({
            "user_id": current_user["sub"],
            "scheduled_time": {"$gte": datetime.utcnow()},
            "status": {"$in": ["confirmed", "pending"]}
        }).sort("scheduled_time", 1).limit(5).to_list(length=5)
        
        if upcoming_bookings:
            next_booking = upcoming_bookings[0]
            response["text"] = format_response(
                f"Your next service is {next_booking.get('service_type', 'a service')} scheduled for {next_booking['scheduled_time'].strftime('%B %d at %I:%M %p')}. You have {len(upcoming_bookings)} total upcoming bookings.",
                personality
            )
        else:
            response["text"] = format_response("You don't have any upcoming bookings. Would you like me to suggest some services?", personality)
    
    elif intent == "recommendation_request":
        # Generate personalized recommendations
        recommendations = await generate_smart_recommendations(current_user["sub"], ai_profile, db)
        response["text"] = format_response(
            f"Based on your preferences, I recommend: {', '.join([r['service'] for r in recommendations[:3]])}. These align perfectly with your usual patterns!",
            personality
        )
        response["suggestions"] = recommendations
    
    elif intent == "budget_query":
        # Handle budget-related questions
        monthly_spending = await calculate_monthly_spending(current_user["sub"], db)
        response["text"] = format_response(
            f"This month you've spent ₹{monthly_spending} on services. Based on your patterns, you typically spend around ₹{monthly_spending * 1.1:.0f} monthly.",
            personality
        )
    
    else:
        # General conversation
        response["text"] = format_response(
            "I'm here to help with all your service needs! You can ask me to book services, check your schedule, get recommendations, or manage your preferences.",
            personality
        )
    
    return response

async def generate_proactive_suggestions(user_id: str, ai_profile: Dict, db) -> List[Dict]:
    """Generate proactive service suggestions based on user patterns"""
    
    suggestions = []
    
    # Get user's booking history
    recent_bookings = await db.bookings.find({
        "user_id": user_id,
        "created_at": {"$gte": datetime.utcnow() - timedelta(days=90)}
    }).to_list(length=100)
    
    # Pattern-based suggestions
    service_frequency = {}
    for booking in recent_bookings:
        service_type = booking.get("service_type")
        if service_type:
            service_frequency[service_type] = service_frequency.get(service_type, 0) + 1
    
    # Suggest recurring services
    for service_type, frequency in service_frequency.items():
        if frequency >= 2:  # Service used at least twice
            last_booking = max([b for b in recent_bookings if b.get("service_type") == service_type], 
                             key=lambda x: x["created_at"])
            days_since = (datetime.utcnow() - last_booking["created_at"]).days
            
            # Suggest if it's been a while
            if days_since > 30:
                suggestions.append({
                    "type": "recurring",
                    "service": service_type,
                    "reason": f"It's been {days_since} days since your last {service_type} service",
                    "confidence": 0.8,
                    "urgency": "medium" if days_since > 60 else "low"
                })
    
    # Seasonal suggestions
    current_month = datetime.utcnow().month
    seasonal_services = get_seasonal_suggestions(current_month)
    
    for service in seasonal_services:
        if service not in service_frequency:  # New service
            suggestions.append({
                "type": "seasonal",
                "service": service,
                "reason": f"Perfect time of year for {service} services",
                "confidence": 0.6,
                "urgency": "low"
            })
    
    # Limit to top 5 suggestions
    return sorted(suggestions, key=lambda x: x["confidence"], reverse=True)[:5]

async def optimize_service_schedule(services: List[Dict], preferences: Dict, ai_profile: Dict, db) -> Dict:
    """Optimize scheduling for multiple services"""
    
    optimized_schedule = {
        "services": [],
        "total_duration": 0,
        "cost_savings": 0,
        "confidence_score": 0.8
    }
    
    # Sort services by priority and dependencies
    sorted_services = sorted(services, key=lambda x: x.get("priority", 5))
    
    current_time = datetime.utcnow()
    
    for i, service in enumerate(sorted_services):
        # Calculate optimal time slot
        optimal_time = current_time + timedelta(days=i+1, hours=preferences.get("preferred_hour", 10))
        
        # Check for service dependencies
        if service.get("depends_on"):
            dependency_service = next((s for s in optimized_schedule["services"] if s["type"] == service["depends_on"]), None)
            if dependency_service:
                optimal_time = dependency_service["scheduled_time"] + timedelta(hours=2)
        
        optimized_service = {
            "type": service["type"],
            "scheduled_time": optimal_time,
            "duration": service.get("duration", 2),
            "estimated_cost": service.get("cost", 500),
            "optimization_reason": "Scheduled based on dependencies and preferences"
        }
        
        optimized_schedule["services"].append(optimized_service)
        optimized_schedule["total_duration"] += optimized_service["duration"]
    
    # Calculate potential savings from bundling
    if len(services) > 1:
        optimized_schedule["cost_savings"] = sum(s.get("cost", 500) for s in services) * 0.15  # 15% bundle discount
    
    return optimized_schedule

def detect_intent(message: str) -> str:
    """Detect user intent from message"""
    
    booking_keywords = ["book", "schedule", "appointment", "need", "want", "hire"]
    schedule_keywords = ["when", "schedule", "upcoming", "next", "calendar"]
    recommendation_keywords = ["suggest", "recommend", "what should", "advice", "help me choose"]
    budget_keywords = ["cost", "price", "budget", "spend", "money", "expensive"]
    
    if any(keyword in message for keyword in booking_keywords):
        return "booking_request"
    elif any(keyword in message for keyword in schedule_keywords):
        return "schedule_query"
    elif any(keyword in message for keyword in recommendation_keywords):
        return "recommendation_request"
    elif any(keyword in message for keyword in budget_keywords):
        return "budget_query"
    else:
        return "general"

def extract_service_type(message: str) -> Optional[str]:
    """Extract service type from message"""
    
    service_keywords = {
        "cleaning": ["clean", "cleaning", "maid", "housekeeping"],
        "plumbing": ["plumber", "plumbing", "pipe", "leak", "drain"],
        "electrical": ["electrician", "electrical", "wiring", "power", "lights"],
        "beauty": ["beauty", "facial", "makeup", "salon", "spa"],
        "fitness": ["fitness", "trainer", "gym", "workout", "exercise"],
        "gardening": ["garden", "gardening", "plants", "landscaping"]
    }
    
    for service_type, keywords in service_keywords.items():
        if any(keyword in message for keyword in keywords):
            return service_type
    
    return None

def format_response(text: str, personality: str) -> str:
    """Format response based on AI personality"""
    
    if personality == "professional":
        return f"Certainly. {text}"
    elif personality == "friendly":
        return f"Absolutely! {text} 😊"
    elif personality == "minimalist":
        return text
    else:
        return text

async def generate_smart_recommendations(user_id: str, ai_profile: Dict, db) -> List[Dict]:
    """Generate smart service recommendations"""
    
    # Get user preferences and history
    bookings = await db.bookings.find({"user_id": user_id}).to_list(length=50)
    
    recommendations = []
    
    # Add some mock intelligent recommendations
    recommendations.extend([
        {"service": "cleaning", "reason": "Due for monthly deep clean", "confidence": 0.9},
        {"service": "beauty", "reason": "Popular in your area this week", "confidence": 0.7},
        {"service": "fitness", "reason": "Matches your wellness goals", "confidence": 0.8}
    ])
    
    return recommendations

async def calculate_monthly_spending(user_id: str, db) -> float:
    """Calculate user's monthly spending on services"""
    
    start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    monthly_bookings = await db.bookings.find({
        "user_id": user_id,
        "created_at": {"$gte": start_of_month},
        "status": "completed"
    }).to_list(length=100)
    
    return sum(booking.get("amount", 0) for booking in monthly_bookings)

def get_seasonal_suggestions(month: int) -> List[str]:
    """Get seasonal service suggestions"""
    
    seasonal_map = {
        1: ["fitness", "beauty"],  # New Year
        2: ["beauty"],  # Valentine's
        3: ["cleaning", "gardening"],  # Spring
        4: ["gardening"],  # Spring
        5: ["beauty", "fitness"],  # Summer prep
        6: ["fitness"],  # Summer
        7: ["fitness"],  # Summer
        8: ["beauty"],  # Summer
        9: ["tutoring"],  # Back to school
        10: ["cleaning"],  # Pre-winter
        11: ["beauty"],  # Festival season
        12: ["cleaning", "beauty"]  # Holiday prep
    }
    
    return seasonal_map.get(month, ["cleaning"])

async def analyze_user_patterns(bookings: List[Dict], ai_profile: Dict, db) -> Dict:
    """Analyze user booking patterns for insights"""
    
    if not bookings:
        return {"message": "Not enough data for analysis"}
    
    # Time patterns
    booking_hours = [b["created_at"].hour for b in bookings]
    most_common_hour = max(set(booking_hours), key=booking_hours.count) if booking_hours else 10
    
    # Service preferences
    service_types = [b.get("service_type") for b in bookings if b.get("service_type")]
    most_used_service = max(set(service_types), key=service_types.count) if service_types else "cleaning"
    
    # Spending patterns
    amounts = [b.get("amount", 0) for b in bookings if b.get("amount")]
    avg_spending = sum(amounts) / len(amounts) if amounts else 0
    
    return {
        "preferred_booking_time": f"{most_common_hour}:00",
        "favorite_service": most_used_service,
        "average_spending": round(avg_spending, 2),
        "booking_frequency": len(bookings) / 12,  # per month
        "insights": [
            f"You prefer booking services around {most_common_hour}:00",
            f"Your go-to service is {most_used_service}",
            f"You spend an average of ₹{avg_spending:.0f} per booking"
        ]
    }

def calculate_learning_accuracy(ai_profile: Dict) -> float:
    """Calculate AI learning accuracy based on successful predictions"""
    
    # Mock calculation - in production, track prediction success
    interactions = ai_profile.get("total_interactions", 0)
    if interactions < 10:
        return 0.6  # Starting accuracy
    elif interactions < 50:
        return 0.75
    else:
        return 0.9

def generate_improvement_recommendations(insights: Dict) -> List[str]:
    """Generate recommendations for improving service experience"""
    
    recommendations = []
    
    if insights.get("average_spending", 0) > 1000:
        recommendations.append("Consider service bundles to save money")
    
    if insights.get("booking_frequency", 0) < 1:
        recommendations.append("Regular service scheduling can improve your home maintenance")
    
    recommendations.append("Enable proactive suggestions for better service timing")
    
    return recommendations

def validate_automation_rule(rule: Dict) -> bool:
    """Validate automation rule structure"""
    
    required_fields = ["trigger", "action", "service_type"]
    return all(field in rule for field in required_fields)

def get_next_execution_time(rules: List[Dict]) -> Optional[datetime]:
    """Get next execution time for automation rules"""
    
    if not rules:
        return None
    
    # Mock calculation - return next hour
    return datetime.utcnow() + timedelta(hours=1)

def calculate_learning_progress(ai_profile: Dict) -> Dict:
    """Calculate AI learning progress"""
    
    interactions = ai_profile.get("total_interactions", 0)
    
    return {
        "interactions": interactions,
        "learning_stage": "Advanced" if interactions > 100 else "Intermediate" if interactions > 20 else "Beginner",
        "accuracy": calculate_learning_accuracy(ai_profile),
        "next_milestone": 50 if interactions < 50 else 100 if interactions < 100 else 200
    }

def get_personality_note(personality: str, context: str) -> str:
    """Get personality-specific note for different contexts"""
    
    notes = {
        "professional": {
            "suggestions": "Here are my carefully analyzed recommendations:",
            "schedule": "Your optimized schedule has been prepared:",
            "general": "I have processed your request:"
        },
        "friendly": {
            "suggestions": "I've got some great ideas for you! 🌟",
            "schedule": "Let me help you organize your perfect schedule! 📅",
            "general": "Happy to help! Here's what I found:"
        },
        "minimalist": {
            "suggestions": "Recommendations:",
            "schedule": "Schedule:",
            "general": "Results:"
        }
    }
    
    return notes.get(personality, {}).get(context, "")

def generate_schedule_explanation(schedule: Dict, ai_profile: Dict) -> str:
    """Generate explanation for optimized schedule"""
    
    personality = ai_profile.get("personality", "friendly")
    service_count = len(schedule.get("services", []))
    savings = schedule.get("cost_savings", 0)
    
    if personality == "professional":
        return f"I have optimized your {service_count} services for maximum efficiency, resulting in ₹{savings:.0f} potential savings through strategic scheduling."
    elif personality == "friendly":
        return f"Great news! I've arranged your {service_count} services perfectly and found ways to save you ₹{savings:.0f}! 🎉"
    else:
        return f"{service_count} services scheduled. ₹{savings:.0f} savings."