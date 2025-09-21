#!/bin/bash

# Sensor Hub Stop Script
echo "Stopping Sensor Hub services..."

# Stop scheduler
if pgrep -f "start-scheduler" > /dev/null; then
    echo "  Stopping scheduler..."
    pkill -f "start-scheduler"
fi

# Stop web app
if pgrep -f "flask.*src\.sensor_hub.*run" > /dev/null; then
    echo "  Stopping web app..."
    pkill -f "flask.*src\.sensor_hub.*run"
fi

sleep 2
echo "✅ All services stopped."
