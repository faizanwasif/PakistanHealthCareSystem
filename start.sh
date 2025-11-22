#!/bin/bash

echo "🚀 Starting Pakistan Healthcare Multi-Agent System..."

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "❌ Failed to create virtual environment"
        exit 1
    fi
fi

# Activate venv
source venv/bin/activate

# Install dependencies (skip if already installed)
echo "📦 Checking dependencies..."
pip check > /dev/null 2>&1 || pip install -r requirements.txt

# Create logs directory
mkdir -p logs

# Check for .env file
if [ ! -f ".env" ]; then
    echo "⚠️  Creating .env template..."
    cat > .env << EOF
GEMINI_API_KEY=your_gemini_api_key_here
FIREBASE_CREDENTIALS_PATH=config/firebase-credentials.json
FIREBASE_DATABASE_URL=https://your-project-id-default-rtdb.firebaseio.com/
MCP_GOOGLE_MAPS_URL=http://localhost:3000/mcp
GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here
JWT_SECRET=your-secret-key-here
ENVIRONMENT=development
LOG_LEVEL=INFO
EOF
    echo "❌ Please edit .env file with your credentials first!"
    exit 1
fi

# Load environment variables
source .env

# Check Firebase credentials
if grep -q "your-project-id" "config/firebase-credentials.json" 2>/dev/null; then
    echo "❌ Please update config/firebase-credentials.json with real Firebase credentials!"
    exit 1
fi

# Install Google Maps MCP server if not installed
if ! command -v mcp-google-map &> /dev/null; then
    echo "📦 Installing Google Maps MCP Server..."
    npm install -g @cablate/mcp-google-map
fi

# Start Google Maps MCP server in background
echo "🗺️  Starting Google Maps MCP Server..."
if [ -n "$GOOGLE_MAPS_API_KEY" ] && [ "$GOOGLE_MAPS_API_KEY" != "your_google_maps_api_key_here" ]; then
    mcp-google-map --port 3000 --apikey "$GOOGLE_MAPS_API_KEY" > logs/mcp-server.log 2>&1 &
    MCP_PID=$!
    echo "✅ Google Maps MCP Server started (PID: $MCP_PID)"
    
    # Wait a moment for server to start
    sleep 3
    
    # Check if MCP server is running
    if curl -s http://localhost:3000/mcp > /dev/null 2>&1; then
        echo "✅ Google Maps MCP Server is running on port 3000"
    else
        echo "⚠️  Google Maps MCP Server may not be fully ready yet"
    fi
else
    echo "⚠️  Google Maps API key not configured - maps features will be limited"
fi

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down servers..."
    if [ -n "$MCP_PID" ]; then
        kill $MCP_PID 2>/dev/null
        echo "✅ Google Maps MCP Server stopped"
    fi
    exit 0
}

# Set trap to cleanup on script exit
trap cleanup SIGINT SIGTERM

# Start the main application
echo "🔥 Starting main server..."
echo ""
echo "🌐 Application will be available at:"
echo "   👉 http://localhost:8000"
echo ""
echo "📱 Frontend pages:"
echo "   • Main App: http://localhost:8000"
echo "   • Login: http://localhost:8000/login.html"
echo "   • Admin: http://localhost:8000/admin.html"
echo ""
echo "📚 API Documentation:"
echo "   • Swagger UI: http://localhost:8000/docs"
echo "   • ReDoc: http://localhost:8000/redoc"
echo ""
echo "🗺️  Google Maps MCP Server: http://localhost:3000/mcp"
echo ""
echo "Press Ctrl+C to stop all servers"
echo "================================"

cd backend
python main.py
