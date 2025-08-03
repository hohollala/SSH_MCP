#!/usr/bin/env python3
"""
SSH MCP Server Usage Examples

This script demonstrates various usage patterns and workflows
for the SSH MCP Server with different AI clients.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from ssh_mcp_server.server import MCPServer


class MCPUsageExamples:
    """Examples of SSH MCP Server usage patterns."""
    
    def __init__(self):
        self.server = MCPServer(max_connections=5, debug=True)
    
    async def start_server(self):
        """Start the MCP server."""
        await self.server.start()
        print("🚀 SSH MCP Server started")
    
    async def stop_server(self):
        """Stop the MCP server."""
        await self.server.stop()
        print("🛑 SSH MCP Server stopped")
    
    async def send_request(self, request):
        """Send a request to the MCP server and return the response."""
        response = await self.server.handle_request(request)
        return response
    
    def print_example(self, title, description):
        """Print example header."""
        print(f"\n{'='*60}")
        print(f"📋 {title}")
        print(f"{'='*60}")
        print(f"Description: {description}\n")
    
    async def example_basic_connection(self):
        """Example: Basic SSH connection establishment."""
        self.print_example(
            "Basic SSH Connection",
            "Establish a basic SSH connection using key authentication"
        )
        
        # Connection request
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "example.com",
                    "username": "developer",
                    "auth_method": "key",
                    "key_path": "~/.ssh/id_rsa",
                    "timeout": 30
                }
            },
            "id": 1
        }
        
        print("Request:")
        print(json.dumps(request, indent=2))
        
        response = await self.send_request(request)
        print("\nResponse:")
        print(json.dumps(response, indent=2))
        
        # Extract connection ID for future use
        if 'result' in response:
            result_data = json.loads(response['result']['content'][0]['text'])
            if result_data.get('success'):
                connection_id = result_data.get('connection_id')
                print(f"\n✅ Connection established with ID: {connection_id}")
                return connection_id
        
        print("\n❌ Connection failed")
        return None
    
    async def example_command_execution(self, connection_id):
        """Example: Execute commands on remote server."""
        self.print_example(
            "Command Execution",
            "Execute various commands on the remote server"
        )
        
        commands = [
            "whoami",
            "pwd",
            "ls -la",
            "uname -a",
            "df -h",
            "free -m"
        ]
        
        for i, command in enumerate(commands, 1):
            print(f"\n--- Command {i}: {command} ---")
            
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_execute",
                    "arguments": {
                        "connection_id": connection_id,
                        "command": command,
                        "timeout": 10
                    }
                },
                "id": i + 10
            }
            
            response = await self.send_request(request)
            
            if 'result' in response:
                result_data = json.loads(response['result']['content'][0]['text'])
                if result_data.get('success'):
                    data = result_data['data']
                    print(f"Exit Code: {data['exit_code']}")
                    print(f"Stdout: {data['stdout']}")
                    if data['stderr']:
                        print(f"Stderr: {data['stderr']}")
                else:
                    print(f"❌ Command failed: {result_data.get('message', 'Unknown error')}")
            else:
                print(f"❌ Request failed: {response.get('error', {}).get('message', 'Unknown error')}")
    
    async def example_file_operations(self, connection_id):
        """Example: File operations on remote server."""
        self.print_example(
            "File Operations",
            "Demonstrate reading, writing, and listing files"
        )
        
        # 1. List home directory
        print("1. Listing home directory...")
        list_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_list_directory",
                "arguments": {
                    "connection_id": connection_id,
                    "directory_path": "~",
                    "detailed": True,
                    "show_hidden": False
                }
            },
            "id": 20
        }
        
        response = await self.send_request(list_request)
        print("Response:", json.dumps(response, indent=2))
        
        # 2. Read a system file
        print("\n2. Reading /etc/hostname...")
        read_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_read_file",
                "arguments": {
                    "connection_id": connection_id,
                    "file_path": "/etc/hostname"
                }
            },
            "id": 21
        }
        
        response = await self.send_request(read_request)
        print("Response:", json.dumps(response, indent=2))
        
        # 3. Write a test file
        print("\n3. Writing test file...")
        write_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_write_file",
                "arguments": {
                    "connection_id": connection_id,
                    "file_path": "/tmp/mcp_test.txt",
                    "content": "Hello from SSH MCP Server!\nThis is a test file.\nTimestamp: 2024-01-01 12:00:00",
                    "create_directories": True
                }
            },
            "id": 22
        }
        
        response = await self.send_request(write_request)
        print("Response:", json.dumps(response, indent=2))
        
        # 4. Read back the test file
        print("\n4. Reading back test file...")
        read_back_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_read_file",
                "arguments": {
                    "connection_id": connection_id,
                    "file_path": "/tmp/mcp_test.txt"
                }
            },
            "id": 23
        }
        
        response = await self.send_request(read_back_request)
        print("Response:", json.dumps(response, indent=2))
    
    async def example_multi_connection(self):
        """Example: Managing multiple SSH connections."""
        self.print_example(
            "Multiple Connections",
            "Demonstrate managing multiple concurrent SSH connections"
        )
        
        # Create multiple connections
        servers = [
            {"hostname": "server1.example.com", "username": "user1"},
            {"hostname": "server2.example.com", "username": "user2"},
            {"hostname": "server3.example.com", "username": "user3"}
        ]
        
        connection_ids = []
        
        for i, server in enumerate(servers, 1):
            print(f"\n--- Connecting to {server['hostname']} ---")
            
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_connect",
                    "arguments": {
                        "hostname": server["hostname"],
                        "username": server["username"],
                        "auth_method": "agent",
                        "timeout": 30
                    }
                },
                "id": 30 + i
            }
            
            response = await self.send_request(request)
            print("Response:", json.dumps(response, indent=2))
            
            # Extract connection ID
            if 'result' in response:
                result_data = json.loads(response['result']['content'][0]['text'])
                if result_data.get('success'):
                    connection_ids.append(result_data.get('connection_id'))
        
        # List all connections
        print("\n--- Listing all connections ---")
        list_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_list_connections",
                "arguments": {}
            },
            "id": 40
        }
        
        response = await self.send_request(list_request)
        print("Response:", json.dumps(response, indent=2))
        
        # Execute commands on all connections
        print("\n--- Executing commands on all connections ---")
        for i, conn_id in enumerate(connection_ids):
            if conn_id:
                print(f"\nConnection {i+1} ({conn_id}):")
                
                request = {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "ssh_execute",
                        "arguments": {
                            "connection_id": conn_id,
                            "command": "hostname && uptime"
                        }
                    },
                    "id": 50 + i
                }
                
                response = await self.send_request(request)
                print("Response:", json.dumps(response, indent=2))
        
        # Disconnect all connections
        print("\n--- Disconnecting all connections ---")
        for i, conn_id in enumerate(connection_ids):
            if conn_id:
                request = {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "ssh_disconnect",
                        "arguments": {
                            "connection_id": conn_id
                        }
                    },
                    "id": 60 + i
                }
                
                response = await self.send_request(request)
                print(f"Disconnect {conn_id}:", json.dumps(response, indent=2))
    
    async def example_error_handling(self):
        """Example: Error handling scenarios."""
        self.print_example(
            "Error Handling",
            "Demonstrate various error scenarios and handling"
        )
        
        error_scenarios = [
            {
                "name": "Invalid hostname",
                "request": {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "ssh_connect",
                        "arguments": {
                            "hostname": "nonexistent.invalid.domain",
                            "username": "testuser",
                            "auth_method": "key",
                            "key_path": "~/.ssh/id_rsa",
                            "timeout": 5
                        }
                    },
                    "id": 70
                }
            },
            {
                "name": "Missing key file",
                "request": {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "ssh_connect",
                        "arguments": {
                            "hostname": "example.com",
                            "username": "testuser",
                            "auth_method": "key",
                            "key_path": "/nonexistent/key/file",
                            "timeout": 5
                        }
                    },
                    "id": 71
                }
            },
            {
                "name": "Invalid connection ID",
                "request": {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "ssh_execute",
                        "arguments": {
                            "connection_id": "invalid_connection_id",
                            "command": "echo test"
                        }
                    },
                    "id": 72
                }
            },
            {
                "name": "Missing required parameter",
                "request": {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "ssh_connect",
                        "arguments": {
                            "hostname": "example.com"
                            # Missing username and auth_method
                        }
                    },
                    "id": 73
                }
            }
        ]
        
        for scenario in error_scenarios:
            print(f"\n--- {scenario['name']} ---")
            print("Request:", json.dumps(scenario['request'], indent=2))
            
            response = await self.send_request(scenario['request'])
            print("Response:", json.dumps(response, indent=2))
            
            # Analyze error
            if 'error' in response:
                error = response['error']
                print(f"Error Code: {error['code']}")
                print(f"Error Message: {error['message']}")
                if 'data' in error:
                    print(f"Error Data: {json.dumps(error['data'], indent=2)}")
    
    async def example_claude_code_workflow(self):
        """Example: Typical Claude Code development workflow."""
        self.print_example(
            "Claude Code Development Workflow",
            "Simulate a typical development workflow with Claude Code"
        )
        
        # 1. Connect to development server
        print("1. Connecting to development server...")
        connect_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "dev.example.com",
                    "username": "developer",
                    "auth_method": "agent"
                }
            },
            "id": 80
        }
        
        response = await self.send_request(connect_request)
        print("Response:", json.dumps(response, indent=2))
        
        # Assume connection successful for demo
        connection_id = "demo_connection_id"
        
        # 2. Check development environment
        print("\n2. Checking development environment...")
        env_commands = [
            "python3 --version",
            "node --version",
            "git --version",
            "docker --version"
        ]
        
        for cmd in env_commands:
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_execute",
                    "arguments": {
                        "connection_id": connection_id,
                        "command": cmd
                    }
                },
                "id": 81
            }
            
            response = await self.send_request(request)
            print(f"{cmd}: {json.dumps(response, indent=2)}")
        
        # 3. Navigate to project directory
        print("\n3. Exploring project structure...")
        list_request = {
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
            "id": 82
        }
        
        response = await self.send_request(list_request)
        print("Project structure:", json.dumps(response, indent=2))
        
        # 4. Read configuration file
        print("\n4. Reading configuration file...")
        read_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_read_file",
                "arguments": {
                    "connection_id": connection_id,
                    "file_path": "/home/developer/project/config.json"
                }
            },
            "id": 83
        }
        
        response = await self.send_request(read_request)
        print("Configuration:", json.dumps(response, indent=2))
        
        # 5. Run tests
        print("\n5. Running tests...")
        test_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_execute",
                "arguments": {
                    "connection_id": connection_id,
                    "command": "cd /home/developer/project && npm test",
                    "timeout": 60
                }
            },
            "id": 84
        }
        
        response = await self.send_request(test_request)
        print("Test results:", json.dumps(response, indent=2))
    
    async def example_gemini_cli_analysis(self):
        """Example: System analysis workflow for Gemini CLI."""
        self.print_example(
            "Gemini CLI System Analysis",
            "Comprehensive system analysis and monitoring"
        )
        
        # Connect to server
        connection_id = "analysis_connection_id"
        
        # System information gathering
        analysis_commands = [
            {
                "name": "System Info",
                "command": "uname -a && cat /etc/os-release"
            },
            {
                "name": "CPU Info",
                "command": "lscpu | head -20"
            },
            {
                "name": "Memory Usage",
                "command": "free -h && cat /proc/meminfo | head -10"
            },
            {
                "name": "Disk Usage",
                "command": "df -h && lsblk"
            },
            {
                "name": "Network Interfaces",
                "command": "ip addr show && ss -tuln"
            },
            {
                "name": "Running Processes",
                "command": "ps aux --sort=-%cpu | head -20"
            },
            {
                "name": "System Load",
                "command": "uptime && w && last -10"
            },
            {
                "name": "Service Status",
                "command": "systemctl status nginx mysql redis-server 2>/dev/null || echo 'Some services not found'"
            }
        ]
        
        for i, analysis in enumerate(analysis_commands, 1):
            print(f"\n--- {analysis['name']} ---")
            
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_execute",
                    "arguments": {
                        "connection_id": connection_id,
                        "command": analysis["command"],
                        "timeout": 30
                    }
                },
                "id": 90 + i
            }
            
            response = await self.send_request(request)
            print("Result:", json.dumps(response, indent=2))
        
        # Log analysis
        print("\n--- Log Analysis ---")
        log_files = [
            "/var/log/syslog",
            "/var/log/auth.log",
            "/var/log/nginx/access.log",
            "/var/log/nginx/error.log"
        ]
        
        for log_file in log_files:
            print(f"\nAnalyzing {log_file}...")
            
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_execute",
                    "arguments": {
                        "connection_id": connection_id,
                        "command": f"tail -50 {log_file} 2>/dev/null || echo 'Log file not accessible'"
                    }
                },
                "id": 100
            }
            
            response = await self.send_request(request)
            print("Log content:", json.dumps(response, indent=2))


async def main():
    """Run all usage examples."""
    examples = MCPUsageExamples()
    
    try:
        await examples.start_server()
        
        print("\n🎯 SSH MCP Server Usage Examples")
        print("=" * 60)
        print("This demonstration shows various usage patterns for the SSH MCP Server.")
        print("Note: These examples use mock connections and may show expected errors.")
        
        # Run examples
        await examples.example_basic_connection()
        
        # Use a mock connection ID for remaining examples
        mock_connection_id = "mock_conn_12345"
        
        await examples.example_command_execution(mock_connection_id)
        await examples.example_file_operations(mock_connection_id)
        await examples.example_multi_connection()
        await examples.example_error_handling()
        await examples.example_claude_code_workflow()
        await examples.example_gemini_cli_analysis()
        
        print("\n" + "=" * 60)
        print("✅ All usage examples completed!")
        print("\nKey takeaways:")
        print("• SSH MCP Server provides comprehensive SSH operations via MCP protocol")
        print("• Supports multiple concurrent connections with unique identifiers")
        print("• Handles various authentication methods (key, password, agent)")
        print("• Provides detailed error handling and reporting")
        print("• Compatible with Claude Code, Gemini CLI, and Claude Desktop")
        print("• Supports file operations, command execution, and connection management")
        
    except Exception as e:
        print(f"❌ Error during examples: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await examples.stop_server()


if __name__ == "__main__":
    asyncio.run(main())