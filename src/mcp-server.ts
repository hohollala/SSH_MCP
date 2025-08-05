import { createLogger } from './logger.js';
import config from './config.js';
import { SSHConnectionManager } from './connection-manager.js';
import { SSHTools } from './tools.js';

export class SSHMCPServer {
  private connectionManager: SSHConnectionManager;
  private tools: SSHTools;
  private logger = createLogger('SSHMCPServer');

  constructor() {
    this.connectionManager = new SSHConnectionManager();
    this.tools = new SSHTools(this.connectionManager);
  }

  async start(): Promise<void> {
    this.logger.info('Starting SSH MCP Server...');
    this.logger.info(`Server name: ${config.serverName}`);
    this.logger.info(`Server version: ${config.serverVersion}`);
    this.logger.info(`Protocol version: ${config.protocolVersion}`);
    this.logger.info(`Debug mode: ${config.debug}`);
    this.logger.info(`Max connections: ${config.maxConnections}`);

    try {
      this.logger.info('SSH MCP Server started successfully');
      
      // Keep the server running
      await this.waitForShutdown();
    } catch (error) {
      this.logger.error('Failed to start SSH MCP Server:', error);
      throw error;
    }
  }

  async stop(): Promise<void> {
    this.logger.info('Stopping SSH MCP Server...');
    
    try {
      // Cleanup SSH connections
      await this.connectionManager.cleanup();
      
      this.logger.info('SSH MCP Server stopped successfully');
    } catch (error) {
      this.logger.error('Error stopping SSH MCP Server:', error);
      throw error;
    }
  }

  private async waitForShutdown(): Promise<void> {
    return new Promise((resolve) => {
      const shutdown = async (signal: string) => {
        this.logger.info(`Received ${signal}, shutting down...`);
        try {
          await this.stop();
          resolve();
        } catch (error) {
          this.logger.error('Error during shutdown:', error);
          process.exit(1);
        }
      };

      process.on('SIGINT', () => shutdown('SIGINT'));
      process.on('SIGTERM', () => shutdown('SIGTERM'));
      
      // Handle uncaught exceptions
      process.on('uncaughtException', (error) => {
        this.logger.error('Uncaught exception:', error);
        shutdown('uncaughtException');
      });

      process.on('unhandledRejection', (reason, promise) => {
        this.logger.error('Unhandled rejection at:', promise, 'reason:', reason);
        shutdown('unhandledRejection');
      });
    });
  }

  // Get server info
  getServerInfo() {
    return {
      name: config.serverName,
      version: config.serverVersion,
      protocolVersion: config.protocolVersion,
      debug: config.debug,
      maxConnections: config.maxConnections,
    };
  }

  // Get connection stats
  getConnectionStats() {
    const connections = this.connectionManager.listConnections();
    return {
      total: connections.length,
      connected: connections.filter(conn => conn.isConnected).length,
      connections: connections.map(conn => ({
        id: conn.id,
        host: conn.host,
        port: conn.port,
        username: conn.username,
        isConnected: conn.isConnected,
        createdAt: conn.createdAt,
        lastUsed: conn.lastUsed,
      })),
    };
  }

  // Get all tools
  getAllTools() {
    return this.tools.getAllTools();
  }

  // Execute tool
  async executeTool(name: string, args: any): Promise<any> {
    return await this.tools.executeTool(name, args);
  }
} 