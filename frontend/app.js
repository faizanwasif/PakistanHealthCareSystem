let currentConversationId = null;
let messageCount = 0;
const API_BASE = 'http://localhost:8000';
let authToken = null;
let isOnline = navigator.onLine;
let offlineQueue = [];
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    checkSystemStatus();
    setupEnterKey();
    loadChatHistory();
    setupOfflineHandling();
    setupVoiceRecording();
});

function setupOfflineHandling() {
    // Monitor connection status
    window.addEventListener('online', () => {
        isOnline = true;
        updateConnectionStatus();
        syncOfflineQueue();
    });
    
    window.addEventListener('offline', () => {
        isOnline = false;
        updateConnectionStatus();
    });
    
    updateConnectionStatus();
}

function updateConnectionStatus() {
    const statusElement = document.getElementById('connection-status');
    if (!statusElement) {
        // Create status indicator
        const status = document.createElement('div');
        status.id = 'connection-status';
        status.style.cssText = `
            position: fixed;
            top: 10px;
            right: 10px;
            padding: 5px 10px;
            border-radius: 5px;
            font-size: 12px;
            z-index: 1000;
        `;
        document.body.appendChild(status);
    }
    
    const statusEl = document.getElementById('connection-status');
    if (isOnline) {
        statusEl.textContent = '🟢 Online';
        statusEl.style.backgroundColor = '#4CAF50';
        statusEl.style.color = 'white';
    } else {
        statusEl.textContent = '🔴 Offline Mode';
        statusEl.style.backgroundColor = '#f44336';
        statusEl.style.color = 'white';
    }
}

async function syncOfflineQueue() {
    if (offlineQueue.length === 0) return;
    
    console.log(`Syncing ${offlineQueue.length} offline messages...`);
    
    for (const queuedMessage of offlineQueue) {
        try {
            await sendMessage(queuedMessage.message, false); // Don't queue again
        } catch (error) {
            console.error('Failed to sync offline message:', error);
        }
    }
    
    offlineQueue = [];
    localStorage.removeItem('offlineQueue');
}

function checkAuth() {
    authToken = localStorage.getItem('token');
    const userName = localStorage.getItem('user_name');
    
    if (!authToken) {
        window.location.href = 'login.html';
        return;
    }
    
    // Display user name
    const userNameElement = document.getElementById('user-name');
    if (userNameElement && userName) {
        userNameElement.textContent = `Welcome, ${userName}!`;
    }
    
    // Load Sehat Card status
    loadSehatCardStatus();
    
    // Load notifications
    loadNotifications();
    
    // Check if admin
    checkIfAdmin();
}

async function checkIfAdmin() {
    try {
        const response = await fetch(`${API_BASE}/api/auth/me`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        const user = await response.json();
        
        if (user.role === 'admin') {
            // Add admin panel link
            const userName = document.getElementById('user-name');
            if (userName) {
                userName.innerHTML += ' <a href="admin.html" style="color: #f44336; text-decoration: none; font-size: 0.9em;">[Admin Panel]</a>';
            }
        }
    } catch (error) {
        console.error('Error checking admin status:', error);
    }
}

async function loadNotifications() {
    try {
        const response = await fetch(`${API_BASE}/api/notifications`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        const data = await response.json();
        
        // Update badge
        const badge = document.getElementById('notif-badge');
        if (data.unread_count > 0) {
            badge.textContent = data.unread_count;
            badge.style.display = 'block';
        } else {
            badge.style.display = 'none';
        }
        
        // Store notifications
        window.notifications = data.notifications;
        
    } catch (error) {
        console.error('Error loading notifications:', error);
    }
}

function toggleNotifications() {
    const dropdown = document.getElementById('notifications-dropdown');
    
    if (dropdown.style.display === 'none') {
        // Show notifications
        displayNotifications();
        dropdown.style.display = 'block';
        
        // Mark as read
        markNotificationsRead();
    } else {
        dropdown.style.display = 'none';
    }
}

function displayNotifications() {
    const dropdown = document.getElementById('notifications-dropdown');
    const notifications = window.notifications || [];
    
    if (notifications.length === 0) {
        dropdown.innerHTML = '<p style="padding: 20px; text-align: center; color: #666;">No notifications</p>';
        return;
    }
    
    let html = '<div style="padding: 10px;">';
    html += '<h4 style="margin: 0 0 10px 0; color: #1976d2;">Notifications</h4>';
    
    notifications.forEach(notif => {
        const date = new Date(notif.created_at).toLocaleDateString();
        const isUnread = notif.status === 'unread';
        
        html += `
            <div style="padding: 10px; margin: 5px 0; background: ${isUnread ? '#e3f2fd' : '#f5f5f5'}; border-radius: 5px; border-left: 3px solid #1976d2;">
                <p style="margin: 0; font-size: 0.9em; line-height: 1.4;">${notif.message}</p>
                <p style="margin: 5px 0 0 0; font-size: 0.75em; color: #999;">${date}</p>
            </div>
        `;
    });
    
    html += '</div>';
    dropdown.innerHTML = html;
}

async function markNotificationsRead() {
    try {
        await fetch(`${API_BASE}/api/notifications/mark-read`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        // Update badge
        document.getElementById('notif-badge').style.display = 'none';
        
    } catch (error) {
        console.error('Error marking notifications read:', error);
    }
}

function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user_id');
    localStorage.removeItem('user_name');
    window.location.href = 'login.html';
}

async function loadChatHistory() {
    try {
        const response = await fetch(`${API_BASE}/api/auth/history`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            console.log('Chat history loaded:', data.conversations.length, 'conversations');
            // You can display history in UI if needed
        }
    } catch (error) {
        console.error('Error loading history:', error);
    }
}

function setupEnterKey() {
    const chatInput = document.getElementById('chat-input');
    if (chatInput) {
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
    }
}

async function checkSystemStatus() {
    try {
        const response = await fetch(`${API_BASE}/health`);
        const data = await response.json();

        if (data.status === 'healthy') {
            document.getElementById('status-text').textContent = 'Online';
            document.querySelector('.status-dot').classList.add('online');
        }

        // Get agent status
        const agentResponse = await fetch(`${API_BASE}/api/admin/agents/status`);
        const agentData = await agentResponse.json();
        document.getElementById('agent-count').textContent = agentData.total_agents;

    } catch (error) {
        console.error('System offline:', error);
        document.getElementById('status-text').textContent = 'Offline';
        document.querySelector('.status-dot').classList.remove('online');
        document.querySelector('.status-dot').classList.add('offline');
    }
}

async function sendMessage() {
    const input = document.getElementById('chat-input');
    if (!input) {
        console.error('Chat input element not found');
        return;
    }

    const query = input.value.trim();
    if (!query) return;

    // Add user message to chat
    addMessage(query, 'user');
    input.value = '';

    // Check if offline
    if (!isOnline) {
        // Queue message for later sync
        const queuedMessage = {
            message: query,
            timestamp: new Date().toISOString(),
            user_id: localStorage.getItem('user_id')
        };
        
        offlineQueue.push(queuedMessage);
        localStorage.setItem('offlineQueue', JSON.stringify(offlineQueue));
        
        // Perform offline triage
        try {
            const symptoms = extractSymptoms(query);
            const response = await fetch(`${API_BASE}/api/offline/triage`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ symptoms })
            });
            
            const result = await response.json();
            if (result.success) {
                const offlineResponse = `🔴 OFFLINE MODE<br><br>${result.data.recommendations.join('. ')}<br><br>
                <strong>Urgency:</strong> ${result.data.urgency_level.toUpperCase()}<br>
                <strong>Confidence:</strong> ${(result.data.confidence * 100).toFixed(0)}%<br><br>
                <small>⚠️ This is an offline assessment. Your message will be sent when connection is restored.</small>`;
                
                addMessage(offlineResponse, 'bot');
            }
        } catch (error) {
            addMessage('🔴 OFFLINE MODE<br><br>Unable to process request offline. Your message has been queued and will be sent when connection is restored.', 'bot');
        }
        
        return;
    }

    // Show loading with agent info
    const loadingId = addMessage('🤖 Processing your query through multi-agent system...<br><small style="color: #999;">Agents: Triage → Eligibility → Facility Matcher → Notification</small>', 'bot', true);

    try {
        // Get citizen ID safely
        const citizenIdInput = document.getElementById('citizen-id');
        const citizenId = citizenIdInput ? citizenIdInput.value : 'citizen_001';

        const response = await fetch(`${API_BASE}/api/chat/message`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({
                query: query,
                conversation_id: currentConversationId
            })
        });

        // Remove loading message first
        removeMessage(loadingId);

        if (!response.ok) {
            const errorData = await response.json();
            console.error('Server error:', errorData);
            addMessage(`Error: ${errorData.detail || 'Server error occurred'}. Please check the server logs.`, 'bot');
            return;
        }

        const data = await response.json();
        
        // Handle new standardized API response format
        const responseData = data.success ? data.data : data;
        
        // Set conversation ID
        let convId = responseData.conversation_id ||
            (responseData.triage && responseData.triage.conversation_id) ||
            (responseData.context && responseData.context.conversation_id);

        if (convId) {
            currentConversationId = convId;

            // Show conversation ID in UI
            try {
                const convInfo = document.getElementById('conversation-info');
                const convIdDisplay = document.getElementById('conv-id-display');
                if (convInfo && convIdDisplay) {
                    convIdDisplay.textContent = currentConversationId.substring(0, 8) + '...';
                    convInfo.style.display = 'block';
                }
            } catch (e) {
                console.error('Error updating UI:', e);
            }
        } else {
            console.error('No conversation_id found in response');
        }

        // Display results
        try {
            console.log('About to call displayResults with:', responseData);
            displayResults(responseData);
            console.log('displayResults completed successfully');
        } catch (displayError) {
            console.error('Error in displayResults:', displayError);
            console.error('Error stack:', displayError.stack);
            console.error('Error name:', displayError.name);
            console.error('Error message:', displayError.message);
            addMessage('Results received but error displaying them. Check console.', 'bot');
        }

        // Update message count
        messageCount++;
        document.getElementById('message-count').textContent = messageCount;

    } catch (error) {
        console.error('Error:', error);
        removeMessage(loadingId);
        addMessage(`Sorry, there was an error: ${error.message}. Please check the server logs for details.`, 'bot');
    }
}

function displayResults(data) {
    console.log('displayResults called with:', data);
    
    // Get the clean message to display
    let message = 'Hello! How can I help you?';
    
    if (data && data.response) {
        // Clean response - just use the response text directly
        message = data.response;
        
        // Add urgency indicator if available
        if (data.urgency) {
            const urgencyColors = {
                'high': '#f44336',
                'medium': '#ff9800', 
                'low': '#4caf50'
            };
            const urgencyColor = urgencyColors[data.urgency] || '#666';
            message += `<br><br><span style="color: ${urgencyColor}; font-weight: bold;">⚠️ Urgency: ${data.urgency.toUpperCase()}</span>`;
        }
        
        // Add action if available
        if (data.action && data.action !== data.response) {
            message += `<br><br><strong>📋 Recommended Action:</strong><br>${data.action}`;
        }
        
        // Add agents involved
        if (data.agents_involved && data.agents_involved.length > 0) {
            message += `<br><br><small style="color: #666;">🤖 Processed by: ${data.agents_involved.join(', ')}</small>`;
        }
    }
    
    console.log('Clean message to display:', message);
    
    // Add message directly to DOM
    const messagesContainer = document.getElementById('chat-messages');
    if (messagesContainer) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot-message';
        messageDiv.innerHTML = `<div class="message-content">${message}</div>`;
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        console.log('Message added to DOM successfully');
    } else {
        console.error('chat-messages container not found');
    }
}

function getUrduRecommendation(urgency) {
    const recommendations = {
        'high': '24 گھنٹوں میں فوری طور پر BHU جائیں',
        'medium': '24 گھنٹوں کے اندر BHU کا دورہ کریں',
        'low': 'گھر پر نگرانی کریں اور ضرورت پڑنے پر ڈاکٹر سے ملیں'
    };
    return recommendations[urgency] || 'طبی مشورہ حاصل کریں';
}

function getEnglishNotification(facility) {
    return `You can visit ${facility.facility_name} (${facility.distance_km} km away). Services available: ${facility.available_services.join(', ')}. Timings: 8am-2pm.`;
}

function showAgentNotification(agentName, message) {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = 'agent-notification';
    notification.innerHTML = `
        <div class="notification-content">
            <strong>✓ ${agentName}</strong>
            <p>${message}</p>
        </div>
    `;

    document.body.appendChild(notification);

    // Animate in
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);

    // Remove after 3 seconds
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 3000);
}

function addMessage(content, type, isLoading = false) {
    const messagesContainer = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    const messageId = `msg-${Date.now()}`;
    messageDiv.id = messageId;
    messageDiv.className = `message ${type}-message`;

    if (isLoading) {
        messageDiv.innerHTML = `<div class="loading">${content}</div>`;
    } else {
        const formattedContent = formatMessageContent(content);
        messageDiv.innerHTML = `<div class="message-content">${formattedContent}</div>`;
    }

    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    return messageId;
}

function formatMessageContent(content) {
    // Handle structured content formatting
    let formatted = content;
    
    // Format bold text (**text**)
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Format bullet points (* item)
    formatted = formatted.replace(/^\* (.+)$/gm, '<li>$1</li>');
    
    // Wrap consecutive list items in ul tags
    formatted = formatted.replace(/(<li>.*<\/li>)/gs, (match) => {
        return `<ul class="formatted-list">${match}</ul>`;
    });
    
    // Format sections with colons (Title:)
    formatted = formatted.replace(/^([^:]+:)(?=\s)/gm, '<div class="section-title">$1</div>');
    
    // Format temperature readings
    formatted = formatted.replace(/(\d+°[CF])/g, '<span class="temperature">$1</span>');
    
    // Format medicine names in parentheses
    formatted = formatted.replace(/\(([^)]+)\)/g, '<span class="medicine-name">($1)</span>');
    
    // Convert line breaks to proper paragraphs
    formatted = formatted.split('\n').map(line => {
        line = line.trim();
        if (line === '') return '';
        if (line.includes('<li>') || line.includes('<div class="section-title">')) return line;
        return `<p>${line}</p>`;
    }).join('');
    
    // Clean up empty paragraphs
    formatted = formatted.replace(/<p><\/p>/g, '');
    
    return formatted;
}

function removeMessage(messageId) {
    const message = document.getElementById(messageId);
    if (message) {
        message.remove();
    }
}

async function loadSehatCardStatus() {
    try {
        const response = await fetch(`${API_BASE}/api/sehat-card/status`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        const data = await response.json();
        
        const statusDiv = document.getElementById('sehat-card-status');
        let html = '';
        
        if (data.has_card) {
            // Has active Sehat Card
            html = `
                <div style="background: #e8f5e9; padding: 15px; border-radius: 8px; border-left: 4px solid #4caf50;">
                    <p style="margin: 0; color: #2e7d32; font-weight: bold;">✅ Active Sehat Card</p>
                    <p style="margin: 5px 0 0 0; font-size: 0.9em; color: #666;">You can use your Sehat Card at covered facilities</p>
                </div>
                <button class="action-btn" onclick="viewEligibilityDetails()" style="margin-top: 10px;">
                    View Details | تفصیلات دیکھیں
                </button>
            `;
        } else if (data.status === 'pending') {
            // Application pending
            html = `
                <div style="background: #fff3e0; padding: 15px; border-radius: 8px; border-left: 4px solid #ff9800;">
                    <p style="margin: 0; color: #e65100; font-weight: bold;">⏳ Application Pending</p>
                    <p style="margin: 5px 0 0 0; font-size: 0.9em; color: #666;">Your application is under review</p>
                    <p style="margin: 5px 0 0 0; font-size: 0.85em; color: #999;">Applied: ${new Date(data.application.applied_at).toLocaleDateString()}</p>
                </div>
            `;
        } else if (data.status === 'rejected') {
            // Application rejected
            html = `
                <div style="background: #ffebee; padding: 15px; border-radius: 8px; border-left: 4px solid #f44336;">
                    <p style="margin: 0; color: #c62828; font-weight: bold;">❌ Application Rejected</p>
                    <p style="margin: 5px 0 0 0; font-size: 0.9em; color: #666;">${data.application.rejection_reason || 'Please contact support'}</p>
                </div>
                <button class="action-btn" onclick="showSehatCardForm()" style="margin-top: 10px;">
                    Apply Again | دوبارہ درخواست دیں
                </button>
            `;
        } else {
            // Not applied
            html = `
                <div style="background: #f5f5f5; padding: 15px; border-radius: 8px;">
                    <p style="margin: 0; color: #666; font-size: 0.9em;">You don't have a Sehat Card yet</p>
                    <p style="margin: 5px 0 0 0; font-size: 0.85em; color: #999;">Apply now to get free healthcare</p>
                </div>
                <button class="action-btn" onclick="showSehatCardForm()" style="margin-top: 10px;">
                    Apply for Sehat Card | صحت کارڈ کے لیے درخواست دیں
                </button>
            `;
        }
        
        statusDiv.innerHTML = html;
        
    } catch (error) {
        console.error('Error loading Sehat Card status:', error);
        document.getElementById('sehat-card-status').innerHTML = `
            <p style="color: #f44336;">Error loading status. Please try again.</p>
        `;
    }
}

function showSehatCardForm() {
    const statusDiv = document.getElementById('sehat-card-status');
    statusDiv.innerHTML = `
        <h4 style="margin-top: 0;">Apply for Sehat Card</h4>
        <div style="display: flex; flex-direction: column; gap: 10px;">
            <input type="number" id="family-members" placeholder="Number of family members" min="1" style="padding: 8px; border: 1px solid #ddd; border-radius: 5px;">
            <input type="number" id="monthly-income" placeholder="Monthly income (PKR)" min="0" style="padding: 8px; border: 1px solid #ddd; border-radius: 5px;">
            <input type="text" id="address" placeholder="Address" style="padding: 8px; border: 1px solid #ddd; border-radius: 5px;">
            <input type="text" id="cnic" placeholder="CNIC (e.g., 12345-1234567-1)" style="padding: 8px; border: 1px solid #ddd; border-radius: 5px;">
            <button onclick="submitSehatCardApplication()" style="padding: 10px; background: #4caf50; color: white; border: none; border-radius: 5px; cursor: pointer; font-weight: bold;">
                Submit Application | درخواست جمع کروائیں
            </button>
            <button onclick="loadSehatCardStatus()" style="padding: 8px; background: #999; color: white; border: none; border-radius: 5px; cursor: pointer;">
                Cancel | منسوخ کریں
            </button>
        </div>
    `;
}

async function submitSehatCardApplication() {
    const familyMembers = document.getElementById('family-members').value;
    const monthlyIncome = document.getElementById('monthly-income').value;
    const address = document.getElementById('address').value;
    const cnic = document.getElementById('cnic').value;
    
    if (!familyMembers || !monthlyIncome || !address || !cnic) {
        alert('Please fill all fields');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/sehat-card/apply`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({
                family_members: parseInt(familyMembers),
                monthly_income: parseInt(monthlyIncome),
                address: address,
                cnic: cnic
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Application failed');
        }
        
        const data = await response.json();
        alert(data.message);
        loadSehatCardStatus();
        loadNotifications();  // Reload notifications
        
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

async function viewEligibilityDetails() {
    try {
        const response = await fetch(`${API_BASE}/api/citizen/eligibility`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        const data = await response.json();

        let html = `<h4>Eligibility Details</h4>`;
        html += `<p><strong>Sehat Card:</strong> ${data.sehat_card_active ? '✅ Active' : '❌ Inactive'}</p>`;

        if (data.eligible_programs.length > 0) {
            html += `<p><strong>Eligible Programs:</strong></p><ul style="margin: 5px 0; padding-left: 20px;">`;
            data.eligible_programs.forEach(program => {
                html += `<li style="font-size: 0.9em;">${program}</li>`;
            });
            html += `</ul>`;
        }

        html += `<p><strong>Covered Facilities:</strong> ${data.covered_facilities.length}</p>`;
        html += `<button onclick="loadSehatCardStatus()" style="padding: 8px 16px; background: #1976d2; color: white; border: none; border-radius: 5px; cursor: pointer; margin-top: 10px;">Back</button>`;

        document.getElementById('sehat-card-status').innerHTML = html;

    } catch (error) {
        console.error('Error checking eligibility:', error);
        alert('Error checking eligibility. Please try again.');
    }
}

async function findNearbyFacilities() {
    // Show loading message
    const loadingId = addMessage('📍 Getting your location...', 'bot', true);
    
    try {
        // Get user's live location
        const position = await new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                reject(new Error('Geolocation is not supported by this browser'));
                return;
            }
            
            navigator.geolocation.getCurrentPosition(resolve, reject, {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 60000
            });
        });
        
        const lat = position.coords.latitude;
        const lng = position.coords.longitude;
        
        // Update loading message
        removeMessage(loadingId);
        const searchingId = addMessage('🔍 Searching for nearby hospitals...', 'bot', true);
        
        // Use the facilities API with live location
        const response = await fetch(`${API_BASE}/api/facilities/nearby?lat=${lat}&lng=${lng}&max_distance=10`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });

        // Remove loading message
        removeMessage(searchingId);

        if (!response.ok) {
            const errorData = await response.json();
            addMessage(`Error: ${errorData.detail || 'Could not find hospitals'}`, 'bot');
            return;
        }

        const data = await response.json();
        
        if (data.success && data.data.facilities) {
            // Format hospital results with live location
            let hospitalMessage = `<strong>🏥 Found ${data.data.total_found} Nearby Hospitals</strong><br>`;
            hospitalMessage += `<small>📍 Your location: ${lat.toFixed(4)}, ${lng.toFixed(4)}</small><br>`;
            
            if (data.data.expanded_search) {
                hospitalMessage += `<small>🔍 Expanded search to ${data.data.search_radius_used}km radius</small><br>`;
            }
            hospitalMessage += `<br>`;
            
            data.data.facilities.forEach((hospital, index) => {
                hospitalMessage += `<div style="background: #f8f9fa; padding: 12px; margin: 8px 0; border-radius: 8px; border-left: 4px solid #1976d2;">`;
                hospitalMessage += `<strong>${index + 1}. ${hospital.facility_name}</strong><br>`;
                hospitalMessage += `📍 Distance: ${hospital.distance_km} km<br>`;
                hospitalMessage += `🏥 Services: ${hospital.available_services.join(', ')}<br>`;
                hospitalMessage += `📍 Address: ${hospital.address}<br>`;
                hospitalMessage += `⏰ Timings: ${hospital.timings}<br>`;
                if (hospital.sehat_card_accepted) {
                    hospitalMessage += `💳 <span style="color: #4caf50;">Sehat Card Accepted</span><br>`;
                }
                hospitalMessage += `</div>`;
            });
            
            addMessage(hospitalMessage, 'bot');
        } else {
            addMessage('No hospitals found even with expanded search. Please contact emergency services if urgent.', 'bot');
        }

    } catch (error) {
        console.error('Error finding facilities:', error);
        removeMessage(loadingId);
        
        if (error.message.includes('location') || error.code === 1) {
            addMessage('❌ Location access denied. Using default location (Karachi) to find hospitals.<br><br>Please enable location access for better results.', 'bot');
            
            // Fallback to default location
            setTimeout(() => findNearbyFacilitiesDefault(), 1000);
        } else {
            addMessage('Error finding nearby hospitals. Please try again.', 'bot');
        }
    }
}

async function findNearbyFacilitiesDefault() {
    // Fallback function with default Karachi location
    const loadingId = addMessage('🔍 Searching hospitals in Karachi...', 'bot', true);
    
    try {
        const response = await fetch(`${API_BASE}/api/facilities/nearby?lat=24.8607&lng=67.0011&max_distance=10`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });

        removeMessage(loadingId);

        if (response.ok) {
            const data = await response.json();
            if (data.success && data.data.facilities) {
                let hospitalMessage = `<strong>🏥 Found ${data.data.total_found} Hospitals in Karachi:</strong><br><br>`;
                
                data.data.facilities.forEach((hospital, index) => {
                    hospitalMessage += `<div style="background: #f8f9fa; padding: 12px; margin: 8px 0; border-radius: 8px; border-left: 4px solid #1976d2;">`;
                    hospitalMessage += `<strong>${index + 1}. ${hospital.facility_name}</strong><br>`;
                    hospitalMessage += `📍 Distance: ${hospital.distance_km} km<br>`;
                    hospitalMessage += `🏥 Services: ${hospital.available_services.join(', ')}<br>`;
                    hospitalMessage += `📍 Address: ${hospital.address}<br>`;
                    hospitalMessage += `⏰ Timings: ${hospital.timings}<br>`;
                    if (hospital.sehat_card_accepted) {
                        hospitalMessage += `💳 <span style="color: #4caf50;">Sehat Card Accepted</span><br>`;
                    }
                    hospitalMessage += `</div>`;
                });
                
                addMessage(hospitalMessage, 'bot');
            }
        }
    } catch (error) {
        removeMessage(loadingId);
        addMessage('Error finding hospitals. Please try again.', 'bot');
    }
}

async function viewTrace() {
    if (!currentConversationId) {
        alert('No conversation to trace. Please send a message first.');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/mcp/trace/${currentConversationId}`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        let traceHtml = `<h3 style="color: #1976d2;">Conversation ID: ${data.conversation_id || currentConversationId}</h3>`;

        // Check if we have data
        const messages = data.messages || [];
        const decisions = data.decisions || [];

        if (messages.length === 0 && decisions.length === 0) {
            traceHtml += `<p style="color: #f44336; padding: 20px;">No trace data found. The conversation may still be processing or data wasn't logged.</p>`;
        }

        // Messages
        if (messages.length > 0) {
            traceHtml += `<h4>📨 Inter-Agent Messages (${messages.length})</h4>`;
            traceHtml += `<div style="max-height: 300px; overflow-y: auto; margin-bottom: 20px;">`;
            messages.forEach((msg, i) => {
                traceHtml += `<div style="background: #e3f2fd; padding: 12px; margin: 10px 0; border-radius: 8px; border-left: 3px solid #1976d2;">`;
                traceHtml += `<strong style="color: #1976d2;">${i + 1}. ${msg.from_agent} → ${msg.to_agent}</strong><br>`;
                traceHtml += `<span style="color: #666;">Status: ${msg.status}</span><br>`;
                traceHtml += `<span style="color: #999; font-size: 0.9em;">Time: ${new Date(msg.timestamp).toLocaleString()}</span>`;
                traceHtml += `</div>`;
            });
            traceHtml += `</div>`;
        } else {
            traceHtml += `<p style="color: #999;">No inter-agent messages recorded.</p>`;
        }

        // Decisions
        if (decisions.length > 0) {
            traceHtml += `<h4>🧠 Agent Decisions (${decisions.length})</h4>`;
            traceHtml += `<div style="max-height: 300px; overflow-y: auto;">`;
            decisions.forEach((decision, i) => {
                traceHtml += `<div style="background: #f0f7ff; padding: 12px; margin: 10px 0; border-radius: 8px; border-left: 3px solid #4caf50;">`;
                traceHtml += `<strong style="color: #4caf50;">${i + 1}. ${decision.agent_id}</strong><br>`;
                traceHtml += `<strong>Decision:</strong> ${decision.decision}<br>`;
                traceHtml += `<strong>Confidence:</strong> ${decision.confidence || 'N/A'}<br>`;
                traceHtml += `<strong>Reasoning:</strong> <em>${decision.reasoning || 'No reasoning provided'}</em>`;
                traceHtml += `</div>`;
            });
            traceHtml += `</div>`;
        } else {
            traceHtml += `<p style="color: #999;">No agent decisions recorded.</p>`;
        }

        // Add download button
        traceHtml += `<div style="margin-top: 20px; text-align: center;">`;
        traceHtml += `<button onclick="downloadTrace('${currentConversationId}')" style="padding: 10px 20px; background: #1976d2; color: white; border: none; border-radius: 5px; cursor: pointer;">`;
        traceHtml += `Download Full Trace (JSON)`;
        traceHtml += `</button>`;
        traceHtml += `</div>`;

        document.getElementById('trace-content').innerHTML = traceHtml;
        document.getElementById('trace-modal').style.display = 'block';

    } catch (error) {
        console.error('Error fetching trace:', error);
        alert(`Error fetching agent trace: ${error.message}\n\nPlease check:\n1. You sent a message first\n2. Server is running\n3. Check browser console for details`);
    }
}

function downloadTrace(conversationId) {
    fetch(`${API_BASE}/mcp/trace/${conversationId}`)
        .then(response => response.json())
        .then(data => {
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `trace_${conversationId}.json`;
            a.click();
            URL.revokeObjectURL(url);
        })
        .catch(error => {
            console.error('Error downloading trace:', error);
            alert('Error downloading trace');
        });
}

function closeModal() {
    document.getElementById('trace-modal').style.display = 'none';
}

// Close modal when clicking outside
window.onclick = function (event) {
    const modal = document.getElementById('trace-modal');
    if (event.target === modal) {
        modal.style.display = 'none';
    }
}

function setupVoiceRecording() {
    // Voice button is now inline in HTML, just ensure it exists
    const voiceButton = document.getElementById('voice-button');
    if (voiceButton) {
        voiceButton.onclick = toggleVoiceRecording;
    }
}

async function toggleVoiceRecording() {
    const voiceButton = document.getElementById('voice-button');
    
    if (!isRecording) {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];
            
            mediaRecorder.ondataavailable = (event) => {
                audioChunks.push(event.data);
            };
            
            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                await processVoiceInput(audioBlob);
                
                // Stop all tracks
                stream.getTracks().forEach(track => track.stop());
            };
            
            mediaRecorder.start();
            isRecording = true;
            
            // Update button appearance
            voiceButton.innerHTML = '⏹️';
            voiceButton.classList.add('recording');
            
            // Add recording indicator
            addMessage('🎤 Recording... Click stop when finished', 'bot');
            
        } catch (error) {
            console.error('Error accessing microphone:', error);
            addMessage('❌ Could not access microphone. Please check permissions.', 'bot');
        }
    } else {
        // Stop recording
        if (mediaRecorder && mediaRecorder.state === 'recording') {
            mediaRecorder.stop();
        }
        
        isRecording = false;
        voiceButton.innerHTML = '🎤';
        voiceButton.classList.remove('recording');
    }
}

async function processVoiceInput(audioBlob) {
    try {
        // Show processing message
        const processingId = addMessage('🔄 Processing voice input...', 'bot', true);
        
        // Create FormData for file upload
        const formData = new FormData();
        formData.append('file', audioBlob, 'audio.wav');
        
        // Send to voice chat endpoint
        const response = await fetch(`${API_BASE}/api/voice/chat`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`
            },
            body: formData
        });
        
        // Remove processing message
        removeMessage(processingId);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            // Add user's transcribed message
            addMessage(`🎤 "${data.data.urdu_input}" (${data.data.english_input})`, 'user');
            
            // Add bot response with Urdu translation
            let responseText = data.data.english_response;
            if (data.data.urdu_response) {
                responseText += `<br><br>🗣️ اردو: ${data.data.urdu_response}`;
            }
            
            if (data.data.agents_involved) {
                responseText += `<br><br>🤖 Agents: ${data.data.agents_involved.join(', ')}`;
            }
            
            addMessage(responseText, 'bot');
            
            currentConversationId = data.data.conversation_id;
            
        } else {
            addMessage(`❌ Voice processing failed: ${data.message}`, 'bot');
        }
        
    } catch (error) {
        console.error('Voice processing error:', error);
        addMessage(`❌ Voice processing error: ${error.message}`, 'bot');
    }
}

// Refresh system status every 30 seconds
setInterval(checkSystemStatus, 30000);
