# Indy7 PC-HMI — Deep Space Command Center 🚀

이 프로그램은 Neuromeka(뉴로메카) 사의 **Indy7 협동 로봇**을 컴퓨터(PC)에서 조종하고 작업 지시를 내리기 위해 만들어진 리모컨(HMI) 소프트웨어입니다.
기존에 태블릿(안드로이드 앱)에서 짰던 작업 파일(JSON)을 컴퓨터로 가져와서 그대로 쓸 수 있고, 컴퓨터에서 편하게 수정한 뒤 다시 태블릿으로 보낼 수도 있는 **100% 양방향 호환성**을 자랑합니다.

> **테마**: "Deep Space Command Center" — 깊은 우주 사령실 컨셉의 다크 모드 UI.  
> 디자인 토큰(`presentation/ui/theme.py`)을 수정하면 앱 전체 스타일이 일괄 변경됩니다.

---

## 📦 1. 설치 및 실행

### 필수 라이브러리
```bash
pip install -r requirements.txt
```
| 라이브러리 | 역할 |
|---|---|
| `customtkinter` | 둥글고 예쁜 다크모드 UI 프레임워크 |
| `numpy` & `scipy` | 로봇 좌표 계산, 팔레타이징 수학 |
| `matplotlib` | 오실로스코프(실시간 그래프) |
| `paho-mqtt` & `pymysql` | MQTT 통신 / MES DB 연동 |
| `pyserial` | 시리얼 통신 |
| `pymcprotocol` | 미쓰비시 PLC (MC Protocol) |

### 실행 방법
```bash
# 전체 앱 (PLC/MQTT 없이 UI만 확인)
python3 run_ui_only.py

# 전체 앱 (PLC/MQTT/MES 연결 포함)
python3 main.py
```

---

## 🏗 2. 아키텍처

**Clean Architecture + DDD (Domain-Driven Design)** 기반으로 설계되었습니다.

```
Indy7_HMI_Clean/
├── core/                           # 핵심 비즈니스 로직
│   ├── domains/
│   │   ├── robot/                  # 로봇 제어 도메인
│   │   │   ├── communication/      # IndyDCP 클라이언트 매니저
│   │   │   └── use_cases/          # 로봇 제어 유스케이스 (JOG, 이동, F/T탐색)
│   │   ├── motion_management/      # 모션 엔티티
│   │   ├── plc_communication/      # PLC 통신 레포지토리
│   │   ├── mes_integration/        # MES DB 연동
│   │   └── teaching_management/    # 티칭 트리 파서
│   ├── application/use_cases/      # 팩토리 오케스트레이터
│   ├── kernel/                     # DI 컨테이너 (Microkernel)
│   └── shared/                     # 도메인 이벤트
├── presentation/ui/                # UI 계층 (화면)
│   ├── theme.py                    # 🎨 디자인 토큰 (색상/폰트 중앙 관리)
│   ├── main_window.py              # 메인 윈도우 (Page 1 ↔ Page 2 전환)
│   ├── robot_hmi/                  # Page 2: Teaching/Setting Mode
│   │   ├── robot_hmi_view.py       # HMI 메인 뷰 (트리, 팔레트, 에디터)
│   │   ├── editors/                # 노드별 속성 에디터
│   │   │   ├── motion_editors.py   # JOG, Move, MoveBy 에디터
│   │   │   ├── process_editors.py  # Pick/Place, 팔레타이징, 비전 에디터
│   │   │   ├── logic_editors.py    # If, Loop, Math, Switch 에디터
│   │   │   ├── io_monitor.py       # I/O 모니터링 패널
│   │   │   └── config_dialog.py    # 설정 다이얼로그
│   │   └── tools/                  # 🛠 현장 도구
│   │       ├── oscilloscope.py     # 실시간 오실로스코프
│   │       ├── palletizing_wizard.py # 팔레타이징 마법사 (6패턴)
│   │       └── auto_payload.py     # 페이로드 자동 측정
│   └── digital_twin/              # Page 1: Auto/Monitor Mode (3D 뷰어)
└── infrastructure/                # 인프라 계층
    ├── plc/                       # PLC 클라이언트
    ├── mqtt/                      # MQTT 클라이언트
    └── db/                        # MySQL MES 클라이언트
```

---

## 🚀 3. 주요 기능

### Page 1: Auto / Monitor Mode
- 다중 로봇 상태 모니터링 (Robot A/B/C)
- 3D 뷰어 기반 실시간 좌표 추적
- 전체 로봇 일괄 연결/해제

### Page 2: Setting / Teaching Mode
| 카테고리 | 기능 |
|---|---|
| **APK 기능** | Folder, Move Home, Joint Move, Frame Move, Move B/C, Pick, Place, DO, Wait, Wait DI, Loop, If (DI), Math, Comment, Stop, Call |
| **PC 제어** | Move By, AI, Wait AI, Switch, Force |
| **추가 기능** | Vision ★, Sync ★ *(★ = APK에 없는 PC 전용)* |
| **도구** | 오실로스코프, 팔레타이징 마법사, 페이로드 자동 측정 |

### 🧱 팔레타이징 (Pick & Place)
- **6가지 배치 패턴**: 일반(Z형), 지그재그, 교차(90°), S자형, 외곽나선, 중앙확산
- **마법사 ↔ 에디터 양방향 연동**: 마법사에서 디자인 → 에디터에 M/N/L, 크기, 간격, 패턴 자동 반영
- **P1 기반 자동 좌표 계산**: P2(행 끝), P3(열 끝), P4(층 끝) 자동 생성
- **3동작 시퀀스**: Approach → Target → Retract 자동 실행
- **3D 다단 적재**: L층 높이 적재 완벽 지원

### 🕹 JOG 제어
- Joint / Base / Tool 3모드 실시간 조그
- 속도 1~100단계 슬라이더
- 로봇 상태 실시간 표시 (정상/동작중/에러/비상정지/충돌)

### 🔧 현장 도구
- **오실로스코프**: 관절 각도 / Task 좌표 / F/T 센서를 10Hz 실시간 그래프로 시각화
- **팔레타이징 마법사**: 2D Canvas로 배열 시각 설계, 화살표로 방문 순서 표시
- **페이로드 자동 측정**: 3자세 루틴으로 툴 무게 & 무게중심 자동 계산

### 🔍 고급 로직
- **Stack Search**: F/T 센서 기반 적재물 높이 자동 탐색
- **Spiral Search**: 나선형 경로로 Peg-in-Hole 삽입 자동화

---

## 🎨 4. 디자인 시스템

**"Deep Space Command Center"** 테마 — `presentation/ui/theme.py`

| 토큰 | 값 | 용도 |
|---|---|---|
| `BG_BASE` | `#060311` (Midnight Ink) | 주 배경 |
| `BG_SURFACE` | `#161320` (Slate Deep) | 패널/카드 배경 |
| `ACCENT_PRIMARY` | `#5800fd` (Deep Violet) | 활성 버튼/하이라이트 |
| `TEXT_PRIMARY` | `#ffffff` (White Star) | 기본 텍스트 |
| `SUCCESS` | `#4CAF50` | 실행/ON |
| `DANGER` | `#F44336` | 정지/OFF |

> 색상이나 폰트를 바꾸고 싶으면 `theme.py`만 수정하면 앱 전체가 일괄 변경됩니다.

---

## 📁 5. 작업 파일 호환성

- Android APK (Conty) ↔ PC HMI 간 JSON 파일 100% 호환
- 저장 경로: `user_programs/{Robot_Name}/program.json`
- 불러오기/저장/복사/삭제 모두 지원

---

## 📝 License & Contact

부산 프로젝트 — Indy7 HMI Clean Architecture
