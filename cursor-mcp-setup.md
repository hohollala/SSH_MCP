# Cursor IDE에서 SSH MCP 서버 사용하기

## 개요
Cursor IDE는 2024년 말부터 MCP (Model Context Protocol)를 공식적으로 지원합니다. 
이제 우리의 SSH MCP 서버를 Cursor에서 직접 사용할 수 있습니다.

## 설정 방법

### 1. 프로젝트별 설정 (권장)
프로젝트 루트에 `.cursor/mcp.json` 파일이 이미 생성되어 있습니다:

```json
{
  "mcpServers": {
    "ssh-mcp": {
      "command": "node",
      "args": ["E:\\MCPProjects\\SSH_MCP\\dist\\index.js", "--stdin"],
      "env": {
        "SSH_MCP_DEBUG": "true",
        "SSH_MCP_TIMEOUT": "30",
        "SSH_MCP_MAX_CONNECTIONS": "10"
      }
    }
  }
}
```

### 2. Cursor에서 활성화
1. Cursor IDE를 재시작하세요
2. AI 채팅에서 SSH 관련 작업을 요청하면 자동으로 MCP 서버가 활성화됩니다
3. 또는 직접 `@ssh-mcp` 멘션으로 MCP 서버를 호출할 수 있습니다

### 3. 사용 예시
```
@ssh-mcp development 서버에 연결하고 현재 디렉토리의 파일들을 보여줘
```

```
@ssh-mcp production 서버의 로그 파일을 확인해줘
```

## 주의사항
1. **MCP 서버가 빌드되어 있어야 합니다**: `npm run build` 실행
2. **환경설정 파일이 필요합니다**: `.sshenv` 파일이 프로젝트에 있어야 합니다
3. **Node.js 18+ 필요**: Cursor의 Node.js 버전이 18 이상이어야 합니다

## 문제 해결
- MCP 서버가 인식되지 않으면 Cursor를 재시작해보세요
- 연결 오류가 발생하면 `.sshenv` 파일의 설정을 확인하세요
- 빌드 오류가 있으면 `npm run build`를 다시 실행하세요

## 전역 설정 (선택사항)
프로젝트별이 아닌 전역으로 설정하려면 Cursor 설정에서 MCP 서버를 등록할 수 있습니다.

이제 Claude Desktop뿐만 아니라 Cursor IDE에서도 SSH MCP 서버를 사용할 수 있습니다!