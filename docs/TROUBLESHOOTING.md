# SSH MCP Server Troubleshooting Guide

This guide helps you diagnose and resolve common issues with the SSH MCP Server.

## Common Issues

### Connection Issues

#### Issue: "SSH connection failed: Connection timed out"

**Symptoms:**
- Connection attempts fail with timeout errors
- Long delays before error messages

**Possible Causes:**
1. Network connectivity issues
2. Firewall blocking SSH port
3. SSH service not running on target server
4. Incorrect hostname or IP address

**Solutions:**

1. **Test basic connectivity:**
   ```bash
   ping hostname
   telnet hostname 22
   ```

2. **Check SSH service:**
   ```bash
   ssh -v username@hostname
   ```

3. **Verify firewall settings:**
   ```bash
   # On the target server
   sudo ufw status
   sudo iptables -L
   ```

4. **Increase timeout:**
   ```json
   {
     "name": "ssh_connect",
     "arguments": {
       "hostname": "example.com",
       "username": "user",
       "timeout": 60
     }
   }
   ```

#### Issue: "SSH connection failed: Connection refused"

**Symptoms:**
- Immediate connection refusal
- Error occurs quickly

**Possible Causes:**
1. SSH service not running
2. Wrong port number
3. SSH service bound to different interface

**Solutions:**

1. **Check SSH service status:**
   ```bash
   # On target server
   sudo systemctl status ssh
   sudo systemctl status sshd
   ```

2. **Check SSH port:**
   ```bash
   # On target server
   sudo netstat -tlnp | grep :22
   ```

3. **Try different port:**
   ```json
   {
     "name": "ssh_connect",
     "arguments": {
       "hostname": "example.com",
       "username": "user",
       "port": 2222
     }
   }
   ```

### Authentication Issues

#### Issue: "SSH authentication failed: Invalid credentials"

**Symptoms:**
- Authentication fails with valid credentials
- Works with standard SSH client

**Possible Causes:**
1. Incorrect username or password
2. SSH key file not found or invalid
3. SSH key permissions incorrect
4. SSH agent not available

**Solutions:**

1. **Verify credentials:**
   ```bash
   ssh username@hostname
   ```

2. **Check SSH key file:**
   ```bash
   ls -la ~/.ssh/id_rsa
   chmod 600 ~/.ssh/id_rsa
   ```

3. **Test SSH key:**
   ```bash
   ssh -i ~/.ssh/id_rsa username@hostname
   ```

4. **Check SSH agent:**
   ```bash
   ssh-add -l
   ```

#### Issue: "SSH key file not found"

**Symptoms:**
- Error when using key authentication
- Key file path appears correct

**Solutions:**

1. **Use absolute path:**
   ```json
   {
     "auth_method": "key",
     "key_path": "/home/user/.ssh/id_rsa"
   }
   ```

2. **Check file permissions:**
   ```bash
   ls -la ~/.ssh/id_rsa
   chmod 600 ~/.ssh/id_rsa
   ```

3. **Verify key format:**
   ```bash
   file ~/.ssh/id_rsa
   ssh-keygen -l -f ~/.ssh/id_rsa
   ```

#### Issue: "SSH agent authentication failed"

**Symptoms:**
- Agent authentication fails
- SSH agent is running

**Solutions:**

1. **Check SSH agent:**
   ```bash
   echo $SSH_AUTH_SOCK
   ssh-add -l
   ```

2. **Add keys to agent:**
   ```bash
   ssh-add ~/.ssh/id_rsa
   ```

3. **Restart SSH agent:**
   ```bash
   eval $(ssh-agent)
   ssh-add ~/.ssh/id_rsa
   ```

### Command Execution Issues

#### Issue: "Command execution failed: Permission denied"

**Symptoms:**
- Commands fail with permission errors
- Same commands work in regular SSH session

**Solutions:**

1. **Check user permissions:**
   ```bash
   # Test with ssh_execute
   {
     "name": "ssh_execute",
     "arguments": {
       "connection_id": "conn_123",
       "command": "whoami"
     }
   }
   ```

2. **Use sudo if needed:**
   ```json
   {
     "name": "ssh_execute",
     "arguments": {
       "connection_id": "conn_123",
       "command": "sudo ls /root"
     }
   }
   ```

3. **Check file permissions:**
   ```bash
   ls -la /path/to/file
   ```

#### Issue: "Command timeout"

**Symptoms:**
- Long-running commands are terminated
- Timeout errors

**Solutions:**

1. **Increase timeout:**
   ```json
   {
     "name": "ssh_execute",
     "arguments": {
       "connection_id": "conn_123",
       "command": "long-running-command",
       "timeout": 300
     }
   }
   ```

2. **Run commands in background:**
   ```json
   {
     "name": "ssh_execute",
     "arguments": {
       "connection_id": "conn_123",
       "command": "nohup long-running-command > output.log 2>&1 &"
     }
   }
   ```

### File Operation Issues

#### Issue: "File not found"

**Symptoms:**
- File operations fail with "not found" errors
- Files exist when checked manually

**Solutions:**

1. **Use absolute paths:**
   ```json
   {
     "name": "ssh_read_file",
     "arguments": {
       "connection_id": "conn_123",
       "file_path": "/home/user/file.txt"
     }
   }
   ```

2. **Check file existence:**
   ```json
   {
     "name": "ssh_execute",
     "arguments": {
       "connection_id": "conn_123",
       "command": "ls -la /path/to/file"
     }
   }
   ```

#### Issue: "Permission denied" for file operations

**Solutions:**

1. **Check file permissions:**
   ```bash
   ls -la /path/to/file
   ```

2. **Change permissions if needed:**
   ```bash
   chmod 644 /path/to/file
   ```

3. **Use sudo for system files:**
   ```json
   {
     "name": "ssh_execute",
     "arguments": {
       "connection_id": "conn_123",
       "command": "sudo cat /etc/shadow"
     }
   }
   ```

### MCP Client Issues

#### Issue: "Method not found"

**Symptoms:**
- MCP client reports unknown methods
- Tools are not recognized

**Solutions:**

1. **Check MCP server status:**
   ```bash
   ssh-mcp-server --version
   ```

2. **Verify client configuration:**
   ```json
   {
     "mcpServers": {
       "ssh-server": {
         "command": "ssh-mcp-server"
       }
     }
   }
   ```

3. **Restart MCP client**

#### Issue: "Invalid params"

**Symptoms:**
- Parameter validation errors
- Required parameters missing

**Solutions:**

1. **Check parameter names:**
   ```json
   {
     "name": "ssh_connect",
     "arguments": {
       "hostname": "example.com",
       "username": "user",
       "auth_method": "key"
     }
   }
   ```

2. **Verify required parameters:**
   - `ssh_connect`: hostname, username, auth_method
   - `ssh_execute`: connection_id, command
   - `ssh_read_file`: connection_id, file_path

## Debugging

### Enable Debug Logging

1. **Environment variable:**
   ```bash
   export SSH_MCP_DEBUG=true
   ssh-mcp-server
   ```

2. **MCP client configuration:**
   ```json
   {
     "mcpServers": {
       "ssh-server": {
         "command": "ssh-mcp-server",
         "env": {
           "SSH_MCP_DEBUG": "true",
           "SSH_MCP_LOG_LEVEL": "DEBUG"
         }
       }
     }
   }
   ```

### Log Locations

- **Linux/macOS:** `~/.ssh-mcp-server/logs/`
- **Windows:** `%USERPROFILE%\.ssh-mcp-server\logs\`

### Verbose SSH Debugging

Enable verbose SSH debugging:

```bash
export SSH_MCP_DEBUG=true
export SSH_MCP_SSH_DEBUG=true
ssh-mcp-server
```

### Test with Standalone Script

Create a test script to isolate issues:

```python
#!/usr/bin/env python3
import asyncio
import json
from ssh_mcp_server.server import MCPServer

async def test_connection():
    server = MCPServer(debug=True)
    await server.start()
    
    # Test connection
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "ssh_connect",
            "arguments": {
                "hostname": "your-server.com",
                "username": "your-username",
                "auth_method": "key",
                "key_path": "~/.ssh/id_rsa"
            }
        },
        "id": 1
    }
    
    response = await server.handle_request(request)
    print(json.dumps(response, indent=2))
    
    await server.stop()

if __name__ == "__main__":
    asyncio.run(test_connection())
```

## Performance Issues

### Issue: "Slow connection establishment"

**Solutions:**

1. **Disable DNS lookups:**
   ```bash
   # Add to ~/.ssh/config
   Host *
       UseDNS no
   ```

2. **Use connection pooling:**
   - Reuse connections for multiple operations
   - Don't disconnect immediately after each operation

3. **Optimize SSH configuration:**
   ```bash
   # Add to ~/.ssh/config
   Host *
       Compression yes
       ServerAliveInterval 60
       ServerAliveCountMax 3
   ```

### Issue: "High memory usage"

**Solutions:**

1. **Limit concurrent connections:**
   ```bash
   export SSH_MCP_MAX_CONNECTIONS=5
   ```

2. **Monitor connection usage:**
   ```json
   {
     "name": "ssh_list_connections",
     "arguments": {}
   }
   ```

3. **Clean up unused connections:**
   ```json
   {
     "name": "ssh_disconnect",
     "arguments": {
       "connection_id": "unused_connection"
     }
   }
   ```

## Network Issues

### Issue: "Connection drops frequently"

**Solutions:**

1. **Enable keepalive:**
   ```bash
   # Add to ~/.ssh/config
   Host *
       ServerAliveInterval 30
       ServerAliveCountMax 3
   ```

2. **Check network stability:**
   ```bash
   ping -c 100 hostname
   ```

3. **Use connection monitoring:**
   ```json
   {
     "name": "ssh_execute",
     "arguments": {
       "connection_id": "conn_123",
       "command": "echo 'keepalive'"
     }
   }
   ```

### Issue: "Proxy/firewall interference"

**Solutions:**

1. **Configure SSH proxy:**
   ```bash
   # Add to ~/.ssh/config
   Host target-server
       ProxyCommand nc -X connect -x proxy:8080 %h %p
   ```

2. **Use different port:**
   ```json
   {
     "name": "ssh_connect",
     "arguments": {
       "hostname": "example.com",
       "port": 443
     }
   }
   ```

## Getting Help

### Collect Debug Information

When reporting issues, include:

1. **SSH MCP Server version:**
   ```bash
   ssh-mcp-server --version
   ```

2. **Python version:**
   ```bash
   python --version
   ```

3. **Operating system:**
   ```bash
   uname -a
   ```

4. **Error logs:**
   ```bash
   cat ~/.ssh-mcp-server/logs/ssh-mcp-server.log
   ```

5. **MCP client information:**
   - Client name and version
   - Configuration used

### Test Configuration

Use this minimal test to verify basic functionality:

```json
{
  "jsonrpc": "2.0",
  "method": "tools/list",
  "id": 1
}
```

Expected response should list all available tools.

### Support Channels

- **GitHub Issues:** [Report bugs and feature requests](https://github.com/ssh-mcp-server/ssh-mcp-server/issues)
- **GitHub Discussions:** [Ask questions and get help](https://github.com/ssh-mcp-server/ssh-mcp-server/discussions)
- **Documentation:** [Read the full documentation](https://ssh-mcp-server.readthedocs.io/)

### Before Reporting Issues

1. Check this troubleshooting guide
2. Search existing GitHub issues
3. Test with minimal configuration
4. Collect debug information
5. Provide clear reproduction steps