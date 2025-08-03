"""Comprehensive integration tests for SSH authentication methods.

This module tests all supported authentication methods with various
scenarios including edge cases and error conditions.
"""

import asyncio
import json
import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock, mock_open
from datetime import datetime

from ssh_mcp_server.server import MCPServer
from ssh_mcp_server.models import SSHConfig, ConnectionInfo
from ssh_mcp_server.manager import SSHManager, SSHManagerError
from ssh_mcp_server.auth import AuthenticationHandler, AuthenticationError
from ssh_mcp_server.connection import SSHConnection, ConnectionError


class TestKeyAuthenticationIntegration:
    """Integration tests for SSH key authentication."""
    
    @pytest.fixture
    def server(self):
        """Create MCP server for testing."""
        return MCPServer(max_connections=5, debug=True)
    
    @pytest.fixture
    def temp_key_file(self):
        """Create a temporary SSH key file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False) as f:
            f.write("""-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAFwAAAAdzc2gtcn
NhAAAAAwEAAQAAAQEA1234567890abcdef...
-----END OPENSSH PRIVATE KEY-----""")
            key_path = f.name
        
        yield key_path
        
        # Cleanup
        os.unlink(key_path)
    
    @pytest.mark.asyncio
    async def test_key_auth_with_valid_key_file(self, server, temp_key_file):
        """Test SSH key authentication with valid key file."""
        # Mock connection info
        mock_connection_info = ConnectionInfo.create("key-test.com", "keyuser", 22)
        mock_connection_info.connection_id = "key-conn-123"
        mock_connection_info.connected = True
        
        # Mock SSH manager
        server.ssh_manager.create_connection = AsyncMock(return_value="key-conn-123")
        server.ssh_manager.list_connections = AsyncMock(return_value=[mock_connection_info])
        
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "key-test.com",
                    "username": "keyuser",
                    "auth_method": "key",
                    "key_path": temp_key_file,
                    "port": 22,
                    "timeout": 30
                }
            },
            "id": "key-auth-1"
        }
        
        response = await server.handle_request(request)
        
        # Verify successful connection
        assert "result" in response
        content = json.loads(response["result"]["content"][0]["text"])
        assert content["success"] is True
        assert content["data"]["connection_id"] == "key-conn-123"
        
        # Verify SSH manager was called with correct config
        call_args = server.ssh_manager.create_connection.call_args[0][0]
        assert call_args.auth_method == "key"
        assert call_args.key_path == temp_key_file
    
    @pytest.mark.asyncio
    async def test_key_auth_with_nonexistent_key_file(self, server):
        """Test SSH key authentication with non-existent key file."""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "key-test.com",
                    "username": "keyuser",
                    "auth_method": "key",
                    "key_path": "/nonexistent/key/path.pem"
                }
            },
            "id": "key-auth-2"
        }
        
        response = await server.handle_request(request)
        
        # Should return validation error
        assert "error" in response
        assert "Key file does not exist" in response["error"]["message"]
        assert response["error"]["code"] == -32000  # TOOL_ERROR
    
    @pytest.mark.asyncio
    async def test_key_auth_with_encrypted_key(self, server):
        """Test SSH key authentication with encrypted key file."""
        # Create encrypted key file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False) as f:
            f.write("""-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAACmFlczI1Ni1jdHIAAAAGYmNyeXB0AAAAGAAAABCQ1234...
-----END OPENSSH PRIVATE KEY-----""")
            encrypted_key_path = f.name
        
        try:
            # Mock SSH manager to simulate encrypted key handling
            server.ssh_manager.create_connection = AsyncMock(
                side_effect=SSHManagerError(
                    "Private key is encrypted and requires passphrase",
                    details="Key authentication failed"
                )
            )
            
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_connect",
                    "arguments": {
                        "hostname": "encrypted-key.com",
                        "username": "user",
                        "auth_method": "key",
                        "key_path": encrypted_key_path
                    }
                },
                "id": "key-auth-3"
            }
            
            response = await server.handle_request(request)
            
            # Should return authentication error
            assert "error" in response
            assert "SSH connection failed" in response["error"]["message"]
            assert "Private key is encrypted" in response["error"]["message"]
            
        finally:
            os.unlink(encrypted_key_path)
    
    @pytest.mark.asyncio
    async def test_key_auth_with_invalid_key_format(self, server):
        """Test SSH key authentication with invalid key file format."""
        # Create invalid key file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False) as f:
            f.write("This is not a valid SSH key file\nInvalid content")
            invalid_key_path = f.name
        
        try:
            # Mock SSH manager to simulate invalid key format
            server.ssh_manager.create_connection = AsyncMock(
                side_effect=SSHManagerError(
                    "Invalid key file format",
                    details="Could not parse private key"
                )
            )
            
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_connect",
                    "arguments": {
                        "hostname": "invalid-key.com",
                        "username": "user",
                        "auth_method": "key",
                        "key_path": invalid_key_path
                    }
                },
                "id": "key-auth-4"
            }
            
            response = await server.handle_request(request)
            
            # Should return authentication error
            assert "error" in response
            assert "SSH connection failed" in response["error"]["message"]
            
        finally:
            os.unlink(invalid_key_path)
    
    @pytest.mark.asyncio
    async def test_key_auth_with_different_key_types(self, server):
        """Test SSH key authentication with different key types."""
        key_types = [
            ("rsa", "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA...\n-----END RSA PRIVATE KEY-----"),
            ("ed25519", "-----BEGIN OPENSSH PRIVATE KEY-----\nb3BlbnNzaC1rZXktdjE...\n-----END OPENSSH PRIVATE KEY-----"),
            ("ecdsa", "-----BEGIN EC PRIVATE KEY-----\nMHcCAQEEII...\n-----END EC PRIVATE KEY-----")
        ]
        
        for i, (key_type, key_content) in enumerate(key_types):
            with tempfile.NamedTemporaryFile(mode='w', suffix=f'_{key_type}.pem', delete=False) as f:
                f.write(key_content)
                key_path = f.name
            
            try:
                # Mock successful connection for each key type
                mock_connection_info = ConnectionInfo.create(f"{key_type}-test.com", "user", 22)
                mock_connection_info.connection_id = f"{key_type}-conn-{i}"
                
                server.ssh_manager.create_connection = AsyncMock(return_value=f"{key_type}-conn-{i}")
                server.ssh_manager.list_connections = AsyncMock(return_value=[mock_connection_info])
                
                request = {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "ssh_connect",
                        "arguments": {
                            "hostname": f"{key_type}-test.com",
                            "username": "user",
                            "auth_method": "key",
                            "key_path": key_path
                        }
                    },
                    "id": f"key-type-{i}"
                }
                
                response = await server.handle_request(request)
                
                # Verify successful connection
                assert "result" in response
                content = json.loads(response["result"]["content"][0]["text"])
                assert content["success"] is True
                assert content["data"]["connection_id"] == f"{key_type}-conn-{i}"
                
            finally:
                os.unlink(key_path)


class TestPasswordAuthenticationIntegration:
    """Integration tests for SSH password authentication."""
    
    @pytest.fixture
    def server(self):
        """Create MCP server for testing."""
        return MCPServer(max_connections=5, debug=True)
    
    @pytest.mark.asyncio
    async def test_password_auth_success(self, server):
        """Test successful password authentication."""
        # Mock connection info
        mock_connection_info = ConnectionInfo.create("pass-test.com", "passuser", 22)
        mock_connection_info.connection_id = "pass-conn-123"
        mock_connection_info.connected = True
        
        # Mock SSH manager
        server.ssh_manager.create_connection = AsyncMock(return_value="pass-conn-123")
        server.ssh_manager.list_connections = AsyncMock(return_value=[mock_connection_info])
        
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "pass-test.com",
                    "username": "passuser",
                    "auth_method": "password",
                    "password": "secure_password_123",
                    "port": 22,
                    "timeout": 30
                }
            },
            "id": "pass-auth-1"
        }
        
        response = await server.handle_request(request)
        
        # Verify successful connection
        assert "result" in response
        content = json.loads(response["result"]["content"][0]["text"])
        assert content["success"] is True
        assert content["data"]["connection_id"] == "pass-conn-123"
        
        # Verify SSH manager was called with correct config
        call_args = server.ssh_manager.create_connection.call_args[0][0]
        assert call_args.auth_method == "password"
        assert call_args.password == "secure_password_123"
    
    @pytest.mark.asyncio
    async def test_password_auth_failure(self, server):
        """Test password authentication failure."""
        # Mock SSH manager to simulate authentication failure
        server.ssh_manager.create_connection = AsyncMock(
            side_effect=SSHManagerError(
                "Authentication failed for passuser@wrong-pass.com",
                details="Invalid password"
            )
        )
        
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "wrong-pass.com",
                    "username": "passuser",
                    "auth_method": "password",
                    "password": "wrong_password"
                }
            },
            "id": "pass-auth-2"
        }
        
        response = await server.handle_request(request)
        
        # Should return authentication error
        assert "error" in response
        assert "SSH connection failed" in response["error"]["message"]
        assert "Authentication failed" in response["error"]["message"]
    
    @pytest.mark.asyncio
    async def test_password_auth_with_special_characters(self, server):
        """Test password authentication with special characters."""
        special_passwords = [
            "p@ssw0rd!",
            "пароль123",  # Cyrillic characters
            "密码123",     # Chinese characters
            "pass word with spaces",
            "pass\"with'quotes",
            "pass\\with\\backslashes",
            "pass$with$dollars",
            "pass&with&ampersands"
        ]
        
        for i, password in enumerate(special_passwords):
            # Mock connection info
            mock_connection_info = ConnectionInfo.create("special-pass.com", "user", 22)
            mock_connection_info.connection_id = f"special-conn-{i}"
            
            server.ssh_manager.create_connection = AsyncMock(return_value=f"special-conn-{i}")
            server.ssh_manager.list_connections = AsyncMock(return_value=[mock_connection_info])
            
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_connect",
                    "arguments": {
                        "hostname": "special-pass.com",
                        "username": "user",
                        "auth_method": "password",
                        "password": password
                    }
                },
                "id": f"special-pass-{i}"
            }
            
            response = await server.handle_request(request)
            
            # Verify successful connection
            assert "result" in response
            content = json.loads(response["result"]["content"][0]["text"])
            assert content["success"] is True
            
            # Verify password was passed correctly
            call_args = server.ssh_manager.create_connection.call_args[0][0]
            assert call_args.password == password
    
    @pytest.mark.asyncio
    async def test_password_auth_missing_password(self, server):
        """Test password authentication with missing password parameter."""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "missing-pass.com",
                    "username": "user",
                    "auth_method": "password"
                    # Missing password parameter
                }
            },
            "id": "missing-pass"
        }
        
        response = await server.handle_request(request)
        
        # Should return validation error
        assert "error" in response
        assert "Password is required for password authentication" in response["error"]["message"]
        assert response["error"]["code"] == -32000  # TOOL_ERROR


class TestAgentAuthenticationIntegration:
    """Integration tests for SSH agent authentication."""
    
    @pytest.fixture
    def server(self):
        """Create MCP server for testing."""
        return MCPServer(max_connections=5, debug=True)
    
    @pytest.mark.asyncio
    async def test_agent_auth_success(self, server):
        """Test successful SSH agent authentication."""
        # Mock connection info
        mock_connection_info = ConnectionInfo.create("agent-test.com", "agentuser", 22)
        mock_connection_info.connection_id = "agent-conn-123"
        mock_connection_info.connected = True
        
        # Mock SSH manager
        server.ssh_manager.create_connection = AsyncMock(return_value="agent-conn-123")
        server.ssh_manager.list_connections = AsyncMock(return_value=[mock_connection_info])
        
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "agent-test.com",
                    "username": "agentuser",
                    "auth_method": "agent"
                }
            },
            "id": "agent-auth-1"
        }
        
        # Mock SSH agent environment
        with patch('os.environ.get', return_value='/tmp/ssh_auth_sock'):
            with patch('os.path.exists', return_value=True):
                with patch('paramiko.Agent') as mock_agent:
                    # Mock agent with available keys
                    mock_agent_instance = Mock()
                    mock_key = Mock()
                    mock_key.get_name.return_value = b'ssh-rsa'
                    mock_agent_instance.get_keys.return_value = [mock_key]
                    mock_agent.return_value = mock_agent_instance
                    
                    response = await server.handle_request(request)
                    
                    # Verify successful connection
                    assert "result" in response
                    content = json.loads(response["result"]["content"][0]["text"])
                    assert content["success"] is True
                    assert content["data"]["connection_id"] == "agent-conn-123"
                    
                    # Verify SSH manager was called with correct config
                    call_args = server.ssh_manager.create_connection.call_args[0][0]
                    assert call_args.auth_method == "agent"
    
    @pytest.mark.asyncio
    async def test_agent_auth_no_agent_running(self, server):
        """Test SSH agent authentication when no agent is running."""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "no-agent.com",
                    "username": "user",
                    "auth_method": "agent"
                }
            },
            "id": "no-agent"
        }
        
        # Mock no SSH agent environment
        with patch('os.environ.get', return_value=None):
            response = await server.handle_request(request)
            
            # Should return validation error
            assert "error" in response
            assert "SSH agent not available" in response["error"]["message"]
            assert response["error"]["code"] == -32000  # TOOL_ERROR
    
    @pytest.mark.asyncio
    async def test_agent_auth_agent_socket_not_accessible(self, server):
        """Test SSH agent authentication when agent socket is not accessible."""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "inaccessible-agent.com",
                    "username": "user",
                    "auth_method": "agent"
                }
            },
            "id": "inaccessible-agent"
        }
        
        # Mock SSH agent environment but socket doesn't exist
        with patch('os.environ.get', return_value='/tmp/nonexistent_ssh_auth_sock'):
            with patch('os.path.exists', return_value=False):
                response = await server.handle_request(request)
                
                # Should return validation error
                assert "error" in response
                assert "SSH agent socket not accessible" in response["error"]["message"]
                assert response["error"]["code"] == -32000  # TOOL_ERROR
    
    @pytest.mark.asyncio
    async def test_agent_auth_no_keys_in_agent(self, server):
        """Test SSH agent authentication when agent has no keys."""
        # Mock SSH manager to simulate no keys available
        server.ssh_manager.create_connection = AsyncMock(
            side_effect=SSHManagerError(
                "No suitable keys found in SSH agent",
                details="Agent authentication failed"
            )
        )
        
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "no-keys.com",
                    "username": "user",
                    "auth_method": "agent"
                }
            },
            "id": "no-keys"
        }
        
        # Mock SSH agent environment with no keys
        with patch('os.environ.get', return_value='/tmp/ssh_auth_sock'):
            with patch('os.path.exists', return_value=True):
                with patch('paramiko.Agent') as mock_agent:
                    mock_agent_instance = Mock()
                    mock_agent_instance.get_keys.return_value = []  # No keys
                    mock_agent.return_value = mock_agent_instance
                    
                    response = await server.handle_request(request)
                    
                    # Should return authentication error
                    assert "error" in response
                    assert "SSH connection failed" in response["error"]["message"]
    
    @pytest.mark.asyncio
    async def test_agent_auth_with_multiple_keys(self, server):
        """Test SSH agent authentication with multiple keys available."""
        # Mock connection info
        mock_connection_info = ConnectionInfo.create("multi-keys.com", "user", 22)
        mock_connection_info.connection_id = "multi-keys-conn"
        
        server.ssh_manager.create_connection = AsyncMock(return_value="multi-keys-conn")
        server.ssh_manager.list_connections = AsyncMock(return_value=[mock_connection_info])
        
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "multi-keys.com",
                    "username": "user",
                    "auth_method": "agent"
                }
            },
            "id": "multi-keys"
        }
        
        # Mock SSH agent with multiple keys
        with patch('os.environ.get', return_value='/tmp/ssh_auth_sock'):
            with patch('os.path.exists', return_value=True):
                with patch('paramiko.Agent') as mock_agent:
                    mock_agent_instance = Mock()
                    
                    # Create multiple mock keys
                    mock_keys = []
                    for key_type in ['ssh-rsa', 'ssh-ed25519', 'ecdsa-sha2-nistp256']:
                        mock_key = Mock()
                        mock_key.get_name.return_value = key_type.encode()
                        mock_keys.append(mock_key)
                    
                    mock_agent_instance.get_keys.return_value = mock_keys
                    mock_agent.return_value = mock_agent_instance
                    
                    response = await server.handle_request(request)
                    
                    # Verify successful connection
                    assert "result" in response
                    content = json.loads(response["result"]["content"][0]["text"])
                    assert content["success"] is True


class TestMixedAuthenticationScenarios:
    """Integration tests for mixed authentication scenarios."""
    
    @pytest.fixture
    def server(self):
        """Create MCP server for testing."""
        return MCPServer(max_connections=10, debug=True)
    
    @pytest.mark.asyncio
    async def test_fallback_authentication_methods(self, server):
        """Test fallback between different authentication methods."""
        # Scenario: Try key auth first, then fallback to password
        scenarios = [
            {
                "attempt": 1,
                "auth_method": "key",
                "key_path": "/nonexistent/key.pem",
                "should_fail": True,
                "error_message": "Key file does not exist"
            },
            {
                "attempt": 2,
                "auth_method": "password",
                "password": "fallback_password",
                "should_fail": False,
                "connection_id": "fallback-conn-123"
            }
        ]
        
        for scenario in scenarios:
            if scenario["should_fail"]:
                # First attempt should fail
                request = {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "ssh_connect",
                        "arguments": {
                            "hostname": "fallback-test.com",
                            "username": "user",
                            "auth_method": scenario["auth_method"],
                            "key_path": scenario.get("key_path")
                        }
                    },
                    "id": f"fallback-{scenario['attempt']}"
                }
                
                response = await server.handle_request(request)
                assert "error" in response
                assert scenario["error_message"] in response["error"]["message"]
                
            else:
                # Second attempt should succeed
                mock_connection_info = ConnectionInfo.create("fallback-test.com", "user", 22)
                mock_connection_info.connection_id = scenario["connection_id"]
                
                server.ssh_manager.create_connection = AsyncMock(return_value=scenario["connection_id"])
                server.ssh_manager.list_connections = AsyncMock(return_value=[mock_connection_info])
                
                request = {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "ssh_connect",
                        "arguments": {
                            "hostname": "fallback-test.com",
                            "username": "user",
                            "auth_method": scenario["auth_method"],
                            "password": scenario.get("password")
                        }
                    },
                    "id": f"fallback-{scenario['attempt']}"
                }
                
                response = await server.handle_request(request)
                assert "result" in response
                content = json.loads(response["result"]["content"][0]["text"])
                assert content["success"] is True
    
    @pytest.mark.asyncio
    async def test_concurrent_different_auth_methods(self, server):
        """Test concurrent connections using different authentication methods."""
        # Setup different authentication scenarios
        auth_scenarios = [
            {
                "hostname": "key-server.com",
                "username": "keyuser",
                "auth_method": "key",
                "key_path": "/tmp/test_key.pem",
                "connection_id": "concurrent-key-conn"
            },
            {
                "hostname": "pass-server.com",
                "username": "passuser",
                "auth_method": "password",
                "password": "concurrent_pass",
                "connection_id": "concurrent-pass-conn"
            },
            {
                "hostname": "agent-server.com",
                "username": "agentuser",
                "auth_method": "agent",
                "connection_id": "concurrent-agent-conn"
            }
        ]
        
        # Mock connection infos
        connection_infos = []
        for scenario in auth_scenarios:
            conn_info = ConnectionInfo.create(scenario["hostname"], scenario["username"], 22)
            conn_info.connection_id = scenario["connection_id"]
            connection_infos.append(conn_info)
        
        # Mock SSH manager for concurrent connections
        call_count = 0
        async def mock_create_connection(config):
            nonlocal call_count
            result = auth_scenarios[call_count]["connection_id"]
            call_count += 1
            return result
        
        server.ssh_manager.create_connection = AsyncMock(side_effect=mock_create_connection)
        server.ssh_manager.list_connections = AsyncMock(return_value=connection_infos)
        
        # Create requests for each auth method
        requests = []
        for i, scenario in enumerate(auth_scenarios):
            args = {
                "hostname": scenario["hostname"],
                "username": scenario["username"],
                "auth_method": scenario["auth_method"]
            }
            
            if "key_path" in scenario:
                args["key_path"] = scenario["key_path"]
            if "password" in scenario:
                args["password"] = scenario["password"]
            
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_connect",
                    "arguments": args
                },
                "id": f"concurrent-auth-{i}"
            }
            requests.append(request)
        
        # Execute all requests concurrently with appropriate mocking
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
        for i, response in enumerate(responses):
            assert "result" in response
            content = json.loads(response["result"]["content"][0]["text"])
            assert content["success"] is True
            assert content["data"]["connection_id"] == auth_scenarios[i]["connection_id"]
        
        # Verify SSH manager was called for each connection
        assert server.ssh_manager.create_connection.call_count == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])