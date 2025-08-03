#!/usr/bin/env python3
"""Validation script for integration tests without pytest dependencies."""

import sys
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch

# Add current directory to path
sys.path.insert(0, '.')

from ssh_mcp_server.server import MCPServer
from ssh_mcp_server.models import SSHConfig, ConnectionInfo, CommandResult


async def test_basic_integration():
    """Test basic integration functionality."""
    print("🧪 Testing basic SSH MCP server integration...")
    
    # Create server
    server = MCPServer(max_connections=10, debug=True)
    
    # Mock connection info
    mock_connection_info = ConnectionInfo.create("test.example.com", "testuser", 22)
    mock_connection_info.connection_id = "test-conn-123"
    mock_connection_info.connected = True
    
    # Mock SSH manager methods
    server.ssh_manager.create_connection = AsyncMock(return_value="test-conn-123")
    server.ssh_manager.list_connections = AsyncMock(return_value=[mock_connection_info])
    server.ssh_manager.execute_command = AsyncMock(return_value=CommandResult(
        stdout="Hello, World!",
        stderr="",
        exit_code=0,
        execution_time=0.1,
        command="echo 'Hello, World!'"
    ))
    
    try:
        # Test 1: SSH Connect
        print("  ✓ Testing SSH connect...")
        connect_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_connect",
                "arguments": {
                    "hostname": "test.example.com",
                    "username": "testuser",
                    "auth_method": "agent"
                }
            },
            "id": "test-connect"
        }
        
        with patch('os.environ.get', return_value='/tmp/ssh_auth_sock'):
            with patch('os.path.exists', return_value=True):
                with patch('paramiko.Agent') as mock_agent:
                    mock_agent_instance = Mock()
                    mock_agent_instance.get_keys.return_value = [Mock()]
                    mock_agent.return_value = mock_agent_instance
                    
                    response = await server.handle_request(connect_request)
                    
                    assert "result" in response, f"Expected result, got: {response}"
                    content = json.loads(response["result"]["content"][0]["text"])
                    assert content["success"] is True, f"Expected success=True, got: {content}"
                    assert content["data"]["connection_id"] == "test-conn-123"
                    print("    ✓ SSH connect successful")
        
        # Test 2: SSH Execute
        print("  ✓ Testing SSH execute...")
        execute_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_execute",
                "arguments": {
                    "connection_id": "test-conn-123",
                    "command": "echo 'Hello, World!'"
                }
            },
            "id": "test-execute"
        }
        
        response = await server.handle_request(execute_request)
        
        assert "result" in response, f"Expected result, got: {response}"
        content = json.loads(response["result"]["content"][0]["text"])
        assert content["success"] is True, f"Expected success=True, got: {content}"
        assert "Hello, World!" in content["data"]["stdout"]
        print("    ✓ SSH execute successful")
        
        # Test 3: Error handling
        print("  ✓ Testing error handling...")
        from ssh_mcp_server.manager import SSHManagerError
        server.ssh_manager.execute_command = AsyncMock(
            side_effect=SSHManagerError("Connection lost", "test-conn-123")
        )
        
        error_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ssh_execute",
                "arguments": {
                    "connection_id": "test-conn-123",
                    "command": "failing_command"
                }
            },
            "id": "test-error"
        }
        
        response = await server.handle_request(error_request)
        
        assert "error" in response, f"Expected error, got: {response}"
        assert response["error"]["code"] == -32000  # TOOL_ERROR
        print("    ✓ Error handling successful")
        
        print("✅ All basic integration tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_authentication_methods():
    """Test different authentication methods."""
    print("🔐 Testing authentication methods...")
    
    server = MCPServer(max_connections=5, debug=True)
    
    auth_scenarios = [
        {
            "name": "key_auth",
            "auth_method": "key",
            "key_path": "/tmp/test_key.pem",
            "connection_id": "key-conn-123"
        },
        {
            "name": "password_auth", 
            "auth_method": "password",
            "password": "testpass123",
            "connection_id": "pass-conn-456"
        },
        {
            "name": "agent_auth",
            "auth_method": "agent",
            "connection_id": "agent-conn-789"
        }
    ]
    
    try:
        for scenario in auth_scenarios:
            print(f"  ✓ Testing {scenario['name']}...")
            
            # Mock connection info
            mock_connection_info = ConnectionInfo.create("test.com", "user", 22)
            mock_connection_info.connection_id = scenario["connection_id"]
            mock_connection_info.connected = True
            
            server.ssh_manager.create_connection = AsyncMock(return_value=scenario["connection_id"])
            server.ssh_manager.list_connections = AsyncMock(return_value=[mock_connection_info])
            
            # Prepare request arguments
            args = {
                "hostname": "test.com",
                "username": "user",
                "auth_method": scenario["auth_method"]
            }
            
            if "key_path" in scenario:
                args["key_path"] = scenario["key_path"]
            elif "password" in scenario:
                args["password"] = scenario["password"]
            
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_connect",
                    "arguments": args
                },
                "id": f"auth-test-{scenario['name']}"
            }
            
            # Mock appropriate authentication methods
            with patch('pathlib.Path.exists', return_value=True):
                with patch('os.environ.get', return_value='/tmp/ssh_auth_sock'):
                    with patch('os.path.exists', return_value=True):
                        with patch('paramiko.Agent') as mock_agent:
                            mock_agent_instance = Mock()
                            mock_agent_instance.get_keys.return_value = [Mock()]
                            mock_agent.return_value = mock_agent_instance
                            
                            response = await server.handle_request(request)
                            
                            assert "result" in response, f"Expected result for {scenario['name']}, got: {response}"
                            content = json.loads(response["result"]["content"][0]["text"])
                            assert content["success"] is True, f"Expected success for {scenario['name']}"
                            assert content["data"]["connection_id"] == scenario["connection_id"]
                            print(f"    ✓ {scenario['name']} successful")
        
        print("✅ All authentication method tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Authentication test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_multi_connection_scenarios():
    """Test multiple connection scenarios."""
    print("🔗 Testing multi-connection scenarios...")
    
    server = MCPServer(max_connections=10, debug=True)
    
    try:
        # Create multiple connections
        connections = []
        for i in range(3):
            conn_info = ConnectionInfo.create(f"server{i+1}.com", f"user{i+1}", 22)
            conn_info.connection_id = f"multi-conn-{i+1:03d}"
            conn_info.connected = True
            connections.append(conn_info)
        
        # Mock SSH manager for multiple connections
        connection_ids = [conn.connection_id for conn in connections]
        call_count = 0
        
        async def mock_create_connection(config):
            nonlocal call_count
            result = connection_ids[call_count]
            call_count += 1
            return result
        
        server.ssh_manager.create_connection = AsyncMock(side_effect=mock_create_connection)
        server.ssh_manager.list_connections = AsyncMock(return_value=connections)
        
        # Create multiple connection requests
        for i in range(3):
            print(f"  ✓ Creating connection {i+1}...")
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "ssh_connect",
                    "arguments": {
                        "hostname": f"server{i+1}.com",
                        "username": f"user{i+1}",
                        "auth_method": "agent"
                    }
                },
                "id": f"multi-connect-{i+1}"
            }
            
            with patch('os.environ.get', return_value='/tmp/ssh_auth_sock'):
                with patch('os.path.exists', return_value=True):
                    with patch('paramiko.Agent') as mock_agent:
                        mock_agent_instance = Mock()
                        mock_agent_instance.get_keys.return_value = [Mock()]
                        mock_agent.return_value = mock_agent_instance
                        
                        response = await server.handle_request(request)
                        
                        assert "result" in response, f"Expected result for connection {i+1}, got: {response}"
                        content = json.loads(response["result"]["content"][0]["text"])
                        assert content["success"] is True, f"Expected success for connection {i+1}"
                        assert content["data"]["connection_id"] == f"multi-conn-{i+1:03d}"
                        print(f"    ✓ Connection {i+1} successful")
        
        print("✅ All multi-connection tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Multi-connection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all validation tests."""
    print("🚀 Starting SSH MCP Server Integration Test Validation")
    print("=" * 60)
    
    tests = [
        test_basic_integration,
        test_authentication_methods,
        test_multi_connection_scenarios
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if await test():
                passed += 1
            print()  # Add spacing between tests
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            print()
    
    print("=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All integration tests validation successful!")
        return True
    else:
        print("⚠️  Some integration tests failed validation")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)