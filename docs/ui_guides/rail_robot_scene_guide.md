# Indy7 Rail Robot View Guide

이 문서는 실제 레일 설비 사진을 기준으로 만든 **Page 1 디지털 트윈 UI 가이드**입니다. 현재 HMI의 JSON 실행 로직, 로봇 통신 코드, 티칭 데이터 구조는 변경하지 않고 화면 표현만 작업자 중심으로 정리합니다.

## 목적

기존 3D 화면은 그리드, 투명 박스, 궤적, 위험 존이 한 번에 보여 작업자가 로봇과 레일의 실제 위치 관계를 빠르게 보기 어렵습니다.

새 화면 방향은 다음처럼 단순화합니다. 이번 HTML 시안은 정적인 SVG가 아니라 Three.js 기반의 3D 가이드입니다.

- 기본 표시: 회색 테이블/레일, 흰색 6축 Indy7 형상 로봇 3대, 현재 TCP 위치, 장난감 자동차
- 기본 숨김: 전체 궤적, 위험 존 박스, 상세 그리드, 긴 텍스트 라벨
- 필요 시 표시: 안전 가이드 존, TCP trail, place watch zone, 싱귤러리티 점

## 공정 표현

```text
Robot A: 차체 결합
Robot B: 전면 유리창 조립
Robot C: 완성 장난감 자동차 픽업 및 양품 배출
```

작업자는 화면에서 제품 흐름을 먼저 보고, 필요할 때만 궤적/존/디버그 레이어를 켜는 방향이 적합합니다.

## 현장 치수 반영

```text
Robot A/B/C 간격: 1850mm
로봇 전면 rail 거리: 550mm
Robot A 기준 rail 끝단 여유: 약 1000mm
실제 이송 레일 폭: 약 100mm
```

화면 배치는 로봇 베이스를 뒤쪽에 두고, 레일/차량 작업면을 로봇 앞쪽으로 배치합니다. 즉 작업자가 볼 때 로봇이 앞 레일 위의 차량을 향해 내려오는 구도입니다. 넓은 흰색 알루미늄 프레임은 작업 테이블이고, 실제 검은 이송 레일은 약 100mm 폭으로 좁게 분리해서 표현합니다.

## 레일 기준 티칭 좌표

다음 파일에서 레일 쪽 작업 위치를 확인했습니다.

```text
260519robotc.7.json
- Robot C 첫 Pick target: X 549mm, Y -113mm, Z 100mm

20260519robotB1.7.json
- Robot B 전면 유리창 조립/레일 target: X 544mm, Y -374mm, Z 115mm
- 마지막 FrameMove 직전 press 경로: X 544mm, Y -374mm, Z 149mm
```

두 파일 모두 로봇 로컬 좌표에서 레일/제품 작업점이 X축 전방 약 540~550mm 근처에 있으므로, 3D 가이드에서는 로봇 전면 레일 오프셋을 약 0.55m로 두었습니다.

## 가이드 파일

- HTML 가이드: [rail_robot_scene_guide.html](./rail_robot_scene_guide.html)
- SVG 미리보기: [rail_robot_scene_guide.svg](./rail_robot_scene_guide.svg)

## 실제 앱 반영 방향

1. `Simple View`: 회색 스튜디오 배경에서 레일, 흰색 로봇, 장난감 자동차를 먼저 보여주는 작업자 기본 화면
2. `Debug View`: 안전 박스, 궤적, 위험 점, 그리드를 필요한 순간에 켜는 엔지니어 화면
3. `Mesh Layer`: Google Drive의 Indy7 모델 파일을 로컬에 받은 뒤 단순 링크 형상을 실제 mesh로 교체
4. `Layer Toggle`: Page 1과 Page 2에서 `Rail`, `Robot`, `TCP`, `Zone`, `Grid` 토글 제공
5. `Process Layer`: A/B/C 공정 라벨과 제품 상태를 함께 표시하여 실제 생산 동작과 맞춤

2026-05-19 기준 실제 앱 Page 1에는 경량 Matplotlib 3D 형태로 먼저 반영했습니다. 실시간 동기화를 유지하기 위해 STL/mesh 직접 로딩 대신 흰색 로봇 외피 스타일, 좁은 레일, 차량 도형, 은은한 가이드 존을 사용합니다.

## HTML 시안 실행 메모

`rail_robot_scene_guide.html`은 인터넷이 막힌 현장 PC에서도 열 수 있도록 필요한 Three.js 파일을 `vendor/three` 아래에 포함합니다. 현재 시안은 file URL에서 바로 열 수 있도록 classic script 방식의 `three@0.128.0`을 사용합니다. 최종 앱에 반영할 때도 외부 CDN 대신 프로젝트 내부 asset을 쓰는 구성이 안전합니다.

## Drive 모델 파일 처리 메모

Google Drive 폴더는 브라우저 UI로는 열리지만 터미널에서 파일 목록과 모델 확장자를 안정적으로 읽기 어렵습니다. 실제 모델 반영 시에는 Drive의 Indy7 모델 파일을 로컬 프로젝트 내부 또는 별도 asset 폴더로 받은 뒤 다음 중 하나로 연결하는 방식이 안전합니다.

- Python/Tk 유지: mesh를 단순화한 link geometry 또는 PNG/SVG sprite로 변환
- WebGL 전환: Three.js에서 `glTF/GLB/STL/DAE`를 직접 로딩
- ROS/URDF 기준: `indy-ros`의 URDF/mesh 구조를 참조해 collision/debug layer를 분리

현재 가이드안은 실제 앱에 바로 반영하기 전 사용자가 화면 방향을 결정하기 위한 시안입니다.
