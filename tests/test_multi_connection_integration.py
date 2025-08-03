"""Comprehensive integration tests for multi-connection scenarios.

This module tests the SSH MCP server's ability to handle multiple
concurrent connections with various operations and edge cases.
"""

import asyncio
import json
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from ssh_mcp_server.server import MCPServer
from ssh_mcp_server.models import SSHConfig, ConnectionInfo, CommandResult
from ssh_mcp_server.manager import SSHManager, SSHManagerError


class TestMultiConnectionManagement:
    """Integration tests for managing multiple SSH connections."""
    
    @pytest.fixture
    def server(self):
        """Create MCP server with higher connection limit for testing."""
        return MCPServer(max_connections=20, debug=True)
    
    @pytest.fixture
    def connection_scenarios(self):
        """Create various connection scenarios for testing."""
        scenarios = []
        for i in range(10):
            scenario = {
                "hostname": f"server{i+1:02d}.example.com",
                "username": f"user{i+1:02d}",
                "port": 22 + (i % 3),  # Vary ports: 22, 23, 24
                "auth_method": ["key", "password", "agent"][i % 3],  # Rotate auth methods
                "connection_id": f"multi-conn-{i+1:03d}",
                "connected": True
            }
            
            # Add auth-specific parameters
            if scenario["auth_method"] == "key":
                scenario["key_path"] = f"/home/user{i+1:02d}/.ssh/id_rsa"
            elif scenario["auth_method"] == "password":
                scenario["password"] = f"password{i+1:02d}"
            
            scenarios.append(scenario)
        
        return scenarios
    
    @pytest.mark.asyncio
    async def test_create_multiple_connections_sequentially(self, server, connection_scenarios):
        """Test creating multiple connections one after another."""
        # Mock connection infos
        connection_infos = []
        for scenario in connection_scenarios:
            conn_info = ConnectionInfo.create(
                scenario["hostname"], 
                scenario["username"], 
                scenario["port"]
            )
            conn_info.connection_id = scenario["connection_id"]
            conn_info.connected = scenario["connected"]
            connection_infos.append(conn_info)
        
        # Mock SSH manager for sequential connections
        created_connections = []
        
        async def mock_create_connection(config):
            conn_id = connection_scenarios[len(created_connections)]["connection_id"]
            created_connections.append(conn_id)
            return conn_id
        
        server.ssh_manager.create_connection = AsyncMock(side_effect=mock_create_connection)
        server.ssh_manager.list_connections = AsyncMock(return_value=connection_infos)
        
        # Create connections sequentially
        for i, scenario in enumerate(connection_scenarios):
            args = {
                "hostname": scenario["hostname"],
                "username": scenario["username"],
                "port": scenario["port"],
                "auth_method": scenario["auth_method"]
            }
            
            if "key_path" in scenario:
                args["key_path"] = scenario["key_path"]
            elif "password" in scenario:
                args["password"] = scenario["password"]
            
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_connect",
                    "arguments": args
                },
                "id": f"sequential-{i+1}"
            }
            
            # Mock appropriate authentication methods
            with patch('pathlib.Path.exists', return_value=True):
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
        
        # Verify all connections were created
        assert len(created_connections) == len(connection_scenarios)
        assert server.ssh_manager.create_connection.call_count == len(connection_scenarios)
    
    @pytest.mark.asyncio
    async def test_create_multiple_connections_concurrently(self, server, connection_scenarios):
        """Test creating multiple connections concurrently."""
        # Mock connection infos
        connection_infos = []
        for scenario in connection_scenarios:
            conn_info = ConnectionInfo.create(
                scenario["hostname"], 
                scenario["username"], 
                scenario["port"]
            )
            conn_info.connection_id = scenario["connection_id"]
            conn_info.connected = scenario["connected"]
            connection_infos.append(conn_info)
        
        # Mock SSH manager for concurrent connections
        call_count = 0
        async def mock_create_connection(config):
            nonlocal call_count
            result = connection_scenarios[call_count]["connection_id"]
            call_count += 1
            return result
        
        server.ssh_manager.create_connection = AsyncMock(side_effect=mock_create_connection)
        server.ssh_manager.list_connections = AsyncMock(return_value=connection_infos)
        
        # Create all connection requests
        requests = []
        for i, scenario in enumerate(connection_scenarios):
            args = {
                "hostname": scenario["hostname"],
                "username": scenario["username"],
                "port": scenario["port"],
                "auth_method": scenario["auth_method"]
            }
            
            if "key_path" in scenario:
                args["key_path"] = scenario["key_path"]
            elif "password" in scenario:
                args["password"] = scenario["password"]
            
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_connect",
                    "arguments": args
                },
                "id": f"concurrent-{i+1}"
            }
            requests.append(request)
        
        # Execute all requests concurrently
        with patch('pathlib.Path.exists', return_value=True):
            with patch('os.environ.get', return_value='/tmp/ssh_auth_sock'):
                with patch('os.path.exists', return_value=True):
                    with patch('paramiko.Agent') as mock_agent:
                        mock_agent_instance = Mock()
                        mock_agent_instance.get_keys.return_value = [Mock()]
                        mock_agent.return_value = mock_agent_instance
                        
                        tasks = [server.handle_request(req) for req in requests]
                        responses = await asyncio.gather(*tasks)
        
        # Verify all connections succeeded
        connection_ids = set()
        for response in responses:
            assert "result" in response
            content = json.loads(response["result"]["content"][0]["text"])
            assert content["success"] is True
            connection_ids.add(content["data"]["connection_id"])
        
        # Verify all unique connection IDs were created
        expected_ids = {scenario["connection_id"] for scenario in connection_scenarios}
        assert connection_ids == expected_ids
        assert server.ssh_manager.create_connection.call_count == len(connection_scenarios)
    
    @pytest.mark.asyncio
    async def test_concurrent_operations_on_multiple_connections(self, server, connection_scenarios):
        """Test concurrent operations on multiple established connections."""
        # Setup connections
        connection_infos = []
        for scenario in connection_scenarios:
            conn_info = ConnectionInfo.create(
                scenario["hostname"], 
                scenario["username"], 
                scenario["port"]
            )
            conn_info.connection_id = scenario["connection_id"]
            conn_info.connected = scenario["connected"]
            connection_infos.append(conn_info)
        
        server.ssh_manager.list_connections = AsyncMock(return_value=connection_infos)
        
        # Mock different operations
        server.ssh_manager.execute_command = AsyncMock(return_value=CommandResult(
            stdout="concurrent operation output",
            stderr="",
            exit_code=0,
            execution_time=0.1,
            command="echo 'concurrent test'"
        ))
        
        server.ssh_manager.read_file = AsyncMock(return_value="file content from concurrent read")
        server.ssh_manager.write_file = AsyncMock()
        server.ssh_manager.list_directory = AsyncMock(return_value=[
            {"name": "file1.txt", "type": "file", "size": 1024},
            {"name": "dir1", "type": "directory", "size": 4096}
        ])
        
        # Create mixed operation requests
        operation_requests = []
        operation_types = ["execute", "read_file", "write_file", "list_directory"]
        
        for i, scenario in enumerate(connection_scenarios):
            operation = operation_types[i % len(operation_types)]
            
            if operation == "execute":
                request = {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "ssh_execute",
                        "arguments": {
                            "connection_id": scenario["connection_id"],
                            "command": f"echo 'test from {scenario['hostname']}'"
                        }
                    },
                    "id": f"op-execute-{i}"
                }
            elif operation == "read_file":
                request = {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "ssh_read_file",
                        "arguments": {
                            "connection_id": scenario["connection_id"],
                            "file_path": f"/home/{scenario['username']}/test.txt"
                        }
                    },
                    "id": f"op-read-{i}"
                }
            elif operation == "write_file":
                request = {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "ssh_write_file",
                        "arguments": {
                            "connection_id": scenario["connection_id"],
                            "file_path": f"/home/{scenario['username']}/output.txt",
                            "content": f"Output from {scenario['hostname']}"
                        }
                    },
                    "id": f"op-write-{i}"
                }
            elif operation == "list_directory":
                request = {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "ssh_list_directory",
                        "arguments": {
                            "connection_id": scenario["connection_id"],
                            "directory_path": f"/home/{scenario['username']}"
                        }
                    },
                    "id": f"op-list-{i}"
                }
            
            operation_requests.append(request)
        
        # Execute all operations concurrently
        tasks = [server.handle_request(req) for req in operation_requests]
        responses = await asyncio.gather(*tasks)
        
        # Verify all operations succeeded
        for response in responses:
            assert "result" in response
            content = json.loads(response["result"]["content"][0]["text"])
            assert content["success"] is True
        
        # Verify appropriate manager methods were called
        execute_count = sum(1 for req in operation_requests if "ssh_execute" in req["params"]["name"])
        read_count = sum(1 for req in operation_requests if "ssh_read_file" in req["params"]["name"])
        write_count = sum(1 for req in operation_requests if "ssh_write_file" in req["params"]["name"])
        list_count = sum(1 for req in operation_requests if "ssh_list_directory" in req["params"]["name"])
        
        assert server.ssh_manager.execute_command.call_count == execute_count
        assert server.ssh_manager.read_file.call_count == read_count
        assert server.ssh_manager.write_file.call_count == write_count
        assert server.ssh_manager.list_directory.call_count == list_count
    
    @pytest.mark.asyncio
    async def test_connection_limit_enforcement(self, server):
        """Test that connection limits are properly enforced."""
        # Create more connections than the limit allows
        max_connections = server.max_connections
        excess_connections = 5
        total_attempts = max_connections + excess_connections
        
        # Mock successful connections up to the limit
        successful_connections = []
        for i in range(max_connections):
            conn_info = ConnectionInfo.create(f"limit-test-{i}.com", "user", 22)
            conn_info.connection_id = f"limit-conn-{i:03d}"
            successful_connections.append(conn_info)
        
        # Mock SSH manager behavior
        connection_count = 0
        async def mock_create_connection(config):
            nonlocal connection_count
            if connection_count < max_connections:
                result = f"limit-conn-{connection_count:03d}"
                connection_count += 1
                return result
            else:
                raise SSHManagerError(
                    f"Maximum number of connections ({max_connections}) reached",
                    details=f"Active connections: {max_connections}"
                )
        
        server.ssh_manager.create_connection = AsyncMock(side_effect=mock_create_connection)
        server.ssh_manager.list_connections = AsyncMock(return_value=successful_connections)
        
        # Attempt to create connections beyond the limit
        requests = []
        for i in range(total_attempts):
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
                "id": f"limit-test-{i}"
            }
            requests.append(request)
        
        # Execute requests with mocked agent
        with patch('os.environ.get', return_value='/tmp/ssh_auth_sock'):
            with patch('os.path.exists', return_value=True):
                with patch('paramiko.Agent') as mock_agent:
                    mock_agent_instance = Mock()
                    mock_agent_instance.get_keys.return_value = [Mock()]
                    mock_agent.return_value = mock_agent_instance
                    
                    responses = []
                    for request in requests:
                        response = await server.handle_request(request)
                        responses.append(response)
        
        # Verify results
        successful_responses = [r for r in responses if "result" in r]
        failed_responses = [r for r in responses if "error" in r]
        
        assert len(successful_responses) == max_connections
        assert len(failed_responses) == excess_connections
        
        # Verify error messages for failed connections
        for response in failed_responses:
            assert "Maximum number of connections" in response["error"]["message"]
    
    @pytest.mark.asyncio
    async def test_connection_cleanup_and_reuse(self, server, connection_scenarios):
        """Test connection cleanup and ID reuse scenarios."""
        # Use subset of scenarios for this test
        test_scenarios = connection_scenarios[:5]
        
        # Mock connection infos
        connection_infos = []
        for scenario in test_scenarios:
            conn_info = ConnectionInfo.create(
                scenario["hostname"], 
                scenario["username"], 
                scenario["port"]
            )
            conn_info.connection_id = scenario["connection_id"]
            conn_info.connected = scenario["connected"]
            connection_infos.append(conn_info)
        
        # Mock SSH manager
        call_count = 0
        async def mock_create_connection(config):
            nonlocal call_count
            result = test_scenarios[call_count]["connection_id"]
            call_count += 1
            return result
        
        server.ssh_manager.create_connection = AsyncMock(side_effect=mock_create_connection)
        server.ssh_manager.list_connections = AsyncMock(return_value=connection_infos)
        server.ssh_manager.disconnect_connection = AsyncMock(return_value=True)
        
        # Phase 1: Create all connections
        for i, scenario in enumerate(test_scenarios):
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_connect",
                    "arguments": {
                        "hostname": scenario["hostname"],
                        "username": scenario["username"],
                        "auth_method": "agent"
                    }
                },
                "id": f"cleanup-create-{i}"
            }
            
            with patch('os.environ.get', return_value='/tmp/ssh_auth_sock'):
                with patch('os.path.exists', return_value=True):
                    with patch('paramiko.Agent') as mock_agent:
                        mock_agent_instance = Mock()
                        mock_agent_instance.get_keys.return_value = [Mock()]
                        mock_agent.return_value = mock_agent_instance
                        
                        response = await server.handle_request(request)
                        assert "result" in response
        
        # Phase 2: Disconnect some connections
        connections_to_disconnect = test_scenarios[:3]
        for i, scenario in enumerate(connections_to_disconnect):
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_disconnect",
                    "arguments": {
                        "connection_id": scenario["connection_id"]
                    }
                },
                "id": f"cleanup-disconnect-{i}"
            }
            
            response = await server.handle_request(request)
            assert "result" in response
            content = json.loads(response["result"]["content"][0]["text"])
            assert content["success"] is True
        
        # Phase 3: Verify remaining connections
        remaining_connections = connection_infos[3:]  # Last 2 connections
        server.ssh_manager.list_connections = AsyncMock(return_value=remaining_connections)
        
        list_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_list_connections",
                "arguments": {}
            },
            "id": "cleanup-list"
        }
        
        response = await server.handle_request(list_request)
        assert "result" in response
        content = json.loads(response["result"]["content"][0]["text"])
        assert content["success"] is True
        assert content["data"]["total"] == 2
        
        # Verify disconnect was called for each disconnected connection
        assert server.ssh_manager.disconnect_connection.call_count == 3
    
    @pytest.mark.asyncio
    async def test_mixed_connection_states(self, server, connection_scenarios):
        """Test handling connections in various states (connected, disconnected, error)."""
        # Use subset and modify states
        test_scenarios = connection_scenarios[:6]
        
        # Create connections with mixed states
        connection_infos = []
        for i, scenario in enumerate(test_scenarios):
            conn_info = ConnectionInfo.create(
                scenario["hostname"], 
                scenario["username"], 
                scenario["port"]
            )
            conn_info.connection_id = scenario["connection_id"]
            
            # Vary connection states
            if i < 2:
                conn_info.connected = True  # Healthy connections
            elif i < 4:
                conn_info.connected = False  # Disconnected connections
            else:
                conn_info.connected = True  # Will simulate errors
            
            connection_infos.append(conn_info)
        
        server.ssh_manager.list_connections = AsyncMock(return_value=connection_infos)
        
        # Mock execute command with different behaviors based on connection state
        async def mock_execute_command(connection_id, command, timeout):
            # Find the connection info
            conn_info = next((c for c in connection_infos if c.connection_id == connection_id), None)
            if not conn_info:
                raise SSHManagerError(f"Connection {connection_id} not found")
            
            if not conn_info.connected:
                raise SSHManagerError(f"Connection {connection_id} is not active")
            
            # Simulate error for last 2 connections
            if connection_id in [test_scenarios[4]["connection_id"], test_scenarios[5]["connection_id"]]:
                raise SSHManagerError(f"Network error on connection {connection_id}")
            
            return CommandResult(
                stdout=f"Output from {connection_id}",
                stderr="",
                exit_code=0,
                execution_time=0.1,
                command=command
            )
        
        server.ssh_manager.execute_command = AsyncMock(side_effect=mock_execute_command)
        
        # Test operations on all connections
        requests = []
        for i, scenario in enumerate(test_scenarios):
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_execute",
                    "arguments": {
                        "connection_id": scenario["connection_id"],
                        "command": "echo 'test'"
                    }
                },
                "id": f"mixed-state-{i}"
            }
            requests.append(request)
        
        # Execute all requests
        responses = []
        for request in requests:
            response = await server.handle_request(request)
            responses.append(response)
        
        # Verify results based on connection states
        for i, response in enumerate(responses):
            if i < 2:  # Healthy connections
                assert "result" in response
                content = json.loads(response["result"]["content"][0]["text"])
                assert content["success"] is True
            else:  # Disconnected or error connections
                assert "error" in response
                assert "failed" in response["error"]["message"].lower()
    
    @pytest.mark.asyncio
    async def test_connection_recovery_scenarios(self, server):
        """Test connection recovery in multi-connection environment."""
        # Setup multiple connections with some that will need recovery
        recovery_scenarios = [
            {
                "hostname": "stable.com",
                "connection_id": "stable-conn-001",
                "needs_recovery": False
            },
            {
                "hostname": "unstable.com", 
                "connection_id": "unstable-conn-002",
                "needs_recovery": True
            },
            {
                "hostname": "intermittent.com",
                "connection_id": "intermittent-conn-003", 
                "needs_recovery": True
            }
        ]
        
        # Mock connection infos
        connection_infos = []
        for scenario in recovery_scenarios:
            conn_info = ConnectionInfo.create(scenario["hostname"], "user", 22)
            conn_info.connection_id = scenario["connection_id"]
            conn_info.connected = True
            connection_infos.append(conn_info)
        
        server.ssh_manager.list_connections = AsyncMock(return_value=connection_infos)
        
        # Mock execute command with recovery behavior
        call_counts = {scenario["connection_id"]: 0 for scenario in recovery_scenarios}
        
        async def mock_execute_with_recovery(connection_id, command, timeout):
            call_counts[connection_id] += 1
            
            # Find scenario
            scenario = next((s for s in recovery_scenarios if s["connection_id"] == connection_id), None)
            
            if not scenario["needs_recovery"]:
                # Stable connection always works
                return CommandResult(
                    stdout=f"Stable output from {connection_id}",
                    stderr="",
                    exit_code=0,
                    execution_time=0.1,
                    command=command
                )
            else:
                # Unstable connections fail first, then recover
                if call_counts[connection_id] == 1:
                    raise SSHManagerError(f"Connection lost for {connection_id}")
                else:
                    return CommandResult(
                        stdout=f"Recovered output from {connection_id}",
                        stderr="",
                        exit_code=0,
                        execution_time=0.2,
                        command=command
                    )
        
        server.ssh_manager.execute_command = AsyncMock(side_effect=mock_execute_with_recovery)
        
        # Test operations on all connections
        for scenario in recovery_scenarios:
            # First attempt
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_execute",
                    "arguments": {
                        "connection_id": scenario["connection_id"],
                        "command": "echo 'recovery test'"
                    }
                },
                "id": f"recovery-first-{scenario['connection_id']}"
            }
            
            response = await server.handle_request(request)
            
            if scenario["needs_recovery"]:
                # Should fail on first attempt
                assert "error" in response
            else:
                # Stable connection should succeed
                assert "result" in response
                content = json.loads(response["result"]["content"][0]["text"])
                assert content["success"] is True
                assert "Stable output" in content["data"]["stdout"]
        
        # Second attempt for recovery connections
        for scenario in recovery_scenarios:
            if scenario["needs_recovery"]:
                request = {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "ssh_execute",
                        "arguments": {
                            "connection_id": scenario["connection_id"],
                            "command": "echo 'recovery test retry'"
                        }
                    },
                    "id": f"recovery-second-{scenario['connection_id']}"
                }
                
                response = await server.handle_request(request)
                
                # Should succeed on second attempt
                assert "result" in response
                content = json.loads(response["result"]["content"][0]["text"])
                assert content["success"] is True
                assert "Recovered output" in content["data"]["stdout"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])