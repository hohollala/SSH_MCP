/**
 * Type definitions for SSH MCP Server
 */

// SSH Connection Types
export interface SSHConnection {
  id: string;
  host: string;
  port: number;
  username: string;
  isConnected: boolean;
  createdAt: Date;
  lastUsed: Date;
}

// SSH Authentication Types
export interface SSHAuthConfig {
  password?: string;
  privateKey?: string;
  passphrase?: string;
  agent?: boolean;
}

// SSH Command Types
export interface SSHCommand {
  id: string;
  command: string;
  cwd?: string;
  env?: Record<string, string>;
  timeout?: number;
}

// SSH Command Result
export interface SSHCommandResult {
  id: string;
  exitCode: number;
  stdout: string;
  stderr: string;
  duration: number;
}

// File Operation Types
export interface FileOperation {
  id: string;
  operation: 'read' | 'write' | 'delete' | 'list' | 'upload' | 'download';
  path: string;
  content?: string;
  encoding?: string;
}

// File Operation Result
export interface FileOperationResult {
  id: string;
  success: boolean;
  content?: string;
  files?: string[];
  error?: string;
}

// MCP Tool Types
export interface MCPTool {
  name: string;
  description: string;
  inputSchema: Record<string, any>;
}

// Error Types
export interface SSHMCPServerError extends Error {
  code: string;
  details?: any;
}

// Connection Manager Types
export interface ConnectionManager {
  connect(host: string, port: number, username: string, auth: SSHAuthConfig): Promise<SSHConnection>;
  disconnect(connectionId: string): Promise<void>;
  executeCommand(connectionId: string, command: SSHCommand): Promise<SSHCommandResult>;
  listConnections(): SSHConnection[];
  getConnection(connectionId: string): SSHConnection | undefined;
}

// Tool Manager Types
export interface ToolManager {
  registerTool(tool: MCPTool): void;
  getTools(): MCPTool[];
  executeTool(name: string, args: Record<string, any>): Promise<any>;
}