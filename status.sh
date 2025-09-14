#!/bin/bash

# Sensor Hub Status Script
echo "=== Sensor Hub Status ==="

# Check scheduler
if pgrep -f "start-scheduler" > /dev/null 2>&1; then
    SCHEDULER_PID=$(pgrep -f "start-scheduler")
    echo "📊 Scheduler: ✅ Running (PID: $SCHEDULER_PID)"
else
    echo "📊 Scheduler: ❌ Stopped"
fi

# Check web app
if pgrep -f "flask.*run" > /dev/null 2>&1; then
    WEBAPP_PID=$(pgrep -f "flask.*run")
    echo "🌐 Web App: ✅ Running (PID: $WEBAPP_PID)"
    echo "   🔗 URL: http://localhost:5001"
else
    echo "🌐 Web App: ❌ Stopped"
fi

echo