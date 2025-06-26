# Content Packs

Content Packs are a way to package and distribute module states, configurations, and data in IntentVerse. They enable easy sharing of setups, templates, and pre-configured environments.

## Overview

Content Packs provide:
- **Export/Import**: Save and restore system state
- **Templates**: Pre-configured module setups
- **Sharing**: Distribute configurations between instances
- **Versioning**: Track changes and updates
- **Validation**: Ensure pack integrity and compatibility

## Authentication

All Content Pack endpoints require authentication and appropriate permissions:
- `content_packs.read` - View and preview content packs
- `content_packs.create` - Export new content packs
- `content_packs.install` - Install and load content packs
- `content_packs.update` - Update and refresh content packs
- `content_packs.delete` - Delete and unload content packs

## Local Content Pack Management

### List Available Content Packs

**GET** `/api/v1/content-packs/available`

Returns a list of all available content packs in the local content_packs directory.

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
```

**Required Permission:** `content_packs.read`

**Response:**
```json
[
  {
    "filename": "default.json",
    "name": "Default Configuration",
    "description": "Default system configuration with basic modules",
    "version": "1.0.0",
    "author": "IntentVerse Team",
    "created_at": "2024-01-01T12:00:00Z",
    "file_size": 2048,
    "is_loaded": true
  },
  {
    "filename": "development-setup.json",
    "name": "Development Setup",
    "description": "Pre-configured development environment",
    "version": "1.2.0",
    "author": "Developer",
    "created_at": "2024-01-15T10:30:00Z",
    "file_size": 4096,
    "is_loaded": false
  }
]
```

### Get Loaded Content Packs

**GET** `/api/v1/content-packs/loaded`

Returns information about currently loaded content packs.

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
```

**Required Permission:** `content_packs.read`

**Response:**
```json
[
  {
    "filename": "default.json",
    "name": "Default Configuration",
    "version": "1.0.0",
    "loaded_at": "2024-01-01T12:00:00Z",
    "modules_affected": ["filesystem", "database", "timeline"],
    "load_order": 1
  }
]
```

### Export Content Pack

**POST** `/api/v1/content-packs/export`

Export the current system state as a content pack.

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json
```

**Required Permission:** `content_packs.create`

**Request Body:**
```json
{
  "filename": "my-setup.json",
  "metadata": {
    "name": "My Custom Setup",
    "description": "Custom configuration for my workflow",
    "version": "1.0.0",
    "author": "John Doe",
    "tags": ["development", "custom"],
    "category": "workflow"
  }
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Content pack exported to my-setup.json",
  "path": "/app/content_packs/my-setup.json"
}
```

### Load Content Pack

**POST** `/api/v1/content-packs/load`

Load a content pack by filename.

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json
```

**Required Permission:** `content_packs.install`

**Request Body:**
```json
{
  "filename": "development-setup.json"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Content pack 'development-setup.json' loaded successfully"
}
```

### Unload Content Pack

**POST** `/api/v1/content-packs/unload`

Unload a content pack by filename or name.

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json
```

**Required Permission:** `content_packs.delete`

**Request Body:**
```json
{
  "identifier": "development-setup.json"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Content pack 'development-setup.json' unloaded successfully"
}
```

### Preview Content Pack

**GET** `/api/v1/content-packs/preview/{filename}`

Preview a content pack without loading it, including validation results.

**Parameters:**
- `filename` (path, required): Name of the content pack file

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
```

**Required Permission:** `content_packs.read`

**Response:**
```json
{
  "exists": true,
  "metadata": {
    "name": "Development Setup",
    "description": "Pre-configured development environment",
    "version": "1.2.0",
    "author": "Developer",
    "created_at": "2024-01-15T10:30:00Z",
    "tags": ["development", "setup"],
    "category": "workflow"
  },
  "modules": ["filesystem", "database", "email", "memory"],
  "file_size": 4096,
  "validation": {
    "is_valid": true,
    "errors": [],
    "warnings": [
      "Module 'email' is currently disabled"
    ],
    "compatibility": {
      "version_compatible": true,
      "missing_modules": [],
      "conflicting_modules": []
    }
  }
}
```

### Validate Content Pack

**POST** `/api/v1/content-packs/validate`

Validate a content pack and return detailed validation results.

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json
```

**Required Permission:** `content_packs.read`

**Request Body:**
```json
{
  "filename": "development-setup.json"
}
```

**Response:**
```json
{
  "filename": "development-setup.json",
  "validation": {
    "is_valid": true,
    "errors": [],
    "warnings": [
      "Module 'email' is currently disabled"
    ],
    "compatibility": {
      "version_compatible": true,
      "missing_modules": [],
      "conflicting_modules": []
    },
    "schema_validation": {
      "valid": true,
      "errors": []
    },
    "module_validation": {
      "valid": true,
      "module_checks": {
        "filesystem": "valid",
        "database": "valid",
        "email": "disabled",
        "memory": "valid"
      }
    }
  }
}
```

### Clear All Loaded Packs

**POST** `/api/v1/content-packs/clear-all`

Clear all loaded content packs from tracking.

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
```

**Required Permission:** `content_packs.delete`

**Response:**
```json
{
  "status": "success",
  "message": "All loaded content packs cleared from tracking"
}
```

## Remote Content Pack Management

### List Remote Content Packs

**GET** `/api/v1/content-packs/remote`

Returns a list of all available remote content packs.

**Parameters:**
- `force_refresh` (query, optional): Force refresh of remote cache

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
```

**Required Permission:** `content_packs.read`

**Response:**
```json
[
  {
    "filename": "ai-workflow.json",
    "name": "AI Workflow Template",
    "description": "Pre-configured setup for AI development workflows",
    "version": "2.1.0",
    "author": "AI Team",
    "category": "ai",
    "tags": ["ai", "workflow", "template"],
    "download_url": "https://repo.intentverse.com/packs/ai-workflow.json",
    "file_size": 8192,
    "downloads": 1250,
    "rating": 4.8,
    "last_updated": "2024-01-20T15:00:00Z"
  },
  {
    "filename": "data-analysis.json",
    "name": "Data Analysis Setup",
    "description": "Tools and configurations for data analysis",
    "version": "1.5.0",
    "author": "Data Team",
    "category": "analytics",
    "tags": ["data", "analysis", "visualization"],
    "download_url": "https://repo.intentverse.com/packs/data-analysis.json",
    "file_size": 6144,
    "downloads": 890,
    "rating": 4.6,
    "last_updated": "2024-01-18T12:00:00Z"
  }
]
```

### Get Remote Content Pack Info

**GET** `/api/v1/content-packs/remote/info/{filename}`

Get detailed information about a specific remote content pack.

**Parameters:**
- `filename` (path, required): Name of the remote content pack

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
```

**Required Permission:** `content_packs.read`

**Response:**
```json
{
  "filename": "ai-workflow.json",
  "name": "AI Workflow Template",
  "description": "Pre-configured setup for AI development workflows with integrated tools for model training, evaluation, and deployment.",
  "version": "2.1.0",
  "author": "AI Team",
  "category": "ai",
  "tags": ["ai", "workflow", "template", "machine-learning"],
  "download_url": "https://repo.intentverse.com/packs/ai-workflow.json",
  "file_size": 8192,
  "downloads": 1250,
  "rating": 4.8,
  "last_updated": "2024-01-20T15:00:00Z",
  "changelog": [
    {
      "version": "2.1.0",
      "date": "2024-01-20",
      "changes": ["Added model evaluation tools", "Updated database schemas"]
    },
    {
      "version": "2.0.0",
      "date": "2024-01-15",
      "changes": ["Major refactor", "New AI integration modules"]
    }
  ],
  "requirements": {
    "min_version": "0.1.0",
    "modules": ["filesystem", "database", "memory", "web_search"],
    "dependencies": []
  },
  "screenshots": [
    "https://repo.intentverse.com/screenshots/ai-workflow-1.png",
    "https://repo.intentverse.com/screenshots/ai-workflow-2.png"
  ]
}
```

### Search Remote Content Packs

**POST** `/api/v1/content-packs/remote/search`

Search remote content packs by query, category, or tags.

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json
```

**Required Permission:** `content_packs.read`

**Request Body:**
```json
{
  "query": "data analysis",
  "category": "analytics",
  "tags": ["visualization", "data"]
}
```

**Response:**
```json
[
  {
    "filename": "data-analysis.json",
    "name": "Data Analysis Setup",
    "description": "Tools and configurations for data analysis",
    "version": "1.5.0",
    "author": "Data Team",
    "category": "analytics",
    "tags": ["data", "analysis", "visualization"],
    "relevance_score": 0.95,
    "download_url": "https://repo.intentverse.com/packs/data-analysis.json"
  }
]
```

### Download Remote Content Pack

**POST** `/api/v1/content-packs/remote/download`

Download a remote content pack to local cache.

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json
```

**Required Permission:** `content_packs.install`

**Request Body:**
```json
{
  "filename": "ai-workflow.json"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Content pack 'ai-workflow.json' downloaded successfully",
  "cache_path": "/app/cache/content_packs/ai-workflow.json"
}
```

### Install Remote Content Pack

**POST** `/api/v1/content-packs/remote/install`

Download and install a remote content pack.

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json
```

**Required Permission:** `content_packs.install`

**Request Body:**
```json
{
  "filename": "ai-workflow.json",
  "load_immediately": true
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Content pack 'ai-workflow.json' installed and loaded successfully"
}
```

### Get Remote Repository Info

**GET** `/api/v1/content-packs/remote/repository-info`

Get information about the remote repository including statistics.

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
```

**Required Permission:** `content_packs.read`

**Response:**
```json
{
  "repository_url": "https://repo.intentverse.com",
  "total_packs": 45,
  "categories": [
    {"name": "ai", "count": 12},
    {"name": "analytics", "count": 8},
    {"name": "workflow", "count": 15},
    {"name": "development", "count": 10}
  ],
  "popular_tags": [
    {"tag": "workflow", "count": 25},
    {"tag": "ai", "count": 18},
    {"tag": "data", "count": 15}
  ],
  "last_updated": "2024-01-20T15:00:00Z",
  "cache_status": {
    "last_refresh": "2024-01-20T10:00:00Z",
    "cache_age_hours": 5,
    "is_stale": false
  }
}
```

### Refresh Remote Cache

**POST** `/api/v1/content-packs/remote/refresh-cache`

Force refresh the remote manifest cache.

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
```

**Required Permission:** `content_packs.update`

**Response:**
```json
{
  "status": "success",
  "message": "Remote cache refreshed successfully",
  "content_packs_count": 45
}
```

### Clear Remote Cache

**POST** `/api/v1/content-packs/remote/clear-cache`

Clear the remote content pack cache.

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN
```

**Required Permission:** `content_packs.delete`

**Response:**
```json
{
  "status": "success",
  "message": "Remote cache cleared successfully"
}
```

## Content Pack Structure

### Content Pack Format

Content packs are JSON files with the following structure:

```json
{
  "metadata": {
    "name": "My Content Pack",
    "description": "Description of the content pack",
    "version": "1.0.0",
    "author": "Author Name",
    "created_at": "2024-01-01T12:00:00Z",
    "tags": ["tag1", "tag2"],
    "category": "workflow",
    "min_version": "0.1.0"
  },
  "modules": {
    "filesystem": {
      "current_directory": "/home/user",
      "bookmarks": ["/home/user/projects", "/var/log"],
      "settings": {
        "show_hidden": false,
        "default_permissions": "644"
      }
    },
    "database": {
      "connections": [
        {
          "name": "main",
          "type": "sqlite",
          "path": "/app/data.db"
        }
      ],
      "saved_queries": [
        {
          "name": "User Count",
          "query": "SELECT COUNT(*) FROM users"
        }
      ]
    },
    "memory": {
      "data": {
        "user_preferences": {"theme": "dark"},
        "app_config": {"debug": false}
      }
    }
  },
  "settings": {
    "ui_layout": "default",
    "theme": "dark",
    "language": "en"
  }
}
```

### Validation Rules

Content packs are validated against these rules:

1. **Schema Validation**: Must conform to the content pack JSON schema
2. **Version Compatibility**: Must be compatible with current IntentVerse version
3. **Module Validation**: Referenced modules must exist and be available
4. **Data Integrity**: Module data must be valid for each module type
5. **Security Checks**: No malicious content or unsafe configurations

## Error Handling

### Common Errors

**400 Bad Request - Missing Filename**
```json
{
  "detail": "Filename is required"
}
```

**404 Not Found - Pack Not Found**
```json
{
  "detail": "Content pack 'invalid-pack.json' not found"
}
```

**500 Internal Server Error - Export Failed**
```json
{
  "detail": "Failed to export content pack"
}
```

**422 Unprocessable Entity - Validation Failed**
```json
{
  "detail": "Content pack validation failed",
  "validation_errors": [
    "Module 'invalid_module' not found",
    "Version '2.0.0' not compatible with current version '1.0.0'"
  ]
}
```

## Best Practices

### Creating Content Packs

1. **Descriptive Metadata**: Use clear names and descriptions
2. **Version Control**: Use semantic versioning (major.minor.patch)
3. **Documentation**: Include comprehensive descriptions and tags
4. **Testing**: Validate content packs before sharing
5. **Size Optimization**: Keep content packs reasonably sized

### Managing Content Packs

1. **Regular Backups**: Export content packs regularly for backup
2. **Version Tracking**: Keep track of content pack versions
3. **Validation**: Always validate before loading content packs
4. **Cleanup**: Regularly clean up unused content packs
5. **Security**: Only load content packs from trusted sources

### Integration Examples

```python
# Python example for content pack management
import requests
import json

class ContentPackManager:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    
    def export_current_state(self, filename, metadata):
        """Export current system state as content pack."""
        payload = {
            'filename': filename,
            'metadata': metadata
        }
        
        response = requests.post(
            f"{self.base_url}/api/v1/content-packs/export",
            headers=self.headers,
            data=json.dumps(payload)
        )
        response.raise_for_status()
        return response.json()
    
    def load_content_pack(self, filename):
        """Load a content pack."""
        payload = {'filename': filename}
        
        response = requests.post(
            f"{self.base_url}/api/v1/content-packs/load",
            headers=self.headers,
            data=json.dumps(payload)
        )
        response.raise_for_status()
        return response.json()
    
    def preview_content_pack(self, filename):
        """Preview a content pack before loading."""
        response = requests.get(
            f"{self.base_url}/api/v1/content-packs/preview/{filename}",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

# Usage
manager = ContentPackManager('http://localhost:8000', 'your-token')

# Export current state
result = manager.export_current_state(
    'my-backup.json',
    {
        'name': 'My Backup',
        'description': 'Backup of my current setup',
        'version': '1.0.0',
        'author': 'Me'
    }
)
print(f"Exported: {result['path']}")

# Preview before loading
preview = manager.preview_content_pack('development-setup.json')
if preview['validation']['is_valid']:
    manager.load_content_pack('development-setup.json')
    print("Content pack loaded successfully")
else:
    print(f"Validation errors: {preview['validation']['errors']}")
```

```javascript
// JavaScript example for content pack management
class ContentPackManager {
  constructor(baseUrl, token) {
    this.baseUrl = baseUrl;
    this.headers = {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    };
  }
  
  async listAvailable() {
    const response = await fetch(`${this.baseUrl}/api/v1/content-packs/available`, {
      headers: this.headers
    });
    
    if (!response.ok) {
      throw new Error(`Failed to list content packs: ${response.statusText}`);
    }
    
    return response.json();
  }
  
  async installRemotePack(filename, loadImmediately = true) {
    const response = await fetch(`${this.baseUrl}/api/v1/content-packs/remote/install`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify({
        filename: filename,
        load_immediately: loadImmediately
      })
    });
    
    if (!response.ok) {
      throw new Error(`Failed to install content pack: ${response.statusText}`);
    }
    
    return response.json();
  }
  
  async searchRemotePacks(query, category = null, tags = []) {
    const response = await fetch(`${this.baseUrl}/api/v1/content-packs/remote/search`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify({
        query: query,
        category: category,
        tags: tags
      })
    });
    
    if (!response.ok) {
      throw new Error(`Failed to search content packs: ${response.statusText}`);
    }
    
    return response.json();
  }
}

// Usage
const manager = new ContentPackManager('http://localhost:8000', 'your-token');

// Search for AI-related content packs
const aiPacks = await manager.searchRemotePacks('artificial intelligence', 'ai', ['machine-learning']);
console.log(`Found ${aiPacks.length} AI content packs`);

// Install the first result
if (aiPacks.length > 0) {
  const result = await manager.installRemotePack(aiPacks[0].filename);
  console.log(result.message);
}
```