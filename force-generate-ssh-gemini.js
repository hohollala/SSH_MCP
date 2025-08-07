#!/usr/bin/env node

import { promises as fs } from 'fs';
import { join } from 'path';
import { homedir } from 'os';
import { geminiCommandTemplates } from './dist/command-templates.js';

async function forceGenerateSshGemini() {
  try {
    console.log('🔧 SSH Gemini CLI 명령어를 강제로 생성합니다...');
    
    const targetPath = join(homedir(), '.gemini', 'commands', 'ssh');
    
    // 디렉토리가 없으면 생성
    await fs.mkdir(targetPath, { recursive: true });
    console.log(`📁 디렉토리 확인: ${targetPath}`);
    
    const generatedFiles = [];
    
    // Gemini CLI용 SSH TOML 파일 강제 생성
    for (const [filename, template] of Object.entries(geminiCommandTemplates)) {
      const filePath = join(targetPath, filename);
      
      try {
        await fs.writeFile(filePath, template, 'utf8');
        generatedFiles.push(filename);
        console.log(`✅ 생성됨: ${filename}`);
      } catch (error) {
        console.error(`❌ 생성 실패: ${filename}`, error);
      }
    }
    
    console.log(`📊 총 ${generatedFiles.length}개 SSH 파일 생성 완료`);
    console.log(`📋 생성된 파일들: ${generatedFiles.join(', ')}`);
    
    // 생성된 파일 목록 확인
    const files = await fs.readdir(targetPath);
    const tomlFiles = files.filter(file => file.endsWith('.toml'));
    console.log(`📋 현재 SSH .toml 파일들: ${tomlFiles.join(', ')}`);
    
    console.log('🎉 SSH Gemini CLI 명령어 생성 완료!');
    
  } catch (error) {
    console.error('❌ 오류 발생:', error);
    process.exit(1);
  }
}

forceGenerateSshGemini();
