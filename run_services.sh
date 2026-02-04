#!/bin/bash

# Start Flask API in background
echo "Starting Flask API..."
# Using --chdir visualization so imports within graph_api_server work if they depend on being in that dir,
# but mainly to locate the app.
# Note: graph_api_server.py does relative path imports for files in root (../dashboard.html),
# so running from root might be better if pythonpath is set, but --chdir is safer for gunicorn finding the app module.
gunicorn --bind 0.0.0.0:8000 --chdir visualization --timeout 600 graph_api_server:app &

# Start Streamlit Dashboard in foreground
echo "Starting Streamlit Dashboard..."
streamlit run visualization/streamlit_dashboard.py --server.port 8501 --server.address 0.0.0.0
