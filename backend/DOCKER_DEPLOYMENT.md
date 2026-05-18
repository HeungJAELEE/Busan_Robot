# Docker Deployment Guide

Indy7 HMI의 백엔드 서비스는 Docker Compose로 실행할 수 있습니다. 현재 구성은 HMI 화면은 로컬에서 실행하고, MQTT/로봇 상태 수집/DB 저장/디지털 트윈/PLC/비전 서비스를 컨테이너로 분리하는 형태입니다.

Windows 현장 PC에서 실행할 때는 [`DOCKER_WINDOWS_DEPLOYMENT.md`](./DOCKER_WINDOWS_DEPLOYMENT.md)를 먼저 참고합니다.

## 1. 준비

Docker Desktop 또는 Docker Engine과 Docker Compose v2가 필요합니다.

```bash
cd /Users/leejaeheung/Documents/Busan_Project/Indy7_HMI_Clean/backend
cp .env.example .env
```

`.env`에서 현장 네트워크 값만 수정합니다.

```env
ROBOT_A_IP=192.168.3.7
ROBOT_B_IP=192.168.3.6
ROBOT_C_IP=192.168.3.5
ROBOT_NAME=NRMK-Indy7

MYSQL_HOST=192.168.3.141
MYSQL_PORT=3306
MYSQL_USER=guest
MYSQL_PASSWORD=guest1234
MYSQL_DATABASE=faictory_mes

PLC_IP=192.168.3.150
PLC_PORT=2000
PLC_MONITOR_IP=192.168.3.160
PLC_PROCESS_START_DEVICE=X11
PLC_PROCESS_STOP_DEVICE=X12
PLC_ROBOT_START_OUTPUT=Y160
ROBOT_START_DI=DI0
PLC_ROBOT_COMPLETE_DEVICE=X145
PLC_DONE_SIGNAL_MAP=PLC150:M1150,PLC130:M1130,PLC120:M1120
```

## 2. 기본 실행

```bash
docker compose build
docker compose up -d message_broker db_worker digital_twin
```

로봇 또는 PLC까지 실제 장비에 붙일 때만 아래 서비스를 추가로 켭니다.

```bash
docker compose up -d robot_controller plc_bridge
```

비전 서비스는 Torch/YOLO 의존성이 무겁고 카메라 장치가 필요하므로 별도 profile로 분리되어 있습니다.

```bash
docker compose --profile vision up -d vision_yolo
```

## 3. 로그와 종료

```bash
docker compose logs -f robot_controller
docker compose logs -f db_worker
docker compose ps
docker compose down
```

Mosquitto 데이터는 named volume에 남습니다. 완전히 초기화해야 할 때만 아래 명령을 씁니다.

```bash
docker compose down -v
```

## 4. Registry 이미지 업로드

이 저장소는 GitHub Container Registry(GHCR)로 Docker 이미지를 자동 업로드하도록 구성되어 있습니다.

main 브랜치에 push되면 GitHub Actions가 아래 이미지를 빌드하고 업로드합니다.

```text
ghcr.io/heungjaelee/indy7-hmi-robot-controller
ghcr.io/heungjaelee/indy7-hmi-db-worker
ghcr.io/heungjaelee/indy7-hmi-digital-twin
ghcr.io/heungjaelee/indy7-hmi-plc-bridge
ghcr.io/heungjaelee/indy7-hmi-vision-yolo
```

현장 PC에서 빌드 없이 업로드된 이미지만 받아 실행하려면 아래 명령을 사용합니다.

```bash
cd /Users/leejaeheung/Documents/Busan_Project/Indy7_HMI_Clean/backend
cp .env.example .env
docker compose -f docker-compose.registry.yml pull
docker compose -f docker-compose.registry.yml up -d message_broker db_worker digital_twin
docker compose -f docker-compose.registry.yml up -d robot_controller plc_bridge
```

비전 서비스는 필요할 때만 profile을 켭니다.

```bash
docker compose -f docker-compose.registry.yml --profile vision up -d vision_yolo
```

로컬 PC에 Docker Desktop이 설치되어 있고 수동 업로드를 하려면 아래처럼 실행할 수 있습니다.

```bash
cd /Users/leejaeheung/Documents/Busan_Project/Indy7_HMI_Clean/backend
docker login ghcr.io
REGISTRY=ghcr.io/heungjaelee TAG=latest PLATFORM=linux/amd64 ./scripts/docker-build-push.sh
```

## 5. 서비스 구성

| 서비스 | 역할 | 기본 포트/연결 |
|---|---|---|
| `message_broker` | MQTT Mosquitto 브로커 | `1883`, WebSocket `9001` |
| `robot_controller` | IndyDCP 로봇 상태 폴링 및 명령 브리지 | `ROBOT_A_IP`, `ROBOT_NAME` |
| `digital_twin` | 로봇 실시간 상태 WebSocket 브로드캐스트 | `8080` |
| `db_worker` | MQTT 이벤트를 MySQL에 저장 | `MYSQL_*` |
| `plc_bridge` | PLC 센서 폴링 | `PLC_IP`, `PLC_PORT` |
| `vision_yolo` | 카메라/YOLO 감지 | `CAMERA_DEVICE`, profile `vision` |

컨테이너 내부 MQTT 주소는 항상 `message_broker:1883`입니다. 외부 HMI나 다른 PC에서 MQTT에 붙을 때는 Docker가 실행 중인 PC의 IP와 `.env`의 `MQTT_PORT`를 사용합니다.

## 6. 로봇 여러 대 운용

현재 `robot_controller`는 `.env`의 `ROBOT_A_IP`를 기본 로봇으로 실행합니다. Robot A/B/C를 컨테이너로 동시에 분리하려면 `docker-compose.yml`에 `robot_controller_b`, `robot_controller_c` 서비스를 복제하고 아래 값만 다르게 지정하면 됩니다.

```yaml
environment:
  ROBOT_IP: ${ROBOT_B_IP:-192.168.3.6}
  ROBOT_NAME: Indy7
```

HMI에서 선택한 로봇으로 명령을 라우팅하는 기능은 프론트엔드 실시간 제어 로직과 같이 맞춰야 합니다.

## 7. 현장 주의사항

- Docker Desktop이 실행되는 PC가 `192.168.3.x` 로봇/PLC 대역에 실제로 접근 가능해야 합니다.
- 로봇 제어는 실시간성과 안전 정지가 중요하므로, 실제 생산 장비 연결 전에는 `message_broker`, `db_worker`, `digital_twin`만 먼저 띄워서 상태 수집 경로를 확인합니다.
- `vision_yolo`는 빌드 시간이 오래 걸릴 수 있습니다. 카메라가 없는 Mac/Windows 환경에서는 profile을 켜지 않는 것이 좋습니다.
- MySQL이 연결되지 않아도 `db_worker`는 죽지 않고 재시도/로그를 남기며, MQTT와 로봇 상태 수집은 독립적으로 유지됩니다.
