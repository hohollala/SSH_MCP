"""Unit tests for error handling and logging system."""

import json
import logging
import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any

from ssh_mcp_server.errors import (
    MCPError, MCPErrorCode, MCPException, ConnectionException,
    AuthenticationException, TimeoutException, PermissionException,
    CommandException, generate_error_message, create_detailed_error_context,
    sanitize_error_message, MCPLogger, get_logger, configure_logging
)


class TestMCPError:
    """Test cases for MCPError class."""
    
    def test_mcp_error_creation(self):
        """Test basic MCPError creation."""
        error = MCPError(
            code=MCPErrorCode.CONNECTION_ERROR,
            message="Connection failed",
            data={"hostname": "example.com"}
        )
        
        assert error.code == MCPErrorCode.CONNECTION_ERROR
        assert error.message == "Connection failed"
        assert error.data == {"hostname": "example.com"}
    
    def test_mcp_error_validation(self):
        """Test MCPError validation."""
        # Test invalid code
        with pytest.raises(ValueError, match="Error code must be an integer"):
            MCPError(code="invalid", message="test")
        
        # Test invalid message
        with pytest.raises(ValueError, match="Error message must be a non-empty string"):
            MCPError(code=1000, message="")
        
        with pytest.raises(ValueError, match="Error message must be a non-empty string"):
            MCPError(code=1000, message=123)
    
    def test_sensitive_data_filtering(self):
        """Test filtering of sensitive information."""
        error = MCPError(
            code=MCPErrorCode.AUTHENTICATION_ERROR,
            message="Auth failed",
            data={
                "username": "testuser",
                "password": "secret123",
                "ssh_key": "private_key_content",
                "hostname": "example.com",
                "nested": {
                    "token": "abc123",
                    "safe_data": "public_info"
                }
            }
        )
        
        assert error.data["username"] == "testuser"
        assert error.data["password"] == "[FILTERED]"
        assert error.data["ssh_key"] == "[FILTERED]"
        assert error.data["hostname"] == "example.com"
        assert error.data["nested"]["token"] == "[FILTERED]"
        assert error.data["nested"]["safe_data"] == "public_info"
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        error = MCPError(
            code=MCPErrorCode.INVALID_PARAMS,
            message="Invalid parameters",
            data={"parameter": "hostname"}
        )
        
        result = error.to_dict()
        expected = {
            "code": MCPErrorCode.INVALID_PARAMS,
            "message": "Invalid parameters",
            "data": {"parameter": "hostname"}
        }
        
        assert result == expected
    
    def test_to_dict_without_data(self):
        """Test conversion to dictionary without data."""
        error = MCPError(
            code=MCPErrorCode.INTERNAL_ERROR,
            message="Internal error"
        )
        
        result = error.to_dict()
        expected = {
            "code": MCPErrorCode.INTERNAL_ERROR,
            "message": "Internal error"
        }
        
        assert result == expected
    
    def test_to_json_rpc_error(self):
        """Test conversion to JSON-RPC error format."""
        error = MCPError(
            code=MCPErrorCode.METHOD_NOT_FOUND,
            message="Method not found"
        )
        
        result = error.to_json_rpc_error()
        expected = {
            "error": {
                "code": MCPErrorCode.METHOD_NOT_FOUND,
                "message": "Method not found"
            }
        }
        
        assert result == expected
    
    def test_class_methods(self):
        """Test class methods for creating specific error types."""
        # Test parse_error
        error = MCPError.parse_error("Invalid JSON")
        assert error.code == MCPErrorCode.PARSE_ERROR
        assert error.message == "Parse error"
        assert error.data == {"details": "Invalid JSON"}
        
        # Test connection_error
        error = MCPError.connection_error("example.com", "Connection refused")
        assert error.code == MCPErrorCode.CONNECTION_ERROR
        assert "example.com" in error.message
        assert error.data["hostname"] == "example.com"
        assert error.data["details"] == "Connection refused"
        
        # Test authentication_error
        error = MCPError.authentication_error("testuser", "Invalid key")
        assert error.code == MCPErrorCode.AUTHENTICATION_ERROR
        assert "testuser" in error.message
        assert error.data["username"] == "testuser"
        assert error.data["details"] == "Invalid key"
        
        # Test timeout_error
        error = MCPError.timeout_error("ssh_connect", 30)
        assert error.code == MCPErrorCode.TIMEOUT_ERROR
        assert "ssh_connect" in error.message
        assert error.data["operation"] == "ssh_connect"
        assert error.data["timeout_seconds"] == 30
        
        # Test command_error
        error = MCPError.command_error("ls -la", 1, "Permission denied")
        assert error.code == MCPErrorCode.COMMAND_ERROR
        assert "ls -la" in error.message
        assert error.data["command"] == "ls -la"
        assert error.data["exit_code"] == 1
        assert error.data["stderr"] == "Permission denied"
    
    def test_string_representations(self):
        """Test string representations of MCPError."""
        error = MCPError(
            code=MCPErrorCode.CONNECTION_ERROR,
            message="Connection failed"
        )
        
        assert str(error) == f"MCPError({MCPErrorCode.CONNECTION_ERROR}): Connection failed"
        assert "MCPError" in repr(error)
        assert "Connection failed" in repr(error)


class TestMCPException:
    """Test cases for MCP exception classes."""
    
    def test_mcp_exception(self):
        """Test basic MCPException."""
        error = MCPError(
            code=MCPErrorCode.INTERNAL_ERROR,
            message="Test error"
        )
        exception = MCPException(error)
        
        assert exception.error == error
        assert str(exception) == str(error)
    
    def test_from_error_code(self):
        """Test creating MCPException from error code."""
        exception = MCPException.from_error_code(
            MCPErrorCode.TOOL_ERROR,
            "Tool failed",
            {"tool": "ssh_connect"}
        )
        
        assert exception.error.code == MCPErrorCode.TOOL_ERROR
        assert exception.error.message == "Tool failed"
        assert exception.error.data == {"tool": "ssh_connect"}
    
    def test_connection_exception(self):
        """Test ConnectionException."""
        exception = ConnectionException(
            "Failed to connect",
            hostname="example.com",
            details="Connection refused"
        )
        
        assert exception.error.code == MCPErrorCode.CONNECTION_ERROR
        assert exception.error.message == "Failed to connect"
        assert exception.error.data["hostname"] == "example.com"
        assert exception.error.data["details"] == "Connection refused"
    
    def test_authentication_exception(self):
        """Test AuthenticationException."""
        exception = AuthenticationException(
            "Auth failed",
            username="testuser",
            details="Invalid key"
        )
        
        assert exception.error.code == MCPErrorCode.AUTHENTICATION_ERROR
        assert exception.error.message == "Auth failed"
        assert exception.error.data["username"] == "testuser"
        assert exception.error.data["details"] == "Invalid key"
    
    def test_timeout_exception(self):
        """Test TimeoutException."""
        exception = TimeoutException(
            "Operation timed out",
            operation="ssh_connect",
            timeout=30
        )
        
        assert exception.error.code == MCPErrorCode.TIMEOUT_ERROR
        assert exception.error.message == "Operation timed out"
        assert exception.error.data["operation"] == "ssh_connect"
        assert exception.error.data["timeout_seconds"] == 30
    
    def test_permission_exception(self):
        """Test PermissionException."""
        exception = PermissionException(
            "Access denied",
            resource="/etc/passwd",
            details="Insufficient permissions"
        )
        
        assert exception.error.code == MCPErrorCode.PERMISSION_ERROR
        assert exception.error.message == "Access denied"
        assert exception.error.data["resource"] == "/etc/passwd"
        assert exception.error.data["details"] == "Insufficient permissions"
    
    def test_command_exception(self):
        """Test CommandException."""
        exception = CommandException(
            "Command failed",
            command="ls -la",
            exit_code=1,
            stderr="Permission denied"
        )
        
        assert exception.error.code == MCPErrorCode.COMMAND_ERROR
        assert exception.error.message == "Command failed"
        assert exception.error.data["command"] == "ls -la"
        assert exception.error.data["exit_code"] == 1
        assert exception.error.data["stderr"] == "Permission denied"


class TestErrorMessageGeneration:
    """Test cases for error message generation."""
    
    def test_connection_error_messages(self):
        """Test connection error message generation."""
        # Test connection refused
        context = {
            "hostname": "example.com",
            "port": 22,
            "username": "testuser",
            "details": "Connection refused"
        }
        message = generate_error_message("connection", context, user_friendly=True)
        assert "Connection refused" in message
        assert "example.com:22" in message
        assert "firewall" in message.lower()
        
        # Test timeout
        context["details"] = "Connection timeout"
        message = generate_error_message("connection", context, user_friendly=True)
        assert "timed out" in message
        assert "network connectivity" in message.lower()
        
        # Test technical message
        message = generate_error_message("connection", context, user_friendly=False)
        assert "SSH connection failed" in message
        assert "testuser@example.com:22" in message
    
    def test_authentication_error_messages(self):
        """Test authentication error message generation."""
        # Test key authentication
        context = {
            "username": "testuser",
            "hostname": "example.com",
            "auth_method": "key",
            "details": "Key not found"
        }
        message = generate_error_message("authentication", context, user_friendly=True)
        assert "SSH key file not found" in message
        assert "verify the key path" in message.lower()
        
        # Test password authentication
        context["auth_method"] = "password"
        context["details"] = "Invalid password"
        message = generate_error_message("authentication", context, user_friendly=True)
        assert "Password authentication failed" in message
        assert "testuser@example.com" in message
        
        # Test agent authentication
        context["auth_method"] = "agent"
        message = generate_error_message("authentication", context, user_friendly=True)
        assert "SSH agent authentication failed" in message
        assert "SSH agent is running" in message
    
    def test_command_error_messages(self):
        """Test command error message generation."""
        # Test command not found
        context = {
            "command": "nonexistent_command",
            "exit_code": 127,
            "stderr": "command not found"
        }
        message = generate_error_message("command", context, user_friendly=True)
        assert "Command not found" in message
        assert "nonexistent_command" in message
        assert "PATH" in message
        
        # Test permission denied
        context["exit_code"] = 126
        message = generate_error_message("command", context, user_friendly=True)
        assert "Permission denied executing" in message
        assert "not executable" in message
        
        # Test general failure
        context["exit_code"] = 1
        context["stderr"] = "File not found"
        message = generate_error_message("command", context, user_friendly=True)
        assert "failed with error" in message
        assert "File not found" in message
    
    def test_file_error_messages(self):
        """Test file error message generation."""
        # Test file not found
        context = {
            "file_path": "/path/to/file.txt",
            "operation": "read",
            "details": "File not found"
        }
        message = generate_error_message("file", context, user_friendly=True)
        assert "File not found" in message
        assert "/path/to/file.txt" in message
        assert "verify the file path exists" in message.lower()
        
        # Test permission denied
        context["details"] = "Permission denied"
        message = generate_error_message("file", context, user_friendly=True)
        assert "Permission denied reading file" in message
        assert "check file permissions" in message.lower()
        
        # Test write operation
        context["operation"] = "write"
        context["details"] = "Directory does not exist"
        message = generate_error_message("file", context, user_friendly=True)
        assert "Directory does not exist" in message
        assert "create_dirs option" in message
    
    def test_timeout_error_messages(self):
        """Test timeout error message generation."""
        context = {
            "operation": "ssh_connect",
            "timeout_seconds": 30,
            "details": "Connection timeout"
        }
        message = generate_error_message("timeout", context, user_friendly=True)
        assert "timed out after 30 seconds" in message
        assert "ssh_connect" in message
        assert "taking longer than expected" in message.lower()


class TestErrorContext:
    """Test cases for error context creation."""
    
    def test_create_detailed_error_context(self):
        """Test creating detailed error context."""
        exception = ConnectionError("Connection failed")
        context = create_detailed_error_context(
            exception,
            operation="ssh_connect",
            connection_id="12345678-1234-1234-1234-123456789012",
            hostname="example.com"
        )
        
        assert context["operation"] == "ssh_connect"
        assert context["exception_type"] == "ConnectionError"
        assert context["exception_message"] == "Connection failed"
        assert context["connection_id"] == "12345678"  # Truncated
        assert context["hostname"] == "example.com"
        assert "timestamp" in context
    
    def test_sanitize_error_message(self):
        """Test error message sanitization."""
        # Test with sensitive information
        message = "Authentication failed: password=secret123 key=/path/to/key"
        
        # In production mode
        sanitized = sanitize_error_message(message, debug_mode=False)
        assert "secret123" not in sanitized
        assert "[FILTERED]" in sanitized
        
        # In debug mode
        sanitized = sanitize_error_message(message, debug_mode=True)
        assert "password=[FILTERED]" in sanitized
        assert "key=[FILTERED]" in sanitized


class TestMCPLogger:
    """Test cases for MCPLogger class."""
    
    def test_logger_creation(self):
        """Test logger creation."""
        logger = MCPLogger("test_logger", debug=True)
        assert logger.name == "test_logger"
        assert logger.debug_mode is True
        assert logger.logger.level == logging.DEBUG
    
    def test_logger_creation_with_log_level(self):
        """Test logger creation with specific log level."""
        logger = MCPLogger("test_logger", log_level="WARNING")
        assert logger.logger.level == logging.WARNING
    
    @patch('logging.StreamHandler')
    def test_handler_configuration(self, mock_handler):
        """Test handler configuration."""
        logger = MCPLogger("test_logger", debug=True)
        # Handler should be configured
        assert len(logger.logger.handlers) > 0
    
    def test_sensitive_info_filtering(self):
        """Test filtering of sensitive information in logs."""
        logger = MCPLogger("test_logger", debug=False)
        
        message = "Connection failed: password=secret123 token=abc123"
        filtered = logger._filter_sensitive_info(message)
        
        assert "secret123" not in filtered
        assert "abc123" not in filtered
        assert "[FILTERED]" in filtered
    
    def test_context_filtering(self):
        """Test filtering of sensitive information in context."""
        logger = MCPLogger("test_logger", debug=True)
        
        context = {
            "username": "testuser",
            "password": "secret123",
            "hostname": "example.com",
            "ssh_key": "private_key_content"
        }
        
        filtered = logger._filter_context(context)
        
        assert filtered["username"] == "testuser"
        assert filtered["password"] == "[FILTERED]"
        assert filtered["hostname"] == "example.com"
        assert filtered["ssh_key"] == "[FILTERED]"
    
    @patch('logging.Logger.debug')
    def test_debug_logging(self, mock_debug):
        """Test debug logging."""
        logger = MCPLogger("test_logger", debug=True)
        logger.debug("Test message", connection_id="12345")
        
        mock_debug.assert_called_once()
        call_args = mock_debug.call_args[0][0]
        assert "Test message" in call_args
        assert "Context:" in call_args
    
    @patch('logging.Logger.info')
    def test_info_logging(self, mock_info):
        """Test info logging."""
        logger = MCPLogger("test_logger", debug=False)
        logger.info("Test message")
        
        mock_info.assert_called_once()
        call_args = mock_info.call_args[0][0]
        assert "Test message" in call_args
    
    @patch('logging.Logger.error')
    def test_error_logging_with_exception(self, mock_error):
        """Test error logging with exception."""
        logger = MCPLogger("test_logger", debug=True)
        exception = ValueError("Test exception")
        logger.error("Test error", exception=exception, connection_id="12345")
        
        mock_error.assert_called_once()
        call_args = mock_error.call_args[0][0]
        assert "Test error" in call_args
        assert "ValueError" in call_args
        assert "Test exception" in call_args
    
    def test_mcp_request_logging(self):
        """Test MCP request logging."""
        logger = MCPLogger("test_logger", debug=True)
        
        with patch.object(logger, 'debug') as mock_debug:
            logger.log_mcp_request("req123", "ssh_connect", {"hostname": "example.com"})
            mock_debug.assert_called_once()
            call_args = mock_debug.call_args[0][0]
            assert "MCP Request [req123]: ssh_connect" in call_args
    
    def test_ssh_operation_logging(self):
        """Test SSH operation logging."""
        logger = MCPLogger("test_logger", debug=True)
        
        with patch.object(logger, 'info') as mock_info:
            logger.log_ssh_operation("connect", "12345678-1234", True, "Connected successfully")
            mock_info.assert_called_once()
            call_args = mock_info.call_args[0][0]
            assert "SSH connect successful" in call_args
            assert "[conn: 12345678]" in call_args
    
    def test_set_debug_mode(self):
        """Test setting debug mode."""
        logger = MCPLogger("test_logger", debug=False)
        assert logger.debug_mode is False
        assert logger.logger.level == logging.INFO
        
        logger.set_debug_mode(True)
        assert logger.debug_mode is True
        assert logger.logger.level == logging.DEBUG
    
    def test_set_log_level(self):
        """Test setting log level."""
        logger = MCPLogger("test_logger")
        
        logger.set_log_level("ERROR")
        assert logger.logger.level == logging.ERROR
        
        logger.set_log_level("DEBUG")
        assert logger.logger.level == logging.DEBUG


class TestGlobalLogger:
    """Test cases for global logger functions."""
    
    def test_get_logger(self):
        """Test getting global logger."""
        logger1 = get_logger("test_logger", debug=True)
        logger2 = get_logger("test_logger", debug=False)
        
        # Should return the same instance
        assert logger1 is logger2
    
    def test_configure_logging(self):
        """Test configuring global logging."""
        configure_logging(debug=True, log_level="DEBUG")
        logger = get_logger()
        
        assert logger.debug_mode is True
        assert logger.logger.level == logging.DEBUG


if __name__ == "__main__":
    pytest.main([__file__])