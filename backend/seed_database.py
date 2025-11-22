from backend.database import get_db
import asyncio

async def seed_database():
    """Seed database with sample data"""
    db = get_db()
    
    # Sample facilities
    facilities = [
        {
            "id": "facility_001",
            "name": "Karachi General Hospital",
            "type": "hospital",
            "location": {"lat": 24.8607, "lng": 67.0011},
            "address": "Karachi, Pakistan",
            "services": ["emergency", "general", "pediatric"],
            "contact": "+92-21-99261300"
        },
        {
            "id": "facility_002", 
            "name": "Lahore BHU Center",
            "type": "bhu",
            "location": {"lat": 31.5204, "lng": 74.3587},
            "address": "Lahore, Pakistan",
            "services": ["general", "maternal"],
            "contact": "+92-42-99261300"
        }
    ]
    
    # Sample medicines
    medicines = [
        {
            "id": "med_001",
            "name": "Paracetamol",
            "generic_name": "Acetaminophen",
            "category": "analgesic",
            "stock": 100
        },
        {
            "id": "med_002",
            "name": "Amoxicillin", 
            "generic_name": "Amoxicillin",
            "category": "antibiotic",
            "stock": 50
        }
    ]
    
    # Add facilities
    for facility in facilities:
        await db.add_document("facilities", facility)
    
    # Add medicines  
    for medicine in medicines:
        await db.add_document("medicines", medicine)
