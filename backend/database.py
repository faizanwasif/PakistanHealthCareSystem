import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from config.config import config
import logging
import os
from typing import Dict, List, Any, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class Database:
    db = None
    executor = ThreadPoolExecutor(max_workers=10)

async def connect_db():
    try:
        # Initialize Firebase Admin SDK
        if not firebase_admin._apps:
            # Get the project root directory (parent of backend)
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            creds_path = os.path.join(project_root, config.FIREBASE_CREDENTIALS_PATH)
            
            if os.path.exists(creds_path):
                cred = credentials.Certificate(creds_path)
                firebase_admin.initialize_app(cred)
                logger.info(f"Using Firebase credentials from: {creds_path}")
            else:
                logger.error(f"Firebase credentials file not found at: {creds_path}")
                raise Exception(f"Firebase credentials file not found at: {creds_path}")
        
        Database.db = firestore.client()
        logger.info("Connected to Firebase Firestore")
        
        # Create initial collections and seed data if needed
        await _initialize_collections()
        
    except Exception as e:
        logger.error(f"Failed to connect to Firebase: {e}")
        raise

async def close_db():
    if Database.db:
        logger.info("Firebase connection closed")

def get_db():
    return Database.db

async def _initialize_collections():
    """Initialize Firestore collections with sample data if empty"""
    try:
        # Check if users collection exists and has data
        users_ref = Database.db.collection('users')
        users = await _run_async(users_ref.limit(1).get)
        
        if not users:
            logger.info("Initializing Firebase collections with sample data...")
            await _seed_sample_data()
    except Exception as e:
        logger.warning(f"Could not initialize collections: {e}")

async def _seed_sample_data():
    """Seed Firebase with sample data"""
    try:
        # Sample facilities
        facilities_data = [
            {
                "facility_id": "fac_001",
                "name": "Karachi General Hospital",
                "type": "hospital",
                "location": {"lat": 24.8607, "lng": 67.0011},
                "services": ["emergency", "cardiology", "pediatrics"],
                "doctors": [{"name": "Dr. Ahmed", "specialty": "cardiology"}],
                "timings": "24/7",
                "sehat_card_accepted": True
            },
            {
                "facility_id": "fac_002", 
                "name": "Lahore Medical Center",
                "type": "clinic",
                "location": {"lat": 31.5204, "lng": 74.3587},
                "services": ["general", "dermatology"],
                "doctors": [{"name": "Dr. Fatima", "specialty": "general"}],
                "timings": "9 AM - 6 PM",
                "sehat_card_accepted": True
            }
        ]
        
        for facility in facilities_data:
            await _run_async(
                Database.db.collection('facilities').document(facility['facility_id']).set,
                facility
            )
        
        logger.info("Sample data seeded successfully")
    except Exception as e:
        logger.error(f"Error seeding sample data: {e}")

async def _run_async(func, *args, **kwargs):
    """Run synchronous Firestore operations asynchronously"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(Database.executor, func, *args, **kwargs)

# Firebase helper functions to replace MongoDB operations
class FirebaseCollection:
    def __init__(self, collection_name: str):
        self.collection_name = collection_name
        self.ref = Database.db.collection(collection_name)
        self._query_ref = self.ref
        self._limit = None
        self._order_by = None
    
    async def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find one document matching query"""
        try:
            docs = await self._execute_query(query, limit=1)
            return docs[0] if docs else None
        except Exception as e:
            logger.error(f"Error in find_one: {e}")
            return None
    
    def find(self, query: Dict[str, Any] = None):
        """Find documents matching query - returns self for chaining"""
        self._query = query or {}
        return self
    
    def sort(self, field: str, direction: int = 1):
        """Sort results - returns self for chaining"""
        direction_str = 'ASCENDING' if direction == 1 else 'DESCENDING'
        self._order_by = (field, direction_str)
        return self
    
    def limit(self, count: int):
        """Limit results - returns self for chaining"""
        self._limit = count
        return self
    
    async def to_list(self, length: int = None):
        """Execute query and return list of documents"""
        return await self._execute_query(self._query, self._limit or length, self._order_by)
    
    async def insert_one(self, document: Dict[str, Any]) -> str:
        """Insert one document"""
        try:
            doc_ref = await _run_async(self.ref.add, document)
            return doc_ref[1].id
        except Exception as e:
            logger.error(f"Error in insert_one: {e}")
            raise
    
    async def update_one(self, query: Dict[str, Any], update: Dict[str, Any]) -> bool:
        """Update one document"""
        try:
            docs = await self._execute_query(query, limit=1)
            if docs:
                doc_id = docs[0]['_id']
                update_data = update.get('$set', update)
                await _run_async(self.ref.document(doc_id).update, update_data)
                return True
            return False
        except Exception as e:
            logger.error(f"Error in update_one: {e}")
            return False
    
    async def update_many(self, query: Dict[str, Any], update: Dict[str, Any]) -> int:
        """Update multiple documents"""
        try:
            docs = await self._execute_query(query)
            count = 0
            update_data = update.get('$set', update)
            for doc in docs:
                doc_id = doc['_id']
                await _run_async(self.ref.document(doc_id).update, update_data)
                count += 1
            return count
        except Exception as e:
            logger.error(f"Error in update_many: {e}")
            return 0
    
    async def count_documents(self, query: Dict[str, Any] = None) -> int:
        """Count documents matching query"""
        try:
            docs = await self._execute_query(query or {})
            return len(docs)
        except Exception as e:
            logger.error(f"Error in count_documents: {e}")
            return 0
    
    async def _execute_query(self, query: Dict[str, Any], limit: int = None, order_by: tuple = None) -> List[Dict[str, Any]]:
        """Execute query and return documents"""
        try:
            query_ref = self.ref
            
            # Apply filters
            for field, value in query.items():
                if field != '_id':
                    query_ref = query_ref.where(filter=FieldFilter(field, '==', value))
            
            # Apply ordering
            if order_by:
                field, direction = order_by
                from google.cloud.firestore import Query
                direction_enum = Query.ASCENDING if direction == 'ASCENDING' else Query.DESCENDING
                query_ref = query_ref.order_by(field, direction=direction_enum)
            
            # Apply limit
            if limit:
                query_ref = query_ref.limit(limit)
            
            docs = await _run_async(query_ref.get)
            
            results = []
            for doc in docs:
                data = doc.to_dict()
                data['_id'] = doc.id
                results.append(data)
            
            return results
        except Exception as e:
            logger.error(f"Error in _execute_query: {e}")
            return []

# Create collection instances to mimic MongoDB collections
class FirebaseDB:
    def __init__(self):
        self.users = FirebaseCollection('users')
        self.citizens = FirebaseCollection('citizens')
        self.facilities = FirebaseCollection('facilities')
        self.conversations = FirebaseCollection('conversations')
        self.notifications = FirebaseCollection('notifications')
        self.sehat_card_applications = FirebaseCollection('sehat_card_applications')
        self.agent_decisions = FirebaseCollection('agent_decisions')
        self.follow_ups = FirebaseCollection('follow_ups')
        self.mcp_messages = FirebaseCollection('mcp_messages')

# Override get_db to return Firebase collections
def get_db():
    if Database.db is None:
        logger.error("Database not connected - cannot proceed")
        raise Exception("Database not connected - please restart the server")
    return Database.db
