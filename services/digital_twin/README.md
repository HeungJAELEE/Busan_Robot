# 🌍 Digital Twin 마이크로서비스

이 모듈은 로봇의 실시간 관절 데이터 스트림을 구독하여, 3D 뷰어(Three.js, Unity, WebGL 등) 클라이언트들에게 뿌려주는 중계 서버 역할을 합니다.
가벼운 웹소켓(Websocket) 통신을 전담하며, 로봇 코어의 부하 없이 다수의 관전자를 수용할 수 있게 해줍니다.

## 🏗 폴더 구조 (OOD & TDD)
- `src/main.py`: 서비스 진입점 (웹소켓 서버 오픈 및 MQTT 구독)
- `src/domain/`: 클라이언트 세션 관리 및 데이터 포맷팅
- `src/infrastructure/`: Websockets 비동기 엔진 및 MQTT 매니저
- `tests/`: `pytest`를 이용한 단위 테스트

## 🚀 개발 및 실행 방법
1. **VSCode DevContainer 환경**
   - 이 폴더를 VSCode로 열고 `Reopen in Container`를 실행하면 모든 파이썬 환경이 자동으로 세팅됩니다.
2. **테스트 실행 (TDD)**
   - 터미널에서 `pytest tests/` 입력
3. **단독 실행**
   - `python src/main.py`
