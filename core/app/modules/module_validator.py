"""
Module validation system for IntentVerse modules.
Provides comprehensive validation and health checking for modules.
"""

import importlib
import inspect
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ModuleValidator:
    """
    Validates module structure, implementation, and health.
    """
    
    def __init__(self, modules_base_path: str = "core/app/modules"):
        self.modules_base_path = Path(modules_base_path)
        self.validation_rules = {
            "required_files": ["__init__.py", "schema.py", "tool.py"],
            "required_schema_fields": ["module_id", "display_name", "category", "description"],
            "required_tool_methods": ["get_schema", "initialize_mock_data", "get_tools"],
            "valid_categories": [
                "productivity", "identity", "infrastructure", 
                "cloud", "security", "devops", "business"
            ]
        }
    
    def validate_module(self, module_id: str) -> Dict[str, Any]:
        """
        Perform comprehensive validation of a module.
        
        Args:
            module_id: ID of the module to validate
            
        Returns:
            Validation results
        """
        validation_result = {
            "module_id": module_id,
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": "unknown",
            "checks": {},
            "errors": [],
            "warnings": [],
            "recommendations": []
        }
        
        try:
            module_path = self.modules_base_path / module_id
            
            # Check if module directory exists
            if not module_path.exists():
                validation_result["overall_status"] = "failed"
                validation_result["errors"].append(f"Module directory not found: {module_path}")
                return validation_result
            
            # Perform individual checks
            validation_result["checks"]["file_structure"] = self._check_file_structure(module_path)
            validation_result["checks"]["schema_validation"] = self._check_schema(module_path)
            validation_result["checks"]["tool_implementation"] = self._check_tool_implementation(module_path, module_id)
            validation_result["checks"]["import_validation"] = self._check_imports(module_id)
            validation_result["checks"]["sandbox_safety"] = self._check_sandbox_safety(module_path)
            
            # Collect errors and warnings
            for check_name, check_result in validation_result["checks"].items():
                if check_result.get("errors"):
                    validation_result["errors"].extend(check_result["errors"])
                if check_result.get("warnings"):
                    validation_result["warnings"].extend(check_result["warnings"])
            
            # Determine overall status
            if validation_result["errors"]:
                validation_result["overall_status"] = "failed"
            elif validation_result["warnings"]:
                validation_result["overall_status"] = "warning"
            else:
                validation_result["overall_status"] = "passed"
            
            # Generate recommendations
            validation_result["recommendations"] = self._generate_recommendations(validation_result)
            
        except Exception as e:
            logger.error(f"Validation failed for module {module_id}: {e}")
            validation_result["overall_status"] = "error"
            validation_result["errors"].append(f"Validation error: {str(e)}")
        
        return validation_result
    
    def _check_file_structure(self, module_path: Path) -> Dict[str, Any]:
        """Check if module has required file structure."""
        result = {
            "status": "passed",
            "errors": [],
            "warnings": [],
            "details": {}
        }
        
        # Check required files
        for required_file in self.validation_rules["required_files"]:
            file_path = module_path / required_file
            exists = file_path.exists()
            result["details"][required_file] = {
                "exists": exists,
                "path": str(file_path)
            }
            
            if not exists:
                result["errors"].append(f"Missing required file: {required_file}")
                result["status"] = "failed"
        
        # Check for optional files
        optional_files = ["sample_data.py", "README.md"]
        for optional_file in optional_files:
            file_path = module_path / optional_file
            if file_path.exists():
                result["details"][optional_file] = {
                    "exists": True,
                    "path": str(file_path)
                }
            else:
                result["warnings"].append(f"Optional file not found: {optional_file}")
        
        return result
    
    def _check_schema(self, module_path: Path) -> Dict[str, Any]:
        """Check schema.py file for required structure."""
        result = {
            "status": "passed",
            "errors": [],
            "warnings": [],
            "details": {}
        }
        
        schema_file = module_path / "schema.py"
        if not schema_file.exists():
            result["errors"].append("schema.py file not found")
            result["status"] = "failed"
            return result
        
        try:
            # Read and parse schema file
            with open(schema_file, 'r') as f:
                content = f.read()
            
            # Check for UI_SCHEMA definition
            if "UI_SCHEMA" not in content:
                result["errors"].append("UI_SCHEMA not found in schema.py")
                result["status"] = "failed"
            
            # Try to import and validate schema
            module_name = f"core.app.modules.{module_path.name}.schema"
            try:
                spec = importlib.util.spec_from_file_location(module_name, schema_file)
                schema_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(schema_module)
                
                if hasattr(schema_module, 'UI_SCHEMA'):
                    schema = schema_module.UI_SCHEMA
                    result["details"]["schema_content"] = schema
                    
                    # Validate required fields
                    for field in self.validation_rules["required_schema_fields"]:
                        if field not in schema:
                            result["errors"].append(f"Missing required schema field: {field}")
                            result["status"] = "failed"
                    
                    # Validate category
                    category = schema.get("category")
                    if category not in self.validation_rules["valid_categories"]:
                        result["errors"].append(f"Invalid category: {category}")
                        result["status"] = "failed"
                    
                    # Check for components
                    if "components" not in schema or not isinstance(schema["components"], list):
                        result["warnings"].append("No components defined in schema")
                    
                else:
                    result["errors"].append("UI_SCHEMA not accessible in schema module")
                    result["status"] = "failed"
                    
            except Exception as e:
                result["errors"].append(f"Failed to import schema: {str(e)}")
                result["status"] = "failed"
        
        except Exception as e:
            result["errors"].append(f"Failed to read schema file: {str(e)}")
            result["status"] = "failed"
        
        return result
    
    def _check_tool_implementation(self, module_path: Path, module_id: str) -> Dict[str, Any]:
        """Check tool.py implementation."""
        result = {
            "status": "passed",
            "errors": [],
            "warnings": [],
            "details": {}
        }
        
        tool_file = module_path / "tool.py"
        if not tool_file.exists():
            result["errors"].append("tool.py file not found")
            result["status"] = "failed"
            return result
        
        try:
            # Try to import the tool module
            module_name = f"core.app.modules.{module_id}.tool"
            spec = importlib.util.spec_from_file_location(module_name, tool_file)
            tool_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(tool_module)
            
            # Find the tool class
            tool_class = None
            for name, obj in inspect.getmembers(tool_module):
                if (inspect.isclass(obj) and 
                    name.endswith('Tool') and 
                    obj.__module__ == module_name):
                    tool_class = obj
                    break
            
            if not tool_class:
                result["errors"].append("No tool class found (should end with 'Tool')")
                result["status"] = "failed"
                return result
            
            result["details"]["tool_class"] = tool_class.__name__
            
            # Check required methods
            for method_name in self.validation_rules["required_tool_methods"]:
                if not hasattr(tool_class, method_name):
                    result["errors"].append(f"Missing required method: {method_name}")
                    result["status"] = "failed"
                else:
                    method = getattr(tool_class, method_name)
                    if not callable(method):
                        result["errors"].append(f"Method {method_name} is not callable")
                        result["status"] = "failed"
            
            # Try to instantiate the tool
            try:
                tool_instance = tool_class()
                result["details"]["instantiation"] = "success"
                
                # Test required methods
                try:
                    schema = tool_instance.get_schema()
                    if not isinstance(schema, dict):
                        result["errors"].append("get_schema() must return a dictionary")
                        result["status"] = "failed"
                except Exception as e:
                    result["errors"].append(f"get_schema() failed: {str(e)}")
                    result["status"] = "failed"
                
                try:
                    tools = tool_instance.get_tools()
                    if not isinstance(tools, dict):
                        result["errors"].append("get_tools() must return a dictionary")
                        result["status"] = "failed"
                    else:
                        result["details"]["tools_count"] = len(tools)
                except Exception as e:
                    result["errors"].append(f"get_tools() failed: {str(e)}")
                    result["status"] = "failed"
                
                try:
                    mock_data = tool_instance.initialize_mock_data()
                    if not isinstance(mock_data, dict):
                        result["errors"].append("initialize_mock_data() must return a dictionary")
                        result["status"] = "failed"
                except Exception as e:
                    result["errors"].append(f"initialize_mock_data() failed: {str(e)}")
                    result["status"] = "failed"
                
            except Exception as e:
                result["errors"].append(f"Failed to instantiate tool class: {str(e)}")
                result["status"] = "failed"
        
        except Exception as e:
            result["errors"].append(f"Failed to import tool module: {str(e)}")
            result["status"] = "failed"
        
        return result
    
    def _check_imports(self, module_id: str) -> Dict[str, Any]:
        """Check if module can be imported correctly."""
        result = {
            "status": "passed",
            "errors": [],
            "warnings": [],
            "details": {}
        }
        
        try:
            # Try to import the module
            module_name = f"core.app.modules.{module_id}"
            module = importlib.import_module(module_name)
            
            # Check for expected exports
            expected_exports = ["UI_SCHEMA"]
            for export in expected_exports:
                if hasattr(module, export):
                    result["details"][f"has_{export.lower()}"] = True
                else:
                    result["warnings"].append(f"Missing export: {export}")
            
            # Check for tool class export
            tool_class_found = False
            for attr_name in dir(module):
                if attr_name.endswith('Tool'):
                    tool_class_found = True
                    result["details"]["tool_class_export"] = attr_name
                    break
            
            if not tool_class_found:
                result["warnings"].append("No tool class exported")
        
        except Exception as e:
            result["errors"].append(f"Import failed: {str(e)}")
            result["status"] = "failed"
        
        return result
    
    def _check_sandbox_safety(self, module_path: Path) -> Dict[str, Any]:
        """Check for sandbox safety indicators."""
        result = {
            "status": "passed",
            "errors": [],
            "warnings": [],
            "details": {}
        }
        
        # Check for sandbox indicators in files
        safety_indicators = ["is_sandbox", "sandbox", "mock", ".local", ".test"]
        files_to_check = ["tool.py", "schema.py"]
        
        for file_name in files_to_check:
            file_path = module_path / file_name
            if file_path.exists():
                try:
                    with open(file_path, 'r') as f:
                        content = f.read()
                    
                    found_indicators = []
                    for indicator in safety_indicators:
                        if indicator in content:
                            found_indicators.append(indicator)
                    
                    result["details"][file_name] = {
                        "safety_indicators": found_indicators,
                        "indicator_count": len(found_indicators)
                    }
                    
                    if not found_indicators:
                        result["warnings"].append(f"No sandbox safety indicators found in {file_name}")
                
                except Exception as e:
                    result["warnings"].append(f"Could not check {file_name}: {str(e)}")
        
        return result
    
    def _generate_recommendations(self, validation_result: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []
        
        # File structure recommendations
        file_check = validation_result["checks"].get("file_structure", {})
        if "sample_data.py" not in file_check.get("details", {}):
            recommendations.append("Consider adding sample_data.py for better mock data organization")
        
        if "README.md" not in file_check.get("details", {}):
            recommendations.append("Add README.md with module documentation")
        
        # Schema recommendations
        schema_check = validation_result["checks"].get("schema_validation", {})
        schema_content = schema_check.get("details", {}).get("schema_content", {})
        if not schema_content.get("components"):
            recommendations.append("Add UI components to schema for better user experience")
        
        # Tool recommendations
        tool_check = validation_result["checks"].get("tool_implementation", {})
        tools_count = tool_check.get("details", {}).get("tools_count", 0)
        if tools_count < 3:
            recommendations.append("Consider adding more tools for comprehensive functionality")
        
        # Safety recommendations
        safety_check = validation_result["checks"].get("sandbox_safety", {})
        for file_name, file_details in safety_check.get("details", {}).items():
            if file_details.get("indicator_count", 0) < 2:
                recommendations.append(f"Add more sandbox safety indicators to {file_name}")
        
        return recommendations
    
    def validate_all_modules(self) -> Dict[str, Any]:
        """Validate all modules in the modules directory."""
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_modules": 0,
            "passed": 0,
            "failed": 0,
            "warnings": 0,
            "modules": {}
        }
        
        if not self.modules_base_path.exists():
            return results
        
        for module_dir in self.modules_base_path.iterdir():
            if module_dir.is_dir() and not module_dir.name.startswith('.'):
                module_id = module_dir.name
                validation_result = self.validate_module(module_id)
                results["modules"][module_id] = validation_result
                results["total_modules"] += 1
                
                if validation_result["overall_status"] == "passed":
                    results["passed"] += 1
                elif validation_result["overall_status"] == "failed":
                    results["failed"] += 1
                elif validation_result["overall_status"] == "warning":
                    results["warnings"] += 1
        
        return results
    
    def get_module_health_summary(self) -> Dict[str, Any]:
        """Get a summary of all module health status."""
        validation_results = self.validate_all_modules()
        
        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_health": "healthy",
            "statistics": {
                "total_modules": validation_results["total_modules"],
                "healthy_modules": validation_results["passed"],
                "unhealthy_modules": validation_results["failed"],
                "modules_with_warnings": validation_results["warnings"]
            },
            "recommendations": [],
            "critical_issues": []
        }
        
        # Determine overall health
        if validation_results["failed"] > 0:
            summary["overall_health"] = "unhealthy"
        elif validation_results["warnings"] > 0:
            summary["overall_health"] = "warning"
        
        # Collect critical issues and recommendations
        for module_id, module_result in validation_results["modules"].items():
            if module_result["overall_status"] == "failed":
                summary["critical_issues"].extend([
                    f"{module_id}: {error}" for error in module_result["errors"]
                ])
            
            summary["recommendations"].extend([
                f"{module_id}: {rec}" for rec in module_result["recommendations"]
            ])
        
        return summary