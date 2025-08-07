#!/usr/bin/env node

import { CommandInstaller } from './dist/command-installer.js';

async function forceInstallCommands() {
  try {
    console.log('강제로 SSH 명령어 문서를 설치합니다...');
    
    const installer = new CommandInstaller();
    
    // 강제 모드로 모든 명령어 파일 설치
    await installer.installCommands(true);
    
    // 설치 정보 확인
    const info = await installer.getInstallationInfo();
    console.log('설치 정보:', info);
    
    console.log('✅ SSH 명령어 문서 설치 완료!');
    
  } catch (error) {
    console.error('❌ 설치 실패:', error);
    process.exit(1);
  }
}

forceInstallCommands();
