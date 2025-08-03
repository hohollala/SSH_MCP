#!/usr/bin/env python3
"""
Demonstration of MCP tool schema functionality.

This script shows how to use the MCP tool schemas for validation and formatting.
"""

import json
import sys
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from ssh_mcp_server.tools import (
    get_all_tool_schemas, validate_tool_parameters, ToolResult,
    format_connection_info, format_command_result
)
from ssh_mcp_server.models import ConnectionInfo, CommandResult


def demonstrate_tool_schemas():
    """Demonstrate MCP tool schema functionality."""
    print("=== MCP Tool Schema Demonstration ===\n")
    
    # Get all available tool schemas
    schemas = get_all_tool_schemas()
    print(f"Available tools: {', '.join(schemas.keys())}\n")
    
    # Show schema for ssh_connect tool
    ssh_connect_schema = schemas["ssh_connect"]
    print("SSH Connect Tool Schema:")
    print(f"Name: {ssh_connect_schema.name}")
    print(f"Description: {ssh_connect_schema.description}")
    print("Parameters:")
    for param in ssh_connect_schema.parameters:
        required = "required" if param.required else "optional"
        default = f" (default: {param.default})" if param.default is not None else ""
        enum_info = f" (options: {param.enum})" if param.enum else ""
        print(f"  - {param.name} ({param.type.value}, {required}): {param.description}{default}{enum_info}")
    print()
    
    # Convert to MCP format
    mcp_schema = ssh_connect_schema.to_mcp_schema()
    print("MCP Schema Format:")
    print(json.dumps(mcp_schema, indent=2))
    print()


def demonstrate_parameter_validation():
    """Demonstrate parameter validation."""
    print("=== Parameter Validation Demonstration ===\n")
    
    # Valid parameters
    print("1. Valid SSH connection parameters:")
    valid_params = {
        "hostname": "example.com",
        "username": "user",
        "port": 22,
        "auth_method": "key",
        "key_path": "/home/user/.ssh/id_rsa",
        "timeout": 30
    }
    
    try:
        validated = validate_tool_parameters("ssh_connect", valid_params)
        print("✓ Validation successful!")
        print(f"Validated parameters: {json.dumps(validated, indent=2)}")
    except Exception as e:
        print(f"✗ Validation failed: {e}")
    print()
    
    # Minimal parameters (using defaults)
    print("2. Minimal SSH connection parameters (using defaults):")
    minimal_params = {
        "hostname": "192.168.1.100",
        "username": "admin"
    }
    
    try:
        validated = validate_tool_parameters("ssh_connect", minimal_params)
        print("✓ Validation successful!")
        print(f"Validated parameters: {json.dumps(validated, indent=2)}")
    except Exception as e:
        print(f"✗ Validation failed: {e}")
    print()
    
    # Invalid parameters
    print("3. Invalid parameters (missing required field):")
    invalid_params = {
        "hostname": "example.com"
        # Missing required 'username'
    }
    
    try:
        validated = validate_tool_parameters("ssh_connect", invalid_params)
        print("✓ Validation successful!")
        print(f"Validated parameters: {json.dumps(validated, indent=2)}")
    except Exception as e:
        print(f"✗ Validation failed: {e}")
    print()
    
    # Invalid enum value
    print("4. Invalid enum value:")
    invalid_enum_params = {
        "hostname": "example.com",
        "username": "user",
        "auth_method": "invalid_method"
    }
    
    try:
        validated = validate_tool_parameters("ssh_connect", invalid_enum_params)
        print("✓ Validation successful!")
        print(f"Validated parameters: {json.dumps(validated, indent=2)}")
    except Exception as e:
        print(f"✗ Validation failed: {e}")
    print()


def demonstrate_tool_results():
    """Demonstrate tool result formatting."""
    print("=== Tool Result Formatting Demonstration ===\n")
    
    # Success result
    print("1. Success result:")
    success_data = {
        "connection_id": "12345678-1234-1234-1234-123456789012",
        "status": "connected"
    }
    success_result = ToolResult.success(success_data, {"execution_time": 1.5})
    print(success_result.to_json())
    print()
    
    # Error result
    print("2. Error result:")
    error_result = ToolResult.error("Connection failed: Authentication error", {"error_code": "AUTH_FAILED"})
    print(error_result.to_json())
    print()


def demonstrate_output_formatting():
    """Demonstrate output formatting for SSH objects."""
    print("=== Output Formatting Demonstration ===\n")
    
    # Format ConnectionInfo
    print("1. ConnectionInfo formatting:")
    connection_info = ConnectionInfo.create("example.com", "user", 22)
    connection_info.connected = True
    formatted_connection = format_connection_info(connection_info)
    print(json.dumps(formatted_connection, indent=2))
    print()
    
    # Format CommandResult
    print("2. CommandResult formatting:")
    command_result = CommandResult(
        stdout="Hello, World!\n",
        stderr="",
        exit_code=0,
        execution_time=0.5,
        command="echo 'Hello, World!'"
    )
    formatted_result = format_command_result(command_result)
    print(json.dumps(formatted_result, indent=2))
    print()


def demonstrate_all_tool_schemas():
    """Show all available tool schemas."""
    print("=== All Tool Schemas ===\n")
    
    schemas = get_all_tool_schemas()
    
    for tool_name, schema in schemas.items():
        print(f"Tool: {tool_name}")
        print(f"Description: {schema.description}")
        print(f"Parameters: {len(schema.parameters)}")
        
        if schema.parameters:
            required_params = [p.name for p in schema.parameters if p.required]
            optional_params = [p.name for p in schema.parameters if not p.required]
            
            if required_params:
                print(f"  Required: {', '.join(required_params)}")
            if optional_params:
                print(f"  Optional: {', '.join(optional_params)}")
        else:
            print("  No parameters")
        
        print()


if __name__ == "__main__":
    try:
        demonstrate_tool_schemas()
        demonstrate_parameter_validation()
        demonstrate_tool_results()
        demonstrate_output_formatting()
        demonstrate_all_tool_schemas()
        
        print("=== Demonstration Complete ===")
        print("All MCP tool schema functionality is working correctly!")
        
    except Exception as e:
        print(f"Error during demonstration: {e}")
        sys.exit(1)