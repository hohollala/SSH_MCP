"""Unit tests for MCP Server Core."""

import asyncio
import json
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from ssh_mcp_server.server import (
    MCPServer, MCPRequest, MCPResponse
)
from ssh_mcp_server.errors import MCPError, MCPErrorCode
from ssh_mcp_server.models import SSHConfig, CommandResult, ConnectionInfo
from ssh_mcp_server.manager import SSHManagerError
from ssh_mcp_server.tools import ToolError


class TestMCPRequest:
    """Test MCPRequest class."""
    
    def test_from_dict_basic(self):
        """Test creating MCPRequest from basic dictionary."""
        data = {
            "jsonrpc": "2.0",
            "method": "test_method",
            "id": 1
        }
        
        request = MCPRequest.from_dict(data)
        
        assert request.jsonrpc == "2.0"
        assert request.method == "test_method"
        assert request.id == 1
        assert request.params is None
    
    def test_from_dict_with_params(self):
        """Test creating MCPRequest with parameters."""
        data = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "ssh_connect", "arguments": {"hostname": "test.com"}},
            "id": "test-id"
        }
        
        request = MCPRequest.from_dict(data)
        
        assert request.jsonrpc == "2.0"
        assert request.method == "tools/call"
        assert request.params == {"name": "ssh_connect", "arguments": {"hostname": "test.com"}}
        assert request.id == "test-id"
    
    def test_from_dict_defaults(self):
        """Test MCPRequest with default values."""
        data = {"method": "test_method"}
        
        request = MCPRequest.from_dict(data)
        
        assert request.jsonrpc == "2.0"
        assert request.method == "test_method"
        assert request.params is None
        assert request.id is None


class TestMCPResponse:
    """Test MCPResponse class."""
    
    def test_to_dict_success(self):
        """Test converting successful response to dictionary."""
        response = MCPResponse(result={"status": "ok"}, id=1)
        
        result = response.to_dict()
        
        expected = {
            "jsonrpc": "2.0",
            "result": {"status": "ok"},
            "id": 1
        }
        assert result == expected
    
    def test_to_dict_error(self):
        """Test converting error response to dictionary."""
        error = {"code": -32600, "message": "Invalid request"}
        response = MCPResponse(error=error, id=1)
        
        result = response.to_dict()
        
        expected = {
            "jsonrpc": "2.0",
            "error": {"code": -32600, "message": "Invalid request"},
            "id": 1
        }
        assert result == expected
    
    def test_to_dict_no_id(self):
        """Test response without ID."""
        response = MCPResponse(result={"status": "ok"})
        
        result = response.to_dict()
        
        expected = {
            "jsonrpc": "2.0",
            "result": {"status": "ok"}
        }
        assert result == expected


class TestMCPError:
    """Test MCPError class."""
    
    def test_to_dict_basic(self):
        """Test converting basic error to dictionary."""
        error = MCPError(code=-32600, message="Invalid request")
        
        result = error.to_dict()
        
        expected = {
            "code": -32600,
            "message": "Invalid request"
        }
        assert result == expected
    
    def test_to_dict_with_data(self):
        """Test converting error with data to dictionary."""
        error = MCPError(
            code=-32000,
            message="Tool error",
            data={"tool": "ssh_connect", "details": "Connection failed"}
        )
        
        result = error.to_dict()
        
        expected = {
            "code": -32000,
            "message": "Tool error",
            "data": {"tool": "ssh_connect", "details": "Connection failed"}
        }
        assert result == expected


class TestMCPServer:
    """Test MCPServer class."""
    
    @pytest.fixture
    def server(self):
        """Create MCP server for testing."""
        return MCPServer(max_connections=5, debug=True)
    
    def test_init(self, server):
        """Test MCP server initialization."""
        assert server.max_connections == 5
        assert server.debug is True
        assert len(server.tools) == 7  # All registered tools
        assert server._running is False
        assert server._request_count == 0
        assert isinstance(server._start_time, datetime)
    
    def test_register_tools(self, server):
        """Test tool registration."""
        expected_tools = {
            "ssh_connect",
            "ssh_execute", 
            "ssh_read_file",
            "ssh_write_file",
            "ssh_list_directory",
            "ssh_disconnect",
            "ssh_list_connections"
        }
        
        assert set(server.tools.keys()) == expected_tools
        
        # Verify all tools are callable
        for tool_name, tool_handler in server.tools.items():
            assert callable(tool_handler)
    
    @pytest.mark.asyncio
    async def test_start_stop(self, server):
        """Test server start and stop."""
        # Mock SSH manager
        server.ssh_manager.start = AsyncMock()
        server.ssh_manager.stop = AsyncMock()
        
        # Test start
        await server.start()
        assert server._running is True
        server.ssh_manager.start.assert_called_once()
        
        # Test stop
        await server.stop()
        assert server._running is False
        server.ssh_manager.stop.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_already_running(self, server):
        """Test starting server when already running."""
        server._running = True
        server.ssh_manager.start = AsyncMock()
        
        await server.start()
        
        # Should not call SSH manager start again
        server.ssh_manager.start.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_handle_request_string_input(self, server):
        """Test handling request from JSON string."""
        request_json = json.dumps({
            "jsonrpc": "2.0",
            "method": "initialize",
            "id": 1
        })
        
        response = await server.handle_request(request_json)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        assert response["result"]["protocolVersion"] == "2024-11-05"
    
    @pytest.mark.asyncio
    async def test_handle_request_dict_input(self, server):
        """Test handling request from dictionary."""
        request_dict = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "id": 1
        }
        
        response = await server.handle_request(request_dict)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
    
    @pytest.mark.asyncio
    async def test_handle_request_parse_error(self, server):
        """Test handling invalid JSON."""
        invalid_json = "{'invalid': json}"
        
        response = await server.handle_request(invalid_json)
        
        assert response["jsonrpc"] == "2.0"
        assert response["error"]["code"] == MCPErrorCode.PARSE_ERROR
        assert "Parse error" in response["error"]["message"]
    
    @pytest.mark.asyncio
    async def test_handle_request_invalid_request(self, server):
        """Test handling invalid request structure."""
        invalid_request = {"invalid": "request"}
        
        response = await server.handle_request(invalid_request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["error"]["code"] == MCPErrorCode.INVALID_REQUEST
        assert "Invalid request" in response["error"]["message"]
    
    @pytest.mark.asyncio
    async def test_handle_request_method_not_found(self, server):
        """Test handling unknown method."""
        request = {
            "jsonrpc": "2.0",
            "method": "unknown_method",
            "id": 1
        }
        
        response = await server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert response["error"]["code"] == MCPErrorCode.METHOD_NOT_FOUND
        assert "Method not found" in response["error"]["message"]
    
    @pytest.mark.asyncio
    async def test_handle_initialize(self, server):
        """Test initialize request handling."""
        request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "id": 1
        }
        
        response = await server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert response["result"]["protocolVersion"] == "2024-11-05"
        assert "capabilities" in response["result"]
        assert "serverInfo" in response["result"]
        assert response["result"]["serverInfo"]["name"] == "ssh-mcp-server"
    
    @pytest.mark.asyncio
    async def test_handle_tools_list(self, server):
        """Test tools/list request handling."""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": 1
        }
        
        response = await server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "tools" in response["result"]
        assert len(response["result"]["tools"]) == 7
        
        # Check that all tools have required schema fields
        for tool in response["result"]["tools"]:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
    
    @pytest.mark.asyncio
    async def test_handle_tools_call_missing_params(self, server):
        """Test tools/call without parameters."""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 1
        }
        
        response = await server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert response["error"]["code"] == MCPErrorCode.INVALID_PARAMS
        assert "Missing parameters" in response["error"]["message"]
    
    @pytest.mark.asyncio
    async def test_handle_tools_call_missing_tool_name(self, server):
        """Test tools/call without tool name."""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"arguments": {}},
            "id": 1
        }
        
        response = await server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert response["error"]["code"] == MCPErrorCode.INVALID_PARAMS
        assert "Missing tool name" in response["error"]["message"]
    
    @pytest.mark.asyncio
    async def test_handle_tools_call_unknown_tool(self, server):
        """Test tools/call with unknown tool."""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "unknown_tool", "arguments": {}},
            "id": 1
        }
        
        response = await server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert response["error"]["code"] == MCPErrorCode.METHOD_NOT_FOUND
        assert "Tool not found" in response["error"]["message"]
    
    @pytest.mark.asyncio
    async def test_handle_ssh_connect_success(self, server):
        """Test successful ssh_connect tool call."""
        # Mock SSH manager
        server.ssh_manager.create_connection = AsyncMock(return_value="test-conn-id")
        server.ssh_manager.list_connections = AsyncMock(return_value=[
            ConnectionInfo.create("test.com", "user", 22)
        ])
        
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "test.com",
                    "username": "user"
                }
            },
            "id": 1
        }
        
        response = await server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        
        # Parse the result content
        content = json.loads(response["result"]["content"][0]["text"])
        assert content["success"] is True
        assert "data" in content
    
    @pytest.mark.asyncio
    async def test_handle_ssh_connect_failure(self, server):
        """Test failed ssh_connect tool call."""
        # Mock SSH manager to raise error
        server.ssh_manager.create_connection = AsyncMock(
            side_effect=SSHManagerError("Connection failed")
        )
        
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "test.com",
                    "username": "user"
                }
            },
            "id": 1
        }
        
        response = await server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert response["error"]["code"] == MCPErrorCode.TOOL_ERROR
        assert "SSH connection failed" in response["error"]["message"]
    
    @pytest.mark.asyncio
    async def test_handle_ssh_execute_success(self, server):
        """Test successful ssh_execute tool call."""
        # Mock SSH manager
        command_result = CommandResult(
            stdout="Hello World",
            stderr="",
            exit_code=0,
            execution_time=0.5,
            command="echo 'Hello World'"
        )
        server.ssh_manager.execute_command = AsyncMock(return_value=command_result)
        
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_execute",
                "arguments": {
                    "connection_id": "test-conn-id",
                    "command": "echo 'Hello World'"
                }
            },
            "id": 1
        }
        
        response = await server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        
        # Parse the result content
        content = json.loads(response["result"]["content"][0]["text"])
        assert content["success"] is True
        assert content["data"]["stdout"] == "Hello World"
        assert content["data"]["exit_code"] == 0
    
    @pytest.mark.asyncio
    async def test_handle_ssh_disconnect_success(self, server):
        """Test successful ssh_disconnect tool call."""
        # Mock SSH manager
        server.ssh_manager.disconnect_connection = AsyncMock(return_value=True)
        
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_disconnect",
                "arguments": {
                    "connection_id": "test-conn-id"
                }
            },
            "id": 1
        }
        
        response = await server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        
        # Parse the result content
        content = json.loads(response["result"]["content"][0]["text"])
        assert content["success"] is True
        assert content["data"]["status"] == "disconnected"
    
    @pytest.mark.asyncio
    async def test_handle_ssh_list_connections_success(self, server):
        """Test successful ssh_list_connections tool call."""
        # Mock SSH manager
        connections = [
            ConnectionInfo.create("test1.com", "user1", 22),
            ConnectionInfo.create("test2.com", "user2", 2222)
        ]
        server.ssh_manager.list_connections = AsyncMock(return_value=connections)
        
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_list_connections",
                "arguments": {}
            },
            "id": 1
        }
        
        response = await server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        
        # Parse the result content
        content = json.loads(response["result"]["content"][0]["text"])
        assert content["success"] is True
        assert content["data"]["total"] == 2
        assert len(content["data"]["connections"]) == 2
    
    @pytest.mark.asyncio
    async def test_handle_file_operations_connection_not_found(self, server):
        """Test that file operations return connection not found error when connection doesn't exist."""
        # Test ssh_read_file
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_read_file",
                "arguments": {
                    "connection_id": "test-conn-id",
                    "file_path": "/test/path"
                }
            },
            "id": 1
        }
        
        response = await server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert response["error"]["code"] == MCPErrorCode.TOOL_ERROR
        assert "Connection" in response["error"]["message"]
        assert "not found" in response["error"]["message"]
        
        # Test ssh_write_file
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_write_file",
                "arguments": {
                    "connection_id": "test-conn-id",
                    "file_path": "/test/path",
                    "content": "test content"
                }
            },
            "id": 2
        }
        
        response = await server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 2
        assert response["error"]["code"] == MCPErrorCode.TOOL_ERROR
        assert "Connection" in response["error"]["message"]
        assert "not found" in response["error"]["message"]
        
        # Test ssh_list_directory
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_list_directory",
                "arguments": {
                    "connection_id": "test-conn-id",
                    "directory_path": "/test/path"
                }
            },
            "id": 3
        }
        
        response = await server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 3
        assert response["error"]["code"] == MCPErrorCode.TOOL_ERROR
        assert "Connection" in response["error"]["message"]
        assert "not found" in response["error"]["message"]
    
    @pytest.mark.asyncio
    async def test_handle_tools_call_validation_error(self, server):
        """Test tools/call with invalid parameters."""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "test.com"
                    # Missing required username
                }
            },
            "id": 1
        }
        
        response = await server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert response["error"]["code"] == MCPErrorCode.TOOL_ERROR
        assert "Required parameter" in response["error"]["message"]
    
    @pytest.mark.asyncio
    async def test_get_server_stats(self, server):
        """Test getting server statistics."""
        # Mock SSH manager stats
        server.ssh_manager.get_manager_stats = AsyncMock(return_value={
            "active_connections": 2,
            "total_connections_created": 5
        })
        
        stats = await server.get_server_stats()
        
        assert "server" in stats
        assert "ssh_manager" in stats
        assert stats["server"]["running"] is False
        assert stats["server"]["request_count"] == 0
        assert stats["server"]["debug"] is True
        assert stats["server"]["tools_registered"] == 7
        assert stats["ssh_manager"]["active_connections"] == 2
    
    def test_str_repr(self, server):
        """Test string representations."""
        str_repr = str(server)
        assert "MCPServer" in str_repr
        assert "running=False" in str_repr
        assert "tools=7" in str_repr
        
        repr_str = repr(server)
        assert "MCPServer" in repr_str
        assert "max_connections=5" in repr_str
        assert "debug=True" in repr_str


@pytest.mark.asyncio
async def test_server_integration():
    """Integration test for MCP server."""
    server = MCPServer(max_connections=2, debug=False)
    
    try:
        # Start server
        await server.start()
        assert server._running is True
        
        # Test initialize
        init_response = await server.handle_request({
            "jsonrpc": "2.0",
            "method": "initialize",
            "id": 1
        })
        assert init_response["result"]["serverInfo"]["name"] == "ssh-mcp-server"
        
        # Test tools list
        tools_response = await server.handle_request({
            "jsonrpc": "2.0", 
            "method": "tools/list",
            "id": 2
        })
        assert len(tools_response["result"]["tools"]) == 7
        
        # Test server stats
        stats = await server.get_server_stats()
        assert stats["server"]["request_count"] == 2
        
    finally:
        # Stop server
        await server.stop()
        assert server._running is False


if __name__ == "__main__":
    pytest.main([__file__])