# SSH MCP Server - JSON 환경변수 설정 가이드

## 개요

SSH MCP 서버는 이제 JSON 형식의 환경변수 파일을 지원합니다. 기존 `.env` 형식과 함께 JSON 형식도 사용할 수 있어 더 구조적이고 관리하기 쉬운 설정이 가능합니다.

## JSON 환경변수 파일 구조

### 기본 구조

```json
{
  "_comments": {
    "description": "SSH MCP Server Configuration - JSON Format",
    "warning": "이 파일은 git에 커밋하지 마세요!",
    "usage": [
      "1. 서버별로 환경변수를 설정하세요",
      "2. MCP 명령어에서 ${VAR_NAME} 형태로 참조하세요",
      "3. 빈 문자열이나 null 값은 사용하지 않습니다"
    ]
  },
  "servers": {
    "development": {
      "DEV_HOST": "192.168.1.100",
      "DEV_USER": "ubuntu",
      "DEV_KEY_PATH": "~/.ssh/id_rsa",
      "DEV_PORT": 22
    },
    "production": {
      "PROD_HOST": "prod.example.com",
      "PROD_USER": "admin",
      "PROD_KEY_PATH": "~/.ssh/prod_key",
      "PROD_PORT": 2222
    }
  },
  "defaults": {
    "DEFAULT_TIMEOUT": 60,
    "DEFAULT_USE_AGENT": false,
    "DEFAULT_PORT": 22
  }
}
```

## 사용 방법

### 1. JSON 환경변수 파일 생성

```bash
# ssh_init 도구를 사용하여 템플릿 생성
mcp_ssh_init --force
```

또는 직접 `.sshenv` 파일을 JSON 형식으로 작성합니다.

### 2. 환경변수 사용

MCP 명령어에서 `${VARIABLE_NAME}` 형태로 참조:

```json
{
  "host": "${DEV_HOST}",
  "username": "${DEV_USER}",
  "privateKeyPath": "${DEV_KEY_PATH}",
  "port": "${DEV_PORT}"
}
```

### 3. 서버별 설정

각 환경별로 서버 설정을 그룹화할 수 있습니다:

- `development`: 개발 환경
- `staging`: 스테이징 환경  
- `production`: 운영 환경
- `custom`: 사용자 정의 환경

## 주요 특징

### 1. 자동 포맷 감지

파일이 `{`로 시작하고 `}`로 끝나면 자동으로 JSON 형식으로 인식합니다.

### 2. 빈 값 처리

- 빈 문자열(`""`)은 저장하지 않습니다
- 빈 값이 있으면 환경변수 치환 시 원본 문자열을 유지합니다

### 3. 데이터 타입 지원

- `string`: 문자열 값
- `number`: 숫자 값 (문자열로 변환됨)
- `boolean`: 불린 값 (문자열로 변환됨)

### 4. 중첩 구조

`servers`와 `defaults` 섹션에서 모든 변수를 자동으로 추출합니다.

## 사용 예제

### 개발 서버 연결

```json
{
  "name": "ssh_connect",
  "arguments": {
    "host": "${DEV_HOST}",
    "username": "${DEV_USER}",
    "privateKeyPath": "${DEV_KEY_PATH}"
  }
}
```

### 운영 서버 연결

```json
{
  "name": "ssh_connect", 
  "arguments": {
    "host": "${PROD_HOST}",
    "username": "${PROD_USER}",
    "privateKeyPath": "${PROD_KEY_PATH}",
    "port": "${PROD_PORT}"
  }
}
```

## 보안 주의사항

1. `.sshenv` 파일을 `.gitignore`에 추가하세요
2. 가능하면 비밀번호 대신 SSH 키를 사용하세요
3. 파일 권한을 `600`으로 설정하세요: `chmod 600 .sshenv`
4. 민감한 정보는 별도의 보안 저장소를 사용하세요

## 기존 형식과의 호환성

JSON 형식과 기존 `KEY=VALUE` 형식 모두 지원합니다. 파일 내용에 따라 자동으로 파싱 방식이 결정됩니다.

## 문제 해결

### 환경변수를 찾을 수 없음

```
Environment variable not found: TEST_HOST
```

해결방법: `.sshenv` 파일에 해당 변수가 정의되어 있고 빈 값이 아닌지 확인하세요.

### JSON 파싱 오류

```
Invalid JSON in .sshenv file
```

해결방법: JSON 문법을 확인하고 올바른 형식으로 수정하세요.