#!/usr/bin/env python3
"""
Demonstration of MCP Server Core functionality.

This script shows how to use the MCP server core implementation including
JSON-RPC 2.0 message processing, tool registration, and request handling.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from ssh_mcp_server.server import MCPServer


async def demonstrate_mcp_server():
    """Demonstrate MCP server functionality."""
    print("=== MCP Server Core Demonstration ===\n")
    
    # Create and start MCP server
    server = MCPServer(max_connections=5, debug=True)
    
    try:
        print("1. Starting MCP Server...")
        await server.start()
        print(f"   Server started: {server}")
        print()
        
        # Test initialize request
        print("2. Testing initialize request...")
        init_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "id": 1
        }
        
        response = await server.handle_request(init_request)
        print(f"   Request: {json.dumps(init_request, indent=2)}")
        print(f"   Response: {json.dumps(response, indent=2)}")
        print()
        
        # Test tools/list request
        print("3. Testing tools/list request...")
        tools_request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": 2
        }
        
        response = await server.handle_request(tools_request)
        print(f"   Request: {json.dumps(tools_request, indent=2)}")
        print(f"   Available tools: {len(response['result']['tools'])}")
        for tool in response['result']['tools']:
            print(f"     - {tool['name']}: {tool['description']}")
        print()
        
        # Test tools/call request (ssh_list_connections)
        print("4. Testing tools/call request (ssh_list_connections)...")
        call_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_list_connections",
                "arguments": {}
            },
            "id": 3
        }
        
        response = await server.handle_request(call_request)
        print(f"   Request: {json.dumps(call_request, indent=2)}")
        print(f"   Response success: {'result' in response}")
        if 'result' in response:
            content = json.loads(response['result']['content'][0]['text'])
            print(f"   Active connections: {content['data']['total']}")
        print()
        
        # Test invalid request
        print("5. Testing invalid request handling...")
        invalid_request = {
            "jsonrpc": "2.0",
            "method": "unknown_method",
            "id": 4
        }
        
        response = await server.handle_request(invalid_request)
        print(f"   Request: {json.dumps(invalid_request, indent=2)}")
        print(f"   Error code: {response['error']['code']}")
        print(f"   Error message: {response['error']['message']}")
        print()
        
        # Test parameter validation error
        print("6. Testing parameter validation...")
        validation_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "test.com"
                    # Missing required 'username' parameter
                }
            },
            "id": 5
        }
        
        response = await server.handle_request(validation_request)
        print(f"   Request: {json.dumps(validation_request, indent=2)}")
        print(f"   Validation error: {response['error']['message']}")
        print()
        
        # Test JSON string input
        print("7. Testing JSON string input...")
        json_string_request = json.dumps({
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": 6
        })
        
        response = await server.handle_request(json_string_request)
        print(f"   JSON string input processed successfully: {'result' in response}")
        print()
        
        # Test malformed JSON
        print("8. Testing malformed JSON handling...")
        malformed_json = "{'invalid': json, 'missing': quotes}"
        
        response = await server.handle_request(malformed_json)
        print(f"   Malformed JSON: {malformed_json}")
        print(f"   Parse error handled: {response['error']['code'] == -32700}")
        print(f"   Error message: {response['error']['message']}")
        print()
        
        # Show server statistics
        print("9. Server statistics...")
        stats = await server.get_server_stats()
        print(f"   Server running: {stats['server']['running']}")
        print(f"   Request count: {stats['server']['request_count']}")
        print(f"   Tools registered: {stats['server']['tools_registered']}")
        print(f"   SSH connections: {stats['ssh_manager']['active_connections']}")
        print()
        
    finally:
        print("10. Stopping MCP Server...")
        await server.stop()
        print(f"    Server stopped: {server}")
        print()


async def demonstrate_tool_handlers():
    """Demonstrate individual tool handlers."""
    print("=== Tool Handler Demonstration ===\n")
    
    server = MCPServer(max_connections=2, debug=False)
    
    try:
        await server.start()
        
        # Test ssh_connect with mock (will fail but show validation)
        print("1. Testing ssh_connect tool...")
        connect_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "example.com",
                    "username": "testuser",
                    "auth_method": "agent",
                    "timeout": 10
                }
            },
            "id": 1
        }
        
        response = await server.handle_request(connect_request)
        print(f"   Connection attempt result: {'error' in response}")
        if 'error' in response:
            print(f"   Expected error (no real SSH server): {response['error']['message']}")
        print()
        
        # Test file operations (not implemented)
        print("2. Testing file operation tools (not implemented)...")
        
        # Test ssh_read_file
        read_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_read_file",
                "arguments": {
                    "connection_id": "dummy-id",
                    "file_path": "/test/path"
                }
            },
            "id": 2
        }
        response = await server.handle_request(read_request)
        print(f"   ssh_read_file: {'not yet implemented' in response['error']['message']}")
        
        # Test ssh_write_file
        write_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_write_file",
                "arguments": {
                    "connection_id": "dummy-id",
                    "file_path": "/test/path",
                    "content": "test content"
                }
            },
            "id": 3
        }
        response = await server.handle_request(write_request)
        print(f"   ssh_write_file: {'not yet implemented' in response['error']['message']}")
        
        # Test ssh_list_directory
        list_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_list_directory",
                "arguments": {
                    "connection_id": "dummy-id",
                    "directory_path": "/test/path"
                }
            },
            "id": 4
        }
        response = await server.handle_request(list_request)
        print(f"   ssh_list_directory: {'not yet implemented' in response['error']['message']}")
        
        print()
        
    finally:
        await server.stop()


async def demonstrate_error_handling():
    """Demonstrate error handling capabilities."""
    print("=== Error Handling Demonstration ===\n")
    
    server = MCPServer(max_connections=1, debug=True)
    
    try:
        await server.start()
        
        error_cases = [
            {
                "name": "Parse Error",
                "request": "invalid json {",
                "expected_code": -32700
            },
            {
                "name": "Invalid Request",
                "request": {"invalid": "structure"},
                "expected_code": -32600
            },
            {
                "name": "Method Not Found",
                "request": {"jsonrpc": "2.0", "method": "nonexistent", "id": 1},
                "expected_code": -32601
            },
            {
                "name": "Invalid Params",
                "request": {"jsonrpc": "2.0", "method": "tools/call", "id": 1},
                "expected_code": -32602
            }
        ]
        
        for i, case in enumerate(error_cases, 1):
            print(f"{i}. {case['name']}:")
            response = await server.handle_request(case['request'])
            
            actual_code = response.get('error', {}).get('code')
            print(f"   Expected code: {case['expected_code']}")
            print(f"   Actual code: {actual_code}")
            print(f"   Correct: {actual_code == case['expected_code']}")
            print(f"   Message: {response.get('error', {}).get('message', 'N/A')}")
            print()
        
    finally:
        await server.stop()


async def main():
    """Run all demonstrations."""
    try:
        await demonstrate_mcp_server()
        await demonstrate_tool_handlers()
        await demonstrate_error_handling()
        
        print("=== Demonstration Complete ===")
        print("MCP Server Core implementation is working correctly!")
        print("\nKey features demonstrated:")
        print("✓ JSON-RPC 2.0 message processing")
        print("✓ Tool registration and routing")
        print("✓ Request/response validation")
        print("✓ Error handling and reporting")
        print("✓ Parameter validation")
        print("✓ Server lifecycle management")
        
    except Exception as e:
        print(f"Error during demonstration: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())