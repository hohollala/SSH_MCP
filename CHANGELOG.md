# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive documentation and usage examples
- API documentation with detailed tool specifications
- Troubleshooting guide for common issues
- MCP client-specific configuration examples
- Usage examples for different workflow patterns

## [0.1.0] - 2024-08-03

### Added
- Initial release of SSH MCP Server
- SSH connection management with multiple authentication methods
- Support for SSH key, password, and SSH agent authentication
- Remote command execution with timeout handling
- File system operations (read, write, list directory)
- Connection pooling and management
- MCP protocol implementation for AI clients
- Support for Claude Code, Gemini CLI, and Claude Desktop
- Comprehensive error handling and logging
- Automatic reconnection capabilities
- CLI entry point and configuration management
- Type hints and comprehensive test suite

### Features

#### Core SSH Operations
- **ssh_connect**: Establish SSH connections with multiple authentication methods
- **ssh_execute**: Execute commands on remote servers with timeout handling
- **ssh_read_file**: Read files from remote servers with encoding support
- **ssh_write_file**: Write files to remote servers with permission control
- **ssh_list_directory**: List directory contents with detailed information
- **ssh_disconnect**: Close SSH connections and clean up resources
- **ssh_list_connections**: List all active SSH connections

#### Authentication Methods
- **SSH Key Authentication**: Support for RSA, Ed25519, ECDSA, and DSA keys
- **Password Authentication**: Secure password-based authentication
- **SSH Agent Authentication**: Integration with SSH agent for key management
- **Encrypted Key Support**: Handle encrypted SSH keys with passphrases

#### Connection Management
- **Multiple Concurrent Connections**: Support up to 10 simultaneous connections
- **Connection Pooling**: Efficient connection reuse and management
- **Health Monitoring**: Automatic connection health checks and recovery
- **Unique Connection IDs**: Each connection gets a unique identifier
- **Connection Timeout**: Configurable connection and operation timeouts

#### MCP Protocol Compliance
- **JSON-RPC 2.0**: Full JSON-RPC 2.0 protocol implementation
- **MCP Standard**: Complete Model Context Protocol compliance
- **Tool Schema Validation**: Comprehensive parameter validation
- **Error Handling**: Standardized error codes and messages
- **Content Type Support**: Proper MCP content type handling

#### AI Client Compatibility
- **Claude Code**: Interactive development workflow support
- **Gemini CLI**: Batch analysis and system monitoring capabilities
- **Claude Desktop**: User-friendly desktop environment integration
- **Protocol Negotiation**: Automatic capability negotiation with clients

#### Error Handling and Logging
- **Comprehensive Error Codes**: Detailed error categorization
- **Debug Mode**: Extensive debug logging for troubleshooting
- **Configurable Logging**: Multiple log levels and output formats
- **Security Filtering**: Sensitive information filtering in logs
- **Error Recovery**: Automatic reconnection and error recovery

#### Security Features
- **Secure Authentication**: No credential storage or logging
- **Connection Encryption**: All SSH connections use encryption
- **Host Key Verification**: SSH host key validation
- **Rate Limiting**: Protection against brute force attacks
- **Input Validation**: Comprehensive parameter validation

#### Configuration and Deployment
- **Environment Variables**: Configurable via environment variables
- **Configuration Files**: Support for JSON configuration files
- **CLI Interface**: Command-line interface for server management
- **Package Distribution**: Available via PyPI and source installation
- **Cross-Platform**: Support for Linux, macOS, and Windows

#### Testing and Quality Assurance
- **Unit Tests**: Comprehensive unit test coverage
- **Integration Tests**: End-to-end integration testing
- **Compatibility Tests**: MCP client compatibility verification
- **Performance Tests**: Load and stress testing
- **Code Quality**: Type hints, linting, and formatting

#### Documentation
- **API Documentation**: Complete tool and parameter documentation
- **Usage Examples**: Practical usage examples and workflows
- **Client Configuration**: MCP client setup guides
- **Troubleshooting**: Common issues and solutions guide
- **Best Practices**: Security and performance recommendations

### Technical Specifications

#### Dependencies
- **Python**: 3.8+ support
- **Paramiko**: SSH client library (3.0.0+)
- **Cryptography**: Cryptographic operations (3.4.8+)
- **MCP Protocol**: Model Context Protocol implementation

#### Performance
- **Connection Limits**: Up to 10 concurrent connections (configurable)
- **Command Timeout**: 30-second default timeout (configurable)
- **File Size Limits**: 10MB default file operation limit
- **Memory Usage**: Efficient memory management and cleanup

#### Compatibility
- **Python Versions**: 3.8, 3.9, 3.10, 3.11, 3.12
- **Operating Systems**: Linux, macOS, Windows
- **SSH Servers**: OpenSSH and compatible SSH servers
- **MCP Clients**: Claude Code, Gemini CLI, Claude Desktop

[Unreleased]: https://github.com/ssh-mcp-server/ssh-mcp-server/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/ssh-mcp-server/ssh-mcp-server/releases/tag/v0.1.0