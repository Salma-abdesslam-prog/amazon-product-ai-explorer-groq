#!/bin/bash
set -e

echo "========================================="
echo "   Amazone-Product-AI-Explorer — Starting Services"
echo "========================================="

# Check Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
  echo ""
  echo "WARNING: Ollama is not running or not installed."
  echo "  1. Install Ollama: https://ollama.com/download"
  echo "  2. Pull the model:  ollama pull phi3"
  echo "  3. Then re-run this script."
  echo ""
fi

# Backend
echo "[1/2] Starting FastAPI backend on port 8080..."
cd backend && uvicorn main:app --host 0.0.0.0 --port 8080 --reload &
BACKEND_PID=$!
cd ..

# Frontend
echo "[2/2] Starting React frontend on port 3000..."
cd frontend && npm start &
FRONTEND_PID=$!
cd ..

echo ""
echo "========================================="
echo "  Backend  → http://localhost:8080"
echo "  Ollama   → http://localhost:11434"
echo "  Frontend → http://localhost:3000"
echo "========================================="
echo "Press Ctrl+C to stop all services."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
