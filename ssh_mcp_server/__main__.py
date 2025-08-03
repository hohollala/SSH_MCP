#!/usr/bin/env python3
"""
SSH MCP Server - Main Entry Point

This module provides the main entry point for the SSH MCP Server.
It handles environment variable processing, configuration loading,
MCP server initialization, and server lifecycle management.
"""

import asyncio
import json
import logging
import os
import signal
import sys
from typing import Dict, Any, Optional
from pathlib import Path

from .server import MCPServer
from .errors import get_logger, MCPLogger


class ServerConfig:
    """Configuration class for SSH MCP Server."""
    
    def __init__(self):
        """Initialize configuration from environment variables."""
        # Server configuration
        self.debug = self._get_bool_env("SSH_MCP_DEBUG", False)
        self.max_connections = self._get_int_env("SSH_MCP_MAX_CONNECTIONS", 10)
        self.timeout = self._get_int_env("SSH_MCP_TIMEOUT", 30)
        self.log_level = self._get_env("SSH_MCP_LOG_LEVEL", "INFO")
        
        # MCP protocol configuration
        self.protocol_version = self._get_env("SSH_MCP_PROTOCOL_VERSION", "2024-11-05")
        self.server_name = self._get_env("SSH_MCP_SERVER_NAME", "ssh-mcp-server")
        self.server_version = self._get_env("SSH_MCP_SERVER_VERSION", "0.1.0")
        
        # Connection configuration
        self.connection_timeout = self._get_int_env("SSH_MCP_CONNECTION_TIMEOUT", 30)
        self.command_timeout = self._get_int_env("SSH_MCP_COMMAND_TIMEOUT", 60)
        self.reconnect_attempts = self._get_int_env("SSH_MCP_RECONNECT_ATTEMPTS", 3)
        self.reconnect_delay = self._get_int_env("SSH_MCP_RECONNECT_DELAY", 5)
        
        # Security configuration
        self.allow_password_auth = self._get_bool_env("SSH_MCP_ALLOW_PASSWORD_AUTH", True)
        self.allow_agent_auth = self._get_bool_env("SSH_MCP_ALLOW_AGENT_AUTH", True)
        self.allow_key_auth = self._get_bool_env("SSH_MCP_ALLOW_KEY_AUTH", True)
        
        # Logging configuration
        self.log_file = self._get_env("SSH_MCP_LOG_FILE", None)
        self.log_format = self._get_env("SSH_MCP_LOG_FORMAT", 
                                       "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    def _get_env(self, key: str, default: str) -> str:
        """Get string environment variable."""
        return os.getenv(key, default)
    
    def _get_int_env(self, key: str, default: int) -> int:
        """Get integer environment variable."""
        try:
            return int(os.getenv(key, str(default)))
        except ValueError:
            return default
    
    def _get_bool_env(self, key: str, default: bool) -> bool:
        """Get boolean environment variable."""
        value = os.getenv(key, "").lower()
        if value in ("true", "1", "yes", "on"):
            return True
        elif value in ("false", "0", "no", "off"):
            return False
        return default
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "debug": self.debug,
            "max_connections": self.max_connections,
            "timeout": self.timeout,
            "log_level": self.log_level,
            "protocol_version": self.protocol_version,
            "server_name": self.server_name,
            "server_version": self.server_version,
            "connection_timeout": self.connection_timeout,
            "command_timeout": self.command_timeout,
            "reconnect_attempts": self.reconnect_attempts,
            "reconnect_delay": self.reconnect_delay,
            "allow_password_auth": self.allow_password_auth,
            "allow_agent_auth": self.allow_agent_auth,
            "allow_key_auth": self.allow_key_auth,
            "log_file": self.log_file,
            "log_format": self.log_format
        }


class MCPServerRunner:
    """Main runner class for SSH MCP Server."""
    
    def __init__(self, config: ServerConfig):
        """Initialize server runner.
        
        Args:
            config: Server configuration
        """
        self.config = config
        self.server: Optional[MCPServer] = None
        self.logger = self._setup_logging()
        self._shutdown_event = asyncio.Event()
        self._running = False
    
    def _setup_logging(self) -> MCPLogger:
        """Setup logging configuration."""
        # Configure root logger
        log_level = getattr(logging, self.config.log_level.upper(), logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(self.config.log_format)
        
        # Setup handlers
        handlers = []
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        handlers.append(console_handler)
        
        # File handler if specified
        if self.config.log_file:
            try:
                log_path = Path(self.config.log_file)
                log_path.parent.mkdir(parents=True, exist_ok=True)
                file_handler = logging.FileHandler(log_path)
                file_handler.setFormatter(formatter)
                handlers.append(file_handler)
            except Exception as e:
                print(f"Warning: Could not setup file logging: {e}", file=sys.stderr)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        
        # Remove existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Add new handlers
        for handler in handlers:
            root_logger.addHandler(handler)
        
        # Create MCP logger
        logger = get_logger(__name__ + ".MCPServerRunner", debug=self.config.debug)
        
        return logger
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            """Handle shutdown signals."""
            signal_name = signal.Signals(signum).name
            self.logger.info(f"Received {signal_name}, initiating graceful shutdown...")
            self._shutdown_event.set()
        
        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # On Unix systems, also handle SIGHUP
        if hasattr(signal, 'SIGHUP'):
            signal.signal(signal.SIGHUP, signal_handler)
    
    async def start(self) -> None:
        """Start the MCP server."""
        if self._running:
            self.logger.warning("Server is already running")
            return
        
        self.logger.info("Starting SSH MCP Server...")
        self.logger.info(f"Configuration: {json.dumps(self.config.to_dict(), indent=2)}")
        
        try:
            # Create and configure server
            self.server = MCPServer(
                max_connections=self.config.max_connections,
                debug=self.config.debug
            )
            
            # Start server
            await self.server.start()
            self._running = True
            
            self.logger.info("SSH MCP Server started successfully")
            self.logger.info(f"Server info: {self.server}")
            
            # Log server capabilities
            stats = await self.server.get_server_stats()
            self.logger.info(f"Server capabilities: {stats['server']['tools_registered']} tools registered")
            
        except Exception as e:
            self.logger.error(f"Failed to start server: {e}", exception=e)
            raise
    
    async def stop(self) -> None:
        """Stop the MCP server."""
        if not self._running:
            self.logger.warning("Server is not running")
            return
        
        self.logger.info("Stopping SSH MCP Server...")
        
        try:
            if self.server:
                # Get final stats
                stats = await self.server.get_server_stats()
                self.logger.info(f"Final server stats: {stats}")
                
                # Stop server
                await self.server.stop()
                self.server = None
            
            self._running = False
            self.logger.info("SSH MCP Server stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error during server shutdown: {e}", exception=e)
            raise
    
    async def run(self) -> None:
        """Run the MCP server with proper lifecycle management."""
        # Setup signal handlers
        self._setup_signal_handlers()
        
        try:
            # Start server
            await self.start()
            
            # Run main loop
            await self._main_loop()
            
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
        except Exception as e:
            self.logger.error(f"Unexpected error in main loop: {e}", exception=e)
            raise
        finally:
            # Ensure cleanup
            await self.stop()
    
    async def _main_loop(self) -> None:
        """Main server loop."""
        self.logger.info("Entering main server loop...")
        
        try:
            # Wait for shutdown signal
            await self._shutdown_event.wait()
            
        except asyncio.CancelledError:
            self.logger.info("Main loop cancelled")
        except Exception as e:
            self.logger.error(f"Error in main loop: {e}", exception=e)
            raise
    
    async def handle_stdio(self) -> None:
        """Handle MCP communication over stdio.
        
        This method implements the MCP stdio transport protocol
        for communication with MCP clients.
        """
        self.logger.info("Starting MCP stdio communication...")
        
        try:
            # Read from stdin and write to stdout
            reader = asyncio.StreamReader()
            protocol = asyncio.StreamReaderProtocol(reader)
            await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)
            
            while self._running and not self._shutdown_event.is_set():
                try:
                    # Read line from stdin
                    line = await reader.readline()
                    if not line:
                        # EOF reached
                        break
                    
                    # Decode and parse JSON
                    try:
                        request_data = json.loads(line.decode('utf-8').strip())
                    except json.JSONDecodeError as e:
                        self.logger.error(f"Invalid JSON received: {e}")
                        continue
                    
                    # Handle request
                    if self.server:
                        response = await self.server.handle_request(request_data)
                        
                        # Write response to stdout
                        response_json = json.dumps(response)
                        sys.stdout.write(response_json + '\n')
                        sys.stdout.flush()
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"Error handling stdio communication: {e}", exception=e)
        
        except Exception as e:
            self.logger.error(f"Error in stdio handler: {e}", exception=e)
        finally:
            self.logger.info("MCP stdio communication ended")


def load_config_from_file(config_path: str) -> Dict[str, Any]:
    """Load configuration from JSON file.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Configuration dictionary
    """
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: Configuration file not found: {config_path}", file=sys.stderr)
        return {}
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in configuration file: {e}", file=sys.stderr)
        return {}
    except Exception as e:
        print(f"Error: Could not load configuration file: {e}", file=sys.stderr)
        return {}


def print_usage():
    """Print usage information."""
    print("SSH MCP Server - Model Context Protocol server for SSH operations")
    print()
    print("Usage:")
    print("  python -m ssh_mcp_server [options]")
    print()
    print("Options:")
    print("  --help, -h          Show this help message")
    print("  --version, -v       Show version information")
    print("  --config FILE       Load configuration from JSON file")
    print("  --stdio             Run in stdio mode (default)")
    print("  --debug             Enable debug mode")
    print()
    print("Environment Variables:")
    print("  SSH_MCP_DEBUG                Enable debug mode (true/false)")
    print("  SSH_MCP_MAX_CONNECTIONS      Maximum SSH connections (default: 10)")
    print("  SSH_MCP_TIMEOUT              Default timeout in seconds (default: 30)")
    print("  SSH_MCP_LOG_LEVEL            Log level (DEBUG/INFO/WARNING/ERROR)")
    print("  SSH_MCP_LOG_FILE             Log file path (optional)")
    print("  SSH_MCP_PROTOCOL_VERSION     MCP protocol version")
    print("  SSH_MCP_CONNECTION_TIMEOUT   SSH connection timeout")
    print("  SSH_MCP_COMMAND_TIMEOUT      Command execution timeout")
    print("  SSH_MCP_ALLOW_PASSWORD_AUTH  Allow password authentication")
    print("  SSH_MCP_ALLOW_AGENT_AUTH     Allow SSH agent authentication")
    print("  SSH_MCP_ALLOW_KEY_AUTH       Allow SSH key authentication")
    print()
    print("Examples:")
    print("  python -m ssh_mcp_server")
    print("  python -m ssh_mcp_server --debug")
    print("  python -m ssh_mcp_server --config config.json")
    print("  SSH_MCP_DEBUG=true python -m ssh_mcp_server")


def print_version():
    """Print version information."""
    from . import __version__
    print(f"SSH MCP Server version {__version__}")


async def main():
    """Main entry point for SSH MCP Server."""
    # Parse command line arguments
    args = sys.argv[1:]
    config_file = None
    stdio_mode = True
    debug_override = None
    
    i = 0
    while i < len(args):
        arg = args[i]
        
        if arg in ("--help", "-h"):
            print_usage()
            sys.exit(0)
        elif arg in ("--version", "-v"):
            print_version()
            sys.exit(0)
        elif arg == "--config":
            if i + 1 < len(args):
                config_file = args[i + 1]
                i += 1
            else:
                print("Error: --config requires a file path", file=sys.stderr)
                sys.exit(1)
        elif arg == "--stdio":
            stdio_mode = True
        elif arg == "--debug":
            debug_override = True
        else:
            print(f"Error: Unknown argument: {arg}", file=sys.stderr)
            print_usage()
            sys.exit(1)
        
        i += 1
    
    try:
        # Load configuration
        config = ServerConfig()
        
        # Load from config file if specified
        if config_file:
            file_config = load_config_from_file(config_file)
            # Apply file configuration to environment
            for key, value in file_config.items():
                env_key = f"SSH_MCP_{key.upper()}"
                if env_key not in os.environ:
                    os.environ[env_key] = str(value)
            
            # Reload configuration with file values
            config = ServerConfig()
        
        # Apply debug override
        if debug_override is not None:
            config.debug = debug_override
        
        # Create and run server
        runner = MCPServerRunner(config)
        
        if stdio_mode:
            # Run in stdio mode for MCP communication
            await runner.start()
            try:
                await runner.handle_stdio()
            finally:
                await runner.stop()
        else:
            # Run in standalone mode
            await runner.run()
    
    except KeyboardInterrupt:
        print("\nShutdown requested by user", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        if config and config.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def cli_main():
    """CLI entry point for the ssh-mcp-server command."""
    asyncio.run(main())


if __name__ == "__main__":
    # Run the main function
    cli_main()