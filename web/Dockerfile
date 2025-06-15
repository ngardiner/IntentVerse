# Use an official Node.js image. Alpine versions are lightweight.
FROM node:20-alpine
WORKDIR /app
COPY package.json ./
# Install all dependencies
RUN npm install
# Copy the application source code.
COPY . .
# Expose the port React runs on.
EXPOSE 3000
# The command to start the web server.
CMD ["npm", "start"]