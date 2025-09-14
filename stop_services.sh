#!/bin/bash
echo "🛑 Stopping Sensor Hub services..."
pkill -f "start-scheduler" 2>/dev/null || true
pkill -f "flask.*run" 2>/dev/null || true
echo "✅ Services stopped."
