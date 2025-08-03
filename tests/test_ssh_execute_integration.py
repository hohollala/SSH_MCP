"""Integration tests for SSH execute tool."""

import asyncio
import json
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from ssh_mcp_server.server import MCPServer
from ssh_mcp_server.models import SSHConfig, CommandResult, ConnectionInfo
from ssh_mcp_server.manager import SSHManagerError
from ssh_mcp_server.tools import ToolError, validate_tool_parameters


class TestSSHExecuteIntegration:
    """Integration tests for ssh_execute tool."""
    
    @pytest.fixture
    def server(self):
        """Create MCP server for testing."""
        return MCPServer(max_connections=5, debug=True)
    
    @pytest.fixture
    def mock_connection_id(self):
        """Mock connection ID for testing."""
        return "12345678-1234-1234-1234-123456789012"
    
    @pytest.fixture
    def sample_command_result(self):
        """Sample command result for testing."""
        return CommandResult(
            stdout="Hello, World!\nThis is a test output",
            stderr="",
            exit_code=0,
            execution_time=0.5,
            command="echo 'Hello, World!'; echo 'This is a test output'"
        )
    
    @pytest.fixture
    def error_command_result(self):
        """Sample error command result for testing."""
        return CommandResult(
            stdout="",
            stderr="bash: nonexistent_command: command not found",
            exit_code=127,
            execution_time=0.1,
            command="nonexistent_command"
        )
    
    @pytest.mark.asyncio
    async def test_ssh_execute_success_basic(self, server, mock_connection_id, sample_command_result):
        """Test successful basic command execution."""
        # Mock SSH manager
        server.ssh_manager.execute_command = AsyncMock(return_value=sample_command_result)
        
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_execute",
                "arguments": {
                    "connection_id": mock_connection_id,
                    "command": "echo 'Hello, World!'"
                }
            },
            "id": 1
        }
        
        response = await server.handle_request(request)
        
        # Verify response structure
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        assert "content" in response["result"]
        assert len(response["result"]["content"]) == 1
        assert response["result"]["content"][0]["type"] == "text"
        
        # Parse and verify result content
        content = json.loads(response["result"]["content"][0]["text"])
        assert content["success"] is True
        assert "data" in content
        assert "metadata" in content
        
        # Verify command result data
        data = content["data"]
        assert data["stdout"] == "Hello, World!\nThis is a test output"
        assert data["stderr"] == ""
        assert data["exit_code"] == 0
        assert data["success"] is True
        assert data["execution_time"] == 0.5
        assert data["command"] == "echo 'Hello, World!'; echo 'This is a test output'"
        assert data["has_output"] is True
        assert "timestamp" in data
        
        # Verify metadata
        assert content["metadata"]["tool"] == "ssh_execute"
        
        # Verify SSH manager was called correctly
        server.ssh_manager.execute_command.assert_called_once_with(
            mock_connection_id, "echo 'Hello, World!'", 60
        )
    
    @pytest.mark.asyncio
    async def test_ssh_execute_success_with_timeout(self, server, mock_connection_id, sample_command_result):
        """Test successful command execution with custom timeout."""
        # Mock SSH manager
        server.ssh_manager.execute_command = AsyncMock(return_value=sample_command_result)
        
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_execute",
                "arguments": {
                    "connection_id": mock_connection_id,
                    "command": "sleep 5 && echo 'done'",
                    "timeout": 120
                }
            },
            "id": 1
        }
        
        response = await server.handle_request(request)
        
        # Verify response is successful
        assert "result" in response
        content = json.loads(response["result"]["content"][0]["text"])
        assert content["success"] is True
        
        # Verify SSH manager was called with custom timeout
        server.ssh_manager.execute_command.assert_called_once_with(
            mock_connection_id, "sleep 5 && echo 'done'", 120
        )
    
    @pytest.mark.asyncio
    async def test_ssh_execute_command_with_error(self, server, mock_connection_id, error_command_result):
        """Test command execution that returns non-zero exit code."""
        # Mock SSH manager
        server.ssh_manager.execute_command = AsyncMock(return_value=error_command_result)
        
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_execute",
                "arguments": {
                    "connection_id": mock_connection_id,
                    "command": "nonexistent_command"
                }
            },
            "id": 1
        }
        
        response = await server.handle_request(request)
        
        # Verify response structure (should still be successful from MCP perspective)
        assert "result" in response
        content = json.loads(response["result"]["content"][0]["text"])
        assert content["success"] is True  # Tool execution succeeded
        
        # Verify command result shows the error
        data = content["data"]
        assert data["stdout"] == ""
        assert data["stderr"] == "bash: nonexistent_command: command not found"
        assert data["exit_code"] == 127
        assert data["success"] is False  # Command execution failed
        assert data["command"] == "nonexistent_command"
    
    @pytest.mark.asyncio
    async def test_ssh_execute_connection_not_found(self, server, mock_connection_id):
        """Test command execution with non-existent connection."""
        # Mock SSH manager to raise connection not found error
        server.ssh_manager.execute_command = AsyncMock(
            side_effect=SSHManagerError(
                f"Connection {mock_connection_id[:8]} not found",
                mock_connection_id,
                "Connection may have been disconnected or never existed"
            )
        )
        
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_execute",
                "arguments": {
                    "connection_id": mock_connection_id,
                    "command": "echo 'test'"
                }
            },
            "id": 1
        }
        
        response = await server.handle_request(request)
        
        # Verify error response
        assert "error" in response
        assert response["error"]["code"] == -32000  # TOOL_ERROR
        assert "Command execution failed" in response["error"]["message"]
        assert "data" in response["error"]
        assert response["error"]["data"]["tool"] == "ssh_execute"
        assert response["error"]["data"]["details"]["connection_id"] == mock_connection_id
    
    @pytest.mark.asyncio
    async def test_ssh_execute_connection_not_active(self, server, mock_connection_id):
        """Test command execution with inactive connection."""
        # Mock SSH manager to raise connection not active error
        server.ssh_manager.execute_command = AsyncMock(
            side_effect=SSHManagerError(
                f"Connection {mock_connection_id[:8]} is not active",
                mock_connection_id,
                "Connection may have been lost or disconnected"
            )
        )
        
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_execute",
                "arguments": {
                    "connection_id": mock_connection_id,
                    "command": "ls -la"
                }
            },
            "id": 1
        }
        
        response = await server.handle_request(request)
        
        # Verify error response
        assert "error" in response
        assert response["error"]["code"] == -32000  # TOOL_ERROR
        assert "Command execution failed" in response["error"]["message"]
    
    @pytest.mark.asyncio
    async def test_ssh_execute_parameter_validation(self, server):
        """Test parameter validation for ssh_execute tool."""
        # Test missing connection_id
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_execute",
                "arguments": {
                    "command": "echo 'test'"
                }
            },
            "id": 1
        }
        
        response = await server.handle_request(request)
        
        assert "error" in response
        assert response["error"]["code"] == -32000  # TOOL_ERROR
        assert "Required parameter" in response["error"]["message"]
        
        # Test missing command
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_execute",
                "arguments": {
                    "connection_id": "12345678-1234-1234-1234-123456789012"
                }
            },
            "id": 2
        }
        
        response = await server.handle_request(request)
        
        assert "error" in response
        assert response["error"]["code"] == -32000  # TOOL_ERROR
        assert "Required parameter" in response["error"]["message"]
        
        # Test invalid timeout (too high)
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_execute",
                "arguments": {
                    "connection_id": "12345678-1234-1234-1234-123456789012",
                    "command": "echo 'test'",
                    "timeout": 5000  # Above maximum of 3600
                }
            },
            "id": 3
        }
        
        response = await server.handle_request(request)
        
        assert "error" in response
        assert response["error"]["code"] == -32000  # TOOL_ERROR
        assert "must be <= 3600" in response["error"]["message"]
        
        # Test invalid timeout (too low)
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_execute",
                "arguments": {
                    "connection_id": "12345678-1234-1234-1234-123456789012",
                    "command": "echo 'test'",
                    "timeout": 0  # Below minimum of 1
                }
            },
            "id": 4
        }
        
        response = await server.handle_request(request)
        
        assert "error" in response
        assert response["error"]["code"] == -32000  # TOOL_ERROR
        assert "must be >= 1" in response["error"]["message"]
    
    @pytest.mark.asyncio
    async def test_ssh_execute_complex_commands(self, server, mock_connection_id):
        """Test execution of complex commands with pipes, redirects, etc."""
        complex_commands = [
            "ps aux | grep nginx | wc -l",
            "find /var/log -name '*.log' -type f | head -10",
            "cat /etc/hosts | grep localhost > /tmp/localhost_entries",
            "for i in {1..5}; do echo \"Line $i\"; done",
            "if [ -f /etc/passwd ]; then echo 'File exists'; else echo 'File not found'; fi"
        ]
        
        for i, command in enumerate(complex_commands):
            # Create a result for each command
            result = CommandResult(
                stdout=f"Output for command {i+1}",
                stderr="",
                exit_code=0,
                execution_time=0.3,
                command=command
            )
            
            server.ssh_manager.execute_command = AsyncMock(return_value=result)
            
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_execute",
                    "arguments": {
                        "connection_id": mock_connection_id,
                        "command": command
                    }
                },
                "id": i + 1
            }
            
            response = await server.handle_request(request)
            
            # Verify successful execution
            assert "result" in response
            content = json.loads(response["result"]["content"][0]["text"])
            assert content["success"] is True
            assert content["data"]["command"] == command
            assert content["data"]["stdout"] == f"Output for command {i+1}"
    
    @pytest.mark.asyncio
    async def test_ssh_execute_long_output(self, server, mock_connection_id):
        """Test command execution with long output."""
        # Create a result with long output
        long_output = "Line " + "\n".join([f"Output line {i}" for i in range(1000)])
        result = CommandResult(
            stdout=long_output,
            stderr="",
            exit_code=0,
            execution_time=2.5,
            command="seq 1 1000 | sed 's/^/Output line /'"
        )
        
        server.ssh_manager.execute_command = AsyncMock(return_value=result)
        
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_execute",
                "arguments": {
                    "connection_id": mock_connection_id,
                    "command": "seq 1 1000 | sed 's/^/Output line /'"
                }
            },
            "id": 1
        }
        
        response = await server.handle_request(request)
        
        # Verify successful execution with long output
        assert "result" in response
        content = json.loads(response["result"]["content"][0]["text"])
        assert content["success"] is True
        assert len(content["data"]["stdout"]) > 10000  # Should be quite long
        assert "Output line 999" in content["data"]["stdout"]
    
    @pytest.mark.asyncio
    async def test_ssh_execute_concurrent_commands(self, server, mock_connection_id):
        """Test concurrent command execution on the same connection."""
        # Create different results for concurrent commands
        results = [
            CommandResult(
                stdout=f"Result {i}",
                stderr="",
                exit_code=0,
                execution_time=0.1 * i,
                command=f"echo 'Command {i}'"
            )
            for i in range(1, 6)
        ]
        
        # Mock SSH manager to return different results based on call count
        call_count = 0
        async def mock_execute_command(conn_id, command, timeout):
            nonlocal call_count
            result = results[call_count % len(results)]
            call_count += 1
            return result
        
        server.ssh_manager.execute_command = AsyncMock(side_effect=mock_execute_command)
        
        # Create concurrent requests
        requests = [
            {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_execute",
                    "arguments": {
                        "connection_id": mock_connection_id,
                        "command": f"echo 'Command {i}'"
                    }
                },
                "id": i
            }
            for i in range(1, 6)
        ]
        
        # Execute requests concurrently
        tasks = [server.handle_request(request) for request in requests]
        responses = await asyncio.gather(*tasks)
        
        # Verify all responses are successful
        for i, response in enumerate(responses):
            assert "result" in response
            content = json.loads(response["result"]["content"][0]["text"])
            assert content["success"] is True
            assert f"Result {i+1}" in content["data"]["stdout"]
        
        # Verify SSH manager was called for each request
        assert server.ssh_manager.execute_command.call_count == 5


class TestSSHExecuteValidationIntegration:
    """Integration tests for ssh_execute parameter validation."""
    
    def test_ssh_execute_validation_comprehensive(self):
        """Test comprehensive parameter validation for ssh_execute."""
        # Valid parameters
        valid_params = {
            "connection_id": "12345678-1234-1234-1234-123456789012",
            "command": "ls -la /home/user",
            "timeout": 30
        }
        
        result = validate_tool_parameters("ssh_execute", valid_params)
        assert result["connection_id"] == "12345678-1234-1234-1234-123456789012"
        assert result["command"] == "ls -la /home/user"
        assert result["timeout"] == 30
        
        # Test with minimal parameters (timeout should default)
        minimal_params = {
            "connection_id": "12345678-1234-1234-1234-123456789012",
            "command": "pwd"
        }
        
        result = validate_tool_parameters("ssh_execute", minimal_params)
        assert result["timeout"] == 60  # default value
        
        # Test timeout boundary values
        boundary_params = {
            "connection_id": "12345678-1234-1234-1234-123456789012",
            "command": "echo 'test'",
            "timeout": 1  # minimum
        }
        
        result = validate_tool_parameters("ssh_execute", boundary_params)
        assert result["timeout"] == 1
        
        boundary_params["timeout"] = 3600  # maximum
        result = validate_tool_parameters("ssh_execute", boundary_params)
        assert result["timeout"] == 3600
    
    def test_ssh_execute_validation_edge_cases(self):
        """Test edge cases in ssh_execute parameter validation."""
        # Test with string timeout (should be converted)
        params = {
            "connection_id": "12345678-1234-1234-1234-123456789012",
            "command": "echo 'test'",
            "timeout": "120"
        }
        
        result = validate_tool_parameters("ssh_execute", params)
        assert result["timeout"] == 120
        assert isinstance(result["timeout"], int)
        
        # Test with empty command (should fail)
        params = {
            "connection_id": "12345678-1234-1234-1234-123456789012",
            "command": ""
        }
        
        # Empty command should pass validation (it's a valid string)
        # The actual emptiness check happens in the connection layer
        result = validate_tool_parameters("ssh_execute", params)
        assert result["command"] == ""
        
        # Test with very long command
        long_command = "echo '" + "x" * 10000 + "'"
        params = {
            "connection_id": "12345678-1234-1234-1234-123456789012",
            "command": long_command
        }
        
        result = validate_tool_parameters("ssh_execute", params)
        assert result["command"] == long_command
        
        # Test with command containing special characters
        special_command = "echo 'Hello \"World\"! & echo $HOME | grep user'"
        params = {
            "connection_id": "12345678-1234-1234-1234-123456789012",
            "command": special_command
        }
        
        result = validate_tool_parameters("ssh_execute", params)
        assert result["command"] == special_command


if __name__ == "__main__":
    pytest.main([__file__])