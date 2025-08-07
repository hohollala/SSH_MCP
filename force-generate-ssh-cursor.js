#!/usr/bin/env node

import { promises as fs } from 'fs';
import { join } from 'path';
import { homedir } from 'os';
import { cursorCommandTemplates } from './dist/command-templates.js';

async function forceGenerateSshCursor() {
  try {
    console.log('🔧 Cursor용 SSH 명령어를 강제로 생성합니다...');
    
    const targetPath = join(homedir(), '.cursor', 'rules');
    
    // 디렉토리가 없으면 생성
    await fs.mkdir(targetPath, { recursive: true });
    console.log(`📁 디렉토리 확인: ${targetPath}`);
    
    const generatedFiles = [];
    
    // Cursor용 SSH MD 파일 강제 생성
    for (const [filename, template] of Object.entries(cursorCommandTemplates)) {
      const filePath = join(targetPath, filename);
      
      try {
        await fs.writeFile(filePath, template, 'utf8');
        generatedFiles.push(filename);
        console.log(`✅ 생성됨: ${filename}`);
      } catch (error) {
        console.error(`❌ 생성 실패: ${filename}`, error);
      }
    }
    
    console.log(`📊 총 ${generatedFiles.length}개 Cursor SSH 파일 생성 완료`);
    console.log(`📋 생성된 파일들: ${generatedFiles.join(', ')}`);
    
    // 생성된 파일 목록 확인
    const files = await fs.readdir(targetPath);
    const mdFiles = files.filter(file => file.endsWith('.md'));
    console.log(`📋 현재 Cursor .md 파일들: ${mdFiles.join(', ')}`);
    
    console.log('🎉 Cursor용 SSH 명령어 생성 완료!');
    
  } catch (error) {
    console.error('❌ 오류 발생:', error);
    process.exit(1);
  }
}

forceGenerateSshCursor();
