// SSH MCP 명령어 문서 템플릿
export const commandTemplates = {
  'connect.md': `# SSH Connect - 원격 서버 연결

## 사용법
\`\`\`
mcp__ssh-mcp__ssh_connect
\`\`\`

## 설명
SSH를 통해 원격 서버에 연결합니다.

## 매개변수
- **host** (필수): 서버 호스트명 또는 IP 주소
- **username** (필수): SSH 사용자명
- **port** (선택, 기본값: 22): SSH 포트
- **password** (선택): 비밀번호 인증 시 사용
- **privateKey** (선택): 개인키 인증 시 사용
- **passphrase** (선택): 개인키 암호구문
- **useAgent** (선택, 기본값: false): SSH 에이전트 사용 여부

## 예시
\`\`\`json
{
  "host": "192.168.1.100",
  "username": "ubuntu",
  "port": 22,
  "password": "your_password"
}
\`\`\`

## 반환값
연결 성공 시 connectionId를 반환합니다.
`,

  'disconnect.md': `# SSH Disconnect - 연결 해제

## 사용법
\`\`\`
mcp__ssh-mcp__ssh_disconnect
\`\`\`

## 설명
활성화된 SSH 연결을 해제합니다.

## 매개변수
- **connectionId** (필수): 해제할 연결의 ID

## 예시
\`\`\`json
{
  "connectionId": "conn_123456"
}
\`\`\`

## 반환값
연결 해제 성공 메시지를 반환합니다.
`,

  'list-connections.md': `# SSH List Connections - 연결 목록 조회

## 사용법
\`\`\`
mcp__ssh-mcp__ssh_list_connections
\`\`\`

## 설명
현재 활성화된 모든 SSH 연결 목록을 조회합니다.

## 매개변수
매개변수가 필요하지 않습니다.

## 예시
\`\`\`json
{}
\`\`\`

## 반환값
활성 연결 목록과 상태 정보를 반환합니다.
`,

  'list-files.md': `# SSH List Files - 파일 목록 조회

## 사용법
\`\`\`
mcp__ssh-mcp__ssh_list_files
\`\`\`

## 설명
SSH 연결을 통해 원격 서버의 디렉토리 파일 목록을 조회합니다.

## 매개변수
- **connectionId** (필수): 사용할 연결 ID
- **path** (선택, 기본값: "."): 조회할 디렉토리 경로

## 예시
\`\`\`json
{
  "connectionId": "conn_123456",
  "path": "/home/ubuntu"
}
\`\`\`

## 반환값
디렉토리 파일 목록과 상세 정보를 반환합니다.
`,

  'exec.md': `# SSH Exec - 원격 명령 실행

## 사용법
\`\`\`
mcp__ssh-mcp__ssh_execute_command
\`\`\`

## 설명
SSH 연결을 통해 원격 서버에서 명령을 실행합니다.

## 매개변수
- **connectionId** (필수): 사용할 연결 ID
- **command** (필수): 실행할 명령어
- **cwd** (선택): 작업 디렉토리
- **timeout** (선택, 기본값: 60): 타임아웃(초)

## 예시
\`\`\`json
{
  "connectionId": "conn_123456",
  "command": "ls -la",
  "cwd": "/home/ubuntu"
}
\`\`\`

## 반환값
명령 실행 결과와 출력을 반환합니다.
`,

  'read.md': `# SSH Read - 파일 읽기

## 사용법
\`\`\`
mcp__ssh-mcp__ssh_read_file
\`\`\`

## 설명
SSH 연결을 통해 원격 서버의 파일을 읽습니다.

## 매개변수
- **connectionId** (필수): 사용할 연결 ID
- **path** (필수): 읽을 파일 경로
- **encoding** (선택, 기본값: utf8): 파일 인코딩

## 예시
\`\`\`json
{
  "connectionId": "conn_123456",
  "path": "/home/ubuntu/config.txt",
  "encoding": "utf8"
}
\`\`\`

## 반환값
파일 내용을 반환합니다.
`,

  'write.md': `# SSH Write - 파일 쓰기

## 사용법
\`\`\`
mcp__ssh-mcp__ssh_write_file
\`\`\`

## 설명
SSH 연결을 통해 원격 서버에 파일을 작성합니다.

## 매개변수
- **connectionId** (필수): 사용할 연결 ID
- **path** (필수): 저장할 파일 경로
- **content** (필수): 파일 내용
- **encoding** (선택, 기본값: utf8): 파일 인코딩

## 예시
\`\`\`json
{
  "connectionId": "conn_123456",
  "path": "/home/ubuntu/output.txt",
  "content": "Hello World!"
}
\`\`\`

## 반환값
파일 쓰기 성공 메시지를 반환합니다.
`,


  'init.md': `# SSH Init - SSH 환경 초기화

## 사용법
\`\`\`
mcp__ssh-mcp__ssh_init
\`\`\`

## 설명
SSH MCP 환경을 초기화하여 .sshenv 설정 파일을 생성합니다.

## 매개변수
- **path** (선택, 기본값: "."): .sshenv 파일을 생성할 경로
- **force** (선택, 기본값: false): 기존 파일 덮어쓰기 여부
- **addGitignore** (선택, 기본값: true): .gitignore에 .sshenv 추가 여부

## 예시
\`\`\`json
{
  "path": ".",
  "force": false,
  "addGitignore": true
}
\`\`\`

## 반환값
초기화 성공 여부와 생성된 파일 경로를 반환합니다.

## .sshenv 파일 사용법
생성된 .sshenv 파일에 서버별 환경변수를 설정하고, MCP 명령어에서 \${VAR_NAME} 형태로 참조하세요.

### 예시 설정
\`\`\`env
DEV_HOST=192.168.1.100
DEV_USER=ubuntu
DEV_PASSWORD=your_password
\`\`\`

### 예시 사용
\`\`\`json
{
  "host": "\${DEV_HOST}",
  "username": "\${DEV_USER}",
  "password": "\${DEV_PASSWORD}"
}
\`\`\`

## 보안 주의사항
- .sshenv 파일을 git에 커밋하지 마세요
- 가능하면 password 대신 SSH 키를 사용하세요
- 파일 권한을 600으로 설정하세요: \`chmod 600 .sshenv\`
`,

  'README.md': `# SSH MCP Commands Guide

SSH MCP 서버의 모든 명령어를 설명합니다.

## 환경 설정
- [init](./init.md) - SSH 환경 초기화 (.sshenv 파일 생성)

## 연결 관리
- [connect](./connect.md) - SSH 서버 연결
- [disconnect](./disconnect.md) - SSH 연결 해제
- [list-connections](./list-connections.md) - 활성 연결 목록

## 명령 실행
- [exec](./exec.md) - 원격 명령 실행

## 파일 조작
- [read](./read.md) - 파일 읽기
- [write](./write.md) - 파일 쓰기
- [list-files](./list-files.md) - 파일 목록

## 빠른 시작
1. \`init\`으로 .sshenv 환경 파일 생성
2. .sshenv 파일에 서버 정보 입력
3. \`connect\`로 서버에 연결 (환경변수 사용)
4. \`exec\`로 명령 실행 또는 \`list-files\`로 파일 탐색
5. 작업 완료 후 \`disconnect\`로 연결 해제

## 환경변수 사용 예시
\`\`\`json
{
  "host": "\${DEV_HOST}",
  "username": "\${DEV_USER}",
  "password": "\${DEV_PASSWORD}"
}
\`\`\`

## 명령어 매핑
- \`ssh_init\` → init
- \`ssh_connect\` → connect
- \`ssh_disconnect\` → disconnect  
- \`ssh_list_connections\` → list-connections
- \`ssh_execute_command\` → exec
- \`ssh_read_file\` → read
- \`ssh_write_file\` → write
- \`ssh_list_files\` → list-files
`
};