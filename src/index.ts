/**
 * Main entry point for SSH MCP Server
 */

import { logger } from './logger.js';
import config from './config.js';

async function main(): Promise<void> {
  try {
    logger.info('Starting SSH MCP Server...');
    logger.info(`Debug mode: ${config.debug}`);
    logger.info(`Max connections: ${config.maxConnections}`);
    logger.info(`Default timeout: ${config.defaultTimeout}s`);
    
    // TODO: Initialize and run MCP server (will be implemented in later tasks)
    logger.info('SSH MCP Server initialized successfully');
    
    // For now, just keep the server running
    logger.info('Server is ready to accept connections...');
    
    // This will be replaced with actual MCP server loop in later tasks
    await runServer();
    
  } catch (error) {
    logger.error('Failed to start SSH MCP Server:', error);
    process.exit(1);
  }
}

async function runServer(): Promise<void> {
  logger.info('Server loop started (placeholder implementation)');
  
  // Keep the server running until interrupted
  return new Promise((resolve, reject) => {
    process.on('SIGINT', () => {
      logger.info('Received shutdown signal, stopping server...');
      resolve();
    });
    
    process.on('SIGTERM', () => {
      logger.info('Received termination signal, stopping server...');
      resolve();
    });
    
    process.on('uncaughtException', (error) => {
      logger.error('Uncaught exception:', error);
      reject(error);
    });
    
    process.on('unhandledRejection', (reason, promise) => {
      logger.error('Unhandled rejection at:', promise, 'reason:', reason);
      reject(reason);
    });
  });
}

// Handle unhandled promise rejections
process.on('unhandledRejection', (reason, promise) => {
  logger.error('Unhandled Rejection at:', promise, 'reason:', reason);
  process.exit(1);
});

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((error) => {
    logger.error('Application failed to start:', error);
    process.exit(1);
  });
}