#!/bin/bash
echo "Starting IT Support service..."
echo "--------------------------------"

# Fix ownership of data directories to match host user (UID 1000)
if [ -d "/app/data" ]; then
    chown -R 1000:1000 /app/data 2>/dev/null || true
    chmod -R 755 /app/data 2>/dev/null || true
    echo "/app/data permissions fixed"
fi

echo "File permissions setup complete"
echo "--------------------------------"

# Start uvicorn with hot-reload for development
echo "Starting uvicorn server with auto-reload..."
exec uvicorn app.main:app --host 0.0.0.0 --port 80 --reload