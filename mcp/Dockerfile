# Use an official lightweight Python image as a parent image
FROM python:3.11-slim
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container to /app
WORKDIR /app

# Copy the requirements files into the container at /app
# This is done first to leverage Docker's layer caching.
COPY requirements.txt .
COPY tests/requirements.txt ./tests/

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install test dependencies
RUN pip install --no-cache-dir -r tests/requirements.txt

# Copy the rest of the application's code from your host to your container at /app
COPY ./app ./app
COPY ./tests ./tests

# Expose port 8001 to allow the AI model to connect
EXPOSE 8001

# Note: The CMD to run the application is specified in the docker-compose.yml file.
