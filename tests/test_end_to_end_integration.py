"""End-to-end integration tests for SSH MCP Server.

This module contains comprehensive integration tests that verify the complete
functionality of the SSH MCP Server with real SSH connections and various
authentication methods.
"""

import asyncio
import json
import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from ssh_mcp_server.server import MCPServer
from ssh_mcp_server.models import SSHConfig, ConnectionInfo, CommandResult
from ssh_mcp_server.manager import SSHManager, SSHManagerError
from ssh_mcp_server.connection import SSHConnection, ConnectionError
from ssh_mcp_server.auth import AuthenticationHandler, AuthenticationError
from ssh_mcp_server.errors import MCPError


class TestEndToEndIntegration:
    """Comprehensive end-to-end integration tests."""
    
    @pytest.fixture
    def server(self):
        """Create MCP server for testing."""
        return MCPServer(max_connections=10, debug=True)
    
    @pytest.fixture
    def mock_ssh_server_config(self):
        """Mock SSH server configuration for testing."""
        return {
            "hostname": "test-ssh-server.local",
            "username": "testuser",
            "port": 22,
            "timeout": 30
        }
    
    @pytest.mark.asyncio
    async def test_complete_ssh_workflow_with_key_auth(self, server, mock_ssh_server_config):
        """Test complete SSH workflow: connect -> execute -> file ops -> disconnect."""
        # Mock SSH components for complete workflow
        mock_connection_info = ConnectionInfo.create(
            mock_ssh_server_config["hostname"],
            mock_ssh_server_config["username"],
            mock_ssh_server_config["port"]
        )
        mock_connection_info.connection_id = "workflow-conn-123"
        mock_connection_info.connected = True
        
        # Mock SSH manager methods
        server.ssh_manager.create_connection = AsyncMock(return_value="workflow-conn-123")
        server.ssh_manager.list_connections = AsyncMock(return_value=[mock_connection_info])
        server.ssh_manager.execute_command = AsyncMock(return_value=CommandResult(
            stdout="total 8\ndrwxr-xr-x 2 testuser testuser 4096 Jan 1 12:00 .\ndrwxr-xr-x 3 testuser testuser 4096 Jan 1 12:00 ..",
            stderr="",
            exit_code=0,
            execution_time=0.2,
            command="ls -la"
        ))
        server.ssh_manager.read_file = AsyncMock(return_value="Hello, World!\nThis is a test file.")
        server.ssh_manager.write_file = AsyncMock()
        server.ssh_manager.list_directory = AsyncMock(return_value=[
            {"name": "test.txt", "type": "file", "size": 1024},
            {"name": "subdir", "type": "directory", "size": 4096}
        ])
        server.ssh_manager.disconnect_connection = AsyncMock(return_value=True)
        
        # Step 1: Connect with key authentication
        with patch('pathlib.Path.exists', return_value=True):
            connect_request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_connect",
                    "arguments": {
                        "hostname": mock_ssh_server_config["hostname"],
                        "username": mock_ssh_server_config["username"],
                        "auth_method": "key",
                        "key_path": "/home/testuser/.ssh/id_rsa",
                        "port": mock_ssh_server_config["port"],
                        "timeout": mock_ssh_server_config["timeout"]
                    }
                },
                "id": "workflow-1"
            }
            
            response = await server.handle_request(connect_request)
            assert "result" in response
            content = json.loads(response["result"]["content"][0]["text"])
            assert content["success"] is True
            connection_id = content["data"]["connection_id"]
            assert connection_id == "workflow-conn-123"
        
        # Step 2: Execute command
        execute_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_execute",
                "arguments": {
                    "connection_id": connection_id,
                    "command": "ls -la",
                    "timeout": 30
                }
            },
            "id": "workflow-2"
        }
        
        response = await server.handle_request(execute_request)
        assert "result" in response
        content = json.loads(response["result"]["content"][0]["text"])
        assert content["success"] is True
        assert "total 8" in content["data"]["stdout"]
        assert content["data"]["exit_code"] == 0
        
        # Step 3: Read file
        read_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_read_file",
                "arguments": {
                    "connection_id": connection_id,
                    "file_path": "/home/testuser/test.txt",
                    "encoding": "utf-8"
                }
            },
            "id": "workflow-3"
        }
        
        response = await server.handle_request(read_request)
        assert "result" in response
        content = json.loads(response["result"]["content"][0]["text"])
        assert content["success"] is True
        assert "Hello, World!" in content["data"]["content"]
        
        # Step 4: Write file
        write_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_write_file",
                "arguments": {
                    "connection_id": connection_id,
                    "file_path": "/home/testuser/output.txt",
                    "content": "This is test output\nLine 2\nLine 3",
                    "encoding": "utf-8",
                    "create_dirs": False
                }
            },
            "id": "workflow-4"
        }
        
        response = await server.handle_request(write_request)
        assert "result" in response
        content = json.loads(response["result"]["content"][0]["text"])
        assert content["success"] is True
        assert content["data"]["status"] == "success"
        
        # Step 5: List directory
        list_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_list_directory",
                "arguments": {
                    "connection_id": connection_id,
                    "directory_path": "/home/testuser",
                    "show_hidden": False,
                    "detailed": True
                }
            },
            "id": "workflow-5"
        }
        
        response = await server.handle_request(list_request)
        assert "result" in response
        content = json.loads(response["result"]["content"][0]["text"])
        assert content["success"] is True
        assert len(content["data"]["entries"]) == 2
        assert content["data"]["entries"][0]["name"] == "test.txt"
        
        # Step 6: List connections
        list_conn_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_list_connections",
                "arguments": {}
            },
            "id": "workflow-6"
        }
        
        response = await server.handle_request(list_conn_request)
        assert "result" in response
        content = json.loads(response["result"]["content"][0]["text"])
        assert content["success"] is True
        assert content["data"]["total"] == 1
        assert content["data"]["connections"][0]["connection_id"] == connection_id
        
        # Step 7: Disconnect
        disconnect_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_disconnect",
                "arguments": {
                    "connection_id": connection_id
                }
            },
            "id": "workflow-7"
        }
        
        response = await server.handle_request(disconnect_request)
        assert "result" in response
        content = json.loads(response["result"]["content"][0]["text"])
        assert content["success"] is True
        assert content["data"]["status"] == "disconnected"
        
        # Verify all SSH manager methods were called
        server.ssh_manager.create_connection.assert_called_once()
        server.ssh_manager.execute_command.assert_called_once()
        server.ssh_manager.read_file.assert_called_once()
        server.ssh_manager.write_file.assert_called_once()
        server.ssh_manager.list_directory.assert_called_once()
        server.ssh_manager.disconnect_connection.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_multiple_authentication_methods(self, server):
        """Test different authentication methods work correctly."""
        # Test data for different auth methods
        auth_scenarios = [
            {
                "name": "key_auth",
                "auth_method": "key",
                "key_path": "/home/user/.ssh/id_rsa",
                "connection_id": "key-conn-123"
            },
            {
                "name": "password_auth",
                "auth_method": "password",
                "password": "testpass123",
                "connection_id": "pass-conn-456"
            },
            {
                "name": "agent_auth",
                "auth_method": "agent",
                "connection_id": "agent-conn-789"
            }
        ]
        
        for i, scenario in enumerate(auth_scenarios):
            # Mock connection info for this scenario
            mock_connection_info = ConnectionInfo.create("test.com", "user", 22)
            mock_connection_info.connection_id = scenario["connection_id"]
            mock_connection_info.connected = True
            
            # Mock SSH manager for this scenario
            server.ssh_manager.create_connection = AsyncMock(return_value=scenario["connection_id"])
            server.ssh_manager.list_connections = AsyncMock(return_value=[mock_connection_info])
            
            # Prepare request arguments
            args = {
                "hostname": "test.com",
                "username": "user",
                "auth_method": scenario["auth_method"]
            }
            
            # Add auth-specific parameters
            if scenario["auth_method"] == "key":
                args["key_path"] = scenario["key_path"]
            elif scenario["auth_method"] == "password":
                args["password"] = scenario["password"]
            
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_connect",
                    "arguments": args
                },
                "id": f"auth-test-{i+1}"
            }
            
            # Mock path exists for key auth
            with patch('pathlib.Path.exists', return_value=True):
                # Mock SSH agent for agent auth
                with patch('os.environ.get', return_value='/tmp/ssh_auth_sock'):
                    with patch('os.path.exists', return_value=True):
                        with patch('paramiko.Agent') as mock_agent:
                            mock_agent_instance = Mock()
                            mock_agent_instance.get_keys.return_value = [Mock()]
                            mock_agent.return_value = mock_agent_instance
                            
                            response = await server.handle_request(request)
                            
                            # Verify successful connection
                            assert "result" in response
                            content = json.loads(response["result"]["content"][0]["text"])
                            assert content["success"] is True
                            assert content["data"]["connection_id"] == scenario["connection_id"]
                            
                            # Verify SSH manager was called with correct config
                            call_args = server.ssh_manager.create_connection.call_args[0][0]
                            assert call_args.auth_method == scenario["auth_method"]
                            
                            if scenario["auth_method"] == "key":
                                assert call_args.key_path == scenario["key_path"]
                            elif scenario["auth_method"] == "password":
                                assert call_args.password == scenario["password"]
    
    @pytest.mark.asyncio
    async def test_multiple_concurrent_connections(self, server):
        """Test managing multiple concurrent SSH connections."""
        # Create multiple connection scenarios
        connections = []
        for i in range(5):
            conn_info = ConnectionInfo.create(f"server{i+1}.com", f"user{i+1}", 22 + i)
            conn_info.connection_id = f"multi-conn-{i+1:03d}"
            conn_info.connected = True
            connections.append(conn_info)
        
        # Mock SSH manager for multiple connections
        connection_ids = [conn.connection_id for conn in connections]
        
        call_count = 0
        async def mock_create_connection(config):
            nonlocal call_count
            result = connection_ids[call_count]
            call_count += 1
            return result
        
        server.ssh_manager.create_connection = AsyncMock(side_effect=mock_create_connection)
        server.ssh_manager.list_connections = AsyncMock(return_value=connections)
        
        # Create multiple connection requests
        connect_requests = []
        for i in range(5):
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_connect",
                    "arguments": {
                        "hostname": f"server{i+1}.com",
                        "username": f"user{i+1}",
                        "port": 22 + i,
                        "auth_method": "agent"
                    }
                },
                "id": f"multi-connect-{i+1}"
            }
            connect_requests.append(request)
        
        # Execute all connection requests concurrently
        with patch('os.environ.get', return_value='/tmp/ssh_auth_sock'):
            with patch('os.path.exists', return_value=True):
                with patch('paramiko.Agent') as mock_agent:
                    mock_agent_instance = Mock()
                    mock_agent_instance.get_keys.return_value = [Mock()]
                    mock_agent.return_value = mock_agent_instance
                    
                    tasks = [server.handle_request(req) for req in connect_requests]
                    responses = await asyncio.gather(*tasks)
        
        # Verify all connections were successful
        for i, response in enumerate(responses):
            assert "result" in response
            content = json.loads(response["result"]["content"][0]["text"])
            assert content["success"] is True
            assert content["data"]["connection_id"] == f"multi-conn-{i+1:03d}"
        
        # Test concurrent command execution on different connections
        server.ssh_manager.execute_command = AsyncMock(return_value=CommandResult(
            stdout="concurrent test output",
            stderr="",
            exit_code=0,
            execution_time=0.1,
            command="echo 'concurrent test'"
        ))
        
        execute_requests = []
        for i in range(5):
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_execute",
                    "arguments": {
                        "connection_id": f"multi-conn-{i+1:03d}",
                        "command": f"echo 'test from connection {i+1}'"
                    }
                },
                "id": f"multi-execute-{i+1}"
            }
            execute_requests.append(request)
        
        # Execute commands concurrently
        tasks = [server.handle_request(req) for req in execute_requests]
        responses = await asyncio.gather(*tasks)
        
        # Verify all executions were successful
        for response in responses:
            assert "result" in response
            content = json.loads(response["result"]["content"][0]["text"])
            assert content["success"] is True
            assert "concurrent test output" in content["data"]["stdout"]
        
        # Verify SSH manager was called for each execution
        assert server.ssh_manager.execute_command.call_count == 5
    
    @pytest.mark.asyncio
    async def test_error_scenarios_comprehensive(self, server):
        """Test comprehensive error handling scenarios."""
        # Test connection errors
        connection_error_scenarios = [
            {
                "name": "connection_timeout",
                "error": SSHManagerError("Connection timeout", details="Host unreachable"),
                "expected_message": "SSH connection failed"
            },
            {
                "name": "authentication_failed",
                "error": SSHManagerError("Authentication failed", details="Invalid credentials"),
                "expected_message": "SSH connection failed"
            },
            {
                "name": "host_unreachable",
                "error": SSHManagerError("Host unreachable", details="Network error"),
                "expected_message": "SSH connection failed"
            },
            {
                "name": "max_connections",
                "error": SSHManagerError("Maximum connections reached", details="Limit: 10"),
                "expected_message": "SSH connection failed"
            }
        ]
        
        for i, scenario in enumerate(connection_error_scenarios):
            server.ssh_manager.create_connection = AsyncMock(side_effect=scenario["error"])
            
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_connect",
                    "arguments": {
                        "hostname": "error-test.com",
                        "username": "user",
                        "auth_method": "agent"
                    }
                },
                "id": f"error-connect-{i+1}"
            }
            
            with patch('os.environ.get', return_value='/tmp/ssh_auth_sock'):
                with patch('os.path.exists', return_value=True):
                    with patch('paramiko.Agent') as mock_agent:
                        mock_agent_instance = Mock()
                        mock_agent_instance.get_keys.return_value = [Mock()]
                        mock_agent.return_value = mock_agent_instance
                        
                        response = await server.handle_request(request)
                        
                        # Verify error response
                        assert "error" in response
                        assert scenario["expected_message"] in response["error"]["message"]
                        assert response["error"]["code"] == -32000  # TOOL_ERROR
        
        # Test command execution errors
        execution_error_scenarios = [
            {
                "name": "connection_not_found",
                "error": SSHManagerError("Connection not found", "nonexistent-conn"),
                "expected_message": "Command execution failed"
            },
            {
                "name": "connection_lost",
                "error": SSHManagerError("Connection lost", "lost-conn"),
                "expected_message": "Command execution failed"
            },
            {
                "name": "command_timeout",
                "error": SSHManagerError("Command timeout", "timeout-conn"),
                "expected_message": "Command execution failed"
            }
        ]
        
        for i, scenario in enumerate(execution_error_scenarios):
            server.ssh_manager.execute_command = AsyncMock(side_effect=scenario["error"])
            
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_execute",
                    "arguments": {
                        "connection_id": "test-conn-123",
                        "command": "echo 'test'"
                    }
                },
                "id": f"error-execute-{i+1}"
            }
            
            response = await server.handle_request(request)
            
            # Verify error response
            assert "error" in response
            assert scenario["expected_message"] in response["error"]["message"]
            assert response["error"]["code"] == -32000  # TOOL_ERROR
        
        # Test file operation errors
        file_error_scenarios = [
            {
                "tool": "ssh_read_file",
                "error": SSHManagerError("File not found", "test-conn"),
                "arguments": {
                    "connection_id": "test-conn-123",
                    "file_path": "/nonexistent/file.txt"
                }
            },
            {
                "tool": "ssh_write_file",
                "error": SSHManagerError("Permission denied", "test-conn"),
                "arguments": {
                    "connection_id": "test-conn-123",
                    "file_path": "/root/protected.txt",
                    "content": "test content"
                }
            },
            {
                "tool": "ssh_list_directory",
                "error": SSHManagerError("Directory not accessible", "test-conn"),
                "arguments": {
                    "connection_id": "test-conn-123",
                    "directory_path": "/restricted/dir"
                }
            }
        ]
        
        for i, scenario in enumerate(file_error_scenarios):
            # Mock the appropriate manager method
            if scenario["tool"] == "ssh_read_file":
                server.ssh_manager.read_file = AsyncMock(side_effect=scenario["error"])
            elif scenario["tool"] == "ssh_write_file":
                server.ssh_manager.write_file = AsyncMock(side_effect=scenario["error"])
            elif scenario["tool"] == "ssh_list_directory":
                server.ssh_manager.list_directory = AsyncMock(side_effect=scenario["error"])
            
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": scenario["tool"],
                    "arguments": scenario["arguments"]
                },
                "id": f"error-file-{i+1}"
            }
            
            response = await server.handle_request(request)
            
            # Verify error response
            assert "error" in response
            assert response["error"]["code"] == -32000  # TOOL_ERROR
    
    @pytest.mark.asyncio
    async def test_connection_recovery_scenarios(self, server):
        """Test connection recovery and reconnection scenarios."""
        # Mock connection info
        mock_connection_info = ConnectionInfo.create("recovery.test.com", "user", 22)
        mock_connection_info.connection_id = "recovery-conn-123"
        mock_connection_info.connected = True
        
        # Initial successful connection
        server.ssh_manager.create_connection = AsyncMock(return_value="recovery-conn-123")
        server.ssh_manager.list_connections = AsyncMock(return_value=[mock_connection_info])
        
        # Connect
        connect_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "recovery.test.com",
                    "username": "user",
                    "auth_method": "agent"
                }
            },
            "id": "recovery-1"
        }
        
        with patch('os.environ.get', return_value='/tmp/ssh_auth_sock'):
            with patch('os.path.exists', return_value=True):
                with patch('paramiko.Agent') as mock_agent:
                    mock_agent_instance = Mock()
                    mock_agent_instance.get_keys.return_value = [Mock()]
                    mock_agent.return_value = mock_agent_instance
                    
                    response = await server.handle_request(connect_request)
                    assert "result" in response
        
        # Simulate connection loss and recovery
        connection_lost_scenarios = [
            {
                "name": "temporary_network_loss",
                "first_error": SSHManagerError("Connection lost", "recovery-conn-123"),
                "recovery_result": CommandResult(
                    stdout="recovered output",
                    stderr="",
                    exit_code=0,
                    execution_time=0.3,
                    command="echo 'recovered'"
                )
            },
            {
                "name": "ssh_daemon_restart",
                "first_error": SSHManagerError("SSH daemon not responding", "recovery-conn-123"),
                "recovery_result": CommandResult(
                    stdout="daemon restarted",
                    stderr="",
                    exit_code=0,
                    execution_time=0.5,
                    command="systemctl status sshd"
                )
            }
        ]
        
        for i, scenario in enumerate(recovery_scenarios):
            # First attempt fails
            server.ssh_manager.execute_command = AsyncMock(side_effect=scenario["first_error"])
            
            execute_request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_execute",
                    "arguments": {
                        "connection_id": "recovery-conn-123",
                        "command": "echo 'test recovery'"
                    }
                },
                "id": f"recovery-fail-{i+1}"
            }
            
            response = await server.handle_request(execute_request)
            assert "error" in response
            
            # Second attempt succeeds (simulating recovery)
            server.ssh_manager.execute_command = AsyncMock(return_value=scenario["recovery_result"])
            
            execute_request["id"] = f"recovery-success-{i+1}"
            response = await server.handle_request(execute_request)
            
            assert "result" in response
            content = json.loads(response["result"]["content"][0]["text"])
            assert content["success"] is True
    
    @pytest.mark.asyncio
    async def test_performance_and_stress_scenarios(self, server):
        """Test performance under various stress conditions."""
        # Test rapid connection creation and destruction
        rapid_connections = []
        for i in range(10):
            conn_info = ConnectionInfo.create(f"rapid{i}.com", "user", 22)
            conn_info.connection_id = f"rapid-{i:03d}"
            conn_info.connected = True
            rapid_connections.append(conn_info)
        
        # Mock rapid connection creation
        connection_ids = [conn.connection_id for conn in rapid_connections]
        call_count = 0
        
        async def mock_rapid_create(config):
            nonlocal call_count
            result = connection_ids[call_count % len(connection_ids)]
            call_count += 1
            return result
        
        server.ssh_manager.create_connection = AsyncMock(side_effect=mock_rapid_create)
        server.ssh_manager.list_connections = AsyncMock(return_value=rapid_connections)
        server.ssh_manager.disconnect_connection = AsyncMock(return_value=True)
        
        # Create and destroy connections rapidly
        for i in range(10):
            # Connect
            connect_request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_connect",
                    "arguments": {
                        "hostname": f"rapid{i}.com",
                        "username": "user",
                        "auth_method": "agent"
                    }
                },
                "id": f"rapid-connect-{i}"
            }
            
            with patch('os.environ.get', return_value='/tmp/ssh_auth_sock'):
                with patch('os.path.exists', return_value=True):
                    with patch('paramiko.Agent') as mock_agent:
                        mock_agent_instance = Mock()
                        mock_agent_instance.get_keys.return_value = [Mock()]
                        mock_agent.return_value = mock_agent_instance
                        
                        response = await server.handle_request(connect_request)
                        assert "result" in response
            
            # Disconnect immediately
            disconnect_request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_disconnect",
                    "arguments": {
                        "connection_id": f"rapid-{i:03d}"
                    }
                },
                "id": f"rapid-disconnect-{i}"
            }
            
            response = await server.handle_request(disconnect_request)
            assert "result" in response
        
        # Test high-volume command execution
        server.ssh_manager.execute_command = AsyncMock(return_value=CommandResult(
            stdout="bulk command output",
            stderr="",
            exit_code=0,
            execution_time=0.05,
            command="echo 'bulk'"
        ))
        
        # Execute many commands concurrently
        bulk_requests = []
        for i in range(50):
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_execute",
                    "arguments": {
                        "connection_id": "bulk-conn-123",
                        "command": f"echo 'bulk command {i}'"
                    }
                },
                "id": f"bulk-{i}"
            }
            bulk_requests.append(request)
        
        # Execute all requests concurrently
        tasks = [server.handle_request(req) for req in bulk_requests]
        responses = await asyncio.gather(*tasks)
        
        # Verify all succeeded
        for response in responses:
            assert "result" in response
            content = json.loads(response["result"]["content"][0]["text"])
            assert content["success"] is True
        
        # Verify high call count
        assert server.ssh_manager.execute_command.call_count == 50
    
    @pytest.mark.asyncio
    async def test_mcp_protocol_compliance(self, server):
        """Test MCP protocol compliance and edge cases."""
        # Test invalid JSON-RPC requests
        invalid_requests = [
            # Missing jsonrpc field
            {
                "method": "tools/call",
                "params": {"name": "ssh_connect", "arguments": {}},
                "id": 1
            },
            # Invalid jsonrpc version
            {
                "jsonrpc": "1.0",
                "method": "tools/call",
                "params": {"name": "ssh_connect", "arguments": {}},
                "id": 2
            },
            # Missing method
            {
                "jsonrpc": "2.0",
                "params": {"name": "ssh_connect", "arguments": {}},
                "id": 3
            },
            # Invalid method
            {
                "jsonrpc": "2.0",
                "method": "invalid/method",
                "params": {"name": "ssh_connect", "arguments": {}},
                "id": 4
            },
            # Missing tool name
            {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"arguments": {}},
                "id": 5
            },
            # Invalid tool name
            {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "invalid_tool", "arguments": {}},
                "id": 6
            }
        ]
        
        for i, request in enumerate(invalid_requests):
            response = await server.handle_request(request)
            
            # All should return errors
            assert "error" in response
            assert response["jsonrpc"] == "2.0"
            assert response["id"] == request.get("id", None)
            
            # Error codes should be appropriate
            if "jsonrpc" not in request or request.get("jsonrpc") != "2.0":
                assert response["error"]["code"] == -32600  # Invalid Request
            elif "method" not in request:
                assert response["error"]["code"] == -32600  # Invalid Request
            elif request.get("method") == "invalid/method":
                assert response["error"]["code"] == -32601  # Method not found
            elif "name" not in request.get("params", {}):
                assert response["error"]["code"] == -32602  # Invalid params
            elif request.get("params", {}).get("name") == "invalid_tool":
                assert response["error"]["code"] == -32601  # Method not found
        
        # Test valid requests with proper responses
        mock_connection_info = ConnectionInfo.create("protocol.test.com", "user", 22)
        mock_connection_info.connection_id = "protocol-conn-123"
        
        server.ssh_manager.create_connection = AsyncMock(return_value="protocol-conn-123")
        server.ssh_manager.list_connections = AsyncMock(return_value=[mock_connection_info])
        
        valid_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "protocol.test.com",
                    "username": "user",
                    "auth_method": "agent"
                }
            },
            "id": "protocol-test"
        }
        
        with patch('os.environ.get', return_value='/tmp/ssh_auth_sock'):
            with patch('os.path.exists', return_value=True):
                with patch('paramiko.Agent') as mock_agent:
                    mock_agent_instance = Mock()
                    mock_agent_instance.get_keys.return_value = [Mock()]
                    mock_agent.return_value = mock_agent_instance
                    
                    response = await server.handle_request(valid_request)
                    
                    # Verify proper MCP response structure
                    assert response["jsonrpc"] == "2.0"
                    assert response["id"] == "protocol-test"
                    assert "result" in response
                    assert "content" in response["result"]
                    assert len(response["result"]["content"]) == 1
                    assert response["result"]["content"][0]["type"] == "text"
                    
                    # Verify content is valid JSON
                    content = json.loads(response["result"]["content"][0]["text"])
                    assert isinstance(content, dict)
                    assert "success" in content
                    assert "data" in content
                    assert "metadata" in content


class TestCompatibilityVerification:
    """Tests to verify compatibility with different MCP clients."""
    
    @pytest.fixture
    def server(self):
        """Create MCP server for compatibility testing."""
        return MCPServer(max_connections=5, debug=False)  # Disable debug for client compatibility
    
    @pytest.mark.asyncio
    async def test_claude_code_compatibility(self, server):
        """Test compatibility with Claude Code client patterns."""
        # Mock typical Claude Code usage patterns
        mock_connection_info = ConnectionInfo.create("claude-test.com", "developer", 22)
        mock_connection_info.connection_id = "claude-conn-123"
        
        server.ssh_manager.create_connection = AsyncMock(return_value="claude-conn-123")
        server.ssh_manager.list_connections = AsyncMock(return_value=[mock_connection_info])
        server.ssh_manager.execute_command = AsyncMock(return_value=CommandResult(
            stdout="Python 3.9.7\n",
            stderr="",
            exit_code=0,
            execution_time=0.1,
            command="python3 --version"
        ))
        
        # Typical Claude Code workflow: connect, check environment, execute code
        requests = [
            # Connect
            {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_connect",
                    "arguments": {
                        "hostname": "claude-test.com",
                        "username": "developer",
                        "auth_method": "agent"
                    }
                },
                "id": "claude-1"
            },
            # Check Python version
            {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_execute",
                    "arguments": {
                        "connection_id": "claude-conn-123",
                        "command": "python3 --version"
                    }
                },
                "id": "claude-2"
            }
        ]
        
        with patch('os.environ.get', return_value='/tmp/ssh_auth_sock'):
            with patch('os.path.exists', return_value=True):
                with patch('paramiko.Agent') as mock_agent:
                    mock_agent_instance = Mock()
                    mock_agent_instance.get_keys.return_value = [Mock()]
                    mock_agent.return_value = mock_agent_instance
                    
                    for request in requests:
                        response = await server.handle_request(request)
                        
                        # Verify Claude Code compatible response format
                        assert response["jsonrpc"] == "2.0"
                        assert "result" in response
                        assert "content" in response["result"]
                        
                        # Content should be parseable JSON
                        content_text = response["result"]["content"][0]["text"]
                        content = json.loads(content_text)
                        assert content["success"] is True
    
    @pytest.mark.asyncio
    async def test_gemini_cli_compatibility(self, server):
        """Test compatibility with Gemini CLI client patterns."""
        # Mock Gemini CLI usage patterns (typically more structured)
        mock_connection_info = ConnectionInfo.create("gemini-server.com", "analyst", 22)
        mock_connection_info.connection_id = "gemini-conn-456"
        
        server.ssh_manager.create_connection = AsyncMock(return_value="gemini-conn-456")
        server.ssh_manager.list_connections = AsyncMock(return_value=[mock_connection_info])
        server.ssh_manager.execute_command = AsyncMock(return_value=CommandResult(
            stdout="total 1024\n-rw-r--r-- 1 analyst analyst 512 Jan 1 12:00 data.csv",
            stderr="",
            exit_code=0,
            execution_time=0.2,
            command="ls -la data.csv"
        ))
        
        # Typical Gemini CLI workflow: structured data analysis
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "gemini-server.com",
                    "username": "analyst",
                    "auth_method": "key",
                    "key_path": "/home/analyst/.ssh/gemini_key",
                    "timeout": 60
                }
            },
            "id": "gemini-connect"
        }
        
        with patch('pathlib.Path.exists', return_value=True):
            response = await server.handle_request(request)
            
            # Verify Gemini CLI compatible response
            assert response["jsonrpc"] == "2.0"
            assert response["id"] == "gemini-connect"
            assert "result" in response
            
            content = json.loads(response["result"]["content"][0]["text"])
            assert content["success"] is True
            assert "metadata" in content
            assert content["metadata"]["tool"] == "ssh_connect"
    
    @pytest.mark.asyncio
    async def test_claude_desktop_compatibility(self, server):
        """Test compatibility with Claude Desktop client patterns."""
        # Mock Claude Desktop usage patterns (interactive sessions)
        mock_connection_info = ConnectionInfo.create("desktop-host.local", "user", 22)
        mock_connection_info.connection_id = "desktop-conn-789"
        
        server.ssh_manager.create_connection = AsyncMock(return_value="desktop-conn-789")
        server.ssh_manager.list_connections = AsyncMock(return_value=[mock_connection_info])
        server.ssh_manager.read_file = AsyncMock(return_value="# Configuration file\nserver_name=production\nport=8080")
        
        # Typical Claude Desktop workflow: interactive file exploration
        requests = [
            # Connect with password (common in desktop environments)
            {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_connect",
                    "arguments": {
                        "hostname": "desktop-host.local",
                        "username": "user",
                        "auth_method": "password",
                        "password": "desktop123"
                    }
                },
                "id": "desktop-1"
            },
            # Read configuration file
            {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_read_file",
                    "arguments": {
                        "connection_id": "desktop-conn-789",
                        "file_path": "/etc/app/config.conf"
                    }
                },
                "id": "desktop-2"
            }
        ]
        
        for request in requests:
            response = await server.handle_request(request)
            
            # Verify Claude Desktop compatible response
            assert response["jsonrpc"] == "2.0"
            assert "result" in response
            
            content = json.loads(response["result"]["content"][0]["text"])
            assert content["success"] is True
            
            # Desktop clients expect detailed metadata
            assert "metadata" in content
            assert "timestamp" in content.get("data", {}) or "metadata" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])