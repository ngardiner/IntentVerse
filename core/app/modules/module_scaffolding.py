"""
Module scaffolding tools for creating new IntentVerse modules.
Provides automated generation of module structure and boilerplate code.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ModuleScaffolder:
    """
    Creates new modules with proper structure and boilerplate code.
    """
    
    def __init__(self, modules_base_path: str = "core/app/modules"):
        self.modules_base_path = Path(modules_base_path)
        self.templates_path = Path(__file__).parent / "templates"
        
        # Category-specific configurations
        self.category_configs = {
            "identity": {
                "common_tools": ["list_users", "create_user", "modify_user", "delete_user", "search_users"],
                "common_data_types": ["users", "groups", "roles", "permissions"],
                "description_template": "Identity and access management for {service_name}"
            },
            "infrastructure": {
                "common_tools": ["list_devices", "configure_device", "monitor_status", "backup_config"],
                "common_data_types": ["network_devices", "servers", "configurations"],
                "description_template": "Infrastructure management for {service_name}"
            },
            "cloud": {
                "common_tools": ["list_resources", "create_resource", "modify_resource", "delete_resource", "get_metrics"],
                "common_data_types": ["cloud_resources", "instances", "storage", "networks"],
                "description_template": "Cloud platform management for {service_name}"
            },
            "security": {
                "common_tools": ["scan_vulnerabilities", "generate_report", "remediate_issue", "monitor_threats"],
                "common_data_types": ["security_events", "vulnerabilities", "threats", "policies"],
                "description_template": "Security management and monitoring for {service_name}"
            },
            "devops": {
                "common_tools": ["build_project", "deploy_application", "run_tests", "manage_pipeline"],
                "common_data_types": ["repositories", "builds", "deployments", "pipelines"],
                "description_template": "Development and operations tools for {service_name}"
            },
            "business": {
                "common_tools": ["create_record", "update_record", "search_records", "generate_report"],
                "common_data_types": ["customers", "orders", "products", "transactions"],
                "description_template": "Business application management for {service_name}"
            }
        }
    
    def create_module(self, 
                     module_id: str, 
                     category: str, 
                     display_name: str, 
                     description: Optional[str] = None,
                     service_name: Optional[str] = None,
                     custom_tools: Optional[List[str]] = None) -> bool:
        """
        Create a new module with complete structure.
        
        Args:
            module_id: Unique identifier (e.g., "active_directory")
            category: Module category (e.g., "identity")
            display_name: Human-readable name (e.g., "Active Directory")
            description: Module description
            service_name: Service name for description template
            custom_tools: Custom tool names to include
            
        Returns:
            Success status
        """
        try:
            # Validate inputs
            if not self._validate_module_inputs(module_id, category):
                return False
            
            # Create module directory
            module_path = self.modules_base_path / module_id
            if module_path.exists():
                logger.error(f"Module directory already exists: {module_path}")
                return False
            
            module_path.mkdir(parents=True, exist_ok=True)
            
            # Generate description if not provided
            if not description and service_name and category in self.category_configs:
                description = self.category_configs[category]["description_template"].format(
                    service_name=service_name
                )
            elif not description:
                description = f"Mock {display_name} module for sandbox testing"
            
            # Create module files
            self._create_init_file(module_path)
            self._create_schema_file(module_path, module_id, category, display_name, description)
            self._create_tool_file(module_path, module_id, category, custom_tools)
            
            # Create sample data if category has common data types
            if category in self.category_configs:
                self._create_sample_data(module_path, category)
            
            logger.info(f"Successfully created module: {module_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create module {module_id}: {e}")
            return False
    
    def _validate_module_inputs(self, module_id: str, category: str) -> bool:
        """Validate module creation inputs."""
        valid_categories = [
            "productivity", "identity", "infrastructure", 
            "cloud", "security", "devops", "business"
        ]
        
        if not module_id or not module_id.replace("_", "").isalnum():
            logger.error("Module ID must be alphanumeric with underscores")
            return False
        
        if category not in valid_categories:
            logger.error(f"Category must be one of: {', '.join(valid_categories)}")
            return False
        
        return True
    
    def _create_init_file(self, module_path: Path) -> None:
        """Create __init__.py file for the module."""
        init_content = '''"""
{module_name} module for IntentVerse.
"""

from .tool import {class_name}Tool
from .schema import UI_SCHEMA

__all__ = ["{class_name}Tool", "UI_SCHEMA"]
'''.format(
            module_name=module_path.name.replace("_", " ").title(),
            class_name="".join(word.capitalize() for word in module_path.name.split("_"))
        )
        
        with open(module_path / "__init__.py", "w") as f:
            f.write(init_content)
    
    def _create_schema_file(self, module_path: Path, module_id: str, category: str, 
                           display_name: str, description: str) -> None:
        """Create schema.py file for the module."""
        schema_content = f'''"""
UI Schema for {display_name} module.
"""

UI_SCHEMA = {{
    "module_id": "{module_id}",
    "display_name": "{display_name}",
    "category": "{category}",
    "description": "{description}",
    "is_sandbox": True,
    "default_enabled": False,
    "components": [
        {{
            "id": "{module_id}_dashboard",
            "type": "dashboard",
            "title": "{display_name} Dashboard",
            "description": "Main dashboard for {display_name} management",
            "layout": {{
                "x": 0,
                "y": 0,
                "w": 12,
                "h": 8
            }},
            "props": {{
                "module_id": "{module_id}",
                "show_stats": True,
                "show_recent_activity": True
            }}
        }},
        {{
            "id": "{module_id}_management",
            "type": "management_panel",
            "title": "{display_name} Management",
            "description": "Management interface for {display_name}",
            "layout": {{
                "x": 0,
                "y": 8,
                "w": 12,
                "h": 6
            }},
            "props": {{
                "module_id": "{module_id}",
                "show_actions": True,
                "show_search": True
            }}
        }}
    ]
}}
'''
        
        with open(module_path / "schema.py", "w") as f:
            f.write(schema_content)
    
    def _create_tool_file(self, module_path: Path, module_id: str, category: str, 
                         custom_tools: Optional[List[str]] = None) -> None:
        """Create tool.py file for the module."""
        class_name = "".join(word.capitalize() for word in module_id.split("_"))
        
        # Get tools for this category
        tools = custom_tools or []
        if category in self.category_configs:
            tools.extend(self.category_configs[category]["common_tools"])
        
        # Remove duplicates while preserving order
        tools = list(dict.fromkeys(tools))
        
        tool_methods = []
        for tool in tools:
            method_name = tool.replace("-", "_")
            tool_methods.append(self._generate_tool_method(method_name, tool))
        
        tool_content = f'''"""
{class_name} tool implementation.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
from ..base_module_template import SandboxModule
from ..mock_data_generator import MockDataGenerator

logger = logging.getLogger(__name__)


class {class_name}Tool(SandboxModule):
    """
    {class_name} module implementation for sandbox environment.
    """
    
    def __init__(self):
        super().__init__(
            module_id="{module_id}",
            category="{category}",
            display_name="{class_name.replace('_', ' ')}",
            description="Mock {class_name.replace('_', ' ').lower()} module for sandbox testing"
        )
        self.mock_generator = MockDataGenerator()
        self.initialize_mock_data()
    
    def get_schema(self) -> Dict[str, Any]:
        """Return the UI schema for this module."""
        from .schema import UI_SCHEMA
        return UI_SCHEMA
    
    def initialize_mock_data(self) -> Dict[str, Any]:
        """Initialize mock data for the module."""
        mock_data = {{
            "initialized_at": datetime.utcnow().isoformat(),
            "module_id": self.module_id,
            "data_version": "1.0.0"
        }}
        
        # Add category-specific mock data
        {self._generate_mock_data_initialization(category)}
        
        self.mock_data = mock_data
        return mock_data
    
    def get_tools(self) -> Dict[str, Any]:
        """Return available tools for this module."""
        return {{
{self._generate_tools_dict(tools)}
        }}

{chr(10).join(tool_methods)}
    
    def get_status(self) -> Dict[str, Any]:
        """Get module status and statistics."""
        return {{
            "module_id": self.module_id,
            "status": "active",
            "mock_data_loaded": bool(self.mock_data),
            "tools_available": len(self.get_tools()),
            "last_updated": datetime.utcnow().isoformat(),
            "is_sandbox": True
        }}
'''
        
        with open(module_path / "tool.py", "w") as f:
            f.write(tool_content)
    
    def _generate_tool_method(self, method_name: str, tool_display_name: str) -> str:
        """Generate a tool method implementation."""
        return f'''    def {method_name}(self, **kwargs) -> Dict[str, Any]:
        """
        {tool_display_name.replace('_', ' ').title()} operation.
        
        Args:
            **kwargs: Tool-specific parameters
            
        Returns:
            Operation result
        """
        try:
            # Mock implementation
            result = {{
                "tool": "{tool_display_name}",
                "status": "success",
                "timestamp": datetime.utcnow().isoformat(),
                "data": {{"message": "Mock {tool_display_name.replace('_', ' ')} operation completed"}},
                "is_sandbox": True
            }}
            
            logger.info(f"Executed {tool_display_name} with args: {{kwargs}}")
            return result
            
        except Exception as e:
            logger.error(f"Error in {tool_display_name}: {{e}}")
            return {{
                "tool": "{tool_display_name}",
                "status": "error",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "is_sandbox": True
            }}'''
    
    def _generate_tools_dict(self, tools: List[str]) -> str:
        """Generate the tools dictionary for get_tools method."""
        tools_entries = []
        for tool in tools:
            method_name = tool.replace("-", "_")
            tools_entries.append(f'''            "{tool}": {{
                "name": "{tool}",
                "description": "Mock {tool.replace('_', ' ')} operation",
                "method": self.{method_name},
                "parameters": {{}},
                "is_sandbox": True
            }}''')
        return ",\n".join(tools_entries)
    
    def _generate_mock_data_initialization(self, category: str) -> str:
        """Generate mock data initialization code for category."""
        if category not in self.category_configs:
            return '        # No specific mock data for this category'
        
        data_types = self.category_configs[category]["common_data_types"]
        init_lines = []
        
        for data_type in data_types:
            if data_type == "users":
                init_lines.append('        mock_data["users"] = self.mock_generator.generate_users(20)')
            elif data_type == "servers":
                init_lines.append('        mock_data["servers"] = self.mock_generator.generate_servers(15)')
            elif data_type == "network_devices":
                init_lines.append('        mock_data["network_devices"] = self.mock_generator.generate_network_devices(10)')
            elif data_type == "cloud_resources":
                init_lines.append('        mock_data["cloud_resources"] = self.mock_generator.generate_cloud_resources(25)')
            elif data_type == "security_events":
                init_lines.append('        mock_data["security_events"] = self.mock_generator.generate_security_events(50)')
            else:
                init_lines.append(f'        mock_data["{data_type}"] = []  # TODO: Implement {data_type} generation')
        
        return "\n".join(init_lines) if init_lines else '        # No specific mock data for this category'
    
    def _create_sample_data(self, module_path: Path, category: str) -> None:
        """Create sample data file for the module."""
        if category not in self.category_configs:
            return
        
        generator = MockDataGenerator()
        sample_data = {
            "module_info": {
                "category": category,
                "created_at": datetime.utcnow().isoformat(),
                "data_version": "1.0.0"
            }
        }
        
        # Generate sample data based on category
        data_types = self.category_configs[category]["common_data_types"]
        for data_type in data_types:
            method_name = f"generate_{data_type}"
            if hasattr(generator, method_name):
                method = getattr(generator, method_name)
                sample_data[data_type] = method(10)
            else:
                # Handle data types that don't have direct generator methods
                if data_type == "groups":
                    sample_data[data_type] = [{"id": f"group_{i}", "name": f"Group {i}"} for i in range(1, 11)]
                elif data_type == "roles":
                    sample_data[data_type] = [{"id": f"role_{i}", "name": f"Role {i}"} for i in range(1, 6)]
                elif data_type == "permissions":
                    sample_data[data_type] = [{"id": f"perm_{i}", "name": f"Permission {i}"} for i in range(1, 16)]
                else:
                    sample_data[data_type] = []
        
        # Save sample data
        with open(module_path / "sample_data.py", "w") as f:
            f.write(f'''"""
Sample data for {module_path.name} module.
"""

SAMPLE_DATA = {json.dumps(sample_data, indent=4, default=str)}
''')
    
    def list_available_modules(self) -> List[Dict[str, Any]]:
        """List all available modules."""
        modules = []
        
        if not self.modules_base_path.exists():
            return modules
        
        for module_dir in self.modules_base_path.iterdir():
            if module_dir.is_dir() and (module_dir / "__init__.py").exists():
                try:
                    # Try to get module info
                    schema_file = module_dir / "schema.py"
                    if schema_file.exists():
                        # Read schema to get module info
                        with open(schema_file, 'r') as f:
                            content = f.read()
                            # Simple extraction (could be improved with AST parsing)
                            if 'UI_SCHEMA' in content:
                                modules.append({
                                    "module_id": module_dir.name,
                                    "path": str(module_dir),
                                    "has_schema": True,
                                    "has_tool": (module_dir / "tool.py").exists(),
                                    "has_sample_data": (module_dir / "sample_data.py").exists()
                                })
                except Exception as e:
                    logger.warning(f"Could not read module info for {module_dir.name}: {e}")
        
        return modules
    
    def generate_module_documentation(self, module_id: str) -> str:
        """Generate documentation for a module."""
        module_path = self.modules_base_path / module_id
        
        if not module_path.exists():
            return f"Module {module_id} not found"
        
        doc_lines = [
            f"# {module_id.replace('_', ' ').title()} Module",
            "",
            f"**Module ID:** `{module_id}`",
            f"**Path:** `{module_path}`",
            "",
            "## Files",
            ""
        ]
        
        # List files
        for file_path in module_path.iterdir():
            if file_path.is_file():
                doc_lines.append(f"- `{file_path.name}`")
        
        doc_lines.extend([
            "",
            "## Usage",
            "",
            f"```python",
            f"from core.app.modules.{module_id} import {module_id.replace('_', ' ').title().replace(' ', '')}Tool",
            f"",
            f"tool = {module_id.replace('_', ' ').title().replace(' ', '')}Tool()",
            f"schema = tool.get_schema()",
            f"tools = tool.get_tools()",
            f"```",
            ""
        ])
        
        return "\n".join(doc_lines)