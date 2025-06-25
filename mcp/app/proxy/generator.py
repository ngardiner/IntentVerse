"""
Proxy Tool Generator for MCP Proxy Engine.

This module provides the ProxyToolGenerator class that creates dynamic proxy
functions for external MCP tools, handling parameter mapping, validation,
and result processing.
"""

import asyncio
import inspect
import logging
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass
from functools import wraps

from .client import MCPTool
from .discovery import ToolDiscoveryService

logger = logging.getLogger(__name__)


@dataclass
class ProxyFunctionMetadata:
    """Metadata for a generated proxy function."""
    original_tool: MCPTool
    server_name: str
    original_name: str
    proxy_name: str
    parameter_mapping: Dict[str, str]
    created_at: float
    
    def __str__(self) -> str:
        return f"ProxyFunction({self.proxy_name} -> {self.server_name}.{self.original_name})"


class ParameterValidator:
    """Validates and converts parameters for proxy function calls."""
    
    def __init__(self, tool: MCPTool):
        """
        Initialize parameter validator.
        
        Args:
            tool: The MCP tool to validate parameters for
        """
        self.tool = tool
        self.schema = tool.input_schema
        self.properties = self.schema.get("properties", {})
        self.required = set(self.schema.get("required", []))
    
    def validate_and_convert(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and convert parameters according to the tool's schema.
        
        Args:
            kwargs: Parameters to validate
            
        Returns:
            Validated and converted parameters
            
        Raises:
            ValueError: If validation fails
        """
        validated = {}
        
        # Check for required parameters
        missing_required = self.required - set(kwargs.keys())
        if missing_required:
            raise ValueError(f"Missing required parameters: {', '.join(missing_required)}")
        
        # Validate and convert each parameter
        for param_name, param_value in kwargs.items():
            if param_name not in self.properties:
                # Allow extra parameters (some tools might accept them)
                validated[param_name] = param_value
                continue
            
            param_schema = self.properties[param_name]
            validated_value = self._validate_parameter(param_name, param_value, param_schema)
            validated[param_name] = validated_value
        
        # Add default values for missing optional parameters
        for param_name, param_schema in self.properties.items():
            if param_name not in validated and "default" in param_schema:
                validated[param_name] = param_schema["default"]
        
        return validated
    
    def _validate_parameter(self, name: str, value: Any, schema: Dict[str, Any]) -> Any:
        """
        Validate a single parameter.
        
        Args:
            name: Parameter name
            value: Parameter value
            schema: Parameter schema
            
        Returns:
            Validated value
            
        Raises:
            ValueError: If validation fails
        """
        param_type = schema.get("type", "string")
        
        # Handle None values
        if value is None:
            if name in self.required:
                raise ValueError(f"Required parameter '{name}' cannot be None")
            return value
        
        # Type validation and conversion
        try:
            if param_type == "string":
                return str(value)
            elif param_type == "integer":
                if isinstance(value, bool):
                    raise ValueError(f"Parameter '{name}' expected integer, got boolean")
                return int(value)
            elif param_type == "number":
                return float(value)
            elif param_type == "boolean":
                if isinstance(value, str):
                    if value.lower() in ("true", "1", "yes", "on"):
                        return True
                    elif value.lower() in ("false", "0", "no", "off"):
                        return False
                    else:
                        raise ValueError(f"Cannot convert string '{value}' to boolean")
                return bool(value)
            elif param_type == "array":
                if not isinstance(value, (list, tuple)):
                    raise ValueError(f"Parameter '{name}' expected array, got {type(value).__name__}")
                return list(value)
            elif param_type == "object":
                if not isinstance(value, dict):
                    raise ValueError(f"Parameter '{name}' expected object, got {type(value).__name__}")
                return value
            else:
                # Unknown type, return as-is
                return value
                
        except (ValueError, TypeError) as e:
            raise ValueError(f"Parameter '{name}' validation failed: {e}")
    
    def get_parameter_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all parameters."""
        info = {}
        for param_name, param_schema in self.properties.items():
            info[param_name] = {
                "type": param_schema.get("type", "string"),
                "description": param_schema.get("description", ""),
                "required": param_name in self.required,
                "default": param_schema.get("default"),
                "enum": param_schema.get("enum"),
                "minimum": param_schema.get("minimum"),
                "maximum": param_schema.get("maximum"),
                "pattern": param_schema.get("pattern")
            }
        return info


class ResultProcessor:
    """Processes results from MCP tool calls."""
    
    @staticmethod
    def process_result(result: Any, tool: MCPTool) -> Any:
        """
        Process the result from an MCP tool call.
        
        Args:
            result: Raw result from MCP tool
            tool: The tool that was called
            
        Returns:
            Processed result
        """
        # If result is already a simple type, return as-is
        if isinstance(result, (str, int, float, bool, type(None))):
            return result
        
        # Handle MCP content format
        if isinstance(result, dict):
            # Check for MCP content array format
            if "content" in result:
                content = result["content"]
                if isinstance(content, list) and len(content) > 0:
                    # Extract text from first content item
                    first_content = content[0]
                    if isinstance(first_content, dict) and "text" in first_content:
                        return first_content["text"]
                    elif isinstance(first_content, dict) and "data" in first_content:
                        return first_content["data"]
            
            # Check for direct result field
            if "result" in result:
                return result["result"]
            
            # Return the dict as-is if no special processing needed
            return result
        
        # Handle list results
        if isinstance(result, list):
            # If it's a list of content items, extract text
            if len(result) > 0 and isinstance(result[0], dict):
                if "text" in result[0]:
                    return result[0]["text"]
                elif "data" in result[0]:
                    return result[0]["data"]
        
        # Return as-is for other types
        return result


class ProxyToolGenerator:
    """
    Generates dynamic proxy functions for MCP tools.
    
    Creates Python functions that can be called like regular functions
    but proxy the calls to external MCP servers through the discovery service.
    """
    
    def __init__(self, discovery_service: ToolDiscoveryService):
        """
        Initialize the proxy tool generator.
        
        Args:
            discovery_service: The tool discovery service to use for tool calls
        """
        self.discovery_service = discovery_service
        self._generated_functions: Dict[str, Callable] = {}
        self._function_metadata: Dict[str, ProxyFunctionMetadata] = {}
    
    def generate_proxy_function(self, tool: MCPTool) -> Callable:
        """
        Generate a proxy function for an MCP tool.
        
        Args:
            tool: The MCP tool to create a proxy for
            
        Returns:
            A callable proxy function
        """
        # Create parameter validator
        validator = ParameterValidator(tool)
        
        # Get parameter information for signature generation
        param_info = validator.get_parameter_info()
        
        # Create the proxy function
        async def proxy_function(**kwargs) -> Any:
            """
            Dynamically generated proxy function for MCP tool.
            
            This function validates parameters, calls the external MCP tool,
            and processes the result.
            """
            try:
                # Log the call
                logger.debug(f"Calling proxy function for tool: {tool.name}")
                
                # Validate and convert parameters
                validated_params = validator.validate_and_convert(kwargs)
                
                # Call the tool through the discovery service
                result = await self.discovery_service.call_tool(tool.name, validated_params)
                
                # Process the result
                processed_result = ResultProcessor.process_result(result, tool)
                
                logger.debug(f"Proxy function call completed for: {tool.name}")
                return processed_result
                
            except Exception as e:
                logger.error(f"Proxy function call failed for {tool.name}: {e}")
                raise
        
        # Set function metadata
        proxy_function.__name__ = tool.name
        proxy_function.__doc__ = self._generate_docstring(tool, param_info)
        
        # Create function signature dynamically
        self._set_function_signature(proxy_function, param_info)
        
        # Store metadata
        metadata = ProxyFunctionMetadata(
            original_tool=tool,
            server_name=tool.server_name,
            original_name=tool.to_core_tool_format()["metadata"]["original_name"],
            proxy_name=tool.name,
            parameter_mapping={},  # Could be used for parameter name mapping
            created_at=asyncio.get_event_loop().time()
        )
        
        self._function_metadata[tool.name] = metadata
        self._generated_functions[tool.name] = proxy_function
        
        logger.info(f"Generated proxy function: {tool.name} -> {tool.server_name}")
        return proxy_function
    
    def _generate_docstring(self, tool: MCPTool, param_info: Dict[str, Dict[str, Any]]) -> str:
        """Generate docstring for the proxy function."""
        lines = [
            f"{tool.description}",
            "",
            f"This is a proxy function for the '{tool.to_core_tool_format()['metadata']['original_name']}' tool",
            f"from the '{tool.server_name}' MCP server.",
            "",
            "Args:"
        ]
        
        # Add parameter documentation
        for param_name, info in param_info.items():
            param_type = info["type"]
            required_str = " (required)" if info["required"] else " (optional)"
            default_str = f", default: {info['default']}" if info["default"] is not None else ""
            
            lines.append(f"    {param_name} ({param_type}){required_str}: {info['description']}{default_str}")
        
        lines.extend([
            "",
            "Returns:",
            "    The result from the MCP tool execution.",
            "",
            "Raises:",
            "    ValueError: If parameter validation fails.",
            "    RuntimeError: If the tool call fails."
        ])
        
        return "\n".join(lines)
    
    def _set_function_signature(self, func: Callable, param_info: Dict[str, Dict[str, Any]]) -> None:
        """Set the function signature dynamically."""
        parameters = []
        
        # Add required parameters first
        for param_name, info in param_info.items():
            if info["required"]:
                param = inspect.Parameter(
                    param_name,
                    inspect.Parameter.KEYWORD_ONLY,
                    annotation=self._get_python_type(info["type"])
                )
                parameters.append(param)
        
        # Add optional parameters with defaults
        for param_name, info in param_info.items():
            if not info["required"]:
                default_value = info["default"] if info["default"] is not None else inspect.Parameter.empty
                param = inspect.Parameter(
                    param_name,
                    inspect.Parameter.KEYWORD_ONLY,
                    default=default_value,
                    annotation=self._get_python_type(info["type"])
                )
                parameters.append(param)
        
        # Create and set the signature
        signature = inspect.Signature(parameters)
        func.__signature__ = signature
    
    def _get_python_type(self, json_type: str) -> type:
        """Convert JSON Schema type to Python type."""
        type_mapping = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "array": list,
            "object": dict
        }
        return type_mapping.get(json_type, str)
    
    def generate_all_proxy_functions(self) -> Dict[str, Callable]:
        """
        Generate proxy functions for all discovered tools.
        
        Returns:
            Dictionary mapping tool names to proxy functions
        """
        logger.info("Generating proxy functions for all discovered tools")
        
        tools = self.discovery_service.get_all_tools()
        generated = {}
        
        for tool in tools:
            try:
                proxy_func = self.generate_proxy_function(tool)
                generated[tool.name] = proxy_func
            except Exception as e:
                logger.error(f"Failed to generate proxy function for {tool.name}: {e}")
        
        logger.info(f"Generated {len(generated)} proxy functions")
        return generated
    
    def get_proxy_function(self, tool_name: str) -> Optional[Callable]:
        """
        Get a generated proxy function by name.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            The proxy function if it exists, None otherwise
        """
        return self._generated_functions.get(tool_name)
    
    def get_function_metadata(self, tool_name: str) -> Optional[ProxyFunctionMetadata]:
        """
        Get metadata for a generated proxy function.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Function metadata if it exists, None otherwise
        """
        return self._function_metadata.get(tool_name)
    
    def get_all_proxy_functions(self) -> Dict[str, Callable]:
        """Get all generated proxy functions."""
        return self._generated_functions.copy()
    
    def get_all_function_metadata(self) -> Dict[str, ProxyFunctionMetadata]:
        """Get metadata for all generated functions."""
        return self._function_metadata.copy()
    
    def remove_proxy_function(self, tool_name: str) -> bool:
        """
        Remove a generated proxy function.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            True if function was removed, False if it didn't exist
        """
        removed_func = self._generated_functions.pop(tool_name, None)
        removed_meta = self._function_metadata.pop(tool_name, None)
        
        if removed_func:
            logger.info(f"Removed proxy function: {tool_name}")
            return True
        return False
    
    def clear_all_functions(self) -> None:
        """Clear all generated proxy functions."""
        count = len(self._generated_functions)
        self._generated_functions.clear()
        self._function_metadata.clear()
        logger.info(f"Cleared {count} proxy functions")
    
    def refresh_proxy_functions(self) -> Dict[str, Callable]:
        """
        Refresh all proxy functions based on current discovered tools.
        
        Returns:
            Dictionary of refreshed proxy functions
        """
        logger.info("Refreshing all proxy functions")
        
        # Clear existing functions
        self.clear_all_functions()
        
        # Generate new functions
        return self.generate_all_proxy_functions()
    
    def validate_tool_call(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        Validate parameters for a tool call without executing it.
        
        Args:
            tool_name: Name of the tool
            **kwargs: Parameters to validate
            
        Returns:
            Validated parameters
            
        Raises:
            ValueError: If tool not found or validation fails
        """
        tool = self.discovery_service.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found")
        
        validator = ParameterValidator(tool)
        return validator.validate_and_convert(kwargs)
    
    def get_tool_parameter_info(self, tool_name: str) -> Optional[Dict[str, Dict[str, Any]]]:
        """
        Get parameter information for a tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Parameter information if tool exists, None otherwise
        """
        tool = self.discovery_service.get_tool(tool_name)
        if not tool:
            return None
        
        validator = ParameterValidator(tool)
        return validator.get_parameter_info()
    
    def get_generation_stats(self) -> Dict[str, Any]:
        """Get statistics about generated proxy functions."""
        return {
            "total_functions": len(self._generated_functions),
            "function_names": list(self._generated_functions.keys()),
            "servers_represented": len(set(
                meta.server_name for meta in self._function_metadata.values()
            )),
            "oldest_function": min(
                (meta.created_at for meta in self._function_metadata.values()),
                default=0
            ),
            "newest_function": max(
                (meta.created_at for meta in self._function_metadata.values()),
                default=0
            )
        }
    
    def __len__(self) -> int:
        """Return number of generated proxy functions."""
        return len(self._generated_functions)
    
    def __contains__(self, tool_name: str) -> bool:
        """Check if a proxy function exists for a tool."""
        return tool_name in self._generated_functions
    
    def __str__(self) -> str:
        return f"ProxyToolGenerator({len(self._generated_functions)} functions)"
    
    def __repr__(self) -> str:
        return (f"ProxyToolGenerator(functions={list(self._generated_functions.keys())}, "
                f"discovery_service={self.discovery_service})")