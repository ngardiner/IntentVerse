# v1.2.0

## Features
* Adds external database abstraction support for MySQL and PostgreSQL, as well as database migration support.
* Adds categories for modules with a tabbed interface, to allow the addition of more mock modules

# v1.1.0

## Features
* Functional MCP Proxy capability
* Adds rate limiting for the API interfaces
* Implement websockets for real-time Timeline updates, with fallback to polling where websockets is unavailable/unsupported
* Shows pack compatibility conditions in the content pack UI
* Content packs now support both content prompts and usage prompts.
* Content packs allow variable substitution to provide dynamic configuration of packs with local persistence.
* Implement tool-level individual enablement toggles

## Fixes
* Configures CORS and uses environment variables to allow non-local users to access the web UI
* Implements JWT refresh tokens to reduce user logout frequency
* Enhanced API versioning system with automatic feature detection and compatibility checking
* Generate JWT secrets rather than requiring environment variables

# v1.0.0

Initial release.

* Functional sandbox for memory, email, filesystem and database modules
* Functional Content Management

Known issues:

* Web UI login page is hardcoded to localhost:8000 and does not support remote or alternate port configurations.
