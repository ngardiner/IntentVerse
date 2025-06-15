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