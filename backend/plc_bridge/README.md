# ⚙️ PLC Bridge 서비스

이 마이크로서비스는 공장 현장의 자동화 장비들, 특히 **미쓰비시(Mitsubishi) PLC**와의 통신을 전담하는 게이트웨이(Gateway)입니다. 로봇(Indy7)이 컨베이어 벨트나 레이저 센서의 신호를 알아야 할 때, 이 서비스가 중간에서 통역사 역할을 합니다.

---

## 🧩 아키텍처 및 통신 구조

```mermaid
flowchart LR
    PLC[미쓰비시 PLC<br/>MELSEC Q/R Series]
    MQTT((📮 MQTT Broker)) 
    
    subgraph PLC Bridge Service
        Poller[MC Protocol Poller]
        Q[State Machine]
        Pub[MQTT Publisher]
    end

    Poller -->|1. 100ms 간격 센서 읽기<br/>D1000, M100| PLC
    PLC -->|2. 데이터 응답| Poller
    Poller -->|3. 값의 변화(Rising Edge) 감지| Q
    Q -->|4. 이벤트 생성| Pub
    Pub -->|5. 퍼블리시<br/>'plc/sensor/part_arrived'| MQTT
```

## 🛠 주요 기능 (Features)

1. **MC Protocol (Type 3E) 통신**
   - 파이썬 라이브러리(`pymcprotocol`)를 활용해 미쓰비시 PLC의 데이터 레지스터(D-디바이스)나 비트 레지스터(M-디바이스)를 초고속으로 지속 폴링(Polling)합니다.

2. **이벤트 드리븐 (Event-Driven) 최적화**
   - 무식하게 센서값을 계속 뿌리지 않습니다. 내부 State Machine이 이전 값을 기억하고 있다가, 값이 0에서 1로 변하는 순간(Rising Edge)에만 MQTT 브로커로 "부품 도착!" 같은 명확한 이벤트를 날립니다.
   - 이를 통해 사내 네트워크의 통신 과부하를 막습니다.

3. **에러 자동 복구**
   - 공장 특성상 랜선이 뽑히거나 노이즈로 통신이 끊길 수 있습니다. 이 모듈은 소켓이 끊어지면 자동으로 재접속을 시도하는 예외처리가 내장되어 있습니다.

## 🚀 실행 및 테스트

```bash
# 개별 모듈 단위 테스트 (TDD)
cd backend/plc_bridge
python -m pytest tests/

# 수동 단독 실행 (로컬 테스트용)
python src/main.py
```
