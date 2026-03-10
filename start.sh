#!/usr/bin/env bash
# MarketShift — Start both frontend and backend dev servers

set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

# Cleanup on exit (Ctrl+C)
cleanup() {
  echo ""
  echo "Shutting down..."
  kill "$BACKEND_PID" 2>/dev/null || true
  kill "$FRONTEND_PID" 2>/dev/null || true
  exit 0
}
trap cleanup SIGINT SIGTERM

# Start backend
echo "Starting backend (http://localhost:8000)..."
cd "$ROOT/backend"
source venv/bin/activate
uvicorn main:app --reload &
BACKEND_PID=$!
cd "$ROOT"

# Brief delay so backend can bind
sleep 2

# Start frontend
echo "Starting frontend (http://localhost:5173)..."
cd "$ROOT/frontend"
npm run dev &
FRONTEND_PID=$!
cd "$ROOT"

echo ""
echo "MarketShift dev servers running:"
echo "  Frontend: http://localhost:5173"
echo "  Backend:  http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop both."
echo ""

wait
