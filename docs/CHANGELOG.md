# v1.1.0

* Configures CORS and uses environment variables to allow non-local users to access the web UI
* Adds rate limiting for the API interfaces
* Implement websockets for real-time Timeline updates, with fallback to polling where websockets is unavailable/unsupported
* Shows pack compatibility conditions in the content pack UI
* Implements JWT refresh tokens to reduce user logout frequency
* Content packs now support both content prompts and usage prompts.
* Content packs allow variable substitution to provide dynamic configuration of packs with local persistence.
* Enhanced API versioning system with automatic feature detection and compatibility checking
* Generate JWT secrets rather than requiring environment variables

# v1.0.0

Initial release.

* Functional sandbox for memory, email, filesystem and database modules
* Functional Content Management
* Functional MCP Proxy capability

Known issues:

* Web UI login page is hardcoded to localhost:8000 and does not support remote or alternate port configurations.
