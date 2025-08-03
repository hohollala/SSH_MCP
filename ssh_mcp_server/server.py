"""MCP Server Core Implementation.

This module implements the core MCP (Model Context Protocol) server functionality
including JSON-RPC 2.0 message processing, tool registration and routing, and
request/response validation.
"""

import asyncio
import json
import logging
import sys
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass, asdict
from datetime import datetime

from .manager import SSHManager, SSHManagerError
from .tools import (
    get_all_tool_schemas, validate_tool_parameters, ToolResult, ToolError,
    format_connection_info, format_command_result
)
from .models import SSHConfig, CommandResult, ConnectionInfo
from .errors import (
    MCPError, MCPErrorCode, MCPException, MCPLogger, get_logger,
    generate_error_message, create_detailed_error_context
)


# Use the enhanced MCP logger
mcp_logger = get_logger(__name__)


@dataclass
class MCPRequest:
    """Represents an MCP request message."""
    jsonrpc: str
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[Union[str, int]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPRequest':
        """Create MCPRequest from dictionary."""
        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            method=data["method"],
            params=data.get("params"),
            id=data.get("id")
        )


@dataclass
class MCPResponse:
    """Represents an MCP response message."""
    jsonrpc: str = "2.0"
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[Union[str, int]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert MCPResponse to dictionary."""
        response = {"jsonrpc": self.jsonrpc}
        
        if self.id is not None:
            response["id"] = self.id
            
        if self.error is not None:
            response["error"] = self.error
        else:
            response["result"] = self.result
            
        return response


# MCPError and MCPErrorCodes moved to errors.py module


class MCPServer:
    """Core MCP server implementation.
    
    This class handles JSON-RPC 2.0 message processing, tool registration and routing,
    and request/response validation for the SSH MCP server.
    """

    def __init__(self, max_connections: int = 10, debug: bool = False):
        """Initialize MCP Server.
        
        Args:
            max_connections: Maximum number of SSH connections to maintain
            debug: Enable debug logging
        """
        self.max_connections = max_connections
        self.debug = debug
        
        # Initialize SSH manager
        self.ssh_manager = SSHManager(max_connections=max_connections)
        
        # Tool registry
        self.tools = self._register_tools()
        
        # Server state
        self._running = False
        self._request_count = 0
        self._start_time = datetime.now()
        
        # Setup enhanced logging
        self.logger = MCPLogger(__name__ + ".MCPServer", debug=debug)
        
        self.logger.info(f"MCP Server initialized with {len(self.tools)} tools")

    def _register_tools(self) -> Dict[str, Callable]:
        """Register all available MCP tools.
        
        Returns:
            Dictionary mapping tool names to their handler functions
        """
        tools = {
            "ssh_connect": self._handle_ssh_connect,
            "ssh_execute": self._handle_ssh_execute,
            "ssh_read_file": self._handle_ssh_read_file,
            "ssh_write_file": self._handle_ssh_write_file,
            "ssh_list_directory": self._handle_ssh_list_directory,
            "ssh_disconnect": self._handle_ssh_disconnect,
            "ssh_list_connections": self._handle_ssh_list_connections,
        }
        
        # Validate that all registered tools have schemas
        tool_schemas = get_all_tool_schemas()
        for tool_name in tools:
            if tool_name not in tool_schemas:
                raise ValueError(f"Tool '{tool_name}' is missing schema definition")
        
        return tools

    async def start(self) -> None:
        """Start the MCP server."""
        if self._running:
            self.logger.warning("MCP Server is already running")
            return
        
        self.logger.info("Starting MCP Server")
        self._running = True
        
        # Start SSH manager
        await self.ssh_manager.start()
        
        self.logger.info("MCP Server started successfully")

    async def stop(self) -> None:
        """Stop the MCP server."""
        if not self._running:
            self.logger.warning("MCP Server is not running")
            return
        
        self.logger.info("Stopping MCP Server")
        self._running = False
        
        # Stop SSH manager
        await self.ssh_manager.stop()
        
        self.logger.info("MCP Server stopped")

    async def handle_request(self, request_data: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Handle an incoming MCP request.
        
        Args:
            request_data: JSON string or dictionary containing the request
            
        Returns:
            Dictionary containing the response
        """
        self._request_count += 1
        request_id = None
        
        try:
            # Parse request if it's a string
            if isinstance(request_data, str):
                try:
                    request_dict = json.loads(request_data)
                except json.JSONDecodeError as e:
                    error = MCPError.parse_error(str(e))
                    self.logger.error("JSON parse error", exception=e)
                    return self._create_error_response(None, error)
            else:
                request_dict = request_data
            
            # Validate and create request object
            try:
                request = MCPRequest.from_dict(request_dict)
                request_id = request.id
            except (KeyError, TypeError) as e:
                error = MCPError.invalid_request(str(e))
                self.logger.error("Invalid request format", exception=e)
                return self._create_error_response(request_id, error)
            
            self.logger.log_mcp_request(request_id, request.method, request.params)
            
            # Handle different request types
            if request.method == "initialize":
                return await self._handle_initialize(request)
            elif request.method == "tools/list":
                return await self._handle_tools_list(request)
            elif request.method == "tools/call":
                return await self._handle_tools_call(request)
            else:
                error = MCPError.method_not_found(request.method)
                self.logger.warning(f"Method not found: {request.method}")
                return self._create_error_response(request_id, error)
        
        except Exception as e:
            error_context = create_detailed_error_context(e, "handle_request", request_id)
            error = MCPError.internal_error(str(e) if self.debug else None)
            self.logger.error("Unexpected error handling request", exception=e, **error_context)
            return self._create_error_response(request_id, error)

    async def _handle_initialize(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle MCP initialize request.
        
        Args:
            request: The initialize request
            
        Returns:
            Initialize response
        """
        self.logger.info("Handling initialize request")
        
        result = {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "ssh-mcp-server",
                "version": "0.1.0"
            }
        }
        
        return self._create_success_response(request.id, result)

    async def _handle_tools_list(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle tools/list request.
        
        Args:
            request: The tools list request
            
        Returns:
            List of available tools
        """
        self.logger.debug("Handling tools/list request")
        
        tool_schemas = get_all_tool_schemas()
        tools = []
        
        for tool_name, schema in tool_schemas.items():
            tools.append(schema.to_mcp_schema())
        
        result = {"tools": tools}
        return self._create_success_response(request.id, result)

    async def _handle_tools_call(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle tools/call request.
        
        Args:
            request: The tool call request
            
        Returns:
            Tool execution result
        """
        if not request.params:
            error = MCPError.invalid_params("Missing parameters for tools/call")
            return self._create_error_response(request.id, error)
        
        tool_name = request.params.get("name")
        if not tool_name:
            error = MCPError.invalid_params("Missing tool name", "name")
            return self._create_error_response(request.id, error)
        
        tool_arguments = request.params.get("arguments", {})
        
        self.logger.debug(f"Handling tools/call request for tool: {tool_name}", tool=tool_name)
        
        # Check if tool exists
        if tool_name not in self.tools:
            error = MCPError.method_not_found(tool_name)
            return self._create_error_response(request.id, error)
        
        try:
            # Validate tool parameters
            validated_params = validate_tool_parameters(tool_name, tool_arguments)
            
            # Execute tool
            tool_handler = self.tools[tool_name]
            result = await tool_handler(validated_params)
            
            # Format result
            if isinstance(result, ToolResult):
                tool_result = result.to_dict()
            else:
                tool_result = {"success": True, "data": result}
            
            return self._create_success_response(request.id, {"content": [{"type": "text", "text": json.dumps(tool_result, indent=2)}]})
        
        except ToolError as e:
            error_data = {"tool": tool_name, "details": e.details}
            error = MCPError(code=MCPErrorCode.TOOL_ERROR, message=f"Tool error: {e}", data=error_data)
            self.logger.error(f"Tool error in {tool_name}", exception=e, tool=tool_name)
            return self._create_error_response(request.id, error)
        
        except Exception as e:
            error_context = create_detailed_error_context(e, f"tool_{tool_name}", tool=tool_name)
            error = MCPError.internal_error(str(e) if self.debug else None)
            self.logger.error(f"Unexpected error in tool {tool_name}", exception=e, **error_context)
            return self._create_error_response(request.id, error)

    # Tool handlers
    async def _handle_ssh_connect(self, params: Dict[str, Any]) -> ToolResult:
        """Handle ssh_connect tool."""
        try:
            # Create SSH config from parameters
            config = SSHConfig(
                hostname=params["hostname"],
                username=params["username"],
                port=params.get("port", 22),
                auth_method=params.get("auth_method", "agent"),
                key_path=params.get("key_path"),
                password=params.get("password"),
                timeout=params.get("timeout", 30)
            )
            
            # Create connection
            connection_id = await self.ssh_manager.create_connection(config)
            
            # Get connection info
            connections = await self.ssh_manager.list_connections()
            connection_info = next(
                (conn for conn in connections if conn.connection_id == connection_id),
                None
            )
            
            if connection_info:
                result_data = format_connection_info(connection_info)
            else:
                result_data = {"connection_id": connection_id, "status": "connected"}
            
            return ToolResult.success(result_data, {"tool": "ssh_connect"})
        
        except SSHManagerError as e:
            context = {"hostname": params["hostname"], "username": params["username"]}
            error_msg = generate_error_message("connection", context, user_friendly=True)
            raise ToolError(error_msg, details={"hostname": params["hostname"], "original_error": str(e)})

    async def _handle_ssh_execute(self, params: Dict[str, Any]) -> ToolResult:
        """Handle ssh_execute tool."""
        try:
            connection_id = params["connection_id"]
            command = params["command"]
            timeout = params.get("timeout", 60)
            
            # Execute command
            result = await self.ssh_manager.execute_command(connection_id, command, timeout)
            
            # Format result
            result_data = format_command_result(result)
            
            return ToolResult.success(result_data, {"tool": "ssh_execute"})
        
        except SSHManagerError as e:
            context = {"command": params["command"], "details": str(e)}
            error_msg = generate_error_message("command", context, user_friendly=True)
            raise ToolError(error_msg, details={"connection_id": params["connection_id"], "command": params["command"]})

    async def _handle_ssh_read_file(self, params: Dict[str, Any]) -> ToolResult:
        """Handle ssh_read_file tool."""
        try:
            connection_id = params["connection_id"]
            file_path = params["file_path"]
            encoding = params.get("encoding", "utf-8")
            
            # Read file
            content = await self.ssh_manager.read_file(connection_id, file_path, encoding)
            
            # Format result
            result_data = {
                "file_path": file_path,
                "content": content,
                "encoding": encoding,
                "size": len(content),
                "lines": content.count('\n') + 1 if content else 0
            }
            
            return ToolResult.success(result_data, {"tool": "ssh_read_file"})
        
        except SSHManagerError as e:
            context = {"file_path": params["file_path"], "operation": "read", "details": str(e)}
            error_msg = generate_error_message("file", context, user_friendly=True)
            raise ToolError(error_msg, details={"connection_id": params["connection_id"], "file_path": params["file_path"]})

    async def _handle_ssh_write_file(self, params: Dict[str, Any]) -> ToolResult:
        """Handle ssh_write_file tool."""
        try:
            connection_id = params["connection_id"]
            file_path = params["file_path"]
            content = params["content"]
            encoding = params.get("encoding", "utf-8")
            create_dirs = params.get("create_dirs", False)
            
            # Write file
            await self.ssh_manager.write_file(connection_id, file_path, content, encoding, create_dirs)
            
            # Format result
            result_data = {
                "file_path": file_path,
                "bytes_written": len(content.encode(encoding)),
                "encoding": encoding,
                "create_dirs": create_dirs,
                "status": "success"
            }
            
            return ToolResult.success(result_data, {"tool": "ssh_write_file"})
        
        except SSHManagerError as e:
            context = {"file_path": params["file_path"], "operation": "write", "details": str(e)}
            error_msg = generate_error_message("file", context, user_friendly=True)
            raise ToolError(error_msg, details={"connection_id": params["connection_id"], "file_path": params["file_path"]})

    async def _handle_ssh_list_directory(self, params: Dict[str, Any]) -> ToolResult:
        """Handle ssh_list_directory tool."""
        try:
            connection_id = params["connection_id"]
            directory_path = params["directory_path"]
            show_hidden = params.get("show_hidden", False)
            detailed = params.get("detailed", False)
            
            # List directory
            entries = await self.ssh_manager.list_directory(connection_id, directory_path, show_hidden, detailed)
            
            # Format result
            result_data = {
                "directory_path": directory_path,
                "entries": entries,
                "total_entries": len(entries),
                "show_hidden": show_hidden,
                "detailed": detailed
            }
            
            return ToolResult.success(result_data, {"tool": "ssh_list_directory"})
        
        except SSHManagerError as e:
            context = {"file_path": params["directory_path"], "operation": "list", "details": str(e)}
            error_msg = generate_error_message("file", context, user_friendly=True)
            raise ToolError(error_msg, details={"connection_id": params["connection_id"], "directory_path": params["directory_path"]})

    async def _handle_ssh_disconnect(self, params: Dict[str, Any]) -> ToolResult:
        """Handle ssh_disconnect tool."""
        try:
            connection_id = params["connection_id"]
            
            # Disconnect connection
            success = await self.ssh_manager.disconnect_connection(connection_id)
            
            if success:
                result_data = {"connection_id": connection_id, "status": "disconnected"}
                return ToolResult.success(result_data, {"tool": "ssh_disconnect"})
            else:
                raise ToolError(f"Connection not found: {connection_id}")
        
        except SSHManagerError as e:
            raise ToolError(f"Disconnect failed: {e}", details={"connection_id": params["connection_id"]})

    async def _handle_ssh_list_connections(self, params: Dict[str, Any]) -> ToolResult:
        """Handle ssh_list_connections tool."""
        try:
            # Get all connections
            connections = await self.ssh_manager.list_connections()
            
            # Format connections
            result_data = {
                "connections": [format_connection_info(conn) for conn in connections],
                "total": len(connections)
            }
            
            return ToolResult.success(result_data, {"tool": "ssh_list_connections"})
        
        except SSHManagerError as e:
            raise ToolError(f"Failed to list connections: {e}")

    def _create_success_response(self, request_id: Optional[Union[str, int]], result: Any) -> Dict[str, Any]:
        """Create a successful MCP response.
        
        Args:
            request_id: The request ID
            result: The result data
            
        Returns:
            Response dictionary
        """
        response = MCPResponse(result=result, id=request_id)
        return response.to_dict()

    def _create_error_response(self, request_id: Optional[Union[str, int]], 
                             error: MCPError) -> Dict[str, Any]:
        """Create an error MCP response.
        
        Args:
            request_id: The request ID
            error: MCPError instance
            
        Returns:
            Error response dictionary
        """
        response = MCPResponse(error=error.to_dict(), id=request_id)
        return response.to_dict()

    async def get_server_stats(self) -> Dict[str, Any]:
        """Get server statistics.
        
        Returns:
            Dictionary with server statistics
        """
        manager_stats = await self.ssh_manager.get_manager_stats()
        
        uptime = datetime.now() - self._start_time
        
        return {
            "server": {
                "running": self._running,
                "uptime": str(uptime),
                "start_time": self._start_time.isoformat(),
                "request_count": self._request_count,
                "debug": self.debug,
                "tools_registered": len(self.tools)
            },
            "ssh_manager": manager_stats
        }

    def __str__(self) -> str:
        """String representation of the MCP Server."""
        return f"MCPServer(running={self._running}, tools={len(self.tools)}, connections={len(self.ssh_manager)})"

    def __repr__(self) -> str:
        """Detailed string representation of the MCP Server."""
        return (f"MCPServer(running={self._running}, "
                f"tools={len(self.tools)}, "
                f"max_connections={self.max_connections}, "
                f"debug={self.debug}, "
                f"requests={self._request_count})")