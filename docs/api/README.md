# IntentVerse API Documentation

Welcome to the comprehensive API documentation for IntentVerse. This documentation covers all available endpoints, authentication methods, and integration patterns.

## 📚 Documentation Structure

- **[Overview](overview.md)** - API architecture, versioning, and general concepts
- **[Authentication](authentication.md)** - JWT tokens, API keys, and security
- **[Core API](core-api.md)** - Module state, UI layout, and system endpoints
- **[MCP Interface](mcp-interface.md)** - Model Context Protocol endpoints for AI integration
- **[Content Packs](content-packs.md)** - Content pack management and operations
- **[User Management](user-management.md)** - User, group, and permission management
- **[Timeline](timeline.md)** - Event logging and timeline management
- **[Error Handling](error-handling.md)** - Error codes, responses, and troubleshooting
- **[Examples](examples.md)** - Code examples and integration patterns (Coming Soon)

## 🚀 Quick Start

### Base URL
```
http://localhost:8000
```

### Authentication
```bash
# Login to get access token
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=your_username&password=your_password"

# Use token in subsequent requests
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/v1/ui/layout"
```

### Interactive Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔗 Quick Links

| Endpoint Category | Base Path | Description |
|------------------|-----------|-------------|
| Authentication | `/auth` | Login, user management |
| Core API | `/api/v1` | Module state, UI layout |
| MCP Interface | `/api/v1/tools`, `/api/v1/execute` | AI model integration |
| Content Packs | `/api/v1/content-packs` | Content management |
| Timeline | `/events` | Event logging |
| Debug | `/api/v1/debug` | Development utilities |

## 📋 API Features

- **RESTful Design**: Standard HTTP methods and status codes
- **JWT Authentication**: Secure token-based authentication
- **API Key Support**: Service-to-service authentication
- **Role-Based Access Control**: Fine-grained permissions
- **Audit Logging**: Complete audit trail of all operations
- **OpenAPI Specification**: Auto-generated documentation
- **CORS Support**: Cross-origin requests enabled
- **Error Handling**: Consistent error responses

## 🛠️ Development Tools

- **FastAPI**: Modern Python web framework
- **Pydantic**: Data validation and serialization
- **SQLModel**: Database ORM with type safety
- **OpenAPI**: Automatic API documentation generation

## 📖 Getting Started

1. **Read the [Overview](overview.md)** to understand the API architecture
2. **Set up [Authentication](authentication.md)** to access protected endpoints
3. **Explore the individual API documentation** for detailed examples and integration patterns
4. **Check [Error Handling](error-handling.md)** for troubleshooting

## 🔄 API Versioning

The current API version is **v1**. All endpoints are prefixed with `/api/v1` except for authentication endpoints which use `/auth`.

## 📞 Support

For questions or issues with the API:
- Check the [Error Handling](error-handling.md) guide
- Review the individual API documentation for detailed examples
- Examine the interactive documentation at `/docs`