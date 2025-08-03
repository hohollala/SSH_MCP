"""Integration tests for SSH connect tool."""

import asyncio
import json
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from ssh_mcp_server.server import MCPServer
from ssh_mcp_server.models import SSHConfig, ConnectionInfo
from ssh_mcp_server.manager import SSHManagerError
from ssh_mcp_server.connection import ConnectionError
from ssh_mcp_server.auth import AuthenticationError
from ssh_mcp_server.tools import ToolError


class TestSSHConnectIntegration:
    """Integration tests for ssh_connect tool."""
    
    @pytest.fixture
    def server(self):
        """Create MCP server for testing."""
        return MCPServer(max_connections=5, debug=True)
    
    @pytest.mark.asyncio
    @patch('pathlib.Path.exists', return_value=True)
    async def test_ssh_connect_success_with_key_auth(self, mock_path_exists, server):
        """Test successful SSH connection with key authentication."""
        # Mock SSH manager to simulate successful connection
        mock_connection_info = ConnectionInfo.create("test.example.com", "testuser", 22)
        mock_connection_info.connection_id = "test-conn-123"
        mock_connection_info.connected = True
        
        server.ssh_manager.create_connection = AsyncMock(return_value="test-conn-123")
        server.ssh_manager.list_connections = AsyncMock(return_value=[mock_connection_info])
        
        # Prepare request
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "test.example.com",
                    "username": "testuser",
                    "auth_method": "key",
                    "key_path": "/home/user/.ssh/id_rsa",
                    "port": 22,
                    "timeout": 30
                }
            },
            "id": 1
        }
        
        # Execute request
        response = await server.handle_request(request)
        
        # Verify response structure
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        assert "error" not in response
        
        # Parse and verify result content
        content = json.loads(response["result"]["content"][0]["text"])
        assert content["success"] is True
        assert "data" in content
        
        # Verify connection data
        connection_data = content["data"]
        assert connection_data["connection_id"] == "test-conn-123"
        assert connection_data["hostname"] == "test.example.com"
        assert connection_data["username"] == "testuser"
        assert connection_data["port"] == 22
        assert connection_data["connected"] is True
        
        # Verify SSH manager was called with correct config
        server.ssh_manager.create_connection.assert_called_once()
        call_args = server.ssh_manager.create_connection.call_args[0][0]
        assert isinstance(call_args, SSHConfig)
        assert call_args.hostname == "test.example.com"
        assert call_args.username == "testuser"
        assert call_args.auth_method == "key"
        assert call_args.key_path == "/home/user/.ssh/id_rsa"
        assert call_args.port == 22
        assert call_args.timeout == 30
    
    @pytest.mark.asyncio
    async def test_ssh_connect_success_with_password_auth(self, server):
        """Test successful SSH connection with password authentication."""
        # Mock SSH manager
        mock_connection_info = ConnectionInfo.create("192.168.1.100", "admin", 2222)
        mock_connection_info.connection_id = "test-conn-456"
        mock_connection_info.connected = True
        
        server.ssh_manager.create_connection = AsyncMock(return_value="test-conn-456")
        server.ssh_manager.list_connections = AsyncMock(return_value=[mock_connection_info])
        
        # Prepare request
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "192.168.1.100",
                    "username": "admin",
                    "auth_method": "password",
                    "password": "secret123",
                    "port": 2222,
                    "timeout": 60
                }
            },
            "id": 2
        }
        
        # Execute request
        response = await server.handle_request(request)
        
        # Verify response
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 2
        assert "result" in response
        
        # Parse result
        content = json.loads(response["result"]["content"][0]["text"])
        assert content["success"] is True
        
        # Verify connection data
        connection_data = content["data"]
        assert connection_data["connection_id"] == "test-conn-456"
        assert connection_data["hostname"] == "192.168.1.100"
        assert connection_data["username"] == "admin"
        assert connection_data["port"] == 2222
        
        # Verify SSH manager was called with correct config
        call_args = server.ssh_manager.create_connection.call_args[0][0]
        assert call_args.auth_method == "password"
        assert call_args.password == "secret123"
        assert call_args.port == 2222
        assert call_args.timeout == 60
    
    @pytest.mark.asyncio
    async def test_ssh_connect_success_with_agent_auth(self, server):
        """Test successful SSH connection with SSH agent authentication."""
        # Mock SSH manager
        mock_connection_info = ConnectionInfo.create("server.local", "user", 22)
        mock_connection_info.connection_id = "test-conn-789"
        mock_connection_info.connected = True
        
        server.ssh_manager.create_connection = AsyncMock(return_value="test-conn-789")
        server.ssh_manager.list_connections = AsyncMock(return_value=[mock_connection_info])
        
        # Prepare request with minimal parameters (defaults to agent auth)
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "server.local",
                    "username": "user"
                    # auth_method defaults to "agent"
                    # port defaults to 22
                    # timeout defaults to 30
                }
            },
            "id": 3
        }
        
        # Execute request
        response = await server.handle_request(request)
        
        # Verify response
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 3
        assert "result" in response
        
        # Parse result
        content = json.loads(response["result"]["content"][0]["text"])
        assert content["success"] is True
        
        # Verify SSH manager was called with defaults
        call_args = server.ssh_manager.create_connection.call_args[0][0]
        assert call_args.auth_method == "agent"
        assert call_args.port == 22
        assert call_args.timeout == 30
        assert call_args.key_path is None
        assert call_args.password is None
    
    @pytest.mark.asyncio
    @patch('os.environ.get', return_value='/tmp/fake_ssh_auth_sock')
    @patch('os.path.exists', return_value=True)
    @patch('paramiko.Agent')
    async def test_ssh_connect_connection_failure(self, mock_agent, mock_path_exists, mock_env_get, server):
        """Test SSH connection failure due to connection error."""
        # Mock SSH agent to have keys available
        mock_agent_instance = Mock()
        mock_agent_instance.get_keys.return_value = [Mock()]  # Mock key
        mock_agent.return_value = mock_agent_instance
        
        # Mock SSH manager to raise connection error
        server.ssh_manager.create_connection = AsyncMock(
            side_effect=SSHManagerError(
                "Failed to create connection to unreachable.host",
                details="Connection timed out"
            )
        )
        
        # Prepare request (using agent auth to avoid key file validation)
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "unreachable.host",
                    "username": "user",
                    "auth_method": "agent"  # Changed to agent to avoid key file issues
                }
            },
            "id": 4
        }
        
        # Execute request
        response = await server.handle_request(request)
        
        # Verify error response
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 4
        assert "error" in response
        assert "result" not in response
        
        # Verify error details
        error = response["error"]
        assert error["code"] == -32000  # TOOL_ERROR
        assert "SSH connection failed" in error["message"]
        assert "data" in error
        assert error["data"]["tool"] == "ssh_connect"
        assert error["data"]["details"]["hostname"] == "unreachable.host"
    
    @pytest.mark.asyncio
    async def test_ssh_connect_authentication_failure(self, server):
        """Test SSH connection failure due to authentication error."""
        # Mock SSH manager to raise authentication error
        server.ssh_manager.create_connection = AsyncMock(
            side_effect=SSHManagerError(
                "Authentication failed for user@badhost.com",
                details="Invalid credentials"
            )
        )
        
        # Prepare request
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "badhost.com",
                    "username": "user",
                    "auth_method": "password",
                    "password": "wrongpassword"
                }
            },
            "id": 5
        }
        
        # Execute request
        response = await server.handle_request(request)
        
        # Verify error response
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 5
        assert "error" in response
        
        error = response["error"]
        assert error["code"] == -32000  # TOOL_ERROR
        assert "SSH connection failed" in error["message"]
        assert "Authentication failed" in error["message"]
    
    @pytest.mark.asyncio
    async def test_ssh_connect_max_connections_exceeded(self, server):
        """Test SSH connection failure when max connections exceeded."""
        # Mock SSH manager to raise max connections error
        server.ssh_manager.create_connection = AsyncMock(
            side_effect=SSHManagerError(
                "Maximum number of connections (5) reached",
                details="Active connections: 5"
            )
        )
        
        # Prepare request
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
            "id": 6
        }
        
        # Execute request
        response = await server.handle_request(request)
        
        # Verify error response
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 6
        assert "error" in response
        
        error = response["error"]
        assert error["code"] == -32000  # TOOL_ERROR
        assert "SSH connection failed" in error["message"]
        assert "Maximum number of connections" in error["message"]
    
    @pytest.mark.asyncio
    async def test_ssh_connect_parameter_validation_errors(self, server):
        """Test SSH connect parameter validation errors."""
        # Missing required hostname
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "username": "user"
                    # Missing hostname
                }
            },
            "id": 7
        }
        
        response = await server.handle_request(request)
        assert response["error"]["code"] == -32000  # TOOL_ERROR
        assert "Required parameter 'hostname'" in response["error"]["message"]
        
        # Missing required username
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "test.com"
                    # Missing username
                }
            },
            "id": 8
        }
        
        response = await server.handle_request(request)
        assert response["error"]["code"] == -32000  # TOOL_ERROR
        assert "Required parameter 'username'" in response["error"]["message"]
        
        # Invalid auth method
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "test.com",
                    "username": "user",
                    "auth_method": "invalid_method"
                }
            },
            "id": 9
        }
        
        response = await server.handle_request(request)
        assert response["error"]["code"] == -32000  # TOOL_ERROR
        assert "must be one of" in response["error"]["message"]
        
        # Invalid port range
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "test.com",
                    "username": "user",
                    "port": 70000  # Invalid port
                }
            },
            "id": 10
        }
        
        response = await server.handle_request(request)
        assert response["error"]["code"] == -32000  # TOOL_ERROR
        assert "must be <= 65535" in response["error"]["message"]
        
        # Invalid timeout range
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "test.com",
                    "username": "user",
                    "timeout": 500  # Invalid timeout
                }
            },
            "id": 11
        }
        
        response = await server.handle_request(request)
        assert response["error"]["code"] == -32000  # TOOL_ERROR
        assert "must be <= 300" in response["error"]["message"]
    
    @pytest.mark.asyncio
    async def test_ssh_connect_connection_info_not_found(self, server):
        """Test SSH connect when connection info is not found after creation."""
        # Mock SSH manager to return connection ID but no connection info
        server.ssh_manager.create_connection = AsyncMock(return_value="test-conn-999")
        server.ssh_manager.list_connections = AsyncMock(return_value=[])  # Empty list
        
        # Prepare request
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
            "id": 12
        }
        
        # Execute request
        response = await server.handle_request(request)
        
        # Should still succeed but with minimal data
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 12
        assert "result" in response
        
        content = json.loads(response["result"]["content"][0]["text"])
        assert content["success"] is True
        assert content["data"]["connection_id"] == "test-conn-999"
        assert content["data"]["status"] == "connected"
    
    @pytest.mark.asyncio
    async def test_ssh_connect_with_metadata(self, server):
        """Test SSH connect response includes proper metadata."""
        # Mock SSH manager
        mock_connection_info = ConnectionInfo.create("meta.test.com", "metauser", 22)
        mock_connection_info.connection_id = "meta-conn-123"
        
        server.ssh_manager.create_connection = AsyncMock(return_value="meta-conn-123")
        server.ssh_manager.list_connections = AsyncMock(return_value=[mock_connection_info])
        
        # Prepare request
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "meta.test.com",
                    "username": "metauser"
                }
            },
            "id": 13
        }
        
        # Execute request
        response = await server.handle_request(request)
        
        # Verify response includes metadata
        content = json.loads(response["result"]["content"][0]["text"])
        assert content["success"] is True
        assert "metadata" in content
        assert content["metadata"]["tool"] == "ssh_connect"
    
    @pytest.mark.asyncio
    async def test_ssh_connect_concurrent_connections(self, server):
        """Test creating multiple SSH connections concurrently."""
        # Mock SSH manager for multiple connections
        connection_ids = ["conn-1", "conn-2", "conn-3"]
        connection_infos = [
            ConnectionInfo.create(f"host{i}.com", f"user{i}", 22)
            for i in range(1, 4)
        ]
        
        for i, conn_info in enumerate(connection_infos):
            conn_info.connection_id = connection_ids[i]
        
        # Mock create_connection to return different IDs
        call_count = 0
        async def mock_create_connection(config):
            nonlocal call_count
            result = connection_ids[call_count]
            call_count += 1
            return result
        
        server.ssh_manager.create_connection = AsyncMock(side_effect=mock_create_connection)
        server.ssh_manager.list_connections = AsyncMock(return_value=connection_infos)
        
        # Create multiple requests
        requests = []
        for i in range(1, 4):
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_connect",
                    "arguments": {
                        "hostname": f"host{i}.com",
                        "username": f"user{i}"
                    }
                },
                "id": i
            }
            requests.append(request)
        
        # Execute requests concurrently
        tasks = [server.handle_request(req) for req in requests]
        responses = await asyncio.gather(*tasks)
        
        # Verify all responses are successful
        for i, response in enumerate(responses):
            assert response["jsonrpc"] == "2.0"
            assert response["id"] == i + 1
            assert "result" in response
            
            content = json.loads(response["result"]["content"][0]["text"])
            assert content["success"] is True
            assert content["data"]["connection_id"] == connection_ids[i]
        
        # Verify SSH manager was called for each connection
        assert server.ssh_manager.create_connection.call_count == 3


class TestSSHConnectValidationIntegration:
    """Integration tests for SSH connect parameter validation."""
    
    @pytest.fixture
    def server(self):
        """Create MCP server for testing."""
        return MCPServer(max_connections=5, debug=True)
    
    @pytest.mark.asyncio
    async def test_ssh_connect_validation_comprehensive(self, server):
        """Test comprehensive parameter validation for ssh_connect."""
        # Mock successful connection for valid cases
        mock_connection_info = ConnectionInfo.create("valid.com", "validuser", 22)
        mock_connection_info.connection_id = "valid-conn"
        
        server.ssh_manager.create_connection = AsyncMock(return_value="valid-conn")
        server.ssh_manager.list_connections = AsyncMock(return_value=[mock_connection_info])
        
        # Test valid minimal parameters
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "valid.com",
                    "username": "validuser"
                }
            },
            "id": 1
        }
        
        response = await server.handle_request(request)
        assert "result" in response
        
        # Test valid comprehensive parameters (using password auth to avoid key file issues)
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "comprehensive.test.com",
                    "username": "testuser",
                    "port": 2222,
                    "auth_method": "password",
                    "password": "testpass",
                    "timeout": 120
                }
            },
            "id": 2
        }
        
        response = await server.handle_request(request)
        assert "result" in response
        
        # Verify the SSH manager was called with correct parameters
        call_args = server.ssh_manager.create_connection.call_args[0][0]
        assert call_args.hostname == "comprehensive.test.com"
        assert call_args.username == "testuser"
        assert call_args.port == 2222
        assert call_args.auth_method == "password"
        assert call_args.password == "testpass"
        assert call_args.timeout == 120
    
    @pytest.mark.asyncio
    async def test_ssh_connect_edge_case_parameters(self, server):
        """Test edge case parameter values for ssh_connect."""
        # Mock successful connection
        server.ssh_manager.create_connection = AsyncMock(return_value="edge-conn")
        server.ssh_manager.list_connections = AsyncMock(return_value=[])
        
        # Test minimum valid port
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "edge.com",
                    "username": "user",
                    "port": 1  # Minimum valid port
                }
            },
            "id": 1
        }
        
        response = await server.handle_request(request)
        assert "result" in response
        
        # Test maximum valid port
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "edge.com",
                    "username": "user",
                    "port": 65535  # Maximum valid port
                }
            },
            "id": 2
        }
        
        response = await server.handle_request(request)
        assert "result" in response
        
        # Test minimum valid timeout
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "edge.com",
                    "username": "user",
                    "timeout": 1  # Minimum valid timeout
                }
            },
            "id": 3
        }
        
        response = await server.handle_request(request)
        assert "result" in response
        
        # Test maximum valid timeout
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "edge.com",
                    "username": "user",
                    "timeout": 300  # Maximum valid timeout
                }
            },
            "id": 4
        }
        
        response = await server.handle_request(request)
        assert "result" in response


if __name__ == "__main__":
    pytest.main([__file__])