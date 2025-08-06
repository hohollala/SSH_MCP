// 환경 변수 설정
process.env.SSH_MCP_DEBUG = 'true';
process.env.SSH_MCP_ALLOW_PASSWORD_AUTH = 'true';
process.env.SSH_MCP_ALLOW_KEY_AUTH = 'true';

import { SSHMCPServer } from './dist/mcp-server.js';
import { readFileSync } from 'fs';

async function testSSHConnect() {
  console.log('MCP SSH 연결 테스트 시작...');
  
  try {
    // MCP 서버 인스턴스 생성
    const mcpServer = new SSHMCPServer();
    
    console.log('MCP 서버 생성 완료');
    
    // 개인키 파일 읽기
    const privateKey = readFileSync('E:\\AIProjects\\ssh_Test\\docs\\first.pem', 'utf8');
    console.log('개인키 파일 로드 완료');
    
    // SSH 연결 테스트를 위한 도구 실행 (개인키 사용)
    const connectResult = await mcpServer.executeTool('ssh_connect', {
      host: '158.180.71.210',
      username: 'ubuntu',
      privateKeyPath: 'E:\\AIProjects\\ssh_Test\\docs\\first.pem',
      port: 22
    });
    
    console.log('SSH 연결 결과:', connectResult);
    
    // 연결 후 명령 실행 테스트
    if (connectResult && connectResult.connectionId) {
      const commandResult = await mcpServer.executeTool('ssh_execute_command', {
        connectionId: connectResult.connectionId,
        command: 'whoami && pwd && ls -la'
      });
      
      console.log('명령 실행 결과:', commandResult);
      
      // 연결 목록 확인
      const connections = await mcpServer.executeTool('ssh_list_connections', {});
      console.log('현재 연결 목록:', connections);
      
      // 연결 해제
      const disconnectResult = await mcpServer.executeTool('ssh_disconnect', {
        connectionId: connectResult.connectionId
      });
      console.log('연결 해제 결과:', disconnectResult);
    }
    
  } catch (error) {
    console.error('테스트 실패:', error);
  }
}

// 테스트 실행
testSSHConnect().catch(console.error); 