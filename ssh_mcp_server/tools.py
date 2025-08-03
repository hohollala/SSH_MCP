"""MCP tool definitions and schemas for SSH MCP Server."""

import json
import logging
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Union, Callable
from enum import Enum

from .models import SSHConfig, CommandResult, ConnectionInfo


logger = logging.getLogger(__name__)


class ToolError(Exception):
    """Custom exception for MCP tool errors."""
    
    def __init__(self, message: str, code: int = -1, details: Optional[Dict[str, Any]] = None):
        """Initialize tool error.
        
        Args:
            message: Human-readable error message
            code: Error code for categorization
            details: Additional error details
        """
        super().__init__(message)
        self.code = code
        self.details = details or {}


class ParameterType(Enum):
    """Supported parameter types for MCP tools."""
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"


@dataclass
class ParameterSchema:
    """Schema definition for a tool parameter."""
    name: str
    type: ParameterType
    description: str
    required: bool = True
    default: Optional[Any] = None
    enum: Optional[List[Any]] = None
    minimum: Optional[Union[int, float]] = None
    maximum: Optional[Union[int, float]] = None
    pattern: Optional[str] = None
    properties: Optional[Dict[str, 'ParameterSchema']] = None
    items: Optional['ParameterSchema'] = None

    def to_json_schema(self) -> Dict[str, Any]:
        """Convert parameter schema to JSON Schema format."""
        schema = {
            "type": self.type.value,
            "description": self.description
        }
        
        if self.enum is not None:
            schema["enum"] = self.enum
        
        if self.minimum is not None:
            schema["minimum"] = self.minimum
            
        if self.maximum is not None:
            schema["maximum"] = self.maximum
            
        if self.pattern is not None:
            schema["pattern"] = self.pattern
            
        if self.default is not None:
            schema["default"] = self.default
            
        if self.properties is not None:
            schema["properties"] = {
                name: prop.to_json_schema() 
                for name, prop in self.properties.items()
            }
            schema["required"] = [
                name for name, prop in self.properties.items() 
                if prop.required
            ]
            
        if self.items is not None:
            schema["items"] = self.items.to_json_schema()
            
        return schema


@dataclass
class ToolSchema:
    """Complete schema definition for an MCP tool."""
    name: str
    description: str
    parameters: List[ParameterSchema]
    examples: Optional[List[Dict[str, Any]]] = None
    
    def to_mcp_schema(self) -> Dict[str, Any]:
        """Convert to MCP tool schema format."""
        # Build properties and required fields
        properties = {}
        required = []
        
        for param in self.parameters:
            properties[param.name] = param.to_json_schema()
            if param.required:
                required.append(param.name)
        
        schema = {
            "name": self.name,
            "description": self.description,
            "inputSchema": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }
        
        return schema


class ParameterValidator:
    """Validates tool parameters against their schemas."""
    
    @staticmethod
    def validate_parameter(value: Any, schema: ParameterSchema) -> Any:
        """Validate a single parameter value against its schema.
        
        Args:
            value: The parameter value to validate
            schema: The parameter schema to validate against
            
        Returns:
            The validated (and possibly converted) value
            
        Raises:
            ToolError: If validation fails
        """
        # Handle None values
        if value is None:
            if schema.required:
                raise ToolError(f"Required parameter '{schema.name}' is missing")
            return schema.default
        
        # Type validation and conversion
        try:
            validated_value = ParameterValidator._validate_type(value, schema)
        except (ValueError, TypeError) as e:
            raise ToolError(f"Invalid type for parameter '{schema.name}': {e}")
        
        # Additional validations
        ParameterValidator._validate_constraints(validated_value, schema)
        
        return validated_value
    
    @staticmethod
    def _validate_type(value: Any, schema: ParameterSchema) -> Any:
        """Validate and convert parameter type."""
        if schema.type == ParameterType.STRING:
            if not isinstance(value, str):
                raise ValueError(f"Expected string, got {type(value).__name__}")
            return value
            
        elif schema.type == ParameterType.INTEGER:
            if isinstance(value, bool):  # bool is subclass of int in Python
                raise ValueError("Expected integer, got boolean")
            if isinstance(value, int):
                return value
            if isinstance(value, str):
                try:
                    return int(value)
                except ValueError:
                    raise ValueError(f"Cannot convert '{value}' to integer")
            raise ValueError(f"Expected integer, got {type(value).__name__}")
            
        elif schema.type == ParameterType.NUMBER:
            if isinstance(value, bool):
                raise ValueError("Expected number, got boolean")
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                try:
                    return float(value)
                except ValueError:
                    raise ValueError(f"Cannot convert '{value}' to number")
            raise ValueError(f"Expected number, got {type(value).__name__}")
            
        elif schema.type == ParameterType.BOOLEAN:
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                if value.lower() in ('true', '1', 'yes', 'on'):
                    return True
                elif value.lower() in ('false', '0', 'no', 'off'):
                    return False
                else:
                    raise ValueError(f"Cannot convert '{value}' to boolean")
            raise ValueError(f"Expected boolean, got {type(value).__name__}")
            
        elif schema.type == ParameterType.OBJECT:
            if not isinstance(value, dict):
                raise ValueError(f"Expected object, got {type(value).__name__}")
            return value
            
        elif schema.type == ParameterType.ARRAY:
            if not isinstance(value, list):
                raise ValueError(f"Expected array, got {type(value).__name__}")
            return value
            
        else:
            raise ValueError(f"Unsupported parameter type: {schema.type}")
    
    @staticmethod
    def _validate_constraints(value: Any, schema: ParameterSchema) -> None:
        """Validate parameter constraints."""
        # Enum validation
        if schema.enum is not None and value not in schema.enum:
            raise ToolError(f"Parameter '{schema.name}' must be one of {schema.enum}, got '{value}'")
        
        # Numeric range validation
        if schema.type in (ParameterType.INTEGER, ParameterType.NUMBER):
            if schema.minimum is not None and value < schema.minimum:
                raise ToolError(f"Parameter '{schema.name}' must be >= {schema.minimum}, got {value}")
            if schema.maximum is not None and value > schema.maximum:
                raise ToolError(f"Parameter '{schema.name}' must be <= {schema.maximum}, got {value}")
        
        # String pattern validation
        if schema.type == ParameterType.STRING and schema.pattern is not None:
            import re
            if not re.match(schema.pattern, value):
                raise ToolError(f"Parameter '{schema.name}' does not match pattern '{schema.pattern}'")
    
    @staticmethod
    def validate_parameters(parameters: Dict[str, Any], schema: ToolSchema) -> Dict[str, Any]:
        """Validate all parameters for a tool.
        
        Args:
            parameters: Dictionary of parameter values
            schema: Tool schema to validate against
            
        Returns:
            Dictionary of validated parameters
            
        Raises:
            ToolError: If validation fails
        """
        validated = {}
        
        # Validate each parameter in the schema
        for param_schema in schema.parameters:
            value = parameters.get(param_schema.name)
            validated[param_schema.name] = ParameterValidator.validate_parameter(value, param_schema)
        
        # Check for unexpected parameters
        expected_params = {param.name for param in schema.parameters}
        provided_params = set(parameters.keys())
        unexpected = provided_params - expected_params
        
        if unexpected:
            raise ToolError(f"Unexpected parameters: {', '.join(unexpected)}")
        
        return validated


class ToolResult:
    """Standardized result format for MCP tools."""
    
    def __init__(self, success: bool, data: Optional[Any] = None, error: Optional[str] = None, 
                 metadata: Optional[Dict[str, Any]] = None):
        """Initialize tool result.
        
        Args:
            success: Whether the tool execution was successful
            data: The result data (if successful)
            error: Error message (if unsuccessful)
            metadata: Additional metadata about the execution
        """
        self.success = success
        self.data = data
        self.error = error
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary format."""
        result = {
            "success": self.success,
            "metadata": self.metadata
        }
        
        if self.success:
            result["data"] = self.data
        else:
            result["error"] = self.error
            
        return result
    
    def to_json(self) -> str:
        """Convert result to JSON string."""
        return json.dumps(self.to_dict(), default=str, indent=2)
    
    @classmethod
    def success(cls, data: Any, metadata: Optional[Dict[str, Any]] = None) -> 'ToolResult':
        """Create a successful result."""
        return cls(success=True, data=data, metadata=metadata)
    
    @classmethod
    def error(cls, error: str, metadata: Optional[Dict[str, Any]] = None) -> 'ToolResult':
        """Create an error result."""
        return cls(success=False, error=error, metadata=metadata)


# Define all MCP tool schemas
SSH_CONNECT_SCHEMA = ToolSchema(
    name="ssh_connect",
    description="Establish an SSH connection to a remote server",
    parameters=[
        ParameterSchema(
            name="hostname",
            type=ParameterType.STRING,
            description="The hostname or IP address of the SSH server",
            required=True
        ),
        ParameterSchema(
            name="username",
            type=ParameterType.STRING,
            description="The username for SSH authentication",
            required=True
        ),
        ParameterSchema(
            name="port",
            type=ParameterType.INTEGER,
            description="The SSH port number",
            required=False,
            default=22,
            minimum=1,
            maximum=65535
        ),
        ParameterSchema(
            name="auth_method",
            type=ParameterType.STRING,
            description="Authentication method to use",
            required=False,
            default="agent",
            enum=["key", "password", "agent"]
        ),
        ParameterSchema(
            name="key_path",
            type=ParameterType.STRING,
            description="Path to SSH private key file (required for 'key' auth)",
            required=False
        ),
        ParameterSchema(
            name="password",
            type=ParameterType.STRING,
            description="Password for authentication (required for 'password' auth)",
            required=False
        ),
        ParameterSchema(
            name="timeout",
            type=ParameterType.INTEGER,
            description="Connection timeout in seconds",
            required=False,
            default=30,
            minimum=1,
            maximum=300
        )
    ],
    examples=[
        {
            "hostname": "example.com",
            "username": "user",
            "auth_method": "key",
            "key_path": "~/.ssh/id_rsa"
        },
        {
            "hostname": "192.168.1.100",
            "username": "admin",
            "port": 2222,
            "auth_method": "password",
            "password": "secret"
        }
    ]
)

SSH_EXECUTE_SCHEMA = ToolSchema(
    name="ssh_execute",
    description="Execute a command on a remote server via SSH",
    parameters=[
        ParameterSchema(
            name="connection_id",
            type=ParameterType.STRING,
            description="The ID of the SSH connection to use",
            required=True
        ),
        ParameterSchema(
            name="command",
            type=ParameterType.STRING,
            description="The command to execute on the remote server",
            required=True
        ),
        ParameterSchema(
            name="timeout",
            type=ParameterType.INTEGER,
            description="Command execution timeout in seconds",
            required=False,
            default=60,
            minimum=1,
            maximum=3600
        )
    ],
    examples=[
        {
            "connection_id": "12345678-1234-1234-1234-123456789012",
            "command": "ls -la /home/user"
        },
        {
            "connection_id": "12345678-1234-1234-1234-123456789012",
            "command": "ps aux | grep nginx",
            "timeout": 30
        }
    ]
)

SSH_READ_FILE_SCHEMA = ToolSchema(
    name="ssh_read_file",
    description="Read the contents of a file on a remote server",
    parameters=[
        ParameterSchema(
            name="connection_id",
            type=ParameterType.STRING,
            description="The ID of the SSH connection to use",
            required=True
        ),
        ParameterSchema(
            name="file_path",
            type=ParameterType.STRING,
            description="The path to the file to read on the remote server",
            required=True
        ),
        ParameterSchema(
            name="encoding",
            type=ParameterType.STRING,
            description="Text encoding to use when reading the file",
            required=False,
            default="utf-8"
        )
    ],
    examples=[
        {
            "connection_id": "12345678-1234-1234-1234-123456789012",
            "file_path": "/etc/nginx/nginx.conf"
        },
        {
            "connection_id": "12345678-1234-1234-1234-123456789012",
            "file_path": "/var/log/application.log",
            "encoding": "utf-8"
        }
    ]
)

SSH_WRITE_FILE_SCHEMA = ToolSchema(
    name="ssh_write_file",
    description="Write content to a file on a remote server",
    parameters=[
        ParameterSchema(
            name="connection_id",
            type=ParameterType.STRING,
            description="The ID of the SSH connection to use",
            required=True
        ),
        ParameterSchema(
            name="file_path",
            type=ParameterType.STRING,
            description="The path to the file to write on the remote server",
            required=True
        ),
        ParameterSchema(
            name="content",
            type=ParameterType.STRING,
            description="The content to write to the file",
            required=True
        ),
        ParameterSchema(
            name="encoding",
            type=ParameterType.STRING,
            description="Text encoding to use when writing the file",
            required=False,
            default="utf-8"
        ),
        ParameterSchema(
            name="create_dirs",
            type=ParameterType.BOOLEAN,
            description="Whether to create parent directories if they don't exist",
            required=False,
            default=False
        )
    ],
    examples=[
        {
            "connection_id": "12345678-1234-1234-1234-123456789012",
            "file_path": "/tmp/test.txt",
            "content": "Hello, World!"
        },
        {
            "connection_id": "12345678-1234-1234-1234-123456789012",
            "file_path": "/etc/myapp/config.json",
            "content": "{\"debug\": true}",
            "create_dirs": True
        }
    ]
)

SSH_LIST_DIRECTORY_SCHEMA = ToolSchema(
    name="ssh_list_directory",
    description="List the contents of a directory on a remote server",
    parameters=[
        ParameterSchema(
            name="connection_id",
            type=ParameterType.STRING,
            description="The ID of the SSH connection to use",
            required=True
        ),
        ParameterSchema(
            name="directory_path",
            type=ParameterType.STRING,
            description="The path to the directory to list",
            required=True
        ),
        ParameterSchema(
            name="show_hidden",
            type=ParameterType.BOOLEAN,
            description="Whether to include hidden files (starting with .)",
            required=False,
            default=False
        ),
        ParameterSchema(
            name="detailed",
            type=ParameterType.BOOLEAN,
            description="Whether to include detailed file information (permissions, size, etc.)",
            required=False,
            default=False
        )
    ],
    examples=[
        {
            "connection_id": "12345678-1234-1234-1234-123456789012",
            "directory_path": "/home/user"
        },
        {
            "connection_id": "12345678-1234-1234-1234-123456789012",
            "directory_path": "/var/log",
            "show_hidden": True,
            "detailed": True
        }
    ]
)

SSH_DISCONNECT_SCHEMA = ToolSchema(
    name="ssh_disconnect",
    description="Disconnect an SSH connection",
    parameters=[
        ParameterSchema(
            name="connection_id",
            type=ParameterType.STRING,
            description="The ID of the SSH connection to disconnect",
            required=True
        )
    ],
    examples=[
        {
            "connection_id": "12345678-1234-1234-1234-123456789012"
        }
    ]
)

SSH_LIST_CONNECTIONS_SCHEMA = ToolSchema(
    name="ssh_list_connections",
    description="List all active SSH connections",
    parameters=[],
    examples=[{}]
)


# Registry of all available tools
TOOL_SCHEMAS = {
    "ssh_connect": SSH_CONNECT_SCHEMA,
    "ssh_execute": SSH_EXECUTE_SCHEMA,
    "ssh_read_file": SSH_READ_FILE_SCHEMA,
    "ssh_write_file": SSH_WRITE_FILE_SCHEMA,
    "ssh_list_directory": SSH_LIST_DIRECTORY_SCHEMA,
    "ssh_disconnect": SSH_DISCONNECT_SCHEMA,
    "ssh_list_connections": SSH_LIST_CONNECTIONS_SCHEMA,
}


def get_tool_schema(tool_name: str) -> Optional[ToolSchema]:
    """Get the schema for a specific tool.
    
    Args:
        tool_name: Name of the tool
        
    Returns:
        ToolSchema instance or None if tool not found
    """
    return TOOL_SCHEMAS.get(tool_name)


def get_all_tool_schemas() -> Dict[str, ToolSchema]:
    """Get all available tool schemas.
    
    Returns:
        Dictionary mapping tool names to their schemas
    """
    return TOOL_SCHEMAS.copy()


def validate_tool_parameters(tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Validate parameters for a specific tool.
    
    Args:
        tool_name: Name of the tool
        parameters: Dictionary of parameter values
        
    Returns:
        Dictionary of validated parameters
        
    Raises:
        ToolError: If tool not found or validation fails
    """
    schema = get_tool_schema(tool_name)
    if schema is None:
        raise ToolError(f"Unknown tool: {tool_name}")
    
    return ParameterValidator.validate_parameters(parameters, schema)


def format_connection_info(connection_info: ConnectionInfo) -> Dict[str, Any]:
    """Format ConnectionInfo for tool output.
    
    Args:
        connection_info: ConnectionInfo instance to format
        
    Returns:
        Formatted dictionary representation
    """
    return {
        "connection_id": connection_info.connection_id,
        "hostname": connection_info.hostname,
        "username": connection_info.username,
        "port": connection_info.port,
        "connected": connection_info.connected,
        "created_at": connection_info.created_at.isoformat(),
        "last_used": connection_info.last_used.isoformat()
    }


def format_command_result(result: CommandResult) -> Dict[str, Any]:
    """Format CommandResult for tool output.
    
    Args:
        result: CommandResult instance to format
        
    Returns:
        Formatted dictionary representation
    """
    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.exit_code,
        "success": result.success,
        "execution_time": result.execution_time,
        "command": result.command,
        "timestamp": result.timestamp.isoformat(),
        "has_output": result.has_output
    }