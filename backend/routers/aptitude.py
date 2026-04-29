from fastapi import APIRouter, HTTPException
from typing import List, Optional
import random

router = APIRouter(prefix="/aptitude", tags=["Provider Aptitude"])

# Centralized Aptitude Questions
APTITUDE_QUESTIONS = {
    "plumbing": [
        {"id": 1, "question": "How do you clear a major blockage in a main sewer line?", "options": ["Use a plunger", "Use a plumbing snake/auger", "Wait for it to clear", "Pour hot water"], "answer": 1},
        {"id": 2, "question": "What is the standard height for a residential kitchen sink?", "options": ["24 inches", "30 inches", "36 inches", "42 inches"], "answer": 2},
        {"id": 3, "question": "Which pipe material is most resistant to corrosion?", "options": ["Galvanized steel", "PVC", "Copper", "Cast iron"], "answer": 1},
        {"id": 4, "question": "What tool is used to tighten a compression nut?", "options": ["Pipe wrench", "Adjustable wrench", "Allen wrench", "Pliers"], "answer": 1},
        {"id": 5, "question": "A 'trap' in plumbing is designed to...", "options": ["Catch hair", "Prevent sewer gases from entering", "Increase water pressure", "Save water"], "answer": 1},
        {"id": 6, "question": "What is the primary function of a vent stack?", "options": ["Drain water", "Regulate air pressure", "Catch debris", "Support pipes"], "answer": 1},
        {"id": 7, "question": "Which valve type is best for fine flow control?", "options": ["Gate valve", "Ball valve", "Globe valve", "Check valve"], "answer": 2}
    ],
    "electrical": [
        {"id": 1, "question": "What is the unit of electrical resistance?", "options": ["Watt", "Volt", "Ampere", "Ohm"], "answer": 3},
        {"id": 2, "question": "Before working on an outlet, you MUST...", "options": ["Wear gloves", "Turn off the breaker", "Check the voltage", "Ask the owner"], "answer": 1},
        {"id": 3, "question": "Which wire is typically the ground wire in the US?", "options": ["Black", "White", "Green or Bare", "Red"], "answer": 2},
        {"id": 4, "question": "A multi-meter is used to measure...", "options": ["Voltage only", "Current only", "Resistance only", "All of the above"], "answer": 3},
        {"id": 5, "question": "What triggers a GFCI outlet?", "options": ["Overload", "Ground fault", "Short circuit", "Low voltage"], "answer": 1},
        {"id": 6, "question": "What is the purpose of a circuit breaker?", "options": ["Increase voltage", "Protect from overcurrent", "Store electricity", "Switch AC to DC"], "answer": 1},
        {"id": 7, "question": "Which gauge wire is thicker, 10 or 14?", "options": ["10 gauge", "14 gauge", "They are the same", "Depends on material"], "answer": 0}
    ],
    "painter": [
        {"id": 1, "question": "What is the best primer for raw drywall?", "options": ["Oil-based", "PVA Primer", "Latex Primer", "No primer needed"], "answer": 1},
        {"id": 2, "question": "How do you remove latex paint from a brush?", "options": ["Turpentine", "Soap and Water", "Paint Thinner", "Alcohol"], "answer": 1},
        {"id": 3, "question": "A 'satin' finish has more sheen than...", "options": ["Gloss", "Eggshell", "Semi-gloss", "High-gloss"], "answer": 1},
        {"id": 4, "question": "Which tape is best for sharp painting lines?", "options": ["Duct Tape", "Masking Tape", "Painter's Blue Tape", "Clear Tape"], "answer": 2},
        {"id": 5, "question": "Why should you sand between paint coats?", "options": ["To change the color", "For better adhesion", "To save paint", "To make it dry faster"], "answer": 1},
        {"id": 6, "question": "What does 'flashing' mean in painting?", "options": ["Drying too fast", "Uneven gloss levels", "Paint peeling", "Using a flashlight"], "answer": 1},
        {"id": 7, "question": "How long should you wait for fresh plaster to dry before painting?", "options": ["24 hours", "3 days", "4 weeks or more", "Immediately"], "answer": 2}
    ],
    "cleaning": [
        {"id": 1, "question": "Which chemical should NEVER be mixed with bleach?", "options": ["Soap", "Ammonia", "Water", "Salt"], "answer": 1},
        {"id": 2, "question": "What is the best material to use for streak-free windows?", "options": ["Paper towel", "Microfiber cloth", "Sponge", "T-shirt"], "answer": 1},
        {"id": 3, "question": "To remove hard water stains, you should use...", "options": ["Baking soda", "Vinegar (Acidic)", "Bleach", "Pine oil"], "answer": 1},
        {"id": 4, "question": "How often should you sanitize high-touch areas?", "options": ["Once a week", "Daily", "Once a month", "Never"], "answer": 1},
        {"id": 5, "question": "What is the proper way to mop a floor?", "options": ["Randomly", "Back and forth", "Figure-8 pattern", "Circular"], "answer": 2},
        {"id": 6, "question": "What is 'cross-contamination' in cleaning?", "options": ["Mixing chemicals", "Spreading germs between areas", "Cleaning with two mops", "Diluting products"], "answer": 1},
        {"id": 7, "question": "Which surface is safe for undiluted vinegar?", "options": ["Marble", "Granite", "Ceramic tile", "Hardwood"], "answer": 2}
    ],
    "beauty": [
        {"id": 1, "question": "Before applying makeup, it is essential to...", "options": ["Skip moisturizer", "Cleanse and prep the skin", "Apply powder first", "Use cold water"], "answer": 1},
        {"id": 2, "question": "What is the correct way to sanitize makeup brushes?", "options": ["Rinse with hot water", "Use a dedicated brush cleanser or alcohol", "Use dish soap only", "Wipe them with a towel"], "answer": 1},
        {"id": 3, "question": "Which ingredient is a common allergen in skincare?", "options": ["Hyaluronic acid", "Fragrance/Parfum", "Aloe vera", "Glycerin"], "answer": 1},
        {"id": 4, "question": "When styling hair with heat, you should always...", "options": ["Apply heat protectant spray", "Style it while dripping wet", "Turn iron to max heat", "Skip conditioner"], "answer": 0},
        {"id": 5, "question": "A patch test is used to...", "options": ["Check skin tone", "Test for allergic reactions", "Estimate product duration", "Hydrate the skin"], "answer": 1}
    ],
    "fitness": [
        {"id": 1, "question": "Which of these is a compound exercise?", "options": ["Bicep curl", "Leg extension", "Squat", "Calf raise"], "answer": 2},
        {"id": 2, "question": "What is the primary muscle targeted during a standard push-up?", "options": ["Latissimus dorsi", "Pectoralis major", "Hamstrings", "Glutes"], "answer": 1},
        {"id": 3, "question": "How do you treat a minor muscle sprain immediately after injury?", "options": ["RICE (Rest, Ice, Compression, Elevation)", "Apply heat immediately", "Stretch it vigorously", "Ignore it"], "answer": 0},
        {"id": 4, "question": "What is an appropriate rest time between high-intensity sets?", "options": ["10 seconds", "1-3 minutes", "10 minutes", "No rest"], "answer": 1},
        {"id": 5, "question": "A dynamic warmup should consist of...", "options": ["Holding stretches for 60s", "Active movements matching the workout", "Sleeping", "Lifting max weight immediately"], "answer": 1}
    ],
    "delivery": [
        {"id": 1, "question": "What is the most important rule when handling fragile packages?", "options": ["Stack them at the bottom", "Secure them and drive smoothly", "Throw them to save time", "Leave them upside down"], "answer": 1},
        {"id": 2, "question": "If a customer is not home to sign for a high-value package, you should...", "options": ["Leave it at the door", "Ask a random neighbor to sign", "Follow standard redelivery procedure", "Keep it for yourself"], "answer": 2},
        {"id": 3, "question": "How should you lift heavy boxes to prevent back injury?", "options": ["Bend your back, keep legs straight", "Bend at the knees and keep your back straight", "Lift rapidly", "Hold it far away from your body"], "answer": 1},
        {"id": 4, "question": "When navigating a new route, the best practice is...", "options": ["Speed to save time", "Use GPS and pre-plan stops", "Guess the way", "Ask pedestrians at every turn"], "answer": 1},
        {"id": 5, "question": "Upon delivering food items, ensuring hygiene means...", "options": ["Opening the bag to check", "Using insulated, clean thermal bags", "Placing it on the bare ground", "Eating the fries"], "answer": 1}
    ],
    "repair": [
        {"id": 1, "question": "When diagnosing a broken appliance, what is the first step?", "options": ["Replace the motor", "Check the power supply/cord", "Take the entire thing apart", "Hit it with a hammer"], "answer": 1},
        {"id": 2, "question": "What does HVAC stand for?", "options": ["Heating, Ventilation, and Air Conditioning", "High Voltage Alternating Current", "Home Vacuum And Cleaning", "Heat Valve And Control"], "answer": 0},
        {"id": 3, "question": "WD-40 is primarily used as a...", "options": ["Permanent glue", "Water displacer and light lubricant", "Electrical insulator", "Paint thinner"], "answer": 1},
        {"id": 4, "question": "To loosen a rusted bolt safely, you should...", "options": ["Apply penetrating oil and wait", "Use extreme force immediately", "Cut it off instantly", "Heat it until it melts"], "answer": 0},
        {"id": 5, "question": "What safety gear is essential when using a grinder?", "options": ["Earplugs only", "Safety glasses and gloves", "A hat", "None"], "answer": 1}
    ],
    "tutoring": [
        {"id": 1, "question": "If a student repeatedly struggles with a concept, the best approach is to...", "options": ["Tell them to study harder", "Explain it exactly the same way louder", "Try a different teaching method or analogy", "Skip the topic entirely"], "answer": 2},
        {"id": 2, "question": "What is the primary purpose of formative assessment?", "options": ["Assigning a final grade", "Tracking ongoing student progress to adapt teaching", "Punishing the student", "Fulfilling legal requirements"], "answer": 1},
        {"id": 3, "question": "Active learning involves...", "options": ["The student listening silently for hours", "Engaging the student in problem-solving and discussion", "The tutor doing all the talking", "Reading from a textbook only"], "answer": 1},
        {"id": 4, "question": "When setting goals for a tutoring session, they should be...", "options": ["Vague and general", "SMART (Specific, Measurable, Achievable, Relevant, Time-bound)", "Impossible to achieve", "Decided entirely by the parent"], "answer": 1},
        {"id": 5, "question": "How should you handle a situation where you don't know the answer to a student's question?", "options": ["Make something up", "Ignore the question", "Admit you don't know and look it up together", "Tell them it won't be on the test"], "answer": 2}
    ]
}

@router.get("/questions/{category}")
async def get_questions(category: str):
    """
    Fetch 5 randomized questions for a given category.
    Defaults to 'painter' if category not found.
    """
    normalized_cat = category.lower()
    if normalized_cat not in APTITUDE_QUESTIONS:
        # Fallback to general or most common categories
        normalized_cat = "painter" 
    
    questions = APTITUDE_QUESTIONS[normalized_cat]
    # Return a random sample of 5 questions
    sample_size = min(len(questions), 5)
    selected = random.sample(questions, sample_size)
    
    return {
        "category": normalized_cat,
        "questions": selected
    }
