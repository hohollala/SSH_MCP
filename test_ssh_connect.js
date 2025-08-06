const { SSHConnectionManager } = require('./dist/connection-manager.js');
const fs = require('fs');
const path = require('path');

async function testSSHConnection() {
  try {
    console.log('🚀 SSH 연결 테스트 시작...');
    
    // SSH 연결 관리자 인스턴스 생성
    const connectionManager = new SSHConnectionManager();
    
    // 연결 설정
    const host = '158.180.71.210';
    const port = 22;
    const username = 'ubuntu';
    const privateKeyPath = path.join(__dirname, 'docs', 'first.pem');
    
    console.log(`📋 연결 정보:`);
    console.log(`   호스트: ${host}`);
    console.log(`   포트: ${port}`);
    console.log(`   사용자: ${username}`);
    console.log(`   개인키 경로: ${privateKeyPath}`);
    
    // 개인키 파일 존재 확인
    if (!fs.existsSync(privateKeyPath)) {
      throw new Error(`개인키 파일을 찾을 수 없습니다: ${privateKeyPath}`);
    }
    
    // 개인키 읽기
    const privateKey = fs.readFileSync(privateKeyPath, 'utf8');
    console.log('✅ 개인키 파일 로드 완료');
    
    // SSH 연결 시도
    console.log('🔌 SSH 연결 시도 중...');
    const connection = await connectionManager.connect(host, port, username, {
      privateKey: privateKey
    });
    
    console.log('✅ SSH 연결 성공!');
    console.log(`   연결 ID: ${connection.id}`);
    console.log(`   연결 시간: ${connection.createdAt}`);
    console.log(`   연결 상태: ${connection.isConnected ? '연결됨' : '연결 안됨'}`);
    
    // 간단한 명령 실행 테스트
    console.log('📝 명령 실행 테스트...');
    const result = await connectionManager.executeCommand(connection.id, {
      command: 'whoami && pwd && date',
      timeout: 10000
    });
    
    console.log('✅ 명령 실행 성공!');
    console.log(`   명령: ${result.command}`);
    console.log(`   종료 코드: ${result.exitCode}`);
    console.log(`   출력:\n${result.stdout}`);
    if (result.stderr) {
      console.log(`   에러:\n${result.stderr}`);
    }
    
    // 연결 목록 확인
    console.log('📊 현재 연결 목록:');
    const connections = connectionManager.listConnections();
    connections.forEach(conn => {
      console.log(`   - ${conn.host}:${conn.port} (${conn.username}) - ${conn.isConnected ? '연결됨' : '연결 안됨'}`);
    });
    
    // 연결 종료
    console.log('🔌 연결 종료 중...');
    await connectionManager.disconnect(connection.id);
    console.log('✅ 연결 종료 완료');
    
    // 정리
    await connectionManager.cleanup();
    console.log('🧹 정리 완료');
    
  } catch (error) {
    console.error('❌ SSH 연결 테스트 실패:', error.message);
    console.error('상세 에러:', error);
  }
}

// 테스트 실행
testSSHConnection(); 