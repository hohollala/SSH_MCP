"""MCP Client Compatibility Tests.

This module implements comprehensive compatibility tests for various MCP clients
including Claude Code, Gemini CLI, and Claude Desktop, as well as MCP protocol
standard compliance verification.

Requirements covered:
- 7.1: Claude Code compatibility
- 7.2: Gemini CLI compatibility  
- 7.3: Claude Desktop compatibility
- 7.4: MCP protocol standard compliance
"""

import asyncio
import json
import pytest
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List, Optional
from datetime import datetime

from ssh_mcp_server.server import MCPServer
from ssh_mcp_server.models import SSHConfig, CommandResult, ConnectionInfo
from ssh_mcp_server.manager import SSHManagerError
from ssh_mcp_server.errors import MCPError, MCPErrorCode
from ssh_mcp_server.tools import get_all_tool_schemas


class TestClaudeCodeCompatibility:
    """Test compatibility with Claude Code client patterns."""
    
    @pytest.fixture
    def server(self):
        """Create MCP server for testing."""
        return MCPServer(max_connections=5, debug=True)
    
    @pytest.fixture
    def mock_ssh_manager(self, server):
        """Mock SSH manager for testing."""
        server.ssh_manager.create_connection = AsyncMock(return_value="claude-conn-1")
        server.ssh_manager.execute_command = AsyncMock()
        server.ssh_manager.read_file = AsyncMock()
        server.ssh_manager.write_file = AsyncMock()
        server.ssh_manager.list_directory = AsyncMock()
        server.ssh_manager.disconnect_connection = AsyncMock(return_value=True)
        server.ssh_manager.list_connections = AsyncMock(return_value=[])
        return server.ssh_manager
    
    @pytest.mark.asyncio
    async def test_claude_code_initialization_sequence(self, server, mock_ssh_manager):
        """Test Claude Code typical initialization sequence."""
        # Claude Code typically starts with initialize
        init_response = await server.handle_request({
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "roots": {"listChanged": True},
                    "sampling": {}
                },
                "clientInfo": {
                    "name": "Claude Code",
                    "version": "1.0.0"
                }
            },
            "id": 1
        })
        
        assert init_response["jsonrpc"] == "2.0"
        assert init_response["id"] == 1
        assert "result" in init_response
        assert init_response["result"]["protocolVersion"] == "2024-11-05"
        assert "capabilities" in init_response["result"]
        assert "serverInfo" in init_response["result"]
        
        # Then tools/list to discover available tools
        tools_response = await server.handle_request({
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": 2
        })
        
        assert tools_response["jsonrpc"] == "2.0"
        assert tools_response["id"] == 2
        assert "result" in tools_response
        assert "tools" in tools_response["result"]
        assert len(tools_response["result"]["tools"]) == 7
        
        # Verify all tools have proper schema format for Claude Code
        for tool in tools_response["result"]["tools"]:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
            assert tool["inputSchema"]["type"] == "object"
            assert "properties" in tool["inputSchema"]
    
    @pytest.mark.asyncio
    async def test_claude_code_interactive_development_workflow(self, server, mock_ssh_manager):
        """Test Claude Code interactive development workflow patterns."""
        # Mock successful responses
        mock_ssh_manager.execute_command.return_value = CommandResult(
            stdout="Python 3.9.7\n",
            stderr="",
            exit_code=0,
            execution_time=0.2,
            command="python3 --version"
        )
        
        mock_ssh_manager.read_file.return_value = "#!/usr/bin/env python3\nprint('Hello World')\n"
        
        mock_ssh_manager.list_directory.return_value = [
            {"name": "app.py", "type": "file", "size": 45},
            {"name": "requirements.txt", "type": "file", "size": 123},
            {"name": "tests", "type": "directory"}
        ]
        
        # 1. Connect to development server
        connect_response = await server.handle_request({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "dev.example.com",
                    "username": "developer",
                    "auth_method": "key",
                    "key_path": "~/.ssh/id_rsa"
                }
            },
            "id": 10
        })
        
        assert connect_response["jsonrpc"] == "2.0"
        assert connect_response["id"] == 10
        assert "result" in connect_response
        
        # Parse result content
        content = json.loads(connect_response["result"]["content"][0]["text"])
        assert content["success"] is True
        connection_id = content["data"]["connection_id"]
        
        # 2. Check Python version
        version_response = await server.handle_request({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_execute",
                "arguments": {
                    "connection_id": connection_id,
                    "command": "python3 --version"
                }
            },
            "id": 11
        })
        
        assert version_response["jsonrpc"] == "2.0"
        assert version_response["id"] == 11
        content = json.loads(version_response["result"]["content"][0]["text"])
        assert content["success"] is True
        assert "Python 3.9.7" in content["data"]["stdout"]
        
        # 3. List project files
        list_response = await server.handle_request({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_list_directory",
                "arguments": {
                    "connection_id": connection_id,
                    "directory_path": "/home/developer/project",
                    "detailed": True
                }
            },
            "id": 12
        })
        
        assert list_response["jsonrpc"] == "2.0"
        content = json.loads(list_response["result"]["content"][0]["text"])
        assert content["success"] is True
        assert len(content["data"]["entries"]) == 3
        
        # 4. Read source file
        read_response = await server.handle_request({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_read_file",
                "arguments": {
                    "connection_id": connection_id,
                    "file_path": "/home/developer/project/app.py"
                }
            },
            "id": 13
        })
        
        assert read_response["jsonrpc"] == "2.0"
        content = json.loads(read_response["result"]["content"][0]["text"])
        assert content["success"] is True
        assert "Hello World" in content["data"]["content"]
    
    @pytest.mark.asyncio
    async def test_claude_code_error_handling_patterns(self, server, mock_ssh_manager):
        """Test Claude Code error handling patterns."""
        # Mock connection failure
        mock_ssh_manager.create_connection.side_effect = SSHManagerError("Connection refused")
        
        # Test connection error handling
        error_response = await server.handle_request({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "unreachable.example.com",
                    "username": "user"
                }
            },
            "id": 20
        })
        
        assert error_response["jsonrpc"] == "2.0"
        assert error_response["id"] == 20
        assert "error" in error_response
        assert error_response["error"]["code"] == MCPErrorCode.TOOL_ERROR
        assert "SSH connection failed" in error_response["error"]["message"]
        
        # Verify error structure matches Claude Code expectations
        error_data = error_response["error"]
        assert "code" in error_data
        assert "message" in error_data
        assert isinstance(error_data["code"], int)
        assert isinstance(error_data["message"], str)
    
    @pytest.mark.asyncio
    async def test_claude_code_concurrent_operations(self, server, mock_ssh_manager):
        """Test Claude Code concurrent operation patterns."""
        # Mock multiple successful connections
        connection_ids = ["claude-conn-1", "claude-conn-2", "claude-conn-3"]
        mock_ssh_manager.create_connection.side_effect = connection_ids
        
        # Mock command results
        mock_ssh_manager.execute_command.side_effect = [
            CommandResult(stdout="Server 1 OK", stderr="", exit_code=0, execution_time=0.1, command="echo 'Server 1 OK'"),
            CommandResult(stdout="Server 2 OK", stderr="", exit_code=0, execution_time=0.1, command="echo 'Server 2 OK'"),
            CommandResult(stdout="Server 3 OK", stderr="", exit_code=0, execution_time=0.1, command="echo 'Server 3 OK'")
        ]
        
        # Create multiple connections concurrently (Claude Code pattern)
        tasks = []
        for i in range(3):
            task = server.handle_request({
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_connect",
                    "arguments": {
                        "hostname": f"server{i+1}.example.com",
                        "username": "admin"
                    }
                },
                "id": 30 + i
            })
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        
        # Verify all connections succeeded
        for i, response in enumerate(responses):
            assert response["jsonrpc"] == "2.0"
            assert response["id"] == 30 + i
            assert "result" in response
            content = json.loads(response["result"]["content"][0]["text"])
            assert content["success"] is True
        
        # Execute commands concurrently
        command_tasks = []
        for i, conn_id in enumerate(connection_ids):
            task = server.handle_request({
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_execute",
                    "arguments": {
                        "connection_id": conn_id,
                        "command": f"echo 'Server {i+1} OK'"
                    }
                },
                "id": 40 + i
            })
            command_tasks.append(task)
        
        command_responses = await asyncio.gather(*command_tasks)
        
        # Verify all commands succeeded
        for i, response in enumerate(command_responses):
            assert response["jsonrpc"] == "2.0"
            content = json.loads(response["result"]["content"][0]["text"])
            assert content["success"] is True
            assert f"Server {i+1} OK" in content["data"]["stdout"]


class TestGeminiCLICompatibility:
    """Test compatibility with Gemini CLI client patterns."""
    
    @pytest.fixture
    def server(self):
        """Create MCP server for testing."""
        return MCPServer(max_connections=10, debug=False)
    
    @pytest.fixture
    def mock_ssh_manager(self, server):
        """Mock SSH manager for testing."""
        server.ssh_manager.create_connection = AsyncMock(return_value="gemini-conn-1")
        server.ssh_manager.execute_command = AsyncMock()
        server.ssh_manager.read_file = AsyncMock()
        server.ssh_manager.write_file = AsyncMock()
        server.ssh_manager.list_directory = AsyncMock()
        server.ssh_manager.disconnect_connection = AsyncMock(return_value=True)
        server.ssh_manager.list_connections = AsyncMock(return_value=[])
        return server.ssh_manager
    
    @pytest.mark.asyncio
    async def test_gemini_cli_batch_analysis_workflow(self, server, mock_ssh_manager):
        """Test Gemini CLI batch analysis workflow patterns."""
        # Mock system analysis responses
        mock_ssh_manager.execute_command.side_effect = [
            CommandResult(stdout="Linux ubuntu 5.4.0-74-generic", stderr="", exit_code=0, execution_time=0.1, command="uname -a"),
            CommandResult(stdout="total 8\ndrwxr-xr-x 2 user user 4096 Jan 1 12:00 logs", stderr="", exit_code=0, execution_time=0.1, command="ls -la /var/log"),
            CommandResult(stdout="user     1234  0.1  0.5  12345  6789 ?        S    12:00   0:01 python3 app.py", stderr="", exit_code=0, execution_time=0.2, command="ps aux | grep python"),
            CommandResult(stdout="              total        used        free      shared  buff/cache   available\nMem:        8000000     2000000     4000000      100000     2000000     5500000", stderr="", exit_code=0, execution_time=0.1, command="free -b")
        ]
        
        mock_ssh_manager.read_file.side_effect = [
            "Jan 1 12:00:01 server app: Application started\nJan 1 12:01:15 server app: Processing request\n",
            "#!/bin/bash\necho 'System check complete'\n"
        ]
        
        # 1. Connect to target system
        connect_response = await server.handle_request({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "analysis-target.example.com",
                    "username": "analyst",
                    "auth_method": "agent"
                }
            },
            "id": 100
        })
        
        assert connect_response["jsonrpc"] == "2.0"
        content = json.loads(connect_response["result"]["content"][0]["text"])
        assert content["success"] is True
        connection_id = content["data"]["connection_id"]
        
        # 2. System information gathering (Gemini CLI pattern)
        system_commands = [
            ("uname -a", "Get system information"),
            ("ls -la /var/log", "List log directory"),
            ("ps aux | grep python", "Find Python processes"),
            ("free -b", "Check memory usage")
        ]
        
        for i, (command, description) in enumerate(system_commands):
            response = await server.handle_request({
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_execute",
                    "arguments": {
                        "connection_id": connection_id,
                        "command": command,
                        "timeout": 30
                    }
                },
                "id": 101 + i
            })
            
            assert response["jsonrpc"] == "2.0"
            content = json.loads(response["result"]["content"][0]["text"])
            assert content["success"] is True
            assert content["data"]["exit_code"] == 0
        
        # 3. Log file analysis
        log_response = await server.handle_request({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_read_file",
                "arguments": {
                    "connection_id": connection_id,
                    "file_path": "/var/log/application.log"
                }
            },
            "id": 110
        })
        
        assert log_response["jsonrpc"] == "2.0"
        content = json.loads(log_response["result"]["content"][0]["text"])
        assert content["success"] is True
        assert "Application started" in content["data"]["content"]
        
        # 4. Script analysis
        script_response = await server.handle_request({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_read_file",
                "arguments": {
                    "connection_id": connection_id,
                    "file_path": "/home/analyst/check_system.sh"
                }
            },
            "id": 111
        })
        
        assert script_response["jsonrpc"] == "2.0"
        content = json.loads(script_response["result"]["content"][0]["text"])
        assert content["success"] is True
        assert "System check complete" in content["data"]["content"]
    
    @pytest.mark.asyncio
    async def test_gemini_cli_structured_data_collection(self, server, mock_ssh_manager):
        """Test Gemini CLI structured data collection patterns."""
        # Mock structured command outputs
        mock_ssh_manager.execute_command.side_effect = [
            CommandResult(stdout='{"version": "1.2.3", "status": "running"}', stderr="", exit_code=0, execution_time=0.1, command="app-status --json"),
            CommandResult(stdout="user1:1001:1001:User One:/home/user1:/bin/bash\nuser2:1002:1002:User Two:/home/user2:/bin/bash", stderr="", exit_code=0, execution_time=0.1, command="cat /etc/passwd | grep user"),
            CommandResult(stdout="tcp        0      0 0.0.0.0:22              0.0.0.0:*               LISTEN\ntcp        0      0 0.0.0.0:80              0.0.0.0:*               LISTEN", stderr="", exit_code=0, execution_time=0.1, command="netstat -tlnp")
        ]
        
        # Connect first
        connect_response = await server.handle_request({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "data-server.example.com",
                    "username": "collector"
                }
            },
            "id": 200
        })
        
        content = json.loads(connect_response["result"]["content"][0]["text"])
        connection_id = content["data"]["connection_id"]
        
        # Collect structured data (typical Gemini CLI pattern)
        data_collection_commands = [
            "app-status --json",
            "cat /etc/passwd | grep user",
            "netstat -tlnp"
        ]
        
        collected_data = []
        for i, command in enumerate(data_collection_commands):
            response = await server.handle_request({
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_execute",
                    "arguments": {
                        "connection_id": connection_id,
                        "command": command
                    }
                },
                "id": 201 + i
            })
            
            assert response["jsonrpc"] == "2.0"
            content = json.loads(response["result"]["content"][0]["text"])
            assert content["success"] is True
            collected_data.append(content["data"])
        
        # Verify structured data collection
        assert len(collected_data) == 3
        assert '{"version": "1.2.3"' in collected_data[0]["stdout"]
        assert "user1:1001" in collected_data[1]["stdout"]
        assert "LISTEN" in collected_data[2]["stdout"]
    
    @pytest.mark.asyncio
    async def test_gemini_cli_error_resilience(self, server, mock_ssh_manager):
        """Test Gemini CLI error resilience patterns."""
        # Mock mixed success/failure responses
        mock_ssh_manager.execute_command.side_effect = [
            CommandResult(stdout="Success command 1", stderr="", exit_code=0, execution_time=0.1, command="echo 'Success command 1'"),
            CommandResult(stdout="", stderr="Command not found", exit_code=127, execution_time=0.1, command="nonexistent-command"),
            CommandResult(stdout="Success command 3", stderr="", exit_code=0, execution_time=0.1, command="echo 'Success command 3'"),
            CommandResult(stdout="", stderr="Permission denied", exit_code=1, execution_time=0.1, command="cat /root/secret")
        ]
        
        # Connect
        connect_response = await server.handle_request({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "test-resilience.example.com",
                    "username": "tester"
                }
            },
            "id": 300
        })
        
        content = json.loads(connect_response["result"]["content"][0]["text"])
        connection_id = content["data"]["connection_id"]
        
        # Execute commands with mixed results (Gemini CLI continues on errors)
        test_commands = [
            "echo 'Success command 1'",
            "nonexistent-command",
            "echo 'Success command 3'",
            "cat /root/secret"
        ]
        
        results = []
        for i, command in enumerate(test_commands):
            response = await server.handle_request({
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_execute",
                    "arguments": {
                        "connection_id": connection_id,
                        "command": command
                    }
                },
                "id": 301 + i
            })
            
            assert response["jsonrpc"] == "2.0"
            content = json.loads(response["result"]["content"][0]["text"])
            assert content["success"] is True  # Tool call succeeds even if command fails
            results.append(content["data"])
        
        # Verify mixed results are handled properly
        assert results[0]["exit_code"] == 0  # Success
        assert results[1]["exit_code"] == 127  # Command not found
        assert results[2]["exit_code"] == 0  # Success
        assert results[3]["exit_code"] == 1  # Permission denied
        
        # Verify error information is preserved
        assert "Command not found" in results[1]["stderr"]
        assert "Permission denied" in results[3]["stderr"]


class TestClaudeDesktopCompatibility:
    """Test compatibility with Claude Desktop client patterns."""
    
    @pytest.fixture
    def server(self):
        """Create MCP server for testing."""
        return MCPServer(max_connections=3, debug=False)
    
    @pytest.fixture
    def mock_ssh_manager(self, server):
        """Mock SSH manager for testing."""
        server.ssh_manager.create_connection = AsyncMock(return_value="desktop-conn-1")
        server.ssh_manager.execute_command = AsyncMock()
        server.ssh_manager.read_file = AsyncMock()
        server.ssh_manager.write_file = AsyncMock()
        server.ssh_manager.list_directory = AsyncMock()
        server.ssh_manager.disconnect_connection = AsyncMock(return_value=True)
        server.ssh_manager.list_connections = AsyncMock(return_value=[])
        return server.ssh_manager
    
    @pytest.mark.asyncio
    async def test_claude_desktop_user_friendly_workflow(self, server, mock_ssh_manager):
        """Test Claude Desktop user-friendly workflow patterns."""
        # Mock user-friendly responses
        mock_ssh_manager.execute_command.side_effect = [
            CommandResult(stdout="Welcome to Ubuntu 20.04.3 LTS", stderr="", exit_code=0, execution_time=0.1, command="cat /etc/issue"),
            CommandResult(stdout="user     pts/0        2024-01-01 12:00 (192.168.1.100)", stderr="", exit_code=0, execution_time=0.1, command="who"),
            CommandResult(stdout="Filesystem      Size  Used Avail Use% Mounted on\n/dev/sda1        20G  5.5G   14G  30% /", stderr="", exit_code=0, execution_time=0.1, command="df -h")
        ]
        
        mock_ssh_manager.list_directory.return_value = [
            {"name": "Documents", "type": "directory", "permissions": "drwxr-xr-x"},
            {"name": "Downloads", "type": "directory", "permissions": "drwxr-xr-x"},
            {"name": "readme.txt", "type": "file", "size": 1024, "permissions": "-rw-r--r--"}
        ]
        
        mock_ssh_manager.read_file.return_value = "Welcome to my server!\nThis is a test file.\n"
        
        # 1. Connect with user-friendly parameters
        connect_response = await server.handle_request({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "my-server.local",
                    "username": "myuser",
                    "auth_method": "key",
                    "key_path": "~/.ssh/id_rsa",
                    "timeout": 30
                }
            },
            "id": 400
        })
        
        assert connect_response["jsonrpc"] == "2.0"
        content = json.loads(connect_response["result"]["content"][0]["text"])
        assert content["success"] is True
        connection_id = content["data"]["connection_id"]
        
        # 2. Basic system information (Claude Desktop style)
        system_info_response = await server.handle_request({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_execute",
                "arguments": {
                    "connection_id": connection_id,
                    "command": "cat /etc/issue"
                }
            },
            "id": 401
        })
        
        assert system_info_response["jsonrpc"] == "2.0"
        content = json.loads(system_info_response["result"]["content"][0]["text"])
        assert content["success"] is True
        assert "Ubuntu" in content["data"]["stdout"]
        
        # 3. Check who's logged in
        who_response = await server.handle_request({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_execute",
                "arguments": {
                    "connection_id": connection_id,
                    "command": "who"
                }
            },
            "id": 402
        })
        
        content = json.loads(who_response["result"]["content"][0]["text"])
        assert content["success"] is True
        assert "pts/0" in content["data"]["stdout"]
        
        # 4. Check disk space
        df_response = await server.handle_request({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_execute",
                "arguments": {
                    "connection_id": connection_id,
                    "command": "df -h"
                }
            },
            "id": 403
        })
        
        content = json.loads(df_response["result"]["content"][0]["text"])
        assert content["success"] is True
        assert "30%" in content["data"]["stdout"]
        
        # 5. Browse home directory
        list_response = await server.handle_request({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_list_directory",
                "arguments": {
                    "connection_id": connection_id,
                    "directory_path": "/home/myuser",
                    "detailed": True
                }
            },
            "id": 404
        })
        
        content = json.loads(list_response["result"]["content"][0]["text"])
        assert content["success"] is True
        assert len(content["data"]["entries"]) == 3
        assert any(entry["name"] == "Documents" for entry in content["data"]["entries"])
        
        # 6. Read a file
        read_response = await server.handle_request({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_read_file",
                "arguments": {
                    "connection_id": connection_id,
                    "file_path": "/home/myuser/readme.txt"
                }
            },
            "id": 405
        })
        
        content = json.loads(read_response["result"]["content"][0]["text"])
        assert content["success"] is True
        assert "Welcome to my server!" in content["data"]["content"]
    
    @pytest.mark.asyncio
    async def test_claude_desktop_file_management(self, server, mock_ssh_manager):
        """Test Claude Desktop file management patterns."""
        # Mock file operations
        mock_ssh_manager.write_file.return_value = None
        mock_ssh_manager.read_file.side_effect = [
            "Original content\n",
            "Updated content\nNew line added\n"
        ]
        
        # Connect
        connect_response = await server.handle_request({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "file-server.local",
                    "username": "fileuser"
                }
            },
            "id": 500
        })
        
        content = json.loads(connect_response["result"]["content"][0]["text"])
        connection_id = content["data"]["connection_id"]
        
        # 1. Read existing file
        read_original = await server.handle_request({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_read_file",
                "arguments": {
                    "connection_id": connection_id,
                    "file_path": "/home/fileuser/document.txt"
                }
            },
            "id": 501
        })
        
        content = json.loads(read_original["result"]["content"][0]["text"])
        assert content["success"] is True
        assert "Original content" in content["data"]["content"]
        
        # 2. Write updated file
        write_response = await server.handle_request({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_write_file",
                "arguments": {
                    "connection_id": connection_id,
                    "file_path": "/home/fileuser/document.txt",
                    "content": "Updated content\nNew line added\n",
                    "create_dirs": False
                }
            },
            "id": 502
        })
        
        content = json.loads(write_response["result"]["content"][0]["text"])
        assert content["success"] is True
        assert content["data"]["status"] == "success"
        
        # 3. Verify file was updated
        read_updated = await server.handle_request({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_read_file",
                "arguments": {
                    "connection_id": connection_id,
                    "file_path": "/home/fileuser/document.txt"
                }
            },
            "id": 503
        })
        
        content = json.loads(read_updated["result"]["content"][0]["text"])
        assert content["success"] is True
        assert "Updated content" in content["data"]["content"]
        assert "New line added" in content["data"]["content"]
    
    @pytest.mark.asyncio
    async def test_claude_desktop_connection_management(self, server, mock_ssh_manager):
        """Test Claude Desktop connection management patterns."""
        # Mock connection info
        mock_connections = [
            ConnectionInfo.create("server1.local", "user1", 22),
            ConnectionInfo.create("server2.local", "user2", 2222)
        ]
        mock_ssh_manager.list_connections.return_value = mock_connections
        
        # 1. List active connections
        list_response = await server.handle_request({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_list_connections",
                "arguments": {}
            },
            "id": 600
        })
        
        assert list_response["jsonrpc"] == "2.0"
        content = json.loads(list_response["result"]["content"][0]["text"])
        assert content["success"] is True
        assert content["data"]["total"] == 2
        assert len(content["data"]["connections"]) == 2
        
        # Verify connection details
        connections = content["data"]["connections"]
        assert connections[0]["hostname"] == "server1.local"
        assert connections[1]["hostname"] == "server2.local"
        
        # 2. Disconnect specific connection
        disconnect_response = await server.handle_request({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_disconnect",
                "arguments": {
                    "connection_id": connections[0]["connection_id"]
                }
            },
            "id": 601
        })
        
        content = json.loads(disconnect_response["result"]["content"][0]["text"])
        assert content["success"] is True
        assert content["data"]["status"] == "disconnected"


class TestMCPProtocolCompliance:
    """Test MCP protocol standard compliance."""
    
    @pytest.fixture
    def server(self):
        """Create MCP server for testing."""
        return MCPServer(max_connections=5, debug=True)
    
    @pytest.mark.asyncio
    async def test_json_rpc_2_0_compliance(self, server):
        """Test JSON-RPC 2.0 protocol compliance."""
        # Test valid request format
        valid_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "id": 1
        }
        
        response = await server.handle_request(valid_request)
        
        # Verify response format
        assert "jsonrpc" in response
        assert response["jsonrpc"] == "2.0"
        assert "id" in response
        assert response["id"] == 1
        assert ("result" in response) or ("error" in response)
        assert not (("result" in response) and ("error" in response))
        
        # Test notification (no id)
        notification = {
            "jsonrpc": "2.0",
            "method": "tools/list"
        }
        
        response = await server.handle_request(notification)
        assert response["jsonrpc"] == "2.0"
        assert "id" not in response or response["id"] is None
    
    @pytest.mark.asyncio
    async def test_mcp_initialize_compliance(self, server):
        """Test MCP initialize method compliance."""
        request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            },
            "id": 1
        }
        
        response = await server.handle_request(request)
        
        # Verify initialize response structure
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        
        result = response["result"]
        assert "protocolVersion" in result
        assert "capabilities" in result
        assert "serverInfo" in result
        
        # Verify server info
        server_info = result["serverInfo"]
        assert "name" in server_info
        assert "version" in server_info
        assert server_info["name"] == "ssh-mcp-server"
        
        # Verify capabilities
        capabilities = result["capabilities"]
        assert "tools" in capabilities
    
    @pytest.mark.asyncio
    async def test_mcp_tools_list_compliance(self, server):
        """Test MCP tools/list method compliance."""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": 2
        }
        
        response = await server.handle_request(request)
        
        # Verify tools/list response structure
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 2
        assert "result" in response
        
        result = response["result"]
        assert "tools" in result
        assert isinstance(result["tools"], list)
        
        # Verify each tool schema
        for tool in result["tools"]:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
            
            # Verify input schema structure
            input_schema = tool["inputSchema"]
            assert "type" in input_schema
            assert input_schema["type"] == "object"
            assert "properties" in input_schema
            
            # Verify properties are properly defined
            properties = input_schema["properties"]
            assert isinstance(properties, dict)
            
            for prop_name, prop_schema in properties.items():
                assert "type" in prop_schema
                assert "description" in prop_schema
    
    @pytest.mark.asyncio
    async def test_mcp_tools_call_compliance(self, server):
        """Test MCP tools/call method compliance."""
        # Mock SSH manager
        server.ssh_manager.create_connection = AsyncMock(return_value="test-conn-1")
        server.ssh_manager.list_connections = AsyncMock(return_value=[
            ConnectionInfo.create("test.com", "user", 22)
        ])
        
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "test.com",
                    "username": "user"
                }
            },
            "id": 3
        }
        
        response = await server.handle_request(request)
        
        # Verify tools/call response structure
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 3
        assert "result" in response
        
        result = response["result"]
        assert "content" in result
        assert isinstance(result["content"], list)
        assert len(result["content"]) > 0
        
        # Verify content structure
        content_item = result["content"][0]
        assert "type" in content_item
        assert "text" in content_item
        assert content_item["type"] == "text"
        
        # Verify content is valid JSON
        content_data = json.loads(content_item["text"])
        assert "success" in content_data
        assert isinstance(content_data["success"], bool)
    
    @pytest.mark.asyncio
    async def test_error_response_compliance(self, server):
        """Test MCP error response compliance."""
        # Test invalid method
        invalid_request = {
            "jsonrpc": "2.0",
            "method": "invalid_method",
            "id": 4
        }
        
        response = await server.handle_request(invalid_request)
        
        # Verify error response structure
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 4
        assert "error" in response
        assert "result" not in response
        
        error = response["error"]
        assert "code" in error
        assert "message" in error
        assert isinstance(error["code"], int)
        assert isinstance(error["message"], str)
        
        # Test invalid parameters
        invalid_params_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect"
                # Missing required arguments
            },
            "id": 5
        }
        
        response = await server.handle_request(invalid_params_request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 5
        assert "error" in response
        
        error = response["error"]
        assert error["code"] == MCPErrorCode.TOOL_ERROR
        assert "Required parameter" in error["message"]
    
    @pytest.mark.asyncio
    async def test_tool_schema_validation_compliance(self, server):
        """Test tool schema validation compliance."""
        # Get all tool schemas
        tool_schemas = get_all_tool_schemas()
        
        # Verify all registered tools have valid schemas
        for tool_name in server.tools.keys():
            assert tool_name in tool_schemas
            
            schema = tool_schemas[tool_name]
            assert schema.name == tool_name
            assert schema.description
            assert isinstance(schema.parameters, list)
            
            # Verify parameter schemas
            for param in schema.parameters:
                assert param.name
                assert param.type
                assert param.description
                assert isinstance(param.required, bool)
        
        # Test parameter validation
        from ssh_mcp_server.tools import validate_tool_parameters, ToolError
        
        # Valid parameters
        valid_params = {
            "hostname": "test.com",
            "username": "user",
            "port": 22,
            "auth_method": "agent"
        }
        
        validated = validate_tool_parameters("ssh_connect", valid_params)
        assert validated["hostname"] == "test.com"
        assert validated["username"] == "user"
        assert validated["port"] == 22
        assert validated["auth_method"] == "agent"
        
        # Invalid parameters
        invalid_params = {
            "hostname": "test.com"
            # Missing required username
        }
        
        with pytest.raises(ToolError) as exc_info:
            validate_tool_parameters("ssh_connect", invalid_params)
        
        assert "Required parameter" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_content_type_compliance(self, server):
        """Test content type handling compliance."""
        # Mock SSH manager
        server.ssh_manager.execute_command = AsyncMock(return_value=CommandResult(
            stdout="Hello World",
            stderr="",
            exit_code=0,
            execution_time=0.1,
            command="echo 'Hello World'"
        ))
        
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_execute",
                "arguments": {
                    "connection_id": "test-conn",
                    "command": "echo 'Hello World'"
                }
            },
            "id": 6
        }
        
        response = await server.handle_request(request)
        
        # Verify content structure
        assert "result" in response
        result = response["result"]
        assert "content" in result
        
        content = result["content"]
        assert isinstance(content, list)
        assert len(content) == 1
        
        content_item = content[0]
        assert content_item["type"] == "text"
        assert "text" in content_item
        
        # Verify text content is valid JSON
        text_data = json.loads(content_item["text"])
        assert isinstance(text_data, dict)
        assert "success" in text_data
        assert "data" in text_data or "error" in text_data


class TestMCPClientCompatibilityIntegration:
    """Integration tests for MCP client compatibility."""
    
    @pytest.fixture
    def server(self):
        """Create MCP server for testing."""
        return MCPServer(max_connections=10, debug=True)
    
    @pytest.mark.asyncio
    async def test_multi_client_compatibility(self, server):
        """Test that server works with multiple client patterns simultaneously."""
        # Mock SSH manager
        server.ssh_manager.create_connection = AsyncMock(side_effect=[
            "claude-code-conn",
            "gemini-cli-conn", 
            "claude-desktop-conn"
        ])
        server.ssh_manager.execute_command = AsyncMock(return_value=CommandResult(
            stdout="Multi-client test",
            stderr="",
            exit_code=0,
            execution_time=0.1,
            command="echo 'Multi-client test'"
        ))
        server.ssh_manager.list_connections = AsyncMock(return_value=[])
        
        # Simulate different client patterns concurrently
        tasks = []
        
        # Claude Code pattern
        claude_code_task = server.handle_request({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "claude-code.example.com",
                    "username": "developer",
                    "auth_method": "key",
                    "key_path": "~/.ssh/id_rsa"
                }
            },
            "id": "claude-code-1"
        })
        tasks.append(claude_code_task)
        
        # Gemini CLI pattern
        gemini_cli_task = server.handle_request({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "gemini-cli.example.com",
                    "username": "analyst",
                    "auth_method": "agent"
                }
            },
            "id": "gemini-cli-1"
        })
        tasks.append(gemini_cli_task)
        
        # Claude Desktop pattern
        claude_desktop_task = server.handle_request({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "claude-desktop.local",
                    "username": "user",
                    "timeout": 30
                }
            },
            "id": "claude-desktop-1"
        })
        tasks.append(claude_desktop_task)
        
        # Execute all tasks concurrently
        responses = await asyncio.gather(*tasks)
        
        # Verify all clients succeeded
        for i, response in enumerate(responses):
            assert response["jsonrpc"] == "2.0"
            assert "result" in response
            content = json.loads(response["result"]["content"][0]["text"])
            assert content["success"] is True
    
    @pytest.mark.asyncio
    async def test_protocol_version_compatibility(self, server):
        """Test protocol version compatibility across clients."""
        # Test different protocol version requests
        protocol_versions = ["2024-11-05", "2024-10-07", "2024-09-01"]
        
        for version in protocol_versions:
            request = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": version,
                    "capabilities": {},
                    "clientInfo": {
                        "name": f"test-client-{version}",
                        "version": "1.0.0"
                    }
                },
                "id": f"init-{version}"
            }
            
            response = await server.handle_request(request)
            
            # Server should respond with its supported version
            assert response["jsonrpc"] == "2.0"
            assert "result" in response
            assert response["result"]["protocolVersion"] == "2024-11-05"
    
    @pytest.mark.asyncio
    async def test_capability_negotiation(self, server):
        """Test capability negotiation with different clients."""
        # Test different capability sets
        capability_sets = [
            {"tools": {}},  # Basic tools capability
            {"tools": {}, "sampling": {}},  # Tools + sampling
            {"roots": {"listChanged": True}, "tools": {}},  # Roots + tools
        ]
        
        for i, capabilities in enumerate(capability_sets):
            request = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": capabilities,
                    "clientInfo": {
                        "name": f"capability-test-{i}",
                        "version": "1.0.0"
                    }
                },
                "id": f"cap-{i}"
            }
            
            response = await server.handle_request(request)
            
            # Server should respond with its capabilities
            assert response["jsonrpc"] == "2.0"
            assert "result" in response
            assert "capabilities" in response["result"]
            assert "tools" in response["result"]["capabilities"]


if __name__ == "__main__":
    pytest.main([__file__])