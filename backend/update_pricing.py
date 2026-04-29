# -*- coding: utf-8 -*-
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import random

MONGODB_URL = "mongodb://localhost:27017"
DATABASE_NAME = "quickserve"

async def update_pricing():
    try:
        client = AsyncIOMotorClient(MONGODB_URL)
        db = client[DATABASE_NAME]
        
        print("=" * 50)
        print("  Updating Service Pricing")
        print("=" * 50)
        
        # Get all services
        services = await db.services.find({}).to_list(length=None)
        print(f"\nFound {len(services)} services to update")
        
        updated_count = 0
        for service in services:
            # Generate reasonable pricing based on category
            category = service.get('category', '').lower()
            
            # Base price ranges by category
            if 'tutor' in category or 'fitness' in category:
                base_price = random.randint(300, 600)
            elif 'beauty' in category or 'salon' in category:
                base_price = random.randint(400, 800)
            elif 'plumb' in category or 'electric' in category or 'repair' in category:
                base_price = random.randint(350, 700)
            elif 'clean' in category:
                base_price = random.randint(300, 500)
            elif 'delivery' in category:
                base_price = random.randint(200, 400)
            else:
                base_price = random.randint(300, 800)
            
            # Add small variation
            price_per_hour = base_price + random.randint(-50, 100)
            
            # Ensure minimum 200 and maximum 1000 for base pricing
            price_per_hour = max(200, min(1000, price_per_hour))
            
            # Update the service
            await db.services.update_one(
                {"_id": service["_id"]},
                {"$set": {"price_per_hour": price_per_hour}}
            )
            updated_count += 1
        
        print(f"\nUpdated {updated_count} services")
        print(f"  Price range: Rs.200 - Rs.1000 per hour")
        print(f"  (Distance-based pricing will add up to Rs.1000 more)")
        
        print("\n" + "=" * 50)
        print("  Pricing update complete!")
        print("=" * 50)
        
        client.close()
        
    except Exception as e:
        print(f"\nError: {e}")
        print("Make sure MongoDB is running on localhost:27017")

if __name__ == "__main__":
    asyncio.run(update_pricing())
