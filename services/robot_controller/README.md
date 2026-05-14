# 🤖 Robot Controller 마이크로서비스

이 모듈은 Indy7 HMI 아키텍처의 심장부로, 실제 로봇과 IndyDCP 소켓을 유지하는 100% 독립적인 에이전트입니다.
로봇의 실시간 상태를 10Hz로 읽어내어 브로드캐스트하며, 외부(UI, 비전 등)에서 MQTT로 들어오는 이동 명령을 수행합니다.

## 🏗 폴더 구조 (OOD & TDD)
- `src/main.py`: 서비스 진입점 (명령 수신 및 10Hz 폴링 루프)
- `src/domain/`: 모션 계획, 경로 검증(Singularity 회피 등) 로직
- `src/infrastructure/`: `indy_utils` 기반 소켓 통신 및 MQTT 매니저
- `tests/`: `pytest`를 이용한 단위 테스트

## 🚀 개발 및 실행 방법
1. **VSCode DevContainer 환경**
   - 이 폴더를 VSCode로 열고 `Reopen in Container`를 실행하면 모든 파이썬 환경이 자동으로 세팅됩니다.
2. **테스트 실행 (TDD)**
   - 터미널에서 `pytest tests/` 입력
3. **단독 실행**
   - `python src/main.py`
