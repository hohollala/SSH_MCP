"""Integration tests for SSH reconnection functionality."""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch

from ssh_mcp_server.connection import SSHConnection, ConnectionError
from ssh_mcp_server.manager import SSHManager
from ssh_mcp_server.models import SSHConfig, ConnectionInfo, CommandResult


@pytest.fixture
def ssh_config():
    """Create a test SSH configuration."""
    return SSHConfig(
        hostname="test.example.com",
        username="testuser",
        auth_method="password",
        password="testpass",
        timeout=10
    )


class TestReconnectionIntegration:
    """Integration tests for reconnection functionality."""
    
    @pytest.mark.asyncio
    async def test_connection_loss_detection_and_recovery(self, ssh_config):
        """Test that connection loss is detected and recovery is attempted."""
        connection_info = ConnectionInfo.create(
            hostname=ssh_config.hostname,
            username=ssh_config.username,
            port=ssh_config.port
        )
        
        connection = SSHConnection(ssh_config, connection_info)
        
        # Mock the SSH client and authentication
        with patch('ssh_mcp_server.connection.SSHClient') as mock_ssh_client_class:
            with patch.object(connection.auth_handler, 'authenticate') as mock_auth:
                mock_client = Mock()
                mock_ssh_client_class.return_value = mock_client
                mock_auth.return_value = None
                
                # Initial connection
                await connection.connect()
                assert connection.connected is True
                
                # Simulate connection loss by making transport inactive
                mock_transport = Mock()
                mock_transport.is_active.return_value = False
                mock_client.get_transport.return_value = mock_transport
                
                # Detect connection loss
                is_lost = await connection.detect_connection_loss()
                assert is_lost is True
                assert connection.is_connection_lost is True
                
                # Mock successful reconnection
                mock_transport.is_active.return_value = True
                connection._connected = False  # Simulate disconnected state
                
                # Force reconnection
                with patch.object(connection, 'connect') as mock_connect:
                    def mock_connect_side_effect():
                        connection._connected = True
                        return None
                    mock_connect.side_effect = mock_connect_side_effect
                    
                    success = await connection.force_reconnect()
                    assert success is True
                    assert connection.connected is True
                    assert connection.is_connection_lost is False
    
    @pytest.mark.asyncio
    async def test_manager_reconnection_monitoring(self, ssh_config):
        """Test that the manager properly monitors and handles reconnections."""
        manager = SSHManager(health_check_interval=1)  # Fast health checks for testing
        await manager.start()
        
        try:
            # Create a connection with mocked SSH client
            with patch('ssh_mcp_server.connection.SSHClient') as mock_ssh_client_class:
                with patch('ssh_mcp_server.auth.AuthenticationHandler.authenticate') as mock_auth:
                    mock_client = Mock()
                    mock_ssh_client_class.return_value = mock_client
                    mock_auth.return_value = None
                    
                    # Mock transport as active initially
                    mock_transport = Mock()
                    mock_transport.is_active.return_value = True
                    mock_client.get_transport.return_value = mock_transport
                    
                    # Create connection
                    connection_id = await manager.create_connection(ssh_config)
                    assert connection_id in manager.connections
                    
                    connection = manager.connections[connection_id]
                    assert connection.connected is True
                    assert connection.auto_reconnect is True
                    
                    # Get initial status
                    status = await manager.get_connection_status(connection_id)
                    assert status is not None
                    assert status["connected"] is True
                    assert status["auto_reconnect"] is True
                    assert status["is_connection_lost"] is False
                    
                    # Simulate connection loss
                    mock_transport.is_active.return_value = False
                    connection._connected = False
                    connection._connection_lost_at = asyncio.get_event_loop().time()
                    
                    # Monitor connections
                    statuses = await manager.monitor_connections()
                    assert connection_id in statuses
                    
                    # Test enabling/disabling auto-reconnect
                    result = await manager.disable_auto_reconnect(connection_id)
                    assert result is True
                    assert connection.auto_reconnect is False
                    
                    result = await manager.enable_auto_reconnect(connection_id)
                    assert result is True
                    assert connection.auto_reconnect is True
                    
        finally:
            await manager.stop()
    
    @pytest.mark.asyncio
    async def test_command_execution_with_automatic_reconnection(self, ssh_config):
        """Test that command execution automatically handles reconnection."""
        connection_info = ConnectionInfo.create(
            hostname=ssh_config.hostname,
            username=ssh_config.username,
            port=ssh_config.port
        )
        
        connection = SSHConnection(ssh_config, connection_info)
        
        with patch('ssh_mcp_server.connection.SSHClient') as mock_ssh_client_class:
            with patch.object(connection.auth_handler, 'authenticate') as mock_auth:
                mock_client = Mock()
                mock_ssh_client_class.return_value = mock_client
                mock_auth.return_value = None
                
                # Initial connection
                await connection.connect()
                assert connection.connected is True
                
                # Simulate connection being lost
                connection._connected = False
                connection._connection_lost_at = asyncio.get_event_loop().time()
                
                # Mock successful reconnection and command execution
                def mock_connect_side_effect():
                    connection._connected = True
                    connection._connection_lost_at = None
                    return None
                
                # Mock command execution
                mock_stdin = Mock()
                mock_stdout = Mock()
                mock_stderr = Mock()
                mock_stdout.read.return_value = b"test output"
                mock_stderr.read.return_value = b""
                mock_stdout.channel.recv_exit_status.return_value = 0
                mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)
                
                with patch.object(connection, 'connect', side_effect=mock_connect_side_effect):
                    with patch.object(connection, 'detect_connection_loss', return_value=False):
                        # Execute command - should trigger reconnection
                        result = await connection.execute_command("echo test")
                        
                        assert result.stdout == "test output"
                        assert result.exit_code == 0
                        assert connection.connected is True
                        assert connection.is_connection_lost is False
    
    @pytest.mark.asyncio
    async def test_health_check_triggers_reconnection(self, ssh_config):
        """Test that health check failures trigger reconnection attempts."""
        connection_info = ConnectionInfo.create(
            hostname=ssh_config.hostname,
            username=ssh_config.username,
            port=ssh_config.port
        )
        
        connection = SSHConnection(ssh_config, connection_info)
        
        with patch('ssh_mcp_server.connection.SSHClient') as mock_ssh_client_class:
            with patch.object(connection.auth_handler, 'authenticate') as mock_auth:
                mock_client = Mock()
                mock_ssh_client_class.return_value = mock_client
                mock_auth.return_value = None
                
                # Initial connection
                await connection.connect()
                assert connection.connected is True
                
                # Mock health check command to fail multiple times
                with patch.object(connection, 'execute_command') as mock_execute:
                    # First few calls fail (simulating connection issues)
                    mock_execute.side_effect = [
                        ConnectionError("Connection lost"),
                        ConnectionError("Connection lost"),
                        ConnectionError("Connection lost"),
                    ]
                    
                    # Perform health checks that will fail
                    for i in range(3):
                        result = await connection.health_check()
                        assert result is False
                    
                    # Should have triggered connection failure handling
                    assert connection._health_check_failures >= 3
                    assert connection.is_connection_lost is True
                    
                    # Mock successful reconnection
                    def mock_connect_side_effect():
                        connection._connected = True
                        connection._connection_lost_at = None
                        connection._health_check_failures = 0
                        return None
                    
                    # Mock successful health check after reconnection
                    mock_execute.side_effect = None
                    mock_execute.return_value = CommandResult(
                        stdout="health_check",
                        stderr="",
                        exit_code=0,
                        execution_time=0.1
                    )
                    
                    with patch.object(connection, 'connect', side_effect=mock_connect_side_effect):
                        # Health check should now succeed and clear the lost state
                        result = await connection.health_check()
                        assert result is True
                        assert connection.is_connection_lost is False
                        assert connection._health_check_failures == 0