# Indy7 Rail Robot View Guide

이 문서는 실제 레일 설비 사진을 기준으로 만든 **결정용 UI 가이드**입니다. 현재 HMI의 동작 로직, JSON 실행 로직, 로봇 통신 코드는 변경하지 않습니다.

## 목적

기존 3D 화면은 그리드, 투명 박스, 궤적, 위험 존이 한 번에 보여 작업자가 로봇과 레일의 실제 위치 관계를 빠르게 보기 어렵습니다.

새 화면 방향은 다음처럼 단순화합니다.

- 기본 표시: 회색 테이블/레일, 흰색 Indy7 로봇, 현재 TCP 위치, 단순 작업물
- 기본 숨김: 전체 궤적, 위험 존 박스, 상세 그리드, 긴 텍스트 라벨
- 필요 시 표시: 안전 가이드 존, TCP trail, place watch zone, 싱귤러리티 점

## 현장 치수 반영

```text
Robot A/B/C 간격: 1850mm
로봇 전면 rail 거리: 500mm
Robot A 기준 rail 끝단 여유: 약 1000mm
```

## 가이드 파일

- HTML 가이드: [rail_robot_scene_guide.html](./rail_robot_scene_guide.html)
- SVG 미리보기: [rail_robot_scene_guide.svg](./rail_robot_scene_guide.svg)

## 실제 앱 적용 방향

1. `Simple View`: 회색 스튜디오 배경에서 레일, 로봇, 작업물만 보여주는 작업자 기본 화면
2. `Debug View`: 현재처럼 안전 박스, 궤적, 위험 점, 그리드를 모두 켜는 엔지니어 화면
3. `Mesh Layer`: Google Drive의 Indy7 모델 파일을 로컬에 받은 뒤 단순 링크 형상을 실제 mesh로 교체
4. `Layer Toggle`: Page 1과 Page 2에서 `Rail`, `Robot`, `TCP`, `Zone`, `Grid` 토글 제공

## Drive 모델 파일 처리 메모

Google Drive 폴더는 브라우저 UI로는 열리지만 터미널에서 파일 목록과 모델 확장자를 안정적으로 읽기 어렵습니다. 실제 모델 반영 시에는 Drive의 Indy7 모델 파일을 로컬 프로젝트 내부 또는 별도 asset 폴더로 받은 뒤 다음 중 하나로 연결하는 방식이 안전합니다.

- Python/Tk 유지: mesh를 단순화한 link geometry 또는 PNG/SVG sprite로 변환
- WebGL 전환: Three.js에서 `glTF/GLB/STL/DAE`를 직접 로딩
- ROS/URDF 기준: `indy-ros`의 URDF/mesh 구조를 참조해 collision/debug layer를 분리

현재 가이드안은 실제 앱에 바로 반영하기 전 사용자가 화면 방향을 결정하기 위한 시안입니다.
