# Docker Deployment Guide

This guide explains how to run the Neo4j Cost Analysis System using Docker.

## Prerequisites

1. **Docker** and **Docker Compose** installed on your machine.
2. A `.env` file in the root directory with your Neo4j credentials.
   ```env
   NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
   NEO4J_USERNAME=neo4j
   NEO4J_PASSWORD=your-password
   NEO4J_DATABASE=neo4j
   ```

## Option 1: Using Docker Compose (Recommended)

This method runs the API and Dashboard as separate containers, which is better for logs and management.

1. **Build and Run:**
   ```bash
   docker-compose up --build
   ```
   Add `-d` to run in background:
   ```bash
   docker-compose up -d --build
   ```

2. **Access the Applications:**
   - **Streamlit Dashboard:** [http://localhost:8501](http://localhost:8501)
   - **Flask API:** [http://localhost:8000](http://localhost:8000)
   - **Visualization Dashboard (HTML):** [http://localhost:8000](http://localhost:8000) (Serves dashboard.html)

3. **Stop the containers:**
   ```bash
   docker-compose down
   ```

## Option 2: Single Container (Good for Azure Web App)

This method runs both services inside a single container using a startup script.

1. **Build the image:**
   ```bash
   docker build -t neo4j-cost-analysis .
   ```

2. **Run the container:**
   ```bash
   docker run -p 8000:8000 -p 8501:8501 --env-file .env neo4j-cost-analysis
   ```

3. **Access:**
   - Same URLs as above.

## Troubleshooting

- **Connection Error:** Ensure your `.env` file has correct Neo4j credentials and the Neo4j instance is accessible from the container (Cloud Aura is recommended).
- **Port Conflict:** If ports 8000 or 8501 are in use, change the mapping in `docker-compose.yml` or the `docker run` command (e.g., `-p 8080:8000`).
