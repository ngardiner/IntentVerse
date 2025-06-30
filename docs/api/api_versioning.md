# API Versioning Strategy

This document outlines the API versioning strategy for the IntentVerse Core Engine.

## Overview

The IntentVerse Core Engine uses a comprehensive API versioning strategy to ensure backward compatibility while allowing the API to evolve. This strategy includes:

1. **URL-based versioning** - Primary versioning mechanism
2. **Header-based versioning** - Secondary mechanism for backward compatibility
3. **Version management system** - To track and manage API versions
4. **Documentation** - Clear documentation of versioning policy
5. **Deprecation policy** - Process for deprecating old versions

## Versioning Mechanisms

### URL-based Versioning

The primary versioning mechanism is URL-based versioning. API endpoints are prefixed with the version number:

```
/api/v1/endpoint
/api/v2/endpoint
```

This approach makes the version explicit and easy to understand. It also allows for different versions of the same endpoint to coexist.

### Header-based Versioning

For backward compatibility, the API also supports header-based versioning. Clients can specify the desired API version using the `X-API-Version` header:

```
X-API-Version: v1
X-API-Version: v2
```

This approach allows clients to use the same URL for different versions of the API.

### Version Precedence

When determining which version to use, the following precedence rules apply:

1. URL-based version (e.g., `/api/v2/endpoint`)
2. Header-based version (e.g., `X-API-Version: v2`)
3. Default version (currently `v2`)

## Version Management

### Version Status

API versions can have one of the following statuses:

- **Current**: The latest stable version
- **Stable**: A stable version that is still supported
- **Deprecated**: A version that is deprecated but still works
- **Sunset**: A version that is no longer supported

### Version Lifecycle

1. A new version is introduced with status **Current**
2. The previous current version becomes **Stable**
3. When a newer version is introduced, older versions may be marked as **Deprecated**
4. After a deprecation period, deprecated versions are **Sunset** and no longer supported

### Deprecation Policy

When a version is deprecated:

1. A deprecation notice is added to the API documentation
2. Deprecation headers are added to responses:
   - `X-API-Deprecated: true`
   - `X-API-Sunset-Date: YYYY-MM-DD`
   - `X-API-Current-Version: vX`
3. The version continues to work for a deprecation period (typically 6-12 months)
4. After the deprecation period, the version is sunset and no longer supported

## API Version Information

### Get All Versions

To get information about all API versions:

```
GET /api/versions
```

Response:

```json
{
  "versions": [
    {
      "version": "v1",
      "release_date": "2023-01-01T00:00:00",
      "status": "stable",
      "sunset_date": null,
      "description": "Initial API version",
      "breaking_changes": [],
      "new_features": [
        "Core API functionality",
        "Authentication and authorization",
        "Module system",
        "Content pack management",
        "Timeline events",
        "WebSocket support for real-time updates"
      ],
      "bug_fixes": []
    },
    {
      "version": "v2",
      "release_date": "2023-07-01T00:00:00",
      "status": "current",
      "sunset_date": null,
      "description": "Enhanced API version with improved module introspection and health checks",
      "breaking_changes": [],
      "new_features": [
        "Enhanced health check endpoint with detailed system status",
        "Module introspection API for discovering available tools",
        "Improved error handling and reporting",
        "Support for header-based versioning"
      ],
      "bug_fixes": []
    }
  ],
  "current_version": "v2"
}
```

### Get Version Information

To get information about a specific version:

```
GET /api/versions/{version}
```

Response:

```json
{
  "version": "v2",
  "release_date": "2023-07-01T00:00:00",
  "status": "current",
  "sunset_date": null,
  "description": "Enhanced API version with improved module introspection and health checks",
  "breaking_changes": [],
  "new_features": [
    "Enhanced health check endpoint with detailed system status",
    "Module introspection API for discovering available tools",
    "Improved error handling and reporting",
    "Support for header-based versioning"
  ],
  "bug_fixes": []
}
```

## Client Implementation

### JavaScript Client

The JavaScript client supports API versioning through the `X-API-Version` header:

```javascript
// API version to use
const API_VERSION = 'v2';

// Add API version header to all requests
apiClient.interceptors.request.use(
  (config) => {
    // Add API version header
    config.headers['X-API-Version'] = API_VERSION;
    return config;
  }
);
```

### Version-specific Clients

For convenience, version-specific clients are provided:

- `client.js` - Uses API v1 (for backward compatibility)
- `client_v2.js` - Uses API v2 (for new features)

## Best Practices

1. **Always specify the version** in client requests, either in the URL or using the `X-API-Version` header.
2. **Monitor deprecation headers** to be aware of upcoming changes.
3. **Upgrade to the latest version** when possible to take advantage of new features and improvements.
4. **Test with multiple versions** to ensure backward compatibility.
5. **Document version-specific features** in API documentation.