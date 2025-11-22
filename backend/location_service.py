"""
Location Service for getting user's exact location
"""
import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

class LocationService:
    """Service for handling user location"""
    
    @staticmethod
    def parse_location_from_input(user_input: str) -> Optional[Dict[str, float]]:
        """
        Parse location from user input
        
        Supports formats:
        - "lat: 31.5204, lng: 74.3587"
        - "31.5204, 74.3587"
        - "Lahore" (would need geocoding)
        
        Args:
            user_input: User's location input
        
        Returns:
            Dictionary with lat and lng, or None if parsing fails
        """
        try:
            # Try to extract coordinates
            import re
            
            # Pattern for "lat: X, lng: Y" or "latitude: X, longitude: Y"
            pattern1 = r'lat(?:itude)?:\s*([-+]?\d+\.?\d*),?\s*lng|lon(?:gitude)?:\s*([-+]?\d+\.?\d*)'
            match1 = re.search(pattern1, user_input, re.IGNORECASE)
            
            if match1:
                lat = float(match1.group(1))
                lng = float(match1.group(2))
                return {"lat": lat, "lng": lng}
            
            # Pattern for "X, Y" (simple comma-separated)
            pattern2 = r'([-+]?\d+\.?\d*)\s*,\s*([-+]?\d+\.?\d*)'
            match2 = re.search(pattern2, user_input)
            
            if match2:
                lat = float(match2.group(1))
                lng = float(match2.group(2))
                
                # Validate coordinates are reasonable
                if -90 <= lat <= 90 and -180 <= lng <= 180:
                    return {"lat": lat, "lng": lng}
            
            logger.warning(f"Could not parse location from: {user_input}")
            return None
            
        except Exception as e:
            logger.error(f"Error parsing location: {e}")
            return None
    
    @staticmethod
    async def geocode_address(address: str) -> Optional[Dict[str, float]]:
        """
        Convert address to coordinates using Google Maps Geocoding API
        
        Args:
            address: Address string (e.g., "Lahore, Pakistan")
        
        Returns:
            Dictionary with lat and lng, or None if geocoding fails
        """
        try:
            import os
            import requests
            
            api_key = os.getenv("GOOGLE_MAPS_API_KEY")
            if not api_key or api_key == "your-google-maps-api-key-here":
                logger.error("Google Maps API key not configured for geocoding")
                return None
            
            url = "https://maps.googleapis.com/maps/api/geocode/json"
            params = {
                "address": address,
                "key": api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("status") == "OK" and data.get("results"):
                location = data["results"][0]["geometry"]["location"]
                return {
                    "lat": location["lat"],
                    "lng": location["lng"]
                }
            else:
                logger.error(f"Geocoding failed: {data.get('status')}")
                return None
                
        except Exception as e:
            logger.error(f"Error geocoding address: {e}")
            return None
    
    @staticmethod
    def get_location_from_request(request_data: Dict) -> Optional[Dict[str, float]]:
        """
        Extract location from API request
        
        Tries multiple sources:
        1. Explicit lat/lng in request
        2. Location object in request
        3. Parse from text input
        4. Geocode from address
        
        Args:
            request_data: Request data dictionary
        
        Returns:
            Dictionary with lat and lng, or None
        """
        # Check for explicit coordinates
        if "lat" in request_data and "lng" in request_data:
            return {
                "lat": float(request_data["lat"]),
                "lng": float(request_data["lng"])
            }
        
        # Check for location object
        if "location" in request_data:
            loc = request_data["location"]
            if isinstance(loc, dict) and "lat" in loc and "lng" in loc:
                return {
                    "lat": float(loc["lat"]),
                    "lng": float(loc["lng"])
                }
        
        # Check for citizen_location
        if "citizen_location" in request_data:
            loc = request_data["citizen_location"]
            if isinstance(loc, dict) and "lat" in loc and "lng" in loc:
                return {
                    "lat": float(loc["lat"]),
                    "lng": float(loc["lng"])
                }
        
        return None
    
    @staticmethod
    def validate_pakistan_location(location: Dict[str, float]) -> bool:
        """
        Validate that location is within Pakistan's approximate boundaries
        
        Pakistan boundaries (approximate):
        - Latitude: 23.5° N to 37.5° N
        - Longitude: 60.5° E to 77.5° E
        
        Args:
            location: Dictionary with lat and lng
        
        Returns:
            True if location is in Pakistan, False otherwise
        """
        lat = location.get("lat", 0)
        lng = location.get("lng", 0)
        
        if 23.5 <= lat <= 37.5 and 60.5 <= lng <= 77.5:
            return True
        
        logger.warning(f"Location {lat}, {lng} is outside Pakistan boundaries")
        return False
    
    @staticmethod
    def get_city_name(lat: float, lng: float) -> str:
        """
        Get approximate city name from coordinates
        
        This is a simple lookup for major Pakistani cities.
        For production, use reverse geocoding API.
        
        Args:
            lat: Latitude
            lng: Longitude
        
        Returns:
            City name or "Unknown"
        """
        # Major Pakistani cities (approximate centers)
        cities = {
            "Karachi": (24.8607, 67.0011),
            "Lahore": (31.5204, 74.3587),
            "Islamabad": (33.6844, 73.0479),
            "Rawalpindi": (33.5651, 73.0169),
            "Faisalabad": (31.4504, 73.1350),
            "Multan": (30.1575, 71.5249),
            "Peshawar": (34.0151, 71.5249),
            "Quetta": (30.1798, 66.9750),
            "Sialkot": (32.4945, 74.5229),
            "Gujranwala": (32.1877, 74.1945)
        }
        
        # Find closest city (within 50km)
        min_distance = float('inf')
        closest_city = "Unknown"
        
        for city, (city_lat, city_lng) in cities.items():
            distance = LocationService._calculate_distance(lat, lng, city_lat, city_lng)
            if distance < min_distance and distance < 50:  # Within 50km
                min_distance = distance
                closest_city = city
        
        return closest_city
    
    @staticmethod
    def _calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance between two coordinates in km"""
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

# Global location service instance
location_service = LocationService()
