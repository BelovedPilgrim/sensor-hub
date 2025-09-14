#!/bin/bash

# Simple Sensor Hub Startup Script
echo "🚀 Starting Sensor Hub..."

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Stop any existing processes
echo "🛑 Stopping existing processes..."
pkill -f "start-scheduler" 2>/dev/null || true
pkill -f "flask.*run" 2>/dev/null || true
sleep 2

# Start scheduler in background
echo "📊 Starting scheduler..."
poetry run python -m sensor_hub.cli start-scheduler &
SCHEDULER_PID=$!
echo "   Scheduler PID: $SCHEDULER_PID"

# Wait a moment
sleep 3

# Start web app in background  
echo "🌐 Starting web application..."
poetry run python -m flask --app src.sensor_hub run --host=0.0.0.0 --port=5001 &
WEBAPP_PID=$!
echo "   Web app PID: $WEBAPP_PID"

# Wait for startup
sleep 3

echo
echo "✅ Sensor Hub started!"
echo "   📊 Scheduler PID: $SCHEDULER_PID"
echo "   🌐 Web App PID: $WEBAPP_PID"
echo "   🔗 Web interface: http://localhost:5001"
echo
echo "💡 To stop all services, run:"
echo "   pkill -f 'start-scheduler|flask.*run'"
echo

# Create simple stop script
cat > stop_services.sh << 'EOF'
#!/bin/bash
echo "🛑 Stopping Sensor Hub services..."
pkill -f "start-scheduler" 2>/dev/null || true
pkill -f "flask.*run" 2>/dev/null || true
echo "✅ Services stopped."
EOF
chmod +x stop_services.sh

echo "📝 Created stop_services.sh script"