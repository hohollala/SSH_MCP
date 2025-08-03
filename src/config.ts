/**
 * Configuration module for SSH MCP Server
 */

import dotenv from 'dotenv';

// Load environment variables
dotenv.config();

export interface ServerConfig {
  debug: boolean;
  defaultTimeout: number;
  maxConnections: number;
  defaultSSHPort: number;
  connectionRetryAttempts: number;
  connectionRetryDelay: number;
  logLevel: string;
}

export const config: ServerConfig = {
  debug: process.env.SSH_MCP_DEBUG?.toLowerCase() === 'true',
  defaultTimeout: parseInt(process.env.SSH_MCP_TIMEOUT || '30', 10),
  maxConnections: parseInt(process.env.SSH_MCP_MAX_CONNECTIONS || '10', 10),
  defaultSSHPort: 22,
  connectionRetryAttempts: 3,
  connectionRetryDelay: 1000, // milliseconds
  logLevel: process.env.SSH_MCP_LOG_LEVEL || 'info',
};

export default config;