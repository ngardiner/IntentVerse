# IntentVerse Architecture

## Core Philosophy

IntentVerse is built on a decoupled, microservices-lite architecture. This design ensures separation of concerns, scalability, and maintainability. The entire system is composed of four key components that communicate via a central, internal REST API.

## The Four Components

### 1. The Core Engine (The "Heart")

* **Purpose:** Manages all application logic, state, and security. It is the single source of truth for the simulation.
* **Technology:** A Python backend framework (e.g., FastAPI).
* **Responsibilities:**
    * Maintains the state of all mock tools (virtual file system, mock emails).
    * Loads pluggable tool modules and their corresponding UI schemas.
    * Exposes the private internal REST API for other services.
    * Manages user authentication and serves JWTs.
    * Emits structured JSON logs for all auditable events to `stdout`.

### 2. The MCP Interface (The "Model's Doorway")

* **Purpose:** To communicate with the AI model using the standard Model Context Protocol (MCP) and act as a lean translator.
* **Technology:** Python with the `fastmcp` library.
* **Responsibilities:**
    * Dynamically queries the Core Engine at startup to get a manifest of available tools.
    * Programmatically registers these tools with the `fastmcp` server.
    * Translates incoming MCP tool calls into HTTP requests to the Core Engine's API.
    * **Note on Security:** Authentication for this public-facing endpoint is deferred until an industry standard emerges for the MCP protocol. In its initial version, this endpoint will be unprotected.

### 3. The Web UI (The "Admin's Window")

* **Purpose:** Provides the human user with a rich, visual interface to observe and manage the simulation.
* **Technology:** A modern JavaScript framework (e.g., React, Vue, Svelte).
* **Responsibilities:**
    * Handles user login and securely stores the JWT.
    * Includes the JWT in the `Authorization` header for all API calls to the Core Engine.
    * Dynamically renders a layout and components based on the UI schemas provided by the Core Engine.

### 4. The Pluggable Modules (The "Tools")

* **Purpose:** To contain the actual implementation logic for each mock tool and the schema for its UI representation.
* **Technology:** Standard Python files/classes.
* **Responsibilities:**
    * Define tool functions (e.g., `create_file`, `send_email`).
    * Provide a JSON schema that describes how the module's state should be visualized in the Web UI.

## Key Architectural Concepts

### User Authentication

User access to the Web UI and its underlying API is secured via JWT (JSON Web Tokens). The flow is standard: a user logs in with credentials, the Core Engine returns a signed JWT, and the Web UI uses this token for all subsequent requests.

### Schema-Driven UI

The UI is not statically coded. At startup, the Web UI queries the Core Engine for a "layout" comprised of UI schemas provided by each active module. The UI then uses a library of generic components (e.g., a generic table, a generic file tree) to dynamically render the entire dashboard. This allows new modules to be added without requiring any frontend code changes.

### External Observability

The Core Engine does not directly push logs to an external service. Instead, it emits structured JSON logs to `stdout`. This allows users to employ standard, robust collector agents (e.g., Vector, Fluent Bit) to pick up these logs and forward them to any observability platform of their choice (Splunk, Datadog, etc.).
