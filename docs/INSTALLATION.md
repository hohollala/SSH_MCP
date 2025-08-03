# SSH MCP Server Installation Guide

This guide provides detailed instructions for installing and setting up the SSH MCP Server on different platforms.

## System Requirements

### Minimum Requirements

- **Python**: 3.8 or higher
- **Operating System**: Linux, macOS, or Windows
- **Memory**: 256MB RAM
- **Disk Space**: 50MB free space
- **Network**: Internet connection for installation

### Recommended Requirements

- **Python**: 3.10 or higher
- **Memory**: 512MB RAM
- **Disk Space**: 100MB free space
- **SSH Client**: OpenSSH client tools

### Dependencies

The SSH MCP Server requires the following Python packages:

- `paramiko>=3.0.0,<4.0.0` - SSH client library
- `cryptography>=3.4.8,<42.0.0` - Cryptographic operations

## Installation Methods

### Method 1: Install from PyPI (Recommended)

This is the easiest and recommended method for most users.

```bash
# Install the latest stable version
pip install ssh-mcp-server

# Verify installation
ssh-mcp-server --version
```

#### With Virtual Environment (Recommended)

```bash
# Create a virtual environment
python -m venv ssh-mcp-env

# Activate the virtual environment
# On Linux/macOS:
source ssh-mcp-env/bin/activate
# On Windows:
ssh-mcp-env\Scripts\activate

# Install SSH MCP Server
pip install ssh-mcp-server

# Verify installation
ssh-mcp-server --version
```

### Method 2: Install from Source

For developers or users who want the latest features:

```bash
# Clone the repository
git clone https://github.com/ssh-mcp-server/ssh-mcp-server.git
cd ssh-mcp-server

# Install in development mode
pip install -e .

# Or install normally
pip install .

# Verify installation
ssh-mcp-server --version
```

### Method 3: Development Installation

For contributors and developers:

```bash
# Clone the repository
git clone https://github.com/ssh-mcp-server/ssh-mcp-server.git
cd ssh-mcp-server

# Install with development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run tests to verify installation
pytest

# Verify installation
ssh-mcp-server --version
```

## Platform-Specific Instructions

### Linux (Ubuntu/Debian)

```bash
# Update package list
sudo apt update

# Install Python and pip if not already installed
sudo apt install python3 python3-pip python3-venv

# Install SSH MCP Server
pip3 install ssh-mcp-server

# Add to PATH if needed
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Verify installation
ssh-mcp-server --version
```

### Linux (CentOS/RHEL/Fedora)

```bash
# Install Python and pip
sudo dnf install python3 python3-pip  # Fedora
# or
sudo yum install python3 python3-pip  # CentOS/RHEL

# Install SSH MCP Server
pip3 install ssh-mcp-server

# Add to PATH if needed
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Verify installation
ssh-mcp-server --version
```

### macOS

#### Using Homebrew (Recommended)

```bash
# Install Python if not already installed
brew install python

# Install SSH MCP Server
pip3 install ssh-mcp-server

# Verify installation
ssh-mcp-server --version
```

#### Using System Python

```bash
# Install SSH MCP Server
pip3 install --user ssh-mcp-server

# Add to PATH if needed
echo 'export PATH="$HOME/Library/Python/3.x/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# Verify installation
ssh-mcp-server --version
```

### Windows

#### Using Python from python.org

```cmd
# Download and install Python from https://python.org
# Make sure to check "Add Python to PATH" during installation

# Install SSH MCP Server
pip install ssh-mcp-server

# Verify installation
ssh-mcp-server --version
```

#### Using Windows Subsystem for Linux (WSL)

```bash
# Install WSL and Ubuntu
wsl --install

# Follow Linux Ubuntu instructions above
```

## Configuration

### Basic Configuration

Create a configuration directory:

```bash
# Linux/macOS
mkdir -p ~/.ssh-mcp-server

# Windows
mkdir %USERPROFILE%\.ssh-mcp-server
```

Create a basic configuration file:

```bash
# Linux/macOS
cat > ~/.ssh-mcp-server/config.json << EOF
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
    "keepalive_interval": 30
  }
}
EOF
```

### Environment Variables

Set up environment variables for configuration:

```bash
# Linux/macOS - Add to ~/.bashrc or ~/.zshrc
export SSH_MCP_DEBUG=false
export SSH_MCP_TIMEOUT=30
export SSH_MCP_MAX_CONNECTIONS=10
export SSH_MCP_LOG_LEVEL=INFO

# Windows - Add to system environment variables
set SSH_MCP_DEBUG=false
set SSH_MCP_TIMEOUT=30
set SSH_MCP_MAX_CONNECTIONS=10
set SSH_MCP_LOG_LEVEL=INFO
```

### SSH Configuration

Ensure SSH client is properly configured:

```bash
# Create SSH directory if it doesn't exist
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Create SSH config file
cat > ~/.ssh/config << EOF
Host *
    ServerAliveInterval 60
    ServerAliveCountMax 3
    Compression yes
    ControlMaster auto
    ControlPath ~/.ssh/control-%r@%h:%p
    ControlPersist 10m
EOF

chmod 600 ~/.ssh/config
```

## MCP Client Setup

### Claude Code

Add to your Claude Code MCP configuration:

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

### Gemini CLI

Add to your Gemini CLI configuration:

```json
{
  "mcpServers": {
    "ssh-server": {
      "command": "ssh-mcp-server",
      "env": {
        "SSH_MCP_TIMEOUT": "45"
      }
    }
  }
}
```

### Claude Desktop

Add to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "ssh-server": {
      "command": "ssh-mcp-server",
      "env": {
        "SSH_MCP_MAX_CONNECTIONS": "5"
      }
    }
  }
}
```

## Verification

### Test Installation

```bash
# Check version
ssh-mcp-server --version

# Test basic functionality
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | ssh-mcp-server --stdin

# Run built-in tests
python -m ssh_mcp_server.tests.basic_test
```

### Test SSH Connectivity

```bash
# Test SSH connection manually
ssh user@hostname

# Test with SSH MCP Server
ssh-mcp-server --test-connection user@hostname
```

## Troubleshooting Installation

### Common Issues

#### Issue: "ssh-mcp-server: command not found"

**Solution:**
```bash
# Check if installed
pip show ssh-mcp-server

# Find installation location
python -c "import ssh_mcp_server; print(ssh_mcp_server.__file__)"

# Add to PATH
export PATH="$HOME/.local/bin:$PATH"
```

#### Issue: "Permission denied" during installation

**Solution:**
```bash
# Install for user only
pip install --user ssh-mcp-server

# Or use virtual environment
python -m venv venv
source venv/bin/activate
pip install ssh-mcp-server
```

#### Issue: "No module named 'paramiko'"

**Solution:**
```bash
# Install dependencies manually
pip install paramiko cryptography

# Then install SSH MCP Server
pip install ssh-mcp-server
```

#### Issue: "SSL certificate verify failed"

**Solution:**
```bash
# Upgrade pip and certificates
pip install --upgrade pip
pip install --upgrade certifi

# Install with trusted hosts
pip install --trusted-host pypi.org --trusted-host pypi.python.org ssh-mcp-server
```

### Platform-Specific Issues

#### Linux: "error: Microsoft Visual C++ 14.0 is required"

This error occurs when installing on Windows. Install Visual Studio Build Tools:

```bash
# Download and install Visual Studio Build Tools
# Or use pre-compiled wheels
pip install --only-binary=all ssh-mcp-server
```

#### macOS: "error: command 'clang' failed"

```bash
# Install Xcode command line tools
xcode-select --install

# Or install via Homebrew
brew install python
pip3 install ssh-mcp-server
```

#### Windows: "error: Microsoft Visual C++ 14.0 is required"

```cmd
# Install Visual Studio Build Tools
# Or use conda
conda install ssh-mcp-server
```

## Upgrading

### Upgrade from PyPI

```bash
# Upgrade to latest version
pip install --upgrade ssh-mcp-server

# Verify upgrade
ssh-mcp-server --version
```

### Upgrade from Source

```bash
# Pull latest changes
git pull origin main

# Reinstall
pip install -e .

# Verify upgrade
ssh-mcp-server --version
```

## Uninstallation

### Remove Package

```bash
# Uninstall SSH MCP Server
pip uninstall ssh-mcp-server

# Remove configuration (optional)
rm -rf ~/.ssh-mcp-server
```

### Clean Virtual Environment

```bash
# Deactivate virtual environment
deactivate

# Remove virtual environment directory
rm -rf ssh-mcp-env
```

## Docker Installation

### Using Docker

```bash
# Pull the Docker image
docker pull ssh-mcp-server/ssh-mcp-server:latest

# Run the container
docker run -d \
  --name ssh-mcp-server \
  -p 8080:8080 \
  -v ~/.ssh:/root/.ssh:ro \
  -e SSH_MCP_DEBUG=false \
  ssh-mcp-server/ssh-mcp-server:latest

# Verify container is running
docker ps
```

### Build from Source

```bash
# Clone repository
git clone https://github.com/ssh-mcp-server/ssh-mcp-server.git
cd ssh-mcp-server

# Build Docker image
docker build -t ssh-mcp-server .

# Run container
docker run -d \
  --name ssh-mcp-server \
  -v ~/.ssh:/root/.ssh:ro \
  ssh-mcp-server
```

## Next Steps

After successful installation:

1. **Read the [API Documentation](API.md)** to understand available tools
2. **Configure your MCP client** using the [Client Configuration Guide](CLIENT_CONFIGURATIONS.md)
3. **Try the usage examples** in the [examples directory](../examples/)
4. **Review the [Troubleshooting Guide](TROUBLESHOOTING.md)** for common issues
5. **Join the community** on [GitHub Discussions](https://github.com/ssh-mcp-server/ssh-mcp-server/discussions)

## Support

If you encounter issues during installation:

1. Check the [Troubleshooting Guide](TROUBLESHOOTING.md)
2. Search [existing issues](https://github.com/ssh-mcp-server/ssh-mcp-server/issues)
3. Create a [new issue](https://github.com/ssh-mcp-server/ssh-mcp-server/issues/new) with:
   - Your operating system and version
   - Python version (`python --version`)
   - Installation method used
   - Complete error message
   - Steps to reproduce the issue