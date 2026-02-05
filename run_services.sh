#!/bin/bash

# Use PORT environment variable provided by Cloud Run, default to 8080
PORT="${PORT:-8080}"

echo "Starting Services on PORT $PORT..."

# Start Flask API in foreground (Primary Service for Cloud Run)
echo "Starting Flask API on port $PORT..."
# Using --chdir visualization so imports within graph_api_server work
exec gunicorn --bind "0.0.0.0:$PORT" --chdir visualization --timeout 600 graph_api_server:app
