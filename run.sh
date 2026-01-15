#!/bin/bash

# Python Library Scanner API - Run Script

echo "🚀 Starting Python Library Scanner API..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Run the Flask app
echo "✅ Starting Flask server on http://localhost:5000"
echo "Press Ctrl+C to stop the server"
echo ""
python app.py
