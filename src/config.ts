/**
 * Configuration module for SSH MCP Server
 */

import dotenv from 'dotenv';

// Load environment variables
dotenv.config();

export interface ServerConfig {
  // Server configuration
  debug: boolean;
  maxConnections: number;
  timeout: number;
  logLevel: string;
  
  // MCP protocol configuration
  protocolVersion: string;
  serverName: string;
  serverVersion: string;
  
  // Connection configuration
  connectionTimeout: number;
  commandTimeout: number;
  reconnectAttempts: number;
  reconnectDelay: number;
  
  // Security configuration
  allowPasswordAuth: boolean;
  allowAgentAuth: boolean;
  allowKeyAuth: boolean;
  
  // Logging configuration
  logFile?: string;
  logFormat: string;
}

class ConfigManager {
  private config: ServerConfig;

  constructor() {
    this.config = this.loadConfig();
  }

  private loadConfig(): ServerConfig {
    return {
      // Server configuration
      debug: this.getBoolEnv('SSH_MCP_DEBUG', false),
      maxConnections: this.getIntEnv('SSH_MCP_MAX_CONNECTIONS', 10),
      timeout: this.getIntEnv('SSH_MCP_TIMEOUT', 30),
      logLevel: this.getEnv('SSH_MCP_LOG_LEVEL', 'INFO'),
      
      // MCP protocol configuration
      protocolVersion: this.getEnv('SSH_MCP_PROTOCOL_VERSION', '2024-11-05'),
      serverName: this.getEnv('SSH_MCP_SERVER_NAME', 'ssh-mcp-server'),
      serverVersion: this.getEnv('SSH_MCP_SERVER_VERSION', '0.1.0'),
      
      // Connection configuration
      connectionTimeout: this.getIntEnv('SSH_MCP_CONNECTION_TIMEOUT', 30),
      commandTimeout: this.getIntEnv('SSH_MCP_COMMAND_TIMEOUT', 60),
      reconnectAttempts: this.getIntEnv('SSH_MCP_RECONNECT_ATTEMPTS', 3),
      reconnectDelay: this.getIntEnv('SSH_MCP_RECONNECT_DELAY', 5),
      
      // Security configuration
      allowPasswordAuth: this.getBoolEnv('SSH_MCP_ALLOW_PASSWORD_AUTH', true),
      allowAgentAuth: this.getBoolEnv('SSH_MCP_ALLOW_AGENT_AUTH', true),
      allowKeyAuth: this.getBoolEnv('SSH_MCP_ALLOW_KEY_AUTH', true),
      
      // Logging configuration
      logFile: this.getEnv('SSH_MCP_LOG_FILE', ''),
      logFormat: this.getEnv('SSH_MCP_LOG_FORMAT', '%timestamp% - %name% - %level% - %message%')
    };
  }

  private getEnv(key: string, defaultValue: string): string {
    return process.env[key] || defaultValue;
  }

  private getIntEnv(key: string, defaultValue: number): number {
    const value = process.env[key];
    if (value === undefined) return defaultValue;
    
    const parsed = parseInt(value, 10);
    return isNaN(parsed) ? defaultValue : parsed;
  }

  private getBoolEnv(key: string, defaultValue: boolean): boolean {
    const value = process.env[key]?.toLowerCase();
    if (value === undefined) return defaultValue;
    
    if (value === 'true' || value === '1' || value === 'yes' || value === 'on') {
      return true;
    }
    if (value === 'false' || value === '0' || value === 'no' || value === 'off') {
      return false;
    }
    return defaultValue;
  }

  getConfig(): ServerConfig {
    return { ...this.config };
  }

  reload(): void {
    this.config = this.loadConfig();
  }
}

const configManager = new ConfigManager();
export default configManager.getConfig();