# ⚙️ PLC Bridge 마이크로서비스

이 모듈은 공장 내부의 미쓰비시/LS PLC와 통신(`pymcprotocol` 등 활용)하여 센서 값을 읽거나 컨베이어 벨트를 제어하는 모듈입니다.
주요 레지스터를 폴링하다가 값이 변경되면 MQTT 채널에 이벤트를 발행(Publish)합니다.

## 🏗 폴더 구조 (OOD & TDD)
- `src/main.py`: 서비스 진입점 (PLC 폴링 루프 시작)
- `src/domain/`: 센서 데이터 검증 및 상태 전이 로직
- `src/infrastructure/`: PLC 소켓 통신 모듈 및 MQTT 매니저
- `tests/`: `pytest`를 이용한 단위 테스트

## 🚀 개발 및 실행 방법
1. **VSCode DevContainer 환경**
   - 이 폴더를 VSCode로 열고 `Reopen in Container`를 실행하면 모든 파이썬 환경이 자동으로 세팅됩니다.
2. **테스트 실행 (TDD)**
   - 터미널에서 `pytest tests/` 입력
3. **단독 실행**
   - `python src/main.py`
