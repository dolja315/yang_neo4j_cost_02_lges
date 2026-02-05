# Use Python 3.12 slim image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV SERVICE_TYPE=flask-api

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose port (Cloud Run uses 8080 by default, but we stick to 8000 for local consistency if needed)
EXPOSE 8000

# Make the startup script executable
RUN chmod +x run_services.sh

# Run the services
# Note: Ensure run_services.sh or command aligns with the new gunicorn command
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--chdir", "visualization", "--timeout", "600", "graph_api_server:app"]
