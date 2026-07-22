# AMEVA-WoL 텔레그램 셋팅 및 사용 완벽 가이드 📖

이 가이드는 **텔레그램 앱 설치**, **봇(Bot) 생성**, **내 User ID 확인**, **AMEVA-WoL 실행 및 조종 방법**을 초보자도 쉽게 따라할 수 있도록 설명합니다.

> 🌐 **웹 HTML 버전으로 보기**: [docs/telegram_setup_guide.html](file:///c:/ameva/AMEVA-WoL/docs/telegram_setup_guide.html) (브라우저에서 열면 예쁜 디자인으로 볼 수 있습니다.)

---

## 1. 텔레그램(Telegram) 앱 설치하기 📱

텔레그램은 스마트폰이나 컴퓨터에서 명령어 패킷을 보낼 수 있는 메신저입니다.

- **스마트폰 (Android / iOS)**: Play 스토어 또는 App Store에서 **Telegram**을 검색하여 설치합니다.
- **PC (Windows / Mac / Linux)**: 공식 홈페이지 ([desktop.telegram.org](https://desktop.telegram.org))에서 PC용 텔레그램을 다운로드하여 설치합니다.
- 전화번호를 통해 회원가입을 진행합니다.

---

## 2. @BotFather로 텔레그램 봇 만들기 🤖

텔레그램 공식 봇 관리자 계정인 **@BotFather**를 통해 나만의 봇을 발급받습니다.

1. 텔레그램 앱 검색창에 `@BotFather`를 검색하고 클릭합니다 (파란색 공식 인증 마크 확인).
2. 대화창에 `/newbot` 명령어를 입력하고 전송합니다.
3. **봇의 이름(Name)**을 입력합니다. (예: `My Home Gateway`)
4. **봇의 아이디(Username)**를 입력합니다. 반드시 끝이 `bot`으로 끝나야 합니다. (예: `my_home_wol_bot`)
5. 생성이 완료되면 봇의 **HTTP API Token (토큰)**이 출력됩니다.

> ⚠️ **주의**: 발급받은 봇 토큰(`123456789:ABCdef...`)은 비밀번호입니다. 절대로 타인에게 보여주거나 외부에 공개하지 마세요!

---

## 3. 내 텔레그램 User ID (숫자 ID) 확인하기 🆔

나 외에 다른 사람이 내 봇을 조종하지 못하도록 내 고유 숫자 User ID를 등록해야 합니다.

1. 텔레그램 검색창에 `@userinfobot` 또는 `@raw_data_bot`을 검색합니다.
2. `/start`를 전송하면 답장으로 **Id: 123456789** 형태의 숫자가 출력됩니다. 이 숫자를 복사합니다.

---

## 4. AMEVA-WoL A-Z 자동 진단 스크립트 실행 🔍

AMEVA-WoL은 운영 체제, 파이썬 버전, 라이브러리 설치 상태, `.env` 토큰 유효성, User ID 숫자 검증, 네트워크 핑, 데이터 폴더 권한까지 **A부터 Z까지 자동으로 전수 점검**하고, 문제가 있는 항목마다 즉시 조치할 수 있는 해결 방법(Heuristic Fix)을 출력해주는 진단 스크립트를 제공합니다.

- **Termux / Linux (쉘 스크립트)**:
  ```bash
  bash scripts/check-environment.sh
  ```
- **Windows (파워쉘 스크립트)**:
  ```powershell
  powershell -ExecutionPolicy Bypass -File .\scripts\check-environment.ps1
  ```

---

## 5. AMEVA-WoL 환경설정 및 실행 🚀

### 1) `.env` 파일 작성
`AMEVA-WoL` 폴더 안에 `.env` 파일을 작성합니다:
```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ_ExampleToken
ALLOWED_USER_IDS=123456789
DEFAULT_BROADCAST=192.168.0.255
DEFAULT_WOL_PORT=9
LOG_LEVEL=INFO
DATA_DIR=./data
```

### 2) 자가 진단 명령어 실행
```bash
python -m ameva_wol --check-config
```

### 3) 게이트웨이 실행
- **기본 모드 (대기 모드)**:
  ```bash
  python -m ameva_wol
  ```
- **Always-On 모드 (5분 주기 자동 모니터링 & 자동 깨우기)**:
  ```bash
  python -m ameva_wol --always-on 5
  ```

---

## 5. 텔레그램 봇으로 컴퓨터 깨우기 ⚡

텔레그램에서 생성한 내 봇과의 대화창에 들어가 아래 명령어를 전송합니다:

1. **컴퓨터 등록 (`/add`)**:
   ```text
   /add desktop AA:BB:CC:DD:EE:01 192.168.0.100
   ```
2. **컴퓨터 켜기 (`/wake`)**:
   ```text
   /wake desktop
   ```
   *모든 등록 컴퓨터 켜기: `/wake all`*
3. **컴퓨터 켜짐/꺼짐 상태 확인 (`/status`)**:
   ```text
   /status desktop
   ```
4. **등록 목록 보기 (`/list`)**:
   ```text
   /list
   ```
