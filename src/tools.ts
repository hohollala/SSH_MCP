import { createLogger } from './logger.js';
import { SSHConnectionManager } from './connection-manager.js';
import { ErrorFactory } from './errors.js';
import { EnvParser } from './env-parser.js';
import { sshenvTemplateWithPassphrase, sshenvTemplateWithoutPassphrase, gitignoreEntry } from './sshenv-template.js';
import { geminiCommandTemplates } from './command-templates.js';
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
    // 비동기 초기화는 필요할 때 수행
  }

  private async ensureEnvParserInitialized(): Promise<void> {
    if (!this.envParser.isEnvLoaded()) {
      try {
        await this.envParser.loadEnvFile();
      } catch (error) {
        this.logger.debug('Environment file not loaded');
      }
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
          privateKeyPath: {
            type: 'string',
            description: 'Path to private key file for authentication (if using key auth)'
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
          clientPath: {
            type: 'string',
            description: 'The absolute path of the client\'s working directory. If not provided, the server\'s working directory will be used.'
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
          },
          includePassphrase: {
            type: 'boolean',
            description: 'Include passphrase fields in the template (for encrypted private keys)',
            default: true
          }
        }
      }
    };
  }

  // Generate Gemini Commands Tool
  getSSHGenerateGeminiTool(): MCPTool {
    return {
      name: 'ssh_generate_gemini',
      description: 'Generate Gemini CLI SSH command TOML files',
      inputSchema: {
        type: 'object',
        properties: {
          path: {
            type: 'string',
            description: 'Path where to create TOML files (default: ~/.gemini/commands/ssh)',
            default: '~/.gemini/commands/ssh'
          },
          force: {
            type: 'boolean',
            description: 'Overwrite existing files',
            default: false
          }
        }
      }
    };
  }

  // Tool execution methods
  async executeSSHConnect(args: any): Promise<SSHConnection> {
    // 환경변수 초기화 보장
    await this.ensureEnvParserInitialized();
    
    // 환경변수 치환
    const expandedArgs = this.envParser.expandObjectVariables(args);
    const { hostname, host, port = 22, username, password, privateKeyPath, passphrase, useAgent = false } = expandedArgs;
    
    // hostname 또는 host 중 하나 사용
    const targetHost = hostname || host;

    this.logger.debug('SSH Connect with expanded args:', { host: targetHost, port, username, useAgent });

    const auth: SSHAuthConfig = {};
    if (password) auth.password = password;
    if (privateKeyPath) {
      try {
        const privateKey = await fs.readFile(privateKeyPath, 'utf8');
        auth.privateKey = privateKey;
        this.logger.debug(`Loaded private key from: ${privateKeyPath}`);
      } catch (error) {
        this.logger.error(`Failed to read private key file: ${privateKeyPath}`, error);
        throw ErrorFactory.connectionFailed(targetHost, port, { error: `Failed to read private key: ${error}` });
      }
    }
    if (passphrase) auth.passphrase = passphrase;
    if (useAgent) auth.agent = true;

    this.logger.info(`Connecting to ${username}@${targetHost}:${port}`);
    return await this.connectionManager.connect(targetHost, port, username, auth);
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
    return Promise.resolve(this.connectionManager.listConnections());
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
    try {
      const { path = '.', clientPath, force = false, addGitignore = true, includePassphrase = true } = args;
      
      // Determine the actual path to use
      const actualPath = clientPath || path;
      const sshenvPath = join(actualPath, '.sshenv');
      
      this.logger.info(`Initializing SSH environment at: ${sshenvPath}`);
      
      // Check if .sshenv already exists
      if (await this.fileExists(sshenvPath) && !force) {
        return {
          success: false,
          message: '.sshenv file already exists. Use --force to overwrite.',
          sshenvPath
        };
      }
      
      // Create directory if it doesn't exist
      try {
        await fs.mkdir(actualPath, { recursive: true });
      } catch (error) {
        this.logger.error(`Failed to create directory: ${actualPath}`, error);
        return {
          success: false,
          message: `Failed to create directory: ${actualPath}`,
          sshenvPath
        };
      }
      
      // Write .sshenv file
      try {
        const template = includePassphrase ? sshenvTemplateWithPassphrase : sshenvTemplateWithoutPassphrase;
        await fs.writeFile(sshenvPath, template, 'utf8');
        this.logger.info(`Created .sshenv file at: ${sshenvPath} (passphrase: ${includePassphrase ? 'included' : 'excluded'})`);
      } catch (error) {
        this.logger.error(`Failed to write .sshenv file: ${sshenvPath}`, error);
        return {
          success: false,
          message: `Failed to write .sshenv file: ${sshenvPath}`,
          sshenvPath
        };
      }
      
      // Update .gitignore if requested
      let gitignoreUpdated = false;
      if (addGitignore) {
        const gitignorePath = join(actualPath, '.gitignore');
        gitignoreUpdated = await this.updateGitignore(gitignorePath);
      }
      
      return {
        success: true,
        message: `SSH environment initialized successfully. Created .sshenv at: ${sshenvPath}`,
        sshenvPath,
        gitignoreUpdated
      };
      
    } catch (error) {
      this.logger.error('Failed to initialize SSH environment', error);
      return {
        success: false,
        message: `Failed to initialize SSH environment: ${error}`,
        sshenvPath: ''
      };
    }
  }

  async executeSSHGenerateGemini(args: any): Promise<{
    success: boolean;
    message: string;
    generatedFiles: string[];
    targetPath: string;
  }> {
    try {
      const { path = '~/.gemini/commands/ssh', force = false } = args;
      
      // Expand ~ to home directory
      const expandedPath = path.replace(/^~/, process.env.HOME || process.env.USERPROFILE || '');
      const targetPath = join(expandedPath);
      
      this.logger.info(`Generating Gemini CLI commands at: ${targetPath}`);
      
      // Create directory if it doesn't exist
      try {
        await fs.mkdir(targetPath, { recursive: true });
        this.logger.info(`Created directory: ${targetPath}`);
      } catch (error) {
        this.logger.error(`Failed to create directory: ${targetPath}`, error);
        return {
          success: false,
          message: `Failed to create directory: ${targetPath}`,
          generatedFiles: [],
          targetPath
        };
      }
      
      const generatedFiles: string[] = [];
      
      // Generate TOML files from templates
      for (const [filename, template] of Object.entries(geminiCommandTemplates)) {
        const filePath = join(targetPath, filename);
        
        // Check if file already exists
        if (await this.fileExists(filePath) && !force) {
          this.logger.warn(`File already exists, skipping: ${filename}`);
          continue;
        }
        
        try {
          await fs.writeFile(filePath, template, 'utf8');
          generatedFiles.push(filename);
          this.logger.info(`Generated: ${filename}`);
        } catch (error) {
          this.logger.error(`Failed to write file: ${filename}`, error);
        }
      }
      
      if (generatedFiles.length === 0) {
        return {
          success: false,
          message: 'No files were generated. All files already exist and --force was not specified.',
          generatedFiles: [],
          targetPath
        };
      }
      
      return {
        success: true,
        message: `Successfully generated ${generatedFiles.length} Gemini CLI command files at: ${targetPath}`,
        generatedFiles,
        targetPath
      };
      
    } catch (error) {
      this.logger.error('Failed to generate Gemini CLI commands', error);
      return {
        success: false,
        message: `Failed to generate Gemini CLI commands: ${error}`,
        generatedFiles: [],
        targetPath: ''
      };
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
      this.getSSHInitTool(),
      this.getSSHGenerateGeminiTool()
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
      case 'ssh_generate_gemini':
        return await this.executeSSHGenerateGemini(args);
      default:
        throw ErrorFactory.methodNotFound(name);
    }
  }
} 