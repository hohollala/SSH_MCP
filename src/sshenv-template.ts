// SSH MCP Server Environment Template
export const sshenvTemplate = `# SSH MCP Server Configuration
# 이 파일은 git에 커밋하지 마세요! (.gitignore에 추가 권장)
# 
# 사용법:
# 1. 서버별로 환경변수를 설정하세요
# 2. MCP 명령어에서 \${VAR_NAME} 형태로 참조하세요
#
# 예시:
# {
#   "host": "\${DEV_HOST}",
#   "username": "\${DEV_USER}",
#   "password": "\${DEV_PASSWORD}"
# }

# =============================================================================
# 개발 서버 설정
# =============================================================================
DEV_HOST=192.168.1.100
DEV_USER=ubuntu
DEV_PASSWORD=
DEV_KEY_PATH=~/.ssh/id_rsa
DEV_PORT=22

# =============================================================================
# 스테이징 서버 설정  
# =============================================================================
STAGING_HOST=staging.example.com
STAGING_USER=deploy
STAGING_PASSWORD=
STAGING_KEY_PATH=~/.ssh/staging_key
STAGING_PORT=22

# =============================================================================
# 운영 서버 설정
# =============================================================================
PROD_HOST=prod.example.com
PROD_USER=admin
PROD_PASSWORD=
PROD_KEY_PATH=~/.ssh/prod_key
PROD_PORT=2222

# =============================================================================
# 기본 설정
# =============================================================================
DEFAULT_TIMEOUT=60
DEFAULT_USE_AGENT=false

# =============================================================================
# 사용자 정의 서버들
# =============================================================================
# MY_SERVER_HOST=
# MY_SERVER_USER=
# MY_SERVER_PASSWORD=
# MY_SERVER_KEY_PATH=
# MY_SERVER_PORT=22

# =============================================================================
# 보안 팁
# =============================================================================
# 1. 이 파일을 .gitignore에 추가하세요
# 2. 가능하면 password 대신 key 인증을 사용하세요
# 3. SSH Agent 사용을 권장합니다 (USE_AGENT=true)
# 4. 파일 권한을 600으로 설정하세요: chmod 600 .sshenv
`;

export const gitignoreEntry = `
# SSH MCP Server
.sshenv
*.sshenv
`;