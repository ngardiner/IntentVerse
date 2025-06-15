# Stage 1 - Use an official Node.js image. Alpine versions are lightweight.
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
# Install all dependencies
RUN npm install

# Stage 2: The final, clean image for running the application
FROM node:20-alpine
WORKDIR /app
# This is the crucial step: Copy the pre-built node_modules from the 'builder' stage.
# This solves the volume mounting problem.
COPY --from=builder /app/node_modules ./node_modules
# Copy the application source code.
COPY . .
# Expose the port React runs on.
EXPOSE 3000
# The command to start the web server.
CMD ["npm", "start"]