/**
 * Location Helper for getting user's exact GPS location
 * Integrates with Google Maps MCP backend
 */

class LocationHelper {
    constructor() {
        this.currentLocation = null;
        this.watchId = null;
    }

    /**
     * Get user's current location using browser Geolocation API
     * @returns {Promise<{lat: number, lng: number}>}
     */
    async getCurrentLocation() {
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                reject(new Error('Geolocation is not supported by your browser'));
                return;
            }

            const options = {
                enableHighAccuracy: true,  // Use GPS if available
                timeout: 10000,            // 10 second timeout
                maximumAge: 0              // Don't use cached position
            };

            navigator.geolocation.getCurrentPosition(
                (position) => {
                    const location = {
                        lat: position.coords.latitude,
                        lng: position.coords.longitude,
                        accuracy: position.coords.accuracy
                    };
                    
                    this.currentLocation = location;
                    console.log('Location obtained:', location);
                    resolve(location);
                },
                (error) => {
                    console.error('Location error:', error);
                    reject(this.handleLocationError(error));
                },
                options
            );
        });
    }

    /**
     * Watch user's location for continuous updates
     * @param {Function} callback - Called when location changes
     */
    watchLocation(callback) {
        if (!navigator.geolocation) {
            console.error('Geolocation not supported');
            return;
        }

        const options = {
            enableHighAccuracy: true,
            timeout: 5000,
            maximumAge: 0
        };

        this.watchId = navigator.geolocation.watchPosition(
            (position) => {
                const location = {
                    lat: position.coords.latitude,
                    lng: position.coords.longitude,
                    accuracy: position.coords.accuracy
                };
                
                this.currentLocation = location;
                callback(location);
            },
            (error) => {
                console.error('Watch location error:', error);
            },
            options
        );
    }

    /**
     * Stop watching location
     */
    stopWatching() {
        if (this.watchId !== null) {
            navigator.geolocation.clearWatch(this.watchId);
            this.watchId = null;
        }
    }

    /**
     * Handle geolocation errors
     */
    handleLocationError(error) {
        switch(error.code) {
            case error.PERMISSION_DENIED:
                return new Error('Location permission denied. Please enable location access in your browser settings.');
            case error.POSITION_UNAVAILABLE:
                return new Error('Location information unavailable. Please check your GPS/network connection.');
            case error.TIMEOUT:
                return new Error('Location request timed out. Please try again.');
            default:
                return new Error('An unknown error occurred while getting location.');
        }
    }

    /**
     * Request location permission
     */
    async requestPermission() {
        try {
            const location = await this.getCurrentLocation();
            return { granted: true, location };
        } catch (error) {
            return { granted: false, error: error.message };
        }
    }

    /**
     * Check if location is in Pakistan (approximate boundaries)
     */
    isInPakistan(location) {
        const { lat, lng } = location;
        // Pakistan boundaries (approximate)
        return lat >= 23.5 && lat <= 37.5 && lng >= 60.5 && lng <= 77.5;
    }

    /**
     * Format location for display
     */
    formatLocation(location) {
        return `${location.lat.toFixed(6)}, ${location.lng.toFixed(6)}`;
    }

    /**
     * Get approximate city name from coordinates
     */
    getCityName(location) {
        const cities = {
            'Karachi': { lat: 24.8607, lng: 67.0011 },
            'Lahore': { lat: 31.5204, lng: 74.3587 },
            'Islamabad': { lat: 33.6844, lng: 73.0479 },
            'Rawalpindi': { lat: 33.5651, lng: 73.0169 },
            'Faisalabad': { lat: 31.4504, lng: 73.1350 },
            'Multan': { lat: 30.1575, lng: 71.5249 },
            'Peshawar': { lat: 34.0151, lng: 71.5249 },
            'Quetta': { lat: 30.1798, lng: 66.9750 }
        };

        let closestCity = 'Unknown';
        let minDistance = Infinity;

        for (const [city, coords] of Object.entries(cities)) {
            const distance = this.calculateDistance(
                location.lat, location.lng,
                coords.lat, coords.lng
            );
            
            if (distance < minDistance && distance < 50) { // Within 50km
                minDistance = distance;
                closestCity = city;
            }
        }

        return closestCity;
    }

    /**
     * Calculate distance between two coordinates (Haversine formula)
     */
    calculateDistance(lat1, lng1, lat2, lng2) {
        const R = 6371; // Earth's radius in km
        const dLat = this.toRadians(lat2 - lat1);
        const dLng = this.toRadians(lng2 - lng1);
        
        const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
                  Math.cos(this.toRadians(lat1)) * Math.cos(this.toRadians(lat2)) *
                  Math.sin(dLng / 2) * Math.sin(dLng / 2);
        
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        return R * c;
    }

    toRadians(degrees) {
        return degrees * (Math.PI / 180);
    }
}

// Global instance
const locationHelper = new LocationHelper();

// Example usage functions

/**
 * Add location button to chat interface
 */
function addLocationButton() {
    const chatInput = document.getElementById('user-input');
    if (!chatInput) return;

    const locationBtn = document.createElement('button');
    locationBtn.id = 'location-btn';
    locationBtn.innerHTML = '📍 Share Location';
    locationBtn.className = 'location-button';
    locationBtn.onclick = shareLocation;

    chatInput.parentElement.insertBefore(locationBtn, chatInput.nextSibling);
}

/**
 * Share location with the system
 */
async function shareLocation() {
    const locationBtn = document.getElementById('location-btn');
    if (locationBtn) {
        locationBtn.disabled = true;
        locationBtn.innerHTML = '⏳ Getting location...';
    }

    try {
        const location = await locationHelper.getCurrentLocation();
        
        // Check if in Pakistan
        if (!locationHelper.isInPakistan(location)) {
            alert('Warning: Your location appears to be outside Pakistan. Results may be limited.');
        }

        const city = locationHelper.getCityName(location);
        const formatted = locationHelper.formatLocation(location);
        
        // Add to chat
        addMessage('user', `📍 My location: ${city} (${formatted})`);
        
        // Send to backend
        await sendLocationToBackend(location);
        
        if (locationBtn) {
            locationBtn.disabled = false;
            locationBtn.innerHTML = '✓ Location shared';
            setTimeout(() => {
                locationBtn.innerHTML = '📍 Share Location';
            }, 3000);
        }

    } catch (error) {
        console.error('Location error:', error);
        alert(error.message);
        
        if (locationBtn) {
            locationBtn.disabled = false;
            locationBtn.innerHTML = '📍 Share Location';
        }
    }
}

/**
 * Send location to backend for facility matching
 */
async function sendLocationToBackend(location) {
    try {
        const response = await fetch(`${API_BASE}/api/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({
                message: 'Find nearest hospital',
                citizen_location: {
                    lat: location.lat,
                    lng: location.lng
                },
                urgency_level: 'MEDIUM',
                conversation_id: currentConversationId
            })
        });

        const data = await response.json();
        
        if (data.facility_recommendation) {
            const facility = data.facility_recommendation;
            addMessage('assistant', 
                `🏥 Nearest Hospital: ${facility.facility_name}\n` +
                `📍 Distance: ${facility.distance_km} km\n` +
                `⏱️ Estimated wait: ${facility.estimated_wait_time || 'N/A'}\n` +
                `✓ Services: ${facility.available_services.join(', ')}`
            );
        } else {
            addMessage('assistant', data.response);
        }

    } catch (error) {
        console.error('Error sending location:', error);
        addMessage('assistant', 'Sorry, I had trouble finding nearby facilities. Please try again.');
    }
}

/**
 * Show location permission prompt
 */
function showLocationPrompt() {
    const prompt = document.createElement('div');
    prompt.className = 'location-prompt';
    prompt.innerHTML = `
        <div class="location-prompt-content">
            <h3>📍 Enable Location Access</h3>
            <p>To find the nearest hospital, we need your location.</p>
            <button onclick="requestLocationAccess()">Allow Location</button>
            <button onclick="dismissLocationPrompt()">Not Now</button>
        </div>
    `;
    document.body.appendChild(prompt);
}

async function requestLocationAccess() {
    const result = await locationHelper.requestPermission();
    
    if (result.granted) {
        dismissLocationPrompt();
        alert('Location access granted! You can now use the location feature.');
    } else {
        alert(result.error);
    }
}

function dismissLocationPrompt() {
    const prompt = document.querySelector('.location-prompt');
    if (prompt) {
        prompt.remove();
    }
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        addLocationButton();
    });
} else {
    addLocationButton();
}
