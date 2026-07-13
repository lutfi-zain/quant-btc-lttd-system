#!/bin/bash
# Start backend and frontend simultaneously

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." &>/dev/null && pwd)"

BACKEND_PORT=8765
FRONTEND_PORT=8766

# Auto-detect public IP (dynamic) — prefers IPv4, falls back to hostname -I
PUBLIC_IP=""
if command -v curl &>/dev/null; then
	PUBLIC_IP=$(curl -4 -s --max-time 3 https://ifconfig.co 2>/dev/null || curl -4 -s --max-time 3 https://api.ipify.org 2>/dev/null || true)
fi
if [ -z "$PUBLIC_IP" ] && command -v hostname &>/dev/null; then
	PUBLIC_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
fi
PUBLIC_IP="${PUBLIC_IP:-<ganti_dengan_ip_public>}"

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
# Kosongkan VITE_API_URL agar frontend pakai window.location.origin + Vite proxy (/api -> backend)
VITE_API_URL="" bun run build
VITE_API_URL="" bun run preview --port $FRONTEND_PORT &
FRONTEND_PID=$!

echo "Waiting for services to start..."
sleep 2

echo ""
echo "============================================"
echo "  ✅ Both servers are running!"
echo ""
echo "  Frontend (dashboard):"
echo "    Local  : http://localhost:$FRONTEND_PORT"
echo "    Public : http://$PUBLIC_IP:$FRONTEND_PORT"
echo ""
echo "  Backend (API):"
echo "    Local  : http://localhost:$BACKEND_PORT"
echo "    Public : http://$PUBLIC_IP:$BACKEND_PORT"
echo ""
echo "  ℹ️  API calls from frontend are proxied via Vite preview server."
echo "  ℹ️  Public URL hanya berfungsi jika firewall/security group"
echo "      mengizinkan port $BACKEND_PORT dan $FRONTEND_PORT."
echo "============================================"
echo ""
echo "Press Ctrl+C to stop both."

# Trap Ctrl+C to kill both background processes
trap "echo 'Stopping services...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGINT SIGTERM

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
