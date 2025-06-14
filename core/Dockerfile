# Use an official lightweight Python image as a parent image
FROM python:3.11-slim

# Set the working directory in the container to /app
WORKDIR /app

# Copy the requirements file into the container at /app
# This is done first to leverage Docker's layer caching.
# The dependencies layer will only be rebuilt if requirements.txt changes.
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code from your host to your container at /app
COPY ./app .

# Expose port 8000 to allow communication to/from the container
EXPOSE 8000

# Note: The CMD to run the application is specified in the docker-compose.yml file.
# This allows for more flexibility during development (e.g., using --reload).
