#!/bin/bash
# Start backend and frontend simultaneously

PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." &>/dev/null && pwd )"


BACKEND_PORT=8765
FRONTEND_PORT=8766

echo "Freeing ports $BACKEND_PORT (backend) and $FRONTEND_PORT (frontend)..."
for port in $BACKEND_PORT $FRONTEND_PORT; do
	pid=$(lsof -ti :$port 2>/dev/null)
	if [ -n "$pid" ]; then
		echo "  Port $port in use by PID $pid — killing..."
		kill -9 $pid 2>/dev/null
		sleep 1
	fi
done

echo "Installing backend dependencies..."
cd "$PROJECT_ROOT/backend" || exit 1
bun install --registry https://registry.npmjs.org/ 2>&1 | tail -2

echo "Installing frontend dependencies..."
cd "$PROJECT_ROOT/frontend" || exit 1
bun install --registry https://registry.npmjs.org/ 2>&1 | tail -2


echo "Starting Backend..."
cd "$PROJECT_ROOT/backend" || exit 1
PORT=$BACKEND_PORT bun index.ts &
BACKEND_PID=$!

echo "Building & Starting Frontend..."
cd "$PROJECT_ROOT/frontend" || exit 1
VITE_API_URL="http://localhost:$BACKEND_PORT" bun run build
VITE_API_URL="http://localhost:$BACKEND_PORT" bun run preview --port $FRONTEND_PORT &
FRONTEND_PID=$!

echo "Waiting for services to start..."
sleep 2

echo "Opening browser..."
if command -v xdg-open &>/dev/null; then
	xdg-open "http://localhost:$FRONTEND_PORT"
elif command -v open &>/dev/null; then
	open "http://localhost:$FRONTEND_PORT"
else
	echo "Could not detect web browser to open http://localhost:$FRONTEND_PORT"
fi

echo "Both servers are running."
echo "Press Ctrl+C to stop both."

# Trap Ctrl+C to kill both background processes
trap "echo 'Stopping services...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGINT SIGTERM

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
