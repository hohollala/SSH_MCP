// SSH MCP Server Environment Template - JSON Format
export const sshenvTemplateWithPassphrase = `{
  "_comments": {
    "description": "SSH MCP Server Configuration - JSON Format",
    "warning": "이 파일은 git에 커밋하지 마세요! (.gitignore에 추가 권장)",
    "usage": [
      "1. 서버별로 환경변수를 설정하세요",
      "2. MCP 명령어에서 \${VAR_NAME} 형태로 참조하세요",
      "3. 빈 문자열이나 null 값은 사용하지 않습니다"
    ],
    "example": {
      "host": "\${DEV_HOST}",
      "username": "\${DEV_USER}",
      "privateKeyPath": "\${DEV_KEY_PATH}"
    },
    "security_tips": [
      "1. 이 파일을 .gitignore에 추가하세요",
      "2. 가능하면 password 대신 key 인증을 사용하세요",
      "3. SSH Agent 사용을 권장합니다 (USE_AGENT=true)",
      "4. 파일 권한을 600으로 설정하세요: chmod 600 .sshenv"
    ]
  },
      "servers": {
      "development": {
        "DEV_HOST": "192.168.1.100",
        "DEV_USER": "ubuntu",
        "DEV_PASSWORD": "",
        "DEV_KEY_PATH": "~/.ssh/id_rsa",
        "DEV_PASSPHRASE": "",
        "DEV_PORT": 22
      },
      "staging": {
        "STAGING_HOST": "staging.example.com",
        "STAGING_USER": "deploy",
        "STAGING_PASSWORD": "",
        "STAGING_KEY_PATH": "~/.ssh/staging_key",
        "STAGING_PASSPHRASE": "",
        "STAGING_PORT": 22
      },
      "production": {
        "PROD_HOST": "prod.example.com",
        "PROD_USER": "admin",
        "PROD_PASSWORD": "",
        "PROD_KEY_PATH": "~/.ssh/prod_key",
        "PROD_PASSPHRASE": "",
        "PROD_PORT": 2222
      },
      "custom": {
        "MY_SERVER_HOST": "example.com",
        "MY_SERVER_USER": "user",
        "MY_SERVER_PASSWORD": "",
        "MY_SERVER_KEY_PATH": "~/.ssh/my_key",
        "MY_SERVER_PASSPHRASE": "",
        "MY_SERVER_PORT": 22
      }
    },
  "defaults": {
    "DEFAULT_TIMEOUT": 60,
    "DEFAULT_USE_AGENT": false,
    "DEFAULT_PORT": 22,
    "DEFAULT_ENCODING": "utf8"
  },
  "templates": {
    "basic_connection": {
      "host": "\${DEV_HOST}",
      "port": "\${DEV_PORT}",
      "username": "\${DEV_USER}",
      "privateKeyPath": "\${DEV_KEY_PATH}",
      "passphrase": "\${DEV_PASSPHRASE}"
    },
    "password_connection": {
      "host": "\${STAGING_HOST}",
      "port": "\${STAGING_PORT}",
      "username": "\${STAGING_USER}",
      "password": "\${STAGING_PASSWORD}"
    },
    "key_with_passphrase": {
      "host": "\${PROD_HOST}",
      "port": "\${PROD_PORT}",
      "username": "\${PROD_USER}",
      "privateKeyPath": "\${PROD_KEY_PATH}",
      "passphrase": "\${PROD_PASSPHRASE}"
    },
    "agent_connection": {
      "host": "\${PROD_HOST}",
      "port": "\${PROD_PORT}",
      "username": "\${PROD_USER}",
      "useAgent": true
    }
  }
}`;

export const sshenvTemplateWithoutPassphrase = `{
  "_comments": {
    "description": "SSH MCP Server Configuration - JSON Format",
    "warning": "이 파일은 git에 커밋하지 마세요! (.gitignore에 추가 권장)",
    "usage": [
      "1. 서버별로 환경변수를 설정하세요",
      "2. MCP 명령어에서 \${VAR_NAME} 형태로 참조하세요",
      "3. 빈 문자열이나 null 값은 사용하지 않습니다"
    ],
    "example": {
      "host": "\${DEV_HOST}",
      "username": "\${DEV_USER}",
      "privateKeyPath": "\${DEV_KEY_PATH}"
    },
    "security_tips": [
      "1. 이 파일을 .gitignore에 추가하세요",
      "2. 가능하면 password 대신 key 인증을 사용하세요",
      "3. SSH Agent 사용을 권장합니다 (USE_AGENT=true)",
      "4. 파일 권한을 600으로 설정하세요: chmod 600 .sshenv"
    ]
  },
  "servers": {
    "development": {
      "DEV_HOST": "192.168.1.100",
      "DEV_USER": "ubuntu",
      "DEV_PASSWORD": "",
      "DEV_KEY_PATH": "~/.ssh/id_rsa",
      "DEV_PORT": 22
    },
    "staging": {
      "STAGING_HOST": "staging.example.com",
      "STAGING_USER": "deploy",
      "STAGING_PASSWORD": "",
      "STAGING_KEY_PATH": "~/.ssh/staging_key",
      "STAGING_PORT": 22
    },
    "production": {
      "PROD_HOST": "prod.example.com",
      "PROD_USER": "admin",
      "PROD_PASSWORD": "",
      "PROD_KEY_PATH": "~/.ssh/prod_key",
      "PROD_PORT": 2222
    },
    "custom": {
      "MY_SERVER_HOST": "example.com",
      "MY_SERVER_USER": "user",
      "MY_SERVER_PASSWORD": "",
      "MY_SERVER_KEY_PATH": "~/.ssh/my_key",
      "MY_SERVER_PORT": 22
    }
  },
  "defaults": {
    "DEFAULT_TIMEOUT": 60,
    "DEFAULT_USE_AGENT": false,
    "DEFAULT_PORT": 22,
    "DEFAULT_ENCODING": "utf8"
  },
  "templates": {
    "basic_connection": {
      "host": "\${DEV_HOST}",
      "port": "\${DEV_PORT}",
      "username": "\${DEV_USER}",
      "privateKeyPath": "\${DEV_KEY_PATH}"
    },
    "password_connection": {
      "host": "\${STAGING_HOST}",
      "port": "\${STAGING_PORT}",
      "username": "\${STAGING_USER}",
      "password": "\${STAGING_PASSWORD}"
    },
    "agent_connection": {
      "host": "\${PROD_HOST}",
      "port": "\${PROD_PORT}",
      "username": "\${PROD_USER}",
      "useAgent": true
    }
  }
}`;

// Backward compatibility
export const sshenvTemplate = sshenvTemplateWithPassphrase;

export const gitignoreEntry = `
# SSH MCP Server
.sshenv
*.sshenv
.sshenv.json
`;