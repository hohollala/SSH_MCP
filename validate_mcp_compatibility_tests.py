#!/usr/bin/env python3
"""
MCP Client Compatibility Test Validation Script

This script validates the MCP client compatibility tests without requiring pytest.
It tests compatibility with Claude Code, Gemini CLI, Claude Desktop, and MCP protocol compliance.

Requirements covered:
- 7.1: Claude Code compatibility
- 7.2: Gemini CLI compatibility  
- 7.3: Claude Desktop compatibility
- 7.4: MCP protocol standard compliance
"""

import asyncio
import json
import sys
import traceback
from typing import Dict, Any, List
from unittest.mock import AsyncMock

# Import SSH MCP Server components
from ssh_mcp_server.server import MCPServer
from ssh_mcp_server.models import SSHConfig, CommandResult, ConnectionInfo
from ssh_mcp_server.manager import SSHManagerError
from ssh_mcp_server.tools import get_all_tool_schemas


class MCPCompatibilityValidator:
    """Validates MCP client compatibility."""
    
    def __init__(self):
        self.server = None
        self.test_results = []
        self.total_tests = 0
        self.passed_tests = 0
    
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test result."""
        self.total_tests += 1
        if success:
            self.passed_tests += 1
            print(f"  ✓ {test_name}")
            if details:
                print(f"    ✓ {details}")
        else:
            print(f"  ✗ {test_name}")
            if details:
                print(f"    ✗ {details}")
        
        self.test_results.append({
            "name": test_name,
            "success": success,
            "details": details
        })
    
    async def setup_server(self):
        """Set up MCP server for testing."""
        self.server = MCPServer(max_connections=10, debug=True)
        
        # Mock SSH manager for testing
        self.server.ssh_manager.create_connection = AsyncMock()
        self.server.ssh_manager.execute_command = AsyncMock()
        self.server.ssh_manager.read_file = AsyncMock()
        self.server.ssh_manager.write_file = AsyncMock()
        self.server.ssh_manager.list_directory = AsyncMock()
        self.server.ssh_manager.disconnect_connection = AsyncMock(return_value=True)
        self.server.ssh_manager.list_connections = AsyncMock(return_value=[])
        
        # Mock the SSH config validation to avoid file system checks
        from unittest.mock import patch
        self.ssh_config_patch = patch('ssh_mcp_server.models.SSHConfig._validate_auth_requirements')
        self.ssh_config_patch.start()
        
        await self.server.start()
    
    async def cleanup_server(self):
        """Clean up MCP server."""
        if self.server:
            await self.server.stop()
        
        # Stop the SSH config patch
        if hasattr(self, 'ssh_config_patch'):
            self.ssh_config_patch.stop()
    
    async def test_claude_code_compatibility(self):
        """Test Claude Code compatibility patterns."""
        print("🎨 Testing Claude Code compatibility...")
        
        try:
            # Mock responses for Claude Code workflow
            self.server.ssh_manager.create_connection.return_value = "claude-conn-1"
            self.server.ssh_manager.execute_command.return_value = CommandResult(
                stdout="Python 3.9.7\n",
                stderr="",
                exit_code=0,
                execution_time=0.2,
                command="python3 --version"
            )
            self.server.ssh_manager.read_file.return_value = "#!/usr/bin/env python3\nprint('Hello World')\n"
            self.server.ssh_manager.list_directory.return_value = [
                {"name": "app.py", "type": "file", "size": 45},
                {"name": "requirements.txt", "type": "file", "size": 123}
            ]
            
            # Test initialization sequence
            init_response = await self.server.handle_request({
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"roots": {"listChanged": True}, "sampling": {}},
                    "clientInfo": {"name": "Claude Code", "version": "1.0.0"}
                },
                "id": 1
            })
            
            success = (init_response.get("jsonrpc") == "2.0" and 
                      "result" in init_response and
                      init_response["result"]["protocolVersion"] == "2024-11-05")
            self.log_test("Claude Code initialization", success, "Initialize request successful")
            
            # Test tools discovery
            tools_response = await self.server.handle_request({
                "jsonrpc": "2.0",
                "method": "tools/list",
                "id": 2
            })
            
            success = (tools_response.get("jsonrpc") == "2.0" and
                      "result" in tools_response and
                      len(tools_response["result"]["tools"]) == 7)
            self.log_test("Claude Code tools discovery", success, "All 7 tools discovered")
            
            # Test interactive development workflow
            connect_response = await self.server.handle_request({
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
            
            success = ("result" in connect_response)
            if success:
                content = json.loads(connect_response["result"]["content"][0]["text"])
                success = content.get("success", False)
                connection_id = content.get("data", {}).get("connection_id", "claude-conn-1")
            
            self.log_test("Claude Code SSH connection", success, "Development server connection")
            
            # Test command execution
            if success:
                exec_response = await self.server.handle_request({
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
                
                success = ("result" in exec_response)
                if success:
                    content = json.loads(exec_response["result"]["content"][0]["text"])
                    success = (content.get("success", False) and 
                              "Python 3.9.7" in content.get("data", {}).get("stdout", ""))
                
                self.log_test("Claude Code command execution", success, "Python version check")
            
            # Test file operations
            if success:
                read_response = await self.server.handle_request({
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "ssh_read_file",
                        "arguments": {
                            "connection_id": connection_id,
                            "file_path": "/home/developer/project/app.py"
                        }
                    },
                    "id": 12
                })
                
                success = ("result" in read_response)
                if success:
                    content = json.loads(read_response["result"]["content"][0]["text"])
                    success = (content.get("success", False) and 
                              "Hello World" in content.get("data", {}).get("content", ""))
                
                self.log_test("Claude Code file reading", success, "Source file access")
            
        except Exception as e:
            self.log_test("Claude Code compatibility", False, f"Error: {str(e)}")
    
    async def test_gemini_cli_compatibility(self):
        """Test Gemini CLI compatibility patterns."""
        print("🔍 Testing Gemini CLI compatibility...")
        
        try:
            # Mock responses for Gemini CLI workflow
            self.server.ssh_manager.create_connection.return_value = "gemini-conn-1"
            # Use return_value instead of side_effect to avoid exhaustion
            self.server.ssh_manager.execute_command.return_value = CommandResult(
                stdout="Linux ubuntu 5.4.0-74-generic", 
                stderr="", 
                exit_code=0, 
                execution_time=0.1, 
                command="uname -a"
            )
            
            # Test connection
            connect_response = await self.server.handle_request({
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
            
            success = ("result" in connect_response)
            if success:
                content = json.loads(connect_response["result"]["content"][0]["text"])
                success = content.get("success", False)
                connection_id = content.get("data", {}).get("connection_id", "gemini-conn-1")
            
            self.log_test("Gemini CLI connection", success, "Analysis target connection")
            
            # Test system analysis commands
            if success:
                system_commands = [
                    ("uname -a", "System information", "Linux ubuntu"),
                    ("app-status --json", "Application status", '{"version": "1.2.3"'),
                    ("cat /etc/passwd | grep user", "User information", "user1:1001")
                ]
                
                for i, (command, description, expected_output) in enumerate(system_commands):
                    # Set specific mock response for each command
                    if "json" in command:
                        self.server.ssh_manager.execute_command.return_value = CommandResult(
                            stdout='{"version": "1.2.3", "status": "running"}',
                            stderr="", exit_code=0, execution_time=0.1, command=command
                        )
                    elif "passwd" in command:
                        self.server.ssh_manager.execute_command.return_value = CommandResult(
                            stdout="user1:1001:1001:User One:/home/user1:/bin/bash",
                            stderr="", exit_code=0, execution_time=0.1, command=command
                        )
                    else:
                        self.server.ssh_manager.execute_command.return_value = CommandResult(
                            stdout="Linux ubuntu 5.4.0-74-generic",
                            stderr="", exit_code=0, execution_time=0.1, command=command
                        )
                    
                    exec_response = await self.server.handle_request({
                        "jsonrpc": "2.0",
                        "method": "tools/call",
                        "params": {
                            "name": "ssh_execute",
                            "arguments": {
                                "connection_id": connection_id,
                                "command": command
                            }
                        },
                        "id": 101 + i
                    })
                    
                    cmd_success = ("result" in exec_response)
                    if cmd_success:
                        content = json.loads(exec_response["result"]["content"][0]["text"])
                        cmd_success = content.get("success", False)
                    
                    self.log_test(f"Gemini CLI {description.lower()}", cmd_success, description)
            
            # Test structured data collection
            if success:
                # Reset the mock to return JSON data
                self.server.ssh_manager.execute_command.return_value = CommandResult(
                    stdout='{"version": "1.2.3", "status": "running"}',
                    stderr="",
                    exit_code=0,
                    execution_time=0.1,
                    command="app-status --json"
                )
                
                # Test JSON output parsing
                json_response = await self.server.handle_request({
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "ssh_execute",
                        "arguments": {
                            "connection_id": connection_id,
                            "command": "app-status --json"
                        }
                    },
                    "id": 110
                })
                
                success = ("result" in json_response)
                if success:
                    content = json.loads(json_response["result"]["content"][0]["text"])
                    success = (content.get("success", False) and 
                              '"version": "1.2.3"' in content.get("data", {}).get("stdout", ""))
                
                self.log_test("Gemini CLI structured data", success, "JSON output parsing")
            
        except Exception as e:
            self.log_test("Gemini CLI compatibility", False, f"Error: {str(e)}")
    
    async def test_claude_desktop_compatibility(self):
        """Test Claude Desktop compatibility patterns."""
        print("🖥️  Testing Claude Desktop compatibility...")
        
        try:
            # Mock responses for Claude Desktop workflow
            self.server.ssh_manager.create_connection.return_value = "desktop-conn-1"
            self.server.ssh_manager.execute_command.side_effect = [
                CommandResult(stdout="Welcome to Ubuntu 20.04.3 LTS", stderr="", exit_code=0, execution_time=0.1, command="cat /etc/issue"),
                CommandResult(stdout="user     pts/0        2024-01-01 12:00 (192.168.1.100)", stderr="", exit_code=0, execution_time=0.1, command="who"),
                CommandResult(stdout="Filesystem      Size  Used Avail Use% Mounted on\n/dev/sda1        20G  5.5G   14G  30% /", stderr="", exit_code=0, execution_time=0.1, command="df -h")
            ]
            self.server.ssh_manager.list_directory.return_value = [
                {"name": "Documents", "type": "directory", "permissions": "drwxr-xr-x"},
                {"name": "readme.txt", "type": "file", "size": 1024, "permissions": "-rw-r--r--"}
            ]
            self.server.ssh_manager.read_file.return_value = "Welcome to my server!\nThis is a test file.\n"
            
            # Test user-friendly connection
            connect_response = await self.server.handle_request({
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
            
            success = ("result" in connect_response)
            if success:
                content = json.loads(connect_response["result"]["content"][0]["text"])
                success = content.get("success", False)
                connection_id = content.get("data", {}).get("connection_id", "desktop-conn-1")
            
            self.log_test("Claude Desktop connection", success, "User-friendly connection")
            
            # Test basic system information
            if success:
                info_response = await self.server.handle_request({
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
                
                success = ("result" in info_response)
                if success:
                    content = json.loads(info_response["result"]["content"][0]["text"])
                    success = (content.get("success", False) and 
                              "Ubuntu" in content.get("data", {}).get("stdout", ""))
                
                self.log_test("Claude Desktop system info", success, "System information display")
            
            # Test directory browsing
            if success:
                list_response = await self.server.handle_request({
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
                    "id": 402
                })
                
                success = ("result" in list_response)
                if success:
                    content = json.loads(list_response["result"]["content"][0]["text"])
                    success = (content.get("success", False) and 
                              len(content.get("data", {}).get("entries", [])) >= 2)
                
                self.log_test("Claude Desktop directory browsing", success, "Home directory listing")
            
            # Test file management
            if success:
                read_response = await self.server.handle_request({
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "ssh_read_file",
                        "arguments": {
                            "connection_id": connection_id,
                            "file_path": "/home/myuser/readme.txt"
                        }
                    },
                    "id": 403
                })
                
                success = ("result" in read_response)
                if success:
                    content = json.loads(read_response["result"]["content"][0]["text"])
                    success = (content.get("success", False) and 
                              "Welcome to my server!" in content.get("data", {}).get("content", ""))
                
                self.log_test("Claude Desktop file management", success, "File reading")
            
        except Exception as e:
            self.log_test("Claude Desktop compatibility", False, f"Error: {str(e)}")
    
    async def test_mcp_protocol_compliance(self):
        """Test MCP protocol standard compliance."""
        print("📋 Testing MCP protocol compliance...")
        
        try:
            # Test JSON-RPC 2.0 compliance
            valid_request = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "id": 1
            }
            
            response = await self.server.handle_request(valid_request)
            
            success = (response.get("jsonrpc") == "2.0" and 
                      response.get("id") == 1 and
                      (("result" in response) or ("error" in response)) and
                      not (("result" in response) and ("error" in response)))
            
            self.log_test("JSON-RPC 2.0 format", success, "Valid response structure")
            
            # Test MCP initialize compliance
            init_request = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test-client", "version": "1.0.0"}
                },
                "id": 2
            }
            
            response = await self.server.handle_request(init_request)
            
            success = ("result" in response and
                      "protocolVersion" in response["result"] and
                      "capabilities" in response["result"] and
                      "serverInfo" in response["result"])
            
            self.log_test("MCP initialize compliance", success, "Proper initialize response")
            
            # Test tools/list compliance
            tools_request = {
                "jsonrpc": "2.0",
                "method": "tools/list",
                "id": 3
            }
            
            response = await self.server.handle_request(tools_request)
            
            success = ("result" in response and
                      "tools" in response["result"] and
                      isinstance(response["result"]["tools"], list))
            
            if success:
                # Verify tool schema structure
                for tool in response["result"]["tools"]:
                    if not all(key in tool for key in ["name", "description", "inputSchema"]):
                        success = False
                        break
                    if tool["inputSchema"].get("type") != "object":
                        success = False
                        break
            
            self.log_test("MCP tools/list compliance", success, "Valid tool schemas")
            
            # Test error response compliance
            invalid_request = {
                "jsonrpc": "2.0",
                "method": "invalid_method",
                "id": 4
            }
            
            response = await self.server.handle_request(invalid_request)
            
            success = ("error" in response and
                      "result" not in response and
                      "code" in response["error"] and
                      "message" in response["error"] and
                      isinstance(response["error"]["code"], int))
            
            self.log_test("MCP error response compliance", success, "Proper error format")
            
            # Test tool schema validation
            tool_schemas = get_all_tool_schemas()
            
            success = len(tool_schemas) == 7
            if success:
                for tool_name in self.server.tools.keys():
                    if tool_name not in tool_schemas:
                        success = False
                        break
                    
                    schema = tool_schemas[tool_name]
                    if not (schema.name and schema.description and isinstance(schema.parameters, list)):
                        success = False
                        break
            
            self.log_test("Tool schema validation", success, "All tools have valid schemas")
            
            # Test content type compliance
            self.server.ssh_manager.execute_command.return_value = CommandResult(
                stdout="Test output",
                stderr="",
                exit_code=0,
                execution_time=0.1,
                command="echo 'Test output'"
            )
            
            tools_call_request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_execute",
                    "arguments": {
                        "connection_id": "test-conn",
                        "command": "echo 'Test output'"
                    }
                },
                "id": 5
            }
            
            response = await self.server.handle_request(tools_call_request)
            
            success = ("result" in response and
                      "content" in response["result"] and
                      isinstance(response["result"]["content"], list) and
                      len(response["result"]["content"]) > 0)
            
            if success:
                content_item = response["result"]["content"][0]
                success = (content_item.get("type") == "text" and
                          "text" in content_item)
                
                if success:
                    # Verify text content is valid JSON
                    try:
                        text_data = json.loads(content_item["text"])
                        success = isinstance(text_data, dict) and "success" in text_data
                    except json.JSONDecodeError:
                        success = False
            
            self.log_test("Content type compliance", success, "Valid content structure")
            
        except Exception as e:
            self.log_test("MCP protocol compliance", False, f"Error: {str(e)}")
    
    async def test_multi_client_compatibility(self):
        """Test multi-client compatibility."""
        print("🔄 Testing multi-client compatibility...")
        
        try:
            # Reset mocks for multi-client test
            self.server.ssh_manager.create_connection.side_effect = [
                "claude-code-conn",
                "gemini-cli-conn",
                "claude-desktop-conn"
            ]
            
            # Test concurrent connections from different client patterns
            tasks = []
            
            # Claude Code pattern
            claude_task = self.server.handle_request({
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
            tasks.append(claude_task)
            
            # Gemini CLI pattern
            gemini_task = self.server.handle_request({
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
            tasks.append(gemini_task)
            
            # Claude Desktop pattern
            desktop_task = self.server.handle_request({
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
            tasks.append(desktop_task)
            
            # Execute all tasks concurrently
            responses = await asyncio.gather(*tasks)
            
            # Verify all clients succeeded
            success = True
            for response in responses:
                if response.get("jsonrpc") != "2.0" or "result" not in response:
                    success = False
                    break
                
                try:
                    content = json.loads(response["result"]["content"][0]["text"])
                    if not content.get("success", False):
                        success = False
                        break
                except (json.JSONDecodeError, KeyError, IndexError):
                    success = False
                    break
            
            self.log_test("Multi-client compatibility", success, "All client patterns work simultaneously")
            
        except Exception as e:
            self.log_test("Multi-client compatibility", False, f"Error: {str(e)}")
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "="*60)
        print(f"📊 Test Results: {self.passed_tests}/{self.total_tests} tests passed")
        
        if self.passed_tests == self.total_tests:
            print("🎉 All MCP client compatibility tests passed!")
            return True
        else:
            print(f"❌ {self.total_tests - self.passed_tests} tests failed")
            
            # Print failed tests
            print("\nFailed tests:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['name']}: {result['details']}")
            
            return False
    
    async def run_all_tests(self):
        """Run all compatibility tests."""
        print("🚀 Starting MCP Client Compatibility Test Validation")
        print("="*60)
        
        try:
            await self.setup_server()
            
            await self.test_claude_code_compatibility()
            print("✅ Claude Code compatibility tests completed!\n")
            
            await self.test_gemini_cli_compatibility()
            print("✅ Gemini CLI compatibility tests completed!\n")
            
            await self.test_claude_desktop_compatibility()
            print("✅ Claude Desktop compatibility tests completed!\n")
            
            await self.test_mcp_protocol_compliance()
            print("✅ MCP protocol compliance tests completed!\n")
            
            await self.test_multi_client_compatibility()
            print("✅ Multi-client compatibility tests completed!\n")
            
            return self.print_summary()
            
        except Exception as e:
            print(f"❌ Test execution failed: {str(e)}")
            traceback.print_exc()
            return False
        
        finally:
            await self.cleanup_server()


async def main():
    """Main function."""
    validator = MCPCompatibilityValidator()
    success = await validator.run_all_tests()
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())