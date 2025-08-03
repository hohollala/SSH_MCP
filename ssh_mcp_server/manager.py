"""SSH Manager for connection pooling and management."""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any
from concurrent.futures import ThreadPoolExecutor

from .models import SSHConfig, CommandResult, ConnectionInfo
from .connection import SSHConnection, ConnectionError
from .auth import AuthenticationHandler


logger = logging.getLogger(__name__)


class SSHManagerError(Exception):
    """Custom exception for SSH Manager errors."""
    
    def __init__(self, message: str, connection_id: Optional[str] = None, details: Optional[str] = None):
        """Initialize SSH Manager error.
        
        Args:
            message: Human-readable error message
            connection_id: ID of the connection related to the error (if applicable)
            details: Additional error details
        """
        super().__init__(message)
        self.connection_id = connection_id
        self.details = details


class SSHManager:
    """Manages multiple SSH connections with connection pooling and monitoring."""
    
    def __init__(self, max_connections: int = 10, health_check_interval: int = 60):
        """Initialize SSH Manager.
        
        Args:
            max_connections: Maximum number of concurrent connections
            health_check_interval: Interval in seconds between health checks
        """
        self.max_connections = max_connections
        self.health_check_interval = health_check_interval
        
        # Connection storage
        self.connections: Dict[str, SSHConnection] = {}
        self.connection_configs: Dict[str, SSHConfig] = {}
        
        # Manager state
        self._running = False
        self._health_check_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        
        # Statistics
        self._total_connections_created = 0
        self._total_commands_executed = 0
        self._start_time = datetime.now()
        
        # Thread pool for blocking operations
        self._executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix="ssh_manager")
        
        self.logger = logging.getLogger(__name__ + ".SSHManager")
        self.logger.info(f"SSH Manager initialized with max_connections={max_connections}")
    
    async def start(self) -> None:
        """Start the SSH Manager and background tasks."""
        if self._running:
            self.logger.warning("SSH Manager is already running")
            return
        
        self.logger.info("Starting SSH Manager")
        self._running = True
        
        # Start health check task
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        self.logger.info("SSH Manager started successfully")
    
    async def stop(self) -> None:
        """Stop the SSH Manager and cleanup all connections."""
        if not self._running:
            self.logger.warning("SSH Manager is not running")
            return
        
        self.logger.info("Stopping SSH Manager")
        self._running = False
        
        # Cancel health check task
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Disconnect all connections
        await self.disconnect_all()
        
        # Shutdown thread pool
        self._executor.shutdown(wait=True)
        
        self.logger.info("SSH Manager stopped")
    
    async def create_connection(self, config: SSHConfig) -> str:
        """Create a new SSH connection.
        
        Args:
            config: SSH configuration for the connection
            
        Returns:
            Unique connection ID
            
        Raises:
            SSHManagerError: If connection creation fails or limits are exceeded
        """
        async with self._lock:
            # Check connection limit
            if len(self.connections) >= self.max_connections:
                raise SSHManagerError(
                    f"Maximum number of connections ({self.max_connections}) reached",
                    details=f"Active connections: {len(self.connections)}"
                )
            
            # Generate unique connection ID
            connection_id = str(uuid.uuid4())
            
            # Create connection info
            connection_info = ConnectionInfo.create(
                hostname=config.hostname,
                username=config.username,
                port=config.port
            )
            connection_info.connection_id = connection_id
            
            self.logger.info(f"Creating connection {connection_id[:8]} to {config.username}@{config.hostname}:{config.port}")
            
            try:
                # Create SSH connection
                ssh_connection = SSHConnection(config, connection_info)
                
                # Attempt to connect
                await ssh_connection.connect()
                
                # Store connection and config
                self.connections[connection_id] = ssh_connection
                self.connection_configs[connection_id] = config
                
                # Update statistics
                self._total_connections_created += 1
                
                self.logger.info(f"Successfully created connection {connection_id[:8]}")
                return connection_id
                
            except ConnectionError as e:
                self.logger.error(f"Failed to create connection {connection_id[:8]}: {e}")
                raise SSHManagerError(
                    f"Failed to create connection to {config.hostname}",
                    connection_id,
                    str(e)
                )
            
            except Exception as e:
                self.logger.error(f"Unexpected error creating connection {connection_id[:8]}: {e}")
                raise SSHManagerError(
                    f"Unexpected error creating connection to {config.hostname}",
                    connection_id,
                    str(e)
                )
    
    async def get_connection(self, connection_id: str) -> Optional[SSHConnection]:
        """Get an SSH connection by ID.
        
        Args:
            connection_id: The connection ID to retrieve
            
        Returns:
            SSHConnection instance or None if not found
        """
        return self.connections.get(connection_id)
    
    async def disconnect_connection(self, connection_id: str) -> bool:
        """Disconnect and remove a specific connection.
        
        Args:
            connection_id: The connection ID to disconnect
            
        Returns:
            True if connection was found and disconnected, False if not found
        """
        async with self._lock:
            connection = self.connections.get(connection_id)
            if not connection:
                self.logger.warning(f"Connection {connection_id[:8]} not found for disconnection")
                return False
            
            self.logger.info(f"Disconnecting connection {connection_id[:8]}")
            
            try:
                await connection.disconnect()
            except Exception as e:
                self.logger.error(f"Error disconnecting connection {connection_id[:8]}: {e}")
            
            # Remove from storage
            self.connections.pop(connection_id, None)
            self.connection_configs.pop(connection_id, None)
            
            self.logger.info(f"Connection {connection_id[:8]} removed from pool")
            return True
    
    async def disconnect_all(self) -> int:
        """Disconnect all active connections.
        
        Returns:
            Number of connections that were disconnected
        """
        async with self._lock:
            connection_ids = list(self.connections.keys())
            disconnected_count = 0
            
            self.logger.info(f"Disconnecting all {len(connection_ids)} connections")
            
            # Disconnect all connections concurrently
            disconnect_tasks = []
            for connection_id in connection_ids:
                connection = self.connections[connection_id]
                task = asyncio.create_task(connection.disconnect())
                disconnect_tasks.append((connection_id, task))
            
            # Wait for all disconnections to complete
            for connection_id, task in disconnect_tasks:
                try:
                    await task
                    disconnected_count += 1
                except Exception as e:
                    self.logger.error(f"Error disconnecting connection {connection_id[:8]}: {e}")
            
            # Clear all connections
            self.connections.clear()
            self.connection_configs.clear()
            
            self.logger.info(f"Disconnected {disconnected_count} connections")
            return disconnected_count
    
    async def execute_command(self, connection_id: str, command: str, timeout: Optional[int] = None) -> CommandResult:
        """Execute a command on a specific connection.
        
        Args:
            connection_id: The connection ID to use
            command: Command to execute
            timeout: Command timeout in seconds
            
        Returns:
            CommandResult with execution details
            
        Raises:
            SSHManagerError: If connection not found or command execution fails
        """
        connection = self.connections.get(connection_id)
        if not connection:
            raise SSHManagerError(
                f"Connection {connection_id[:8]} not found",
                connection_id,
                "Connection may have been disconnected or never existed"
            )
        
        if not connection.connected:
            raise SSHManagerError(
                f"Connection {connection_id[:8]} is not active",
                connection_id,
                "Connection may have been lost or disconnected"
            )
        
        self.logger.debug(f"Executing command on connection {connection_id[:8]}: {command}")
        
        try:
            result = await connection.execute_command(command, timeout)
            self._total_commands_executed += 1
            return result
            
        except ConnectionError as e:
            self.logger.error(f"Command execution failed on connection {connection_id[:8]}: {e}")
            raise SSHManagerError(
                f"Command execution failed on connection {connection_id[:8]}",
                connection_id,
                str(e)
            )
    
    async def list_connections(self) -> List[ConnectionInfo]:
        """Get a list of all active connections.
        
        Returns:
            List of ConnectionInfo objects for all active connections
        """
        connection_list = []
        
        for connection_id, connection in self.connections.items():
            # Update connection info with current state
            connection_info = connection.connection_info
            connection_info.connected = connection.connected
            connection_info.last_used = connection.last_activity
            
            connection_list.append(connection_info)
        
        return connection_list
    
    async def get_connection_stats(self, connection_id: str) -> Optional[Dict]:
        """Get detailed statistics for a specific connection.
        
        Args:
            connection_id: The connection ID to get stats for
            
        Returns:
            Dictionary with connection statistics or None if not found
        """
        connection = self.connections.get(connection_id)
        if not connection:
            return None
        
        return await connection.get_connection_stats()
    
    async def get_manager_stats(self) -> Dict:
        """Get overall manager statistics.
        
        Returns:
            Dictionary with manager statistics
        """
        active_connections = len(self.connections)
        connected_count = sum(1 for conn in self.connections.values() if conn.connected)
        
        uptime = datetime.now() - self._start_time
        
        return {
            "running": self._running,
            "uptime": str(uptime),
            "max_connections": self.max_connections,
            "active_connections": active_connections,
            "connected_count": connected_count,
            "total_connections_created": self._total_connections_created,
            "total_commands_executed": self._total_commands_executed,
            "health_check_interval": self.health_check_interval,
            "start_time": self._start_time.isoformat()
        }
    
    async def health_check_connection(self, connection_id: str) -> bool:
        """Perform a health check on a specific connection.
        
        Args:
            connection_id: The connection ID to check
            
        Returns:
            True if connection is healthy, False otherwise
        """
        connection = self.connections.get(connection_id)
        if not connection:
            return False
        
        return await connection.health_check()
    
    async def health_check_all(self) -> Dict[str, bool]:
        """Perform health checks on all connections.
        
        Returns:
            Dictionary mapping connection IDs to health status
        """
        health_results = {}
        
        # Run health checks concurrently
        health_tasks = []
        for connection_id, connection in self.connections.items():
            task = asyncio.create_task(connection.health_check())
            health_tasks.append((connection_id, task))
        
        # Collect results
        for connection_id, task in health_tasks:
            try:
                health_results[connection_id] = await task
            except Exception as e:
                self.logger.error(f"Health check failed for connection {connection_id[:8]}: {e}")
                health_results[connection_id] = False
        
        return health_results
    
    async def read_file(self, connection_id: str, file_path: str, encoding: str = "utf-8") -> str:
        """Read a file from a remote server.
        
        Args:
            connection_id: The connection ID to use
            file_path: Path to the file to read
            encoding: Text encoding to use when reading the file
            
        Returns:
            File contents as string
            
        Raises:
            SSHManagerError: If connection not found or file operation fails
        """
        connection = self.connections.get(connection_id)
        if not connection:
            raise SSHManagerError(
                f"Connection {connection_id[:8]} not found",
                connection_id,
                "Connection may have been disconnected or never existed"
            )
        
        if not connection.connected:
            raise SSHManagerError(
                f"Connection {connection_id[:8]} is not active",
                connection_id,
                "Connection may have been lost or disconnected"
            )
        
        self.logger.debug(f"Reading file on connection {connection_id[:8]}: {file_path}")
        
        try:
            content = await connection.read_file(file_path, encoding)
            return content
            
        except ConnectionError as e:
            self.logger.error(f"File read failed on connection {connection_id[:8]}: {e}")
            raise SSHManagerError(
                f"File read failed on connection {connection_id[:8]}",
                connection_id,
                str(e)
            )
    
    async def write_file(self, connection_id: str, file_path: str, content: str, 
                        encoding: str = "utf-8", create_dirs: bool = False) -> None:
        """Write content to a file on a remote server.
        
        Args:
            connection_id: The connection ID to use
            file_path: Path to the file to write
            content: Content to write to the file
            encoding: Text encoding to use when writing the file
            create_dirs: Whether to create parent directories if they don't exist
            
        Raises:
            SSHManagerError: If connection not found or file operation fails
        """
        connection = self.connections.get(connection_id)
        if not connection:
            raise SSHManagerError(
                f"Connection {connection_id[:8]} not found",
                connection_id,
                "Connection may have been disconnected or never existed"
            )
        
        if not connection.connected:
            raise SSHManagerError(
                f"Connection {connection_id[:8]} is not active",
                connection_id,
                "Connection may have been lost or disconnected"
            )
        
        self.logger.debug(f"Writing file on connection {connection_id[:8]}: {file_path}")
        
        try:
            await connection.write_file(file_path, content, encoding, create_dirs)
            
        except ConnectionError as e:
            self.logger.error(f"File write failed on connection {connection_id[:8]}: {e}")
            raise SSHManagerError(
                f"File write failed on connection {connection_id[:8]}",
                connection_id,
                str(e)
            )
    
    async def list_directory(self, connection_id: str, directory_path: str, 
                           show_hidden: bool = False, detailed: bool = False) -> List[Dict]:
        """List the contents of a directory on a remote server.
        
        Args:
            connection_id: The connection ID to use
            directory_path: Path to the directory to list
            show_hidden: Whether to include hidden files (starting with .)
            detailed: Whether to include detailed file information
            
        Returns:
            List of dictionaries containing file/directory information
            
        Raises:
            SSHManagerError: If connection not found or directory operation fails
        """
        connection = self.connections.get(connection_id)
        if not connection:
            raise SSHManagerError(
                f"Connection {connection_id[:8]} not found",
                connection_id,
                "Connection may have been disconnected or never existed"
            )
        
        if not connection.connected:
            raise SSHManagerError(
                f"Connection {connection_id[:8]} is not active",
                connection_id,
                "Connection may have been lost or disconnected"
            )
        
        self.logger.debug(f"Listing directory on connection {connection_id[:8]}: {directory_path}")
        
        try:
            entries = await connection.list_directory(directory_path, show_hidden, detailed)
            return entries
            
        except ConnectionError as e:
            self.logger.error(f"Directory listing failed on connection {connection_id[:8]}: {e}")
            raise SSHManagerError(
                f"Directory listing failed on connection {connection_id[:8]}",
                connection_id,
                str(e)
            )

    async def cleanup_unhealthy_connections(self) -> int:
        """Remove connections that are no longer healthy.
        
        Returns:
            Number of connections that were cleaned up
        """
        unhealthy_connections = []
        
        # Identify unhealthy connections that cannot be recovered
        for connection_id, connection in self.connections.items():
            if not connection.connected:
                # Check if connection has auto-reconnect capability
                try:
                    auto_reconnect = getattr(connection, 'auto_reconnect', False)
                    # For mocks or connections without auto_reconnect, treat as no auto-reconnect
                    if not isinstance(auto_reconnect, bool):
                        auto_reconnect = False
                        
                    if not auto_reconnect:
                        unhealthy_connections.append(connection_id)
                    else:
                        # Check if connection has exhausted reconnection attempts
                        is_connection_lost = getattr(connection, 'is_connection_lost', False)
                        reconnect_attempts = getattr(connection, 'reconnect_attempts', 0)
                        max_reconnect_attempts = getattr(connection, '_max_reconnect_attempts', 3)
                        
                        # Ensure we have actual values, not mocks
                        if (isinstance(is_connection_lost, bool) and 
                            isinstance(reconnect_attempts, int) and 
                            isinstance(max_reconnect_attempts, int)):
                            
                            if is_connection_lost and reconnect_attempts >= max_reconnect_attempts:
                                # Connection has exhausted all reconnection attempts
                                unhealthy_connections.append(connection_id)
                except (TypeError, AttributeError):
                    # If we can't determine state, treat as unhealthy and clean up
                    unhealthy_connections.append(connection_id)
        
        # Remove unhealthy connections
        cleanup_count = 0
        for connection_id in unhealthy_connections:
            if await self.disconnect_connection(connection_id):
                cleanup_count += 1
        
        if cleanup_count > 0:
            self.logger.info(f"Cleaned up {cleanup_count} unhealthy connections")
        
        return cleanup_count
    
    async def enable_auto_reconnect(self, connection_id: str) -> bool:
        """Enable auto-reconnection for a specific connection.
        
        Args:
            connection_id: The connection ID to enable auto-reconnect for
            
        Returns:
            True if auto-reconnect was enabled, False if connection not found
        """
        connection = self.connections.get(connection_id)
        if not connection:
            self.logger.warning(f"Connection {connection_id[:8]} not found for auto-reconnect enable")
            return False
        
        connection.auto_reconnect = True
        self.logger.info(f"Auto-reconnect enabled for connection {connection_id[:8]}")
        return True
    
    async def disable_auto_reconnect(self, connection_id: str) -> bool:
        """Disable auto-reconnection for a specific connection.
        
        Args:
            connection_id: The connection ID to disable auto-reconnect for
            
        Returns:
            True if auto-reconnect was disabled, False if connection not found
        """
        connection = self.connections.get(connection_id)
        if not connection:
            self.logger.warning(f"Connection {connection_id[:8]} not found for auto-reconnect disable")
            return False
        
        connection.auto_reconnect = False
        self.logger.info(f"Auto-reconnect disabled for connection {connection_id[:8]}")
        return True
    
    async def force_reconnect(self, connection_id: str) -> bool:
        """Force a reconnection attempt for a specific connection.
        
        Args:
            connection_id: The connection ID to force reconnect
            
        Returns:
            True if reconnection was successful, False otherwise
        """
        connection = self.connections.get(connection_id)
        if not connection:
            self.logger.warning(f"Connection {connection_id[:8]} not found for force reconnect")
            return False
        
        self.logger.info(f"Forcing reconnection for connection {connection_id[:8]}")
        return await connection.force_reconnect()
    
    async def get_connection_status(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed status information for a connection including reconnection state.
        
        Args:
            connection_id: The connection ID to get status for
            
        Returns:
            Dictionary with connection status or None if not found
        """
        connection = self.connections.get(connection_id)
        if not connection:
            return None
        
        stats = await connection.get_connection_stats()
        
        # Add manager-level status information
        stats.update({
            "manager_running": self._running,
            "health_check_interval": self.health_check_interval,
            "in_connection_pool": True
        })
        
        return stats
    
    async def monitor_connections(self) -> Dict[str, Dict[str, Any]]:
        """Monitor all connections and return their status.
        
        Returns:
            Dictionary mapping connection IDs to their status information
        """
        connection_statuses = {}
        
        for connection_id, connection in self.connections.items():
            try:
                status = await self.get_connection_status(connection_id)
                if status:
                    connection_statuses[connection_id] = status
            except Exception as e:
                self.logger.error(f"Error getting status for connection {connection_id[:8]}: {e}")
                connection_statuses[connection_id] = {
                    "error": str(e),
                    "connection_id": connection_id,
                    "status_check_failed": True
                }
        
        return connection_statuses
    
    async def attempt_reconnect_all_lost(self) -> Dict[str, bool]:
        """Attempt to reconnect all connections that are marked as lost.
        
        Returns:
            Dictionary mapping connection IDs to reconnection success status
        """
        reconnect_results = {}
        lost_connections = []
        
        # Identify lost connections
        for connection_id, connection in self.connections.items():
            try:
                is_connection_lost = getattr(connection, 'is_connection_lost', False)
                auto_reconnect = getattr(connection, 'auto_reconnect', False)
                
                if (isinstance(is_connection_lost, bool) and 
                    isinstance(auto_reconnect, bool) and 
                    is_connection_lost and auto_reconnect):
                    lost_connections.append(connection_id)
            except (TypeError, AttributeError):
                pass
        
        if not lost_connections:
            self.logger.info("No lost connections found that need reconnection")
            return reconnect_results
        
        self.logger.info(f"Attempting to reconnect {len(lost_connections)} lost connections")
        
        # Attempt reconnection for each lost connection
        for connection_id in lost_connections:
            try:
                success = await self.force_reconnect(connection_id)
                reconnect_results[connection_id] = success
                
                if success:
                    self.logger.info(f"Successfully reconnected connection {connection_id[:8]}")
                else:
                    self.logger.warning(f"Failed to reconnect connection {connection_id[:8]}")
                    
            except Exception as e:
                self.logger.error(f"Error reconnecting connection {connection_id[:8]}: {e}")
                reconnect_results[connection_id] = False
        
        return reconnect_results
    
    async def _health_check_loop(self) -> None:
        """Background task that performs periodic health checks and monitors reconnections."""
        self.logger.info(f"Starting health check loop (interval: {self.health_check_interval}s)")
        
        while self._running:
            try:
                await asyncio.sleep(self.health_check_interval)
                
                if not self._running:
                    break
                
                if not self.connections:
                    continue
                
                self.logger.debug(f"Performing health checks on {len(self.connections)} connections")
                
                # Perform health checks
                health_results = await self.health_check_all()
                
                # Count connection states
                healthy_count = sum(1 for healthy in health_results.values() if healthy)
                total_count = len(health_results)
                lost_count = 0
                reconnecting_count = 0
                
                for conn in self.connections.values():
                    try:
                        is_lost = getattr(conn, 'is_connection_lost', False)
                        auto_reconnect = getattr(conn, 'auto_reconnect', False)
                        
                        if isinstance(is_lost, bool) and is_lost:
                            lost_count += 1
                            if isinstance(auto_reconnect, bool) and auto_reconnect:
                                reconnecting_count += 1
                    except (TypeError, AttributeError):
                        pass
                
                # Log detailed results
                if healthy_count < total_count:
                    self.logger.warning(
                        f"Health check results: {healthy_count}/{total_count} healthy, "
                        f"{lost_count} lost, {reconnecting_count} attempting reconnection"
                    )
                    
                    # Attempt reconnection for lost connections
                    if reconnecting_count > 0:
                        self.logger.info(f"Attempting reconnection for {reconnecting_count} lost connections")
                        reconnect_results = await self.attempt_reconnect_all_lost()
                        
                        successful_reconnects = sum(1 for success in reconnect_results.values() if success)
                        if successful_reconnects > 0:
                            self.logger.info(f"Successfully reconnected {successful_reconnects} connections")
                    
                    # Cleanup connections that cannot be recovered
                    cleanup_count = await self.cleanup_unhealthy_connections()
                    if cleanup_count > 0:
                        self.logger.info(f"Cleaned up {cleanup_count} unrecoverable connections")
                        
                else:
                    self.logger.debug(f"Health check results: {healthy_count}/{total_count} connections healthy")
                
                # Log connection monitoring summary
                if lost_count > 0 or reconnecting_count > 0:
                    connection_statuses = await self.monitor_connections()
                    self.logger.info(f"Connection monitoring: {len(connection_statuses)} connections monitored")
                
            except asyncio.CancelledError:
                self.logger.info("Health check loop cancelled")
                break
            
            except Exception as e:
                self.logger.error(f"Error in health check loop: {e}")
                # Continue running despite errors
    
    def __len__(self) -> int:
        """Return the number of active connections."""
        return len(self.connections)
    
    def __contains__(self, connection_id: str) -> bool:
        """Check if a connection ID exists in the manager."""
        return connection_id in self.connections
    
    def __str__(self) -> str:
        """String representation of the SSH Manager."""
        return f"SSHManager(connections={len(self.connections)}, max={self.max_connections}, running={self._running})"
    
    def __repr__(self) -> str:
        """Detailed string representation of the SSH Manager."""
        return (f"SSHManager(connections={len(self.connections)}, "
                f"max_connections={self.max_connections}, "
                f"running={self._running}, "
                f"total_created={self._total_connections_created})")