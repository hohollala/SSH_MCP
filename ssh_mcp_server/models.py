"""Data models for SSH MCP Server."""

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Union


@dataclass
class SSHConfig:
    """Configuration for SSH connection.
    
    Attributes:
        hostname: The hostname or IP address of the SSH server
        username: The username for SSH authentication
        port: The SSH port (default: 22)
        auth_method: Authentication method ('key', 'password', 'agent')
        key_path: Path to SSH private key file (required for 'key' auth)
        password: Password for authentication (required for 'password' auth)
        timeout: Connection timeout in seconds (default: 30)
    """
    hostname: str
    username: str
    port: int = 22
    auth_method: str = "agent"
    key_path: Optional[str] = None
    password: Optional[str] = None
    timeout: int = 30

    def __post_init__(self):
        """Validate SSH configuration after initialization."""
        self._validate_hostname()
        self._validate_username()
        self._validate_port()
        self._validate_auth_method()
        self._validate_timeout()
        self._validate_auth_requirements()

    def _validate_hostname(self):
        """Validate hostname format."""
        if not self.hostname or not self.hostname.strip():
            raise ValueError("Hostname cannot be empty")
        
        # Check for invalid patterns like double dots
        if '..' in self.hostname:
            raise ValueError("Invalid hostname format")
        
        # Check if it's an IP address
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if re.match(ip_pattern, self.hostname):
            # Validate IP address ranges
            parts = self.hostname.split('.')
            for part in parts:
                if not (0 <= int(part) <= 255):
                    raise ValueError("Invalid IP address format")
            return
        
        # Basic hostname validation for domain names
        hostname_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-\.]*[a-zA-Z0-9])?$'
        if not re.match(hostname_pattern, self.hostname):
            raise ValueError("Invalid hostname format")

    def _validate_username(self):
        """Validate username."""
        if not self.username or not self.username.strip():
            raise ValueError("Username cannot be empty")

    def _validate_port(self):
        """Validate port number."""
        if not isinstance(self.port, int) or not (1 <= self.port <= 65535):
            raise ValueError("Port must be an integer between 1 and 65535")

    def _validate_auth_method(self):
        """Validate authentication method."""
        valid_methods = {"key", "password", "agent"}
        if self.auth_method not in valid_methods:
            raise ValueError(f"Invalid auth_method. Must be one of: {', '.join(valid_methods)}")

    def _validate_timeout(self):
        """Validate timeout value."""
        if not isinstance(self.timeout, int) or self.timeout <= 0:
            raise ValueError("Timeout must be a positive integer")

    def _validate_auth_requirements(self):
        """Validate authentication method specific requirements."""
        if self.auth_method == "key":
            if not self.key_path:
                raise ValueError("key_path is required when auth_method is 'key'")
            
            key_file = Path(self.key_path)
            if not key_file.exists():
                raise ValueError(f"SSH key file not found: {self.key_path}")
        
        elif self.auth_method == "password":
            if not self.password:
                raise ValueError("password is required when auth_method is 'password'")


@dataclass
class CommandResult:
    """Result of a command execution.
    
    Attributes:
        stdout: Standard output from the command
        stderr: Standard error from the command
        exit_code: Exit code of the command
        execution_time: Time taken to execute the command in seconds
        command: The command that was executed (optional)
        timestamp: When the command was executed
    """
    stdout: str
    stderr: str
    exit_code: int
    execution_time: float
    command: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validate command result after initialization."""
        self._validate_stdout()
        self._validate_stderr()
        self._validate_exit_code()
        self._validate_execution_time()

    def _validate_stdout(self):
        """Validate stdout is a string."""
        if not isinstance(self.stdout, str):
            raise ValueError("stdout must be a string")

    def _validate_stderr(self):
        """Validate stderr is a string."""
        if not isinstance(self.stderr, str):
            raise ValueError("stderr must be a string")

    def _validate_exit_code(self):
        """Validate exit_code is an integer."""
        if not isinstance(self.exit_code, int):
            raise ValueError("exit_code must be an integer")

    def _validate_execution_time(self):
        """Validate execution_time is a non-negative number."""
        if not isinstance(self.execution_time, (int, float)) or self.execution_time < 0:
            raise ValueError("execution_time must be a non-negative number")

    @property
    def success(self) -> bool:
        """Return True if the command executed successfully (exit_code == 0)."""
        return self.exit_code == 0

    @property
    def has_output(self) -> bool:
        """Return True if the command produced any output (stdout or stderr)."""
        return bool(self.stdout.strip() or self.stderr.strip())


@dataclass
class ConnectionInfo:
    """Information about an SSH connection.
    
    Attributes:
        connection_id: Unique identifier for the connection
        hostname: The hostname of the SSH server
        username: The username used for the connection
        port: The SSH port used
        connected: Whether the connection is currently active
        created_at: When the connection was created
        last_used: When the connection was last used
    """
    connection_id: str
    hostname: str
    username: str
    port: int
    connected: bool
    created_at: datetime = field(default_factory=datetime.now)
    last_used: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validate connection info after initialization."""
        self._validate_connection_id()
        self._validate_hostname()
        self._validate_username()
        self._validate_port()
        self._validate_connected()
        self._validate_datetime_fields()

    def _validate_connection_id(self):
        """Validate connection_id format."""
        if not self.connection_id or not self.connection_id.strip():
            raise ValueError("connection_id cannot be empty")
        
        # Validate UUID format
        try:
            uuid.UUID(self.connection_id)
        except ValueError:
            raise ValueError("connection_id must be a valid UUID")

    def _validate_hostname(self):
        """Validate hostname."""
        if not self.hostname or not self.hostname.strip():
            raise ValueError("hostname cannot be empty")

    def _validate_username(self):
        """Validate username."""
        if not self.username or not self.username.strip():
            raise ValueError("username cannot be empty")

    def _validate_port(self):
        """Validate port number."""
        if not isinstance(self.port, int) or not (1 <= self.port <= 65535):
            raise ValueError("port must be an integer between 1 and 65535")

    def _validate_connected(self):
        """Validate connected field."""
        if not isinstance(self.connected, bool):
            raise ValueError("connected must be a boolean")

    def _validate_datetime_fields(self):
        """Validate datetime fields."""
        if not isinstance(self.created_at, datetime):
            raise ValueError("created_at must be a datetime object")
        
        if not isinstance(self.last_used, datetime):
            raise ValueError("last_used must be a datetime object")

    @classmethod
    def create(cls, hostname: str, username: str, port: int = 22) -> 'ConnectionInfo':
        """Create a new ConnectionInfo with generated UUID and current timestamp.
        
        Args:
            hostname: The hostname of the SSH server
            username: The username for the connection
            port: The SSH port (default: 22)
            
        Returns:
            A new ConnectionInfo instance
        """
        connection_id = str(uuid.uuid4())
        now = datetime.now()
        
        return cls(
            connection_id=connection_id,
            hostname=hostname,
            username=username,
            port=port,
            connected=False,
            created_at=now,
            last_used=now
        )

    def update_last_used(self):
        """Update the last_used timestamp to the current time."""
        self.last_used = datetime.now()