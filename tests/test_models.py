"""Unit tests for SSH MCP Server data models."""

import pytest
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

from ssh_mcp_server.models import SSHConfig, CommandResult, ConnectionInfo


class TestSSHConfig:
    """Test cases for SSHConfig data model."""

    def test_valid_ssh_config_with_key(self):
        """Test creating a valid SSH config with key authentication."""
        # Create a temporary key file
        with tempfile.NamedTemporaryFile(delete=False) as temp_key:
            temp_key.write(b"dummy key content")
            key_path = temp_key.name

        try:
            config = SSHConfig(
                hostname="example.com",
                username="testuser",
                port=22,
                auth_method="key",
                key_path=key_path,
                timeout=30
            )
            
            assert config.hostname == "example.com"
            assert config.username == "testuser"
            assert config.port == 22
            assert config.auth_method == "key"
            assert config.key_path == key_path
            assert config.timeout == 30
        finally:
            Path(key_path).unlink()

    def test_valid_ssh_config_with_password(self):
        """Test creating a valid SSH config with password authentication."""
        config = SSHConfig(
            hostname="192.168.1.100",
            username="admin",
            port=2222,
            auth_method="password",
            password="secret123",
            timeout=60
        )
        
        assert config.hostname == "192.168.1.100"
        assert config.username == "admin"
        assert config.port == 2222
        assert config.auth_method == "password"
        assert config.password == "secret123"
        assert config.timeout == 60

    def test_valid_ssh_config_with_agent(self):
        """Test creating a valid SSH config with agent authentication."""
        config = SSHConfig(
            hostname="server.local",
            username="developer",
            auth_method="agent"
        )
        
        assert config.hostname == "server.local"
        assert config.username == "developer"
        assert config.port == 22  # default
        assert config.auth_method == "agent"
        assert config.timeout == 30  # default

    def test_empty_hostname_raises_error(self):
        """Test that empty hostname raises ValueError."""
        with pytest.raises(ValueError, match="Hostname cannot be empty"):
            SSHConfig(hostname="", username="testuser")

    def test_empty_username_raises_error(self):
        """Test that empty username raises ValueError."""
        with pytest.raises(ValueError, match="Username cannot be empty"):
            SSHConfig(hostname="example.com", username="")

    def test_invalid_port_raises_error(self):
        """Test that invalid port raises ValueError."""
        with pytest.raises(ValueError, match="Port must be an integer between 1 and 65535"):
            SSHConfig(hostname="example.com", username="testuser", port=0)
        
        with pytest.raises(ValueError, match="Port must be an integer between 1 and 65535"):
            SSHConfig(hostname="example.com", username="testuser", port=65536)

    def test_invalid_auth_method_raises_error(self):
        """Test that invalid auth_method raises ValueError."""
        with pytest.raises(ValueError, match="Invalid auth_method"):
            SSHConfig(hostname="example.com", username="testuser", auth_method="invalid")

    def test_key_auth_without_key_path_raises_error(self):
        """Test that key auth without key_path raises ValueError."""
        with pytest.raises(ValueError, match="key_path is required when auth_method is 'key'"):
            SSHConfig(hostname="example.com", username="testuser", auth_method="key")

    def test_key_auth_with_nonexistent_key_raises_error(self):
        """Test that key auth with non-existent key file raises ValueError."""
        with pytest.raises(ValueError, match="SSH key file not found"):
            SSHConfig(
                hostname="example.com",
                username="testuser",
                auth_method="key",
                key_path="/nonexistent/key/file"
            )

    def test_password_auth_without_password_raises_error(self):
        """Test that password auth without password raises ValueError."""
        with pytest.raises(ValueError, match="password is required when auth_method is 'password'"):
            SSHConfig(hostname="example.com", username="testuser", auth_method="password")

    def test_invalid_timeout_raises_error(self):
        """Test that invalid timeout raises ValueError."""
        with pytest.raises(ValueError, match="Timeout must be a positive integer"):
            SSHConfig(hostname="example.com", username="testuser", timeout=0)
        
        with pytest.raises(ValueError, match="Timeout must be a positive integer"):
            SSHConfig(hostname="example.com", username="testuser", timeout=-1)

    def test_invalid_hostname_format_raises_error(self):
        """Test that invalid hostname format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid hostname format"):
            SSHConfig(hostname="invalid..hostname", username="testuser")

    def test_valid_ip_address_hostname(self):
        """Test that valid IP address is accepted as hostname."""
        config = SSHConfig(
            hostname="192.168.1.1",
            username="testuser",
            auth_method="agent"
        )
        assert config.hostname == "192.168.1.1"


class TestCommandResult:
    """Test cases for CommandResult data model."""

    def test_valid_command_result(self):
        """Test creating a valid command result."""
        result = CommandResult(
            stdout="Hello World",
            stderr="",
            exit_code=0,
            execution_time=1.5,
            command="echo 'Hello World'"
        )
        
        assert result.stdout == "Hello World"
        assert result.stderr == ""
        assert result.exit_code == 0
        assert result.execution_time == 1.5
        assert result.command == "echo 'Hello World'"
        assert isinstance(result.timestamp, datetime)

    def test_command_result_with_error(self):
        """Test creating a command result with error."""
        result = CommandResult(
            stdout="",
            stderr="Command not found",
            exit_code=127,
            execution_time=0.1
        )
        
        assert result.stdout == ""
        assert result.stderr == "Command not found"
        assert result.exit_code == 127
        assert result.execution_time == 0.1

    def test_success_property(self):
        """Test the success property."""
        success_result = CommandResult("output", "", 0, 1.0)
        assert success_result.success is True
        
        error_result = CommandResult("", "error", 1, 1.0)
        assert error_result.success is False

    def test_has_output_property(self):
        """Test the has_output property."""
        with_output = CommandResult("some output", "", 0, 1.0)
        assert with_output.has_output is True
        
        with_stderr = CommandResult("", "some error", 1, 1.0)
        assert with_stderr.has_output is True
        
        no_output = CommandResult("", "", 0, 1.0)
        assert no_output.has_output is False

    def test_invalid_exit_code_raises_error(self):
        """Test that invalid exit_code raises ValueError."""
        with pytest.raises(ValueError, match="exit_code must be an integer"):
            CommandResult("output", "", "invalid", 1.0)

    def test_invalid_execution_time_raises_error(self):
        """Test that invalid execution_time raises ValueError."""
        with pytest.raises(ValueError, match="execution_time must be a non-negative number"):
            CommandResult("output", "", 0, -1.0)

    def test_invalid_stdout_type_raises_error(self):
        """Test that invalid stdout type raises ValueError."""
        with pytest.raises(ValueError, match="stdout must be a string"):
            CommandResult(123, "", 0, 1.0)

    def test_invalid_stderr_type_raises_error(self):
        """Test that invalid stderr type raises ValueError."""
        with pytest.raises(ValueError, match="stderr must be a string"):
            CommandResult("output", 123, 0, 1.0)


class TestConnectionInfo:
    """Test cases for ConnectionInfo data model."""

    def test_valid_connection_info(self):
        """Test creating valid connection info."""
        connection_id = str(uuid.uuid4())
        now = datetime.now()
        
        info = ConnectionInfo(
            connection_id=connection_id,
            hostname="example.com",
            username="testuser",
            port=22,
            connected=True,
            created_at=now,
            last_used=now
        )
        
        assert info.connection_id == connection_id
        assert info.hostname == "example.com"
        assert info.username == "testuser"
        assert info.port == 22
        assert info.connected is True
        assert info.created_at == now
        assert info.last_used == now

    def test_create_class_method(self):
        """Test the create class method."""
        info = ConnectionInfo.create("server.com", "user", 2222)
        
        assert info.hostname == "server.com"
        assert info.username == "user"
        assert info.port == 2222
        assert info.connected is False
        assert isinstance(info.created_at, datetime)
        assert isinstance(info.last_used, datetime)
        
        # Verify connection_id is a valid UUID
        uuid.UUID(info.connection_id)  # Should not raise

    def test_update_last_used(self):
        """Test updating last_used timestamp."""
        info = ConnectionInfo.create("example.com", "testuser")
        original_time = info.last_used
        
        # Wait a small amount to ensure time difference
        import time
        time.sleep(0.01)
        
        info.update_last_used()
        assert info.last_used > original_time

    def test_empty_connection_id_raises_error(self):
        """Test that empty connection_id raises ValueError."""
        with pytest.raises(ValueError, match="connection_id cannot be empty"):
            ConnectionInfo("", "example.com", "testuser", 22, True)

    def test_invalid_connection_id_format_raises_error(self):
        """Test that invalid connection_id format raises ValueError."""
        with pytest.raises(ValueError, match="connection_id must be a valid UUID"):
            ConnectionInfo("invalid-uuid", "example.com", "testuser", 22, True)

    def test_empty_hostname_raises_error(self):
        """Test that empty hostname raises ValueError."""
        connection_id = str(uuid.uuid4())
        with pytest.raises(ValueError, match="hostname cannot be empty"):
            ConnectionInfo(connection_id, "", "testuser", 22, True)

    def test_empty_username_raises_error(self):
        """Test that empty username raises ValueError."""
        connection_id = str(uuid.uuid4())
        with pytest.raises(ValueError, match="username cannot be empty"):
            ConnectionInfo(connection_id, "example.com", "", 22, True)

    def test_invalid_port_raises_error(self):
        """Test that invalid port raises ValueError."""
        connection_id = str(uuid.uuid4())
        with pytest.raises(ValueError, match="port must be an integer between 1 and 65535"):
            ConnectionInfo(connection_id, "example.com", "testuser", 0, True)

    def test_invalid_connected_type_raises_error(self):
        """Test that invalid connected type raises ValueError."""
        connection_id = str(uuid.uuid4())
        with pytest.raises(ValueError, match="connected must be a boolean"):
            ConnectionInfo(connection_id, "example.com", "testuser", 22, "true")

    def test_invalid_datetime_types_raise_error(self):
        """Test that invalid datetime types raise ValueError."""
        connection_id = str(uuid.uuid4())
        
        with pytest.raises(ValueError, match="created_at must be a datetime object"):
            ConnectionInfo(
                connection_id, "example.com", "testuser", 22, True,
                created_at="invalid", last_used=datetime.now()
            )
        
        with pytest.raises(ValueError, match="last_used must be a datetime object"):
            ConnectionInfo(
                connection_id, "example.com", "testuser", 22, True,
                created_at=datetime.now(), last_used="invalid"
            )