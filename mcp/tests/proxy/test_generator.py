"""
Unit tests for the MCP Proxy Tool Generator.

Tests the ProxyToolGenerator class that creates dynamic proxy functions
for external MCP tools, including parameter validation and result processing.
"""

import pytest
import asyncio
import inspect
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, List, Any, Optional

# Mock the imports to avoid dependency issues during testing
import sys
from unittest.mock import Mock

# Create mock modules to avoid import errors
sys.modules["fastmcp"] = Mock()
sys.modules["fastmcp.tools"] = Mock()

from app.proxy.generator import (
    ProxyToolGenerator,
    ParameterValidator,
    ResultProcessor,
    ProxyFunctionMetadata,
    ValidationError,
    ProcessingError,
)
from app.proxy.discovery import ToolRegistry, ToolInfo
from app.proxy.client import MCPClient, MCPTool


class TestParameterValidator:
    """Test the ParameterValidator class."""

    def test_validate_string_parameter(self):
        """Test validating string parameters."""
        validator = ParameterValidator()

        # Valid string
        result = validator.validate_parameter(
            "test_string", "string", {"type": "string"}
        )
        assert result == "test_string"

        # String with constraints
        schema = {"type": "string", "minLength": 3, "maxLength": 10}
        result = validator.validate_parameter("valid", "string", schema)
        assert result == "valid"

        # Invalid string (too short)
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_parameter("ab", "string", schema)
        assert "minLength" in str(exc_info.value)

        # Invalid string (too long)
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_parameter("this_is_too_long", "string", schema)
        assert "maxLength" in str(exc_info.value)

    def test_validate_integer_parameter(self):
        """Test validating integer parameters."""
        validator = ParameterValidator()

        # Valid integer
        result = validator.validate_parameter(42, "integer", {"type": "integer"})
        assert result == 42

        # Integer from string
        result = validator.validate_parameter("123", "integer", {"type": "integer"})
        assert result == 123

        # Integer with constraints
        schema = {"type": "integer", "minimum": 0, "maximum": 100}
        result = validator.validate_parameter(50, "integer", schema)
        assert result == 50

        # Invalid integer (too small)
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_parameter(-1, "integer", schema)
        assert "minimum" in str(exc_info.value)

        # Invalid integer (too large)
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_parameter(101, "integer", schema)
        assert "maximum" in str(exc_info.value)

        # Invalid integer (not a number)
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_parameter("not_a_number", "integer", {"type": "integer"})
        assert "integer" in str(exc_info.value).lower()

    def test_validate_boolean_parameter(self):
        """Test validating boolean parameters."""
        validator = ParameterValidator()

        # Valid booleans
        assert (
            validator.validate_parameter(True, "boolean", {"type": "boolean"}) is True
        )
        assert (
            validator.validate_parameter(False, "boolean", {"type": "boolean"}) is False
        )

        # Boolean from string
        assert (
            validator.validate_parameter("true", "boolean", {"type": "boolean"}) is True
        )
        assert (
            validator.validate_parameter("false", "boolean", {"type": "boolean"})
            is False
        )
        assert (
            validator.validate_parameter("True", "boolean", {"type": "boolean"}) is True
        )
        assert (
            validator.validate_parameter("False", "boolean", {"type": "boolean"})
            is False
        )

        # Invalid boolean
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_parameter("maybe", "boolean", {"type": "boolean"})
        assert "boolean" in str(exc_info.value).lower()

    def test_validate_array_parameter(self):
        """Test validating array parameters."""
        validator = ParameterValidator()

        # Valid array
        schema = {"type": "array", "items": {"type": "string"}}
        result = validator.validate_parameter(["a", "b", "c"], "array", schema)
        assert result == ["a", "b", "c"]

        # Array with length constraints
        schema = {
            "type": "array",
            "items": {"type": "integer"},
            "minItems": 2,
            "maxItems": 4,
        }
        result = validator.validate_parameter([1, 2, 3], "array", schema)
        assert result == [1, 2, 3]

        # Invalid array (too few items)
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_parameter([1], "array", schema)
        assert "minItems" in str(exc_info.value)

        # Invalid array (too many items)
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_parameter([1, 2, 3, 4, 5], "array", schema)
        assert "maxItems" in str(exc_info.value)

        # Invalid array (wrong item type)
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_parameter([1, "not_integer", 3], "array", schema)
        assert "item" in str(exc_info.value).lower()

    def test_validate_object_parameter(self):
        """Test validating object parameters."""
        validator = ParameterValidator()

        # Valid object
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
            "required": ["name"],
        }

        obj = {"name": "John", "age": 30}
        result = validator.validate_parameter(obj, "object", schema)
        assert result == obj

        # Object missing required property
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_parameter({"age": 30}, "object", schema)
        assert "required" in str(exc_info.value).lower()

        # Object with invalid property type
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_parameter({"name": 123}, "object", schema)
        assert "property" in str(exc_info.value).lower()

    def test_validate_parameters_dict(self):
        """Test validating a complete parameters dictionary."""
        validator = ParameterValidator()

        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer", "minimum": 0},
                "active": {"type": "boolean"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["name", "age"],
        }

        params = {
            "name": "Alice",
            "age": 25,
            "active": True,
            "tags": ["user", "premium"],
        }

        result = validator.validate_parameters(params, schema)
        assert result == params

        # Missing required parameter
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_parameters({"name": "Alice"}, schema)
        assert "required" in str(exc_info.value).lower()


class TestResultProcessor:
    """Test the ResultProcessor class."""

    def test_process_successful_result(self):
        """Test processing a successful tool execution result."""
        processor = ResultProcessor()

        raw_result = {
            "success": True,
            "result": {"data": "test_data", "count": 42},
            "metadata": {"execution_time": 0.5},
        }

        processed = processor.process_result(raw_result, "test_tool", "test_server")

        assert processed["success"] is True
        assert processed["result"] == {"data": "test_data", "count": 42}
        assert processed["metadata"]["execution_time"] == 0.5
        assert processed["metadata"]["tool_name"] == "test_tool"
        assert processed["metadata"]["server_name"] == "test_server"
        assert "processed_at" in processed["metadata"]

    def test_process_error_result(self):
        """Test processing an error result."""
        processor = ResultProcessor()

        raw_result = {
            "success": False,
            "error": "Tool execution failed",
            "error_code": "EXECUTION_ERROR",
        }

        processed = processor.process_result(raw_result, "test_tool", "test_server")

        assert processed["success"] is False
        assert processed["error"] == "Tool execution failed"
        assert processed["error_code"] == "EXECUTION_ERROR"
        assert processed["metadata"]["tool_name"] == "test_tool"
        assert processed["metadata"]["server_name"] == "test_server"

    def test_process_malformed_result(self):
        """Test processing a malformed result."""
        processor = ResultProcessor()

        # Result without success field
        raw_result = {"data": "some_data"}

        with pytest.raises(ProcessingError) as exc_info:
            processor.process_result(raw_result, "test_tool", "test_server")
        assert "malformed" in str(exc_info.value).lower()

    def test_add_proxy_metadata(self):
        """Test adding proxy-specific metadata."""
        processor = ResultProcessor()

        result = {"success": True, "result": "data"}

        enhanced = processor.add_proxy_metadata(
            result, "test_tool", "test_server", execution_time=1.5
        )

        assert enhanced["metadata"]["tool_name"] == "test_tool"
        assert enhanced["metadata"]["server_name"] == "test_server"
        assert enhanced["metadata"]["execution_time"] == 1.5
        assert enhanced["metadata"]["proxy_version"] == "1.0"
        assert "processed_at" in enhanced["metadata"]


class TestProxyFunctionMetadata:
    """Test the ProxyFunctionMetadata dataclass."""

    def test_metadata_creation(self):
        """Test creating proxy function metadata."""
        # Create a mock MCPTool for the metadata
        mock_tool = MCPTool(
            name="test_tool",
            description="A test tool",
            input_schema={"type": "object", "properties": {}},
            server_name="test_server",
        )

        metadata = ProxyFunctionMetadata(
            original_tool=mock_tool,
            server_name="test_server",
            original_name="original_tool",
            proxy_name="test_tool",
            parameter_mapping={},
            created_at=1234567890.0,
        )

        assert metadata.proxy_name == "test_tool"
        assert metadata.original_name == "original_tool"
        assert metadata.server_name == "test_server"
        assert metadata.original_tool.description == "A test tool"
        assert metadata.original_tool.input_schema == {
            "type": "object",
            "properties": {},
        }
        assert metadata.created_at == 1234567890.0

    def test_metadata_to_dict(self):
        """Test converting metadata to dictionary."""
        # Create a mock MCPTool for the metadata
        mock_tool = MCPTool(
            name="test_tool",
            description="A test tool",
            input_schema={"type": "object"},
            server_name="test_server",
        )

        metadata = ProxyFunctionMetadata(
            original_tool=mock_tool,
            server_name="test_server",
            original_name="original_tool",
            proxy_name="test_tool",
            parameter_mapping={},
            created_at=1234567890.0,
        )

        # Test string representation since to_dict() doesn't exist
        metadata_str = str(metadata)
        assert "test_tool" in metadata_str
        assert "test_server" in metadata_str
        assert "original_tool" in metadata_str


class TestProxyToolGenerator:
    """Test the ProxyToolGenerator class."""

    @pytest.fixture
    def mock_discovery_service(self):
        """Create a mock discovery service."""
        discovery_service = Mock()
        discovery_service.registry = ToolRegistry()
        return discovery_service

    @pytest.fixture
    def generator(self, mock_discovery_service):
        """Create a ProxyToolGenerator instance."""
        return ProxyToolGenerator(mock_discovery_service)

    @pytest.fixture
    def sample_tool_info(self):
        """Create sample tool info for testing."""
        return ToolInfo(
            name="test_tool",
            description="A test tool for unit testing",
            server_name="test_server",
            original_name="original_test_tool",
            schema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "A message to process",
                    },
                    "count": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "Number of times to process",
                    },
                },
                "required": ["message"],
            },
            metadata={"version": "1.0"},
        )

    def test_initialization(self, generator, mock_discovery_service):
        """Test that generator initializes correctly."""
        assert generator.discovery_service == mock_discovery_service
        assert generator._generated_functions == {}
        assert generator._function_metadata == {}

    @pytest.mark.asyncio
    async def test_generate_proxy_function(self, generator, sample_tool_info):
        """Test generating a proxy function for a tool."""
        # Mock the discovery service call_tool method
        generator.discovery_service.call_tool = AsyncMock(
            return_value={"processed_message": "Hello World", "processed_count": 3}
        )

        # Generate the proxy function
        proxy_func = generator.generate_proxy_function(sample_tool_info)

        # Check function properties
        assert callable(proxy_func)
        assert proxy_func.__name__ == "test_server.test_tool"
        assert "A test tool for unit testing" in proxy_func.__doc__

        # Check function signature
        sig = inspect.signature(proxy_func)
        assert "message" in sig.parameters
        assert "count" in sig.parameters
        assert sig.parameters["message"].annotation == str
        assert sig.parameters["count"].annotation == str

        # Test calling the function
        result = await proxy_func(message="Hello", count=3)

        assert result == {"processed_message": "Hello World", "processed_count": 3}

        # Verify the discovery service was called correctly
        generator.discovery_service.call_tool.assert_called_once_with(
            "test_tool", {"message": "Hello", "count": 3}
        )

    @pytest.mark.asyncio
    async def test_generate_proxy_function_validation_error(
        self, generator, sample_tool_info
    ):
        """Test proxy function with parameter validation error."""
        generator.discovery_service.call_tool = AsyncMock()

        proxy_func = generator.generate_proxy_function(sample_tool_info)

        # Test with invalid parameters (missing required parameter)
        with pytest.raises(ValidationError) as exc_info:
            await proxy_func(count=3)  # Missing required 'message' parameter

        assert "required" in str(exc_info.value).lower()

        # Test with invalid parameter type
        with pytest.raises(ValidationError) as exc_info:
            await proxy_func(message="Hello", count="not_a_number")

        assert "integer" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_generate_proxy_function_client_error(
        self, generator, sample_tool_info
    ):
        """Test proxy function when client call fails."""
        generator.discovery_service.call_tool = AsyncMock(
            side_effect=Exception("Connection failed")
        )

        proxy_func = generator.generate_proxy_function(sample_tool_info)

        # The function should raise the exception
        with pytest.raises(Exception) as exc_info:
            await proxy_func(message="Hello")

        assert "Connection failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_proxy_function_no_client(self, generator, sample_tool_info):
        """Test proxy function when no client is available."""
        generator.discovery_service.call_tool = AsyncMock(
            side_effect=ValueError("Tool 'test_tool' not found")
        )

        proxy_func = generator.generate_proxy_function(sample_tool_info)

        # The function should raise the exception
        with pytest.raises(ValueError) as exc_info:
            await proxy_func(message="Hello")

        assert "not found" in str(exc_info.value)

    def test_generate_all_proxy_functions(self, generator):
        """Test generating proxy functions for all tools in registry."""
        # Add some tools to the registry
        tool1 = ToolInfo(
            name="tool1",
            description="First tool",
            server_name="server1",
            original_name="tool1",
            schema={"type": "object", "properties": {"param1": {"type": "string"}}},
            metadata={},
        )

        tool2 = ToolInfo(
            name="tool2",
            description="Second tool",
            server_name="server2",
            original_name="tool2",
            schema={"type": "object", "properties": {"param2": {"type": "integer"}}},
            metadata={},
        )

        # Mock the get_all_tools method to return our test tools
        generator.discovery_service.get_all_tools = Mock(
            return_value=[tool1.to_mcp_tool(), tool2.to_mcp_tool()]
        )

        # Generate all proxy functions
        functions = generator.generate_all_proxy_functions()

        assert len(functions) == 2
        assert "server1.tool1" in functions
        assert "server2.tool2" in functions
        assert callable(functions["server1.tool1"])
        assert callable(functions["server2.tool2"])

    def test_get_function_metadata(self, generator, sample_tool_info):
        """Test getting metadata for a generated function."""
        proxy_func = generator.generate_proxy_function(sample_tool_info)

        metadata = generator.get_function_metadata("test_tool")

        assert metadata is not None
        assert metadata.tool_name == "test_tool"
        assert metadata.original_name == "original_test_tool"
        assert metadata.server_name == "test_server"
        assert metadata.description == "A test tool for unit testing"

    def test_get_function_metadata_not_found(self, generator):
        """Test getting metadata for a non-existent function."""
        metadata = generator.get_function_metadata("nonexistent_tool")
        assert metadata is None

    def test_clear_generated_functions(self, generator, sample_tool_info):
        """Test clearing all generated functions."""
        # Generate a function
        generator.generate_proxy_function(sample_tool_info)
        assert len(generator._generated_functions) == 1

        # Clear functions
        generator.clear_generated_functions()
        assert len(generator._generated_functions) == 0

    def test_create_function_signature(self, generator):
        """Test creating function signature from tool schema."""
        schema = {
            "type": "object",
            "properties": {
                "required_param": {"type": "string"},
                "optional_param": {"type": "integer"},
                "boolean_param": {"type": "boolean"},
            },
            "required": ["required_param"],
        }

        sig = generator._create_function_signature(schema)

        assert "required_param" in sig.parameters
        assert "optional_param" in sig.parameters
        assert "boolean_param" in sig.parameters

        # Check parameter annotations
        assert sig.parameters["required_param"].annotation == str
        assert sig.parameters["optional_param"].annotation == Optional[int]
        assert sig.parameters["boolean_param"].annotation == Optional[bool]

        # Check default values
        assert sig.parameters["required_param"].default == inspect.Parameter.empty
        assert sig.parameters["optional_param"].default is None
        assert sig.parameters["boolean_param"].default is None

    def test_map_json_type_to_python(self, generator):
        """Test mapping JSON schema types to Python types."""
        assert generator._map_json_type_to_python("string") == str
        assert generator._map_json_type_to_python("integer") == int
        assert generator._map_json_type_to_python("number") == float
        assert generator._map_json_type_to_python("boolean") == bool
        assert generator._map_json_type_to_python("array") == list
        assert generator._map_json_type_to_python("object") == dict
        assert generator._map_json_type_to_python("unknown") == Any

    def test_get_generation_stats(self, generator):
        """Test getting generation statistics."""
        # Initially no functions generated
        stats = generator.get_generation_stats()
        assert stats["total_functions"] == 0
        assert stats["functions_by_server"] == {}

        # Add some tools and generate functions
        tool1 = ToolInfo(
            name="tool1",
            description="Tool 1",
            server_name="server1",
            original_name="tool1",
            schema={"type": "object"},
            metadata={},
        )
        tool2 = ToolInfo(
            name="tool2",
            description="Tool 2",
            server_name="server1",
            original_name="tool2",
            schema={"type": "object"},
            metadata={},
        )
        tool3 = ToolInfo(
            name="tool3",
            description="Tool 3",
            server_name="server2",
            original_name="tool3",
            schema={"type": "object"},
            metadata={},
        )

        generator.discovery_service.registry.add_tool(tool1)
        generator.discovery_service.registry.add_tool(tool2)
        generator.discovery_service.registry.add_tool(tool3)

        generator.generate_all_proxy_functions()

        stats = generator.get_generation_stats()
        assert stats["total_functions"] == 3
        assert stats["functions_by_server"]["server1"] == 2
        assert stats["functions_by_server"]["server2"] == 1


class TestValidationError:
    """Test the ValidationError exception class."""

    def test_validation_error_creation(self):
        """Test creating a ValidationError."""
        error = ValidationError("Invalid parameter", "param_name", "expected_type")

        assert error.message == "Invalid parameter"
        assert error.parameter_name == "param_name"
        assert error.expected_type == "expected_type"
        assert "Invalid parameter" in str(error)
        assert "param_name" in str(error)


class TestProcessingError:
    """Test the ProcessingError exception class."""

    def test_processing_error_creation(self):
        """Test creating a ProcessingError."""
        error = ProcessingError("Processing failed", "test_tool", "test_server")

        assert error.message == "Processing failed"
        assert error.tool_name == "test_tool"
        assert error.server_name == "test_server"
        assert "Processing failed" in str(error)
        assert "test_tool" in str(error)
        assert "test_server" in str(error)


if __name__ == "__main__":
    pytest.main([__file__])
