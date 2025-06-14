# Use an official Node.js image. Alpine versions are lightweight.
FROM node:20-alpine

# Set the working directory in the container to /app
WORKDIR /app

# Copy package.json and package-lock.json (if available)
# This is done first to leverage Docker's layer caching for dependencies.
COPY package*.json ./

# Install project dependencies
RUN npm install

# Copy the rest of the application's code from your host to your container at /app
COPY . .

# Your app binds to port 3000, so you'll want to expose it
EXPOSE 3000

# The CMD to run the app is specified in the docker-compose.yml for development.
# But we can add a default one here as well.
CMD ["npm", "start"]
