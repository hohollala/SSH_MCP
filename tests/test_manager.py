"""Unit tests for SSH Manager."""

import asyncio
import pytest
import pytest_asyncio
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from ssh_mcp_server.manager import SSHManager, SSHManagerError
from ssh_mcp_server.models import SSHConfig, CommandResult, ConnectionInfo
from ssh_mcp_server.connection import SSHConnection, ConnectionError


class TestSSHManager:
    """Test cases for SSH Manager."""
    
    @pytest.fixture
    def ssh_config(self):
        """Create a test SSH configuration."""
        return SSHConfig(
            hostname="test.example.com",
            username="testuser",
            port=22,
            auth_method="agent",
            timeout=30
        )
    
    @pytest.fixture
    def manager(self):
        """Create a test SSH Manager."""
        return SSHManager(max_connections=5, health_check_interval=10)
    
    @pytest_asyncio.fixture
    async def started_manager(self, manager):
        """Create and start a test SSH Manager."""
        await manager.start()
        yield manager
        await manager.stop()
    
    def test_manager_initialization(self):
        """Test SSH Manager initialization."""
        manager = SSHManager(max_connections=10, health_check_interval=30)
        
        assert manager.max_connections == 10
        assert manager.health_check_interval == 30
        assert len(manager.connections) == 0
        assert len(manager.connection_configs) == 0
        assert not manager._running
        assert manager._total_connections_created == 0
        assert manager._total_commands_executed == 0
        assert isinstance(manager._start_time, datetime)
    
    @pytest.mark.asyncio
    async def test_start_stop_manager(self, manager):
        """Test starting and stopping the SSH Manager."""
        # Initially not running
        assert not manager._running
        assert manager._health_check_task is None
        
        # Start manager
        await manager.start()
        assert manager._running
        assert manager._health_check_task is not None
        
        # Starting again should not cause issues
        await manager.start()
        assert manager._running
        
        # Stop manager
        await manager.stop()
        assert not manager._running
        assert manager._health_check_task.cancelled()
        
        # Stopping again should not cause issues
        await manager.stop()
        assert not manager._running
    
    @pytest.mark.asyncio
    @patch('ssh_mcp_server.manager.SSHConnection')
    async def test_create_connection_success(self, mock_ssh_connection, started_manager, ssh_config):
        """Test successful connection creation."""
        # Mock SSH connection
        mock_connection = AsyncMock()
        mock_connection.connect = AsyncMock()
        mock_connection.connection_info = Mock()
        mock_ssh_connection.return_value = mock_connection
        
        # Create connection
        connection_id = await started_manager.create_connection(ssh_config)
        
        # Verify connection was created
        assert connection_id in started_manager.connections
        assert connection_id in started_manager.connection_configs
        assert started_manager._total_connections_created == 1
        
        # Verify connection was called correctly
        mock_ssh_connection.assert_called_once()
        mock_connection.connect.assert_called_once()
        
        # Verify connection ID is a valid UUID
        uuid.UUID(connection_id)  # Should not raise exception
    
    @pytest.mark.asyncio
    @patch('ssh_mcp_server.manager.SSHConnection')
    async def test_create_connection_failure(self, mock_ssh_connection, started_manager, ssh_config):
        """Test connection creation failure."""
        # Mock SSH connection that fails to connect
        mock_connection = AsyncMock()
        mock_connection.connect = AsyncMock(side_effect=ConnectionError("Connection failed"))
        mock_ssh_connection.return_value = mock_connection
        
        # Attempt to create connection
        with pytest.raises(SSHManagerError) as exc_info:
            await started_manager.create_connection(ssh_config)
        
        assert "Failed to create connection" in str(exc_info.value)
        assert len(started_manager.connections) == 0
        assert started_manager._total_connections_created == 0
    
    @pytest.mark.asyncio
    @patch('ssh_mcp_server.manager.SSHConnection')
    async def test_max_connections_limit(self, mock_ssh_connection, started_manager, ssh_config):
        """Test maximum connections limit enforcement."""
        # Mock SSH connection
        mock_connection = AsyncMock()
        mock_connection.connect = AsyncMock()
        mock_connection.connection_info = Mock()
        mock_ssh_connection.return_value = mock_connection
        
        # Create maximum number of connections
        connection_ids = []
        for i in range(started_manager.max_connections):
            connection_id = await started_manager.create_connection(ssh_config)
            connection_ids.append(connection_id)
        
        assert len(started_manager.connections) == started_manager.max_connections
        
        # Attempt to create one more connection (should fail)
        with pytest.raises(SSHManagerError) as exc_info:
            await started_manager.create_connection(ssh_config)
        
        assert "Maximum number of connections" in str(exc_info.value)
        assert len(started_manager.connections) == started_manager.max_connections
    
    @pytest.mark.asyncio
    async def test_get_connection(self, started_manager):
        """Test getting connections by ID."""
        # Non-existent connection
        connection = await started_manager.get_connection("non-existent")
        assert connection is None
        
        # Add a mock connection
        connection_id = str(uuid.uuid4())
        mock_connection = AsyncMock()
        started_manager.connections[connection_id] = mock_connection
        
        # Get existing connection
        connection = await started_manager.get_connection(connection_id)
        assert connection is mock_connection
    
    @pytest.mark.asyncio
    async def test_disconnect_connection(self, started_manager):
        """Test disconnecting a specific connection."""
        # Non-existent connection
        result = await started_manager.disconnect_connection("non-existent")
        assert result is False
        
        # Add a mock connection
        connection_id = str(uuid.uuid4())
        mock_connection = AsyncMock()
        mock_connection.disconnect = AsyncMock()
        started_manager.connections[connection_id] = mock_connection
        started_manager.connection_configs[connection_id] = Mock()
        
        # Disconnect existing connection
        result = await started_manager.disconnect_connection(connection_id)
        assert result is True
        assert connection_id not in started_manager.connections
        assert connection_id not in started_manager.connection_configs
        mock_connection.disconnect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_disconnect_connection_with_error(self, started_manager):
        """Test disconnecting a connection that raises an error."""
        # Add a mock connection that raises error on disconnect
        connection_id = str(uuid.uuid4())
        mock_connection = AsyncMock()
        mock_connection.disconnect = AsyncMock(side_effect=Exception("Disconnect error"))
        started_manager.connections[connection_id] = mock_connection
        started_manager.connection_configs[connection_id] = Mock()
        
        # Disconnect should still succeed (connection is removed despite error)
        result = await started_manager.disconnect_connection(connection_id)
        assert result is True
        assert connection_id not in started_manager.connections
        assert connection_id not in started_manager.connection_configs
    
    @pytest.mark.asyncio
    async def test_disconnect_all(self, started_manager):
        """Test disconnecting all connections."""
        # Add multiple mock connections
        connection_ids = []
        for i in range(3):
            connection_id = str(uuid.uuid4())
            mock_connection = AsyncMock()
            mock_connection.disconnect = AsyncMock()
            started_manager.connections[connection_id] = mock_connection
            started_manager.connection_configs[connection_id] = Mock()
            connection_ids.append(connection_id)
        
        # Disconnect all
        count = await started_manager.disconnect_all()
        
        assert count == 3
        assert len(started_manager.connections) == 0
        assert len(started_manager.connection_configs) == 0
        
        # Verify all connections were disconnected
        for connection_id in connection_ids:
            mock_connection = started_manager.connections.get(connection_id)
            # Connection should be removed, so this will be None
    
    @pytest.mark.asyncio
    async def test_execute_command_success(self, started_manager):
        """Test successful command execution."""
        # Add a mock connection
        connection_id = str(uuid.uuid4())
        mock_connection = AsyncMock()
        mock_connection.connected = True
        mock_result = CommandResult(
            stdout="test output",
            stderr="",
            exit_code=0,
            execution_time=0.5,
            command="echo test"
        )
        mock_connection.execute_command = AsyncMock(return_value=mock_result)
        started_manager.connections[connection_id] = mock_connection
        
        # Execute command
        result = await started_manager.execute_command(connection_id, "echo test")
        
        assert result is mock_result
        assert started_manager._total_commands_executed == 1
        mock_connection.execute_command.assert_called_once_with("echo test", None)
    
    @pytest.mark.asyncio
    async def test_execute_command_connection_not_found(self, started_manager):
        """Test command execution with non-existent connection."""
        with pytest.raises(SSHManagerError) as exc_info:
            await started_manager.execute_command("non-existent", "echo test")
        
        assert "Connection" in str(exc_info.value)
        assert "not found" in str(exc_info.value)
        assert started_manager._total_commands_executed == 0
    
    @pytest.mark.asyncio
    async def test_execute_command_connection_not_active(self, started_manager):
        """Test command execution with inactive connection."""
        # Add a mock connection that's not connected
        connection_id = str(uuid.uuid4())
        mock_connection = AsyncMock()
        mock_connection.connected = False
        started_manager.connections[connection_id] = mock_connection
        
        with pytest.raises(SSHManagerError) as exc_info:
            await started_manager.execute_command(connection_id, "echo test")
        
        assert "not active" in str(exc_info.value)
        assert started_manager._total_commands_executed == 0
    
    @pytest.mark.asyncio
    async def test_execute_command_execution_failure(self, started_manager):
        """Test command execution failure."""
        # Add a mock connection that fails to execute
        connection_id = str(uuid.uuid4())
        mock_connection = AsyncMock()
        mock_connection.connected = True
        mock_connection.execute_command = AsyncMock(side_effect=ConnectionError("Execution failed"))
        started_manager.connections[connection_id] = mock_connection
        
        with pytest.raises(SSHManagerError) as exc_info:
            await started_manager.execute_command(connection_id, "echo test")
        
        assert "Command execution failed" in str(exc_info.value)
        assert started_manager._total_commands_executed == 0
    
    @pytest.mark.asyncio
    async def test_list_connections(self, started_manager):
        """Test listing all connections."""
        # Initially empty
        connections = await started_manager.list_connections()
        assert len(connections) == 0
        
        # Add mock connections
        connection_infos = []
        for i in range(3):
            connection_id = str(uuid.uuid4())
            connection_info = ConnectionInfo.create(f"host{i}.example.com", f"user{i}")
            connection_info.connection_id = connection_id
            
            mock_connection = AsyncMock()
            mock_connection.connected = True
            mock_connection.last_activity = datetime.now()
            mock_connection.connection_info = connection_info
            mock_connection.disconnect = AsyncMock()
            
            started_manager.connections[connection_id] = mock_connection
            connection_infos.append(connection_info)
        
        # List connections
        connections = await started_manager.list_connections()
        assert len(connections) == 3
        
        # Verify connection info is updated
        for conn_info in connections:
            assert conn_info.connected is True
            assert isinstance(conn_info.last_used, datetime)
    
    @pytest.mark.asyncio
    async def test_get_connection_stats(self, started_manager):
        """Test getting connection statistics."""
        # Non-existent connection
        stats = await started_manager.get_connection_stats("non-existent")
        assert stats is None
        
        # Add a mock connection
        connection_id = str(uuid.uuid4())
        mock_connection = AsyncMock()
        mock_stats = {"connection_id": connection_id, "connected": True}
        mock_connection.get_connection_stats = AsyncMock(return_value=mock_stats)
        started_manager.connections[connection_id] = mock_connection
        
        # Get stats
        stats = await started_manager.get_connection_stats(connection_id)
        assert stats is mock_stats
        mock_connection.get_connection_stats.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_manager_stats(self, started_manager):
        """Test getting manager statistics."""
        # Add some mock connections
        for i in range(2):
            connection_id = str(uuid.uuid4())
            mock_connection = AsyncMock()
            mock_connection.connected = i == 0  # First one connected, second not
            mock_connection.disconnect = AsyncMock()
            started_manager.connections[connection_id] = mock_connection
        
        started_manager._total_connections_created = 5
        started_manager._total_commands_executed = 10
        
        stats = await started_manager.get_manager_stats()
        
        assert stats["running"] is True
        assert stats["max_connections"] == 5
        assert stats["active_connections"] == 2
        assert stats["connected_count"] == 1
        assert stats["total_connections_created"] == 5
        assert stats["total_commands_executed"] == 10
        assert stats["health_check_interval"] == 10
        assert "uptime" in stats
        assert "start_time" in stats
    
    @pytest.mark.asyncio
    async def test_health_check_connection(self, started_manager):
        """Test health checking a specific connection."""
        # Non-existent connection
        result = await started_manager.health_check_connection("non-existent")
        assert result is False
        
        # Add a mock connection
        connection_id = str(uuid.uuid4())
        mock_connection = AsyncMock()
        mock_connection.health_check = AsyncMock(return_value=True)
        started_manager.connections[connection_id] = mock_connection
        
        # Health check
        result = await started_manager.health_check_connection(connection_id)
        assert result is True
        mock_connection.health_check.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check_all(self, started_manager):
        """Test health checking all connections."""
        # Add mock connections
        connection_ids = []
        for i in range(3):
            connection_id = str(uuid.uuid4())
            mock_connection = AsyncMock()
            mock_connection.health_check = AsyncMock(return_value=i % 2 == 0)  # Alternate healthy/unhealthy
            started_manager.connections[connection_id] = mock_connection
            connection_ids.append(connection_id)
        
        # Health check all
        results = await started_manager.health_check_all()
        
        assert len(results) == 3
        assert results[connection_ids[0]] is True
        assert results[connection_ids[1]] is False
        assert results[connection_ids[2]] is True
    
    @pytest.mark.asyncio
    async def test_health_check_all_with_error(self, started_manager):
        """Test health checking all connections with some errors."""
        # Add mock connections
        connection_ids = []
        for i in range(2):
            connection_id = str(uuid.uuid4())
            mock_connection = AsyncMock()
            if i == 0:
                mock_connection.health_check = AsyncMock(return_value=True)
            else:
                mock_connection.health_check = AsyncMock(side_effect=Exception("Health check error"))
            started_manager.connections[connection_id] = mock_connection
            connection_ids.append(connection_id)
        
        # Health check all
        results = await started_manager.health_check_all()
        
        assert len(results) == 2
        assert results[connection_ids[0]] is True
        assert results[connection_ids[1]] is False  # Error should result in False
    
    @pytest.mark.asyncio
    async def test_cleanup_unhealthy_connections(self, started_manager):
        """Test cleaning up unhealthy connections."""
        # Add mock connections (some healthy, some not)
        healthy_id = str(uuid.uuid4())
        unhealthy_id = str(uuid.uuid4())
        
        healthy_connection = AsyncMock()
        healthy_connection.connected = True
        healthy_connection.disconnect = AsyncMock()
        
        unhealthy_connection = AsyncMock()
        unhealthy_connection.connected = False
        unhealthy_connection.disconnect = AsyncMock()
        
        started_manager.connections[healthy_id] = healthy_connection
        started_manager.connections[unhealthy_id] = unhealthy_connection
        started_manager.connection_configs[healthy_id] = Mock()
        started_manager.connection_configs[unhealthy_id] = Mock()
        
        # Cleanup unhealthy connections
        count = await started_manager.cleanup_unhealthy_connections()
        
        assert count == 1
        assert healthy_id in started_manager.connections
        assert unhealthy_id not in started_manager.connections
        assert unhealthy_id not in started_manager.connection_configs
        
        # Verify disconnect was called on unhealthy connection
        unhealthy_connection.disconnect.assert_called_once()
        healthy_connection.disconnect.assert_not_called()
    
    def test_manager_magic_methods(self, manager):
        """Test SSH Manager magic methods."""
        # Add some mock connections
        for i in range(3):
            connection_id = str(uuid.uuid4())
            mock_connection = AsyncMock()
            mock_connection.disconnect = AsyncMock()
            manager.connections[connection_id] = mock_connection
        
        # Test __len__
        assert len(manager) == 3
        
        # Test __contains__
        connection_id = list(manager.connections.keys())[0]
        assert connection_id in manager
        assert "non-existent" not in manager
        
        # Test __str__
        str_repr = str(manager)
        assert "SSHManager" in str_repr
        assert "connections=3" in str_repr
        assert "max=5" in str_repr
        
        # Test __repr__
        repr_str = repr(manager)
        assert "SSHManager" in repr_str
        assert "connections=3" in repr_str
        assert "max_connections=5" in repr_str


class TestSSHManagerIntegration:
    """Integration tests for SSH Manager."""
    
    @pytest.fixture
    def ssh_config(self):
        """Create a test SSH configuration."""
        return SSHConfig(
            hostname="localhost",
            username="testuser",
            port=22,
            auth_method="agent",
            timeout=5
        )
    
    @pytest_asyncio.fixture
    async def manager(self):
        """Create and start a test SSH Manager."""
        manager = SSHManager(max_connections=2, health_check_interval=1)
        await manager.start()
        yield manager
        await manager.stop()
    
    @pytest.mark.asyncio
    @patch('ssh_mcp_server.manager.SSHConnection')
    async def test_full_connection_lifecycle(self, mock_ssh_connection, manager, ssh_config):
        """Test complete connection lifecycle."""
        # Mock SSH connection
        mock_connection = AsyncMock()
        mock_connection.connect = AsyncMock()
        mock_connection.connected = True
        mock_connection.connection_info = Mock()
        mock_connection.last_activity = datetime.now()
        mock_connection.health_check = AsyncMock(return_value=True)
        mock_connection.disconnect = AsyncMock()
        mock_connection.get_connection_stats = AsyncMock(return_value={"test": "stats"})
        
        mock_result = CommandResult(
            stdout="test output",
            stderr="",
            exit_code=0,
            execution_time=0.1,
            command="echo test"
        )
        mock_connection.execute_command = AsyncMock(return_value=mock_result)
        mock_ssh_connection.return_value = mock_connection
        
        # Create connection
        connection_id = await manager.create_connection(ssh_config)
        assert connection_id in manager
        
        # Execute command
        result = await manager.execute_command(connection_id, "echo test")
        assert result.stdout == "test output"
        assert result.success
        
        # Health check
        health = await manager.health_check_connection(connection_id)
        assert health is True
        
        # Get stats
        stats = await manager.get_connection_stats(connection_id)
        assert stats == {"test": "stats"}
        
        # List connections
        connections = await manager.list_connections()
        assert len(connections) == 1
        
        # Disconnect
        result = await manager.disconnect_connection(connection_id)
        assert result is True
        assert connection_id not in manager
    
    @pytest.mark.asyncio
    async def test_health_check_loop_integration(self, manager):
        """Test that health check loop runs and processes connections."""
        # Add a mock unhealthy connection (connected=False means it will be cleaned up)
        connection_id = str(uuid.uuid4())
        mock_connection = AsyncMock()
        mock_connection.connected = False  # This will trigger cleanup
        mock_connection.disconnect = AsyncMock()
        mock_connection.health_check = AsyncMock(return_value=False)
        manager.connections[connection_id] = mock_connection
        manager.connection_configs[connection_id] = Mock()
        
        # Wait for health check loop to run (it runs every 1 second)
        await asyncio.sleep(1.5)
        
        # Connection should be cleaned up because connected=False
        assert connection_id not in manager.connections
        mock_connection.disconnect.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])