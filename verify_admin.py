import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
import os

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def verify_admin():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["quickserve"]
    
    # Check admin@demo.com
    admin = await db.users.find_one({"email": "admin@demo.com"})
    print(f"Admin found: {bool(admin)}")
    if admin:
        print(f"Admin role: {admin.get('role')}")
        print(f"Admin details: {admin}")
        
        # Verify password
        password_to_check = "password123"
        hashed = admin.get("password") or admin.get("password_hash")
        if hashed:
            is_correct = pwd_context.verify(password_to_check, hashed)
            print(f"Password 'password123' is correct: {is_correct}")
        else:
            print("No password found for admin.")
            
        # Update admin to be sure
        await db.users.update_one(
            {"email": "admin@demo.com"},
            {"$set": {
                "role": "admin",
                "password": pwd_context.hash("password123"),
                "is_superadmin": True,
                "verified_by_admin": True,
                "verified_email": True
            }}
        )
        print("Admin user updated/fixed.")
    else:
        # Create admin
        await db.users.insert_one({
            "email": "admin@demo.com",
            "password": pwd_context.hash("password123"),
            "full_name": "Demo Admin",
            "role": "admin",
            "is_superadmin": True,
            "verified_by_admin": True,
            "verified_email": True,
            "created_at": "2024-01-01T00:00:00"
        })
        print("Admin user created.")

if __name__ == "__main__":
    asyncio.run(verify_admin())
