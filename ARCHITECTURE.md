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

#### Dual-Mode Operation

The MCP Interface is designed to run in two distinct modes to support different client use cases:

1.  **Persistent Server (Streamable HTTP):** The default mode when run via `docker-compose`. It operates as a long-running network server, accepting multiple client connections. Ideal for remote or web-based agents.
2.  **Ephemeral Instance (stdio):** The interface can also be invoked as a one-off process by a local client (e.g., `docker run -i ...`). In this mode, it communicates over `stdin/stdout` for a single session. This is made possible by our decoupled architecture, as the ephemeral instance can still connect to the persistent `core` service over the shared network.

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

### Content

Whilst the project presents a set of interfaces for mock MCP interfaces, these alone are not particularly useful. A key use case is the ability to inject mock content for the model to interact with, and for the model to then generate and store its own content. This will be done through content packs.

The content presented by these packs is not part of the core distribution in this source tree. Below are the key points on how content is handled in this project:

* The system is instantiated with a blank StateManager, and blank SQLite database. All modules other than SQLite are stored in StateManager, SQLite will always need to be an outlier. There will never be static content within the python modules themselves.
* There will be a single default content pack that is distributed with the release which has some dummy data for testing and is turned on by default, but can be turned off within the UI. Other content packs can be added/removed.
* Content packs are JSON files directly exported from the UI, with 4 key sections: Metadata, Database, Prompts and State.
   * Metadata
       * Metadata contains the key details needed to populate the manifest for content packs uploaded to the repository. It will contain details such as Name, Summary, Detailed Description, Date Exported, Author Name and Email. These are not mandatory for a UI export, but they will be for inclusion into the content repository. Name/Summary/Date should be populated by core on export, the rest blank placeholders for manual user population when submitting to the Content repository. Metadata is mandatory.
   * Database
       * Export of the SQLite database content, in a mergeable format. It should not replace current content but consist of CREATE/INSERT statements to add the content currently in the SQLite database to any database it is imported into. This is optional.
   * Prompts
       * Prompts allow for storage of text prompts which instruct the model to create content based on the text prompt provided. This is optional.
   * State
      * State is an export of the StateManager, providing the current content state of every module other than database.
      * It must be mergable. The content within state will be merged into the current StateManager context, allowing multiple content packs to exist
      * This section is optional. A content pack may have no state (or empty state) and the modules may or may not be populated with state, ie it could just be memory and no other module. No scenario should ever lead to current state being cleared.
* A separate repository will be created to manage the content packs.