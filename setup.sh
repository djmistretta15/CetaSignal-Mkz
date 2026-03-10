#!/bin/bash
# CetaSignal — Full Setup Script
# Run: chmod +x setup.sh && ./setup.sh

set -e

echo ""
echo "🐋 CetaSignal Setup"
echo "=========================="
echo ""

# Check prerequisites
command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3 required"; exit 1; }
command -v node >/dev/null 2>&1 || { echo "❌ Node.js required"; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "❌ npm required"; exit 1; }

echo "✓ Prerequisites found"
echo ""

# Backend setup
echo "📦 Setting up Python backend..."
cd backend
python3 -m pip install -r requirements.txt -q
cd ..

# Scripts setup
echo "📦 Installing Python scripts dependencies..."
cd scripts
python3 -m pip install -r requirements.txt -q
echo ""

# Download data + train model
echo "📡 Downloading NOAA whale data (synthetic fallback if unavailable)..."
python3 download_noaa.py --max-calls 8 --synthetic-fallback
echo ""

echo "🎼 Extracting cadence features..."
python3 extract_features.py
echo ""

echo "🧠 Training classifier..."
python3 train_model.py
echo ""

cd ..

# Frontend setup
echo "🖥️  Setting up React frontend..."
cd frontend
npm install --silent
echo ""

cd ..

echo "=========================="
echo "✅ Setup complete!"
echo ""
echo "To run:"
echo ""
echo "  Terminal 1 — Backend:"
echo "  cd backend && uvicorn main:app --reload --port 8000"
echo ""
echo "  Terminal 2 — Frontend:"
echo "  cd frontend && npm run dev"
echo ""
echo "  Open: http://localhost:5173"
echo ""
