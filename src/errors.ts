import { SSHMCPServerError } from './types.js';

// Error codes
export enum ErrorCode {
  // Connection errors
  CONNECTION_FAILED = 'CONNECTION_FAILED',
  CONNECTION_TIMEOUT = 'CONNECTION_TIMEOUT',
  AUTHENTICATION_FAILED = 'AUTHENTICATION_FAILED',
  CONNECTION_NOT_FOUND = 'CONNECTION_NOT_FOUND',
  
  // Command execution errors
  COMMAND_TIMEOUT = 'COMMAND_TIMEOUT',
  COMMAND_FAILED = 'COMMAND_FAILED',
  INVALID_COMMAND = 'INVALID_COMMAND',
  
  // File operation errors
  FILE_NOT_FOUND = 'FILE_NOT_FOUND',
  FILE_ACCESS_DENIED = 'FILE_ACCESS_DENIED',
  FILE_OPERATION_FAILED = 'FILE_OPERATION_FAILED',
  
  // Configuration errors
  INVALID_CONFIG = 'INVALID_CONFIG',
  MISSING_CONFIG = 'MISSING_CONFIG',
  
  // MCP protocol errors
  INVALID_REQUEST = 'INVALID_REQUEST',
  METHOD_NOT_FOUND = 'METHOD_NOT_FOUND',
  INVALID_PARAMS = 'INVALID_PARAMS',
  
  // General errors
  INTERNAL_ERROR = 'INTERNAL_ERROR',
  NOT_IMPLEMENTED = 'NOT_IMPLEMENTED'
}

// Error messages
export const ErrorMessages: Record<ErrorCode, string> = {
  [ErrorCode.CONNECTION_FAILED]: 'Failed to establish SSH connection',
  [ErrorCode.CONNECTION_TIMEOUT]: 'SSH connection timed out',
  [ErrorCode.AUTHENTICATION_FAILED]: 'SSH authentication failed',
  [ErrorCode.CONNECTION_NOT_FOUND]: 'SSH connection not found',
  [ErrorCode.COMMAND_TIMEOUT]: 'Command execution timed out',
  [ErrorCode.COMMAND_FAILED]: 'Command execution failed',
  [ErrorCode.INVALID_COMMAND]: 'Invalid command provided',
  [ErrorCode.FILE_NOT_FOUND]: 'File not found',
  [ErrorCode.FILE_ACCESS_DENIED]: 'File access denied',
  [ErrorCode.FILE_OPERATION_FAILED]: 'File operation failed',
  [ErrorCode.INVALID_CONFIG]: 'Invalid configuration',
  [ErrorCode.MISSING_CONFIG]: 'Missing configuration',
  [ErrorCode.INVALID_REQUEST]: 'Invalid MCP request',
  [ErrorCode.METHOD_NOT_FOUND]: 'MCP method not found',
  [ErrorCode.INVALID_PARAMS]: 'Invalid MCP parameters',
  [ErrorCode.INTERNAL_ERROR]: 'Internal server error',
  [ErrorCode.NOT_IMPLEMENTED]: 'Feature not implemented'
};

// Error factory
export class ErrorFactory {
  static createError(code: ErrorCode, message?: string, details?: any): SSHMCPServerError {
    const error = new Error(message || ErrorMessages[code]) as SSHMCPServerError;
    error.code = code;
    error.details = details;
    error.name = 'SSHMCPServerError';
    return error;
  }

  static isSSHMCPServerError(error: any): error is SSHMCPServerError {
    return error && typeof error === 'object' && 'code' in error;
  }

  static connectionFailed(host: string, port: number, details?: any): SSHMCPServerError {
    return this.createError(
      ErrorCode.CONNECTION_FAILED,
      `Failed to connect to ${host}:${port}`,
      { host, port, ...details }
    );
  }

  static connectionTimeout(host: string, port: number, timeout: number): SSHMCPServerError {
    return this.createError(
      ErrorCode.CONNECTION_TIMEOUT,
      `Connection to ${host}:${port} timed out after ${timeout}s`,
      { host, port, timeout }
    );
  }

  static authenticationFailed(host: string, username: string, details?: any): SSHMCPServerError {
    return this.createError(
      ErrorCode.AUTHENTICATION_FAILED,
      `Authentication failed for ${username}@${host}`,
      { host, username, ...details }
    );
  }

  static connectionNotFound(connectionId: string): SSHMCPServerError {
    return this.createError(
      ErrorCode.CONNECTION_NOT_FOUND,
      `Connection ${connectionId} not found`,
      { connectionId }
    );
  }

  static commandTimeout(command: string, timeout: number): SSHMCPServerError {
    return this.createError(
      ErrorCode.COMMAND_TIMEOUT,
      `Command execution timed out after ${timeout}s: ${command}`,
      { command, timeout }
    );
  }

  static commandFailed(command: string, exitCode: number, stderr: string): SSHMCPServerError {
    return this.createError(
      ErrorCode.COMMAND_FAILED,
      `Command failed with exit code ${exitCode}: ${command}`,
      { command, exitCode, stderr }
    );
  }

  static invalidCommand(command: string, reason: string): SSHMCPServerError {
    return this.createError(
      ErrorCode.INVALID_COMMAND,
      `Invalid command: ${command} - ${reason}`,
      { command, reason }
    );
  }

  static fileNotFound(path: string): SSHMCPServerError {
    return this.createError(
      ErrorCode.FILE_NOT_FOUND,
      `File not found: ${path}`,
      { path }
    );
  }

  static fileAccessDenied(path: string): SSHMCPServerError {
    return this.createError(
      ErrorCode.FILE_ACCESS_DENIED,
      `Access denied to file: ${path}`,
      { path }
    );
  }

  static fileOperationFailed(operation: string, path: string, details?: any): SSHMCPServerError {
    return this.createError(
      ErrorCode.FILE_OPERATION_FAILED,
      `File operation failed: ${operation} on ${path}`,
      { operation, path, ...details }
    );
  }

  static invalidConfig(key: string, value: any): SSHMCPServerError {
    return this.createError(
      ErrorCode.INVALID_CONFIG,
      `Invalid configuration: ${key} = ${value}`,
      { key, value }
    );
  }

  static missingConfig(key: string): SSHMCPServerError {
    return this.createError(
      ErrorCode.MISSING_CONFIG,
      `Missing configuration: ${key}`,
      { key }
    );
  }

  static invalidRequest(method: string, details?: any): SSHMCPServerError {
    return this.createError(
      ErrorCode.INVALID_REQUEST,
      `Invalid MCP request: ${method}`,
      { method, ...details }
    );
  }

  static methodNotFound(method: string): SSHMCPServerError {
    return this.createError(
      ErrorCode.METHOD_NOT_FOUND,
      `MCP method not found: ${method}`,
      { method }
    );
  }

  static invalidParams(method: string, details?: any): SSHMCPServerError {
    return this.createError(
      ErrorCode.INVALID_PARAMS,
      `Invalid parameters for method: ${method}`,
      { method, ...details }
    );
  }

  static internalError(message: string, details?: any): SSHMCPServerError {
    return this.createError(
      ErrorCode.INTERNAL_ERROR,
      `Internal error: ${message}`,
      details
    );
  }

  static notImplemented(feature: string): SSHMCPServerError {
    return this.createError(
      ErrorCode.NOT_IMPLEMENTED,
      `Feature not implemented: ${feature}`,
      { feature }
    );
  }
}

// Error handler
export class ErrorHandler {
  static handleError(error: SSHMCPServerError): void {
    // Log the error
    console.error(`[${error.code}] ${error.message}`, error.details);
    
    // You can add additional error handling logic here
    // such as sending to monitoring service, etc.
  }
} 