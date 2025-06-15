# IntentVerse Installation Guide

This guide will walk you through setting up and running the project on your local machine for development.

## Prerequisites

Before you begin, ensure you have the following software installed on your system:

1. **Git:** For cloning the repository.
2. **Docker:** The containerization platform that runs our services.
3. **Docker Compose:** The tool for defining and running multi-container Docker applications. It is included with modern Docker Desktop installations.

On a debian-based system, you would install these with the following commands:

```bash
apt update
apt install git docker.io docker-compose
```

## Installation Steps

### Clone the Repository

First, clone the IntentVerse repository from GitHub to your local machine.

```bash
git clone https://github.com/ngardiner/IntentVerse.git
cd IntentVerse
```

### 2. Build and Run the Application

The entire application stack (Core Engine, MCP Interface, and Web UI) is orchestrated by Docker Compose. To build the images and start all the services, run the following command from the root directory of the project:

```bash
docker compose up --build
```

* The `--build` flag tells Docker Compose to build the images from their respective `Dockerfiles` the first time you run it.
* You will see logs from all three services streaming in your terminal. This is useful for debugging during development.
* To run the services in the background (detached mode), you can use `docker compose up -d`.

### 3. Accessing the Services

Once the containers are running, you can access the different parts of the application:

* **Web UI (Dashboard):** Open your web browser and navigate to `http://localhost:3000`
* **Core Engine API (for direct testing):** The API is available at `http://localhost:8000`. You can access its interactive documentation (provided by FastAPI) at `http://localhost:8000/docs`.
* **MCP Interface:** The MCP server will be listening for connections from AI models on port `8001`.

## Stopping the Application

To stop all running services, press `Ctrl+C` in the terminal where `docker compose up` is running. If you are running in detached mode, use the following command:

```bash
docker compose down
```