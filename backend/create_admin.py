import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import sys

async def create_admin():
    try:
        client = AsyncIOMotorClient("mongodb://localhost:27017")
        db = client.quickserve
        
        # Check if admin exists
        existing = await db.users.find_one({"email": "admin@quickserve.com"})
        if existing:
            print("[OK] Admin user already exists!")
            print("\nLogin with:")
            print("Email: admin@quickserve.com")
            print("Password: admin123")
            client.close()
            return
        
        # Create admin user
        admin = {
            "email": "admin@quickserve.com",
            "password": "$2b$12$LKGfLcdXrjrnfZK3vbzWmOMcxGMsE025hj00DWZWdKlXPXPss1Cwq",  # admin123
            "full_name": "Admin User",
            "phone": "+91-1234567890",
            "role": "admin",
            "created_at": datetime.utcnow(),
            "verified_email": True,
            "verified_by_admin": True,
            "is_superadmin": True,
            "quickserve_credits": 1000
        }
        
        result = await db.users.insert_one(admin)
        print(f"[OK] Admin user created successfully!")
        print(f"User ID: {result.inserted_id}")
        print("\nLogin Details:")
        print("Email: admin@quickserve.com")
        print("Password: admin123")
        
        client.close()
    except Exception as e:
        print(f"[ERROR] Failed to create admin: {e}")
        print("\nMake sure MongoDB is running!")
        print("Run: net start MongoDB")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(create_admin())
