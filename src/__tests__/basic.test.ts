import { SSHMCPServer } from '../mcp-server.js';
import { SSHConnectionManager } from '../connection-manager.js';
import { SSHTools } from '../tools.js';
import config from '../config.js';

describe('SSH MCP Server', () => {
  let server: SSHMCPServer;

  beforeEach(() => {
    server = new SSHMCPServer();
  });

  afterEach(async () => {
    await server.stop();
  });

  test('should create server instance', () => {
    expect(server).toBeDefined();
  });

  test('should get server info', () => {
    const info = server.getServerInfo();
    expect(info.name).toBe(config.serverName);
    expect(info.version).toBe(config.serverVersion);
    expect(info.protocolVersion).toBe(config.protocolVersion);
  });

  test('should get connection stats', () => {
    const stats = server.getConnectionStats();
    expect(stats.total).toBe(0);
    expect(stats.connected).toBe(0);
    expect(stats.connections).toEqual([]);
  });

  test('should get all tools', () => {
    const tools = server.getAllTools();
    expect(tools).toBeDefined();
    expect(Array.isArray(tools)).toBe(true);
    expect(tools.length).toBeGreaterThan(0);
  });

  test('should have ssh_connect tool', () => {
    const tools = server.getAllTools();
    const connectTool = tools.find(tool => tool.name === 'ssh_connect');
    expect(connectTool).toBeDefined();
    expect(connectTool?.description).toContain('SSH connection');
  });

  test('should have ssh_execute_command tool', () => {
    const tools = server.getAllTools();
    const executeTool = tools.find(tool => tool.name === 'ssh_execute_command');
    expect(executeTool).toBeDefined();
    expect(executeTool?.description).toContain('Execute a command');
  });
});

describe('SSH Connection Manager', () => {
  let connectionManager: SSHConnectionManager;

  beforeEach(() => {
    connectionManager = new SSHConnectionManager();
  });

  test('should create connection manager instance', () => {
    expect(connectionManager).toBeDefined();
  });

  test('should list empty connections initially', () => {
    const connections = connectionManager.listConnections();
    expect(connections).toEqual([]);
  });
});

describe('SSH Tools', () => {
  let tools: SSHTools;
  let connectionManager: SSHConnectionManager;

  beforeEach(() => {
    connectionManager = new SSHConnectionManager();
    tools = new SSHTools(connectionManager);
  });

  test('should create tools instance', () => {
    expect(tools).toBeDefined();
  });

  test('should get all tools', () => {
    const allTools = tools.getAllTools();
    expect(allTools).toBeDefined();
    expect(Array.isArray(allTools)).toBe(true);
    expect(allTools.length).toBeGreaterThan(0);
  });

  test('should have required tool methods', () => {
    const allTools = tools.getAllTools();
    const toolNames = allTools.map(tool => tool.name);
    
    expect(toolNames).toContain('ssh_connect');
    expect(toolNames).toContain('ssh_execute_command');
    expect(toolNames).toContain('ssh_list_connections');
    expect(toolNames).toContain('ssh_disconnect');
    expect(toolNames).toContain('ssh_read_file');
    expect(toolNames).toContain('ssh_write_file');
    expect(toolNames).toContain('ssh_list_files');
  });
}); 