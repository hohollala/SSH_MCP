"""Unit tests for MCP tool definitions and schemas."""

import json
import pytest
from datetime import datetime
from unittest.mock import Mock

from ssh_mcp_server.tools import (
    ToolError, ParameterType, ParameterSchema, ToolSchema,
    ParameterValidator, ToolResult, get_tool_schema, get_all_tool_schemas,
    validate_tool_parameters, format_connection_info, format_command_result,
    SSH_CONNECT_SCHEMA, SSH_EXECUTE_SCHEMA, SSH_READ_FILE_SCHEMA,
    SSH_WRITE_FILE_SCHEMA, SSH_LIST_DIRECTORY_SCHEMA, SSH_DISCONNECT_SCHEMA,
    SSH_LIST_CONNECTIONS_SCHEMA, TOOL_SCHEMAS
)
from ssh_mcp_server.models import ConnectionInfo, CommandResult


class TestParameterSchema:
    """Test ParameterSchema functionality."""
    
    def test_basic_parameter_schema(self):
        """Test basic parameter schema creation."""
        schema = ParameterSchema(
            name="test_param",
            type=ParameterType.STRING,
            description="A test parameter",
            required=True
        )
        
        assert schema.name == "test_param"
        assert schema.type == ParameterType.STRING
        assert schema.description == "A test parameter"
        assert schema.required is True
        assert schema.default is None
    
    def test_parameter_schema_with_constraints(self):
        """Test parameter schema with various constraints."""
        schema = ParameterSchema(
            name="port",
            type=ParameterType.INTEGER,
            description="Port number",
            required=False,
            default=22,
            minimum=1,
            maximum=65535
        )
        
        json_schema = schema.to_json_schema()
        
        assert json_schema["type"] == "integer"
        assert json_schema["description"] == "Port number"
        assert json_schema["default"] == 22
        assert json_schema["minimum"] == 1
        assert json_schema["maximum"] == 65535
    
    def test_parameter_schema_with_enum(self):
        """Test parameter schema with enum values."""
        schema = ParameterSchema(
            name="auth_method",
            type=ParameterType.STRING,
            description="Authentication method",
            enum=["key", "password", "agent"]
        )
        
        json_schema = schema.to_json_schema()
        
        assert json_schema["enum"] == ["key", "password", "agent"]
    
    def test_parameter_schema_with_pattern(self):
        """Test parameter schema with regex pattern."""
        schema = ParameterSchema(
            name="hostname",
            type=ParameterType.STRING,
            description="Hostname",
            pattern=r"^[a-zA-Z0-9\-\.]+$"
        )
        
        json_schema = schema.to_json_schema()
        
        assert json_schema["pattern"] == r"^[a-zA-Z0-9\-\.]+$"


class TestToolSchema:
    """Test ToolSchema functionality."""
    
    def test_basic_tool_schema(self):
        """Test basic tool schema creation."""
        parameters = [
            ParameterSchema("param1", ParameterType.STRING, "First parameter"),
            ParameterSchema("param2", ParameterType.INTEGER, "Second parameter", required=False)
        ]
        
        schema = ToolSchema(
            name="test_tool",
            description="A test tool",
            parameters=parameters
        )
        
        assert schema.name == "test_tool"
        assert schema.description == "A test tool"
        assert len(schema.parameters) == 2
    
    def test_tool_schema_to_mcp_format(self):
        """Test conversion to MCP schema format."""
        parameters = [
            ParameterSchema("required_param", ParameterType.STRING, "Required parameter"),
            ParameterSchema("optional_param", ParameterType.INTEGER, "Optional parameter", required=False, default=42)
        ]
        
        schema = ToolSchema(
            name="test_tool",
            description="A test tool",
            parameters=parameters
        )
        
        mcp_schema = schema.to_mcp_schema()
        
        assert mcp_schema["name"] == "test_tool"
        assert mcp_schema["description"] == "A test tool"
        assert "inputSchema" in mcp_schema
        
        input_schema = mcp_schema["inputSchema"]
        assert input_schema["type"] == "object"
        assert "required_param" in input_schema["properties"]
        assert "optional_param" in input_schema["properties"]
        assert input_schema["required"] == ["required_param"]


class TestParameterValidator:
    """Test ParameterValidator functionality."""
    
    def test_validate_string_parameter(self):
        """Test string parameter validation."""
        schema = ParameterSchema("test", ParameterType.STRING, "Test parameter")
        
        # Valid string
        result = ParameterValidator.validate_parameter("hello", schema)
        assert result == "hello"
        
        # Invalid type
        with pytest.raises(ToolError, match="Invalid type"):
            ParameterValidator.validate_parameter(123, schema)
    
    def test_validate_integer_parameter(self):
        """Test integer parameter validation."""
        schema = ParameterSchema("test", ParameterType.INTEGER, "Test parameter")
        
        # Valid integer
        result = ParameterValidator.validate_parameter(42, schema)
        assert result == 42
        
        # String conversion
        result = ParameterValidator.validate_parameter("123", schema)
        assert result == 123
        
        # Boolean should fail
        with pytest.raises(ToolError, match="Invalid type"):
            ParameterValidator.validate_parameter(True, schema)
        
        # Invalid string conversion
        with pytest.raises(ToolError, match="Invalid type"):
            ParameterValidator.validate_parameter("not_a_number", schema)
    
    def test_validate_number_parameter(self):
        """Test number parameter validation."""
        schema = ParameterSchema("test", ParameterType.NUMBER, "Test parameter")
        
        # Valid number
        result = ParameterValidator.validate_parameter(3.14, schema)
        assert result == 3.14
        
        # Integer to float conversion
        result = ParameterValidator.validate_parameter(42, schema)
        assert result == 42.0
        
        # String conversion
        result = ParameterValidator.validate_parameter("2.71", schema)
        assert result == 2.71
    
    def test_validate_boolean_parameter(self):
        """Test boolean parameter validation."""
        schema = ParameterSchema("test", ParameterType.BOOLEAN, "Test parameter")
        
        # Valid boolean
        result = ParameterValidator.validate_parameter(True, schema)
        assert result is True
        
        # String conversions
        for true_val in ["true", "True", "1", "yes", "on"]:
            result = ParameterValidator.validate_parameter(true_val, schema)
            assert result is True
        
        for false_val in ["false", "False", "0", "no", "off"]:
            result = ParameterValidator.validate_parameter(false_val, schema)
            assert result is False
        
        # Invalid string
        with pytest.raises(ToolError, match="Invalid type"):
            ParameterValidator.validate_parameter("maybe", schema)
    
    def test_validate_required_parameter(self):
        """Test required parameter validation."""
        schema = ParameterSchema("test", ParameterType.STRING, "Test parameter", required=True)
        
        # Missing required parameter
        with pytest.raises(ToolError, match="Required parameter"):
            ParameterValidator.validate_parameter(None, schema)
    
    def test_validate_optional_parameter_with_default(self):
        """Test optional parameter with default value."""
        schema = ParameterSchema("test", ParameterType.STRING, "Test parameter", required=False, default="default_value")
        
        # None should return default
        result = ParameterValidator.validate_parameter(None, schema)
        assert result == "default_value"
    
    def test_validate_enum_constraint(self):
        """Test enum constraint validation."""
        schema = ParameterSchema("test", ParameterType.STRING, "Test parameter", enum=["a", "b", "c"])
        
        # Valid enum value
        result = ParameterValidator.validate_parameter("b", schema)
        assert result == "b"
        
        # Invalid enum value
        with pytest.raises(ToolError, match="must be one of"):
            ParameterValidator.validate_parameter("d", schema)
    
    def test_validate_numeric_range_constraints(self):
        """Test numeric range constraint validation."""
        schema = ParameterSchema("test", ParameterType.INTEGER, "Test parameter", minimum=1, maximum=100)
        
        # Valid range
        result = ParameterValidator.validate_parameter(50, schema)
        assert result == 50
        
        # Below minimum
        with pytest.raises(ToolError, match="must be >= 1"):
            ParameterValidator.validate_parameter(0, schema)
        
        # Above maximum
        with pytest.raises(ToolError, match="must be <= 100"):
            ParameterValidator.validate_parameter(101, schema)
    
    def test_validate_pattern_constraint(self):
        """Test pattern constraint validation."""
        schema = ParameterSchema("test", ParameterType.STRING, "Test parameter", pattern=r"^[a-z]+$")
        
        # Valid pattern
        result = ParameterValidator.validate_parameter("hello", schema)
        assert result == "hello"
        
        # Invalid pattern
        with pytest.raises(ToolError, match="does not match pattern"):
            ParameterValidator.validate_parameter("Hello123", schema)
    
    def test_validate_parameters_dict(self):
        """Test validation of parameter dictionary."""
        schema = ToolSchema(
            name="test_tool",
            description="Test tool",
            parameters=[
                ParameterSchema("required_param", ParameterType.STRING, "Required parameter"),
                ParameterSchema("optional_param", ParameterType.INTEGER, "Optional parameter", required=False, default=42)
            ]
        )
        
        # Valid parameters
        params = {"required_param": "hello"}
        result = ParameterValidator.validate_parameters(params, schema)
        assert result["required_param"] == "hello"
        assert result["optional_param"] == 42
        
        # Missing required parameter
        with pytest.raises(ToolError, match="Required parameter"):
            ParameterValidator.validate_parameters({}, schema)
        
        # Unexpected parameter
        with pytest.raises(ToolError, match="Unexpected parameters"):
            ParameterValidator.validate_parameters({"required_param": "hello", "unexpected": "value"}, schema)


class TestToolResult:
    """Test ToolResult functionality."""
    
    def test_success_result(self):
        """Test successful result creation."""
        result = ToolResult.success({"key": "value"}, {"execution_time": 1.5})
        
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.error is None
        assert result.metadata == {"execution_time": 1.5}
    
    def test_error_result(self):
        """Test error result creation."""
        result = ToolResult.error("Something went wrong", {"error_code": 500})
        
        assert result.success is False
        assert result.data is None
        assert result.error == "Something went wrong"
        assert result.metadata == {"error_code": 500}
    
    def test_result_to_dict(self):
        """Test result conversion to dictionary."""
        success_result = ToolResult.success({"data": "test"})
        success_dict = success_result.to_dict()
        
        assert success_dict["success"] is True
        assert success_dict["data"] == {"data": "test"}
        assert "error" not in success_dict
        
        error_result = ToolResult.error("Error message")
        error_dict = error_result.to_dict()
        
        assert error_dict["success"] is False
        assert error_dict["error"] == "Error message"
        assert "data" not in error_dict
    
    def test_result_to_json(self):
        """Test result conversion to JSON."""
        result = ToolResult.success({"key": "value"})
        json_str = result.to_json()
        
        parsed = json.loads(json_str)
        assert parsed["success"] is True
        assert parsed["data"]["key"] == "value"


class TestToolSchemas:
    """Test predefined tool schemas."""
    
    def test_ssh_connect_schema(self):
        """Test SSH connect tool schema."""
        assert SSH_CONNECT_SCHEMA.name == "ssh_connect"
        assert "hostname" in [p.name for p in SSH_CONNECT_SCHEMA.parameters]
        assert "username" in [p.name for p in SSH_CONNECT_SCHEMA.parameters]
        
        # Test MCP schema conversion
        mcp_schema = SSH_CONNECT_SCHEMA.to_mcp_schema()
        assert mcp_schema["name"] == "ssh_connect"
        assert "hostname" in mcp_schema["inputSchema"]["properties"]
    
    def test_ssh_execute_schema(self):
        """Test SSH execute tool schema."""
        assert SSH_EXECUTE_SCHEMA.name == "ssh_execute"
        assert "connection_id" in [p.name for p in SSH_EXECUTE_SCHEMA.parameters]
        assert "command" in [p.name for p in SSH_EXECUTE_SCHEMA.parameters]
    
    def test_ssh_read_file_schema(self):
        """Test SSH read file tool schema."""
        assert SSH_READ_FILE_SCHEMA.name == "ssh_read_file"
        assert "connection_id" in [p.name for p in SSH_READ_FILE_SCHEMA.parameters]
        assert "file_path" in [p.name for p in SSH_READ_FILE_SCHEMA.parameters]
    
    def test_ssh_write_file_schema(self):
        """Test SSH write file tool schema."""
        assert SSH_WRITE_FILE_SCHEMA.name == "ssh_write_file"
        assert "connection_id" in [p.name for p in SSH_WRITE_FILE_SCHEMA.parameters]
        assert "file_path" in [p.name for p in SSH_WRITE_FILE_SCHEMA.parameters]
        assert "content" in [p.name for p in SSH_WRITE_FILE_SCHEMA.parameters]
    
    def test_ssh_list_directory_schema(self):
        """Test SSH list directory tool schema."""
        assert SSH_LIST_DIRECTORY_SCHEMA.name == "ssh_list_directory"
        assert "connection_id" in [p.name for p in SSH_LIST_DIRECTORY_SCHEMA.parameters]
        assert "directory_path" in [p.name for p in SSH_LIST_DIRECTORY_SCHEMA.parameters]
    
    def test_ssh_disconnect_schema(self):
        """Test SSH disconnect tool schema."""
        assert SSH_DISCONNECT_SCHEMA.name == "ssh_disconnect"
        assert "connection_id" in [p.name for p in SSH_DISCONNECT_SCHEMA.parameters]
    
    def test_ssh_list_connections_schema(self):
        """Test SSH list connections tool schema."""
        assert SSH_LIST_CONNECTIONS_SCHEMA.name == "ssh_list_connections"
        assert len(SSH_LIST_CONNECTIONS_SCHEMA.parameters) == 0


class TestToolRegistry:
    """Test tool registry functions."""
    
    def test_get_tool_schema(self):
        """Test getting tool schema by name."""
        schema = get_tool_schema("ssh_connect")
        assert schema is not None
        assert schema.name == "ssh_connect"
        
        # Non-existent tool
        schema = get_tool_schema("non_existent")
        assert schema is None
    
    def test_get_all_tool_schemas(self):
        """Test getting all tool schemas."""
        schemas = get_all_tool_schemas()
        
        assert isinstance(schemas, dict)
        assert "ssh_connect" in schemas
        assert "ssh_execute" in schemas
        assert "ssh_read_file" in schemas
        assert "ssh_write_file" in schemas
        assert "ssh_list_directory" in schemas
        assert "ssh_disconnect" in schemas
        assert "ssh_list_connections" in schemas
        
        # Should be a copy, not the original
        assert schemas is not TOOL_SCHEMAS
    
    def test_validate_tool_parameters(self):
        """Test tool parameter validation."""
        # Valid parameters
        params = {
            "hostname": "example.com",
            "username": "user",
            "auth_method": "key"
        }
        
        result = validate_tool_parameters("ssh_connect", params)
        assert result["hostname"] == "example.com"
        assert result["username"] == "user"
        assert result["auth_method"] == "key"
        assert result["port"] == 22  # default value
        
        # Unknown tool
        with pytest.raises(ToolError, match="Unknown tool"):
            validate_tool_parameters("unknown_tool", {})
        
        # Invalid parameters
        with pytest.raises(ToolError, match="Required parameter"):
            validate_tool_parameters("ssh_connect", {})


class TestFormatters:
    """Test output formatting functions."""
    
    def test_format_connection_info(self):
        """Test ConnectionInfo formatting."""
        connection_info = ConnectionInfo.create("example.com", "user", 22)
        connection_info.connected = True
        
        formatted = format_connection_info(connection_info)
        
        assert formatted["connection_id"] == connection_info.connection_id
        assert formatted["hostname"] == "example.com"
        assert formatted["username"] == "user"
        assert formatted["port"] == 22
        assert formatted["connected"] is True
        assert "created_at" in formatted
        assert "last_used" in formatted
    
    def test_format_command_result(self):
        """Test CommandResult formatting."""
        result = CommandResult(
            stdout="Hello, World!",
            stderr="",
            exit_code=0,
            execution_time=1.5,
            command="echo 'Hello, World!'"
        )
        
        formatted = format_command_result(result)
        
        assert formatted["stdout"] == "Hello, World!"
        assert formatted["stderr"] == ""
        assert formatted["exit_code"] == 0
        assert formatted["success"] is True
        assert formatted["execution_time"] == 1.5
        assert formatted["command"] == "echo 'Hello, World!'"
        assert formatted["has_output"] is True
        assert "timestamp" in formatted


class TestToolParameterValidationIntegration:
    """Integration tests for tool parameter validation."""
    
    def test_ssh_connect_parameter_validation(self):
        """Test SSH connect parameter validation."""
        # Valid minimal parameters
        params = {
            "hostname": "example.com",
            "username": "user"
        }
        
        result = validate_tool_parameters("ssh_connect", params)
        assert result["hostname"] == "example.com"
        assert result["username"] == "user"
        assert result["port"] == 22
        assert result["auth_method"] == "agent"
        assert result["timeout"] == 30
        
        # Valid with all parameters
        params = {
            "hostname": "192.168.1.100",
            "username": "admin",
            "port": 2222,
            "auth_method": "key",
            "key_path": "/path/to/key",
            "timeout": 60
        }
        
        result = validate_tool_parameters("ssh_connect", params)
        assert result["port"] == 2222
        assert result["auth_method"] == "key"
        assert result["key_path"] == "/path/to/key"
        assert result["timeout"] == 60
        
        # Invalid auth method
        params["auth_method"] = "invalid"
        with pytest.raises(ToolError, match="must be one of"):
            validate_tool_parameters("ssh_connect", params)
        
        # Invalid port range
        params["auth_method"] = "key"
        params["port"] = 70000
        with pytest.raises(ToolError, match="must be <= 65535"):
            validate_tool_parameters("ssh_connect", params)
    
    def test_ssh_execute_parameter_validation(self):
        """Test SSH execute parameter validation."""
        # Valid parameters
        params = {
            "connection_id": "12345678-1234-1234-1234-123456789012",
            "command": "ls -la"
        }
        
        result = validate_tool_parameters("ssh_execute", params)
        assert result["connection_id"] == "12345678-1234-1234-1234-123456789012"
        assert result["command"] == "ls -la"
        assert result["timeout"] == 60  # default
        
        # With custom timeout
        params["timeout"] = 120
        result = validate_tool_parameters("ssh_execute", params)
        assert result["timeout"] == 120
        
        # Invalid timeout range
        params["timeout"] = 5000
        with pytest.raises(ToolError, match="must be <= 3600"):
            validate_tool_parameters("ssh_execute", params)
    
    def test_ssh_file_operations_parameter_validation(self):
        """Test SSH file operations parameter validation."""
        # Read file
        params = {
            "connection_id": "12345678-1234-1234-1234-123456789012",
            "file_path": "/etc/hosts"
        }
        
        result = validate_tool_parameters("ssh_read_file", params)
        assert result["encoding"] == "utf-8"  # default
        
        # Write file
        params = {
            "connection_id": "12345678-1234-1234-1234-123456789012",
            "file_path": "/tmp/test.txt",
            "content": "Hello, World!"
        }
        
        result = validate_tool_parameters("ssh_write_file", params)
        assert result["content"] == "Hello, World!"
        assert result["encoding"] == "utf-8"  # default
        assert result["create_dirs"] is False  # default
        
        # List directory
        params = {
            "connection_id": "12345678-1234-1234-1234-123456789012",
            "directory_path": "/home/user"
        }
        
        result = validate_tool_parameters("ssh_list_directory", params)
        assert result["show_hidden"] is False  # default
        assert result["detailed"] is False  # default


if __name__ == "__main__":
    pytest.main([__file__])