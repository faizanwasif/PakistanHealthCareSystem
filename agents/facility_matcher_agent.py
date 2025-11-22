import logging
from typing import Dict, Any, List, Optional
from agents.base_agent import BaseAgent
from backend.models import FacilityRecommendation, UrgencyLevel
from backend.database import get_db
from backend.mcp_client import mcp_client
import math
import os
import json

logger = logging.getLogger(__name__)

class FacilityMatcherAgent(BaseAgent):
    def __init__(self):
        system_prompt = """You are a facility matching agent for Pakistan's healthcare system.
        You find the optimal healthcare facility based on multiple factors.
        
        Your responsibilities:
        - Match facilities based on location, services, and availability
        - Check medicine inventory at facilities
        - Consider doctor specialization
        - Factor in wait times and distance
        - Prioritize based on urgency level
        - Use Google Maps API to find real-time nearby hospitals
        
        Always provide the best match with clear reasoning."""
        
        super().__init__(
            agent_id="facility_matcher_agent",
            capabilities=["facility_search", "medicine_inventory_check", "distance_calculation", "google_maps_search"],
            system_prompt=system_prompt
        )
        
        # Cached facility data for offline mode
        self.facility_cache = []
        self.use_google_maps = os.getenv("USE_GOOGLE_MAPS", "true").lower() == "true"
    
    async def process(self, input_data: Dict[str, Any]) -> FacilityRecommendation:
        """Find optimal facility for citizen"""
        try:
            citizen_location = input_data.get("citizen_location", {})
            urgency_level = input_data.get("urgency_level", UrgencyLevel.MEDIUM)
            required_services = input_data.get("required_services", [])
            required_medicines = input_data.get("required_medicines", [])
            sehat_card_active = input_data.get("sehat_card_active", False)
            conversation_id = input_data.get("conversation_id", "")
            
            logger.info(f"Finding facility for location: {citizen_location}")
            
            # Get nearby facilities
            facilities = await self._get_nearby_facilities(
                citizen_location,
                max_distance_km=15 if urgency_level == UrgencyLevel.HIGH else 25
            )
            
            # Filter by Sehat Card if applicable
            if sehat_card_active:
                facilities = [f for f in facilities if f.get("sehat_card_accepted", False)]
            
            # Score and rank facilities
            scored_facilities = await self._score_facilities(
                facilities,
                citizen_location,
                required_services,
                required_medicines,
                urgency_level
            )
            
            if not scored_facilities:
                raise ValueError("No suitable facilities found")
            
            # Select best facility
            best_facility = scored_facilities[0]
            
            # Check medicine availability
            medicine_availability = await self._check_medicine_availability(
                best_facility["facility_id"],
                required_medicines
            )
            
            # Create decision trace
            decision = await self.make_decision(
                decision_name=f"recommend_facility_{best_facility['facility_id']}",
                inputs=["citizen_location", "facility_database", "medicine_inventory", "urgency_level"],
                alternatives=[f["facility_id"] for f in scored_facilities[:3]],
                context={
                    "conversation_id": conversation_id,
                    "selected_facility": best_facility["facility_id"],
                    "distance": best_facility["distance_km"]
                }
            )
            
            result = FacilityRecommendation(
                facility_id=best_facility["facility_id"],
                facility_name=best_facility["name"],
                distance_km=best_facility["distance_km"],
                available_services=best_facility.get("services", []),
                medicine_availability=medicine_availability,
                estimated_wait_time=best_facility.get("estimated_wait_time"),
                reasoning=decision.reasoning
            )
            
            logger.info(f"Recommended facility: {result.facility_name} ({result.distance_km}km)")
            return result
            
        except Exception as e:
            logger.error(f"Error in facility matching: {e}")
            raise
    
    async def _get_nearby_facilities_from_google_maps(
        self,
        location: Dict[str, float],
        max_distance_km: float = 20
    ) -> List[Dict]:
        """Get nearby hospitals using Google Maps MCP server"""
        try:
            # This would call the Google Maps MCP server
            # For now, we'll simulate the MCP call structure
            logger.info(f"Searching Google Maps for hospitals near {location}")
            
            # In a real MCP implementation, this would be:
            # result = await mcp_client.call_tool("google-maps", "search_places", {
            #     "query": "hospital",
            #     "location": f"{location['lat']},{location['lng']}",
            #     "radius": max_distance_km * 1000  # Convert km to meters
            # })
            
            # For demonstration, we'll use a placeholder that shows the structure
            # You'll need to implement the actual MCP client call
            facilities = await self._call_google_maps_mcp(
                location=location,
                search_type="hospital",
                radius_km=max_distance_km
            )
            
            return facilities
            
        except Exception as e:
            logger.error(f"Error fetching from Google Maps: {e}")
            logger.info("Falling back to database facilities")
            return await self._get_nearby_facilities_from_db(location, max_distance_km)
    
    async def _call_google_maps_mcp(
        self,
        location: Dict[str, float],
        search_type: str = "hospital",
        radius_km: float = 20
    ) -> List[Dict]:
        """Call Google Maps MCP client to find nearby hospitals"""
        try:
            logger.info(f"Calling Google Maps API for {search_type} within {radius_km}km")
            
            # Use the MCP client to search for nearby hospitals
            facilities = await mcp_client.search_nearby_hospitals(
                latitude=location.get("lat", 0),
                longitude=location.get("lng", 0),
                radius_km=radius_km,
                keyword=search_type
            )
            
            if facilities:
                logger.info(f"Found {len(facilities)} facilities from Google Maps")
            else:
                logger.warning("No facilities found from Google Maps, will fall back to database")
            
            return facilities
            
        except Exception as e:
            logger.error(f"Error calling Google Maps MCP: {e}")
            return []
    
    async def _get_nearby_facilities_from_db(
        self,
        location: Dict[str, float],
        max_distance_km: float = 20
    ) -> List[Dict]:
        """Get facilities from database (fallback method)"""
        try:
            db = get_db()
            
            # First, try to get all facilities and calculate distances manually
            # This is more reliable than $near for initial setup
            all_facilities = await db.facilities.find({}).to_list(length=100)
            
            if not all_facilities:
                logger.warning("No facilities found in database")
                return []
            
            # Calculate distances for all facilities
            facilities_with_distance = []
            for facility in all_facilities:
                # Extract coordinates from GeoJSON format
                if "location" in facility and "coordinates" in facility["location"]:
                    coords = facility["location"]["coordinates"]
                    facility_location = {"lng": coords[0], "lat": coords[1]}
                else:
                    continue
                
                distance = self._calculate_distance(location, facility_location)
                
                if distance <= max_distance_km:
                    facility["distance_km"] = distance
                    facilities_with_distance.append(facility)
            
            # Sort by distance
            facilities_with_distance.sort(key=lambda x: x["distance_km"])
            
            return facilities_with_distance[:10]
            
        except Exception as e:
            logger.error(f"Error fetching nearby facilities: {e}")
            # Return cached facilities in offline mode
            if self.facility_cache:
                return self.facility_cache[:5]
            return []
    
    async def _get_nearby_facilities(
        self,
        location: Dict[str, float],
        max_distance_km: float = 20
    ) -> List[Dict]:
        """Get facilities within distance - uses Google Maps or falls back to DB"""
        if self.use_google_maps:
            logger.info("Using Google Maps MCP for facility search")
            return await self._get_nearby_facilities_from_google_maps(location, max_distance_km)
        else:
            logger.info("Using database for facility search")
            return await self._get_nearby_facilities_from_db(location, max_distance_km)
    
    def _calculate_distance(self, loc1: Dict[str, float], loc2: Dict[str, float]) -> float:
        """Calculate distance between two coordinates using Haversine formula"""
        lat1, lng1 = loc1.get("lat", 0), loc1.get("lng", 0)
        lat2, lng2 = loc2.get("lat", 0), loc2.get("lng", 0)
        
        R = 6371  # Earth's radius in km
        
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)
        
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlng / 2) ** 2)
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = R * c
        
        return round(distance, 2)
    
    async def _score_facilities(
        self,
        facilities: List[Dict],
        citizen_location: Dict[str, float],
        required_services: List[str],
        required_medicines: List[str],
        urgency: UrgencyLevel
    ) -> List[Dict]:
        """Score and rank facilities"""
        scored = []
        
        for facility in facilities:
            score = 0
            
            # Distance score (closer is better)
            distance = facility.get("distance_km", 999)
            if distance < 2:
                score += 50
            elif distance < 5:
                score += 30
            elif distance < 10:
                score += 10
            
            # Service availability
            facility_services = facility.get("services", [])
            matching_services = len(set(required_services) & set(facility_services))
            score += matching_services * 20
            
            # Urgency factor
            if urgency == UrgencyLevel.HIGH:
                # Prioritize distance for emergencies
                score += (10 - distance) * 5
            
            facility["score"] = score
            scored.append(facility)
        
        # Sort by score descending
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored
    
    async def _check_medicine_availability(
        self,
        facility_id: str,
        medicines: List[str]
    ) -> Dict[str, bool]:
        """Check medicine availability at facility"""
        try:
            db = get_db()
            availability = {}
            
            for medicine in medicines:
                inventory = await db.medicine_inventory.find_one({
                    "facility_id": facility_id,
                    "medicine_name": {"$regex": medicine, "$options": "i"}
                })
                
                availability[medicine] = inventory and inventory.get("stock_count", 0) > 0
            
            return availability
            
        except Exception as e:
            logger.error(f"Error checking medicine availability: {e}")
            return {med: False for med in medicines}
