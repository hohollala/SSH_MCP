/**
 * Logging configuration for SSH MCP Server
 */

import winston from 'winston';
import config from './config.js';

// Custom format for timestamps
const timestampFormat = winston.format.timestamp({
  format: 'YYYY-MM-DD HH:mm:ss'
});

// Custom format for log messages
const logFormat = winston.format.printf(({ timestamp, level, message, ...meta }) => {
  let logMessage = `${timestamp} - ${level.toUpperCase()} - ${message}`;
  
  if (Object.keys(meta).length > 0) {
    logMessage += ` - ${JSON.stringify(meta)}`;
  }
  
  return logMessage;
});

// Create logger instance
const logger = winston.createLogger({
  level: config.logLevel.toLowerCase(),
  format: winston.format.combine(
    timestampFormat,
    logFormat
  ),
  transports: [
    // Console transport
    new winston.transports.Console({
      format: winston.format.combine(
        winston.format.colorize(),
        timestampFormat,
        logFormat
      )
    })
  ]
});

// Add file transport if log file is specified
if (config.logFile) {
  logger.add(new winston.transports.File({
    filename: config.logFile,
    format: winston.format.combine(
      timestampFormat,
      logFormat
    )
  }));
}

// Create child loggers for different modules
export const createLogger = (module: string) => {
  return logger.child({ module });
};

// Export default logger
export { logger };

// Log uncaught exceptions
process.on('uncaughtException', (error) => {
  logger.error('Uncaught Exception:', error);
  process.exit(1);
});

// Log unhandled promise rejections
process.on('unhandledRejection', (reason, promise) => {
  logger.error('Unhandled Rejection at:', promise, 'reason:', reason);
  process.exit(1);
});