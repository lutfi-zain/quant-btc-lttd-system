#!/bin/bash
# Start backend and frontend simultaneously

PROJECT_ROOT="/run/media/lutfizain/Work/Projects/1.WORKING/quant-btc-lttd-system"

echo "Starting Backend..."
cd "$PROJECT_ROOT/backend" || exit 1
PORT=4000 bun index.ts &
BACKEND_PID=$!

echo "Building & Starting Frontend..."
cd "$PROJECT_ROOT/frontend" || exit 1
VITE_API_URL="http://localhost:4000" bun run build
VITE_API_URL="http://localhost:4000" bun run preview --port 4001 &
FRONTEND_PID=$!

echo "Waiting for services to start..."
sleep 2

echo "Opening browser..."
if command -v xdg-open &> /dev/null; then
    xdg-open "http://localhost:4001"
elif command -v open &> /dev/null; then
    open "http://localhost:4001"
else
    echo "Could not detect web browser to open http://localhost:4001"
fi

echo "Both servers are running."
echo "Press Ctrl+C to stop both."

# Trap Ctrl+C to kill both background processes
trap "echo 'Stopping services...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGINT SIGTERM

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
