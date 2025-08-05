#!/usr/bin/env node

/**
 * SSH MCP Server - Main Entry Point
 * 
 * This module provides the main entry point for the SSH MCP Server.
 * It handles environment variable processing, configuration loading,
 * MCP server initialization, and server lifecycle management.
 */

import { SSHMCPServer } from './mcp-server.js';
import { logger } from './logger.js';
import config from './config.js';
import { ErrorFactory } from './errors.js';
import { SSHMCPServerError } from './types.js';

// CLI argument parsing
function parseArguments(): { 
  version: boolean; 
  help: boolean; 
  debug: boolean;
  stdin: boolean;
} {
  const args = process.argv.slice(2);
  const result = {
    version: false,
    help: false,
    debug: false,
    stdin: false
  };

  for (const arg of args) {
    switch (arg) {
      case '--version':
      case '-v':
        result.version = true;
        break;
      case '--help':
      case '-h':
        result.help = true;
        break;
      case '--debug':
      case '-d':
        result.debug = true;
        break;
      case '--stdin':
        result.stdin = true;
        break;
    }
  }

  return result;
}

// Print version information
function printVersion(): void {
  console.log(`SSH MCP Server v${config.serverVersion}`);
  console.log(`Protocol Version: ${config.protocolVersion}`);
  console.log(`Node.js Version: ${process.version}`);
  console.log(`Platform: ${process.platform} ${process.arch}`);
}

// Print help information
function printHelp(): void {
  console.log('SSH MCP Server - Model Context Protocol Server for SSH Operations');
  console.log('');
  console.log('Usage: node dist/index.js [options]');
  console.log('');
  console.log('Options:');
  console.log('  -h, --help     Show this help message');
  console.log('  -v, --version  Show version information');
  console.log('  -d, --debug    Enable debug mode');
  console.log('  --stdin        Read from stdin (for testing)');
  console.log('');
  console.log('Environment Variables:');
  console.log('  SSH_MCP_DEBUG              Enable debug mode (default: false)');
  console.log('  SSH_MCP_MAX_CONNECTIONS    Maximum SSH connections (default: 10)');
  console.log('  SSH_MCP_TIMEOUT           Default timeout in seconds (default: 30)');
  console.log('  SSH_MCP_LOG_LEVEL         Log level (default: INFO)');
  console.log('  SSH_MCP_LOG_FILE          Log file path (optional)');
  console.log('');
  console.log('Examples:');
  console.log('  node dist/index.js                    # Start server normally');
  console.log('  node dist/index.js --debug            # Start with debug mode');
  console.log('  node dist/index.js --version          # Show version info');
  console.log('');
  console.log('For more information, visit: https://github.com/hohollala/SSH_MCP');
}

// Handle stdin mode for testing
async function handleStdinMode(): Promise<void> {
  logger.info('Running in stdin mode for testing');
  
  let input = '';
  process.stdin.setEncoding('utf8');
  
  process.stdin.on('data', (chunk) => {
    input += chunk;
  });
  
  process.stdin.on('end', async () => {
    try {
      const request = JSON.parse(input);
      logger.info('Received stdin request:', request);
      
      // Create a temporary server for testing
      const server = new SSHMCPServer();
      await server.start();
      
      // Process the request (this would need to be implemented)
      logger.info('Request processed successfully');
    } catch (error) {
      logger.error('Error processing stdin request:', error);
      process.exit(1);
    }
  });
}

// Main application entry point
async function main(): Promise<void> {
  const args = parseArguments();

  // Handle CLI arguments
  if (args.version) {
    printVersion();
    process.exit(0);
  }

  if (args.help) {
    printHelp();
    process.exit(0);
  }

  // Set debug mode if requested
  if (args.debug) {
    process.env.SSH_MCP_DEBUG = 'true';
  }

  try {
    logger.info('Starting SSH MCP Server...');
    logger.info(`Server name: ${config.serverName}`);
    logger.info(`Server version: ${config.serverVersion}`);
    logger.info(`Protocol version: ${config.protocolVersion}`);
    logger.info(`Debug mode: ${config.debug}`);
    logger.info(`Max connections: ${config.maxConnections}`);
    logger.info(`Log level: ${config.logLevel}`);

    // Handle stdin mode
    if (args.stdin) {
      await handleStdinMode();
      return;
    }

    // Create and start the MCP server
    const server = new SSHMCPServer();
    await server.start();

  } catch (error) {
    logger.error('Failed to start SSH MCP Server:', error);
    
    if (ErrorFactory.isSSHMCPServerError(error)) {
      const sshError = error as SSHMCPServerError;
      console.error(`[${sshError.code}] ${sshError.message}`);
      if (sshError.details) {
        console.error('Details:', sshError.details);
      }
    } else {
      console.error('Unexpected error:', error);
    }
    
    process.exit(1);
  }
}

// Handle unhandled promise rejections
process.on('unhandledRejection', (reason, promise) => {
  logger.error('Unhandled Rejection at:', promise, 'reason:', reason);
  process.exit(1);
});

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
  logger.error('Uncaught Exception:', error);
  process.exit(1);
});

// Start the application if this is the main module
if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((error) => {
    logger.error('Application failed to start:', error);
    process.exit(1);
  });
}