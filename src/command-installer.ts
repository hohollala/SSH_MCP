import { promises as fs } from 'fs';
import { join } from 'path';
import { homedir } from 'os';
import { createLogger } from './logger.js';
import { commandTemplates } from './command-templates.js';

export class CommandInstaller {
  private logger = createLogger('CommandInstaller');
  private commandsDir: string;

  constructor() {
    this.commandsDir = join(homedir(), '.claude', 'commands', 'ssh');
  }

  /**
   * SSH 명령어 문서 파일들을 설치합니다
   */
  async installCommands(force: boolean = false): Promise<void> {
    try {
      this.logger.info('Installing SSH command documentation...');
      
      // 디렉토리 생성
      await this.ensureDirectoryExists();
      
      // 모든 명령어 파일 생성
      await this.createCommandFiles(force);
      
      this.logger.info(`SSH command documentation installed successfully at: ${this.commandsDir}`);
    } catch (error) {
      this.logger.error('Failed to install SSH command documentation:', error);
      throw error;
    }
  }

  /**
   * 명령어 문서가 이미 설치되어 있는지 확인
   */
  async isInstalled(): Promise<boolean> {
    try {
      const readmePath = join(this.commandsDir, 'README.md');
      await fs.access(readmePath);
      return true;
    } catch {
      return false;
    }
  }

  /**
   * 디렉토리가 존재하지 않으면 생성
   */
  private async ensureDirectoryExists(): Promise<void> {
    try {
      await fs.mkdir(this.commandsDir, { recursive: true });
      this.logger.debug(`Created directory: ${this.commandsDir}`);
    } catch (error) {
      this.logger.error(`Failed to create directory ${this.commandsDir}:`, error);
      throw error;
    }
  }

  /**
   * 모든 명령어 문서 파일 생성
   */
  private async createCommandFiles(force: boolean = false): Promise<void> {
    const createdFiles: string[] = [];
    const skippedFiles: string[] = [];
    const overwrittenFiles: string[] = [];

    for (const [filename, content] of Object.entries(commandTemplates)) {
      const filePath = join(this.commandsDir, filename);
      
      try {
        // 파일이 이미 존재하는지 확인
        await fs.access(filePath);
        
        if (force) {
          // 강제 모드면 덮어쓰기
          await fs.writeFile(filePath, content, 'utf8');
          overwrittenFiles.push(filename);
          this.logger.debug(`Overwritten file: ${filename}`);
        } else {
          // 강제 모드가 아니면 건드리지 않음
          skippedFiles.push(filename);
          this.logger.debug(`File already exists, skipping: ${filename}`);
        }
      } catch {
        // 파일이 존재하지 않으면 생성
        await fs.writeFile(filePath, content, 'utf8');
        createdFiles.push(filename);
        this.logger.debug(`Created file: ${filename}`);
      }
    }

    this.logger.info(`Created ${createdFiles.length} new files, overwritten ${overwrittenFiles.length} files, skipped ${skippedFiles.length} existing files`);
    
    if (createdFiles.length > 0) {
      this.logger.info('Created files:', createdFiles.join(', '));
    }
    
    if (overwrittenFiles.length > 0) {
      this.logger.info('Overwritten files:', overwrittenFiles.join(', '));
    }
    
    if (skippedFiles.length > 0) {
      this.logger.info('Skipped existing files:', skippedFiles.join(', '));
    }
  }

  /**
   * 특정 명령어 파일만 업데이트
   */
  async updateCommandFile(filename: string, force: boolean = false): Promise<void> {
    const filePath = join(this.commandsDir, filename);
    
    if (!commandTemplates[filename as keyof typeof commandTemplates]) {
      throw new Error(`Unknown command file: ${filename}`);
    }

    const content = commandTemplates[filename as keyof typeof commandTemplates];

    try {
      if (!force) {
        // 파일이 존재하는지 확인
        await fs.access(filePath);
        this.logger.warn(`File already exists: ${filename}. Use force=true to overwrite.`);
        return;
      }
      
      await this.ensureDirectoryExists();
      await fs.writeFile(filePath, content, 'utf8');
      this.logger.info(`Updated command file: ${filename}`);
    } catch (error) {
      if (!force) {
        // 파일이 존재하지 않으면 생성
        await this.ensureDirectoryExists();
        await fs.writeFile(filePath, content, 'utf8');
        this.logger.info(`Created command file: ${filename}`);
      } else {
        this.logger.error(`Failed to update command file ${filename}:`, error);
        throw error;
      }
    }
  }

  /**
   * 설치된 명령어 파일 목록 조회
   */
  async listInstalledCommands(): Promise<string[]> {
    try {
      const files = await fs.readdir(this.commandsDir);
      return files.filter(file => file.endsWith('.md'));
    } catch {
      return [];
    }
  }

  /**
   * 명령어 문서 제거
   */
  async uninstallCommands(): Promise<void> {
    try {
      this.logger.info('Uninstalling SSH command documentation...');
      
      const files = await this.listInstalledCommands();
      
      for (const file of files) {
        const filePath = join(this.commandsDir, file);
        await fs.unlink(filePath);
        this.logger.debug(`Removed file: ${file}`);
      }
      
      // 디렉토리가 비어있으면 제거
      try {
        await fs.rmdir(this.commandsDir);
        this.logger.debug(`Removed empty directory: ${this.commandsDir}`);
      } catch {
        // 디렉토리가 비어있지 않거나 다른 이유로 제거 실패
        this.logger.debug(`Directory not empty or removal failed: ${this.commandsDir}`);
      }
      
      this.logger.info(`Removed ${files.length} command documentation files`);
    } catch (error) {
      this.logger.error('Failed to uninstall SSH command documentation:', error);
      throw error;
    }
  }

  /**
   * 설치 상태 정보 조회
   */
  async getInstallationInfo(): Promise<{
    isInstalled: boolean;
    directory: string;
    installedFiles: string[];
    missingFiles: string[];
  }> {
    const installedFiles = await this.listInstalledCommands();
    const expectedFiles = Object.keys(commandTemplates);
    const missingFiles = expectedFiles.filter(file => !installedFiles.includes(file));
    
    return {
      isInstalled: await this.isInstalled(),
      directory: this.commandsDir,
      installedFiles,
      missingFiles
    };
  }
}