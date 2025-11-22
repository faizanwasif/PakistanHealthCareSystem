#!/bin/bash

echo "Checking Python environment..."

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Creating venv..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "Failed to create virtual environment. Make sure Python 3 is installed."
        exit 1
    fi
    echo "Virtual environment created successfully."
fi

# Activate venv
echo "Activating virtual environment..."
source venv/bin/activate

# Check if requirements are installed by checking for a key package
python -c "import firebase_admin" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "Failed to install dependencies."
        exit 1
    fi
    echo "Dependencies installed successfully."
fi

# Create logs directory
mkdir -p logs

# Check for .env file
if [ ! -f ".env" ]; then
    echo "Creating .env template..."
    cat > .env << EOF
GEMINI_API_KEY=your_gemini_api_key_here
FIREBASE_CREDENTIALS_PATH=config/firebase-credentials.json
FIREBASE_DATABASE_URL=https://your-project-id-default-rtdb.firebaseio.com/
JWT_SECRET=your-secret-key-here
ENVIRONMENT=development
LOG_LEVEL=INFO
EOF
    echo "Please edit .env file with your Firebase and Gemini credentials before running the application."
    echo "Also update config/firebase-credentials.json with your Firebase service account key."
    exit 1
fi

# Check for Firebase credentials
if [ ! -f "config/firebase-credentials.json" ] || grep -q "your-project-id" "config/firebase-credentials.json"; then
    echo "Please update config/firebase-credentials.json with your actual Firebase service account credentials."
    exit 1
fi

# Run the application
echo "Starting application..."
cd backend
python main.py
