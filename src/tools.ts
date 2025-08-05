import { createLogger } from './logger.js';
import { SSHConnectionManager } from './connection-manager.js';
import { ErrorFactory } from './errors.js';
import { EnvParser } from './env-parser.js';
import { sshenvTemplate, gitignoreEntry } from './sshenv-template.js';
import { promises as fs } from 'fs';
import { join } from 'path';
import { 
  SSHConnection, 
  SSHAuthConfig, 
  SSHCommand, 
  SSHCommandResult,
  FileOperationResult,
  MCPTool 
} from './types.js';

export class SSHTools {
  private connectionManager: SSHConnectionManager;
  private envParser: EnvParser;
  private logger = createLogger('SSHTools');

  constructor(connectionManager: SSHConnectionManager) {
    this.connectionManager = connectionManager;
    this.envParser = new EnvParser();
    this.initializeEnvParser();
  }

  private async initializeEnvParser(): Promise<void> {
    try {
      await this.envParser.loadEnvFile();
    } catch (error) {
      // 환경 파일 로드 실패는 치명적이지 않음
      this.logger.debug('Environment file not loaded on startup');
    }
  }

  // SSH Connect Tool
  getSSHConnectTool(): MCPTool {
    return {
      name: 'ssh_connect',
      description: 'Establish SSH connection to a remote server',
      inputSchema: {
        type: 'object',
        properties: {
          host: {
            type: 'string',
            description: 'Hostname or IP address of the remote server'
          },
          port: {
            type: 'number',
            description: 'SSH port (default: 22)',
            default: 22
          },
          username: {
            type: 'string',
            description: 'Username for SSH authentication'
          },
          password: {
            type: 'string',
            description: 'Password for authentication (if using password auth)'
          },
          privateKey: {
            type: 'string',
            description: 'Private key for authentication (if using key auth)'
          },
          passphrase: {
            type: 'string',
            description: 'Passphrase for private key (if required)'
          },
          useAgent: {
            type: 'boolean',
            description: 'Use SSH agent for authentication',
            default: false
          }
        },
        required: ['host', 'username']
      }
    };
  }

  // SSH Execute Command Tool
  getSSHExecuteCommandTool(): MCPTool {
    return {
      name: 'ssh_execute_command',
      description: 'Execute a command on a remote server via SSH',
      inputSchema: {
        type: 'object',
        properties: {
          connectionId: {
            type: 'string',
            description: 'Connection ID from ssh_connect'
          },
          command: {
            type: 'string',
            description: 'Command to execute on the remote server'
          },
          cwd: {
            type: 'string',
            description: 'Working directory for the command'
          },
          timeout: {
            type: 'number',
            description: 'Command timeout in seconds',
            default: 60
          }
        },
        required: ['connectionId', 'command']
      }
    };
  }

  // SSH List Connections Tool
  getSSHListConnectionsTool(): MCPTool {
    return {
      name: 'ssh_list_connections',
      description: 'List all active SSH connections',
      inputSchema: {
        type: 'object',
        properties: {},
        required: []
      }
    };
  }

  // SSH Disconnect Tool
  getSSHDisconnectTool(): MCPTool {
    return {
      name: 'ssh_disconnect',
      description: 'Disconnect from a remote server',
      inputSchema: {
        type: 'object',
        properties: {
          connectionId: {
            type: 'string',
            description: 'Connection ID to disconnect'
          }
        },
        required: ['connectionId']
      }
    };
  }

  // SSH Read File Tool
  getSSHReadFileTool(): MCPTool {
    return {
      name: 'ssh_read_file',
      description: 'Read a file from a remote server',
      inputSchema: {
        type: 'object',
        properties: {
          connectionId: {
            type: 'string',
            description: 'Connection ID from ssh_connect'
          },
          path: {
            type: 'string',
            description: 'Path to the file on the remote server'
          },
          encoding: {
            type: 'string',
            description: 'File encoding (default: utf8)',
            default: 'utf8'
          }
        },
        required: ['connectionId', 'path']
      }
    };
  }

  // SSH Write File Tool
  getSSHWriteFileTool(): MCPTool {
    return {
      name: 'ssh_write_file',
      description: 'Write content to a file on a remote server',
      inputSchema: {
        type: 'object',
        properties: {
          connectionId: {
            type: 'string',
            description: 'Connection ID from ssh_connect'
          },
          path: {
            type: 'string',
            description: 'Path to the file on the remote server'
          },
          content: {
            type: 'string',
            description: 'Content to write to the file'
          },
          encoding: {
            type: 'string',
            description: 'File encoding (default: utf8)',
            default: 'utf8'
          }
        },
        required: ['connectionId', 'path', 'content']
      }
    };
  }

  // SSH List Files Tool
  getSSHListFilesTool(): MCPTool {
    return {
      name: 'ssh_list_files',
      description: 'List files in a directory on a remote server',
      inputSchema: {
        type: 'object',
        properties: {
          connectionId: {
            type: 'string',
            description: 'Connection ID from ssh_connect'
          },
          path: {
            type: 'string',
            description: 'Directory path to list',
            default: '.'
          }
        },
        required: ['connectionId']
      }
    };
  }

  // SSH Init Tool
  getSSHInitTool(): MCPTool {
    return {
      name: 'ssh_init',
      description: 'Initialize SSH MCP environment by creating .sshenv configuration file',
      inputSchema: {
        type: 'object',
        properties: {
          path: {
            type: 'string',
            description: 'Path where to create .sshenv file (default: current directory)',
            default: '.'
          },
          force: {
            type: 'boolean',
            description: 'Overwrite existing .sshenv file',
            default: false
          },
          addGitignore: {
            type: 'boolean',
            description: 'Add .sshenv entry to .gitignore',
            default: true
          }
        }
      }
    };
  }

  // Tool execution methods
  async executeSSHConnect(args: any): Promise<SSHConnection> {
    // 환경변수 치환
    const expandedArgs = this.envParser.expandObjectVariables(args);
    const { host, port = 22, username, password, privateKey, passphrase, useAgent = false } = expandedArgs;

    this.logger.debug('SSH Connect with expanded args:', { host, port, username, useAgent });

    const auth: SSHAuthConfig = {};
    if (password) auth.password = password;
    if (privateKey) auth.privateKey = privateKey;
    if (passphrase) auth.passphrase = passphrase;
    if (useAgent) auth.agent = true;

    this.logger.info(`Connecting to ${username}@${host}:${port}`);
    return await this.connectionManager.connect(host, port, username, auth);
  }

  async executeSSHExecuteCommand(args: any): Promise<SSHCommandResult> {
    const { connectionId, command, cwd, timeout = 60 } = args;

    const sshCommand: SSHCommand = {
      id: `cmd_${Date.now()}`,
      command,
      cwd,
      timeout
    };

    this.logger.info(`Executing command on ${connectionId}: ${command}`);
    return await this.connectionManager.executeCommand(connectionId, sshCommand);
  }

  async executeSSHListConnections(): Promise<SSHConnection[]> {
    this.logger.info('Listing SSH connections');
    return this.connectionManager.listConnections();
  }

  async executeSSHDisconnect(args: any): Promise<{ success: boolean }> {
    const { connectionId } = args;

    this.logger.info(`Disconnecting from ${connectionId}`);
    await this.connectionManager.disconnect(connectionId);
    return { success: true };
  }

  async executeSSHReadFile(args: any): Promise<FileOperationResult> {
    const { connectionId, path } = args;

    const command = `cat "${path}"`;
    const sshCommand: SSHCommand = {
      id: `read_${Date.now()}`,
      command,
      timeout: 30
    };

    this.logger.info(`Reading file on ${connectionId}: ${path}`);
    const result = await this.connectionManager.executeCommand(connectionId, sshCommand);

    if (result.exitCode !== 0) {
      throw ErrorFactory.fileNotFound(path);
    }

    return {
      id: sshCommand.id,
      success: true,
      content: result.stdout
    };
  }

  async executeSSHWriteFile(args: any): Promise<FileOperationResult> {
    const { connectionId, path, content } = args;

    // Escape content for shell
    const escapedContent = content.replace(/'/g, "'\"'\"'");
    const command = `cat > "${path}" << 'EOF'\n${escapedContent}\nEOF`;
    
    const sshCommand: SSHCommand = {
      id: `write_${Date.now()}`,
      command,
      timeout: 30
    };

    this.logger.info(`Writing file on ${connectionId}: ${path}`);
    const result = await this.connectionManager.executeCommand(connectionId, sshCommand);

    if (result.exitCode !== 0) {
      throw ErrorFactory.fileOperationFailed('write', path, { stderr: result.stderr });
    }

    return {
      id: sshCommand.id,
      success: true
    };
  }

  async executeSSHListFiles(args: any): Promise<FileOperationResult> {
    const { connectionId, path = '.' } = args;

    const command = `ls -la "${path}"`;
    const sshCommand: SSHCommand = {
      id: `list_${Date.now()}`,
      command,
      timeout: 30
    };

    this.logger.info(`Listing files on ${connectionId}: ${path}`);
    const result = await this.connectionManager.executeCommand(connectionId, sshCommand);

    if (result.exitCode !== 0) {
      throw ErrorFactory.fileOperationFailed('list', path, { stderr: result.stderr });
    }

    const files = result.stdout
      .split('\n')
      .filter(line => line.trim() && !line.startsWith('total'))
      .map(line => {
        const parts = line.split(/\s+/);
        return parts[parts.length - 1];
      })
      .filter((file): file is string => file !== undefined && file !== '.' && file !== '..');

    return {
      id: sshCommand.id,
      success: true,
      files
    };
  }

  // SSH Init implementation
  async executeSSHInit(args: any): Promise<{
    success: boolean;
    message: string;
    sshenvPath: string;
    gitignoreUpdated?: boolean;
  }> {
    const { path = '.', force = false, addGitignore = true } = args;
    
    const sshenvPath = join(path, '.sshenv');
    const gitignorePath = join(path, '.gitignore');
    
    this.logger.info(`Initializing SSH environment at: ${sshenvPath}`);
    
    try {
      // .sshenv 파일 존재 확인
      const sshenvExists = await this.fileExists(sshenvPath);
      
      if (sshenvExists && !force) {
        return {
          success: false,
          message: '.sshenv file already exists. Use "force: true" to overwrite.',
          sshenvPath
        };
      }
      
      // .sshenv 파일 생성
      await fs.writeFile(sshenvPath, sshenvTemplate, 'utf8');
      this.logger.info('Created .sshenv file');
      
      let gitignoreUpdated = false;
      
      // .gitignore 업데이트
      if (addGitignore) {
        gitignoreUpdated = await this.updateGitignore(gitignorePath);
      }
      
      // 파일 권한 설정 (Unix 시스템에서만)
      if (process.platform !== 'win32') {
        try {
          await fs.chmod(sshenvPath, 0o600);
          this.logger.info('Set .sshenv file permissions to 600');
        } catch (error) {
          this.logger.warn('Failed to set file permissions:', error);
        }
      }
      
      const message = sshenvExists ? 
        'SSH environment file recreated successfully' : 
        'SSH environment file created successfully';
      
      return {
        success: true,
        message,
        sshenvPath,
        gitignoreUpdated
      };
      
    } catch (error) {
      this.logger.error('Failed to initialize SSH environment:', error);
      const errorMessage = error instanceof Error ? error.message : String(error);
      throw ErrorFactory.fileOperationFailed('create', sshenvPath, { error: errorMessage });
    }
  }

  private async fileExists(filePath: string): Promise<boolean> {
    try {
      await fs.access(filePath);
      return true;
    } catch {
      return false;
    }
  }

  private async updateGitignore(gitignorePath: string): Promise<boolean> {
    try {
      let gitignoreContent = '';
      let exists = false;
      
      // 기존 .gitignore 내용 읽기
      if (await this.fileExists(gitignorePath)) {
        gitignoreContent = await fs.readFile(gitignorePath, 'utf8');
        exists = true;
      }
      
      // .sshenv 항목이 이미 있는지 확인
      if (gitignoreContent.includes('.sshenv')) {
        this.logger.debug('.sshenv already in .gitignore');
        return false;
      }
      
      // .gitignore에 .sshenv 항목 추가
      const updatedContent = gitignoreContent + gitignoreEntry;
      await fs.writeFile(gitignorePath, updatedContent, 'utf8');
      
      const action = exists ? 'Updated' : 'Created';
      this.logger.info(`${action} .gitignore with .sshenv entry`);
      
      return true;
      
    } catch (error) {
      this.logger.warn('Failed to update .gitignore:', error);
      return false;
    }
  }

  // Get all tools
  getAllTools(): MCPTool[] {
    return [
      this.getSSHConnectTool(),
      this.getSSHExecuteCommandTool(),
      this.getSSHListConnectionsTool(),
      this.getSSHDisconnectTool(),
      this.getSSHReadFileTool(),
      this.getSSHWriteFileTool(),
      this.getSSHListFilesTool(),
      this.getSSHInitTool()
    ];
  }

  // Execute tool by name
  async executeTool(name: string, args: any): Promise<any> {
    switch (name) {
      case 'ssh_connect':
        return await this.executeSSHConnect(args);
      case 'ssh_execute_command':
        return await this.executeSSHExecuteCommand(args);
      case 'ssh_list_connections':
        return await this.executeSSHListConnections();
      case 'ssh_disconnect':
        return await this.executeSSHDisconnect(args);
      case 'ssh_read_file':
        return await this.executeSSHReadFile(args);
      case 'ssh_write_file':
        return await this.executeSSHWriteFile(args);
      case 'ssh_list_files':
        return await this.executeSSHListFiles(args);
      case 'ssh_init':
        return await this.executeSSHInit(args);
      default:
        throw ErrorFactory.methodNotFound(name);
    }
  }
} 