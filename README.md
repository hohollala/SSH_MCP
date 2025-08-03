# SSH MCP Server

A Model Context Protocol (MCP) server that enables AI clients like Claude Code, Gemini CLI, and Claude Desktop to perform SSH operations on remote Linux servers. This server provides secure, efficient remote server management through a standardized MCP interface.

## Features

- **Multi-Client Support**: Compatible with Claude Code, Gemini CLI, and Claude Desktop
- **Secure Authentication**: SSH key, password, and SSH agent authentication methods
- **Connection Management**: Multiple concurrent SSH connections with unique identifiers
- **Remote Operations**: Command execution, file operations, and directory management
- **Error Handling**: Comprehensive error reporting and recovery mechanisms
- **MCP Compliance**: Full Model Context Protocol and JSON-RPC 2.0 compliance

## Installation

### From PyPI (Recommended)

```bash
pip install ssh-mcp-server
```

### From Source

```bash
git clone https://github.com/ssh-mcp-server/ssh-mcp-server.git
cd ssh-mcp-server
pip install -e .
```

### Development Installation

```bash
git clone https://github.com/ssh-mcp-server/ssh-mcp-server.git
cd ssh-mcp-server
pip install -e ".[dev]"
```

## Quick Start

### 1. Basic Usage

Start the MCP server:

```bash
ssh-mcp-server
```

Or run as a Python module:

```bash
python -m ssh_mcp_server
```

### 2. MCP Client Configuration

Configure your MCP client to use the SSH MCP server:

#### Claude Code Configuration

Add to your MCP settings:

```json
{
  "mcpServers": {
    "ssh-server": {
      "command": "ssh-mcp-server",
      "env": {
        "SSH_MCP_DEBUG": "false"
      }
    }
  }
}
```

#### Gemini CLI Configuration

```json
{
  "mcpServers": {
    "ssh-server": {
      "command": "python",
      "args": ["-m", "ssh_mcp_server"],
      "env": {
        "SSH_MCP_TIMEOUT": "30"
      }
    }
  }
}
```

#### Claude Desktop Configuration

```json
{
  "mcpServers": {
    "ssh-server": {
      "command": "ssh-mcp-server",
      "args": [],
      "env": {
        "SSH_MCP_MAX_CONNECTIONS": "10"
      }
    }
  }
}
```

## Available Tools

The SSH MCP Server provides the following tools:

### Connection Management

- **`ssh_connect`**: Establish SSH connection to a remote server
- **`ssh_disconnect`**: Close an existing SSH connection
- **`ssh_list_connections`**: List all active SSH connections

### Command Execution

- **`ssh_execute`**: Execute commands on remote servers

### File Operations

- **`ssh_read_file`**: Read files from remote servers
- **`ssh_write_file`**: Write files to remote servers
- **`ssh_list_directory`**: List directory contents on remote servers

## Usage Examples

### Connecting to a Server

```python
# Using SSH key authentication
{
  "name": "ssh_connect",
  "arguments": {
    "hostname": "example.com",
    "username": "myuser",
    "auth_method": "key",
    "key_path": "~/.ssh/id_rsa"
  }
}

# Using password authentication
{
  "name": "ssh_connect",
  "arguments": {
    "hostname": "example.com",
    "username": "myuser",
    "auth_method": "password",
    "password": "mypassword"
  }
}

# Using SSH agent
{
  "name": "ssh_connect",
  "arguments": {
    "hostname": "example.com",
    "username": "myuser",
    "auth_method": "agent"
  }
}
```

### Executing Commands

```python
{
  "name": "ssh_execute",
  "arguments": {
    "connection_id": "conn_12345",
    "command": "ls -la /home/user"
  }
}
```

### File Operations

```python
# Read a file
{
  "name": "ssh_read_file",
  "arguments": {
    "connection_id": "conn_12345",
    "file_path": "/etc/hostname"
  }
}

# Write a file
{
  "name": "ssh_write_file",
  "arguments": {
    "connection_id": "conn_12345",
    "file_path": "/tmp/test.txt",
    "content": "Hello, World!"
  }
}

# List directory
{
  "name": "ssh_list_directory",
  "arguments": {
    "connection_id": "conn_12345",
    "directory_path": "/home/user"
  }
}
```

## Configuration

### Environment Variables

- **`SSH_MCP_DEBUG`**: Enable debug logging (default: `false`)
- **`SSH_MCP_TIMEOUT`**: Default connection timeout in seconds (default: `30`)
- **`SSH_MCP_MAX_CONNECTIONS`**: Maximum concurrent connections (default: `10`)
- **`SSH_MCP_LOG_LEVEL`**: Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`)

### Configuration File

Create a configuration file at `~/.ssh-mcp-server/config.json`:

```json
{
  "max_connections": 10,
  "default_timeout": 30,
  "debug": false,
  "log_level": "INFO",
  "ssh_config": {
    "host_key_policy": "auto_add",
    "compression": true,
    "keepalive_interval": 30
  }
}
```

## Authentication Methods

### SSH Key Authentication

```python
{
  "auth_method": "key",
  "key_path": "~/.ssh/id_rsa",
  "key_passphrase": "optional_passphrase"  # Optional
}
```

Supported key types:
- RSA
- Ed25519
- ECDSA
- DSA

### Password Authentication

```python
{
  "auth_method": "password",
  "password": "your_password"
}
```

### SSH Agent Authentication

```python
{
  "auth_method": "agent"
}
```

The server will use keys available in your SSH agent.

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=ssh_mcp_server

# Run integration tests
pytest tests/test_*_integration.py

# Run compatibility tests
pytest tests/test_mcp_client_compatibility.py
```

### Code Quality

```bash
# Format code
black ssh_mcp_server tests

# Sort imports
isort ssh_mcp_server tests

# Type checking
mypy ssh_mcp_server

# Linting
flake8 ssh_mcp_server tests
```

### Building Documentation

```bash
# Install docs dependencies
pip install -e ".[docs]"

# Build documentation
cd docs
make html
```

## Documentation

### Quick Links

- **[Installation Guide](docs/INSTALLATION.md)** - Detailed installation instructions for all platforms
- **[API Documentation](docs/API.md)** - Complete tool reference and parameter specifications
- **[Client Configurations](docs/CLIENT_CONFIGURATIONS.md)** - MCP client setup examples and configurations
- **[Troubleshooting Guide](docs/TROUBLESHOOTING.md)** - Common issues and solutions
- **[Usage Examples](examples/usage_examples.py)** - Practical usage examples and workflows

### Getting Started

1. **Install**: Follow the [Installation Guide](docs/INSTALLATION.md)
2. **Configure**: Set up your MCP client using [Client Configurations](docs/CLIENT_CONFIGURATIONS.md)
3. **Learn**: Try the [Usage Examples](examples/usage_examples.py)
4. **Reference**: Use the [API Documentation](docs/API.md) for detailed tool information
5. **Troubleshoot**: Check the [Troubleshooting Guide](docs/TROUBLESHOOTING.md) if you encounter issues

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/ssh-mcp-server/ssh-mcp-server/issues)
- **Documentation**: [Read the Docs](https://ssh-mcp-server.readthedocs.io/)
- **Discussions**: [GitHub Discussions](https://github.com/ssh-mcp-server/ssh-mcp-server/discussions)