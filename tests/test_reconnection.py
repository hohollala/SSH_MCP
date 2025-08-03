"""Tests for SSH connection reconnection and recovery functionality."""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

import paramiko
from paramiko import SSHException

from ssh_mcp_server.connection import SSHConnection, ConnectionError
from ssh_mcp_server.manager import SSHManager, SSHManagerError
from ssh_mcp_server.models import SSHConfig, ConnectionInfo


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


@pytest.fixture
def connection_info():
    """Create test connection info."""
    return ConnectionInfo.create(
        hostname="test.example.com",
        username="testuser",
        port=22
    )


@pytest.fixture
def mock_ssh_client():
    """Create a mock SSH client."""
    client = Mock(spec=paramiko.SSHClient)
    client.get_transport.return_value = Mock()
    client.get_transport.return_value.is_active.return_value = True
    return client


class TestSSHConnectionReconnection:
    """Test SSH connection reconnection functionality."""
    
    @pytest.mark.asyncio
    async def test_auto_reconnect_property(self, ssh_config, connection_info):
        """Test auto-reconnect property getter and setter."""
        connection = SSHConnection(ssh_config, connection_info)
        
        # Default should be True
        assert connection.auto_reconnect is True
        
        # Test setter
        connection.auto_reconnect = False
        assert connection.auto_reconnect is False
        
        connection.auto_reconnect = True
        assert connection.auto_reconnect is True
    
    @pytest.mark.asyncio
    async def test_reconnect_attempts_property(self, ssh_config, connection_info):
        """Test reconnect attempts property."""
        connection = SSHConnection(ssh_config, connection_info)
        
        # Default should be 0
        assert connection.reconnect_attempts == 0
        
        # Should increment after failed reconnection attempts
        connection._reconnect_attempts = 2
        assert connection.reconnect_attempts == 2
    
    @pytest.mark.asyncio
    async def test_is_connection_lost_property(self, ssh_config, connection_info):
        """Test connection lost property."""
        connection = SSHConnection(ssh_config, connection_info)
        
        # Default should be False
        assert connection.is_connection_lost is False
        
        # Should be True when connection_lost_at is set
        connection._connection_lost_at = datetime.now()
        assert connection.is_connection_lost is True
    
    @pytest.mark.asyncio
    async def test_detect_connection_loss_no_client(self, ssh_config, connection_info):
        """Test connection loss detection when client is None."""
        connection = SSHConnection(ssh_config, connection_info)
        connection.client = None
        
        result = await connection.detect_connection_loss()
        assert result is True
        assert connection.is_connection_lost is True
    
    @pytest.mark.asyncio
    async def test_detect_connection_loss_inactive_transport(self, ssh_config, connection_info, mock_ssh_client):
        """Test connection loss detection when transport is inactive."""
        connection = SSHConnection(ssh_config, connection_info)
        connection.client = mock_ssh_client
        
        # Mock inactive transport
        mock_ssh_client.get_transport.return_value.is_active.return_value = False
        
        result = await connection.detect_connection_loss()
        assert result is True
        assert connection.is_connection_lost is True
    
    @pytest.mark.asyncio
    async def test_detect_connection_loss_no_transport(self, ssh_config, connection_info, mock_ssh_client):
        """Test connection loss detection when transport is None."""
        connection = SSHConnection(ssh_config, connection_info)
        connection.client = mock_ssh_client
        
        # Mock no transport
        mock_ssh_client.get_transport.return_value = None
        
        result = await connection.detect_connection_loss()
        assert result is True
        assert connection.is_connection_lost is True
    
    @pytest.mark.asyncio
    async def test_detect_connection_loss_exception(self, ssh_config, connection_info, mock_ssh_client):
        """Test connection loss detection when exception occurs."""
        connection = SSHConnection(ssh_config, connection_info)
        connection.client = mock_ssh_client
        
        # Mock exception
        mock_ssh_client.get_transport.side_effect = Exception("Connection error")
        
        result = await connection.detect_connection_loss()
        assert result is True
        assert connection.is_connection_lost is True
    
    @pytest.mark.asyncio
    async def test_detect_connection_loss_healthy(self, ssh_config, connection_info, mock_ssh_client):
        """Test connection loss detection when connection is healthy."""
        connection = SSHConnection(ssh_config, connection_info)
        connection.client = mock_ssh_client
        
        # Mock healthy transport
        mock_ssh_client.get_transport.return_value.is_active.return_value = True
        
        result = await connection.detect_connection_loss()
        assert result is False
        assert connection.is_connection_lost is False
    
    @pytest.mark.asyncio
    async def test_handle_connection_failure(self, ssh_config, connection_info):
        """Test connection failure handling."""
        connection = SSHConnection(ssh_config, connection_info)
        connection._health_check_failures = 3  # Trigger failure threshold
        connection._max_health_check_failures = 3
        
        with patch.object(connection, '_attempt_reconnection', new_callable=AsyncMock) as mock_reconnect:
            await connection._handle_connection_failure()
            
            # Should mark connection as lost
            assert connection.is_connection_lost is True
            assert connection.connected is False
            assert connection.connection_info.connected is False
            
            # Should attempt reconnection
            mock_reconnect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_attempt_reconnection_disabled(self, ssh_config, connection_info):
        """Test reconnection attempt when auto-reconnect is disabled."""
        connection = SSHConnection(ssh_config, connection_info)
        connection.auto_reconnect = False
        
        result = await connection._attempt_reconnection()
        assert result is False
    
    @pytest.mark.asyncio
    async def test_attempt_reconnection_max_attempts_reached(self, ssh_config, connection_info):
        """Test reconnection attempt when max attempts are reached."""
        connection = SSHConnection(ssh_config, connection_info)
        connection._reconnect_attempts = 3
        connection._max_reconnect_attempts = 3
        
        result = await connection._attempt_reconnection()
        assert result is False
    
    @pytest.mark.asyncio
    async def test_attempt_reconnection_success(self, ssh_config, connection_info):
        """Test successful reconnection attempt."""
        connection = SSHConnection(ssh_config, connection_info)
        connection._connection_lost_at = datetime.now()
        
        with patch.object(connection, 'connect', new_callable=AsyncMock) as mock_connect:
            with patch.object(connection, '_cleanup_client', new_callable=AsyncMock):
                # Mock successful connection - the connect method should set _connected to True
                def mock_connect_side_effect():
                    connection._connected = True  # Simulate successful connection
                    return None
                
                mock_connect.side_effect = mock_connect_side_effect
                
                result = await connection._attempt_reconnection()
                
                assert result is True
                assert connection._reconnect_attempts == 0  # Should reset on success
                assert connection._connection_lost_at is None  # Should clear lost state
                mock_connect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_attempt_reconnection_failure(self, ssh_config, connection_info):
        """Test failed reconnection attempt."""
        connection = SSHConnection(ssh_config, connection_info)
        connection._connection_lost_at = datetime.now()
        
        with patch.object(connection, 'connect', new_callable=AsyncMock) as mock_connect:
            with patch.object(connection, '_cleanup_client', new_callable=AsyncMock):
                # Mock failed connection
                mock_connect.side_effect = ConnectionError("Connection failed")
                
                result = await connection._attempt_reconnection()
                
                assert result is False
                assert connection._reconnect_attempts == 1  # Should increment
                mock_connect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_force_reconnect(self, ssh_config, connection_info):
        """Test force reconnect functionality."""
        connection = SSHConnection(ssh_config, connection_info)
        connection._reconnect_attempts = 2  # Should reset
        
        with patch.object(connection, '_attempt_reconnection', new_callable=AsyncMock) as mock_reconnect:
            mock_reconnect.return_value = True
            
            result = await connection.force_reconnect()
            
            assert result is True
            assert connection.is_connection_lost is True  # Should mark as lost
            assert connection._reconnect_attempts == 0  # Should reset attempts
            mock_reconnect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_command_with_reconnection(self, ssh_config, connection_info, mock_ssh_client):
        """Test command execution with automatic reconnection."""
        connection = SSHConnection(ssh_config, connection_info)
        connection.client = mock_ssh_client
        connection._connected = False  # Not connected
        connection._connection_lost_at = datetime.now()  # Connection lost
        
        with patch.object(connection, '_attempt_reconnection', new_callable=AsyncMock) as mock_reconnect:
            with patch.object(connection, 'detect_connection_loss', new_callable=AsyncMock) as mock_detect:
                # Mock successful reconnection - this will be called and then set connection as connected
                def mock_reconnect_side_effect():
                    connection._connected = True  # Simulate successful reconnection
                    return True
                
                mock_reconnect.side_effect = mock_reconnect_side_effect
                mock_detect.return_value = False  # After reconnection, connection is healthy
                
                # Mock command execution
                mock_stdin = Mock()
                mock_stdout = Mock()
                mock_stderr = Mock()
                mock_stdout.read.return_value = b"test output"
                mock_stderr.read.return_value = b""
                mock_stdout.channel.recv_exit_status.return_value = 0
                
                mock_ssh_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)
                
                result = await connection.execute_command("echo test")
                
                assert result.stdout == "test output"
                assert result.exit_code == 0
                mock_reconnect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_command_reconnection_failure(self, ssh_config, connection_info):
        """Test command execution when reconnection fails."""
        connection = SSHConnection(ssh_config, connection_info)
        connection._connected = False  # Not connected
        connection._connection_lost_at = datetime.now()  # Connection lost
        
        with patch.object(connection, '_attempt_reconnection', new_callable=AsyncMock) as mock_reconnect:
            # Mock failed reconnection
            mock_reconnect.return_value = False
            
            with pytest.raises(ConnectionError) as exc_info:
                await connection.execute_command("echo test")
            
            assert "reconnection failed" in str(exc_info.value)
            mock_reconnect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check_recovery(self, ssh_config, connection_info, mock_ssh_client):
        """Test health check clearing connection lost state on recovery."""
        connection = SSHConnection(ssh_config, connection_info)
        connection.client = mock_ssh_client
        connection._connected = True
        connection._connection_lost_at = datetime.now()  # Connection was lost
        connection._reconnect_attempts = 2
        
        with patch.object(connection, 'execute_command', new_callable=AsyncMock) as mock_execute:
            from ssh_mcp_server.models import CommandResult
            
            # Mock successful health check
            mock_execute.return_value = CommandResult(
                stdout="health_check",
                stderr="",
                exit_code=0,
                execution_time=0.1
            )
            
            result = await connection.health_check()
            
            assert result is True
            assert connection._connection_lost_at is None  # Should clear lost state
            assert connection._reconnect_attempts == 0  # Should reset attempts
    
    @pytest.mark.asyncio
    async def test_connection_stats_include_reconnection_info(self, ssh_config, connection_info):
        """Test that connection stats include reconnection information."""
        connection = SSHConnection(ssh_config, connection_info)
        connection._reconnect_attempts = 2
        connection._connection_lost_at = datetime.now()
        connection._last_reconnect_attempt = datetime.now()
        
        stats = await connection.get_connection_stats()
        
        assert "auto_reconnect" in stats
        assert "reconnect_attempts" in stats
        assert "max_reconnect_attempts" in stats
        assert "is_connection_lost" in stats
        assert "connection_lost_at" in stats
        assert "last_reconnect_attempt" in stats
        
        assert stats["auto_reconnect"] is True
        assert stats["reconnect_attempts"] == 2
        assert stats["is_connection_lost"] is True


class TestSSHManagerReconnection:
    """Test SSH manager reconnection functionality."""
    
    @pytest.mark.asyncio
    async def test_enable_auto_reconnect(self):
        """Test enabling auto-reconnect for a connection."""
        manager = SSHManager()
        
        # Create a mock connection
        mock_connection = Mock()
        mock_connection.auto_reconnect = False
        connection_id = "test-connection-id"
        manager.connections[connection_id] = mock_connection
        
        result = await manager.enable_auto_reconnect(connection_id)
        
        assert result is True
        assert mock_connection.auto_reconnect is True
    
    @pytest.mark.asyncio
    async def test_enable_auto_reconnect_not_found(self):
        """Test enabling auto-reconnect for non-existent connection."""
        manager = SSHManager()
        
        result = await manager.enable_auto_reconnect("non-existent")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_disable_auto_reconnect(self):
        """Test disabling auto-reconnect for a connection."""
        manager = SSHManager()
        
        # Create a mock connection
        mock_connection = Mock()
        mock_connection.auto_reconnect = True
        connection_id = "test-connection-id"
        manager.connections[connection_id] = mock_connection
        
        result = await manager.disable_auto_reconnect(connection_id)
        
        assert result is True
        assert mock_connection.auto_reconnect is False
    
    @pytest.mark.asyncio
    async def test_force_reconnect(self):
        """Test forcing reconnection for a connection."""
        manager = SSHManager()
        
        # Create a mock connection
        mock_connection = AsyncMock()
        mock_connection.force_reconnect.return_value = True
        connection_id = "test-connection-id"
        manager.connections[connection_id] = mock_connection
        
        result = await manager.force_reconnect(connection_id)
        
        assert result is True
        mock_connection.force_reconnect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_force_reconnect_not_found(self):
        """Test forcing reconnection for non-existent connection."""
        manager = SSHManager()
        
        result = await manager.force_reconnect("non-existent")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_connection_status(self):
        """Test getting connection status with reconnection info."""
        manager = SSHManager()
        manager._running = True
        
        # Create a mock connection
        mock_connection = AsyncMock()
        mock_connection.get_connection_stats.return_value = {
            "connection_id": "test-id",
            "connected": True,
            "auto_reconnect": True,
            "reconnect_attempts": 0
        }
        connection_id = "test-connection-id"
        manager.connections[connection_id] = mock_connection
        
        status = await manager.get_connection_status(connection_id)
        
        assert status is not None
        assert status["connection_id"] == "test-id"
        assert status["manager_running"] is True
        assert status["in_connection_pool"] is True
        assert "health_check_interval" in status
    
    @pytest.mark.asyncio
    async def test_monitor_connections(self):
        """Test monitoring all connections."""
        manager = SSHManager()
        
        # Create mock connections
        mock_connection1 = AsyncMock()
        mock_connection1.get_connection_stats.return_value = {
            "connection_id": "test-id-1",
            "connected": True
        }
        
        mock_connection2 = AsyncMock()
        mock_connection2.get_connection_stats.return_value = {
            "connection_id": "test-id-2",
            "connected": False,
            "is_connection_lost": True
        }
        
        manager.connections["id1"] = mock_connection1
        manager.connections["id2"] = mock_connection2
        
        with patch.object(manager, 'get_connection_status') as mock_get_status:
            mock_get_status.side_effect = [
                {"connection_id": "test-id-1", "connected": True},
                {"connection_id": "test-id-2", "connected": False}
            ]
            
            statuses = await manager.monitor_connections()
            
            assert len(statuses) == 2
            assert "id1" in statuses
            assert "id2" in statuses
    
    @pytest.mark.asyncio
    async def test_attempt_reconnect_all_lost(self):
        """Test attempting to reconnect all lost connections."""
        manager = SSHManager()
        
        # Create mock connections
        mock_connection1 = AsyncMock()
        mock_connection1.is_connection_lost = True
        mock_connection1.auto_reconnect = True
        
        mock_connection2 = AsyncMock()
        mock_connection2.is_connection_lost = False
        mock_connection2.auto_reconnect = True
        
        mock_connection3 = AsyncMock()
        mock_connection3.is_connection_lost = True
        mock_connection3.auto_reconnect = False  # Should be skipped
        
        manager.connections["lost1"] = mock_connection1
        manager.connections["healthy"] = mock_connection2
        manager.connections["lost_no_reconnect"] = mock_connection3
        
        with patch.object(manager, 'force_reconnect') as mock_force_reconnect:
            mock_force_reconnect.return_value = True
            
            results = await manager.attempt_reconnect_all_lost()
            
            # Should only attempt reconnection for lost1
            assert len(results) == 1
            assert "lost1" in results
            assert results["lost1"] is True
            mock_force_reconnect.assert_called_once_with("lost1")
    
    @pytest.mark.asyncio
    async def test_cleanup_unhealthy_connections_with_reconnection(self):
        """Test cleanup considering reconnection capabilities."""
        manager = SSHManager()
        
        # Create mock connections
        mock_connection1 = Mock()
        mock_connection1.connected = False
        mock_connection1.auto_reconnect = False  # Should be cleaned up
        
        mock_connection2 = Mock()
        mock_connection2.connected = False
        mock_connection2.auto_reconnect = True
        mock_connection2.is_connection_lost = True
        mock_connection2.reconnect_attempts = 5
        mock_connection2._max_reconnect_attempts = 3  # Exhausted attempts, should be cleaned up
        
        mock_connection3 = Mock()
        mock_connection3.connected = False
        mock_connection3.auto_reconnect = True
        mock_connection3.is_connection_lost = True
        mock_connection3.reconnect_attempts = 1
        mock_connection3._max_reconnect_attempts = 3  # Still has attempts, should not be cleaned up
        
        manager.connections["no_reconnect"] = mock_connection1
        manager.connections["exhausted"] = mock_connection2
        manager.connections["can_retry"] = mock_connection3
        
        with patch.object(manager, 'disconnect_connection') as mock_disconnect:
            mock_disconnect.return_value = True
            
            cleanup_count = await manager.cleanup_unhealthy_connections()
            
            # Should clean up 2 connections (no_reconnect and exhausted)
            assert cleanup_count == 2
            assert mock_disconnect.call_count == 2