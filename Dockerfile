# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define environment variable
ENV NAME World

# Run upload_to_neo4j.py when the container launches, then start gunicorn
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:8000 visualization.graph_api_server:app"]
