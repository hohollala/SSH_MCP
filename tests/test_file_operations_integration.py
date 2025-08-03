"""Integration tests for file operations with MCP server."""

import pytest
import json
from unittest.mock import Mock, AsyncMock, MagicMock

from ssh_mcp_server.server import MCPServer
from ssh_mcp_server.manager import SSHManager
from ssh_mcp_server.connection import SSHConnection
from ssh_mcp_server.models import SSHConfig, ConnectionInfo


class TestFileOperationsIntegration:
    """Integration tests for file operations through MCP server."""
    
    @pytest.fixture
    def mock_ssh_connection(self):
        """Create a mock SSH connection with file operations."""
        connection = Mock(spec=SSHConnection)
        connection.connected = True
        connection.read_file = AsyncMock(return_value="Hello, World!")
        connection.write_file = AsyncMock()
        connection.list_directory = AsyncMock(return_value=[
            {"name": "file1.txt", "type": "file", "size": 1024},
            {"name": "dir1", "type": "directory", "size": 4096}
        ])
        return connection
    
    @pytest.fixture
    def mock_ssh_manager(self, mock_ssh_connection):
        """Create a mock SSH manager with file operations."""
        manager = Mock(spec=SSHManager)
        manager.connections = {"test-conn-id": mock_ssh_connection}
        manager.read_file = AsyncMock(return_value="Hello, World!")
        manager.write_file = AsyncMock()
        manager.list_directory = AsyncMock(return_value=[
            {"name": "file1.txt", "type": "file", "size": 1024},
            {"name": "dir1", "type": "directory", "size": 4096}
        ])
        return manager
    
    @pytest.fixture
    def mcp_server(self, mock_ssh_manager):
        """Create MCP server with mocked SSH manager."""
        server = MCPServer(max_connections=5, debug=True)
        server.ssh_manager = mock_ssh_manager
        return server
    
    @pytest.mark.asyncio
    async def test_ssh_read_file_integration(self, mcp_server):
        """Test complete ssh_read_file workflow through MCP server."""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_read_file",
                "arguments": {
                    "connection_id": "test-conn-id",
                    "file_path": "/home/user/test.txt",
                    "encoding": "utf-8"
                }
            },
            "id": 1
        }
        
        response = await mcp_server.handle_request(request)
        
        # Verify response structure
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        assert "content" in response["result"]
        
        # Parse the result content
        content = json.loads(response["result"]["content"][0]["text"])
        
        # Verify file read result
        assert content["success"] is True
        assert content["data"]["content"] == "Hello, World!"
        assert content["data"]["file_path"] == "/home/user/test.txt"
        assert content["data"]["encoding"] == "utf-8"
        assert content["data"]["size"] == 13
        assert content["data"]["lines"] == 1
        
        # Verify manager was called correctly
        mcp_server.ssh_manager.read_file.assert_called_once_with(
            "test-conn-id", "/home/user/test.txt", "utf-8"
        )
    
    @pytest.mark.asyncio
    async def test_ssh_write_file_integration(self, mcp_server):
        """Test complete ssh_write_file workflow through MCP server."""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_write_file",
                "arguments": {
                    "connection_id": "test-conn-id",
                    "file_path": "/home/user/output.txt",
                    "content": "Hello, World!",
                    "encoding": "utf-8",
                    "create_dirs": True
                }
            },
            "id": 2
        }
        
        response = await mcp_server.handle_request(request)
        
        # Verify response structure
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 2
        assert "result" in response
        assert "content" in response["result"]
        
        # Parse the result content
        content = json.loads(response["result"]["content"][0]["text"])
        
        # Verify file write result
        assert content["success"] is True
        assert content["data"]["file_path"] == "/home/user/output.txt"
        assert content["data"]["bytes_written"] == 13
        assert content["data"]["encoding"] == "utf-8"
        assert content["data"]["create_dirs"] is True
        assert content["data"]["status"] == "success"
        
        # Verify manager was called correctly
        mcp_server.ssh_manager.write_file.assert_called_once_with(
            "test-conn-id", "/home/user/output.txt", "Hello, World!", "utf-8", True
        )
    
    @pytest.mark.asyncio
    async def test_ssh_list_directory_integration(self, mcp_server):
        """Test complete ssh_list_directory workflow through MCP server."""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_list_directory",
                "arguments": {
                    "connection_id": "test-conn-id",
                    "directory_path": "/home/user",
                    "show_hidden": True,
                    "detailed": True
                }
            },
            "id": 3
        }
        
        response = await mcp_server.handle_request(request)
        
        # Verify response structure
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 3
        assert "result" in response
        assert "content" in response["result"]
        
        # Parse the result content
        content = json.loads(response["result"]["content"][0]["text"])
        
        # Verify directory listing result
        assert content["success"] is True
        assert content["data"]["directory_path"] == "/home/user"
        assert content["data"]["total_entries"] == 2
        assert content["data"]["show_hidden"] is True
        assert content["data"]["detailed"] is True
        
        entries = content["data"]["entries"]
        assert len(entries) == 2
        assert entries[0]["name"] == "file1.txt"
        assert entries[0]["type"] == "file"
        assert entries[0]["size"] == 1024
        assert entries[1]["name"] == "dir1"
        assert entries[1]["type"] == "directory"
        assert entries[1]["size"] == 4096
        
        # Verify manager was called correctly
        mcp_server.ssh_manager.list_directory.assert_called_once_with(
            "test-conn-id", "/home/user", True, True
        )
    
    @pytest.mark.asyncio
    async def test_file_operations_parameter_validation(self, mcp_server):
        """Test parameter validation for file operations."""
        # Test missing connection_id
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_read_file",
                "arguments": {
                    "file_path": "/test/file.txt"
                    # Missing connection_id
                }
            },
            "id": 1
        }
        
        response = await mcp_server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "error" in response
        assert "Required parameter 'connection_id' is missing" in response["error"]["message"]
        
        # Test missing file_path for read
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_read_file",
                "arguments": {
                    "connection_id": "test-conn-id"
                    # Missing file_path
                }
            },
            "id": 2
        }
        
        response = await mcp_server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 2
        assert "error" in response
        assert "Required parameter 'file_path' is missing" in response["error"]["message"]
        
        # Test missing content for write
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_write_file",
                "arguments": {
                    "connection_id": "test-conn-id",
                    "file_path": "/test/file.txt"
                    # Missing content
                }
            },
            "id": 3
        }
        
        response = await mcp_server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 3
        assert "error" in response
        assert "Required parameter 'content' is missing" in response["error"]["message"]
    
    @pytest.mark.asyncio
    async def test_file_operations_with_defaults(self, mcp_server):
        """Test file operations with default parameter values."""
        # Test read file with default encoding
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_read_file",
                "arguments": {
                    "connection_id": "test-conn-id",
                    "file_path": "/test/file.txt"
                    # encoding should default to "utf-8"
                }
            },
            "id": 1
        }
        
        response = await mcp_server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        
        # Verify default encoding was used
        mcp_server.ssh_manager.read_file.assert_called_with(
            "test-conn-id", "/test/file.txt", "utf-8"
        )
        
        # Test write file with defaults
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_write_file",
                "arguments": {
                    "connection_id": "test-conn-id",
                    "file_path": "/test/file.txt",
                    "content": "test content"
                    # encoding should default to "utf-8", create_dirs to False
                }
            },
            "id": 2
        }
        
        response = await mcp_server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 2
        assert "result" in response
        
        # Verify defaults were used
        mcp_server.ssh_manager.write_file.assert_called_with(
            "test-conn-id", "/test/file.txt", "test content", "utf-8", False
        )
        
        # Test list directory with defaults
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_list_directory",
                "arguments": {
                    "connection_id": "test-conn-id",
                    "directory_path": "/test/dir"
                    # show_hidden and detailed should default to False
                }
            },
            "id": 3
        }
        
        response = await mcp_server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 3
        assert "result" in response
        
        # Verify defaults were used
        mcp_server.ssh_manager.list_directory.assert_called_with(
            "test-conn-id", "/test/dir", False, False
        )