# MCP Client Configuration Examples

This document provides detailed configuration examples for different MCP clients to use the SSH MCP Server.

## Claude Code Configuration

Claude Code is an AI-powered code editor that supports MCP servers for enhanced functionality.

### Basic Configuration

Add the following to your Claude Code MCP settings file (usually located at `~/.claude-code/mcp.json`):

```json
{
  "mcpServers": {
    "ssh-server": {
      "command": "ssh-mcp-server",
      "env": {
        "SSH_MCP_DEBUG": "false",
        "SSH_MCP_TIMEOUT": "30",
        "SSH_MCP_MAX_CONNECTIONS": "10"
      }
    }
  }
}
```

### Advanced Configuration

For development environments with specific requirements:

```json
{
  "mcpServers": {
    "ssh-server": {
      "command": "python",
      "args": ["-m", "ssh_mcp_server"],
      "env": {
        "SSH_MCP_DEBUG": "true",
        "SSH_MCP_LOG_LEVEL": "DEBUG",
        "SSH_MCP_TIMEOUT": "60",
        "SSH_MCP_MAX_CONNECTIONS": "5",
        "SSH_AUTH_SOCK": "/tmp/ssh-agent.sock"
      },
      "cwd": "/path/to/project"
    }
  }
}
```

### Usage Examples in Claude Code

#### Connecting to Development Server

```javascript
// Connect to your development server
await mcp.call("ssh_connect", {
  hostname: "dev.example.com",
  username: "developer",
  auth_method: "key",
  key_path: "~/.ssh/dev_server_key"
});
```

#### Interactive Development Workflow

```javascript
// 1. Connect to server
const connection = await mcp.call("ssh_connect", {
  hostname: "dev.example.com",
  username: "developer",
  auth_method: "agent"
});

// 2. Check Python version
const pythonVersion = await mcp.call("ssh_execute", {
  connection_id: connection.connection_id,
  command: "python3 --version"
});

// 3. Read source file
const sourceCode = await mcp.call("ssh_read_file", {
  connection_id: connection.connection_id,
  file_path: "/home/developer/project/main.py"
});

// 4. List project directory
const projectFiles = await mcp.call("ssh_list_directory", {
  connection_id: connection.connection_id,
  directory_path: "/home/developer/project",
  detailed: true
});
```

## Gemini CLI Configuration

Gemini CLI is a command-line interface for Google's Gemini AI that supports MCP servers.

### Basic Configuration

Create or update `~/.gemini-cli/mcp.json`:

```json
{
  "mcpServers": {
    "ssh-server": {
      "command": "ssh-mcp-server",
      "args": [],
      "env": {
        "SSH_MCP_TIMEOUT": "45",
        "SSH_MCP_DEBUG": "false"
      }
    }
  }
}
```

### Configuration for System Analysis

For system administration and analysis tasks:

```json
{
  "mcpServers": {
    "ssh-server": {
      "command": "ssh-mcp-server",
      "env": {
        "SSH_MCP_DEBUG": "false",
        "SSH_MCP_TIMEOUT": "120",
        "SSH_MCP_MAX_CONNECTIONS": "15",
        "SSH_MCP_LOG_LEVEL": "INFO"
      },
      "timeout": 300
    }
  }
}
```

### Usage Examples in Gemini CLI

#### System Analysis Workflow

```bash
# Connect to multiple servers for analysis
gemini-cli "Connect to servers web1.example.com, web2.example.com, and db.example.com using SSH keys, then gather system information including CPU usage, memory usage, disk space, and running processes. Format the results as a structured comparison."
```

#### Batch Operations

```bash
# Batch system updates
gemini-cli "Connect to all servers in the production environment and perform the following tasks: 1) Check for available package updates, 2) Review system logs for errors, 3) Verify service status for nginx, mysql, and redis, 4) Generate a summary report."
```

#### Log Analysis

```bash
# Analyze application logs
gemini-cli "Connect to the application server and analyze the last 1000 lines of /var/log/application.log. Identify any error patterns, performance issues, or unusual activity. Provide recommendations for investigation."
```

## Claude Desktop Configuration

Claude Desktop is the desktop application for Claude AI with MCP support.

### Basic Configuration

Update the Claude Desktop configuration file (location varies by OS):

**macOS:** `~/Library/Application Support/Claude/mcp.json`
**Windows:** `%APPDATA%\Claude\mcp.json`
**Linux:** `~/.config/claude/mcp.json`

```json
{
  "mcpServers": {
    "ssh-server": {
      "command": "ssh-mcp-server",
      "env": {
        "SSH_MCP_DEBUG": "false",
        "SSH_MCP_TIMEOUT": "30"
      }
    }
  }
}
```

### User-Friendly Configuration

For desktop users who prefer simpler interactions:

```json
{
  "mcpServers": {
    "ssh-server": {
      "command": "ssh-mcp-server",
      "env": {
        "SSH_MCP_DEBUG": "false",
        "SSH_MCP_TIMEOUT": "60",
        "SSH_MCP_MAX_CONNECTIONS": "3",
        "SSH_MCP_LOG_LEVEL": "WARNING"
      },
      "description": "SSH server management for remote operations"
    }
  }
}
```

### Usage Examples in Claude Desktop

#### File Management

```
I need to manage files on my remote server. Please:
1. Connect to server.example.com with username 'myuser' using my SSH key
2. List the contents of my home directory
3. Read the contents of config.txt
4. Create a backup of config.txt named config.txt.backup
```

#### Server Maintenance

```
Help me perform routine maintenance on my web server:
1. Connect to webserver.example.com
2. Check disk space usage
3. Review the last 50 lines of the web server access log
4. Check if the web server service is running
5. Provide a summary of the server status
```

## Universal Configuration Options

### Environment Variables

These environment variables work with all MCP clients:

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `SSH_MCP_DEBUG` | Enable debug logging | `false` | `true` |
| `SSH_MCP_LOG_LEVEL` | Logging level | `INFO` | `DEBUG` |
| `SSH_MCP_TIMEOUT` | Default connection timeout (seconds) | `30` | `60` |
| `SSH_MCP_MAX_CONNECTIONS` | Maximum concurrent connections | `10` | `5` |
| `SSH_MCP_CONFIG_FILE` | Custom configuration file path | None | `/path/to/config.json` |

### Configuration File

Create a global configuration file at `~/.ssh-mcp-server/config.json`:

```json
{
  "server": {
    "max_connections": 10,
    "default_timeout": 30,
    "debug": false,
    "log_level": "INFO"
  },
  "ssh": {
    "host_key_policy": "auto_add",
    "compression": true,
    "keepalive_interval": 30,
    "connect_timeout": 10
  },
  "security": {
    "allowed_hosts": ["*.example.com", "192.168.1.*"],
    "blocked_commands": ["rm -rf /", "dd if="],
    "max_file_size": 10485760
  }
}
```

## Client-Specific Features

### Claude Code Features

- **Interactive Development**: Real-time code editing and execution
- **Project Integration**: Seamless integration with development workflows
- **Error Handling**: Detailed error reporting for debugging
- **Concurrent Operations**: Multiple simultaneous operations

### Gemini CLI Features

- **Batch Processing**: Execute multiple operations in sequence
- **Structured Output**: JSON and structured data handling
- **System Analysis**: Comprehensive system monitoring and analysis
- **Automation**: Script-friendly command execution

### Claude Desktop Features

- **User-Friendly Interface**: Simplified interaction patterns
- **File Management**: Intuitive file operations
- **Connection Management**: Easy connection setup and management
- **Visual Feedback**: Clear status and progress indicators

## Troubleshooting Client Configurations

### Common Configuration Issues

#### Issue: MCP Server Not Found

**Solution:**
```json
{
  "mcpServers": {
    "ssh-server": {
      "command": "/usr/local/bin/ssh-mcp-server",
      "env": {
        "PATH": "/usr/local/bin:/usr/bin:/bin"
      }
    }
  }
}
```

#### Issue: Permission Denied

**Solution:**
```json
{
  "mcpServers": {
    "ssh-server": {
      "command": "python",
      "args": ["-m", "ssh_mcp_server"],
      "env": {
        "PYTHONPATH": "/path/to/ssh-mcp-server"
      }
    }
  }
}
```

#### Issue: Connection Timeout

**Solution:**
```json
{
  "mcpServers": {
    "ssh-server": {
      "command": "ssh-mcp-server",
      "env": {
        "SSH_MCP_TIMEOUT": "120"
      },
      "timeout": 300
    }
  }
}
```

### Validation Commands

Test your configuration with these commands:

```bash
# Test server availability
ssh-mcp-server --version

# Test MCP protocol
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | ssh-mcp-server --stdin

# Test with specific client
claude-code --test-mcp ssh-server
gemini-cli --validate-mcp ssh-server
```

## Best Practices

### Security

1. **Use SSH keys instead of passwords**
2. **Limit connection counts**
3. **Enable logging for audit trails**
4. **Restrict allowed hosts when possible**

### Performance

1. **Set appropriate timeouts**
2. **Limit concurrent connections**
3. **Use connection pooling**
4. **Monitor resource usage**

### Reliability

1. **Enable debug logging during setup**
2. **Test configurations before deployment**
3. **Monitor connection health**
4. **Implement error handling in client code**

### Example Production Configuration

```json
{
  "mcpServers": {
    "ssh-server": {
      "command": "ssh-mcp-server",
      "env": {
        "SSH_MCP_DEBUG": "false",
        "SSH_MCP_LOG_LEVEL": "WARNING",
        "SSH_MCP_TIMEOUT": "45",
        "SSH_MCP_MAX_CONNECTIONS": "8",
        "SSH_MCP_CONFIG_FILE": "/etc/ssh-mcp-server/config.json"
      },
      "timeout": 300,
      "restart": true,
      "restartDelay": 5000
    }
  }
}
```

This configuration provides:
- Minimal logging for production
- Reasonable timeouts
- Connection limits
- Automatic restart on failure
- Custom configuration file location