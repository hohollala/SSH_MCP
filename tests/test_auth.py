"""Unit tests for SSH Authentication Handler."""

import os
import tempfile
import unittest.mock
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import paramiko
import pytest

from ssh_mcp_server.auth import AuthenticationHandler, AuthenticationError
from ssh_mcp_server.models import SSHConfig


class TestAuthenticationHandler:
    """Test cases for AuthenticationHandler."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.auth_handler = AuthenticationHandler()
        self.mock_client = Mock(spec=paramiko.SSHClient)
    
    def test_init(self):
        """Test AuthenticationHandler initialization."""
        handler = AuthenticationHandler()
        assert handler is not None
        assert hasattr(handler, 'logger')
    
    def test_authenticate_unsupported_method(self):
        """Test authentication with unsupported method raises error."""
        # Create a valid config first, then modify the auth_method to bypass validation
        config = SSHConfig(
            hostname="example.com",
            username="testuser",
            auth_method="agent"
        )
        # Manually set unsupported method to bypass model validation
        config.auth_method = "unsupported"
        
        with pytest.raises(AuthenticationError) as exc_info:
            self.auth_handler.authenticate(self.mock_client, config)
        
        assert "Unsupported authentication method" in str(exc_info.value)
        assert exc_info.value.auth_method == "unsupported"


class TestKeyAuthentication:
    """Test cases for SSH key authentication."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.auth_handler = AuthenticationHandler()
        self.mock_client = Mock(spec=paramiko.SSHClient)
    
    def test_authenticate_with_key_success(self):
        """Test successful key authentication."""
        # Create a temporary key file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem') as temp_key:
            temp_key.write("-----BEGIN PRIVATE KEY-----\nfake_key_content\n-----END PRIVATE KEY-----")
            key_path = temp_key.name
        
        try:
            config = SSHConfig(
                hostname="example.com",
                username="testuser",
                auth_method="key",
                key_path=key_path
            )
            
            mock_key = Mock(spec=paramiko.RSAKey)
            
            with patch.object(self.auth_handler, '_load_private_key', return_value=mock_key):
                self.auth_handler.authenticate(self.mock_client, config)
            
            # Verify client.connect was called with correct parameters
            self.mock_client.connect.assert_called_once_with(
                hostname="example.com",
                port=22,
                username="testuser",
                pkey=mock_key,
                timeout=30,
                allow_agent=False,
                look_for_keys=False
            )
        finally:
            Path(key_path).unlink()
    
    def test_authenticate_with_key_no_key_path(self):
        """Test key authentication without key path raises error."""
        # Create a valid config first, then modify to bypass validation
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem') as temp_key:
            temp_key.write("-----BEGIN PRIVATE KEY-----\nfake_key_content\n-----END PRIVATE KEY-----")
            key_path = temp_key.name
        
        try:
            config = SSHConfig(
                hostname="example.com",
                username="testuser",
                auth_method="key",
                key_path=key_path
            )
            # Remove key_path to simulate missing configuration
            config.key_path = None
            
            with pytest.raises(AuthenticationError) as exc_info:
                self.auth_handler.authenticate(self.mock_client, config)
            
            assert "SSH key path is required" in str(exc_info.value)
            assert exc_info.value.auth_method == "key"
        finally:
            Path(key_path).unlink()
    
    def test_authenticate_with_key_file_not_found(self):
        """Test key authentication with non-existent key file raises error."""
        # Create a valid config first, then modify to bypass validation
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem') as temp_key:
            temp_key.write("-----BEGIN PRIVATE KEY-----\nfake_key_content\n-----END PRIVATE KEY-----")
            key_path = temp_key.name
        
        try:
            config = SSHConfig(
                hostname="example.com",
                username="testuser",
                auth_method="key",
                key_path=key_path
            )
            # Change to non-existent path after validation
            config.key_path = "/nonexistent/key/file"
            
            with pytest.raises(AuthenticationError) as exc_info:
                self.auth_handler.authenticate(self.mock_client, config)
            
            assert "SSH key file not found" in str(exc_info.value)
            assert exc_info.value.auth_method == "key"
        finally:
            Path(key_path).unlink()
    
    def test_authenticate_with_key_directory_instead_of_file(self):
        """Test key authentication with directory instead of file raises error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = SSHConfig(
                hostname="example.com",
                username="testuser",
                auth_method="key",
                key_path=temp_dir
            )
            
            with pytest.raises(AuthenticationError) as exc_info:
                self.auth_handler.authenticate(self.mock_client, config)
            
            assert "SSH key path is not a file" in str(exc_info.value)
            assert exc_info.value.auth_method == "key"
    
    def test_authenticate_with_encrypted_key(self):
        """Test key authentication with encrypted key raises error."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem') as temp_key:
            temp_key.write("-----BEGIN PRIVATE KEY-----\nfake_key_content\n-----END PRIVATE KEY-----")
            key_path = temp_key.name
        
        try:
            config = SSHConfig(
                hostname="example.com",
                username="testuser",
                auth_method="key",
                key_path=key_path
            )
            
            with patch.object(self.auth_handler, '_load_private_key', 
                            side_effect=paramiko.PasswordRequiredException("Key is encrypted")):
                with pytest.raises(AuthenticationError) as exc_info:
                    self.auth_handler.authenticate(self.mock_client, config)
                
                assert "encrypted and requires a passphrase" in str(exc_info.value)
                assert exc_info.value.auth_method == "key"
        finally:
            Path(key_path).unlink()
    
    def test_authenticate_with_key_connection_failure(self):
        """Test key authentication with connection failure raises error."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem') as temp_key:
            temp_key.write("-----BEGIN PRIVATE KEY-----\nfake_key_content\n-----END PRIVATE KEY-----")
            key_path = temp_key.name
        
        try:
            config = SSHConfig(
                hostname="example.com",
                username="testuser",
                auth_method="key",
                key_path=key_path
            )
            
            mock_key = Mock(spec=paramiko.RSAKey)
            
            with patch.object(self.auth_handler, '_load_private_key', return_value=mock_key):
                self.mock_client.connect.side_effect = paramiko.AuthenticationException("Auth failed")
                
                with pytest.raises(AuthenticationError) as exc_info:
                    self.auth_handler.authenticate(self.mock_client, config)
                
                assert "Authentication failed" in str(exc_info.value)
                assert exc_info.value.auth_method == "key"
        finally:
            Path(key_path).unlink()
    
    def test_load_private_key_rsa(self):
        """Test loading RSA private key."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem') as temp_key:
            temp_key.write("-----BEGIN RSA PRIVATE KEY-----\nfake_rsa_key\n-----END RSA PRIVATE KEY-----")
            key_path = Path(temp_key.name)
        
        try:
            mock_rsa_key = Mock(spec=paramiko.RSAKey)
            
            with patch('paramiko.RSAKey.from_private_key_file', return_value=mock_rsa_key):
                result = self.auth_handler._load_private_key(key_path)
                assert result == mock_rsa_key
        finally:
            key_path.unlink()
    
    def test_load_private_key_invalid(self):
        """Test loading invalid private key raises error."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem') as temp_key:
            temp_key.write("invalid key content")
            key_path = Path(temp_key.name)
        
        try:
            with patch('paramiko.RSAKey.from_private_key_file', 
                      side_effect=paramiko.SSHException("Invalid key")):
                with patch('paramiko.DSSKey.from_private_key_file', 
                          side_effect=paramiko.SSHException("Invalid key")):
                    with patch('paramiko.ECDSAKey.from_private_key_file', 
                              side_effect=paramiko.SSHException("Invalid key")):
                        with patch('paramiko.Ed25519Key.from_private_key_file', 
                                  side_effect=paramiko.SSHException("Invalid key")):
                            with pytest.raises(paramiko.SSHException):
                                self.auth_handler._load_private_key(key_path)
        finally:
            key_path.unlink()


class TestPasswordAuthentication:
    """Test cases for password authentication."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.auth_handler = AuthenticationHandler()
        self.mock_client = Mock(spec=paramiko.SSHClient)
    
    def test_authenticate_with_password_success(self):
        """Test successful password authentication."""
        config = SSHConfig(
            hostname="example.com",
            username="testuser",
            auth_method="password",
            password="secret123"
        )
        
        self.auth_handler.authenticate(self.mock_client, config)
        
        # Verify client.connect was called with correct parameters
        self.mock_client.connect.assert_called_once_with(
            hostname="example.com",
            port=22,
            username="testuser",
            password="secret123",
            timeout=30,
            allow_agent=False,
            look_for_keys=False
        )
    
    def test_authenticate_with_password_no_password(self):
        """Test password authentication without password raises error."""
        config = SSHConfig(
            hostname="example.com",
            username="testuser",
            auth_method="password",
            password="temp"
        )
        # Remove password to simulate missing configuration
        config.password = None
        
        with pytest.raises(AuthenticationError) as exc_info:
            self.auth_handler.authenticate(self.mock_client, config)
        
        assert "Password is required" in str(exc_info.value)
        assert exc_info.value.auth_method == "password"
    
    def test_authenticate_with_password_auth_failure(self):
        """Test password authentication with wrong credentials raises error."""
        config = SSHConfig(
            hostname="example.com",
            username="testuser",
            auth_method="password",
            password="wrongpassword"
        )
        
        self.mock_client.connect.side_effect = paramiko.AuthenticationException("Invalid credentials")
        
        with pytest.raises(AuthenticationError) as exc_info:
            self.auth_handler.authenticate(self.mock_client, config)
        
        assert "Invalid username or password" in str(exc_info.value)
        assert exc_info.value.auth_method == "password"


class TestAgentAuthentication:
    """Test cases for SSH agent authentication."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.auth_handler = AuthenticationHandler()
        self.mock_client = Mock(spec=paramiko.SSHClient)
    
    def test_authenticate_with_agent_success(self):
        """Test successful agent authentication."""
        config = SSHConfig(
            hostname="example.com",
            username="testuser",
            auth_method="agent"
        )
        
        with patch.object(self.auth_handler, '_is_ssh_agent_available', return_value=True):
            self.auth_handler.authenticate(self.mock_client, config)
        
        # Verify client.connect was called with correct parameters
        self.mock_client.connect.assert_called_once_with(
            hostname="example.com",
            port=22,
            username="testuser",
            timeout=30,
            allow_agent=True,
            look_for_keys=False
        )
    
    def test_authenticate_with_agent_not_available(self):
        """Test agent authentication when agent is not available raises error."""
        config = SSHConfig(
            hostname="example.com",
            username="testuser",
            auth_method="agent"
        )
        
        with patch.object(self.auth_handler, '_is_ssh_agent_available', return_value=False):
            with pytest.raises(AuthenticationError) as exc_info:
                self.auth_handler.authenticate(self.mock_client, config)
            
            assert "SSH agent is not available" in str(exc_info.value)
            assert exc_info.value.auth_method == "agent"
    
    def test_authenticate_with_agent_auth_failure(self):
        """Test agent authentication failure raises error."""
        config = SSHConfig(
            hostname="example.com",
            username="testuser",
            auth_method="agent"
        )
        
        with patch.object(self.auth_handler, '_is_ssh_agent_available', return_value=True):
            self.mock_client.connect.side_effect = paramiko.AuthenticationException("No suitable keys")
            
            with pytest.raises(AuthenticationError) as exc_info:
                self.auth_handler.authenticate(self.mock_client, config)
            
            assert "SSH agent authentication failed" in str(exc_info.value)
            assert exc_info.value.auth_method == "agent"
    
    def test_is_ssh_agent_available_no_auth_sock(self):
        """Test SSH agent availability when SSH_AUTH_SOCK is not set."""
        with patch.dict(os.environ, {}, clear=True):
            result = self.auth_handler._is_ssh_agent_available()
            assert result is False
    
    def test_is_ssh_agent_available_socket_not_exists(self):
        """Test SSH agent availability when socket doesn't exist."""
        with patch.dict(os.environ, {'SSH_AUTH_SOCK': '/nonexistent/socket'}):
            result = self.auth_handler._is_ssh_agent_available()
            assert result is False
    
    def test_is_ssh_agent_available_no_keys(self):
        """Test SSH agent availability when agent has no keys."""
        mock_agent = Mock()
        mock_agent.get_keys.return_value = []
        
        with patch.dict(os.environ, {'SSH_AUTH_SOCK': '/tmp/ssh-agent'}):
            with patch('os.path.exists', return_value=True):
                with patch('paramiko.Agent', return_value=mock_agent):
                    result = self.auth_handler._is_ssh_agent_available()
                    assert result is False
    
    def test_is_ssh_agent_available_with_keys(self):
        """Test SSH agent availability when agent has keys."""
        mock_key = Mock()
        mock_agent = Mock()
        mock_agent.get_keys.return_value = [mock_key]
        
        with patch.dict(os.environ, {'SSH_AUTH_SOCK': '/tmp/ssh-agent'}):
            with patch('os.path.exists', return_value=True):
                with patch('paramiko.Agent', return_value=mock_agent):
                    result = self.auth_handler._is_ssh_agent_available()
                    assert result is True
    
    def test_is_ssh_agent_available_connection_error(self):
        """Test SSH agent availability when connection to agent fails."""
        with patch.dict(os.environ, {'SSH_AUTH_SOCK': '/tmp/ssh-agent'}):
            with patch('os.path.exists', return_value=True):
                with patch('paramiko.Agent', side_effect=Exception("Connection failed")):
                    result = self.auth_handler._is_ssh_agent_available()
                    assert result is False


class TestConfigValidation:
    """Test cases for configuration validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.auth_handler = AuthenticationHandler()
    
    def test_validate_config_key_auth_valid(self):
        """Test validation of valid key authentication config."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem') as temp_key:
            temp_key.write("-----BEGIN PRIVATE KEY-----\nfake_key_content\n-----END PRIVATE KEY-----")
            key_path = temp_key.name
        
        try:
            config = SSHConfig(
                hostname="example.com",
                username="testuser",
                auth_method="key",
                key_path=key_path
            )
            
            mock_key = Mock(spec=paramiko.RSAKey)
            
            with patch.object(self.auth_handler, '_load_private_key', return_value=mock_key):
                is_valid, error_msg = self.auth_handler.validate_config(config)
                assert is_valid is True
                assert error_msg is None
        finally:
            Path(key_path).unlink()
    
    def test_validate_config_key_auth_no_key_path(self):
        """Test validation of key auth config without key path."""
        # Create a valid config first, then modify to bypass validation
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem') as temp_key:
            temp_key.write("-----BEGIN PRIVATE KEY-----\nfake_key_content\n-----END PRIVATE KEY-----")
            key_path = temp_key.name
        
        try:
            config = SSHConfig(
                hostname="example.com",
                username="testuser",
                auth_method="key",
                key_path=key_path
            )
            config.key_path = None
            
            is_valid, error_msg = self.auth_handler.validate_config(config)
            assert is_valid is False
            assert "SSH key path is required" in error_msg
        finally:
            Path(key_path).unlink()
    
    def test_validate_config_key_auth_file_not_found(self):
        """Test validation of key auth config with non-existent key file."""
        # Create a valid config first, then modify to bypass validation
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem') as temp_key:
            temp_key.write("-----BEGIN PRIVATE KEY-----\nfake_key_content\n-----END PRIVATE KEY-----")
            key_path = temp_key.name
        
        try:
            config = SSHConfig(
                hostname="example.com",
                username="testuser",
                auth_method="key",
                key_path=key_path
            )
            # Change to non-existent path after validation
            config.key_path = "/nonexistent/key/file"
            
            is_valid, error_msg = self.auth_handler.validate_config(config)
            assert is_valid is False
            assert "SSH key file not found" in error_msg
        finally:
            Path(key_path).unlink()
    
    def test_validate_config_key_auth_encrypted_key(self):
        """Test validation of key auth config with encrypted key."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem') as temp_key:
            temp_key.write("-----BEGIN PRIVATE KEY-----\nfake_key_content\n-----END PRIVATE KEY-----")
            key_path = temp_key.name
        
        try:
            config = SSHConfig(
                hostname="example.com",
                username="testuser",
                auth_method="key",
                key_path=key_path
            )
            
            with patch.object(self.auth_handler, '_load_private_key', 
                            side_effect=paramiko.PasswordRequiredException("Key is encrypted")):
                is_valid, error_msg = self.auth_handler.validate_config(config)
                assert is_valid is False
                assert "encrypted and requires a passphrase" in error_msg
        finally:
            Path(key_path).unlink()
    
    def test_validate_config_password_auth_valid(self):
        """Test validation of valid password authentication config."""
        config = SSHConfig(
            hostname="example.com",
            username="testuser",
            auth_method="password",
            password="secret123"
        )
        
        is_valid, error_msg = self.auth_handler.validate_config(config)
        assert is_valid is True
        assert error_msg is None
    
    def test_validate_config_password_auth_no_password(self):
        """Test validation of password auth config without password."""
        config = SSHConfig(
            hostname="example.com",
            username="testuser",
            auth_method="password",
            password="temp"
        )
        config.password = None
        
        is_valid, error_msg = self.auth_handler.validate_config(config)
        assert is_valid is False
        assert "Password is required" in error_msg
    
    def test_validate_config_agent_auth_valid(self):
        """Test validation of valid agent authentication config."""
        config = SSHConfig(
            hostname="example.com",
            username="testuser",
            auth_method="agent"
        )
        
        with patch.object(self.auth_handler, '_is_ssh_agent_available', return_value=True):
            is_valid, error_msg = self.auth_handler.validate_config(config)
            assert is_valid is True
            assert error_msg is None
    
    def test_validate_config_agent_auth_not_available(self):
        """Test validation of agent auth config when agent is not available."""
        config = SSHConfig(
            hostname="example.com",
            username="testuser",
            auth_method="agent"
        )
        
        with patch.object(self.auth_handler, '_is_ssh_agent_available', return_value=False):
            is_valid, error_msg = self.auth_handler.validate_config(config)
            assert is_valid is False
            assert "SSH agent is not available" in error_msg
    
    def test_validate_config_unsupported_method(self):
        """Test validation of config with unsupported auth method."""
        config = SSHConfig(
            hostname="example.com",
            username="testuser",
            auth_method="agent"
        )
        # Manually set unsupported method to bypass model validation
        config.auth_method = "unsupported"
        
        is_valid, error_msg = self.auth_handler.validate_config(config)
        assert is_valid is False
        assert "Unsupported authentication method" in error_msg


class TestAuthenticationError:
    """Test cases for AuthenticationError exception."""
    
    def test_authentication_error_creation(self):
        """Test creating AuthenticationError with all parameters."""
        error = AuthenticationError("Test message", "key", "Additional details")
        
        assert str(error) == "Test message"
        assert error.auth_method == "key"
        assert error.details == "Additional details"
    
    def test_authentication_error_without_details(self):
        """Test creating AuthenticationError without details."""
        error = AuthenticationError("Test message", "password")
        
        assert str(error) == "Test message"
        assert error.auth_method == "password"
        assert error.details is None