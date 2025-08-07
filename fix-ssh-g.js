#!/usr/bin/env node

import { promises as fs } from 'fs';
import { join } from 'path';
import { homedir } from 'os';
import { commandTemplates } from './dist/command-templates.js';

async function fixSshG() {
  try {
    console.log('🔧 모든 SSH 명령어 MD 파일들을 강제로 생성합니다...');
    
    const commandsDir = join(homedir(), '.claude', 'commands', 'ssh');
    
    // 디렉토리가 없으면 생성
    await fs.mkdir(commandsDir, { recursive: true });
    console.log(`📁 디렉토리 확인: ${commandsDir}`);
    
    const generatedFiles = [];
    
    // 모든 MD 파일 템플릿 생성
    for (const [filename, template] of Object.entries(commandTemplates)) {
      if (filename.endsWith('.md')) {
        const filePath = join(commandsDir, filename);
        
        try {
          await fs.writeFile(filePath, template, 'utf8');
          generatedFiles.push(filename);
          console.log(`✅ 생성됨: ${filename}`);
        } catch (error) {
          console.error(`❌ 생성 실패: ${filename}`, error);
        }
      }
    }
    
    console.log(`📊 총 ${generatedFiles.length}개 SSH MD 파일 생성 완료`);
    console.log(`📋 생성된 파일들: ${generatedFiles.join(', ')}`);
    
    // 전체 파일 목록 확인
    const files = await fs.readdir(commandsDir);
    const mdFiles = files.filter(file => file.endsWith('.md'));
    console.log(`📋 현재 .md 파일들: ${mdFiles.join(', ')}`);
    
    console.log('🎉 모든 SSH 명령어 MD 파일 생성 완료!');
    
  } catch (error) {
    console.error('❌ 오류 발생:', error);
    process.exit(1);
  }
}

fixSshG();
