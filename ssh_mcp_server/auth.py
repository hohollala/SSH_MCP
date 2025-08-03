"""SSH Authentication Handler for MCP Server."""

import logging
import os
from pathlib import Path
from typing import Optional, Tuple

import paramiko
from paramiko import SSHClient, AuthenticationException, SSHException

from .models import SSHConfig


logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Custom exception for authentication failures."""
    
    def __init__(self, message: str, auth_method: str, details: Optional[str] = None):
        """Initialize authentication error.
        
        Args:
            message: Human-readable error message
            auth_method: The authentication method that failed
            details: Additional error details
        """
        super().__init__(message)
        self.auth_method = auth_method
        self.details = details


class AuthenticationHandler:
    """Handles SSH authentication using various methods."""
    
    def __init__(self):
        """Initialize the authentication handler."""
        self.logger = logging.getLogger(__name__ + ".AuthenticationHandler")
    
    def authenticate(self, client: SSHClient, config: SSHConfig) -> None:
        """Authenticate SSH client using the specified configuration.
        
        Args:
            client: The paramiko SSHClient instance
            config: SSH configuration containing authentication details
            
        Raises:
            AuthenticationError: If authentication fails
        """
        self.logger.debug(f"Attempting {config.auth_method} authentication for {config.username}@{config.hostname}")
        
        try:
            if config.auth_method == "key":
                self._authenticate_with_key(client, config)
            elif config.auth_method == "password":
                self._authenticate_with_password(client, config)
            elif config.auth_method == "agent":
                self._authenticate_with_agent(client, config)
            else:
                raise AuthenticationError(
                    f"Unsupported authentication method: {config.auth_method}",
                    config.auth_method
                )
            
            self.logger.info(f"Successfully authenticated {config.username}@{config.hostname} using {config.auth_method}")
            
        except AuthenticationError:
            # Re-raise AuthenticationError as-is (from the specific auth methods)
            raise
        
        except AuthenticationException as e:
            if config.auth_method == "password":
                error_msg = f"Invalid username or password for {config.username}@{config.hostname}"
                details = "Credentials rejected by server"
            elif config.auth_method == "agent":
                error_msg = f"SSH agent authentication failed for {config.username}@{config.hostname}"
                details = "No suitable keys found in SSH agent or keys rejected by server"
            else:  # key authentication
                error_msg = f"Authentication failed for {config.username}@{config.hostname} using {config.auth_method}"
                details = str(e)
            
            self.logger.error(f"{error_msg}: {str(e)}")
            raise AuthenticationError(error_msg, config.auth_method, details)
        
        except SSHException as e:
            error_msg = f"SSH error during {config.auth_method} authentication"
            self.logger.error(f"{error_msg}: {str(e)}")
            raise AuthenticationError(error_msg, config.auth_method, str(e))
        
        except Exception as e:
            error_msg = f"Unexpected error during {config.auth_method} authentication"
            self.logger.error(f"{error_msg}: {str(e)}")
            raise AuthenticationError(error_msg, config.auth_method, str(e))
    
    def _authenticate_with_key(self, client: SSHClient, config: SSHConfig) -> None:
        """Authenticate using SSH private key.
        
        Args:
            client: The paramiko SSHClient instance
            config: SSH configuration with key authentication details
            
        Raises:
            AuthenticationError: If key authentication fails
        """
        if not config.key_path:
            raise AuthenticationError("SSH key path is required for key authentication", "key")
        
        key_path = Path(config.key_path).expanduser()
        
        if not key_path.exists():
            raise AuthenticationError(f"SSH key file not found: {key_path}", "key")
        
        if not key_path.is_file():
            raise AuthenticationError(f"SSH key path is not a file: {key_path}", "key")
        
        # Check file permissions (should be readable only by owner)
        try:
            stat_info = key_path.stat()
            if stat_info.st_mode & 0o077:  # Check if group/other have any permissions
                self.logger.warning(f"SSH key file {key_path} has overly permissive permissions")
        except OSError as e:
            self.logger.warning(f"Could not check permissions for {key_path}: {e}")
        
        try:
            # Try to load the key and determine its type
            key = self._load_private_key(key_path)
            
            self.logger.debug(f"Loaded {type(key).__name__} from {key_path}")
            
            # Attempt authentication with the loaded key
            client.connect(
                hostname=config.hostname,
                port=config.port,
                username=config.username,
                pkey=key,
                timeout=config.timeout,
                allow_agent=False,  # Don't fall back to agent
                look_for_keys=False  # Don't look for other keys
            )
            
        except paramiko.PasswordRequiredException:
            raise AuthenticationError(
                f"SSH key {key_path} is encrypted and requires a passphrase",
                "key",
                "Key file is password protected"
            )
        
        except paramiko.AuthenticationException:
            # Let this bubble up to be handled by the main authenticate method
            raise
        
        except (paramiko.SSHException, OSError) as e:
            raise AuthenticationError(
                f"Failed to load or use SSH key {key_path}",
                "key",
                str(e)
            )
    
    def _authenticate_with_password(self, client: SSHClient, config: SSHConfig) -> None:
        """Authenticate using username and password.
        
        Args:
            client: The paramiko SSHClient instance
            config: SSH configuration with password authentication details
            
        Raises:
            AuthenticationError: If password authentication fails
        """
        if not config.password:
            raise AuthenticationError("Password is required for password authentication", "password")
        
        try:
            client.connect(
                hostname=config.hostname,
                port=config.port,
                username=config.username,
                password=config.password,
                timeout=config.timeout,
                allow_agent=False,  # Don't fall back to agent
                look_for_keys=False  # Don't look for keys
            )
            
        except AuthenticationException:
            # Let this bubble up to be handled by the main authenticate method
            raise
    
    def _authenticate_with_agent(self, client: SSHClient, config: SSHConfig) -> None:
        """Authenticate using SSH agent.
        
        Args:
            client: The paramiko SSHClient instance
            config: SSH configuration for agent authentication
            
        Raises:
            AuthenticationError: If agent authentication fails
        """
        # Check if SSH agent is available
        if not self._is_ssh_agent_available():
            raise AuthenticationError(
                "SSH agent is not available or has no keys loaded",
                "agent",
                "No SSH_AUTH_SOCK environment variable or agent not running"
            )
        
        try:
            client.connect(
                hostname=config.hostname,
                port=config.port,
                username=config.username,
                timeout=config.timeout,
                allow_agent=True,  # Use SSH agent
                look_for_keys=False  # Don't look for key files
            )
            
        except AuthenticationException:
            # Let this bubble up to be handled by the main authenticate method
            raise
    
    def _load_private_key(self, key_path: Path) -> paramiko.PKey:
        """Load a private key from file, trying different key types.
        
        Args:
            key_path: Path to the private key file
            
        Returns:
            Loaded private key object
            
        Raises:
            paramiko.SSHException: If key cannot be loaded
        """
        key_types = [
            paramiko.RSAKey,
            paramiko.DSSKey,
            paramiko.ECDSAKey,
            paramiko.Ed25519Key
        ]
        
        last_exception = None
        
        for key_type in key_types:
            try:
                return key_type.from_private_key_file(str(key_path))
            except paramiko.SSHException as e:
                last_exception = e
                continue
            except Exception as e:
                last_exception = e
                continue
        
        # If we get here, none of the key types worked
        raise paramiko.SSHException(f"Could not load private key from {key_path}: {last_exception}")
    
    def _is_ssh_agent_available(self) -> bool:
        """Check if SSH agent is available and has keys.
        
        Returns:
            True if SSH agent is available with keys, False otherwise
        """
        # Check if SSH_AUTH_SOCK environment variable is set
        auth_sock = os.environ.get('SSH_AUTH_SOCK')
        if not auth_sock:
            self.logger.debug("SSH_AUTH_SOCK not set, SSH agent not available")
            return False
        
        # Check if the socket exists
        if not os.path.exists(auth_sock):
            self.logger.debug(f"SSH agent socket {auth_sock} does not exist")
            return False
        
        try:
            # Try to connect to the agent and get keys
            agent = paramiko.Agent()
            keys = agent.get_keys()
            
            if not keys:
                self.logger.debug("SSH agent has no keys loaded")
                return False
            
            self.logger.debug(f"SSH agent has {len(keys)} keys available")
            return True
            
        except Exception as e:
            self.logger.debug(f"Error connecting to SSH agent: {e}")
            return False
    
    def validate_config(self, config: SSHConfig) -> Tuple[bool, Optional[str]]:
        """Validate SSH configuration for authentication.
        
        Args:
            config: SSH configuration to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if config.auth_method == "key":
                if not config.key_path:
                    return False, "SSH key path is required for key authentication"
                
                key_path = Path(config.key_path).expanduser()
                if not key_path.exists():
                    return False, f"SSH key file not found: {key_path}"
                
                if not key_path.is_file():
                    return False, f"SSH key path is not a file: {key_path}"
                
                # Try to load the key to validate it
                try:
                    self._load_private_key(key_path)
                except paramiko.PasswordRequiredException:
                    return False, f"SSH key {key_path} is encrypted and requires a passphrase"
                except Exception as e:
                    return False, f"Invalid SSH key file {key_path}: {e}"
            
            elif config.auth_method == "password":
                if not config.password:
                    return False, "Password is required for password authentication"
            
            elif config.auth_method == "agent":
                if not self._is_ssh_agent_available():
                    return False, "SSH agent is not available or has no keys loaded"
            
            else:
                return False, f"Unsupported authentication method: {config.auth_method}"
            
            return True, None
            
        except Exception as e:
            return False, f"Configuration validation error: {e}"