// SSH MCP 명령어 문서 템플릿
export const commandTemplates = {
  'connect.md': `# connect

## 설명
SSH를 통해 원격 서버에 연결합니다

## 카테고리
SSH 연결 관리

## 사용법
\`\`\`
/ssh:connect [host] [username] [--port 22] [--auth password|key|agent]
\`\`\`

## 매개변수
- \`host\` (필수) - 서버 호스트명 또는 IP 주소
- \`username\` (필수) - SSH 사용자명  
- \`--port\` - SSH 포트 (기본값: 22)
- \`--auth\` - 인증 방식 (password, key, agent)
- \`--privateKey\` - 개인키 파일 경로
- \`--passphrase\` - 개인키 암호구문
- \`--useAgent\` - SSH 에이전트 사용 여부

## 예시
- \`/ssh:connect 192.168.1.100 ubuntu --auth password\`
- \`/ssh:connect server.com admin --port 2222 --auth key\`

## 반환값
연결 성공 시 connectionId를 반환합니다.

## 관련 명령어
- [disconnect](./disconnect.md) - SSH 연결 해제
- [list-connections](./list-connections.md) - 활성 연결 목록
`,

  'disconnect.md': `# disconnect

## 설명
활성화된 SSH 연결을 안전하게 해제합니다

## 카테고리
SSH 연결 관리

## 사용법
\`\`\`
/ssh:disconnect [connectionId] [--all] [--force]
\`\`\`

## 매개변수
- \`connectionId\` (필수) - 해제할 연결의 ID
- \`--all\` - 모든 활성 연결 해제
- \`--force\` - 강제 연결 해제 (응답 대기 없음)

## 예시
- \`/ssh:disconnect conn_123456\`
- \`/ssh:disconnect --all\`
- \`/ssh:disconnect conn_123456 --force\`

## 반환값
연결 해제 성공 메시지를 반환합니다.

## 관련 명령어
- [connect](./connect.md) - SSH 서버 연결
- [list-connections](./list-connections.md) - 활성 연결 목록
`,

  'list-connections.md': `# list-connections

## 설명
현재 활성화된 모든 SSH 연결 목록을 조회합니다

## 카테고리
SSH 연결 관리

## 사용법
\`\`\`
/ssh:list-connections [--status active|inactive|all] [--format table|json]
\`\`\`

## 매개변수
- \`--status\` - 연결 상태 필터 (active, inactive, all)
- \`--format\` - 출력 형식 (table, json)
- \`--detail\` - 상세 정보 포함 여부

## 예시
- \`/ssh:list-connections\`
- \`/ssh:list-connections --status active\`
- \`/ssh:list-connections --format json\`

## 반환값
활성 연결 목록, 상태 정보, 연결 통계를 포함한 연결 보고서를 반환합니다.

## 관련 명령어
- [connect](./connect.md) - SSH 서버 연결
- [disconnect](./disconnect.md) - SSH 연결 해제
`,

  'list-files.md': `# list-files

## 설명
SSH 연결을 통해 원격 서버의 파일 목록을 조회합니다

## 카테고리
파일 조작

## 사용법
\`\`\`
/ssh:list-files [connectionId] [path]
\`\`\`

## 매개변수
- \`connectionId\` (필수) - 사용할 연결 ID
- \`path\` (선택, 기본값: ".") - 조회할 디렉토리 경로

## 예시
- \`/ssh:list-files conn_123456\`
- \`/ssh:list-files conn_123456 /home/ubuntu\`
- \`/ssh:list-files conn_123456 /var/log\`

## 반환값
디렉토리 파일 목록과 상세 정보를 반환합니다.

## 관련 명령어
- [read](./read.md) - 파일 읽기
- [write](./write.md) - 파일 쓰기
- [exec](./exec.md) - 원격 명령 실행
`,

  'exec.md': `# exec

## 설명
SSH 연결을 통해 원격 서버에서 명령을 실행합니다

## 카테고리
명령 실행

## 사용법
\`\`\`
/ssh:exec [connectionId] [command] [--cwd path] [--timeout seconds]
\`\`\`

## 매개변수
- \`connectionId\` (필수) - 사용할 연결 ID
- \`command\` (필수) - 실행할 명령어
- \`--cwd\` (선택) - 작업 디렉토리
- \`--timeout\` (선택, 기본값: 60) - 타임아웃(초)

## 예시
- \`/ssh:exec conn_123456 "ls -la"\`
- \`/ssh:exec conn_123456 "ps aux" --cwd /home/ubuntu\`
- \`/ssh:exec conn_123456 "tail -f /var/log/syslog" --timeout 300\`

## 반환값
명령 실행 결과와 출력을 반환합니다.

## 관련 명령어
- [list-files](./list-files.md) - 파일 목록
- [read](./read.md) - 파일 읽기
- [write](./write.md) - 파일 쓰기
`,

  'read.md': `# read

## 설명
SSH 연결을 통해 원격 서버의 파일을 읽습니다

## 카테고리
파일 조작

## 사용법
\`\`\`
/ssh:read [connectionId] [path] [--encoding utf8]
\`\`\`

## 매개변수
- \`connectionId\` (필수) - 사용할 연결 ID
- \`path\` (필수) - 읽을 파일 경로
- \`--encoding\` (선택, 기본값: utf8) - 파일 인코딩

## 예시
- \`/ssh:read conn_123456 /home/ubuntu/config.txt\`
- \`/ssh:read conn_123456 /var/log/syslog --encoding utf8\`
- \`/ssh:read conn_123456 /etc/hosts\`

## 반환값
파일 내용을 반환합니다.

## 관련 명령어
- [write](./write.md) - 파일 쓰기
- [list-files](./list-files.md) - 파일 목록
- [exec](./exec.md) - 원격 명령 실행
`,

  'write.md': `# write

## 설명
SSH 연결을 통해 원격 서버에 파일을 씁니다

## 카테고리
파일 조작

## 사용법
\`\`\`
/ssh:write [connectionId] [path] [content] [--encoding utf8]
\`\`\`

## 매개변수
- \`connectionId\` (필수) - 사용할 연결 ID
- \`path\` (필수) - 저장할 파일 경로
- \`content\` (필수) - 파일 내용
- \`--encoding\` (선택, 기본값: utf8) - 파일 인코딩

## 예시
- \`/ssh:write conn_123456 /home/ubuntu/output.txt "Hello World!"\`
- \`/ssh:write conn_123456 /tmp/test.txt "Test content" --encoding utf8\`
- \`/ssh:write conn_123456 /var/log/custom.log "Log entry"\`

## 반환값
파일 쓰기 성공 메시지를 반환합니다.

## 관련 명령어
- [read](./read.md) - 파일 읽기
- [list-files](./list-files.md) - 파일 목록
- [exec](./exec.md) - 원격 명령 실행
`,

  'init.md': `# init

## 설명
SSH MCP 환경을 초기화하여 .sshenv 설정 파일을 생성합니다

## 카테고리
환경 설정

## 사용법
\`\`\`
/ssh:init [--path .] [--force] [--addGitignore]
\`\`\`

## 매개변수
- \`--path\` (선택, 기본값: ".") - .sshenv 파일을 생성할 경로
- \`--force\` (선택, 기본값: false) - 기존 파일 덮어쓰기 여부
- \`--addGitignore\` (선택, 기본값: true) - .gitignore에 .sshenv 추가 여부

## 예시
- \`/ssh:init\`
- \`/ssh:init --path /custom/path\`
- \`/ssh:init --force --addGitignore false\`

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

## 관련 명령어
- [connect](./connect.md) - SSH 서버 연결
- [README](./README.md) - 모든 명령어 설명
`,

  'generate-g.md': `# generate-g

## 설명
Gemini CLI용 SSH 명령어 TOML 파일들을 자동으로 생성합니다

## 카테고리
도구 관리

## 사용법
\`\`\`
/ssh:generate-g [--path ~/.gemini/commands/ssh] [--force]
\`\`\`

## 예시
- \`/ssh:generate-g\`
- \`/ssh:generate-g --path /custom/path/ssh\`
- \`/ssh:generate-g --force\`

## 관련 명령어
- [init](./init.md) - SSH 환경 초기화
- [README](./README.md) - 모든 명령어 설명
`,

  'README.md': `# SSH MCP Commands Guide

SSH MCP 서버의 모든 명령어를 설명합니다.

## 환경 설정
- [init](./init.md) - SSH 환경 초기화 (.sshenv 파일 생성)
- [generate-g](./generate-g.md) - Gemini CLI용 명령어 생성

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
- \`ssh_generate_gemini\` → generate-g
`
};

// Gemini CLI용 SSH 명령어 템플릿
export const geminiCommandTemplates = {
  'connect.toml': `description="SSH를 통해 원격 서버에 연결"
prompt = """
---
allowed-tools: [mcp__ssh-mcp__ssh_connect, Read, Write]
description: "SSH를 통해 원격 서버에 연결"
---

# /ssh:connect - SSH Server Connection

## Purpose
SSH를 통해 원격 서버에 안전하게 연결하고 세션을 관리합니다.

## Usage
\`\`\`
/ssh:connect [host] [username] [--port 22] [--auth password|key|agent]
\`\`\`

## Arguments
- \`host\` (필수) - 서버 호스트명 또는 IP 주소
- \`username\` (필수) - SSH 사용자명  
- \`--port\` - SSH 포트 (기본값: 22)
- \`--auth\` - 인증 방식 (password, key, agent)
- \`--privateKey\` - 개인키 파일 경로
- \`--passphrase\` - 개인키 암호구문
- \`--useAgent\` - SSH 에이전트 사용 여부

## Execution
1. SSH 연결 매개변수 검증 및 준비
2. 지정된 인증 방식으로 서버 연결 시도
3. 연결 성공 시 connectionId 생성 및 반환
4. 연결 정보를 세션에 저장하여 관리
5. 연결 상태 및 오류 처리

## Claude Code Integration
- Uses mcp__ssh-mcp__ssh_connect for secure connection establishment
- Leverages Read for configuration file processing
- Applies Write for connection logging and session management
- Maintains secure credential handling and session tracking

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
"""
`,

  'disconnect.toml': `description="활성화된 SSH 연결을 안전하게 해제"
prompt = """
---
allowed-tools: [mcp__ssh-mcp__ssh_disconnect, Read]
description: "활성화된 SSH 연결을 안전하게 해제"
---

# /ssh:disconnect - SSH Connection Termination

## Purpose
활성화된 SSH 연결을 안전하게 해제하고 리소스를 정리합니다.

## Usage
\`\`\`
/ssh:disconnect [connectionId] [--all] [--force]
\`\`\`

## Arguments
- \`connectionId\` (필수) - 해제할 연결의 ID
- \`--all\` - 모든 활성 연결 해제
- \`--force\` - 강제 연결 해제 (응답 대기 없음)

## Execution
1. 연결 ID 유효성 검증 및 상태 확인
2. 활성 세션 및 프로세스 정리
3. 안전한 연결 종료 및 리소스 해제
4. 연결 상태 업데이트 및 로그 기록
5. 정리 결과 및 상태 보고

## Claude Code Integration
- Uses mcp__ssh-mcp__ssh_disconnect for secure connection termination
- Leverages Read for connection status verification
- Maintains proper session cleanup and resource management
- Ensures graceful disconnection with error handling

## 예시
\`\`\`json
{
  "connectionId": "conn_123456"
}
\`\`\`

## 반환값
연결 해제 성공 메시지를 반환합니다.
"""
`,

  'list-connections.toml': `description="현재 활성화된 모든 SSH 연결 목록을 조회"
prompt = """
---
allowed-tools: [mcp__ssh-mcp__ssh_list_connections, Read]
description: "현재 활성화된 모든 SSH 연결 목록을 조회"
---

# /ssh:list-connections - Active SSH Connections

## Purpose
현재 활성화된 모든 SSH 연결의 상태와 정보를 조회하고 관리합니다.

## Usage
\`\`\`
/ssh:list-connections [--status active|inactive|all] [--format table|json]
\`\`\`

## Arguments
- \`--status\` - 연결 상태 필터 (active, inactive, all)
- \`--format\` - 출력 형식 (table, json)
- \`--detail\` - 상세 정보 포함 여부

## Execution
1. 현재 세션의 모든 연결 상태 스캔
2. 연결별 상태 및 메타데이터 수집
3. 필터 조건 적용 및 정렬
4. 지정된 형식으로 결과 포맷팅
5. 연결 통계 및 요약 정보 제공

## Claude Code Integration
- Uses mcp__ssh-mcp__ssh_list_connections for connection enumeration
- Leverages Read for connection metadata processing
- Maintains comprehensive connection state tracking
- Provides formatted output with filtering options

## 예시
\`\`\`json
{}
\`\`\`

## 반환값
활성 연결 목록, 상태 정보, 연결 통계를 포함한 연결 보고서를 반환합니다.
"""
`,

  'list-files.toml': `description="SSH 연결을 통해 원격 서버의 파일 목록을 조회"
prompt = """
---
allowed-tools: [mcp__ssh-mcp__ssh_list_files, Read]
description: "SSH 연결을 통해 원격 서버의 파일 목록을 조회"
---

# /ssh:list-files - SSH List Files

## Purpose
SSH 연결을 통해 원격 서버의 디렉토리 파일 목록을 조회합니다.

## Usage
\`\`\`
/ssh:list-files [connectionId] [path]
\`\`\`

## Arguments
- \`connectionId\` (필수) - 사용할 연결 ID
- \`path\` (선택, 기본값: ".") - 조회할 디렉토리 경로

## Execution
1. 연결 ID 유효성 검증 및 상태 확인
2. 지정된 경로의 파일 시스템 탐색
3. 파일 및 디렉토리 정보 수집
4. 권한, 크기, 수정일 등 메타데이터 포함
5. 구조화된 파일 목록 반환

## Claude Code Integration
- Uses mcp__ssh-mcp__ssh_list_files for remote file enumeration
- Leverages Read for file metadata processing
- Maintains secure file system access
- Provides comprehensive file listing with details

## 예시
\`\`\`json
{
  "connectionId": "conn_123456",
  "path": "/home/ubuntu"
}
\`\`\`

## 반환값
디렉토리 파일 목록과 상세 정보를 반환합니다.
"""
`,

  'exec.toml': `description="SSH 연결을 통해 원격 서버에서 명령을 실행"
prompt = """
---
allowed-tools: [mcp__ssh-mcp__ssh_execute_command, Read, Write]
description: "SSH 연결을 통해 원격 서버에서 명령을 실행"
---

# /ssh:exec - SSH Exec - 원격 명령 실행

## Purpose
SSH 연결을 통해 원격 서버에서 명령을 실행하고 결과를 반환합니다.

## Usage
\`\`\`
/ssh:exec [connectionId] [command] [--cwd path] [--timeout seconds]
\`\`\`

## Arguments
- \`connectionId\` (필수) - 사용할 연결 ID
- \`command\` (필수) - 실행할 명령어
- \`--cwd\` (선택) - 작업 디렉토리
- \`--timeout\` (선택, 기본값: 60) - 타임아웃(초)

## Execution
1. 연결 ID 유효성 검증 및 상태 확인
2. 명령어 실행 환경 준비 및 설정
3. 원격 서버에서 명령 실행
4. 실시간 출력 스트림 처리
5. 실행 결과 및 종료 코드 반환

## Claude Code Integration
- Uses mcp__ssh-mcp__ssh_execute_command for remote command execution
- Leverages Read for command output processing
- Applies Write for command logging and result storage
- Maintains secure command execution with proper error handling

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
"""
`,

  'read.toml': `description="SSH 연결을 통해 원격 서버의 파일을 읽기"
prompt = """
---
allowed-tools: [mcp__ssh-mcp__ssh_read_file, Read]
description: "SSH 연결을 통해 원격 서버의 파일을 읽기"
---

# /ssh:read - SSH Read - 파일 읽기

## Purpose
SSH 연결을 통해 원격 서버의 파일을 안전하게 읽고 내용을 반환합니다.

## Usage
\`\`\`
/ssh:read [connectionId] [path] [--encoding utf8]
\`\`\`

## Arguments
- \`connectionId\` (필수) - 사용할 연결 ID
- \`path\` (필수) - 읽을 파일 경로
- \`--encoding\` (선택, 기본값: utf8) - 파일 인코딩

## Execution
1. 연결 ID 유효성 검증 및 상태 확인
2. 파일 경로 유효성 및 접근 권한 확인
3. 원격 파일 읽기 및 내용 검증
4. 지정된 인코딩으로 내용 디코딩
5. 파일 내용 및 메타데이터 반환

## Claude Code Integration
- Uses mcp__ssh-mcp__ssh_read_file for secure file reading
- Leverages Read for file content processing
- Maintains proper file access permissions
- Ensures secure file transfer with error handling

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
"""
`,

  'write.toml': `description="SSH 연결을 통해 원격 서버에 파일을 쓰기"
prompt = """
---
allowed-tools: [mcp__ssh-mcp__ssh_write_file, Read, Write]
description: "SSH 연결을 통해 원격 서버에 파일을 쓰기"
---

# /ssh:write - SSH Write - 파일 쓰기

## Purpose
SSH 연결을 통해 원격 서버에 파일을 안전하게 작성하고 저장합니다.

## Usage
\`\`\`
/ssh:write [connectionId] [path] [content] [--encoding utf8]
\`\`\`

## Arguments
- \`connectionId\` (필수) - 사용할 연결 ID
- \`path\` (필수) - 저장할 파일 경로
- \`content\` (필수) - 파일 내용
- \`--encoding\` (선택, 기본값: utf8) - 파일 인코딩

## Execution
1. 연결 ID 유효성 검증 및 상태 확인
2. 파일 경로 유효성 및 쓰기 권한 확인
3. 파일 내용 인코딩 및 전송 준비
4. 원격 서버에 파일 작성
5. 파일 쓰기 결과 및 상태 반환

## Claude Code Integration
- Uses mcp__ssh-mcp__ssh_write_file for secure file writing
- Leverages Read for file content validation
- Applies Write for file creation and modification
- Maintains secure file transfer with proper error handling

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
"""
`,

  'init.toml': `description="SSH MCP 환경을 초기화하여 .sshenv 설정 파일을 생성"
prompt = """
---
allowed-tools: [mcp__ssh-mcp__ssh_init, Read, Write]
description: "SSH MCP 환경을 초기화하여 .sshenv 설정 파일을 생성"
---

# /ssh:init - SSH Init - SSH 환경 초기화

## Purpose
SSH MCP 환경을 초기화하여 .sshenv 설정 파일을 생성하고 환경을 구성합니다.

## Usage
\`\`\`
/ssh:init [--path .] [--force] [--addGitignore]
\`\`\`

## Arguments
- \`--path\` (선택, 기본값: ".") - .sshenv 파일을 생성할 경로
- \`--force\` (선택, 기본값: false) - 기존 파일 덮어쓰기 여부
- \`--addGitignore\` (선택, 기본값: true) - .gitignore에 .sshenv 추가 여부

## Execution
1. 지정된 경로의 디렉토리 유효성 확인
2. 기존 .sshenv 파일 존재 여부 확인
3. .sshenv 템플릿 파일 생성
4. .gitignore 파일 업데이트 (옵션)
5. 초기화 완료 상태 및 파일 경로 반환

## Claude Code Integration
- Uses mcp__ssh-mcp__ssh_init for environment initialization
- Leverages Read for existing file checking
- Applies Write for configuration file creation
- Maintains proper file permissions and security

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
"""
`
};