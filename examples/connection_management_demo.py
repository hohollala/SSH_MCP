#!/usr/bin/env python3
"""
Connection Management Tools Demo

This script demonstrates the ssh_disconnect and ssh_list_connections tools
functionality through the MCP server interface.
"""

import asyncio
import json
import logging
from datetime import datetime

from ssh_mcp_server.server import MCPServer
from ssh_mcp_server.models import ConnectionInfo


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def demo_connection_management():
    """Demonstrate connection management tools functionality."""
    print("=== SSH MCP Server Connection Management Demo ===\n")
    
    # Create and start MCP server
    server = MCPServer(max_connections=5, debug=True)
    await server.start()
    
    try:
        # Step 1: List connections (should be empty initially)
        print("1. Listing connections (should be empty initially):")
        list_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_list_connections",
                "arguments": {}
            },
            "id": "demo-list-1"
        }
        
        response = await server.handle_request(list_request)
        content = json.loads(response["result"]["content"][0]["text"])
        print(f"   Total connections: {content['data']['total']}")
        print(f"   Connections: {content['data']['connections']}\n")
        
        # Step 2: Simulate some connections by mocking the manager
        print("2. Simulating active connections:")
        
        # Create mock connection infos
        mock_connections = []
        for i in range(3):
            conn_info = ConnectionInfo.create(f"server{i+1}.example.com", f"user{i+1}", 22)
            conn_info.connection_id = f"demo-conn-{i+1:03d}"
            conn_info.connected = True
            mock_connections.append(conn_info)
        
        # Mock the list_connections method
        async def mock_list_connections():
            return mock_connections
        
        server.ssh_manager.list_connections = mock_list_connections
        
        # List connections again
        response = await server.handle_request(list_request)
        content = json.loads(response["result"]["content"][0]["text"])
        print(f"   Total connections: {content['data']['total']}")
        
        for i, conn in enumerate(content['data']['connections']):
            print(f"   Connection {i+1}:")
            print(f"     ID: {conn['connection_id']}")
            print(f"     Host: {conn['hostname']}")
            print(f"     User: {conn['username']}")
            print(f"     Status: {'Connected' if conn['connected'] else 'Disconnected'}")
        print()
        
        # Step 3: Disconnect a specific connection
        print("3. Disconnecting a specific connection:")
        connection_to_disconnect = mock_connections[1].connection_id
        print(f"   Disconnecting: {connection_to_disconnect}")
        
        # Mock the disconnect_connection method
        async def mock_disconnect_connection(conn_id):
            if conn_id == connection_to_disconnect:
                # Remove from mock connections
                mock_connections[:] = [c for c in mock_connections if c.connection_id != conn_id]
                return True
            return False
        
        server.ssh_manager.disconnect_connection = mock_disconnect_connection
        
        disconnect_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_disconnect",
                "arguments": {
                    "connection_id": connection_to_disconnect
                }
            },
            "id": "demo-disconnect-1"
        }
        
        response = await server.handle_request(disconnect_request)
        content = json.loads(response["result"]["content"][0]["text"])
        
        if content['success']:
            print(f"   ✓ Successfully disconnected: {content['data']['connection_id']}")
            print(f"   Status: {content['data']['status']}")
        else:
            print(f"   ✗ Failed to disconnect: {content.get('error', 'Unknown error')}")
        print()
        
        # Step 4: List connections again to verify disconnection
        print("4. Listing connections after disconnection:")
        response = await server.handle_request(list_request)
        content = json.loads(response["result"]["content"][0]["text"])
        print(f"   Total connections: {content['data']['total']}")
        
        for i, conn in enumerate(content['data']['connections']):
            print(f"   Connection {i+1}:")
            print(f"     ID: {conn['connection_id']}")
            print(f"     Host: {conn['hostname']}")
            print(f"     User: {conn['username']}")
            print(f"     Status: {'Connected' if conn['connected'] else 'Disconnected'}")
        print()
        
        # Step 5: Try to disconnect a non-existent connection
        print("5. Attempting to disconnect non-existent connection:")
        nonexistent_id = "nonexistent-connection-123"
        print(f"   Attempting to disconnect: {nonexistent_id}")
        
        disconnect_request["params"]["arguments"]["connection_id"] = nonexistent_id
        disconnect_request["id"] = "demo-disconnect-2"
        
        response = await server.handle_request(disconnect_request)
        
        if "error" in response:
            print(f"   ✓ Expected error occurred: {response['error']['message']}")
        else:
            content = json.loads(response["result"]["content"][0]["text"])
            if not content['success']:
                print(f"   ✓ Expected failure: {content.get('error', 'Connection not found')}")
        print()
        
        # Step 6: Demonstrate connection info formatting
        print("6. Connection information formatting:")
        if mock_connections:
            conn = mock_connections[0]
            print(f"   Connection ID: {conn.connection_id}")
            print(f"   Hostname: {conn.hostname}")
            print(f"   Username: {conn.username}")
            print(f"   Port: {conn.port}")
            print(f"   Connected: {conn.connected}")
            print(f"   Created: {conn.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   Last Used: {conn.last_used.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Step 7: Test concurrent operations
        print("7. Testing concurrent connection management:")
        
        # Create multiple concurrent requests
        concurrent_requests = []
        
        # Add list requests
        for i in range(3):
            req = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_list_connections",
                    "arguments": {}
                },
                "id": f"concurrent-list-{i}"
            }
            concurrent_requests.append(req)
        
        # Add disconnect requests for remaining connections
        for conn in mock_connections:
            req = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_disconnect",
                    "arguments": {
                        "connection_id": conn.connection_id
                    }
                },
                "id": f"concurrent-disconnect-{conn.connection_id}"
            }
            concurrent_requests.append(req)
        
        print(f"   Executing {len(concurrent_requests)} concurrent requests...")
        
        # Execute all requests concurrently
        tasks = [server.handle_request(req) for req in concurrent_requests]
        responses = await asyncio.gather(*tasks)
        
        successful_operations = 0
        for response in responses:
            if "result" in response:
                content = json.loads(response["result"]["content"][0]["text"])
                if content.get('success', False):
                    successful_operations += 1
        
        print(f"   ✓ {successful_operations}/{len(responses)} operations completed successfully")
        print()
        
        print("=== Demo completed successfully! ===")
        
    except Exception as e:
        logger.error(f"Demo failed with error: {e}")
        raise
    
    finally:
        # Stop the server
        await server.stop()


async def demo_error_scenarios():
    """Demonstrate error handling in connection management tools."""
    print("\n=== Error Handling Demo ===\n")
    
    server = MCPServer(max_connections=5, debug=True)
    await server.start()
    
    try:
        # Test 1: Missing connection_id parameter
        print("1. Testing missing connection_id parameter:")
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_disconnect",
                "arguments": {}  # Missing connection_id
            },
            "id": "error-test-1"
        }
        
        response = await server.handle_request(request)
        if "error" in response:
            print(f"   ✓ Expected validation error: {response['error']['message']}")
        print()
        
        # Test 2: Invalid parameter type
        print("2. Testing invalid parameter type:")
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_disconnect",
                "arguments": {
                    "connection_id": 12345  # Should be string
                }
            },
            "id": "error-test-2"
        }
        
        response = await server.handle_request(request)
        if "error" in response:
            print(f"   ✓ Expected type error: {response['error']['message']}")
        print()
        
        # Test 3: Manager error simulation
        print("3. Testing SSH manager error:")
        
        # Mock manager to raise an error
        from ssh_mcp_server.manager import SSHManagerError
        
        async def mock_disconnect_with_error(conn_id):
            raise SSHManagerError("Simulated network error", conn_id)
        
        server.ssh_manager.disconnect_connection = mock_disconnect_with_error
        
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_disconnect",
                "arguments": {
                    "connection_id": "test-connection"
                }
            },
            "id": "error-test-3"
        }
        
        response = await server.handle_request(request)
        if "error" in response:
            print(f"   ✓ Expected manager error: {response['error']['message']}")
        print()
        
        print("=== Error handling demo completed! ===")
        
    finally:
        await server.stop()


if __name__ == "__main__":
    print("Starting SSH MCP Server Connection Management Demo...")
    print("This demo shows the ssh_disconnect and ssh_list_connections tools in action.\n")
    
    # Run the main demo
    asyncio.run(demo_connection_management())
    
    # Run error scenarios demo
    asyncio.run(demo_error_scenarios())
    
    print("\nDemo completed! The connection management tools are working correctly.")