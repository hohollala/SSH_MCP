"""Comprehensive integration tests for error scenarios.

This module tests various error conditions and edge cases to ensure
robust error handling throughout the SSH MCP server.
"""

import asyncio
import json
import pytest
import tempfile
import os
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from ssh_mcp_server.server import MCPServer
from ssh_mcp_server.models import SSHConfig, ConnectionInfo, CommandResult
from ssh_mcp_server.manager import SSHManager, SSHManagerError
from ssh_mcp_server.connection import SSHConnection, ConnectionError
from ssh_mcp_server.auth import AuthenticationHandler, AuthenticationError
from ssh_mcp_server.errors import MCPError


class TestNetworkErrorScenarios:
    """Integration tests for network-related error scenarios."""
    
    @pytest.fixture
    def server(self):
        """Create MCP server for testing."""
        return MCPServer(max_connections=5, debug=True)
    
    @pytest.mark.asyncio
    async def test_connection_timeout_scenarios(self, server):
        """Test various connection timeout scenarios."""
        timeout_scenarios = [
            {
                "name": "dns_resolution_timeout",
                "hostname": "nonexistent-dns-host.invalid",
                "error": SSHManagerError("DNS resolution timeout", details="Host not found"),
                "expected_message": "SSH connection failed"
            },
            {
                "name": "connection_timeout",
                "hostname": "192.168.254.254",  # Non-routable IP
                "error": SSHManagerError("Connection timeout", details="Host unreachable"),
                "expected_message": "SSH connection failed"
            },
            {
                "name": "ssh_handshake_timeout",
                "hostname": "slow-handshake.com",
                "error": SSHManagerError("SSH handshake timeout", details="Server not responding"),
                "expected_message": "SSH connection failed"
            }
        ]
        
        for scenario in timeout_scenarios:
            # Mock SSH manager to simulate timeout
            server.ssh_manager.create_connection = AsyncMock(side_effect=scenario["error"])
            
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_connect",
                    "arguments": {
                        "hostname": scenario["hostname"],
                        "username": "user",
                        "auth_method": "agent",
                        "timeout": 5  # Short timeout for testing
                    }
                },
                "id": f"timeout-{scenario['name']}"
            }
            
            with patch('os.environ.get', return_value='/tmp/ssh_auth_sock'):
                with patch('os.path.exists', return_value=True):
                    with patch('paramiko.Agent') as mock_agent:
                        mock_agent_instance = Mock()
                        mock_agent_instance.get_keys.return_value = [Mock()]
                        mock_agent.return_value = mock_agent_instance
                        
                        response = await server.handle_request(request)
                        
                        # Verify timeout error
                        assert "error" in response
                        assert scenario["expected_message"] in response["error"]["message"]
                        assert response["error"]["code"] == -32000  # TOOL_ERROR
    
    @pytest.mark.asyncio
    async def test_network_interruption_during_operations(self, server):
        """Test network interruptions during various operations."""
        # Setup initial connection
        mock_connection_info = ConnectionInfo.create("network-test.com", "user", 22)
        mock_connection_info.connection_id = "network-conn-123"
        mock_connection_info.connected = True
        
        server.ssh_manager.create_connection = AsyncMock(return_value="network-conn-123")
        server.ssh_manager.list_connections = AsyncMock(return_value=[mock_connection_info])
        
        # Connect first
        connect_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "network-test.com",
                    "username": "user",
                    "auth_method": "agent"
                }
            },
            "id": "network-connect"
        }
        
        with patch('os.environ.get', return_value='/tmp/ssh_auth_sock'):
            with patch('os.path.exists', return_value=True):
                with patch('paramiko.Agent') as mock_agent:
                    mock_agent_instance = Mock()
                    mock_agent_instance.get_keys.return_value = [Mock()]
                    mock_agent.return_value = mock_agent_instance
                    
                    response = await server.handle_request(connect_request)
                    assert "result" in response
        
        # Test network interruption scenarios during operations
        interruption_scenarios = [
            {
                "operation": "ssh_execute",
                "arguments": {
                    "connection_id": "network-conn-123",
                    "command": "long_running_command"
                },
                "error": SSHManagerError("Network connection lost during command execution", "network-conn-123"),
                "manager_method": "execute_command"
            },
            {
                "operation": "ssh_read_file",
                "arguments": {
                    "connection_id": "network-conn-123",
                    "file_path": "/large/file.txt"
                },
                "error": SSHManagerError("Connection lost during file transfer", "network-conn-123"),
                "manager_method": "read_file"
            },
            {
                "operation": "ssh_write_file",
                "arguments": {
                    "connection_id": "network-conn-123",
                    "file_path": "/remote/file.txt",
                    "content": "test content"
                },
                "error": SSHManagerError("Network error during file write", "network-conn-123"),
                "manager_method": "write_file"
            },
            {
                "operation": "ssh_list_directory",
                "arguments": {
                    "connection_id": "network-conn-123",
                    "directory_path": "/large/directory"
                },
                "error": SSHManagerError("Connection interrupted during directory listing", "network-conn-123"),
                "manager_method": "list_directory"
            }
        ]
        
        for scenario in interruption_scenarios:
            # Mock the appropriate manager method to simulate network interruption
            mock_method = AsyncMock(side_effect=scenario["error"])
            setattr(server.ssh_manager, scenario["manager_method"], mock_method)
            
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": scenario["operation"],
                    "arguments": scenario["arguments"]
                },
                "id": f"interruption-{scenario['operation']}"
            }
            
            response = await server.handle_request(request)
            
            # Verify network interruption error
            assert "error" in response
            assert "failed" in response["error"]["message"].lower()
            assert response["error"]["code"] == -32000  # TOOL_ERROR
    
    @pytest.mark.asyncio
    async def test_port_and_firewall_errors(self, server):
        """Test port-related and firewall error scenarios."""
        port_scenarios = [
            {
                "name": "port_closed",
                "port": 2222,
                "error": SSHManagerError("Connection refused", details="Port 2222 is closed"),
                "expected_message": "SSH connection failed"
            },
            {
                "name": "port_filtered",
                "port": 22,
                "error": SSHManagerError("Connection filtered", details="Firewall blocking connection"),
                "expected_message": "SSH connection failed"
            },
            {
                "name": "invalid_port",
                "port": 99999,  # This should be caught by validation
                "error": None,  # Validation error, not manager error
                "expected_message": "must be <= 65535"
            }
        ]
        
        for scenario in port_scenarios:
            if scenario["error"]:
                # Mock SSH manager to simulate port error
                server.ssh_manager.create_connection = AsyncMock(side_effect=scenario["error"])
            
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_connect",
                    "arguments": {
                        "hostname": "port-test.com",
                        "username": "user",
                        "port": scenario["port"],
                        "auth_method": "agent"
                    }
                },
                "id": f"port-{scenario['name']}"
            }
            
            with patch('os.environ.get', return_value='/tmp/ssh_auth_sock'):
                with patch('os.path.exists', return_value=True):
                    with patch('paramiko.Agent') as mock_agent:
                        mock_agent_instance = Mock()
                        mock_agent_instance.get_keys.return_value = [Mock()]
                        mock_agent.return_value = mock_agent_instance
                        
                        response = await server.handle_request(request)
                        
                        # Verify port error
                        assert "error" in response
                        assert scenario["expected_message"] in response["error"]["message"]


class TestAuthenticationErrorScenarios:
    """Integration tests for authentication-related error scenarios."""
    
    @pytest.fixture
    def server(self):
        """Create MCP server for testing."""
        return MCPServer(max_connections=5, debug=True)
    
    @pytest.mark.asyncio
    async def test_key_authentication_errors(self, server):
        """Test various SSH key authentication error scenarios."""
        key_error_scenarios = [
            {
                "name": "key_file_not_found",
                "key_path": "/nonexistent/key.pem",
                "mock_file_exists": False,
                "error": None,  # Validation error
                "expected_message": "Key file does not exist"
            },
            {
                "name": "key_file_permission_denied",
                "key_path": "/root/.ssh/id_rsa",
                "mock_file_exists": True,
                "error": SSHManagerError("Permission denied reading key file", details="Insufficient permissions"),
                "expected_message": "SSH connection failed"
            },
            {
                "name": "invalid_key_format",
                "key_path": "/tmp/invalid_key.pem",
                "mock_file_exists": True,
                "error": SSHManagerError("Invalid key file format", details="Could not parse private key"),
                "expected_message": "SSH connection failed"
            },
            {
                "name": "encrypted_key_no_passphrase",
                "key_path": "/tmp/encrypted_key.pem",
                "mock_file_exists": True,
                "error": SSHManagerError("Private key is encrypted", details="Passphrase required"),
                "expected_message": "SSH connection failed"
            },
            {
                "name": "key_rejected_by_server",
                "key_path": "/tmp/rejected_key.pem",
                "mock_file_exists": True,
                "error": SSHManagerError("Key rejected by server", details="Public key authentication failed"),
                "expected_message": "SSH connection failed"
            }
        ]
        
        for scenario in key_error_scenarios:
            if scenario["error"]:
                # Mock SSH manager to simulate key error
                server.ssh_manager.create_connection = AsyncMock(side_effect=scenario["error"])
            
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_connect",
                    "arguments": {
                        "hostname": "key-error-test.com",
                        "username": "user",
                        "auth_method": "key",
                        "key_path": scenario["key_path"]
                    }
                },
                "id": f"key-error-{scenario['name']}"
            }
            
            with patch('pathlib.Path.exists', return_value=scenario["mock_file_exists"]):
                response = await server.handle_request(request)
                
                # Verify key authentication error
                assert "error" in response
                assert scenario["expected_message"] in response["error"]["message"]
                assert response["error"]["code"] == -32000  # TOOL_ERROR
    
    @pytest.mark.asyncio
    async def test_password_authentication_errors(self, server):
        """Test various password authentication error scenarios."""
        password_error_scenarios = [
            {
                "name": "wrong_password",
                "password": "wrong_password",
                "error": SSHManagerError("Authentication failed", details="Invalid password"),
                "expected_message": "SSH connection failed"
            },
            {
                "name": "account_locked",
                "password": "correct_password",
                "error": SSHManagerError("Account locked", details="Too many failed attempts"),
                "expected_message": "SSH connection failed"
            },
            {
                "name": "password_expired",
                "password": "expired_password",
                "error": SSHManagerError("Password expired", details="Password change required"),
                "expected_message": "SSH connection failed"
            },
            {
                "name": "user_not_found",
                "password": "any_password",
                "error": SSHManagerError("User not found", details="Invalid username"),
                "expected_message": "SSH connection failed"
            }
        ]
        
        for scenario in password_error_scenarios:
            # Mock SSH manager to simulate password error
            server.ssh_manager.create_connection = AsyncMock(side_effect=scenario["error"])
            
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_connect",
                    "arguments": {
                        "hostname": "password-error-test.com",
                        "username": "user",
                        "auth_method": "password",
                        "password": scenario["password"]
                    }
                },
                "id": f"password-error-{scenario['name']}"
            }
            
            response = await server.handle_request(request)
            
            # Verify password authentication error
            assert "error" in response
            assert scenario["expected_message"] in response["error"]["message"]
            assert response["error"]["code"] == -32000  # TOOL_ERROR
    
    @pytest.mark.asyncio
    async def test_agent_authentication_errors(self, server):
        """Test various SSH agent authentication error scenarios."""
        agent_error_scenarios = [
            {
                "name": "no_agent_running",
                "mock_env_var": None,
                "mock_socket_exists": False,
                "error": None,  # Validation error
                "expected_message": "SSH agent not available"
            },
            {
                "name": "agent_socket_inaccessible",
                "mock_env_var": "/tmp/nonexistent_socket",
                "mock_socket_exists": False,
                "error": None,  # Validation error
                "expected_message": "SSH agent socket not accessible"
            },
            {
                "name": "agent_no_keys",
                "mock_env_var": "/tmp/ssh_auth_sock",
                "mock_socket_exists": True,
                "mock_keys": [],
                "error": SSHManagerError("No keys in SSH agent", details="Agent has no suitable keys"),
                "expected_message": "SSH connection failed"
            },
            {
                "name": "agent_keys_rejected",
                "mock_env_var": "/tmp/ssh_auth_sock",
                "mock_socket_exists": True,
                "mock_keys": [Mock()],
                "error": SSHManagerError("All agent keys rejected", details="Server rejected all keys"),
                "expected_message": "SSH connection failed"
            }
        ]
        
        for scenario in agent_error_scenarios:
            if scenario["error"]:
                # Mock SSH manager to simulate agent error
                server.ssh_manager.create_connection = AsyncMock(side_effect=scenario["error"])
            
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_connect",
                    "arguments": {
                        "hostname": "agent-error-test.com",
                        "username": "user",
                        "auth_method": "agent"
                    }
                },
                "id": f"agent-error-{scenario['name']}"
            }
            
            with patch('os.environ.get', return_value=scenario["mock_env_var"]):
                with patch('os.path.exists', return_value=scenario["mock_socket_exists"]):
                    if scenario.get("mock_keys") is not None:
                        with patch('paramiko.Agent') as mock_agent:
                            mock_agent_instance = Mock()
                            mock_agent_instance.get_keys.return_value = scenario["mock_keys"]
                            mock_agent.return_value = mock_agent_instance
                            
                            response = await server.handle_request(request)
                    else:
                        response = await server.handle_request(request)
                    
                    # Verify agent authentication error
                    assert "error" in response
                    assert scenario["expected_message"] in response["error"]["message"]
                    assert response["error"]["code"] == -32000  # TOOL_ERROR


class TestOperationErrorScenarios:
    """Integration tests for operation-specific error scenarios."""
    
    @pytest.fixture
    def server(self):
        """Create MCP server for testing."""
        return MCPServer(max_connections=5, debug=True)
    
    @pytest.fixture
    def mock_connection_id(self):
        """Mock connection ID for testing."""
        return "error-test-conn-123"
    
    @pytest.mark.asyncio
    async def test_command_execution_errors(self, server, mock_connection_id):
        """Test various command execution error scenarios."""
        execution_error_scenarios = [
            {
                "name": "command_not_found",
                "command": "nonexistent_command",
                "error": None,  # Command executes but returns error
                "result": CommandResult(
                    stdout="",
                    stderr="bash: nonexistent_command: command not found",
                    exit_code=127,
                    execution_time=0.1,
                    command="nonexistent_command"
                )
            },
            {
                "name": "permission_denied",
                "command": "cat /root/secret.txt",
                "error": None,  # Command executes but returns error
                "result": CommandResult(
                    stdout="",
                    stderr="cat: /root/secret.txt: Permission denied",
                    exit_code=1,
                    execution_time=0.05,
                    command="cat /root/secret.txt"
                )
            },
            {
                "name": "command_timeout",
                "command": "sleep 3600",
                "error": SSHManagerError("Command execution timeout", mock_connection_id),
                "result": None
            },
            {
                "name": "connection_lost_during_execution",
                "command": "long_running_process",
                "error": SSHManagerError("Connection lost during command execution", mock_connection_id),
                "result": None
            },
            {
                "name": "out_of_memory",
                "command": "memory_intensive_command",
                "error": None,  # Command executes but returns error
                "result": CommandResult(
                    stdout="",
                    stderr="bash: cannot allocate memory",
                    exit_code=1,
                    execution_time=0.2,
                    command="memory_intensive_command"
                )
            }
        ]
        
        for scenario in execution_error_scenarios:
            if scenario["error"]:
                # Mock SSH manager to simulate execution error
                server.ssh_manager.execute_command = AsyncMock(side_effect=scenario["error"])
            else:
                # Mock SSH manager to return error result
                server.ssh_manager.execute_command = AsyncMock(return_value=scenario["result"])
            
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_execute",
                    "arguments": {
                        "connection_id": mock_connection_id,
                        "command": scenario["command"]
                    }
                },
                "id": f"exec-error-{scenario['name']}"
            }
            
            response = await server.handle_request(request)
            
            if scenario["error"]:
                # Should return MCP error
                assert "error" in response
                assert "Command execution failed" in response["error"]["message"]
                assert response["error"]["code"] == -32000  # TOOL_ERROR
            else:
                # Should return successful MCP response but with command error
                assert "result" in response
                content = json.loads(response["result"]["content"][0]["text"])
                assert content["success"] is True  # MCP operation succeeded
                assert content["data"]["success"] is False  # Command failed
                assert content["data"]["exit_code"] != 0
    
    @pytest.mark.asyncio
    async def test_file_operation_errors(self, server, mock_connection_id):
        """Test various file operation error scenarios."""
        file_error_scenarios = [
            {
                "operation": "ssh_read_file",
                "arguments": {
                    "connection_id": mock_connection_id,
                    "file_path": "/nonexistent/file.txt"
                },
                "error": SSHManagerError("File not found", mock_connection_id),
                "manager_method": "read_file"
            },
            {
                "operation": "ssh_read_file",
                "arguments": {
                    "connection_id": mock_connection_id,
                    "file_path": "/root/secret.txt"
                },
                "error": SSHManagerError("Permission denied", mock_connection_id),
                "manager_method": "read_file"
            },
            {
                "operation": "ssh_write_file",
                "arguments": {
                    "connection_id": mock_connection_id,
                    "file_path": "/readonly/file.txt",
                    "content": "test content"
                },
                "error": SSHManagerError("Read-only file system", mock_connection_id),
                "manager_method": "write_file"
            },
            {
                "operation": "ssh_write_file",
                "arguments": {
                    "connection_id": mock_connection_id,
                    "file_path": "/full/disk/file.txt",
                    "content": "test content"
                },
                "error": SSHManagerError("No space left on device", mock_connection_id),
                "manager_method": "write_file"
            },
            {
                "operation": "ssh_list_directory",
                "arguments": {
                    "connection_id": mock_connection_id,
                    "directory_path": "/nonexistent/directory"
                },
                "error": SSHManagerError("Directory not found", mock_connection_id),
                "manager_method": "list_directory"
            },
            {
                "operation": "ssh_list_directory",
                "arguments": {
                    "connection_id": mock_connection_id,
                    "directory_path": "/restricted/directory"
                },
                "error": SSHManagerError("Permission denied", mock_connection_id),
                "manager_method": "list_directory"
            }
        ]
        
        for scenario in file_error_scenarios:
            # Mock the appropriate manager method to simulate file error
            mock_method = AsyncMock(side_effect=scenario["error"])
            setattr(server.ssh_manager, scenario["manager_method"], mock_method)
            
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": scenario["operation"],
                    "arguments": scenario["arguments"]
                },
                "id": f"file-error-{scenario['operation']}-{len(scenario['arguments'])}"
            }
            
            response = await server.handle_request(request)
            
            # Verify file operation error
            assert "error" in response
            assert "failed" in response["error"]["message"].lower()
            assert response["error"]["code"] == -32000  # TOOL_ERROR
    
    @pytest.mark.asyncio
    async def test_connection_management_errors(self, server):
        """Test connection management error scenarios."""
        connection_error_scenarios = [
            {
                "operation": "ssh_execute",
                "connection_id": "nonexistent-conn-123",
                "error": SSHManagerError("Connection not found", "nonexistent-conn-123"),
                "manager_method": "execute_command",
                "arguments": {"command": "echo test"}
            },
            {
                "operation": "ssh_disconnect",
                "connection_id": "already-disconnected-456",
                "error": None,  # Returns False instead of error
                "manager_method": "disconnect_connection",
                "arguments": {}
            },
            {
                "operation": "ssh_read_file",
                "connection_id": "inactive-conn-789",
                "error": SSHManagerError("Connection is not active", "inactive-conn-789"),
                "manager_method": "read_file",
                "arguments": {"file_path": "/test/file.txt"}
            }
        ]
        
        for scenario in connection_error_scenarios:
            if scenario["error"]:
                # Mock the appropriate manager method to simulate connection error
                mock_method = AsyncMock(side_effect=scenario["error"])
                setattr(server.ssh_manager, scenario["manager_method"], mock_method)
            else:
                # Mock method to return False (for disconnect)
                mock_method = AsyncMock(return_value=False)
                setattr(server.ssh_manager, scenario["manager_method"], mock_method)
            
            # Prepare arguments
            arguments = {"connection_id": scenario["connection_id"]}
            arguments.update(scenario["arguments"])
            
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": scenario["operation"],
                    "arguments": arguments
                },
                "id": f"conn-error-{scenario['operation']}"
            }
            
            response = await server.handle_request(request)
            
            # Verify connection management error
            assert "error" in response
            if scenario["error"]:
                assert scenario["error"].message in response["error"]["message"]
            else:
                assert "not found" in response["error"]["message"].lower()
            assert response["error"]["code"] == -32000  # TOOL_ERROR


class TestResourceLimitErrorScenarios:
    """Integration tests for resource limit error scenarios."""
    
    @pytest.fixture
    def server(self):
        """Create MCP server with limited resources for testing."""
        return MCPServer(max_connections=3, debug=True)  # Low limit for testing
    
    @pytest.mark.asyncio
    async def test_connection_limit_exceeded(self, server):
        """Test behavior when connection limit is exceeded."""
        # Create connections up to the limit
        max_connections = server.max_connections
        
        # Mock successful connections up to limit
        successful_connections = []
        for i in range(max_connections):
            conn_info = ConnectionInfo.create(f"limit-test-{i}.com", "user", 22)
            conn_info.connection_id = f"limit-conn-{i}"
            successful_connections.append(conn_info)
        
        # Mock SSH manager behavior
        connection_count = 0
        async def mock_create_connection(config):
            nonlocal connection_count
            if connection_count < max_connections:
                result = f"limit-conn-{connection_count}"
                connection_count += 1
                return result
            else:
                raise SSHManagerError(
                    f"Maximum number of connections ({max_connections}) reached",
                    details=f"Active connections: {max_connections}"
                )
        
        server.ssh_manager.create_connection = AsyncMock(side_effect=mock_create_connection)
        server.ssh_manager.list_connections = AsyncMock(return_value=successful_connections)
        
        # Create connections up to limit (should succeed)
        for i in range(max_connections):
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_connect",
                    "arguments": {
                        "hostname": f"limit-test-{i}.com",
                        "username": "user",
                        "auth_method": "agent"
                    }
                },
                "id": f"limit-success-{i}"
            }
            
            with patch('os.environ.get', return_value='/tmp/ssh_auth_sock'):
                with patch('os.path.exists', return_value=True):
                    with patch('paramiko.Agent') as mock_agent:
                        mock_agent_instance = Mock()
                        mock_agent_instance.get_keys.return_value = [Mock()]
                        mock_agent.return_value = mock_agent_instance
                        
                        response = await server.handle_request(request)
                        assert "result" in response
        
        # Try to create one more connection (should fail)
        excess_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "excess-connection.com",
                    "username": "user",
                    "auth_method": "agent"
                }
            },
            "id": "limit-exceeded"
        }
        
        with patch('os.environ.get', return_value='/tmp/ssh_auth_sock'):
            with patch('os.path.exists', return_value=True):
                with patch('paramiko.Agent') as mock_agent:
                    mock_agent_instance = Mock()
                    mock_agent_instance.get_keys.return_value = [Mock()]
                    mock_agent.return_value = mock_agent_instance
                    
                    response = await server.handle_request(excess_request)
                    
                    # Should fail with connection limit error
                    assert "error" in response
                    assert "Maximum number of connections" in response["error"]["message"]
                    assert response["error"]["code"] == -32000  # TOOL_ERROR
    
    @pytest.mark.asyncio
    async def test_memory_and_performance_limits(self, server):
        """Test behavior under memory and performance constraints."""
        # Mock connection
        mock_connection_info = ConnectionInfo.create("perf-test.com", "user", 22)
        mock_connection_info.connection_id = "perf-conn-123"
        
        server.ssh_manager.create_connection = AsyncMock(return_value="perf-conn-123")
        server.ssh_manager.list_connections = AsyncMock(return_value=[mock_connection_info])
        
        # Connect first
        connect_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "perf-test.com",
                    "username": "user",
                    "auth_method": "agent"
                }
            },
            "id": "perf-connect"
        }
        
        with patch('os.environ.get', return_value='/tmp/ssh_auth_sock'):
            with patch('os.path.exists', return_value=True):
                with patch('paramiko.Agent') as mock_agent:
                    mock_agent_instance = Mock()
                    mock_agent_instance.get_keys.return_value = [Mock()]
                    mock_agent.return_value = mock_agent_instance
                    
                    response = await server.handle_request(connect_request)
                    assert "result" in response
        
        # Test resource-intensive operations
        resource_scenarios = [
            {
                "name": "large_file_read",
                "operation": "ssh_read_file",
                "arguments": {
                    "connection_id": "perf-conn-123",
                    "file_path": "/huge/file.txt"
                },
                "error": SSHManagerError("File too large to read", "perf-conn-123"),
                "manager_method": "read_file"
            },
            {
                "name": "memory_intensive_command",
                "operation": "ssh_execute",
                "arguments": {
                    "connection_id": "perf-conn-123",
                    "command": "memory_intensive_process"
                },
                "error": SSHManagerError("Command exceeded memory limits", "perf-conn-123"),
                "manager_method": "execute_command"
            },
            {
                "name": "large_directory_listing",
                "operation": "ssh_list_directory",
                "arguments": {
                    "connection_id": "perf-conn-123",
                    "directory_path": "/huge/directory"
                },
                "error": SSHManagerError("Directory too large to list", "perf-conn-123"),
                "manager_method": "list_directory"
            }
        ]
        
        for scenario in resource_scenarios:
            # Mock the appropriate manager method to simulate resource error
            mock_method = AsyncMock(side_effect=scenario["error"])
            setattr(server.ssh_manager, scenario["manager_method"], mock_method)
            
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": scenario["operation"],
                    "arguments": scenario["arguments"]
                },
                "id": f"resource-{scenario['name']}"
            }
            
            response = await server.handle_request(request)
            
            # Verify resource limit error
            assert "error" in response
            assert "failed" in response["error"]["message"].lower()
            assert response["error"]["code"] == -32000  # TOOL_ERROR


if __name__ == "__main__":
    pytest.main([__file__, "-v"])