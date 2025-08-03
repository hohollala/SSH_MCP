"""Tests for SSH file operations functionality."""

import pytest
import tempfile
import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from ssh_mcp_server.connection import SSHConnection, ConnectionError
from ssh_mcp_server.manager import SSHManager, SSHManagerError
from ssh_mcp_server.server import MCPServer
from ssh_mcp_server.models import SSHConfig, ConnectionInfo
from ssh_mcp_server.tools import ToolError


class TestSSHConnectionFileOperations:
    """Test file operations in SSHConnection class."""
    
    @pytest.fixture
    def ssh_config(self):
        """Create a test SSH configuration."""
        return SSHConfig(
            hostname="test.example.com",
            username="testuser",
            port=22,
            auth_method="agent",  # Use agent auth to avoid key file validation
            timeout=30
        )
    
    @pytest.fixture
    def connection_info(self):
        """Create test connection info."""
        info = ConnectionInfo.create("test.example.com", "testuser", 22)
        info.connection_id = "test-connection-id"
        return info
    
    @pytest.fixture
    def ssh_connection(self, ssh_config, connection_info):
        """Create a test SSH connection."""
        connection = SSHConnection(ssh_config, connection_info)
        connection._connected = True
        connection.client = Mock()
        return connection
    
    @pytest.mark.asyncio
    async def test_read_file_success(self, ssh_connection):
        """Test successful file reading."""
        # Mock SFTP operations
        mock_sftp = Mock()
        mock_file = Mock()
        mock_file.read.return_value = b"Hello, World!"
        
        # Create a proper context manager mock
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_file
        mock_context.__exit__.return_value = None
        mock_sftp.open.return_value = mock_context
        
        ssh_connection.client.open_sftp.return_value = mock_sftp
        
        # Test file reading
        content = await ssh_connection.read_file("/test/file.txt")
        
        assert content == "Hello, World!"
        mock_sftp.open.assert_called_once_with("/test/file.txt", 'r')
        mock_sftp.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_read_file_not_connected(self, ssh_connection):
        """Test file reading when not connected."""
        ssh_connection._connected = False
        
        with pytest.raises(ConnectionError) as exc_info:
            await ssh_connection.read_file("/test/file.txt")
        
        assert "Connection not established" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_read_file_empty_path(self, ssh_connection):
        """Test file reading with empty path."""
        with pytest.raises(ConnectionError) as exc_info:
            await ssh_connection.read_file("")
        
        assert "File path cannot be empty" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_read_file_not_found(self, ssh_connection):
        """Test file reading when file doesn't exist."""
        mock_sftp = Mock()
        mock_sftp.open.side_effect = FileNotFoundError("File not found")
        ssh_connection.client.open_sftp.return_value = mock_sftp
        
        with pytest.raises(ConnectionError) as exc_info:
            await ssh_connection.read_file("/nonexistent/file.txt")
        
        assert "File not found" in str(exc_info.value)
        mock_sftp.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_read_file_permission_denied(self, ssh_connection):
        """Test file reading with permission error."""
        mock_sftp = Mock()
        mock_sftp.open.side_effect = PermissionError("Permission denied")
        ssh_connection.client.open_sftp.return_value = mock_sftp
        
        with pytest.raises(ConnectionError) as exc_info:
            await ssh_connection.read_file("/restricted/file.txt")
        
        assert "Permission denied" in str(exc_info.value)
        mock_sftp.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_read_file_encoding_error(self, ssh_connection):
        """Test file reading with encoding error."""
        mock_sftp = Mock()
        mock_file = Mock()
        mock_file.read.return_value = b"\xff\xfe\x00\x00"  # Invalid UTF-8
        
        # Create a proper context manager mock
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_file
        mock_context.__exit__.return_value = None
        mock_sftp.open.return_value = mock_context
        
        ssh_connection.client.open_sftp.return_value = mock_sftp
        
        with pytest.raises(ConnectionError) as exc_info:
            await ssh_connection.read_file("/test/binary.txt", encoding="utf-8")
        
        assert "Encoding error" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_write_file_success(self, ssh_connection):
        """Test successful file writing."""
        # Mock SFTP operations
        mock_sftp = Mock()
        mock_file = Mock()
        
        # Create a proper context manager mock
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_file
        mock_context.__exit__.return_value = None
        mock_sftp.open.return_value = mock_context
        
        ssh_connection.client.open_sftp.return_value = mock_sftp
        
        # Test file writing
        await ssh_connection.write_file("/test/output.txt", "Hello, World!")
        
        mock_sftp.open.assert_called_once_with("/test/output.txt", 'w')
        mock_file.write.assert_called_once_with(b"Hello, World!")
        mock_sftp.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_write_file_with_create_dirs(self, ssh_connection):
        """Test file writing with directory creation."""
        # Mock SFTP operations
        mock_sftp = Mock()
        mock_file = Mock()
        
        # Create a proper context manager mock
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_file
        mock_context.__exit__.return_value = None
        mock_sftp.open.return_value = mock_context
        
        ssh_connection.client.open_sftp.return_value = mock_sftp
        
        # Mock execute_command for mkdir
        ssh_connection.execute_command = AsyncMock()
        
        # Test file writing with directory creation
        await ssh_connection.write_file("/new/path/output.txt", "Content", create_dirs=True)
        
        ssh_connection.execute_command.assert_called_once_with("mkdir -p '/new/path'")
        mock_sftp.open.assert_called_once_with("/new/path/output.txt", 'w')
        mock_file.write.assert_called_once_with(b"Content")
    
    @pytest.mark.asyncio
    async def test_write_file_not_connected(self, ssh_connection):
        """Test file writing when not connected."""
        ssh_connection._connected = False
        
        with pytest.raises(ConnectionError) as exc_info:
            await ssh_connection.write_file("/test/file.txt", "content")
        
        assert "Connection not established" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_write_file_permission_denied(self, ssh_connection):
        """Test file writing with permission error."""
        mock_sftp = Mock()
        mock_sftp.open.side_effect = PermissionError("Permission denied")
        ssh_connection.client.open_sftp.return_value = mock_sftp
        
        with pytest.raises(ConnectionError) as exc_info:
            await ssh_connection.write_file("/restricted/file.txt", "content")
        
        assert "Permission denied" in str(exc_info.value)
        mock_sftp.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_list_directory_success(self, ssh_connection):
        """Test successful directory listing."""
        # Mock SFTP operations
        mock_sftp = Mock()
        mock_sftp.listdir.return_value = ["file1.txt", "file2.txt", ".hidden"]
        ssh_connection.client.open_sftp.return_value = mock_sftp
        
        # Test directory listing
        entries = await ssh_connection.list_directory("/test/dir")
        
        assert len(entries) == 2  # Hidden file should be excluded by default
        assert entries[0]["name"] == "file1.txt"
        assert entries[1]["name"] == "file2.txt"
        mock_sftp.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_list_directory_with_hidden(self, ssh_connection):
        """Test directory listing including hidden files."""
        mock_sftp = Mock()
        mock_sftp.listdir.return_value = ["file1.txt", ".hidden", "file2.txt"]
        ssh_connection.client.open_sftp.return_value = mock_sftp
        
        entries = await ssh_connection.list_directory("/test/dir", show_hidden=True)
        
        assert len(entries) == 3
        assert any(entry["name"] == ".hidden" for entry in entries)
    
    @pytest.mark.asyncio
    async def test_list_directory_detailed(self, ssh_connection):
        """Test detailed directory listing."""
        from paramiko import SFTPAttributes
        
        mock_sftp = Mock()
        
        # Create mock file attributes
        attr1 = SFTPAttributes()
        attr1.filename = "file1.txt"
        attr1.st_mode = 0o100644  # Regular file
        attr1.st_size = 1024
        attr1.st_mtime = 1640995200  # 2022-01-01 00:00:00
        attr1.st_uid = 1000
        attr1.st_gid = 1000
        
        attr2 = SFTPAttributes()
        attr2.filename = "dir1"
        attr2.st_mode = 0o040755  # Directory
        attr2.st_size = 4096
        attr2.st_mtime = 1640995200
        attr2.st_uid = 1000
        attr2.st_gid = 1000
        
        mock_sftp.listdir_attr.return_value = [attr1, attr2]
        ssh_connection.client.open_sftp.return_value = mock_sftp
        
        entries = await ssh_connection.list_directory("/test/dir", detailed=True)
        
        assert len(entries) == 2
        
        file_entry = next(e for e in entries if e["name"] == "file1.txt")
        assert file_entry["type"] == "file"
        assert file_entry["size"] == 1024
        assert file_entry["permissions"] == "644"
        
        dir_entry = next(e for e in entries if e["name"] == "dir1")
        assert dir_entry["type"] == "directory"
        assert dir_entry["size"] == 4096
    
    @pytest.mark.asyncio
    async def test_list_directory_not_found(self, ssh_connection):
        """Test directory listing when directory doesn't exist."""
        mock_sftp = Mock()
        mock_sftp.listdir.side_effect = FileNotFoundError("Directory not found")
        ssh_connection.client.open_sftp.return_value = mock_sftp
        
        with pytest.raises(ConnectionError) as exc_info:
            await ssh_connection.list_directory("/nonexistent/dir")
        
        assert "Directory not found" in str(exc_info.value)
        mock_sftp.close.assert_called_once()


class TestSSHManagerFileOperations:
    """Test file operations in SSHManager class."""
    
    @pytest.fixture
    def ssh_manager(self):
        """Create a test SSH manager."""
        return SSHManager(max_connections=5)
    
    @pytest.fixture
    def mock_connection(self):
        """Create a mock SSH connection."""
        connection = Mock(spec=SSHConnection)
        connection.connected = True
        connection.read_file = AsyncMock(return_value="file content")
        connection.write_file = AsyncMock()
        connection.list_directory = AsyncMock(return_value=[{"name": "file.txt", "type": "file"}])
        return connection
    
    @pytest.mark.asyncio
    async def test_read_file_success(self, ssh_manager, mock_connection):
        """Test successful file reading through manager."""
        connection_id = "test-connection"
        ssh_manager.connections[connection_id] = mock_connection
        
        content = await ssh_manager.read_file(connection_id, "/test/file.txt")
        
        assert content == "file content"
        mock_connection.read_file.assert_called_once_with("/test/file.txt", "utf-8")
    
    @pytest.mark.asyncio
    async def test_read_file_connection_not_found(self, ssh_manager):
        """Test file reading with non-existent connection."""
        with pytest.raises(SSHManagerError) as exc_info:
            await ssh_manager.read_file("nonexistent", "/test/file.txt")
        
        assert "Connection" in str(exc_info.value)
        assert "not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_read_file_connection_not_active(self, ssh_manager, mock_connection):
        """Test file reading with inactive connection."""
        connection_id = "test-connection"
        mock_connection.connected = False
        ssh_manager.connections[connection_id] = mock_connection
        
        with pytest.raises(SSHManagerError) as exc_info:
            await ssh_manager.read_file(connection_id, "/test/file.txt")
        
        assert "not active" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_write_file_success(self, ssh_manager, mock_connection):
        """Test successful file writing through manager."""
        connection_id = "test-connection"
        ssh_manager.connections[connection_id] = mock_connection
        
        await ssh_manager.write_file(connection_id, "/test/file.txt", "content", create_dirs=True)
        
        mock_connection.write_file.assert_called_once_with("/test/file.txt", "content", "utf-8", True)
    
    @pytest.mark.asyncio
    async def test_list_directory_success(self, ssh_manager, mock_connection):
        """Test successful directory listing through manager."""
        connection_id = "test-connection"
        ssh_manager.connections[connection_id] = mock_connection
        
        entries = await ssh_manager.list_directory(connection_id, "/test/dir", show_hidden=True, detailed=True)
        
        assert len(entries) == 1
        assert entries[0]["name"] == "file.txt"
        mock_connection.list_directory.assert_called_once_with("/test/dir", True, True)


class TestMCPServerFileOperationTools:
    """Test file operation tools in MCP Server."""
    
    @pytest.fixture
    def mcp_server(self):
        """Create a test MCP server."""
        server = MCPServer(max_connections=5, debug=True)
        server.ssh_manager = Mock(spec=SSHManager)
        return server
    
    @pytest.mark.asyncio
    async def test_handle_ssh_read_file_success(self, mcp_server):
        """Test successful ssh_read_file tool execution."""
        # Mock manager response
        mcp_server.ssh_manager.read_file = AsyncMock(return_value="Hello, World!")
        
        params = {
            "connection_id": "test-conn",
            "file_path": "/test/file.txt",
            "encoding": "utf-8"
        }
        
        result = await mcp_server._handle_ssh_read_file(params)
        
        assert result.success
        assert result.data["content"] == "Hello, World!"
        assert result.data["file_path"] == "/test/file.txt"
        assert result.data["size"] == 13
        assert result.data["lines"] == 1
        
        mcp_server.ssh_manager.read_file.assert_called_once_with("test-conn", "/test/file.txt", "utf-8")
    
    @pytest.mark.asyncio
    async def test_handle_ssh_read_file_error(self, mcp_server):
        """Test ssh_read_file tool with error."""
        mcp_server.ssh_manager.read_file = AsyncMock(side_effect=SSHManagerError("File not found"))
        
        params = {
            "connection_id": "test-conn",
            "file_path": "/nonexistent.txt"
        }
        
        with pytest.raises(ToolError) as exc_info:
            await mcp_server._handle_ssh_read_file(params)
        
        assert "File read failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_handle_ssh_write_file_success(self, mcp_server):
        """Test successful ssh_write_file tool execution."""
        mcp_server.ssh_manager.write_file = AsyncMock()
        
        params = {
            "connection_id": "test-conn",
            "file_path": "/test/output.txt",
            "content": "Hello, World!",
            "encoding": "utf-8",
            "create_dirs": True
        }
        
        result = await mcp_server._handle_ssh_write_file(params)
        
        assert result.success
        assert result.data["file_path"] == "/test/output.txt"
        assert result.data["bytes_written"] == 13
        assert result.data["create_dirs"] is True
        assert result.data["status"] == "success"
        
        mcp_server.ssh_manager.write_file.assert_called_once_with(
            "test-conn", "/test/output.txt", "Hello, World!", "utf-8", True
        )
    
    @pytest.mark.asyncio
    async def test_handle_ssh_write_file_error(self, mcp_server):
        """Test ssh_write_file tool with error."""
        mcp_server.ssh_manager.write_file = AsyncMock(side_effect=SSHManagerError("Permission denied"))
        
        params = {
            "connection_id": "test-conn",
            "file_path": "/restricted/file.txt",
            "content": "content"
        }
        
        with pytest.raises(ToolError) as exc_info:
            await mcp_server._handle_ssh_write_file(params)
        
        assert "File write failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_handle_ssh_list_directory_success(self, mcp_server):
        """Test successful ssh_list_directory tool execution."""
        mock_entries = [
            {"name": "file1.txt", "type": "file", "size": 1024},
            {"name": "dir1", "type": "directory", "size": 4096}
        ]
        mcp_server.ssh_manager.list_directory = AsyncMock(return_value=mock_entries)
        
        params = {
            "connection_id": "test-conn",
            "directory_path": "/test/dir",
            "show_hidden": True,
            "detailed": True
        }
        
        result = await mcp_server._handle_ssh_list_directory(params)
        
        assert result.success
        assert result.data["directory_path"] == "/test/dir"
        assert result.data["total_entries"] == 2
        assert result.data["show_hidden"] is True
        assert result.data["detailed"] is True
        assert len(result.data["entries"]) == 2
        
        mcp_server.ssh_manager.list_directory.assert_called_once_with(
            "test-conn", "/test/dir", True, True
        )
    
    @pytest.mark.asyncio
    async def test_handle_ssh_list_directory_error(self, mcp_server):
        """Test ssh_list_directory tool with error."""
        mcp_server.ssh_manager.list_directory = AsyncMock(side_effect=SSHManagerError("Directory not found"))
        
        params = {
            "connection_id": "test-conn",
            "directory_path": "/nonexistent"
        }
        
        with pytest.raises(ToolError) as exc_info:
            await mcp_server._handle_ssh_list_directory(params)
        
        assert "Directory listing failed" in str(exc_info.value)


class TestFileOperationIntegration:
    """Integration tests for file operations."""
    
    @pytest.mark.asyncio
    async def test_file_operations_end_to_end(self):
        """Test complete file operations workflow."""
        # This would be an integration test with a real SSH server
        # For now, we'll skip it as it requires external setup
        pytest.skip("Integration test requires real SSH server setup")
    
    @pytest.mark.asyncio
    async def test_file_operations_with_various_encodings(self):
        """Test file operations with different text encodings."""
        # Test UTF-8, Latin-1, ASCII encodings
        pytest.skip("Encoding test requires real SSH server setup")
    
    @pytest.mark.asyncio
    async def test_large_file_operations(self):
        """Test file operations with large files."""
        # Test reading/writing large files
        pytest.skip("Large file test requires real SSH server setup")