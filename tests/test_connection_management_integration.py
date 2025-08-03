"""Integration tests for SSH connection management tools.

This module contains integration tests for the ssh_disconnect and ssh_list_connections
MCP tools, testing their functionality through the complete MCP server stack.
"""

import json
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from ssh_mcp_server.server import MCPServer
from ssh_mcp_server.models import ConnectionInfo, SSHConfig
from ssh_mcp_server.manager import SSHManagerError


class TestConnectionManagementIntegration:
    """Integration tests for connection management tools."""

    @pytest_asyncio.fixture
    async def server(self):
        """Create an MCP server instance for testing."""
        server = MCPServer(max_connections=5, debug=True)
        await server.start()
        yield server
        await server.stop()

    @pytest.mark.asyncio
    async def test_ssh_disconnect_success(self, server):
        """Test successful disconnection of an SSH connection."""
        # Mock SSH manager to simulate successful disconnection
        server.ssh_manager.disconnect_connection = AsyncMock(return_value=True)
        
        # Prepare disconnect request
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_disconnect",
                "arguments": {
                    "connection_id": "test-connection-12345"
                }
            },
            "id": "disconnect-test-1"
        }
        
        # Execute request
        response = await server.handle_request(request)
        
        # Verify response structure
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "disconnect-test-1"
        assert "result" in response
        assert "error" not in response
        
        # Parse and verify result content
        content = json.loads(response["result"]["content"][0]["text"])
        assert content["success"] is True
        assert content["data"]["connection_id"] == "test-connection-12345"
        assert content["data"]["status"] == "disconnected"
        assert content["metadata"]["tool"] == "ssh_disconnect"
        
        # Verify SSH manager was called correctly
        server.ssh_manager.disconnect_connection.assert_called_once_with("test-connection-12345")

    @pytest.mark.asyncio
    async def test_ssh_disconnect_connection_not_found(self, server):
        """Test disconnection when connection ID doesn't exist."""
        # Mock SSH manager to simulate connection not found
        server.ssh_manager.disconnect_connection = AsyncMock(return_value=False)
        
        # Prepare disconnect request
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_disconnect",
                "arguments": {
                    "connection_id": "nonexistent-connection"
                }
            },
            "id": "disconnect-test-2"
        }
        
        # Execute request
        response = await server.handle_request(request)
        
        # Verify error response
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "disconnect-test-2"
        assert "error" in response
        assert "result" not in response
        
        # Verify error details
        error = response["error"]
        assert error["code"] == -32000  # TOOL_ERROR
        assert "Connection not found" in error["message"]
        assert error["data"]["tool"] == "ssh_disconnect"

    @pytest.mark.asyncio
    async def test_ssh_disconnect_manager_error(self, server):
        """Test disconnection when SSH manager raises an error."""
        # Mock SSH manager to raise an error
        server.ssh_manager.disconnect_connection = AsyncMock(
            side_effect=SSHManagerError("Network error during disconnect", "test-conn-123")
        )
        
        # Prepare disconnect request
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_disconnect",
                "arguments": {
                    "connection_id": "test-conn-123"
                }
            },
            "id": "disconnect-test-3"
        }
        
        # Execute request
        response = await server.handle_request(request)
        
        # Verify error response
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "disconnect-test-3"
        assert "error" in response
        
        # Verify error details
        error = response["error"]
        assert error["code"] == -32000  # TOOL_ERROR
        assert "Disconnect failed" in error["message"]
        assert "Network error during disconnect" in error["message"]

    @pytest.mark.asyncio
    async def test_ssh_disconnect_missing_connection_id(self, server):
        """Test disconnection with missing connection_id parameter."""
        # Prepare disconnect request without connection_id
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_disconnect",
                "arguments": {}
            },
            "id": "disconnect-test-4"
        }
        
        # Execute request
        response = await server.handle_request(request)
        
        # Verify error response
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "disconnect-test-4"
        assert "error" in response
        
        # Verify parameter validation error
        error = response["error"]
        assert error["code"] == -32000  # TOOL_ERROR
        assert "Required parameter 'connection_id' is missing" in error["message"]

    @pytest.mark.asyncio
    async def test_ssh_list_connections_empty(self, server):
        """Test listing connections when no connections exist."""
        # Mock SSH manager to return empty list
        server.ssh_manager.list_connections = AsyncMock(return_value=[])
        
        # Prepare list connections request
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_list_connections",
                "arguments": {}
            },
            "id": "list-test-1"
        }
        
        # Execute request
        response = await server.handle_request(request)
        
        # Verify response structure
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "list-test-1"
        assert "result" in response
        assert "error" not in response
        
        # Parse and verify result content
        content = json.loads(response["result"]["content"][0]["text"])
        assert content["success"] is True
        assert content["data"]["total"] == 0
        assert content["data"]["connections"] == []
        assert content["metadata"]["tool"] == "ssh_list_connections"
        
        # Verify SSH manager was called
        server.ssh_manager.list_connections.assert_called_once()

    @pytest.mark.asyncio
    async def test_ssh_list_connections_single(self, server):
        """Test listing connections with a single active connection."""
        # Create mock connection info
        connection_info = ConnectionInfo.create("example.com", "testuser", 22)
        connection_info.connection_id = "conn-12345"
        connection_info.connected = True
        
        # Mock SSH manager to return single connection
        server.ssh_manager.list_connections = AsyncMock(return_value=[connection_info])
        
        # Prepare list connections request
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_list_connections",
                "arguments": {}
            },
            "id": "list-test-2"
        }
        
        # Execute request
        response = await server.handle_request(request)
        
        # Verify response structure
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "list-test-2"
        assert "result" in response
        
        # Parse and verify result content
        content = json.loads(response["result"]["content"][0]["text"])
        assert content["success"] is True
        assert content["data"]["total"] == 1
        assert len(content["data"]["connections"]) == 1
        
        # Verify connection details
        conn = content["data"]["connections"][0]
        assert conn["connection_id"] == "conn-12345"
        assert conn["hostname"] == "example.com"
        assert conn["username"] == "testuser"
        assert conn["port"] == 22
        assert conn["connected"] is True

    @pytest.mark.asyncio
    async def test_ssh_list_connections_multiple(self, server):
        """Test listing connections with multiple active connections."""
        # Create mock connection infos
        connections = []
        for i in range(3):
            conn_info = ConnectionInfo.create(f"server{i+1}.com", f"user{i+1}", 22 + i)
            conn_info.connection_id = f"conn-{i+1:05d}"
            conn_info.connected = i != 1  # Make second connection disconnected
            connections.append(conn_info)
        
        # Mock SSH manager to return multiple connections
        server.ssh_manager.list_connections = AsyncMock(return_value=connections)
        
        # Prepare list connections request
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_list_connections",
                "arguments": {}
            },
            "id": "list-test-3"
        }
        
        # Execute request
        response = await server.handle_request(request)
        
        # Verify response structure
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "list-test-3"
        assert "result" in response
        
        # Parse and verify result content
        content = json.loads(response["result"]["content"][0]["text"])
        assert content["success"] is True
        assert content["data"]["total"] == 3
        assert len(content["data"]["connections"]) == 3
        
        # Verify connection details
        returned_connections = content["data"]["connections"]
        
        # Check first connection
        assert returned_connections[0]["connection_id"] == "conn-00001"
        assert returned_connections[0]["hostname"] == "server1.com"
        assert returned_connections[0]["username"] == "user1"
        assert returned_connections[0]["port"] == 22
        assert returned_connections[0]["connected"] is True
        
        # Check second connection (disconnected)
        assert returned_connections[1]["connection_id"] == "conn-00002"
        assert returned_connections[1]["hostname"] == "server2.com"
        assert returned_connections[1]["username"] == "user2"
        assert returned_connections[1]["port"] == 23
        assert returned_connections[1]["connected"] is False
        
        # Check third connection
        assert returned_connections[2]["connection_id"] == "conn-00003"
        assert returned_connections[2]["hostname"] == "server3.com"
        assert returned_connections[2]["username"] == "user3"
        assert returned_connections[2]["port"] == 24
        assert returned_connections[2]["connected"] is True

    @pytest.mark.asyncio
    async def test_ssh_list_connections_manager_error(self, server):
        """Test listing connections when SSH manager raises an error."""
        # Mock SSH manager to raise an error
        server.ssh_manager.list_connections = AsyncMock(
            side_effect=SSHManagerError("Database connection failed")
        )
        
        # Prepare list connections request
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_list_connections",
                "arguments": {}
            },
            "id": "list-test-4"
        }
        
        # Execute request
        response = await server.handle_request(request)
        
        # Verify error response
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "list-test-4"
        assert "error" in response
        
        # Verify error details
        error = response["error"]
        assert error["code"] == -32000  # TOOL_ERROR
        assert "Failed to list connections" in error["message"]
        assert "Database connection failed" in error["message"]

    @pytest.mark.asyncio
    async def test_connection_management_workflow(self, server):
        """Test a complete workflow of connection management operations."""
        # Mock connection info for workflow
        connection_info = ConnectionInfo.create("workflow.com", "workuser", 22)
        connection_info.connection_id = "workflow-conn-123"
        connection_info.connected = True
        
        # Step 1: List connections (should be empty initially)
        server.ssh_manager.list_connections = AsyncMock(return_value=[])
        
        list_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_list_connections",
                "arguments": {}
            },
            "id": "workflow-1"
        }
        
        response = await server.handle_request(list_request)
        content = json.loads(response["result"]["content"][0]["text"])
        assert content["data"]["total"] == 0
        
        # Step 2: Simulate connection creation (would be done by ssh_connect)
        # Update mock to return the new connection
        server.ssh_manager.list_connections = AsyncMock(return_value=[connection_info])
        
        # Step 3: List connections again (should show the new connection)
        list_request["id"] = "workflow-2"
        response = await server.handle_request(list_request)
        content = json.loads(response["result"]["content"][0]["text"])
        assert content["data"]["total"] == 1
        assert content["data"]["connections"][0]["connection_id"] == "workflow-conn-123"
        
        # Step 4: Disconnect the connection
        server.ssh_manager.disconnect_connection = AsyncMock(return_value=True)
        
        disconnect_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_disconnect",
                "arguments": {
                    "connection_id": "workflow-conn-123"
                }
            },
            "id": "workflow-3"
        }
        
        response = await server.handle_request(disconnect_request)
        content = json.loads(response["result"]["content"][0]["text"])
        assert content["success"] is True
        assert content["data"]["status"] == "disconnected"
        
        # Step 5: List connections again (should be empty after disconnect)
        server.ssh_manager.list_connections = AsyncMock(return_value=[])
        
        list_request["id"] = "workflow-4"
        response = await server.handle_request(list_request)
        content = json.loads(response["result"]["content"][0]["text"])
        assert content["data"]["total"] == 0

    @pytest.mark.asyncio
    async def test_connection_info_formatting(self, server):
        """Test that connection information is properly formatted in responses."""
        # Create connection info with specific timestamps
        now = datetime.now()
        connection_info = ConnectionInfo.create("format-test.com", "formatuser", 2222)
        connection_info.connection_id = "format-test-conn"
        connection_info.connected = True
        connection_info.created_at = now
        connection_info.last_used = now
        
        # Mock SSH manager
        server.ssh_manager.list_connections = AsyncMock(return_value=[connection_info])
        
        # Prepare request
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_list_connections",
                "arguments": {}
            },
            "id": "format-test"
        }
        
        # Execute request
        response = await server.handle_request(request)
        content = json.loads(response["result"]["content"][0]["text"])
        
        # Verify formatting
        conn = content["data"]["connections"][0]
        assert conn["connection_id"] == "format-test-conn"
        assert conn["hostname"] == "format-test.com"
        assert conn["username"] == "formatuser"
        assert conn["port"] == 2222
        assert conn["connected"] is True
        assert "created_at" in conn
        assert "last_used" in conn
        
        # Verify timestamp format (should be ISO format)
        assert conn["created_at"] == now.isoformat()
        assert conn["last_used"] == now.isoformat()

    @pytest.mark.asyncio
    async def test_concurrent_connection_management(self, server):
        """Test concurrent connection management operations."""
        import asyncio
        
        # Mock SSH manager for concurrent operations
        server.ssh_manager.disconnect_connection = AsyncMock(return_value=True)
        server.ssh_manager.list_connections = AsyncMock(return_value=[])
        
        # Create multiple concurrent requests
        requests = []
        
        # Add disconnect requests
        for i in range(3):
            requests.append({
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_disconnect",
                    "arguments": {
                        "connection_id": f"concurrent-conn-{i}"
                    }
                },
                "id": f"concurrent-disconnect-{i}"
            })
        
        # Add list requests
        for i in range(2):
            requests.append({
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_list_connections",
                    "arguments": {}
                },
                "id": f"concurrent-list-{i}"
            })
        
        # Execute all requests concurrently
        tasks = [server.handle_request(req) for req in requests]
        responses = await asyncio.gather(*tasks)
        
        # Verify all responses are successful
        assert len(responses) == 5
        
        for response in responses:
            assert response["jsonrpc"] == "2.0"
            assert "result" in response
            content = json.loads(response["result"]["content"][0]["text"])
            assert content["success"] is True
        
        # Verify disconnect calls were made
        assert server.ssh_manager.disconnect_connection.call_count == 3
        
        # Verify list calls were made
        assert server.ssh_manager.list_connections.call_count == 2