"""Error handling and logging system for SSH MCP Server.

This module provides comprehensive error handling classes, error codes,
and logging utilities for the SSH MCP Server.
"""

import logging
import re
from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Dict, Optional, Union


class MCPErrorCode(IntEnum):
    """Standard MCP error codes following JSON-RPC 2.0 specification."""
    
    # JSON-RPC 2.0 standard error codes
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    
    # MCP-specific error codes (range: -32000 to -32099)
    TOOL_ERROR = -32000
    CONNECTION_ERROR = -32001
    AUTHENTICATION_ERROR = -32002
    TIMEOUT_ERROR = -32003
    PERMISSION_ERROR = -32004
    FILE_NOT_FOUND_ERROR = -32005
    DIRECTORY_ERROR = -32006
    COMMAND_ERROR = -32007
    NETWORK_ERROR = -32008
    RESOURCE_LIMIT_ERROR = -32009
    VALIDATION_ERROR = -32010
    CONFIGURATION_ERROR = -32011
    PROTOCOL_ERROR = -32012


@dataclass
class MCPError:
    """Represents an MCP error with code, message, and optional details.
    
    This class provides structured error information that can be serialized
    to JSON-RPC 2.0 error responses and includes security-aware filtering
    of sensitive information.
    """
    
    code: int
    message: str
    data: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Validate error after initialization."""
        self._validate_code()
        self._validate_message()
        self._filter_sensitive_data()
    
    def _validate_code(self):
        """Validate error code."""
        if not isinstance(self.code, int):
            raise ValueError("Error code must be an integer")
    
    def _validate_message(self):
        """Validate error message."""
        if not isinstance(self.message, str) or not self.message.strip():
            raise ValueError("Error message must be a non-empty string")
    
    def _filter_sensitive_data(self):
        """Filter sensitive information from error data."""
        if self.data is None:
            return
        
        # List of sensitive keys to filter
        sensitive_keys = {
            'password', 'passwd', 'pwd', 'secret', 'token', 'key', 'auth',
            'credential', 'private_key', 'ssh_key', 'passphrase'
        }
        
        # Recursively filter sensitive data
        self.data = self._filter_dict(self.data, sensitive_keys)
    
    def _filter_dict(self, data: Dict[str, Any], sensitive_keys: set) -> Dict[str, Any]:
        """Recursively filter sensitive keys from dictionary."""
        if not isinstance(data, dict):
            return data
        
        filtered = {}
        for key, value in data.items():
            # Check if key is sensitive (case-insensitive)
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                filtered[key] = "[FILTERED]"
            elif isinstance(value, dict):
                filtered[key] = self._filter_dict(value, sensitive_keys)
            elif isinstance(value, list):
                filtered[key] = [
                    self._filter_dict(item, sensitive_keys) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                filtered[key] = value
        
        return filtered
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert MCPError to dictionary for JSON-RPC response.
        
        Returns:
            Dictionary representation of the error
        """
        error_dict = {
            "code": self.code,
            "message": self.message
        }
        
        if self.data is not None:
            error_dict["data"] = self.data
        
        return error_dict
    
    def to_json_rpc_error(self) -> Dict[str, Any]:
        """Convert to JSON-RPC 2.0 error format.
        
        Returns:
            JSON-RPC 2.0 error dictionary
        """
        return {"error": self.to_dict()}
    
    @classmethod
    def parse_error(cls, details: Optional[str] = None) -> 'MCPError':
        """Create a parse error.
        
        Args:
            details: Additional error details
            
        Returns:
            MCPError instance for parse error
        """
        data = {"details": details} if details else None
        return cls(
            code=MCPErrorCode.PARSE_ERROR,
            message="Parse error",
            data=data
        )
    
    @classmethod
    def invalid_request(cls, details: Optional[str] = None) -> 'MCPError':
        """Create an invalid request error.
        
        Args:
            details: Additional error details
            
        Returns:
            MCPError instance for invalid request
        """
        data = {"details": details} if details else None
        return cls(
            code=MCPErrorCode.INVALID_REQUEST,
            message="Invalid request",
            data=data
        )
    
    @classmethod
    def method_not_found(cls, method: Optional[str] = None) -> 'MCPError':
        """Create a method not found error.
        
        Args:
            method: The method that was not found
            
        Returns:
            MCPError instance for method not found
        """
        message = f"Method not found: {method}" if method else "Method not found"
        data = {"method": method} if method else None
        return cls(
            code=MCPErrorCode.METHOD_NOT_FOUND,
            message=message,
            data=data
        )
    
    @classmethod
    def invalid_params(cls, details: Optional[str] = None, param_name: Optional[str] = None) -> 'MCPError':
        """Create an invalid parameters error.
        
        Args:
            details: Additional error details
            param_name: Name of the invalid parameter
            
        Returns:
            MCPError instance for invalid parameters
        """
        data = {}
        if details:
            data["details"] = details
        if param_name:
            data["parameter"] = param_name
        
        return cls(
            code=MCPErrorCode.INVALID_PARAMS,
            message="Invalid parameters",
            data=data if data else None
        )
    
    @classmethod
    def internal_error(cls, details: Optional[str] = None) -> 'MCPError':
        """Create an internal error.
        
        Args:
            details: Additional error details
            
        Returns:
            MCPError instance for internal error
        """
        data = {"details": details} if details else None
        return cls(
            code=MCPErrorCode.INTERNAL_ERROR,
            message="Internal error",
            data=data
        )
    
    @classmethod
    def connection_error(cls, hostname: Optional[str] = None, details: Optional[str] = None) -> 'MCPError':
        """Create a connection error.
        
        Args:
            hostname: The hostname that failed to connect
            details: Additional error details
            
        Returns:
            MCPError instance for connection error
        """
        message = f"Connection failed to {hostname}" if hostname else "Connection failed"
        data = {}
        if hostname:
            data["hostname"] = hostname
        if details:
            data["details"] = details
        
        return cls(
            code=MCPErrorCode.CONNECTION_ERROR,
            message=message,
            data=data if data else None
        )
    
    @classmethod
    def authentication_error(cls, username: Optional[str] = None, details: Optional[str] = None) -> 'MCPError':
        """Create an authentication error.
        
        Args:
            username: The username that failed authentication
            details: Additional error details
            
        Returns:
            MCPError instance for authentication error
        """
        message = f"Authentication failed for user {username}" if username else "Authentication failed"
        data = {}
        if username:
            data["username"] = username
        if details:
            data["details"] = details
        
        return cls(
            code=MCPErrorCode.AUTHENTICATION_ERROR,
            message=message,
            data=data if data else None
        )
    
    @classmethod
    def timeout_error(cls, operation: Optional[str] = None, timeout: Optional[int] = None) -> 'MCPError':
        """Create a timeout error.
        
        Args:
            operation: The operation that timed out
            timeout: The timeout value in seconds
            
        Returns:
            MCPError instance for timeout error
        """
        message = f"Operation timed out: {operation}" if operation else "Operation timed out"
        data = {}
        if operation:
            data["operation"] = operation
        if timeout:
            data["timeout_seconds"] = timeout
        
        return cls(
            code=MCPErrorCode.TIMEOUT_ERROR,
            message=message,
            data=data if data else None
        )
    
    @classmethod
    def permission_error(cls, resource: Optional[str] = None, details: Optional[str] = None) -> 'MCPError':
        """Create a permission error.
        
        Args:
            resource: The resource that access was denied to
            details: Additional error details
            
        Returns:
            MCPError instance for permission error
        """
        message = f"Permission denied: {resource}" if resource else "Permission denied"
        data = {}
        if resource:
            data["resource"] = resource
        if details:
            data["details"] = details
        
        return cls(
            code=MCPErrorCode.PERMISSION_ERROR,
            message=message,
            data=data if data else None
        )
    
    @classmethod
    def file_not_found_error(cls, file_path: Optional[str] = None) -> 'MCPError':
        """Create a file not found error.
        
        Args:
            file_path: The file path that was not found
            
        Returns:
            MCPError instance for file not found error
        """
        message = f"File not found: {file_path}" if file_path else "File not found"
        data = {"file_path": file_path} if file_path else None
        
        return cls(
            code=MCPErrorCode.FILE_NOT_FOUND_ERROR,
            message=message,
            data=data
        )
    
    @classmethod
    def command_error(cls, command: Optional[str] = None, exit_code: Optional[int] = None, 
                     stderr: Optional[str] = None) -> 'MCPError':
        """Create a command execution error.
        
        Args:
            command: The command that failed
            exit_code: The exit code of the failed command
            stderr: Standard error output from the command
            
        Returns:
            MCPError instance for command error
        """
        message = f"Command failed: {command}" if command else "Command execution failed"
        data = {}
        if command:
            data["command"] = command
        if exit_code is not None:
            data["exit_code"] = exit_code
        if stderr:
            data["stderr"] = stderr
        
        return cls(
            code=MCPErrorCode.COMMAND_ERROR,
            message=message,
            data=data if data else None
        )
    
    def __str__(self) -> str:
        """String representation of the error."""
        return f"MCPError({self.code}): {self.message}"
    
    def __repr__(self) -> str:
        """Detailed string representation of the error."""
        return f"MCPError(code={self.code}, message='{self.message}', data={self.data})"


class MCPException(Exception):
    """Base exception class for MCP-related errors.
    
    This exception wraps MCPError instances and provides a way to raise
    structured errors that can be caught and converted to proper MCP responses.
    """
    
    def __init__(self, error: MCPError):
        """Initialize MCP exception.
        
        Args:
            error: The MCPError instance
        """
        self.error = error
        super().__init__(str(error))
    
    @classmethod
    def from_error_code(cls, code: MCPErrorCode, message: str, 
                       data: Optional[Dict[str, Any]] = None) -> 'MCPException':
        """Create MCPException from error code.
        
        Args:
            code: The error code
            message: Error message
            data: Additional error data
            
        Returns:
            MCPException instance
        """
        error = MCPError(code=code, message=message, data=data)
        return cls(error)


class ConnectionException(MCPException):
    """Exception for SSH connection-related errors."""
    
    def __init__(self, message: str, hostname: Optional[str] = None, 
                 details: Optional[str] = None):
        """Initialize connection exception.
        
        Args:
            message: Error message
            hostname: The hostname that failed
            details: Additional error details
        """
        error = MCPError.connection_error(hostname, details)
        error.message = message  # Override with custom message
        super().__init__(error)


class AuthenticationException(MCPException):
    """Exception for SSH authentication-related errors."""
    
    def __init__(self, message: str, username: Optional[str] = None, 
                 details: Optional[str] = None):
        """Initialize authentication exception.
        
        Args:
            message: Error message
            username: The username that failed
            details: Additional error details
        """
        error = MCPError.authentication_error(username, details)
        error.message = message  # Override with custom message
        super().__init__(error)


class TimeoutException(MCPException):
    """Exception for timeout-related errors."""
    
    def __init__(self, message: str, operation: Optional[str] = None, 
                 timeout: Optional[int] = None):
        """Initialize timeout exception.
        
        Args:
            message: Error message
            operation: The operation that timed out
            timeout: The timeout value in seconds
        """
        error = MCPError.timeout_error(operation, timeout)
        error.message = message  # Override with custom message
        super().__init__(error)


class PermissionException(MCPException):
    """Exception for permission-related errors."""
    
    def __init__(self, message: str, resource: Optional[str] = None, 
                 details: Optional[str] = None):
        """Initialize permission exception.
        
        Args:
            message: Error message
            resource: The resource that access was denied to
            details: Additional error details
        """
        error = MCPError.permission_error(resource, details)
        error.message = message  # Override with custom message
        super().__init__(error)


class CommandException(MCPException):
    """Exception for command execution errors."""
    
    def __init__(self, message: str, command: Optional[str] = None, 
                 exit_code: Optional[int] = None, stderr: Optional[str] = None):
        """Initialize command exception.
        
        Args:
            message: Error message
            command: The command that failed
            exit_code: The exit code of the failed command
            stderr: Standard error output from the command
        """
        error = MCPError.command_error(command, exit_code, stderr)
        error.message = message  # Override with custom message
        super().__init__(error)


def generate_error_message(error_type: str, context: Dict[str, Any], 
                          user_friendly: bool = True) -> str:
    """Generate contextual error messages based on error type and context.
    
    Args:
        error_type: Type of error (connection, authentication, command, etc.)
        context: Context information for the error
        user_friendly: Whether to generate user-friendly messages
        
    Returns:
        Generated error message string
    """
    if error_type == "connection":
        return _generate_connection_error_message(context, user_friendly)
    elif error_type == "authentication":
        return _generate_authentication_error_message(context, user_friendly)
    elif error_type == "command":
        return _generate_command_error_message(context, user_friendly)
    elif error_type == "file":
        return _generate_file_error_message(context, user_friendly)
    elif error_type == "permission":
        return _generate_permission_error_message(context, user_friendly)
    elif error_type == "timeout":
        return _generate_timeout_error_message(context, user_friendly)
    elif error_type == "network":
        return _generate_network_error_message(context, user_friendly)
    else:
        return f"An error occurred: {context.get('details', 'Unknown error')}"


def _generate_connection_error_message(context: Dict[str, Any], user_friendly: bool) -> str:
    """Generate connection error messages."""
    hostname = context.get('hostname', 'unknown host')
    port = context.get('port', 22)
    username = context.get('username', 'unknown user')
    details = context.get('details', '')
    
    if user_friendly:
        if 'refused' in details.lower():
            return f"Connection refused by {hostname}:{port}. The SSH service may not be running or may be blocked by a firewall."
        elif 'timeout' in details.lower():
            return f"Connection to {hostname}:{port} timed out. Please check the hostname and network connectivity."
        elif 'unreachable' in details.lower():
            return f"Host {hostname} is unreachable. Please verify the hostname and network connection."
        elif 'resolve' in details.lower():
            return f"Could not resolve hostname {hostname}. Please check the hostname spelling and DNS configuration."
        else:
            return f"Failed to connect to {username}@{hostname}:{port}. Please verify the connection details and network connectivity."
    else:
        return f"SSH connection failed to {username}@{hostname}:{port}: {details}"


def _generate_authentication_error_message(context: Dict[str, Any], user_friendly: bool) -> str:
    """Generate authentication error messages."""
    username = context.get('username', 'unknown user')
    hostname = context.get('hostname', 'unknown host')
    auth_method = context.get('auth_method', 'unknown')
    details = context.get('details', '')
    
    if user_friendly:
        if auth_method == 'key':
            if 'not found' in details.lower():
                return f"SSH key file not found. Please verify the key path and ensure the file exists."
            elif 'permission' in details.lower():
                return f"SSH key file permission denied. Please check that the key file is readable and has correct permissions (600)."
            elif 'invalid' in details.lower():
                return f"Invalid SSH key format. Please ensure you're using a valid private key file."
            else:
                return f"SSH key authentication failed for {username}@{hostname}. Please verify the key file and ensure it's authorized on the server."
        elif auth_method == 'password':
            return f"Password authentication failed for {username}@{hostname}. Please verify the username and password."
        elif auth_method == 'agent':
            return f"SSH agent authentication failed for {username}@{hostname}. Please ensure SSH agent is running and has the correct keys loaded."
        else:
            return f"Authentication failed for {username}@{hostname}. Please verify your credentials and authentication method."
    else:
        return f"SSH authentication failed for {username}@{hostname} using {auth_method}: {details}"


def _generate_command_error_message(context: Dict[str, Any], user_friendly: bool) -> str:
    """Generate command execution error messages."""
    command = context.get('command', 'unknown command')
    exit_code = context.get('exit_code')
    stderr = context.get('stderr', '')
    
    if user_friendly:
        if exit_code == 127:
            return f"Command not found: '{command}'. Please verify the command exists and is in the PATH."
        elif exit_code == 126:
            return f"Permission denied executing '{command}'. The command exists but is not executable."
        elif exit_code == 1:
            if stderr:
                return f"Command '{command}' failed with error: {stderr.strip()}"
            else:
                return f"Command '{command}' failed with exit code 1. Check the command syntax and arguments."
        elif exit_code and exit_code > 0:
            if stderr:
                return f"Command '{command}' failed (exit code {exit_code}): {stderr.strip()}"
            else:
                return f"Command '{command}' failed with exit code {exit_code}."
        else:
            return f"Command execution failed: {command}"
    else:
        return f"Command failed: {command} (exit code: {exit_code}, stderr: {stderr})"


def _generate_file_error_message(context: Dict[str, Any], user_friendly: bool) -> str:
    """Generate file operation error messages."""
    file_path = context.get('file_path', 'unknown file')
    operation = context.get('operation', 'access')
    details = context.get('details', '')
    
    if user_friendly:
        if operation == 'read':
            if 'not found' in details.lower():
                return f"File not found: {file_path}. Please verify the file path exists."
            elif 'permission' in details.lower():
                return f"Permission denied reading file: {file_path}. Please check file permissions."
            else:
                return f"Failed to read file: {file_path}. Please verify the file exists and is readable."
        elif operation == 'write':
            if 'permission' in details.lower():
                return f"Permission denied writing to file: {file_path}. Please check directory and file permissions."
            elif 'directory' in details.lower():
                return f"Directory does not exist for file: {file_path}. Please create the directory first or enable create_dirs option."
            else:
                return f"Failed to write file: {file_path}. Please verify the directory exists and is writable."
        elif operation == 'list':
            if 'not found' in details.lower():
                return f"Directory not found: {file_path}. Please verify the directory path exists."
            elif 'permission' in details.lower():
                return f"Permission denied listing directory: {file_path}. Please check directory permissions."
            else:
                return f"Failed to list directory: {file_path}. Please verify the directory exists and is accessible."
        else:
            return f"File operation failed on {file_path}: {details}"
    else:
        return f"File {operation} failed: {file_path} - {details}"


def _generate_permission_error_message(context: Dict[str, Any], user_friendly: bool) -> str:
    """Generate permission error messages."""
    resource = context.get('resource', 'unknown resource')
    operation = context.get('operation', 'access')
    details = context.get('details', '')
    
    if user_friendly:
        if operation == 'execute':
            return f"Permission denied executing command on {resource}. You may need elevated privileges (sudo) or the command may not be executable."
        elif operation == 'read':
            return f"Permission denied reading {resource}. Please check that you have read permissions for this file or directory."
        elif operation == 'write':
            return f"Permission denied writing to {resource}. Please check that you have write permissions for this file or directory."
        else:
            return f"Permission denied accessing {resource}. Please verify you have the necessary permissions."
    else:
        return f"Permission denied: {operation} on {resource} - {details}"


def _generate_timeout_error_message(context: Dict[str, Any], user_friendly: bool) -> str:
    """Generate timeout error messages."""
    operation = context.get('operation', 'operation')
    timeout = context.get('timeout_seconds')
    details = context.get('details', '')
    
    if user_friendly:
        if timeout:
            return f"Operation timed out after {timeout} seconds: {operation}. The operation may be taking longer than expected or the connection may be slow."
        else:
            return f"Operation timed out: {operation}. Please try again or increase the timeout value."
    else:
        return f"Timeout: {operation} (timeout: {timeout}s) - {details}"


def _generate_network_error_message(context: Dict[str, Any], user_friendly: bool) -> str:
    """Generate network error messages."""
    hostname = context.get('hostname', 'unknown host')
    details = context.get('details', '')
    
    if user_friendly:
        if 'dns' in details.lower():
            return f"DNS resolution failed for {hostname}. Please check the hostname and DNS configuration."
        elif 'network' in details.lower():
            return f"Network error connecting to {hostname}. Please check your network connection and firewall settings."
        else:
            return f"Network error occurred while connecting to {hostname}. Please verify network connectivity."
    else:
        return f"Network error: {hostname} - {details}"


def create_detailed_error_context(exception: Exception, operation: str = "", 
                                connection_id: Optional[str] = None,
                                **kwargs) -> Dict[str, Any]:
    """Create detailed error context from exception and operation details.
    
    Args:
        exception: The exception that occurred
        operation: The operation being performed when the error occurred
        connection_id: The connection ID if applicable
        **kwargs: Additional context information
        
    Returns:
        Dictionary with detailed error context
    """
    context = {
        "operation": operation,
        "exception_type": type(exception).__name__,
        "exception_message": str(exception),
        "timestamp": logging.Formatter().formatTime(logging.LogRecord(
            name="", level=0, pathname="", lineno=0, msg="", args=(), exc_info=None
        ))
    }
    
    if connection_id:
        conn_id_str = str(connection_id)
        context["connection_id"] = conn_id_str[:8] if len(conn_id_str) > 8 else conn_id_str
    
    # Add any additional context
    context.update(kwargs)
    
    # Extract specific error information based on exception type
    if hasattr(exception, 'errno'):
        context["errno"] = exception.errno
    
    if hasattr(exception, 'strerror'):
        context["system_error"] = exception.strerror
    
    return context


def sanitize_error_message(message: str, debug_mode: bool = False) -> str:
    """Sanitize error messages to remove sensitive information.
    
    Args:
        message: The original error message
        debug_mode: Whether debug mode is enabled
        
    Returns:
        Sanitized error message
    """
    sensitive_patterns = [
        r'password[=:]\s*\S+',
        r'passwd[=:]\s*\S+',
        r'secret[=:]\s*\S+',
        r'token[=:]\s*\S+',
        r'key[=:]\s*\S+',
        r'auth[=:]\s*\S+',
    ]
    
    sanitized = message
    for pattern in sensitive_patterns:
        if debug_mode:
            # In debug mode, show the key but filter the value
            sanitized = re.sub(pattern, lambda m: m.group(0).split('=')[0] + '=[FILTERED]', 
                             sanitized, flags=re.IGNORECASE)
        else:
            # In production mode, replace entire match
            sanitized = re.sub(pattern, '[FILTERED]', sanitized, flags=re.IGNORECASE)
    
    return sanitized


class MCPLogger:
    """Enhanced logging system for SSH MCP Server with debug mode support.
    
    This class provides structured logging with different levels, debug mode support,
    and security-aware filtering of sensitive information in log messages.
    """
    
    def __init__(self, name: str = "ssh_mcp_server", debug: bool = False, 
                 log_level: Optional[str] = None):
        """Initialize MCP Logger.
        
        Args:
            name: Logger name
            debug: Enable debug mode
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        self.name = name
        self.debug_mode = debug
        self.logger = logging.getLogger(name)
        
        # Set logging level
        if log_level:
            level = getattr(logging, log_level.upper(), logging.INFO)
        elif self.debug_mode:
            level = logging.DEBUG
        else:
            level = logging.INFO
        
        self.logger.setLevel(level)
        
        # Configure handler if not already configured
        if not self.logger.handlers:
            self._configure_handler()
        
        # Security filter for sensitive information
        self.sensitive_patterns = [
            r'password[=:]\s*\S+',
            r'passwd[=:]\s*\S+',
            r'secret[=:]\s*\S+',
            r'token[=:]\s*\S+',
            r'private_key[=:]\s*\S+',
            r'ssh_key[=:]\s*\S+',
            r'passphrase[=:]\s*\S+',
        ]
    
    def _configure_handler(self):
        """Configure logging handler with appropriate formatter."""
        handler = logging.StreamHandler()
        
        if self.debug_mode:
            # Detailed format for debug mode
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
            )
        else:
            # Simple format for production
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            )
        
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def _filter_sensitive_info(self, message: str) -> str:
        """Filter sensitive information from log messages.
        
        Args:
            message: Original log message
            
        Returns:
            Filtered log message
        """
        if self.debug_mode:
            # In debug mode, show more information but still filter passwords
            filtered = message
            for pattern in self.sensitive_patterns:
                filtered = re.sub(pattern, lambda m: m.group(0).split('=')[0] + '=[FILTERED]', 
                                filtered, flags=re.IGNORECASE)
            return filtered
        else:
            # In production mode, be more aggressive with filtering
            filtered = message
            for pattern in self.sensitive_patterns:
                filtered = re.sub(pattern, '[FILTERED]', filtered, flags=re.IGNORECASE)
            return filtered
    
    def debug(self, message: str, **kwargs):
        """Log debug message.
        
        Args:
            message: Log message
            **kwargs: Additional context information
        """
        if self.debug_mode:
            filtered_message = self._filter_sensitive_info(message)
            if kwargs:
                filtered_message += f" | Context: {self._filter_context(kwargs)}"
            self.logger.debug(filtered_message)
    
    def info(self, message: str, **kwargs):
        """Log info message.
        
        Args:
            message: Log message
            **kwargs: Additional context information
        """
        filtered_message = self._filter_sensitive_info(message)
        if kwargs and self.debug_mode:
            filtered_message += f" | Context: {self._filter_context(kwargs)}"
        self.logger.info(filtered_message)
    
    def warning(self, message: str, **kwargs):
        """Log warning message.
        
        Args:
            message: Log message
            **kwargs: Additional context information
        """
        filtered_message = self._filter_sensitive_info(message)
        if kwargs:
            filtered_message += f" | Context: {self._filter_context(kwargs)}"
        self.logger.warning(filtered_message)
    
    def error(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """Log error message.
        
        Args:
            message: Log message
            exception: Exception instance if available
            **kwargs: Additional context information
        """
        filtered_message = self._filter_sensitive_info(message)
        
        if exception:
            filtered_message += f" | Exception: {type(exception).__name__}: {str(exception)}"
        
        if kwargs:
            filtered_message += f" | Context: {self._filter_context(kwargs)}"
        
        if self.debug_mode and exception:
            self.logger.error(filtered_message, exc_info=True)
        else:
            self.logger.error(filtered_message)
    
    def critical(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """Log critical message.
        
        Args:
            message: Log message
            exception: Exception instance if available
            **kwargs: Additional context information
        """
        filtered_message = self._filter_sensitive_info(message)
        
        if exception:
            filtered_message += f" | Exception: {type(exception).__name__}: {str(exception)}"
        
        if kwargs:
            filtered_message += f" | Context: {self._filter_context(kwargs)}"
        
        if self.debug_mode and exception:
            self.logger.critical(filtered_message, exc_info=True)
        else:
            self.logger.critical(filtered_message)
    
    def log_mcp_request(self, request_id: Optional[str], method: str, params: Optional[Dict] = None):
        """Log MCP request with appropriate detail level.
        
        Args:
            request_id: Request ID
            method: MCP method name
            params: Request parameters
        """
        if self.debug_mode:
            filtered_params = self._filter_context(params) if params else None
            self.debug(f"MCP Request [{request_id}]: {method}", params=filtered_params)
        else:
            self.info(f"MCP Request: {method}")
    
    def log_mcp_response(self, request_id: Optional[str], success: bool, 
                        error_code: Optional[int] = None):
        """Log MCP response with appropriate detail level.
        
        Args:
            request_id: Request ID
            success: Whether the request was successful
            error_code: Error code if request failed
        """
        if success:
            if self.debug_mode:
                self.debug(f"MCP Response [{request_id}]: Success")
            else:
                self.info("MCP Response: Success")
        else:
            if self.debug_mode:
                self.debug(f"MCP Response [{request_id}]: Error {error_code}")
            else:
                self.warning(f"MCP Response: Error {error_code}")
    
    def log_ssh_operation(self, operation: str, connection_id: Optional[str] = None, 
                         success: bool = True, details: Optional[str] = None):
        """Log SSH operation with appropriate detail level.
        
        Args:
            operation: SSH operation name
            connection_id: Connection ID if applicable
            success: Whether the operation was successful
            details: Additional operation details
        """
        conn_id_short = connection_id[:8] if connection_id else "unknown"
        
        if success:
            message = f"SSH {operation} successful"
            if self.debug_mode:
                message += f" [conn: {conn_id_short}]"
                if details:
                    message += f" | {details}"
            self.info(message)
        else:
            message = f"SSH {operation} failed"
            if connection_id:
                message += f" [conn: {conn_id_short}]"
            if details:
                message += f" | {details}"
            self.error(message)
    
    def _filter_context(self, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Filter sensitive information from context dictionary.
        
        Args:
            context: Context dictionary
            
        Returns:
            Filtered context dictionary
        """
        if not context:
            return {}
        
        filtered = {}
        sensitive_keys = {
            'password', 'passwd', 'pwd', 'secret', 'token', 'key', 'auth',
            'credential', 'private_key', 'ssh_key', 'passphrase'
        }
        
        for key, value in context.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                filtered[key] = "[FILTERED]"
            elif isinstance(value, str):
                filtered[key] = self._filter_sensitive_info(value)
            else:
                filtered[key] = value
        
        return filtered
    
    def set_debug_mode(self, debug: bool):
        """Enable or disable debug mode.
        
        Args:
            debug: Whether to enable debug mode
        """
        self.debug_mode = debug
        if debug:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)
    
    def set_log_level(self, level: str):
        """Set logging level.
        
        Args:
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        log_level = getattr(logging, level.upper(), logging.INFO)
        self.logger.setLevel(log_level)
    
    def get_logger(self) -> logging.Logger:
        """Get the underlying logger instance.
        
        Returns:
            Logger instance
        """
        return self.logger


# Global logger instance
_global_logger: Optional[MCPLogger] = None


def get_logger(name: str = "ssh_mcp_server", debug: bool = False, 
               log_level: Optional[str] = None) -> MCPLogger:
    """Get or create a global logger instance.
    
    Args:
        name: Logger name
        debug: Enable debug mode
        log_level: Logging level
        
    Returns:
        MCPLogger instance
    """
    global _global_logger
    
    if _global_logger is None:
        _global_logger = MCPLogger(name, debug, log_level)
    
    return _global_logger


def configure_logging(debug: bool = False, log_level: Optional[str] = None):
    """Configure global logging settings.
    
    Args:
        debug: Enable debug mode
        log_level: Logging level
    """
    global _global_logger
    
    if _global_logger is None:
        _global_logger = MCPLogger("ssh_mcp_server", debug, log_level)
    else:
        _global_logger.set_debug_mode(debug)
        if log_level:
            _global_logger.set_log_level(log_level)