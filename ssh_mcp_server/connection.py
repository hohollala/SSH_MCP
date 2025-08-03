"""SSH Connection management for MCP Server."""

import asyncio
import logging
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

import paramiko
from paramiko import SSHClient, SSHException

from .models import SSHConfig, CommandResult, ConnectionInfo
from .auth import AuthenticationHandler, AuthenticationError


logger = logging.getLogger(__name__)


class ConnectionError(Exception):
    """Custom exception for connection-related errors."""
    
    def __init__(self, message: str, connection_id: Optional[str] = None, details: Optional[str] = None):
        """Initialize connection error.
        
        Args:
            message: Human-readable error message
            connection_id: ID of the connection that failed (if applicable)
            details: Additional error details
        """
        super().__init__(message)
        self.connection_id = connection_id
        self.details = details


class SSHConnection:
    """Manages a single SSH connection with health monitoring and resource cleanup."""
    
    def __init__(self, config: SSHConfig, connection_info: ConnectionInfo):
        """Initialize SSH connection.
        
        Args:
            config: SSH configuration for the connection
            connection_info: Connection metadata and state information
        """
        self.config = config
        self.connection_info = connection_info
        self.client: Optional[SSHClient] = None
        self.auth_handler = AuthenticationHandler()
        self.logger = logging.getLogger(__name__ + f".SSHConnection[{connection_info.connection_id[:8]}]")
        
        # Connection state tracking
        self._connected = False
        self._last_activity = datetime.now()
        self._connection_start_time: Optional[datetime] = None
        
        # Health check configuration
        self._health_check_interval = 30  # seconds
        self._health_check_timeout = 10   # seconds
        self._last_health_check: Optional[datetime] = None
        self._health_check_failures = 0
        self._max_health_check_failures = 3
        
        # Reconnection configuration
        self._auto_reconnect = True
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 3
        self._reconnect_delay = 5  # seconds
        self._reconnect_backoff_multiplier = 2
        self._last_reconnect_attempt: Optional[datetime] = None
        self._connection_lost_at: Optional[datetime] = None
    
    @property
    def connection_id(self) -> str:
        """Get the connection ID."""
        return self.connection_info.connection_id
    
    @property
    def connected(self) -> bool:
        """Check if the connection is currently active."""
        return self._connected and self.client is not None
    
    @property
    def last_activity(self) -> datetime:
        """Get the timestamp of the last activity on this connection."""
        return self._last_activity
    
    @property
    def connection_duration(self) -> Optional[timedelta]:
        """Get the duration since connection was established."""
        if self._connection_start_time:
            return datetime.now() - self._connection_start_time
        return None
    
    @property
    def auto_reconnect(self) -> bool:
        """Check if auto-reconnection is enabled."""
        return self._auto_reconnect
    
    @auto_reconnect.setter
    def auto_reconnect(self, value: bool) -> None:
        """Enable or disable auto-reconnection."""
        self._auto_reconnect = value
        self.logger.info(f"Auto-reconnect {'enabled' if value else 'disabled'}")
    
    @property
    def reconnect_attempts(self) -> int:
        """Get the number of reconnection attempts made."""
        return self._reconnect_attempts
    
    @property
    def is_connection_lost(self) -> bool:
        """Check if the connection is considered lost."""
        return self._connection_lost_at is not None
    
    async def connect(self) -> None:
        """Establish SSH connection.
        
        Raises:
            ConnectionError: If connection fails
        """
        if self.connected:
            self.logger.debug("Connection already established")
            return
        
        self.logger.info(f"Connecting to {self.config.username}@{self.config.hostname}:{self.config.port}")
        
        try:
            # Create new SSH client
            self.client = SSHClient()
            
            # Configure host key policy (for now, auto-add unknown hosts)
            # In production, this should be more restrictive
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Authenticate and connect
            self.auth_handler.authenticate(self.client, self.config)
            
            # Update connection state
            self._connected = True
            self._connection_start_time = datetime.now()
            self._last_activity = datetime.now()
            self._health_check_failures = 0
            
            # Update connection info
            self.connection_info.connected = True
            self.connection_info.update_last_used()
            
            self.logger.info(f"Successfully connected to {self.config.hostname}")
            
        except AuthenticationError as e:
            self.logger.error(f"Authentication failed: {e}")
            await self._cleanup_client()
            raise ConnectionError(
                f"Authentication failed for {self.config.username}@{self.config.hostname}",
                self.connection_id,
                str(e)
            )
        
        except (SSHException, OSError, Exception) as e:
            self.logger.error(f"Connection failed: {e}")
            await self._cleanup_client()
            raise ConnectionError(
                f"Failed to connect to {self.config.hostname}:{self.config.port}",
                self.connection_id,
                str(e)
            )
    
    async def disconnect(self) -> None:
        """Close SSH connection and cleanup resources."""
        self.logger.info(f"Disconnecting from {self.config.hostname}")
        
        try:
            await self._cleanup_client()
            
            # Update connection state
            self._connected = False
            self._connection_start_time = None
            self.connection_info.connected = False
            
            self.logger.info("Connection closed successfully")
            
        except Exception as e:
            self.logger.error(f"Error during disconnect: {e}")
            # Still mark as disconnected even if cleanup failed
            self._connected = False
            self.connection_info.connected = False
    
    async def execute_command(self, command: str, timeout: Optional[int] = None) -> CommandResult:
        """Execute a command on the remote server.
        
        Args:
            command: Command to execute
            timeout: Command timeout in seconds (uses config timeout if not specified)
            
        Returns:
            CommandResult with execution details
            
        Raises:
            ConnectionError: If connection is not established or command execution fails
        """
        if not self.connected:
            # Check if we should attempt reconnection
            if self._auto_reconnect and self.is_connection_lost:
                self.logger.info("Connection lost, attempting reconnection before command execution")
                if await self._attempt_reconnection():
                    self.logger.info("Reconnection successful, proceeding with command execution")
                else:
                    raise ConnectionError(
                        "Connection not established and reconnection failed",
                        self.connection_id,
                        "Unable to reconnect to execute command"
                    )
            else:
                raise ConnectionError(
                    "Connection not established",
                    self.connection_id,
                    "Call connect() first"
                )
        
        if not command.strip():
            raise ConnectionError(
                "Command cannot be empty",
                self.connection_id
            )
        
        # Detect connection loss before executing command
        if await self.detect_connection_loss():
            if self._auto_reconnect:
                self.logger.info("Connection loss detected, attempting reconnection")
                if await self._attempt_reconnection():
                    self.logger.info("Reconnection successful, proceeding with command execution")
                else:
                    raise ConnectionError(
                        "Connection lost and reconnection failed",
                        self.connection_id,
                        "Unable to reconnect to execute command"
                    )
            else:
                raise ConnectionError(
                    "Connection lost",
                    self.connection_id,
                    "Connection is no longer active"
                )
        
        self.logger.debug(f"Executing command: {command}")
        
        start_time = time.time()
        cmd_timeout = timeout or self.config.timeout
        
        try:
            # Execute command
            stdin, stdout, stderr = self.client.exec_command(
                command,
                timeout=cmd_timeout
            )
            
            # Read output
            stdout_data = stdout.read().decode('utf-8', errors='replace')
            stderr_data = stderr.read().decode('utf-8', errors='replace')
            exit_code = stdout.channel.recv_exit_status()
            
            execution_time = time.time() - start_time
            
            # Update activity timestamp
            self._last_activity = datetime.now()
            self.connection_info.update_last_used()
            
            result = CommandResult(
                stdout=stdout_data,
                stderr=stderr_data,
                exit_code=exit_code,
                execution_time=execution_time,
                command=command
            )
            
            self.logger.debug(f"Command completed with exit code {exit_code} in {execution_time:.2f}s")
            return result
            
        except (SSHException, OSError) as e:
            self.logger.error(f"SSH error executing command: {e}")
            
            # Check if this is a connection-related error
            if "Socket is closed" in str(e) or "Connection lost" in str(e) or "Broken pipe" in str(e):
                self.logger.warning("Connection-related error detected during command execution")
                await self._handle_connection_failure()
                
                # Attempt reconnection if enabled
                if self._auto_reconnect and await self._attempt_reconnection():
                    self.logger.info("Reconnected successfully, retrying command")
                    return await self.execute_command(command, timeout)
            
            raise ConnectionError(
                f"SSH error executing command: {command}",
                self.connection_id,
                str(e)
            )
        
        except Exception as e:
            self.logger.error(f"Unexpected error executing command: {e}")
            raise ConnectionError(
                f"Failed to execute command: {command}",
                self.connection_id,
                str(e)
            )
    
    async def health_check(self) -> bool:
        """Perform a health check on the connection.
        
        Returns:
            True if connection is healthy, False otherwise
        """
        if not self.connected:
            return False
        
        self.logger.debug("Performing health check")
        
        try:
            # Simple command to test connection
            result = await self.execute_command("echo 'health_check'", timeout=self._health_check_timeout)
            
            if result.success and "health_check" in result.stdout:
                self._last_health_check = datetime.now()
                self._health_check_failures = 0
                
                # Clear connection lost state if health check passes
                if self._connection_lost_at:
                    self.logger.info("Connection recovered after being lost")
                    self._connection_lost_at = None
                    self._reconnect_attempts = 0
                
                self.logger.debug("Health check passed")
                return True
            else:
                self._health_check_failures += 1
                self.logger.warning(f"Health check failed: unexpected output (failure #{self._health_check_failures})")
                await self._handle_connection_failure()
                return False
                
        except Exception as e:
            self._health_check_failures += 1
            self.logger.warning(f"Health check failed: {e} (failure #{self._health_check_failures})")
            await self._handle_connection_failure()
            return False
    
    async def _handle_connection_failure(self) -> None:
        """Handle connection failure and potentially trigger reconnection."""
        # If we've had too many failures, mark connection as lost
        if self._health_check_failures >= self._max_health_check_failures:
            if not self._connection_lost_at:
                self._connection_lost_at = datetime.now()
                self.logger.error(f"Connection lost after {self._health_check_failures} health check failures")
            
            self._connected = False
            self.connection_info.connected = False
            
            # Attempt reconnection if enabled
            if self._auto_reconnect and self._reconnect_attempts < self._max_reconnect_attempts:
                await self._attempt_reconnection()
    
    async def _attempt_reconnection(self) -> bool:
        """Attempt to reconnect to the SSH server.
        
        Returns:
            True if reconnection was successful, False otherwise
        """
        if not self._auto_reconnect:
            self.logger.debug("Auto-reconnect is disabled, skipping reconnection attempt")
            return False
        
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            self.logger.error(f"Maximum reconnection attempts ({self._max_reconnect_attempts}) reached")
            return False
        
        # Calculate delay with exponential backoff
        delay = self._reconnect_delay * (self._reconnect_backoff_multiplier ** self._reconnect_attempts)
        
        self.logger.info(f"Attempting reconnection #{self._reconnect_attempts + 1} in {delay} seconds")
        
        # Wait before attempting reconnection
        await asyncio.sleep(delay)
        
        self._reconnect_attempts += 1
        self._last_reconnect_attempt = datetime.now()
        
        try:
            # Clean up existing client
            await self._cleanup_client()
            
            # Reset connection state
            self._connected = False
            self._health_check_failures = 0
            
            # Attempt to reconnect
            await self.connect()
            
            if self._connected:  # Check the internal _connected flag
                self.logger.info(f"Reconnection successful after {self._reconnect_attempts} attempts")
                self._connection_lost_at = None
                self._reconnect_attempts = 0
                return True
            else:
                self.logger.warning(f"Reconnection attempt #{self._reconnect_attempts} failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Reconnection attempt #{self._reconnect_attempts} failed: {e}")
            
            # If we've exhausted all attempts, give up
            if self._reconnect_attempts >= self._max_reconnect_attempts:
                self.logger.error(f"All reconnection attempts exhausted. Connection permanently lost.")
                return False
            
            return False
    
    async def detect_connection_loss(self) -> bool:
        """Detect if the connection has been lost.
        
        This method performs a lightweight check to detect connection loss
        without the overhead of a full health check.
        
        Returns:
            True if connection loss is detected, False otherwise
        """
        if not self.client:
            if not self._connection_lost_at:
                self._connection_lost_at = datetime.now()
                self.logger.error("Connection loss detected: no client")
            return True
        
        try:
            # Check if the transport is still active
            transport = self.client.get_transport()
            if not transport or not transport.is_active():
                self.logger.warning("SSH transport is no longer active")
                if not self._connection_lost_at:
                    self._connection_lost_at = datetime.now()
                    self.logger.error("Connection loss detected via transport check")
                return True
            
            return False
            
        except Exception as e:
            self.logger.warning(f"Error checking connection status: {e}")
            if not self._connection_lost_at:
                self._connection_lost_at = datetime.now()
                self.logger.error("Connection loss detected via exception")
            return True
    
    async def force_reconnect(self) -> bool:
        """Force a reconnection attempt regardless of current state.
        
        Returns:
            True if reconnection was successful, False otherwise
        """
        self.logger.info("Forcing reconnection")
        
        # Mark connection as lost to trigger reconnection logic
        if not self._connection_lost_at:
            self._connection_lost_at = datetime.now()
        
        # Reset reconnection attempts to allow retry
        self._reconnect_attempts = 0
        
        return await self._attempt_reconnection()
    
    async def is_health_check_needed(self) -> bool:
        """Check if a health check is needed based on time since last check.
        
        Returns:
            True if health check is needed
        """
        if not self.connected:
            return False
        
        if self._last_health_check is None:
            return True
        
        time_since_check = datetime.now() - self._last_health_check
        return time_since_check.total_seconds() >= self._health_check_interval
    
    async def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics and status information.
        
        Returns:
            Dictionary with connection statistics
        """
        stats = {
            "connection_id": self.connection_id,
            "hostname": self.config.hostname,
            "username": self.config.username,
            "port": self.config.port,
            "connected": self.connected,
            "auth_method": self.config.auth_method,
            "created_at": self.connection_info.created_at.isoformat(),
            "last_used": self.connection_info.last_used.isoformat(),
            "last_activity": self._last_activity.isoformat(),
            "health_check_failures": self._health_check_failures,
            "connection_duration": None,
            "auto_reconnect": self._auto_reconnect,
            "reconnect_attempts": self._reconnect_attempts,
            "max_reconnect_attempts": self._max_reconnect_attempts,
            "is_connection_lost": self.is_connection_lost
        }
        
        if self.connection_duration:
            stats["connection_duration"] = str(self.connection_duration)
        
        if self._last_health_check:
            stats["last_health_check"] = self._last_health_check.isoformat()
        
        if self._connection_lost_at:
            stats["connection_lost_at"] = self._connection_lost_at.isoformat()
        
        if self._last_reconnect_attempt:
            stats["last_reconnect_attempt"] = self._last_reconnect_attempt.isoformat()
        
        return stats
    
    async def read_file(self, file_path: str, encoding: str = "utf-8") -> str:
        """Read the contents of a file on the remote server.
        
        Args:
            file_path: Path to the file to read
            encoding: Text encoding to use when reading the file
            
        Returns:
            File contents as string
            
        Raises:
            ConnectionError: If connection is not established or file operation fails
        """
        if not self.connected:
            raise ConnectionError(
                "Connection not established",
                self.connection_id,
                "Call connect() first"
            )
        
        if not file_path.strip():
            raise ConnectionError(
                "File path cannot be empty",
                self.connection_id
            )
        
        self.logger.debug(f"Reading file: {file_path}")
        
        try:
            # Use SFTP to read the file
            sftp = self.client.open_sftp()
            
            try:
                with sftp.open(file_path, 'r') as remote_file:
                    content = remote_file.read().decode(encoding)
                
                # Update activity timestamp
                self._last_activity = datetime.now()
                self.connection_info.update_last_used()
                
                self.logger.debug(f"Successfully read file: {file_path} ({len(content)} characters)")
                return content
                
            finally:
                sftp.close()
                
        except FileNotFoundError:
            raise ConnectionError(
                f"File not found: {file_path}",
                self.connection_id,
                "The specified file does not exist on the remote server"
            )
        
        except PermissionError:
            raise ConnectionError(
                f"Permission denied: {file_path}",
                self.connection_id,
                "Insufficient permissions to read the file"
            )
        
        except UnicodeDecodeError as e:
            raise ConnectionError(
                f"Encoding error reading file: {file_path}",
                self.connection_id,
                f"Cannot decode file with encoding '{encoding}': {e}"
            )
        
        except (SSHException, OSError) as e:
            self.logger.error(f"Error reading file {file_path}: {e}")
            raise ConnectionError(
                f"Failed to read file: {file_path}",
                self.connection_id,
                str(e)
            )
    
    async def write_file(self, file_path: str, content: str, encoding: str = "utf-8", 
                        create_dirs: bool = False) -> None:
        """Write content to a file on the remote server.
        
        Args:
            file_path: Path to the file to write
            content: Content to write to the file
            encoding: Text encoding to use when writing the file
            create_dirs: Whether to create parent directories if they don't exist
            
        Raises:
            ConnectionError: If connection is not established or file operation fails
        """
        if not self.connected:
            raise ConnectionError(
                "Connection not established",
                self.connection_id,
                "Call connect() first"
            )
        
        if not file_path.strip():
            raise ConnectionError(
                "File path cannot be empty",
                self.connection_id
            )
        
        self.logger.debug(f"Writing file: {file_path} ({len(content)} characters)")
        
        try:
            # Use SFTP to write the file
            sftp = self.client.open_sftp()
            
            try:
                # Create parent directories if requested
                if create_dirs:
                    import posixpath
                    parent_dir = posixpath.dirname(file_path)
                    if parent_dir and parent_dir != '/':
                        try:
                            # Try to create the directory structure
                            await self.execute_command(f"mkdir -p '{parent_dir}'")
                        except Exception as e:
                            self.logger.warning(f"Could not create parent directories for {file_path}: {e}")
                
                # Write the file
                with sftp.open(file_path, 'w') as remote_file:
                    remote_file.write(content.encode(encoding))
                
                # Update activity timestamp
                self._last_activity = datetime.now()
                self.connection_info.update_last_used()
                
                self.logger.debug(f"Successfully wrote file: {file_path}")
                
            finally:
                sftp.close()
                
        except PermissionError:
            raise ConnectionError(
                f"Permission denied: {file_path}",
                self.connection_id,
                "Insufficient permissions to write the file"
            )
        
        except UnicodeEncodeError as e:
            raise ConnectionError(
                f"Encoding error writing file: {file_path}",
                self.connection_id,
                f"Cannot encode content with encoding '{encoding}': {e}"
            )
        
        except (SSHException, OSError) as e:
            self.logger.error(f"Error writing file {file_path}: {e}")
            raise ConnectionError(
                f"Failed to write file: {file_path}",
                self.connection_id,
                str(e)
            )
    
    async def list_directory(self, directory_path: str, show_hidden: bool = False, 
                           detailed: bool = False) -> List[Dict[str, Any]]:
        """List the contents of a directory on the remote server.
        
        Args:
            directory_path: Path to the directory to list
            show_hidden: Whether to include hidden files (starting with .)
            detailed: Whether to include detailed file information
            
        Returns:
            List of dictionaries containing file/directory information
            
        Raises:
            ConnectionError: If connection is not established or directory operation fails
        """
        if not self.connected:
            raise ConnectionError(
                "Connection not established",
                self.connection_id,
                "Call connect() first"
            )
        
        if not directory_path.strip():
            raise ConnectionError(
                "Directory path cannot be empty",
                self.connection_id
            )
        
        self.logger.debug(f"Listing directory: {directory_path}")
        
        try:
            # Use SFTP to list the directory
            sftp = self.client.open_sftp()
            
            try:
                # Get directory listing
                entries = []
                
                if detailed:
                    # Use listdir_attr for detailed information
                    for attr in sftp.listdir_attr(directory_path):
                        # Skip hidden files if not requested
                        if not show_hidden and attr.filename.startswith('.'):
                            continue
                        
                        entry = {
                            "name": attr.filename,
                            "type": "directory" if attr.st_mode and (attr.st_mode & 0o040000) else "file",
                            "size": attr.st_size if attr.st_size is not None else 0,
                            "permissions": oct(attr.st_mode)[-3:] if attr.st_mode else "000",
                            "modified": datetime.fromtimestamp(attr.st_mtime).isoformat() if attr.st_mtime else None,
                            "owner_id": attr.st_uid if attr.st_uid is not None else None,
                            "group_id": attr.st_gid if attr.st_gid is not None else None
                        }
                        entries.append(entry)
                else:
                    # Use simple listdir for basic listing
                    for filename in sftp.listdir(directory_path):
                        # Skip hidden files if not requested
                        if not show_hidden and filename.startswith('.'):
                            continue
                        
                        entry = {
                            "name": filename,
                            "type": "unknown"  # We don't know if it's a file or directory without stat
                        }
                        entries.append(entry)
                
                # Sort entries by name
                entries.sort(key=lambda x: x["name"])
                
                # Update activity timestamp
                self._last_activity = datetime.now()
                self.connection_info.update_last_used()
                
                self.logger.debug(f"Successfully listed directory: {directory_path} ({len(entries)} entries)")
                return entries
                
            finally:
                sftp.close()
                
        except FileNotFoundError:
            raise ConnectionError(
                f"Directory not found: {directory_path}",
                self.connection_id,
                "The specified directory does not exist on the remote server"
            )
        
        except PermissionError:
            raise ConnectionError(
                f"Permission denied: {directory_path}",
                self.connection_id,
                "Insufficient permissions to list the directory"
            )
        
        except (SSHException, OSError) as e:
            self.logger.error(f"Error listing directory {directory_path}: {e}")
            raise ConnectionError(
                f"Failed to list directory: {directory_path}",
                self.connection_id,
                str(e)
            )

    async def _cleanup_client(self) -> None:
        """Clean up SSH client resources."""
        if self.client:
            try:
                self.client.close()
            except Exception as e:
                self.logger.warning(f"Error closing SSH client: {e}")
            finally:
                self.client = None
    
    def __str__(self) -> str:
        """String representation of the connection."""
        status = "connected" if self.connected else "disconnected"
        return f"SSHConnection({self.config.username}@{self.config.hostname}:{self.config.port}, {status})"
    
    def __repr__(self) -> str:
        """Detailed string representation of the connection."""
        return (f"SSHConnection(id={self.connection_id[:8]}, "
                f"host={self.config.hostname}, "
                f"user={self.config.username}, "
                f"port={self.config.port}, "
                f"connected={self.connected})")