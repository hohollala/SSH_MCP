# SSH MCP Server API Documentation

This document provides detailed information about all available tools and their parameters in the SSH MCP Server.

## Overview

The SSH MCP Server implements the Model Context Protocol (MCP) and provides SSH operations through JSON-RPC 2.0 messages. All tools follow the MCP specification and return structured responses.

## Tool Categories

### Connection Management Tools

#### ssh_connect

Establishes an SSH connection to a remote server.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `hostname` | string | Yes | Remote server hostname or IP address |
| `username` | string | Yes | SSH username |
| `auth_method` | string | Yes | Authentication method: `"key"`, `"password"`, or `"agent"` |
| `port` | integer | No | SSH port (default: 22) |
| `timeout` | integer | No | Connection timeout in seconds (default: 30) |
| `key_path` | string | No | Path to SSH private key (required for `"key"` auth) |
| `key_passphrase` | string | No | Passphrase for encrypted SSH key |
| `password` | string | No | SSH password (required for `"password"` auth) |

**Example Request:**

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "ssh_connect",
    "arguments": {
      "hostname": "example.com",
      "username": "myuser",
      "auth_method": "key",
      "key_path": "~/.ssh/id_rsa",
      "port": 22,
      "timeout": 30
    }
  },
  "id": 1
}
```

**Success Response:**

```json
{
  "jsonrpc": "2.0",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"success\": true, \"connection_id\": \"conn_abc123\", \"message\": \"Successfully connected to example.com\"}"
      }
    ]
  },
  "id": 1
}
```

**Error Response:**

```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -1,
    "message": "SSH connection failed: Authentication failed",
    "data": {
      "hostname": "example.com",
      "username": "myuser",
      "error_type": "authentication_error"
    }
  },
  "id": 1
}
```

#### ssh_disconnect

Closes an existing SSH connection.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `connection_id` | string | Yes | ID of the connection to close |

**Example Request:**

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "ssh_disconnect",
    "arguments": {
      "connection_id": "conn_abc123"
    }
  },
  "id": 2
}
```

**Success Response:**

```json
{
  "jsonrpc": "2.0",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"success\": true, \"message\": \"Connection conn_abc123 closed successfully\"}"
      }
    ]
  },
  "id": 2
}
```

#### ssh_list_connections

Lists all active SSH connections.

**Parameters:**

None.

**Example Request:**

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "ssh_list_connections",
    "arguments": {}
  },
  "id": 3
}
```

**Success Response:**

```json
{
  "jsonrpc": "2.0",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"success\": true, \"data\": {\"connections\": [{\"connection_id\": \"conn_abc123\", \"hostname\": \"example.com\", \"username\": \"myuser\", \"connected\": true, \"created_at\": \"2024-01-01T12:00:00Z\"}], \"total\": 1}}"
      }
    ]
  },
  "id": 3
}
```

### Command Execution Tools

#### ssh_execute

Executes a command on a remote server via SSH.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `connection_id` | string | Yes | ID of the SSH connection to use |
| `command` | string | Yes | Command to execute |
| `timeout` | integer | No | Command timeout in seconds (default: 30) |
| `working_directory` | string | No | Working directory for command execution |

**Example Request:**

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "ssh_execute",
    "arguments": {
      "connection_id": "conn_abc123",
      "command": "ls -la /home/user",
      "timeout": 10
    }
  },
  "id": 4
}
```

**Success Response:**

```json
{
  "jsonrpc": "2.0",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"success\": true, \"data\": {\"stdout\": \"total 24\\ndrwxr-xr-x 3 user user 4096 Jan  1 12:00 .\\ndrwxr-xr-x 3 root root 4096 Jan  1 11:00 ..\\n-rw-r--r-- 1 user user  220 Jan  1 12:00 .bash_logout\", \"stderr\": \"\", \"exit_code\": 0, \"execution_time\": 0.123}}"
      }
    ]
  },
  "id": 4
}
```

**Error Response:**

```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -1,
    "message": "Command execution failed: Permission denied",
    "data": {
      "connection_id": "conn_abc123",
      "command": "ls -la /root",
      "exit_code": 1,
      "stderr": "ls: cannot open directory '/root': Permission denied"
    }
  },
  "id": 4
}
```

### File Operation Tools

#### ssh_read_file

Reads the contents of a file from a remote server.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `connection_id` | string | Yes | ID of the SSH connection to use |
| `file_path` | string | Yes | Path to the file to read |
| `encoding` | string | No | File encoding (default: "utf-8") |
| `max_size` | integer | No | Maximum file size in bytes (default: 1MB) |

**Example Request:**

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "ssh_read_file",
    "arguments": {
      "connection_id": "conn_abc123",
      "file_path": "/etc/hostname",
      "encoding": "utf-8"
    }
  },
  "id": 5
}
```

**Success Response:**

```json
{
  "jsonrpc": "2.0",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"success\": true, \"data\": {\"content\": \"myserver.example.com\\n\", \"size\": 20, \"encoding\": \"utf-8\", \"file_path\": \"/etc/hostname\"}}"
      }
    ]
  },
  "id": 5
}
```

#### ssh_write_file

Writes content to a file on a remote server.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `connection_id` | string | Yes | ID of the SSH connection to use |
| `file_path` | string | Yes | Path to the file to write |
| `content` | string | Yes | Content to write to the file |
| `encoding` | string | No | File encoding (default: "utf-8") |
| `mode` | string | No | File permissions in octal (e.g., "644") |
| `create_directories` | boolean | No | Create parent directories if they don't exist |

**Example Request:**

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "ssh_write_file",
    "arguments": {
      "connection_id": "conn_abc123",
      "file_path": "/tmp/test.txt",
      "content": "Hello, World!\nThis is a test file.",
      "mode": "644",
      "create_directories": true
    }
  },
  "id": 6
}
```

**Success Response:**

```json
{
  "jsonrpc": "2.0",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"success\": true, \"data\": {\"bytes_written\": 35, \"file_path\": \"/tmp/test.txt\", \"mode\": \"644\"}}"
      }
    ]
  },
  "id": 6
}
```

#### ssh_list_directory

Lists the contents of a directory on a remote server.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `connection_id` | string | Yes | ID of the SSH connection to use |
| `directory_path` | string | Yes | Path to the directory to list |
| `show_hidden` | boolean | No | Include hidden files (default: false) |
| `detailed` | boolean | No | Include detailed file information (default: false) |

**Example Request:**

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "ssh_list_directory",
    "arguments": {
      "connection_id": "conn_abc123",
      "directory_path": "/home/user",
      "show_hidden": true,
      "detailed": true
    }
  },
  "id": 7
}
```

**Success Response:**

```json
{
  "jsonrpc": "2.0",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"success\": true, \"data\": {\"directory_path\": \"/home/user\", \"entries\": [{\"name\": \".\", \"type\": \"directory\", \"size\": 4096, \"permissions\": \"drwxr-xr-x\", \"owner\": \"user\", \"group\": \"user\", \"modified\": \"2024-01-01T12:00:00Z\"}, {\"name\": \"..\", \"type\": \"directory\", \"size\": 4096, \"permissions\": \"drwxr-xr-x\", \"owner\": \"root\", \"group\": \"root\", \"modified\": \"2024-01-01T11:00:00Z\"}, {\"name\": \"document.txt\", \"type\": \"file\", \"size\": 1024, \"permissions\": \"-rw-r--r--\", \"owner\": \"user\", \"group\": \"user\", \"modified\": \"2024-01-01T12:30:00Z\"}], \"total\": 3}}"
      }
    ]
  },
  "id": 7
}
```

## Error Handling

### Error Codes

The SSH MCP Server uses standard JSON-RPC 2.0 error codes plus custom error codes:

| Code | Description |
|------|-------------|
| -32700 | Parse error (Invalid JSON) |
| -32600 | Invalid Request |
| -32601 | Method not found |
| -32602 | Invalid params |
| -32603 | Internal error |
| -1 | SSH connection error |
| -2 | Authentication error |
| -3 | Command execution error |
| -4 | File operation error |
| -5 | Permission error |
| -6 | Timeout error |
| -7 | Network error |

### Error Response Format

All errors follow the JSON-RPC 2.0 error response format:

```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -1,
    "message": "Human-readable error message",
    "data": {
      "additional": "error details",
      "context": "specific to the error type"
    }
  },
  "id": 1
}
```

### Common Error Scenarios

#### Connection Errors

```json
{
  "error": {
    "code": -1,
    "message": "SSH connection failed: Connection timed out",
    "data": {
      "hostname": "unreachable.example.com",
      "port": 22,
      "timeout": 30,
      "error_type": "connection_timeout"
    }
  }
}
```

#### Authentication Errors

```json
{
  "error": {
    "code": -2,
    "message": "SSH authentication failed: Invalid credentials",
    "data": {
      "hostname": "example.com",
      "username": "wronguser",
      "auth_method": "password",
      "error_type": "authentication_failed"
    }
  }
}
```

#### Permission Errors

```json
{
  "error": {
    "code": -5,
    "message": "Permission denied: Cannot read file",
    "data": {
      "file_path": "/root/secret.txt",
      "operation": "read",
      "error_type": "permission_denied"
    }
  }
}
```

## Response Formats

### Success Response Structure

All successful tool calls return a response with this structure:

```json
{
  "jsonrpc": "2.0",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{JSON_STRING_WITH_RESULT_DATA}"
      }
    ]
  },
  "id": REQUEST_ID
}
```

The `text` field contains a JSON string with the actual result data.

### Data Structures

#### Connection Info

```json
{
  "connection_id": "conn_abc123",
  "hostname": "example.com",
  "username": "myuser",
  "port": 22,
  "connected": true,
  "created_at": "2024-01-01T12:00:00Z",
  "last_used": "2024-01-01T12:30:00Z"
}
```

#### Command Result

```json
{
  "stdout": "command output",
  "stderr": "error output",
  "exit_code": 0,
  "execution_time": 1.234
}
```

#### File Info

```json
{
  "name": "filename.txt",
  "type": "file",
  "size": 1024,
  "permissions": "-rw-r--r--",
  "owner": "user",
  "group": "user",
  "modified": "2024-01-01T12:00:00Z"
}
```

## Authentication Details

### SSH Key Authentication

When using SSH key authentication:

1. The `key_path` parameter should point to a private key file
2. Supported key formats: OpenSSH, PEM, PKCS#8
3. Encrypted keys require the `key_passphrase` parameter
4. The server will attempt to load the key and authenticate

### Password Authentication

When using password authentication:

1. The password is transmitted securely through the MCP connection
2. Passwords are not logged or stored
3. Failed attempts are rate-limited to prevent brute force attacks

### SSH Agent Authentication

When using SSH agent authentication:

1. The server connects to the SSH agent via the SSH_AUTH_SOCK environment variable
2. All keys available in the agent are tried for authentication
3. This method is recommended for security and convenience

## Rate Limiting and Quotas

### Connection Limits

- Maximum concurrent connections: 10 (configurable)
- Connection timeout: 30 seconds (configurable)
- Idle connection cleanup: 1 hour

### Command Execution Limits

- Maximum command timeout: 300 seconds
- Maximum concurrent commands per connection: 5
- Command output size limit: 10MB

### File Operation Limits

- Maximum file size for read operations: 10MB
- Maximum file size for write operations: 10MB
- Maximum directory entries returned: 1000

## Best Practices

### Connection Management

1. Always call `ssh_disconnect` when done with a connection
2. Reuse connections for multiple operations when possible
3. Handle connection failures gracefully with retry logic

### Error Handling

1. Check the error code to determine the appropriate response
2. Use the error data for debugging and user feedback
3. Implement exponential backoff for transient errors

### Security

1. Use SSH key authentication when possible
2. Avoid hardcoding credentials in client code
3. Validate file paths to prevent directory traversal attacks
4. Limit command execution to trusted operations

### Performance

1. Batch multiple operations when possible
2. Use appropriate timeouts for long-running operations
3. Monitor connection usage and clean up unused connections