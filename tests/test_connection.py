"""Tests for SSH connection management."""

import asyncio
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
import paramiko

from ssh_mcp_server.connection import SSHConnection, ConnectionError
from ssh_mcp_server.models import SSHConfig, ConnectionInfo, CommandResult
from ssh_mcp_server.auth import AuthenticationError


class TestSSHConnection:
    """Test cases for SSHConnection class."""
    
    @pytest.fixture
    def ssh_config(self):
        """Create a test SSH configuration."""
        return SSHConfig(
            hostname="test.example.com",
            username="testuser",
            port=22,
            auth_method="agent",  # Use agent auth to avoid key file validation
            timeout=30
        )
    
    @pytest.fixture
    def connection_info(self):
        """Create test connection info."""
        return ConnectionInfo.create(
            hostname="test.example.com",
            username="testuser",
            port=22
        )
    
    @pytest.fixture
    def ssh_connection(self, ssh_config, connection_info):
        """Create a test SSH connection."""
        return SSHConnection(ssh_config, connection_info)
    
    def test_init(self, ssh_connection, ssh_config, connection_info):
        """Test SSH connection initialization."""
        assert ssh_connection.config == ssh_config
        assert ssh_connection.connection_info == connection_info
        assert ssh_connection.client is None
        assert not ssh_connection.connected
        assert ssh_connection.connection_id == connection_info.connection_id
    
    def test_properties(self, ssh_connection):
        """Test SSH connection properties."""
        # Initially not connected
        assert not ssh_connection.connected
        assert ssh_connection.connection_duration is None
        assert isinstance(ssh_connection.last_activity, datetime)
        
        # Mock connection state
        ssh_connection._connected = True
        ssh_connection.client = Mock()
        ssh_connection._connection_start_time = datetime.now() - timedelta(minutes=5)
        
        assert ssh_connection.connected
        assert isinstance(ssh_connection.connection_duration, timedelta)
    
    @pytest.mark.asyncio
    async def test_connect_success(self, ssh_connection):
        """Test successful SSH connection."""
        mock_client = Mock(spec=paramiko.SSHClient)
        
        with patch('ssh_mcp_server.connection.SSHClient', return_value=mock_client), \
             patch.object(ssh_connection.auth_handler, 'authenticate') as mock_auth:
            
            await ssh_connection.connect()
            
            # Verify client setup
            mock_client.set_missing_host_key_policy.assert_called_once()
            mock_auth.assert_called_once_with(mock_client, ssh_connection.config)
            
            # Verify connection state
            assert ssh_connection.connected
            assert ssh_connection.client == mock_client
            assert ssh_connection.connection_info.connected
            assert ssh_connection._connection_start_time is not None
    
    @pytest.mark.asyncio
    async def test_connect_already_connected(self, ssh_connection):
        """Test connecting when already connected."""
        ssh_connection._connected = True
        ssh_connection.client = Mock()
        
        with patch('ssh_mcp_server.connection.SSHClient') as mock_ssh_client:
            await ssh_connection.connect()
            
            # Should not create new client
            mock_ssh_client.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_connect_authentication_error(self, ssh_connection):
        """Test connection failure due to authentication error."""
        mock_client = Mock(spec=paramiko.SSHClient)
        auth_error = AuthenticationError("Auth failed", "key")
        
        with patch('ssh_mcp_server.connection.SSHClient', return_value=mock_client), \
             patch.object(ssh_connection.auth_handler, 'authenticate', side_effect=auth_error):
            
            with pytest.raises(ConnectionError) as exc_info:
                await ssh_connection.connect()
            
            assert "Authentication failed" in str(exc_info.value)
            assert exc_info.value.connection_id == ssh_connection.connection_id
            assert not ssh_connection.connected
            assert ssh_connection.client is None
    
    @pytest.mark.asyncio
    async def test_connect_ssh_exception(self, ssh_connection):
        """Test connection failure due to SSH exception."""
        mock_client = Mock(spec=paramiko.SSHClient)
        ssh_error = paramiko.SSHException("Connection failed")
        
        with patch('ssh_mcp_server.connection.SSHClient', return_value=mock_client), \
             patch.object(ssh_connection.auth_handler, 'authenticate', side_effect=ssh_error):
            
            with pytest.raises(ConnectionError) as exc_info:
                await ssh_connection.connect()
            
            assert "Failed to connect" in str(exc_info.value)
            assert not ssh_connection.connected
    
    @pytest.mark.asyncio
    async def test_disconnect(self, ssh_connection):
        """Test SSH disconnection."""
        # Setup connected state
        mock_client = Mock()
        ssh_connection.client = mock_client
        ssh_connection._connected = True
        ssh_connection._connection_start_time = datetime.now()
        ssh_connection.connection_info.connected = True
        
        await ssh_connection.disconnect()
        
        # Verify cleanup
        mock_client.close.assert_called_once()
        assert not ssh_connection.connected
        assert ssh_connection.client is None
        assert not ssh_connection.connection_info.connected
        assert ssh_connection._connection_start_time is None
    
    @pytest.mark.asyncio
    async def test_disconnect_with_error(self, ssh_connection):
        """Test disconnection when client close fails."""
        mock_client = Mock()
        mock_client.close.side_effect = Exception("Close failed")
        ssh_connection.client = mock_client
        ssh_connection._connected = True
        ssh_connection.connection_info.connected = True
        
        await ssh_connection.disconnect()
        
        # Should still mark as disconnected despite error
        assert not ssh_connection.connected
        assert ssh_connection.client is None
        assert not ssh_connection.connection_info.connected
    
    @pytest.mark.asyncio
    async def test_execute_command_success(self, ssh_connection):
        """Test successful command execution."""
        # Setup connected state
        mock_client = Mock()
        mock_stdin = Mock()
        mock_stdout = Mock()
        mock_stderr = Mock()
        mock_channel = Mock()
        
        mock_stdout.read.return_value = b"command output"
        mock_stderr.read.return_value = b"error output"
        mock_stdout.channel = mock_channel
        mock_channel.recv_exit_status.return_value = 0
        
        mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)
        
        ssh_connection.client = mock_client
        ssh_connection._connected = True
        
        result = await ssh_connection.execute_command("ls -la")
        
        # Verify command execution
        mock_client.exec_command.assert_called_once_with("ls -la", timeout=30)
        
        # Verify result
        assert isinstance(result, CommandResult)
        assert result.stdout == "command output"
        assert result.stderr == "error output"
        assert result.exit_code == 0
        assert result.command == "ls -la"
        assert result.execution_time > 0
    
    @pytest.mark.asyncio
    async def test_execute_command_not_connected(self, ssh_connection):
        """Test command execution when not connected."""
        with pytest.raises(ConnectionError) as exc_info:
            await ssh_connection.execute_command("ls")
        
        assert "Connection not established" in str(exc_info.value)
        assert exc_info.value.connection_id == ssh_connection.connection_id
    
    @pytest.mark.asyncio
    async def test_execute_command_empty(self, ssh_connection):
        """Test command execution with empty command."""
        ssh_connection._connected = True
        ssh_connection.client = Mock()
        
        with pytest.raises(ConnectionError) as exc_info:
            await ssh_connection.execute_command("")
        
        assert "Command cannot be empty" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_execute_command_ssh_exception(self, ssh_connection):
        """Test command execution with SSH exception."""
        mock_client = Mock()
        mock_client.exec_command.side_effect = paramiko.SSHException("Exec failed")
        
        ssh_connection.client = mock_client
        ssh_connection._connected = True
        
        with pytest.raises(ConnectionError) as exc_info:
            await ssh_connection.execute_command("ls")
        
        assert "SSH error executing command" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_execute_command_with_timeout(self, ssh_connection):
        """Test command execution with custom timeout."""
        mock_client = Mock()
        mock_stdin = Mock()
        mock_stdout = Mock()
        mock_stderr = Mock()
        mock_channel = Mock()
        
        mock_stdout.read.return_value = b"output"
        mock_stderr.read.return_value = b""
        mock_stdout.channel = mock_channel
        mock_channel.recv_exit_status.return_value = 0
        
        mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)
        
        ssh_connection.client = mock_client
        ssh_connection._connected = True
        
        await ssh_connection.execute_command("sleep 1", timeout=60)
        
        mock_client.exec_command.assert_called_once_with("sleep 1", timeout=60)
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, ssh_connection):
        """Test successful health check."""
        # Mock execute_command to return successful health check
        async def mock_execute(cmd, timeout=None):
            return CommandResult(
                stdout="health_check\n",
                stderr="",
                exit_code=0,
                execution_time=0.1,
                command=cmd
            )
        
        ssh_connection._connected = True
        ssh_connection.client = Mock()
        
        with patch.object(ssh_connection, 'execute_command', side_effect=mock_execute):
            result = await ssh_connection.health_check()
        
        assert result is True
        assert ssh_connection._health_check_failures == 0
        assert ssh_connection._last_health_check is not None
    
    @pytest.mark.asyncio
    async def test_health_check_not_connected(self, ssh_connection):
        """Test health check when not connected."""
        result = await ssh_connection.health_check()
        assert result is False
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, ssh_connection):
        """Test health check failure."""
        ssh_connection._connected = True
        ssh_connection.client = Mock()
        
        with patch.object(ssh_connection, 'execute_command', side_effect=ConnectionError("Failed")):
            result = await ssh_connection.health_check()
        
        assert result is False
        assert ssh_connection._health_check_failures == 1
    
    @pytest.mark.asyncio
    async def test_health_check_max_failures(self, ssh_connection):
        """Test health check with maximum failures reached."""
        ssh_connection._connected = True
        ssh_connection.client = Mock()
        ssh_connection._health_check_failures = ssh_connection._max_health_check_failures - 1
        
        with patch.object(ssh_connection, 'execute_command', side_effect=ConnectionError("Failed")):
            result = await ssh_connection.health_check()
        
        assert result is False
        assert not ssh_connection._connected
        assert not ssh_connection.connection_info.connected
    
    @pytest.mark.asyncio
    async def test_is_health_check_needed(self, ssh_connection):
        """Test health check timing logic."""
        # Not connected - no health check needed
        assert not await ssh_connection.is_health_check_needed()
        
        # Connected but no previous check - health check needed
        ssh_connection._connected = True
        ssh_connection.client = Mock()  # Need client to be considered connected
        assert await ssh_connection.is_health_check_needed()
        
        # Recent health check - not needed
        ssh_connection._last_health_check = datetime.now()
        assert not await ssh_connection.is_health_check_needed()
        
        # Old health check - needed
        ssh_connection._last_health_check = datetime.now() - timedelta(seconds=60)
        assert await ssh_connection.is_health_check_needed()
    
    @pytest.mark.asyncio
    async def test_get_connection_stats(self, ssh_connection):
        """Test connection statistics retrieval."""
        stats = await ssh_connection.get_connection_stats()
        
        assert stats["connection_id"] == ssh_connection.connection_id
        assert stats["hostname"] == "test.example.com"
        assert stats["username"] == "testuser"
        assert stats["port"] == 22
        assert stats["connected"] is False
        assert stats["auth_method"] == "agent"
        assert "created_at" in stats
        assert "last_used" in stats
        assert "last_activity" in stats
        assert stats["health_check_failures"] == 0
        assert stats["connection_duration"] is None
        
        # Test with connection duration
        ssh_connection._connection_start_time = datetime.now() - timedelta(minutes=5)
        stats = await ssh_connection.get_connection_stats()
        assert stats["connection_duration"] is not None
        
        # Test with health check timestamp
        ssh_connection._last_health_check = datetime.now()
        stats = await ssh_connection.get_connection_stats()
        assert "last_health_check" in stats
    
    def test_string_representations(self, ssh_connection):
        """Test string representations of connection."""
        str_repr = str(ssh_connection)
        assert "testuser@test.example.com:22" in str_repr
        assert "disconnected" in str_repr
        
        repr_str = repr(ssh_connection)
        assert "SSHConnection" in repr_str
        assert ssh_connection.connection_id[:8] in repr_str
        assert "test.example.com" in repr_str
        assert "testuser" in repr_str
    
    @pytest.mark.asyncio
    async def test_cleanup_client(self, ssh_connection):
        """Test client cleanup method."""
        mock_client = Mock()
        ssh_connection.client = mock_client
        
        await ssh_connection._cleanup_client()
        
        mock_client.close.assert_called_once()
        assert ssh_connection.client is None
    
    @pytest.mark.asyncio
    async def test_cleanup_client_with_error(self, ssh_connection):
        """Test client cleanup with close error."""
        mock_client = Mock()
        mock_client.close.side_effect = Exception("Close failed")
        ssh_connection.client = mock_client
        
        await ssh_connection._cleanup_client()
        
        # Should still set client to None despite error
        assert ssh_connection.client is None


class TestConnectionError:
    """Test cases for ConnectionError exception."""
    
    def test_init_basic(self):
        """Test basic ConnectionError initialization."""
        error = ConnectionError("Test error")
        assert str(error) == "Test error"
        assert error.connection_id is None
        assert error.details is None
    
    def test_init_with_connection_id(self):
        """Test ConnectionError with connection ID."""
        error = ConnectionError("Test error", "conn-123")
        assert error.connection_id == "conn-123"
    
    def test_init_with_details(self):
        """Test ConnectionError with details."""
        error = ConnectionError("Test error", details="Additional info")
        assert error.details == "Additional info"
    
    def test_init_full(self):
        """Test ConnectionError with all parameters."""
        error = ConnectionError("Test error", "conn-123", "Additional info")
        assert str(error) == "Test error"
        assert error.connection_id == "conn-123"
        assert error.details == "Additional info"