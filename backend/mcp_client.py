"""
MCP Client for Google Maps MCP Server Integration
"""
import logging
import aiohttp
import json
from typing import Dict, Any, List, Optional
import os

logger = logging.getLogger(__name__)

class MCPClient:
    """Client for communicating with Google Maps MCP Server"""
    
    def __init__(self):
        self.mcp_server_url = os.getenv("MCP_GOOGLE_MAPS_URL", "http://localhost:3000/mcp")
        self.google_maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        self.session = None
        
        if not self.google_maps_api_key:
            logger.warning("Google Maps API key not configured. Please set GOOGLE_MAPS_API_KEY in .env")
    
    async def _get_session(self):
        """Get or create aiohttp session"""
        if self.session is None:
            headers = {}
            if self.google_maps_api_key:
                headers["X-Google-Maps-API-Key"] = self.google_maps_api_key
            
            self.session = aiohttp.ClientSession(
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self.session
    
    async def _call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Call MCP server tool"""
        try:
            session = await self._get_session()
            
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
            
            async with session.post(self.mcp_server_url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    if "result" in data:
                        return data["result"]
                    elif "error" in data:
                        logger.error(f"MCP server error: {data['error']}")
                        return None
                else:
                    logger.error(f"HTTP error {response.status} calling MCP server")
                    return None
                    
        except Exception as e:
            logger.error(f"Error calling MCP tool {tool_name}: {e}")
            return None
    
    async def search_nearby_hospitals(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = 20,
        keyword: str = "hospital"
    ) -> List[Dict[str, Any]]:
        """Search for nearby hospitals using MCP Google Maps server"""
        try:
            arguments = {
                "location": f"{latitude},{longitude}",
                "radius": radius_km * 1000,  # Convert km to meters
                "keyword": keyword,
                "type": "hospital"
            }
            
            result = await self._call_mcp_tool("search_nearby", arguments)
            
            if not result:
                logger.warning("No results from MCP search_nearby")
                return []
            
            facilities = []
            places = result.get("content", [])
            
            if isinstance(places, str):
                # Parse JSON string if needed
                try:
                    places = json.loads(places)
                except:
                    logger.error("Failed to parse MCP response")
                    return []
            
            for place in places[:10]:  # Limit to top 10
                if isinstance(place, dict):
                    facility = {
                        "facility_id": place.get("place_id", ""),
                        "name": place.get("name", ""),
                        "location": {
                            "type": "Point",
                            "coordinates": [
                                place.get("geometry", {}).get("location", {}).get("lng", 0),
                                place.get("geometry", {}).get("location", {}).get("lat", 0)
                            ]
                        },
                        "distance_km": self._calculate_distance(
                            latitude, longitude,
                            place.get("geometry", {}).get("location", {}).get("lat", 0),
                            place.get("geometry", {}).get("location", {}).get("lng", 0)
                        ),
                        "address": place.get("vicinity", ""),
                        "rating": place.get("rating", 0),
                        "user_ratings_total": place.get("user_ratings_total", 0),
                        "types": place.get("types", []),
                        "services": self._extract_services(place.get("types", [])),
                        "sehat_card_accepted": False,
                        "is_open": place.get("opening_hours", {}).get("open_now", None),
                        "source": "mcp_google_maps"
                    }
                    facilities.append(facility)
            
            logger.info(f"Found {len(facilities)} hospitals from MCP Google Maps")
            return facilities
            
        except Exception as e:
            logger.error(f"Error in search_nearby_hospitals: {e}")
            return []
    
    async def get_place_details(self, place_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed place information using MCP server"""
        try:
            arguments = {
                "place_id": place_id,
                "fields": "name,formatted_address,formatted_phone_number,opening_hours,rating,reviews,website"
            }
            
            result = await self._call_mcp_tool("get_place_details", arguments)
            
            if result and "content" in result:
                content = result["content"]
                if isinstance(content, str):
                    try:
                        return json.loads(content)
                    except:
                        return {"raw_content": content}
                return content
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting place details: {e}")
            return None
    
    async def get_directions(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        mode: str = "driving"
    ) -> Optional[Dict[str, Any]]:
        """Get directions using MCP server"""
        try:
            arguments = {
                "origin": f"{origin_lat},{origin_lng}",
                "destination": f"{dest_lat},{dest_lng}",
                "mode": mode
            }
            
            result = await self._call_mcp_tool("maps_directions", arguments)
            
            if result and "content" in result:
                content = result["content"]
                if isinstance(content, str):
                    try:
                        directions_data = json.loads(content)
                        if directions_data.get("routes"):
                            route = directions_data["routes"][0]
                            leg = route["legs"][0]
                            
                            return {
                                "distance_km": leg["distance"]["value"] / 1000,
                                "distance_text": leg["distance"]["text"],
                                "duration_minutes": leg["duration"]["value"] / 60,
                                "duration_text": leg["duration"]["text"],
                                "start_address": leg["start_address"],
                                "end_address": leg["end_address"]
                            }
                    except:
                        return {"raw_content": content}
                return content
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting directions: {e}")
            return None
    
    async def geocode_address(self, address: str) -> Optional[Dict[str, Any]]:
        """Convert address to coordinates using MCP server"""
        try:
            arguments = {"address": address}
            result = await self._call_mcp_tool("maps_geocode", arguments)
            
            if result and "content" in result:
                content = result["content"]
                if isinstance(content, str):
                    try:
                        return json.loads(content)
                    except:
                        return {"raw_content": content}
                return content
            
            return None
            
        except Exception as e:
            logger.error(f"Error geocoding address: {e}")
            return None
    
    def _calculate_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance between two coordinates using Haversine formula"""
        import math
        
        R = 6371  # Earth's radius in km
        
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)
        
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlng / 2) ** 2)
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = R * c
        
        return distance
    
    def _extract_services(self, types: List[str]) -> List[str]:
        """Extract service types from Google Maps place types"""
        services = []
        
        service_mapping = {
            "hospital": "emergency",
            "doctor": "general_consultation", 
            "pharmacy": "pharmacy",
            "health": "general_health"
        }
        
        for place_type in types:
            for key, service in service_mapping.items():
                if key in place_type.lower():
                    services.append(service)
        
        return list(set(services)) if services else ["general_health"]
    
    async def close(self):
        """Close the HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None

# Global MCP client instance
mcp_client = MCPClient()
