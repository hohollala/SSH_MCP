import { promises as fs } from 'fs';
import { join } from 'path';
import { createLogger } from './logger.js';

export class EnvParser {
  private logger = createLogger('EnvParser');
  private envVars: Map<string, string> = new Map();
  private isLoaded = false;
  private envFilePath: string;

  constructor(envFilePath?: string) {
    this.envFilePath = envFilePath || join(process.cwd(), '.sshenv');
  }

  /**
   * .sshenv 파일을 로드하여 환경변수를 파싱합니다
   */
  async loadEnvFile(): Promise<void> {
    try {
      const content = await fs.readFile(this.envFilePath, 'utf8');
      this.parseEnvContent(content);
      this.isLoaded = true;
      this.logger.info(`Loaded SSH environment variables from: ${this.envFilePath}`);
      this.logger.debug(`Loaded ${this.envVars.size} environment variables`);
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === 'ENOENT') {
        this.logger.warn(`SSH environment file not found: ${this.envFilePath}`);
        this.logger.info('Use "init" command to create .sshenv file');
      } else {
        this.logger.error('Failed to load SSH environment file:', error);
        throw error;
      }
    }
  }

  /**
   * 환경변수 파일 내용을 파싱합니다
   */
  private parseEnvContent(content: string): void {
    const lines = content.split('\n');
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i]?.trim() || '';
      
      // 빈 줄이나 주석 건너뛰기
      if (!line || line.startsWith('#')) {
        continue;
      }
      
      // KEY=VALUE 형태 파싱
      const equalIndex = line.indexOf('=');
      if (equalIndex === -1) {
        this.logger.warn(`Invalid env line ${i + 1}: ${line}`);
        continue;
      }
      
      const key = line.substring(0, equalIndex).trim();
      const value = line.substring(equalIndex + 1).trim();
      
      // 따옴표 제거
      const cleanValue = this.removeQuotes(value);
      
      this.envVars.set(key, cleanValue);
      this.logger.debug(`Loaded env var: ${key}=${cleanValue ? '[SET]' : '[EMPTY]'}`);
    }
  }

  /**
   * 따옴표 제거
   */
  private removeQuotes(value: string): string {
    if (value.length >= 2) {
      if ((value.startsWith('"') && value.endsWith('"')) ||
          (value.startsWith("'") && value.endsWith("'"))) {
        return value.slice(1, -1);
      }
    }
    return value;
  }

  /**
   * 문자열에서 ${VAR_NAME} 형태의 변수를 치환합니다
   */
  expandVariables(input: string): string {
    if (!this.isLoaded) {
      this.logger.warn('Environment variables not loaded. Call loadEnvFile() first.');
      return input;
    }

    return input.replace(/\$\{([^}]+)\}/g, (match, varName) => {
      const value = this.envVars.get(varName);
      
      if (value === undefined) {
        this.logger.warn(`Environment variable not found: ${varName}`);
        return match; // 원본 문자열 유지
      }
      
      if (value === '') {
        this.logger.warn(`Environment variable is empty: ${varName}`);
        return '';
      }
      
      this.logger.debug(`Expanded \${${varName}} -> ${value}`);
      return value;
    });
  }

  /**
   * 객체의 모든 문자열 값에서 환경변수를 치환합니다
   */
  expandObjectVariables(obj: any): any {
    if (typeof obj === 'string') {
      return this.expandVariables(obj);
    }
    
    if (typeof obj === 'number' || typeof obj === 'boolean' || obj === null) {
      return obj;
    }
    
    if (Array.isArray(obj)) {
      return obj.map(item => this.expandObjectVariables(item));
    }
    
    if (typeof obj === 'object') {
      const result: any = {};
      for (const [key, value] of Object.entries(obj)) {
        result[key] = this.expandObjectVariables(value);
      }
      return result;
    }
    
    return obj;
  }

  /**
   * 특정 환경변수 값 조회
   */
  getEnvVar(name: string): string | undefined {
    return this.envVars.get(name);
  }

  /**
   * 모든 환경변수 목록 조회
   */
  getAllEnvVars(): Record<string, string> {
    return Object.fromEntries(this.envVars);
  }

  /**
   * 환경변수가 로드되었는지 확인
   */
  isEnvLoaded(): boolean {
    return this.isLoaded;
  }

  /**
   * 환경변수 개수 조회
   */
  getEnvCount(): number {
    return this.envVars.size;
  }

  /**
   * 환경변수 파일 경로 조회
   */
  getEnvFilePath(): string {
    return this.envFilePath;
  }

  /**
   * 환경변수 파일 존재 여부 확인
   */
  async envFileExists(): Promise<boolean> {
    try {
      await fs.access(this.envFilePath);
      return true;
    } catch {
      return false;
    }
  }

  /**
   * 환경변수 유효성 검사
   */
  validateRequiredVars(requiredVars: string[]): { valid: boolean; missing: string[] } {
    const missing = requiredVars.filter(varName => {
      const value = this.envVars.get(varName);
      return value === undefined || value === '';
    });

    return {
      valid: missing.length === 0,
      missing
    };
  }
}