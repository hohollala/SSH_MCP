# SSH MCP Server

A Model Context Protocol (MCP) server that enables AI clients like Claude Code, Gemini CLI, and Claude Desktop to perform SSH operations on remote servers. This server provides secure, efficient remote server management through a standardized MCP interface.

## Features

- **🔗 SSH Connection Management**: Multiple concurrent SSH connections with unique identifiers
- **⚡ Remote Command Execution**: Execute commands on remote servers with real-time output
- **📁 File Operations**: Read, write, and list files on remote servers
- **🔐 Secure Authentication**: SSH key (PEM format), password, and SSH agent authentication
- **🛡️ Error Handling**: Comprehensive error reporting and recovery mechanisms
- **📊 Connection Monitoring**: Real-time connection status and usage tracking
- **🌐 Multi-Client Support**: Compatible with Claude Code, Gemini CLI, and Claude Desktop
- **📝 Environment Variables**: JSON and KEY=VALUE format support for .sshenv files

## Installation

### Prerequisites

- Node.js 18.0.0 or higher
- npm or yarn package manager

### Quick Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/hohollala/SSH_MCP.git
   cd SSH_MCP
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Build the project**
   ```bash
   npm run build
   ```

4. **Register with MCP clients**

   **Using Claude CLI (Recommended):**
   ```bash
   # User-level registration
   claude mcp add ssh-mcp -s user -- node "[installation-path]/dist/index.js"
   
   # Workspace-level registration  
   claude mcp add ssh-mcp -s workspace -- node "[installation-path]/dist/index.js"
   ```

## Manual Configuration

Configure your MCP client by editing the configuration file:

### Claude Desktop
**Config file:** `%USERPROFILE%\.claude\settings.json` (Windows) / `~/.claude/settings.json` (macOS/Linux)

```json
{
  "mcpServers": {
    "ssh-mcp": {
      "command": "node",
      "args": ["[installation-path]/dist/index.js", "--stdin"],
      "env": {
        "SSH_MCP_DEBUG": "false",
        "SSH_MCP_TIMEOUT": "30",
        "SSH_MCP_MAX_CONNECTIONS": "10"
      }
    }
  }
}
```

### Claude Code
**Config file:** `%USERPROFILE%\.claude-code\mcp.json` (Windows) / `~/.claude-code/mcp.json` (macOS/Linux)

```json
{
  "mcpServers": {
    "ssh-mcp": {
      "command": "node",
      "args": ["[installation-path]/dist/index.js", "--stdin"],
      "env": {
        "SSH_MCP_DEBUG": "false",
        "SSH_MCP_TIMEOUT": "30",
        "SSH_MCP_MAX_CONNECTIONS": "10"
      }
    }
  }
}
```

### Cursor
**Config file:** `%APPDATA%\Cursor\User\mcp.json` (Windows) / `~/.config/Cursor/User/mcp.json` (macOS/Linux)

```json
{
  "mcpServers": {
    "ssh-mcp": {
      "command": "node",
      "args": ["[installation-path]/dist/index.js", "--stdin"],
      "env": {
        "SSH_MCP_DEBUG": "false",
        "SSH_MCP_TIMEOUT": "30",
        "SSH_MCP_MAX_CONNECTIONS": "10"
      }
    }
  }
}
```

### Gemini CLI
**Config file:** `%USERPROFILE%\.gemini\settings.json` (Windows) / `~/.gemini/settings.json` (macOS/Linux)

```json
{
  "mcpServers": {
    "ssh-mcp": {
      "command": "node",
      "args": ["[installation-path]/dist/index.js", "--stdin"],
      "env": {
        "SSH_MCP_DEBUG": "false",
        "SSH_MCP_TIMEOUT": "30",
        "SSH_MCP_MAX_CONNECTIONS": "10"
      }
    }
  }
}
```

## Configuration

### SSH Connection Configuration (.sshenv)

Use the `ssh_init` tool to create a `.sshenv` file for managing SSH connection information:

#### JSON Format (Recommended)
```json
{
  "servers": {
    "development": {
      "DEV_HOST": "192.168.1.100",
      "DEV_USER": "ubuntu",
      "DEV_PASSWORD": "your_password",
      "DEV_KEY_PATH": "~/.ssh/id_rsa",
      "DEV_PORT": 22
    },
    "staging": {
      "STAGING_HOST": "staging.example.com",
      "STAGING_USER": "deploy",
      "STAGING_KEY_PATH": "~/.ssh/staging_key",
      "STAGING_PORT": 22
    },
    "production": {
      "PROD_HOST": "prod.example.com",
      "PROD_USER": "admin",
      "PROD_KEY_PATH": "~/.ssh/prod_key",
      "PROD_PORT": 22
    }
  },
  "defaults": {
    "DEFAULT_PORT": 22,
    "DEFAULT_TIMEOUT": 30
  }
}
```

#### Traditional KEY=VALUE Format
```bash
# Development Server
DEV_HOST=192.168.1.100
DEV_USER=ubuntu
DEV_PASSWORD=your_password
DEV_KEY_PATH=~/.ssh/id_rsa

# Production Server  
PROD_HOST=prod.example.com
PROD_USER=admin
PROD_KEY_PATH=~/.ssh/prod_key
```

### Environment Variables

- **`SSH_MCP_DEBUG`**: Enable debug logging (default: `false`)
- **`SSH_MCP_TIMEOUT`**: Default connection timeout in seconds (default: `30`)
- **`SSH_MCP_MAX_CONNECTIONS`**: Maximum concurrent connections (default: `10`)
- **`SSH_MCP_LOG_LEVEL`**: Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`)

## Available Tools

### Connection Management
- **`ssh_connect`**: Establish SSH connection to a remote server
- **`ssh_disconnect`**: Close an existing SSH connection  
- **`ssh_list_connections`**: List all active SSH connections

### Command Execution
- **`ssh_execute_command`**: Execute commands on remote servers

### File Operations
- **`ssh_read_file`**: Read files from remote servers
- **`ssh_write_file`**: Write files to remote servers
- **`ssh_list_files`**: List directory contents on remote servers

### Environment Setup
- **`ssh_init`**: Initialize SSH environment configuration file

## Usage Examples

### With Claude Code

```
"Connect to the development server and check the PHP version"
```

```
"Analyze the server's system information comprehensively. Check CPU, memory, and disk usage"
```

```
"Check the files in the web root directory and read the config.php file to analyze its contents"
```

### Connection Examples

#### SSH Key Authentication
```javascript
ssh_connect({
  host: "192.168.1.100",
  username: "admin",
  privateKeyPath: "/path/to/private/key"
})
```

#### Password Authentication
```javascript
ssh_connect({
  host: "192.168.1.100", 
  username: "admin",
  password: "your_password"
})
```

#### Using Environment Variables
```javascript
// Uses ${DEV_HOST}, ${DEV_USER}, ${DEV_PASSWORD} from .sshenv
ssh_connect({
  host: "${DEV_HOST}",
  username: "${DEV_USER}",
  password: "${DEV_PASSWORD}"
})
```

### Command Execution
```javascript
ssh_execute_command({
  connectionId: "admin@192.168.1.100:22",
  command: "ls -la /home/admin"
})
```

### File Operations
```javascript
// Read a file
ssh_read_file({
  connectionId: "admin@192.168.1.100:22",
  path: "/etc/hosts"
})

// Write a file
ssh_write_file({
  connectionId: "admin@192.168.1.100:22",
  path: "/tmp/test.txt",
  content: "Hello, World!"
})
```

## Authentication Methods

### SSH Key Authentication (PEM Format Required)

SSH MCP Server supports PEM format SSH keys only. If you have OpenSSH format keys, convert them:

```bash
ssh-keygen -p -m PEM -f ~/.ssh/id_rsa -N ""
```

**⚠️ Important:** This command converts your existing key to PEM format. Consider backing up your key first.

Supported key types:
- RSA (PEM format)
- Ed25519 (converted to PEM)
- ECDSA (converted to PEM)

### Password Authentication

Direct password authentication is supported but SSH keys are recommended for better security.

### SSH Agent Authentication

Uses keys available in your SSH agent:

```javascript
ssh_connect({
  host: "example.com",
  username: "user",
  useAgent: true
})
```

## Troubleshooting

### Common Issues

**Connection Failures:**
- Verify host address and port
- Check username and authentication credentials
- Ensure SSH service is running on remote server
- Check firewall settings

**Authentication Failures:**
- Verify password accuracy
- Ensure SSH key is in PEM format
- Check key passphrase
- Verify SSH agent is running

**SSH Key Format Issues:**
Convert OpenSSH keys to PEM format:
```bash
ssh-keygen -p -m PEM -f ~/.ssh/id_rsa -N ""
```

### Testing Installation

```bash
# Check version
node dist/index.js --version

# Test basic functionality
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | node dist/index.js --stdin

# Verify MCP registration
claude mcp list
```

### Debug Mode

Enable debug logging for troubleshooting:

```bash
export SSH_MCP_LOG_LEVEL=DEBUG
export SSH_MCP_DEBUG=true
```

## Development

### Project Structure
```
SSH_MCP/
├── src/
│   ├── index.ts           # Entry point
│   ├── mcp-server.ts      # MCP server implementation
│   ├── connection-manager.ts # SSH connection management
│   ├── tools.ts           # MCP tools implementation
│   ├── env-parser.ts      # Environment variable parser
│   └── types.ts           # TypeScript type definitions
├── dist/                  # Compiled JavaScript
├── docs/                  # Documentation
└── README.md
```

### Build Commands

```bash
# Development build
npm run build

# Watch mode for development
npm run build:watch

# Clean build
npm run clean && npm run build
```

### Testing

```bash
# Run basic functionality test
npm test

# Test with debug output
SSH_MCP_DEBUG=true npm test
```

## Security Best Practices

### SSH Key Management
- Use SSH keys instead of passwords when possible
- Store private keys securely with appropriate file permissions (600)
- Use passphrases for additional key protection
- Regularly rotate SSH keys

### Environment Security
- Add `.sshenv` to `.gitignore` (automatically done by `ssh_init`)
- Never commit authentication credentials to version control
- Use environment variables for sensitive data
- Implement proper access controls on configuration files

### Connection Security
- Use non-standard SSH ports when possible
- Implement connection timeouts
- Monitor and log SSH access
- Use SSH agent for key management

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/hohollala/SSH_MCP/issues)
- **Documentation**: [Complete Documentation](docs/index.html)
- **Repository**: [GitHub Repository](https://github.com/hohollala/SSH_MCP)

## Version

Current Version: 0.1.0

---

**Note**: This is a Node.js/TypeScript implementation of SSH MCP Server, designed for seamless integration with AI clients for remote server management.