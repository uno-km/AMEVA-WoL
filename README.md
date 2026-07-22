# AMEVA-WoL ⚡

> **Lightweight, Secure, Telegram-Controlled Wake-on-LAN Gateway for Termux & Linux**  
> **안드로이드 Termux 및 저사양 리눅스를 위한 초경량·고보안 텔레그램 Wake-on-LAN 게이트웨이**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.10%2B-green.svg)](https://www.python.org/)

---

## 📚 텔레그램 봇 설정 & 초보자 가이드

텔레그램 앱 설치부터 봇 생성, User ID 확인, 실행 방법까지 쉽게 작성된 가이드 문서입니다. 아래 링크를 눌러 확인하세요:

- 🌐 **웹 HTML 가이드 (추천)**: [docs/telegram_setup_guide.html](file:///c:/ameva/AMEVA-WoL/docs/telegram_setup_guide.html) (브라우저로 열면 예쁜 디자인으로 볼 수 있습니다.)
- 📝 **마크다운 가이드**: [docs/telegram_setup_guide.md](file:///c:/ameva/AMEVA-WoL/docs/telegram_setup_guide.md)

---

## 📌 개요 (Overview)

**AMEVA-WoL**은 구형 안드로이드 스마트폰(Samsung Galaxy S7 등 Termux 환경) 및 저사양 리눅스 노트북/서버에서 **루트(Root) 권한 없이** 24시간 작동하는 텔레그램 조종 Wake-on-LAN (WoL) 게이트웨이입니다.

사용자가 텔레그램으로 메세지를 전송하면, 게이트웨이가 공유기 내부 네트워크(LAN)로 102바이트 UDP Magic Packet을 브로드캐스트하여 원격으로 컴퓨터를 켭니다.

---

## ✨ 핵심 기능 (Key Features)

- 🚀 **초경량 저전력**: 유휴 CPU 점유율 < 0.1%, 메모리 사용량 ~25–40 MB.
- 🛡️ **포트 포워딩 / 웹서버 없음**: 텔레그램 롱 폴링(Long Polling) 방식만 사용하여 공유기 포트포워딩이나 공인 IP, DDNS가 일절 필요 없습니다.
- 🔐 **강력한 보안**:
  - `ALLOWED_USER_IDS`에 지정된 텔레그램 사용자만 명령 가능.
  - 셀 명령어 주입 방지 (`shell=False`).
  - 봇 토큰 및 개인정보 자동 마스킹 및 예외 안전 처리.
  - 슬라이딩 윈도우 Rate Limiting 적용.
- 💾 **원자적(Atomic) 데이터 저장**: `devices.json` 저장 시 임시 파일 후 `fsync()` 교체로 데이터 손상 방지.
- 🔒 **단일 인스턴스 파일 락**: 프로세스 중복 실행 자동 방지 (`.lock`).
- 🕒 **Always-On 상시 감시 모드**: 설정한 주기마다 컴퓨터 켜짐 상태(Ping)를 확인하고, 꺼져있으면 자동으로 깨우는 기능.

---

## 🚀 빠른 시작 가이드 (Quick Start)

### 1. 설치 및 의존성 구성
```bash
git clone https://github.com/uno-km/AMEVA-WoL.git
cd AMEVA-WoL

# 가상환경 생성 및 활성화
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 패키지 설치
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. `.env` 파일 작성
```bash
cp .env.example .env
chmod 600 .env
```
`.env` 파일을 열고 텔레그램 봇 토큰과 사용자 ID를 입력합니다:
```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ_ExampleToken
ALLOWED_USER_IDS=123456789
DEFAULT_BROADCAST=192.168.0.255
DEFAULT_WOL_PORT=9
LOG_LEVEL=INFO
DATA_DIR=./data
```

### 3. A-Z 시스템 자가 진단 스크립트 실행 (System Audit)

AMEVA-WoL에 포함된 진단 스크립트를 실행하면 Python 버전, 라이브러리, `.env` 토큰 유효성, User ID, 데이터 디렉토리 권한, 네트워크 연결을 A부터 Z까지 점검하고 부족한 항목의 해결 방법(Heuristic Fix)을 자동으로 안내합니다:

- **Termux / Linux**: `bash scripts/check-environment.sh`
- **Windows**: `powershell -ExecutionPolicy Bypass -File .\scripts\check-environment.ps1`

```bash
# Python 내장 자가 진단도 지원됩니다:
python -m ameva_wol --check-config
```

### 4. 실행
- **기본 대기 모드**:
  ```bash
  python -m ameva_wol
  ```
- **Always-On 감시 모드 (5분 주기)**:
  ```bash
  python -m ameva_wol --always-on 5
  ```

---

## 📖 텔레그램 주요 명령어

| 명령어 | 설명 | 사용 예시 |
| :--- | :--- | :--- |
| `/start` | 게이트웨이 인증 상태 및 안내 | `/start` |
| `/how` | 상세 사용 설명서 | `/how` |
| `/id` | 내 텔레그램 User ID 확인 | `/id` |
| `/add` | 컴퓨터 등록 | `/add desktop AA:BB:CC:DD:EE:01 192.168.0.100` |
| `/wake` | 컴퓨터 깨우기 (WoL 전송) | `/wake desktop` 또는 `/wake all` |
| `/status` | 컴퓨터 켜짐 상태 확인 (Ping) | `/status desktop` 또는 `/status all` |
| `/list` | 등록된 장치 목록 보기 | `/list` |
| `/remove` | 등록된 장치 삭제 | `/remove desktop` |

---

## 📱 Termux / 안드로이드 부팅 설정

Termux 실행 및 Termux:Boot 자동 부팅 설정은 [docs/telegram_setup_guide.html](file:///c:/ameva/AMEVA-WoL/docs/telegram_setup_guide.html) 또는 `termux/start-ameva-wol.sh` 파일 주석을 참고하세요.

---

## 📄 라이선스 (License)

본 프로젝트는 **MIT License**를 따릅니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참고하세요.
