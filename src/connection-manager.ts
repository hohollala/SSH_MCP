import { Client } from 'ssh2';
import { createLogger } from './logger.js';
import config from './config.js';
import { 
  SSHConnection, 
  SSHAuthConfig, 
  SSHCommand, 
  SSHCommandResult,
  ConnectionManager 
} from './types.js';
import { ErrorFactory } from './errors.js';

export class SSHConnectionManager implements ConnectionManager {
  private connections: Map<string, { connection: Client; info: SSHConnection }> = new Map();
  private logger = createLogger('SSHConnectionManager');

  async connect(
    host: string, 
    port: number, 
    username: string, 
    auth: SSHAuthConfig
  ): Promise<SSHConnection> {
    const connectionId = this.generateConnectionId(host, port, username);
    
    // Check if connection already exists
    if (this.connections.has(connectionId)) {
      const existing = this.connections.get(connectionId)!;
      if (existing.info.isConnected) {
        this.logger.info(`Reusing existing connection to ${host}:${port}`);
        return existing.info;
      }
    }

    return new Promise((resolve, reject) => {
      const client = new Client();
      const connectionInfo: SSHConnection = {
        id: connectionId,
        host,
        port,
        username,
        isConnected: false,
        createdAt: new Date(),
        lastUsed: new Date()
      };

      const connectConfig: any = {
        host,
        port,
        username,
        readyTimeout: config.connectionTimeout * 1000,
        keepaliveInterval: 30000,  // 30초마다 keepalive
        keepaliveCountMax: 10,     // 10번까지 실패 허용
        algorithms: {
          serverHostKey: ['ssh-rsa', 'ssh-dss', 'ecdsa-sha2-nistp256', 'ecdsa-sha2-nistp384', 'ecdsa-sha2-nistp521', 'ssh-ed25519']
        }
      };

      // Add authentication methods
      if (auth.password) {
        connectConfig.password = auth.password;
      } else if (auth.privateKey) {
        connectConfig.privateKey = auth.privateKey;
        if (auth.passphrase) {
          connectConfig.passphrase = auth.passphrase;
        }
      } else if (auth.agent) {
        connectConfig.agent = process.env.SSH_AUTH_SOCK;
      }

      client.on('ready', () => {
        this.logger.info(`SSH connection established to ${host}:${port}`);
        connectionInfo.isConnected = true;
        connectionInfo.lastUsed = new Date();
        
        this.connections.set(connectionId, {
          connection: client,
          info: connectionInfo
        });
        
        this.logger.info(`Connection stored with ID: ${connectionId}`);
        this.logger.info(`Total connections: ${this.connections.size}`);
        
        // 연결 상태 모니터링
        const keepAliveInterval = setInterval(() => {
          if (this.connections.has(connectionId)) {
            connectionInfo.lastUsed = new Date();
            this.logger.debug(`Keepalive for ${connectionId}`);
          } else {
            clearInterval(keepAliveInterval);
          }
        }, 60000); // 1분마다 상태 확인
        
        resolve(connectionInfo);
      });

      client.on('error', (error) => {
        this.logger.error(`SSH connection error to ${host}:${port}:`, error);
        reject(ErrorFactory.connectionFailed(host, port, { error: error.message }));
      });

      client.on('timeout', () => {
        this.logger.error(`SSH connection timeout to ${host}:${port}`);
        reject(ErrorFactory.connectionTimeout(host, port, config.connectionTimeout));
      });

      client.on('end', () => {
        this.logger.info(`SSH connection ended to ${host}:${port}`);
        // 연결이 정상적으로 종료된 경우에만 삭제
        // 연결이 성공적으로 유지되어야 하므로 삭제하지 않음
        // this.removeConnection(connectionId);
      });

      // Handle connection close
      client.on('close', () => {
        this.logger.info(`SSH connection closed to ${host}:${port}`);
        // 연결이 정상적으로 종료된 경우에만 삭제
        // 연결이 성공적으로 유지되어야 하므로 삭제하지 않음
        // this.removeConnection(connectionId);
      });

      client.connect(connectConfig);
    });
  }

  async disconnect(connectionId: string): Promise<void> {
    const connection = this.connections.get(connectionId);
    if (!connection) {
      throw ErrorFactory.connectionNotFound(connectionId);
    }

    return new Promise((resolve) => {
      connection.connection.end();
      this.removeConnection(connectionId);
      this.logger.info(`Disconnected from ${connection.info.host}:${connection.info.port}`);
      resolve();
    });
  }

  async executeCommand(connectionId: string, command: SSHCommand): Promise<SSHCommandResult> {
    const connection = this.connections.get(connectionId);
    if (!connection) {
      throw ErrorFactory.connectionNotFound(connectionId);
    }

    if (!connection.info.isConnected) {
      throw ErrorFactory.connectionFailed(
        connection.info.host, 
        connection.info.port, 
        { reason: 'Connection not established' }
      );
    }

    return new Promise((resolve, reject) => {
      const startTime = Date.now();
      let stdout = '';
      let stderr = '';

      connection.connection.exec(command.command, (error, stream) => {
        if (error) {
          reject(ErrorFactory.commandFailed(command.command, -1, error.message));
          return;
        }

        stream.on('data', (data: Buffer) => {
          stdout += data.toString();
        });

        stream.stderr.on('data', (data: Buffer) => {
          stderr += data.toString();
        });

        stream.on('close', (code: number) => {
          const duration = Date.now() - startTime;
          connection.info.lastUsed = new Date();

          const result: SSHCommandResult = {
            id: command.id,
            exitCode: code || 0,
            stdout,
            stderr,
            duration
          };

          this.logger.info(`Command executed on ${connection.info.host}: ${command.command} (exit: ${code})`);
          resolve(result);
        });

        stream.on('error', (error: Error) => {
          reject(ErrorFactory.commandFailed(command.command, -1, error.message));
        });
      });
    });
  }

  listConnections(): SSHConnection[] {
    return Array.from(this.connections.values()).map(conn => conn.info);
  }

  getConnection(connectionId: string): SSHConnection | undefined {
    const connection = this.connections.get(connectionId);
    return connection?.info;
  }

  private generateConnectionId(host: string, port: number, username: string): string {
    const timestamp = Date.now();
    const random = Math.random().toString(36).substring(2, 8);
    return `${username}@${host}:${port}_${timestamp}_${random}`;
  }

  private removeConnection(connectionId: string): void {
    const connection = this.connections.get(connectionId);
    if (connection) {
      connection.info.isConnected = false;
      this.connections.delete(connectionId);
      this.logger.info(`Removed connection: ${connectionId}`);
    }
  }

  // Cleanup method for graceful shutdown
  async cleanup(): Promise<void> {
    this.logger.info('Cleaning up SSH connections...');
    const disconnectPromises = Array.from(this.connections.keys()).map(id => this.disconnect(id));
    await Promise.allSettled(disconnectPromises);
    this.logger.info('SSH connections cleanup completed');
  }
} 