# Factory MES / PLC / Robot 연동 기준

이 문서는 `youngjinsgithub/factory_mes`의 `*_Process_pendant.py` 흐름을 기준으로, Indy7 HMI가 현장 PLC 중심 구조에 붙는 방식을 정리한 문서입니다.

## 1. 제어권 기준

현장 제어권은 PLC가 가집니다.

- Robot은 PLC와 물리 배선된 DI를 보고 움직입니다.
- Vision 카메라 프로그램은 PLC와 직접 통신합니다.
- HMI/Backend는 PLC 신호를 읽어서 MQTT 이벤트와 DB 기록으로 남깁니다.
- HMI/Backend가 기본값으로 PLC 출력이나 Robot 시작 신호를 강제로 쓰지 않습니다.

## 2. 사용자 신호 맵

| 구분 | 신호 | 의미 | 처리 방향 |
|---|---|---|---|
| 공정 시작 | `X11` | PLC 공정 시작 입력 | PLC Bridge가 읽고 `plc/process/start` 발행 |
| 공정 정지 | `X12` | PLC 공정 정지 입력 | PLC Bridge가 읽고 `plc/process/stop` 발행 |
| 로봇 시작 | `Y160 -> Robot DI0` | PLC 출력이 로봇 DI0으로 물리 연결 | HMI는 쓰지 않고 구조만 기록 |
| 로봇 완료 | `X145` | 로봇 완료 신호가 PLC로 들어온 입력 | PLC Bridge가 읽고 `plc/robot/complete` 발행 |
| 공정 A 종료 | `M1150` | PLC150/A 완료 DB 기록 기준 | `plc/process/done`, `station_id=PLC150` |
| 공정 B 종료 | `M1130` | PLC130/B 완료 DB 기록 기준 | `plc/process/done`, `station_id=PLC130` |
| 공정 C 종료 | `M1120` | PLC120/C 완료 DB 기록 기준 | `plc/process/done`, `station_id=PLC120` |

`factory_mes` 참고 코드에서는 `M1150/M1130/M1120`이 관제 PLC `192.168.3.160:2000`에 모이는 것으로 되어 있습니다. 실제 현장에서 각 PLC에 분산되어 있으면 `.env`의 `PLC_MONITOR_IP` 또는 `PLC_DONE_SIGNAL_MAP`을 현장 구조에 맞게 바꾸면 됩니다.

## 3. Vision 카메라 Git 기준 신호

참고 저장소: `https://github.com/youngjinsgithub/factory_mes`

실행 파일:

- `mes/A_Process_pendant.py`
- `mes/B_Process_pendant.py`
- `mes/C_Process_pendant.py`

확인된 핵심 흐름:

| 파일 | 접속 PLC | 읽기 | 쓰기 | DB 기록 기준 |
|---|---|---|---|---|
| `A_Process_pendant.py` | PLC150, PLC160 | PLC160 `M1150` | PLC150 `M250` RED, `M260` BLUE | `M1150` 상승 엣지 |
| `B_Process_pendant.py` | PLC140, PLC160 | PLC140 `B150`, PLC160 `M1130` | PLC140 `M250` OK, `M260` NG | `M1130` 상승 엣지 |
| `C_Process_pendant.py` | PLC120, PLC160 | PLC120 `B130`, PLC160 `M1120` | PLC120 `M250` OK, `M260` NG | `M1120` 상승 엣지 |

Vision 쪽에서 PLC에 결과를 직접 쓰므로, HMI 백엔드는 그 값을 중복으로 쓰지 않습니다.

Vision PC의 DB 표준 설정은 아래 값입니다.

```python
DB_CONFIG = {
    'host': '192.168.3.141',
    'port': 3306,
    'user': 'guest',
    'password': 'guest1234',
    'db': 'faictory_mes',
    'charset': 'utf8mb4',
    'autocommit': True,
    'use_unicode': True,
    'init_command': "SET NAMES utf8mb4"
}
```

`factory_mes` 원본은 `localhost/root/1234` 형태로 되어 있으므로, Vision PC 설치 스크립트가 위 값으로 자동 패치합니다.

## 4. MQTT 이벤트 규격

PLC Bridge는 신호 변화만 MQTT로 발행합니다.

| Topic | 발생 조건 | 예시 payload |
|---|---|---|
| `plc/process/start` | `X11` OFF -> ON | `{"signal":"process_start","device":"X11","edge":"rising"}` |
| `plc/process/stop` | `X12` OFF -> ON | `{"signal":"process_stop","device":"X12","edge":"rising"}` |
| `plc/robot/complete` | `X145` OFF -> ON | `{"signal":"robot_complete","device":"X145","edge":"rising"}` |
| `plc/process/done` | `M1150/M1130/M1120` OFF -> ON | `{"signal":"process_done","station_id":"PLC150","device":"M1150"}` |
| `plc/signal` | 감시 신호 값 변경 | 모든 변경 상태 공통 로그 |

DB Worker는 위 이벤트 중 시작/정지/로봇완료/공정완료를 `plc_process_events` 테이블에 저장합니다.

## 5. Docker 환경 변수

`backend/.env`에서 현장 주소를 조정합니다.

```env
PLC_IP=192.168.3.150
PLC_PORT=2000

PLC_PROCESS_IP=192.168.3.150
PLC_PROCESS_PORT=2000

PLC_MONITOR_IP=192.168.3.160
PLC_MONITOR_PORT=2000

PLC_PROCESS_START_DEVICE=X11
PLC_PROCESS_STOP_DEVICE=X12
PLC_ROBOT_START_OUTPUT=Y160
ROBOT_START_DI=DI0
PLC_ROBOT_COMPLETE_DEVICE=X145
PLC_DONE_SIGNAL_MAP=PLC150:M1150,PLC130:M1130,PLC120:M1120
PLC_SCAN_INTERVAL_SEC=0.1
```

## 6. 실행

```bash
cd /Users/leejaeheung/Documents/Busan_Project/Indy7_HMI_Clean/backend
docker compose up -d --build plc_bridge db_worker
docker compose logs -f plc_bridge db_worker
```

정상 로그 예시:

```text
PLC 신호 맵
공정 시작: X11
공정 정지: X12
로봇 시작 배선: PLC Y160 -> Robot DI0
로봇 완료: X145
종료 DB: PLC150 M1150
종료 DB: PLC130 M1130
종료 DB: PLC120 M1120
```

## 7. 운영 주의사항

- `Y160`은 PLC 출력이고 Robot DI0으로 물리 연결된 신호입니다. HMI에서 직접 쓰지 않는 것이 기본입니다.
- 시작/정지/완료/종료 신호는 상승 엣지 기준으로 기록합니다.
- Vision 프로그램은 자체적으로 PLC에 OK/NG 또는 차종 신호를 씁니다. 같은 비트를 HMI에서 동시에 쓰면 충돌 위험이 있습니다.
- DB가 꺼져 있어도 PLC Bridge는 MQTT 이벤트를 계속 발행합니다. DB Worker는 DB가 연결되면 자동으로 기록합니다.
