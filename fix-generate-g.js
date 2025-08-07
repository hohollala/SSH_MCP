#!/usr/bin/env node

import { promises as fs } from 'fs';
import { join } from 'path';
import { homedir } from 'os';
import { commandTemplates } from './dist/command-templates.js';

async function fixGenerateG() {
  try {
    console.log('🔧 generate-g.md 파일을 강제로 생성합니다...');
    
    const commandsDir = join(homedir(), '.claude', 'commands', 'ssh');
    const generateGPath = join(commandsDir, 'generate-g.md');
    
    // 디렉토리가 없으면 생성
    await fs.mkdir(commandsDir, { recursive: true });
    console.log(`📁 디렉토리 확인: ${commandsDir}`);
    
    // generate-g.md 템플릿 가져오기
    const generateGTemplate = commandTemplates['generate-g.md'];
    
    if (!generateGTemplate) {
      throw new Error('generate-g.md 템플릿을 찾을 수 없습니다!');
    }
    
    // 파일 생성
    await fs.writeFile(generateGPath, generateGTemplate, 'utf8');
    console.log(`✅ generate-g.md 파일 생성 완료: ${generateGPath}`);
    
    // 생성된 파일 확인
    const stats = await fs.stat(generateGPath);
    console.log(`📊 파일 크기: ${stats.size} bytes`);
    console.log(`🕒 생성 시간: ${stats.mtime}`);
    
    // 전체 파일 목록 확인
    const files = await fs.readdir(commandsDir);
    const mdFiles = files.filter(file => file.endsWith('.md'));
    console.log(`📋 현재 .md 파일들: ${mdFiles.join(', ')}`);
    
    console.log('🎉 generate-g.md 파일 수정 완료!');
    
  } catch (error) {
    console.error('❌ 오류 발생:', error);
    process.exit(1);
  }
}

fixGenerateG();
