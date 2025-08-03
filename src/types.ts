/**
 * Type definitions for SSH MCP Server
 */

export interface SSHConfig {
  hostname: string;
  username: string;
  port?: number;
  authMethod: 'key' | 'password' | 'agent';
  keyPath?: string;
  password?: string;
  timeout?: number;
}

export interface CommandResult {
  stdout: string;
  stderr: string;
  exitCode: number;
  executionTime: number;
}

export interface ConnectionInfo {
  connectionId: string;
  hostname: string;
  username: string;
  port: number;
  connected: boolean;
  createdAt: Date;
  lastUsed: Date;
}

export interface MCPTool {
  name: string;
  description: string;
  inputSchema: {
    type: string;
    properties: Record<string, any>;
    required?: string[];
  };
}

export interface MCPResource {
  uri: string;
  name: string;
  description?: string;
  mimeType?: string;
}