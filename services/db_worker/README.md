# 🗄 DB Worker 마이크로서비스

이 모듈은 로봇의 실시간 상태와 작업 완료 이력을 외부 MES 시스템(MySQL DB)으로 전송하는 독립적인 백그라운드 워커입니다. 
다른 모듈의 코드를 절대 참조하지 않는 무결성(Shared-Nothing) 구조를 가집니다.

## 🏗 폴더 구조 (OOD & TDD)
- `src/main.py`: 서비스 진입점 (MQTT 구독 시작)
- `src/domain/`: 데이터 정제 및 비즈니스 로직
- `src/infrastructure/`: PyMySQL 기반 데이터베이스 통신 및 MQTT 매니저
- `tests/`: `pytest`를 이용한 단위 테스트

## 🚀 개발 및 실행 방법
1. **VSCode DevContainer 환경**
   - 이 폴더를 VSCode로 열고 `Reopen in Container`를 실행하면 모든 파이썬 환경이 자동으로 세팅됩니다.
2. **테스트 실행 (TDD)**
   - 터미널에서 `pytest tests/` 입력
3. **단독 실행**
   - `python src/main.py`
