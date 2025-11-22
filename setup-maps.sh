#!/bin/bash

echo "🗺️  Setting up Google Maps MCP Server..."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js first:"
    echo "   sudo apt update && sudo apt install nodejs npm"
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed. Please install npm first:"
    echo "   sudo apt install npm"
    exit 1
fi

# Install Google Maps MCP server globally
echo "📦 Installing Google Maps MCP Server..."
npm install -g @cablate/mcp-google-map

if [ $? -eq 0 ]; then
    echo "✅ Google Maps MCP Server installed successfully!"
    echo ""
    echo "🔑 To start the server, you need your Google Maps API key:"
    echo "   1. Go to: https://console.cloud.google.com/apis/credentials"
    echo "   2. Create or select a project"
    echo "   3. Enable Maps JavaScript API and Places API"
    echo "   4. Create an API key"
    echo ""
    echo "🚀 Start the server with:"
    echo "   mcp-google-map --port 3000 --apikey \"YOUR_API_KEY\""
    echo ""
    echo "Or add GOOGLE_MAPS_API_KEY to your .env file and run:"
    echo "   mcp-google-map --port 3000 --apikey \"\$GOOGLE_MAPS_API_KEY\""
else
    echo "❌ Failed to install Google Maps MCP Server"
    exit 1
fi
