// 환경 변수 설정
process.env.SSH_MCP_DEBUG = 'true';
process.env.SSH_MCP_ALLOW_PASSWORD_AUTH = 'true';
process.env.SSH_MCP_ALLOW_KEY_AUTH = 'true';

import { SSHMCPServer } from './dist/mcp-server.js';

async function checkServerStructure() {
  console.log('SSH 서버 폴더 구조 확인...');
  
  try {
    // MCP 서버 인스턴스 생성
    const mcpServer = new SSHMCPServer();
    
    console.log('MCP 서버 생성 완료');
    
    // SSH 연결
    const connectResult = await mcpServer.executeTool('ssh_connect', {
      host: '158.180.71.210',
      username: 'ubuntu',
      privateKeyPath: 'E:\\AIProjects\\ssh_Test\\docs\\first.pem',
      port: 22
    });
    
    console.log('SSH 연결 결과:', connectResult);
    
    // connectionId 확인
    const connectionId = connectResult.id || connectResult.connectionId;
    console.log('사용할 connectionId:', connectionId);
    
    if (!connectionId) {
      console.error('연결 ID를 찾을 수 없습니다');
      return;
    }
    
    // 서버의 폴더 구조 확인
    const commands = [
      'pwd',                    // 현재 디렉토리
      'ls -la',                 // 현재 폴더 내용
      'ls -la /home/ubuntu',    // 홈 디렉토리
      'ls -la /var/www',        // 웹 서버 폴더 (있다면)
      'ls -la /opt',            // opt 폴더
      'df -h',                  // 디스크 사용량
      'free -h',                // 메모리 사용량
      'ps aux | head -10'       // 실행 중인 프로세스
    ];
    
    for (const command of commands) {
      console.log(`\n=== ${command} ===`);
      try {
        const result = await mcpServer.executeTool('ssh_execute_command', {
          connectionId: connectionId,
          command: command
        });
        
        console.log('결과:', result.stdout);
        if (result.stderr) {
          console.log('오류:', result.stderr);
        }
      } catch (error) {
        console.log('명령 실행 실패:', error.message);
      }
    }
    
    // 연결 해제
    const disconnectResult = await mcpServer.executeTool('ssh_disconnect', {
      connectionId: connectionId
    });
    console.log('연결 해제 완료');
    
  } catch (error) {
    console.error('테스트 실패:', error);
  }
}

// 테스트 실행
checkServerStructure().catch(console.error); 