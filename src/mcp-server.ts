import { createLogger } from './logger.js';
import config from './config.js';
import { SSHConnectionManager } from './connection-manager.js';
import { SSHTools } from './tools.js';
import { CommandInstaller } from './command-installer.js';
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';

export class SSHMCPServer {
  private connectionManager: SSHConnectionManager;
  private tools: SSHTools;
  private commandInstaller: CommandInstaller;
  private logger = createLogger('SSHMCPServer');
  private server: Server;

  constructor() {
    this.connectionManager = new SSHConnectionManager();
    this.tools = new SSHTools(this.connectionManager);
    this.commandInstaller = new CommandInstaller();
    
    // Create MCP server instance
    this.server = new Server({
      name: config.serverName,
      version: config.serverVersion,
    });
    
    this.setupHandlers();
  }

  private setupHandlers(): void {
    // Handle tool listing
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: this.getAllTools(),
      };
    });

    // Handle tool execution  
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;
      try {
        const result = await this.executeTool(name, args || {});
        return result;
      } catch (error) {
        throw new Error(error instanceof Error ? error.message : 'Tool execution failed');
      }
    });
  }

  async start(): Promise<void> {
    this.logger.info('Starting SSH MCP Server...');
    this.logger.info(`Server name: ${config.serverName}`);
    this.logger.info(`Server version: ${config.serverVersion}`);
    this.logger.info(`Protocol version: ${config.protocolVersion}`);
    this.logger.info(`Debug mode: ${config.debug}`);
    this.logger.info(`Max connections: ${config.maxConnections}`);

    try {
      // Install command documentation files if not already installed
      await this.installCommandDocumentation();
      
      // Create stdio transport
      const transport = new StdioServerTransport();
      
      // Connect server to transport
      await this.server.connect(transport);
      
      this.logger.info('SSH MCP Server started successfully with stdio transport');
      
    } catch (error) {
      this.logger.error('Failed to start SSH MCP Server:', error);
      throw error;
    }
  }


  async stop(): Promise<void> {
    this.logger.info('Stopping SSH MCP Server...');
    
    try {
      // Close MCP server
      if (this.server) {
        await this.server.close();
        this.logger.info('MCP server closed');
      }
      
      // Cleanup SSH connections
      await this.connectionManager.cleanup();
      
      this.logger.info('SSH MCP Server stopped successfully');
    } catch (error) {
      this.logger.error('Error stopping SSH MCP Server:', error);
      throw error;
    }
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
      }))
    };
  }

  // Get all available tools
  getAllTools() {
    return this.tools.getAllTools();
  }

  // Execute a tool
  async executeTool(name: string, args: any): Promise<any> {
    return this.tools.executeTool(name, args);
  }

  // Install command documentation files
  private async installCommandDocumentation(): Promise<void> {
    try {
      const isInstalled = await this.commandInstaller.isInstalled();
      
      if (!isInstalled) {
        this.logger.info('Installing SSH command documentation...');
        await this.commandInstaller.installCommands();
      } else {
        this.logger.debug('SSH command documentation already installed');
      }
    } catch (error) {
      this.logger.warn('Failed to install command documentation:', error);
      // Don't throw error to prevent server startup failure
    }
  }

  // Get command installation info
  async getCommandInstallationInfo() {
    return this.commandInstaller.getInstallationInfo();
  }
} 