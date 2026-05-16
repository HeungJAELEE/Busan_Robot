# Json Robot Design Pattern

이 문서는 Indy7 HMI PC 프로그램에서 만든 Teaching 로직을 Neuromeka Conty/APK 계열 JSON으로 안정적으로 저장하고, 다시 로봇 또는 APK에 이식하기 위한 설계 규칙이다.

핵심 목표는 하나다.

> 사람이 UI로 만들든, AI가 자연어를 해석해서 만들든, 같은 로직이면 같은 JSON 구조가 나오게 한다.

## 1. Golden Rules

반드시 지켜야 하는 규칙이다.

1. `program`은 실행 순서와 트리 구조만 담당한다.
2. `moveList`는 Move 명령의 속도, TCP, refFrame, waypoint 참조를 담당한다.
3. `wpList`는 실제 좌표 `q/p` 값을 담당한다.
4. 모든 `program` 노드는 `id`, `pId`, `type`, `enable`을 가져야 한다.
5. `pId`는 반드시 먼저 존재하는 부모 노드의 `id`를 가리켜야 한다.
6. 화면의 mm 입력은 JSON 저장 시 meter로 변환한다.
7. `If / Elif / Else` 체인은 같은 부모 아래에서 연속 배치한다.
8. `Wait DI`와 `If DI`를 혼동하지 않는다.
9. Pick/Place 직접 좌표는 `target.point.q/p`가 비어 있으면 안 된다.
10. 상대/특수 Move `104/105/106`은 원본 `moveList/wpList` 보존을 우선한다.

## 2. Top Level Schema

표준 파일 구조:

```json
{
  "info": {"name": "program_name"},
  "wpList": [],
  "program": [],
  "moveList": []
}
```

권장 기본 노드:

```json
{
  "type": 999,
  "enable": true,
  "pId": 0,
  "id": 1,
  "toolInfo": [],
  "palletInfo": [],
  "visionInfo": {"useVision": false},
  "collisionPolicy": {"policy": 0, "time": 2},
  "conveyorConfigInfo": {"conveyorConfig": []}
}
```

```json
{
  "type": 2,
  "enable": true,
  "pId": 0,
  "id": 2,
  "varList": []
}
```

## 3. Unit Rules

좌표와 TCP 단위가 제일 중요하다.

| 항목 | UI 입력 | JSON 저장 |
|---|---:|---:|
| X/Y/Z 위치 | mm | m |
| TCP X/Y/Z | mm | m |
| 접근/후퇴 거리 | mm | m |
| Rx/Ry/Rz | deg | deg |
| 관절 q1~q6 | deg | deg |
| Wait 시간 | sec | sec |

예시:

```text
화면 X 206mm, Y -370mm, Z 120mm
JSON p = [0.206, -0.370, 0.120, rx, ry, rz]
```

```text
화면 TCP Z 210mm
JSON tcp = [0, 0, 0.21, 0, 0, 0]
```

## 4. Common Node Pattern

모든 `program` 노드는 아래 공통 필드를 가진다.

```json
{
  "type": 20,
  "enable": true,
  "pId": 0,
  "id": 3
}
```

트리 구조는 `pId`로 만든다.

```json
[
  {"type": 20, "id": 3, "pId": 0, "enable": true, "count": 6},
  {"type": 28, "id": 4, "pId": 3, "enable": true, "time": 1, "diList": [{"idx": 10, "value": 1}]},
  {"type": 29, "id": 5, "pId": 3, "enable": true, "diList": [{"idx": 11, "value": 1}]},
  {"type": 201, "id": 6, "pId": 5, "enable": true}
]
```

위 구조는 다음 뜻이다.

```text
Loop
  Wait DI10 ON
  If DI11 ON
    Pick
```

## 5. Move Pattern

Move 계열은 `program` 노드에 좌표를 직접 넣지 않는다.

지원 타입:

| Type | 의미 | 안정성 |
|---:|---|---|
| 102 | JointMove | 안정 |
| 103 | FrameMove | 안정 |
| 104 | Move B 계열/상대 Move 샘플 | 주의 |
| 105 | Move By 계열/상대 Move 샘플 | 주의 |
| 106 | Move C/특수 Move 샘플 | 주의 |

### 5.1 Move 3-Part Reference

실행 노드:

```json
{
  "type": 103,
  "enable": true,
  "pId": 0,
  "name": "move_approach",
  "id": 3
}
```

Move 설정:

```json
{
  "type": 103,
  "name": "move_approach",
  "intpl": 1,
  "tcp": [0, 0, 0.21, 0, 0, 0],
  "refFrame": {"type": 1, "tref": [0, 0, 0, 0, 0, 0]},
  "boundary": {"velLevel": 3, "accLevel": 3},
  "blendOpt": {"processLoop": false, "constant": false},
  "wpList": [{"t": 2, "id": 0}]
}
```

실제 좌표:

```json
{
  "id": 0,
  "type": 0,
  "tBase": 0,
  "stopBlend": true,
  "blendRadius": 0,
  "name": "move_approach-00",
  "q": [10, -20, -90, 0, -70, 10],
  "p": [0.206, -0.370, 0.120, 0, 180, 0]
}
```

검증 규칙:

```text
program.name == moveList.name
moveList.wpList[].id exists in wpList[].id
```

## 6. Pick / Place Pattern

Pick/Place는 `program` 노드 안에 `target`을 직접 가진다.

| Type | 의미 |
|---:|---|
| 201 | Pick |
| 202 | Place |

### 6.1 Direct Point Pick

```json
{
  "type": 201,
  "enable": true,
  "pId": 5,
  "id": 6,
  "toolId": 0,
  "sensName": "",
  "approach": {
    "direction": 0,
    "distance": 0.05,
    "boundary": {"velLevel": 3, "accLevel": 3},
    "waitTime": 0,
    "waitFor": {"type": 0, "time": 0}
  },
  "retract": {
    "direction": 1,
    "distance": 0.05,
    "boundary": {"velLevel": 3, "accLevel": 3},
    "waitTime": 0,
    "waitFor": {"type": 0, "time": 0}
  },
  "target": {
    "type": 0,
    "boundary": {"velLevel": 3, "accLevel": 3},
    "pallet": {},
    "point": {
      "q": [10, -20, -90, 0, -70, 10],
      "p": [0.206, -0.370, 0.120, 0, 180, 0]
    },
    "refFrame": {"type": 1, "tref": [0, 0, 0, 0, 0, 0]},
    "tcp": [0, 0, 0.21, 0, 0, 0]
  }
}
```

주의:

```text
approach.distance 0.05 = 50mm
retract.distance 0.05 = 50mm
target.point.p[0:3]이 모두 0이면 실제 좌표 누락 가능성이 높다.
```

## 7. Palletizing Pattern

팔레트 Pick/Place는 `target.type = 1`로 저장한다.

Pick/Place 노드:

```json
{
  "type": 201,
  "enable": true,
  "pId": 5,
  "id": 6,
  "toolId": 0,
  "target": {
    "type": 1,
    "boundary": {"velLevel": 3, "accLevel": 3},
    "pallet": {
      "palletId": "PLT_RED",
      "currentIdxVar": {"value": "Red", "type": 10}
    },
    "point": {"q": [], "p": []},
    "refFrame": {"type": 1, "tref": [0, 0, 0, 0, 0, 0]},
    "tcp": [0, 0, 0.21, 0, 0, 0]
  }
}
```

Program Settings의 팔레트 정의:

```json
{
  "id": "PLT_RED",
  "name": "PLT_RED",
  "m": 2,
  "n": 2,
  "l": 4,
  "points": [
    {"p": [0.100, -0.600, 0.120, 0, 180, 0]},
    {"p": [0.200, -0.600, 0.120, 0, 180, 0]},
    {"p": [0.100, -0.500, 0.120, 0, 180, 0]},
    {"p": [0.100, -0.600, 0.220, 0, 180, 0]}
  ]
}
```

의미:

```text
m = X/row 방향 개수
n = Y/column 방향 개수
l = layer 수
points[0] = P1
points[1] = P2
points[2] = P3
points[3] = P4 또는 layer 기준점
```

카운터 변수 `Red`가 0이면 첫 슬롯, 1이면 두 번째 슬롯으로 이동한다.

## 8. DI / DO Pattern

### 8.1 Wait DI

대기 게이트다. 조건이 맞을 때까지 기다린다.

```json
{
  "type": 28,
  "enable": true,
  "pId": 3,
  "id": 4,
  "time": 1,
  "diList": [{"idx": 10, "value": 1}]
}
```

실전 의미:

```text
DI10이 ON이면 통과
DI10이 OFF이면 대기 또는 N.G
```

### 8.2 If DI

선택 분기다. 조건이 맞으면 자식을 실행한다.

```json
{
  "type": 29,
  "enable": true,
  "pId": 3,
  "id": 5,
  "diList": [{"idx": 11, "value": 1}]
}
```

### 8.3 Elif DI

바로 앞의 `If DI` 또는 `Elif DI`와 같은 부모 아래에 연속으로 배치한다.

```json
[
  {"type": 29, "id": 5, "pId": 3, "enable": true, "diList": [{"idx": 11, "value": 1}]},
  {"type": 30, "id": 6, "pId": 3, "enable": true, "diList": [{"idx": 12, "value": 1}]},
  {"type": 30, "id": 7, "pId": 3, "enable": true, "diList": [{"idx": 13, "value": 1}]}
]
```

실전 추천:

```text
DI10 = Wait gate
DI11 = Red 선택
DI12 = Blue 선택
DI13 = Green 선택
```

Page2/Page3 시뮬레이션에서는 `대기 DI 적용` 또는 `대기 DI` 버튼으로 `type=28`만 자동 적용하고, `type=29/30` 선택 DI는 사용자가 직접 켜는 것이 안전하다.

### 8.4 Smart DO

```json
{
  "type": 4,
  "enable": true,
  "pId": 3,
  "id": 8,
  "doList": [{"idx": 13, "value": 1}]
}
```

### 8.5 EndTool DO

```json
{
  "type": 6,
  "enable": true,
  "pId": 3,
  "id": 9,
  "endtoolDoList": [{"idx": 0, "value": 1}]
}
```

## 9. Variable / If / Loop Pattern

### 9.1 Variable Initialize

```json
{
  "type": 2,
  "enable": true,
  "pId": 0,
  "id": 2,
  "varList": [
    {"name": "Red", "type": 1, "value": 0},
    {"name": "Blue", "type": 1, "value": 0},
    {"name": "Green", "type": 1, "value": 0}
  ]
}
```

### 9.2 Variable Increment

```json
{
  "type": 3,
  "enable": true,
  "pId": 5,
  "id": 10,
  "varList": [{"name": "Red", "type": 1, "value": "Red+1"}]
}
```

### 9.3 If Var

```json
{
  "type": 24,
  "enable": true,
  "pId": 5,
  "id": 11,
  "cond": {
    "left": {"type": 10, "value": "Red"},
    "right": {"type": 1, "value": 0},
    "op": 0
  }
}
```

Operator:

| op | 의미 |
|---:|---|
| 0 | `==` |
| 1 | `!=` |
| 2 | `>` |
| 3 | `>=` |
| 4 | `<` |
| 5 | `<=` |

### 9.4 Loop

유한 반복:

```json
{"type": 20, "enable": true, "pId": 0, "id": 3, "count": 6}
```

무한 반복:

```json
{"type": 20, "enable": true, "pId": 0, "id": 3, "count": -1}
```

Page3 로봇 점검 Data수집 모드에서는 내부 무한 루프를 한 Cycle에서 1회전만 실행하고, 외부 목표 반복 수로 전체 반복을 관리한다.

## 10. Tool Pattern

`Tool Command(type=40)`는 단순 DO가 아니다. `Program Settings(type=999)`의 `toolInfo` 매핑을 참조한다.

Tool command node:

```json
{
  "type": 40,
  "enable": true,
  "pId": 3,
  "id": 20,
  "toolCmd": {"toolId": 0, "cmdId": 2}
}
```

Tool info:

```json
{
  "id": 0,
  "name": "Gripper",
  "appType": 1,
  "onTarget": true,
  "toolCommand": [
    {"id": 2, "name": "Hold", "commType": 1, "postwait": 1, "doMap": [{"idx": 0, "value": 0}, {"idx": 1, "value": 1}]},
    {"id": 3, "name": "Release", "commType": 1, "postwait": 1, "doMap": [{"idx": 0, "value": 1}, {"idx": 1, "value": 0}]}
  ]
}
```

주의:

```text
Robot A/B/C의 toolInfo가 다르면 같은 Pick이라도 실제 DO 동작이 달라질 수 있다.
```

## 11. Real Example: Robot A Color Branch

목표:

```text
Loop 6회
DI10이 ON일 때만 한 사이클 진입
DI11 ON이면 Red 팔레트 실행
DI12 ON이면 Blue 팔레트 실행
DI13 ON이면 Green 팔레트 실행
각 색상은 카운터가 0이면 1번 슬롯, 1이면 2번 슬롯
작업 후 카운터 +1
```

권장 트리:

```text
Variables
  Red = 0
  Blue = 0
  Green = 0
Loop count=6
  Wait DI10=ON
  If DI11=ON
    If Red == 0
      Pick Red slot 1
      Place target
      Red = Red + 1
    Elif Red == 1
      Pick Red slot 2
      Place target
      Red = Red + 1
  If DI12=ON
    If Blue == 0
      Pick Blue slot 1
      Place target
      Blue = Blue + 1
    Elif Blue == 1
      Pick Blue slot 2
      Place target
      Blue = Blue + 1
  If DI13=ON
    If Green == 0
      Pick Green slot 1
      Place target
      Green = Green + 1
    Elif Green == 1
      Pick Green slot 2
      Place target
      Green = Green + 1
```

중요:

```text
DI10은 Wait DI다.
DI11/12/13은 If DI다.
시뮬레이션에서 전체 DI를 모두 켜면 모든 색상이 한 번에 조건 TRUE가 될 수 있다.
테스트할 때는 대기 DI만 자동 적용하고 선택 DI는 직접 켠다.
```

## 12. Stable Command Table

| Type | 기능 | 권장 상태 |
|---:|---|---|
| 1 | Stop | 안정 |
| 2 | Variables | 안정 |
| 3 | Var Assign / Math | 안정 |
| 4 | Smart DO | 안정 |
| 5 | Smart AO | 안정 |
| 6 | EndTool DO | 안정 |
| 20 | Loop | 안정 |
| 21 | Loop Break | 안정 |
| 22 | Wait Time | 안정 |
| 23 | Wait For Var | 안정 |
| 24 | If Var | 안정 |
| 25 | Elif Var | 안정 |
| 26 | Else | 안정 |
| 28 | Wait DI | 안정 |
| 29 | If DI | 안정 |
| 30 | Elif DI | 안정 |
| 40 | Tool Command | toolInfo 필요 |
| 41 | Tool Sensing | toolInfo 필요 |
| 100 | Home | 안정 |
| 102 | JointMove | 안정 |
| 103 | FrameMove | 안정 |
| 104 | Move B / relative sample | 주의 |
| 105 | Move By / relative sample | 주의 |
| 106 | Move C / special sample | 주의 |
| 200 | Pick Group | 안정 |
| 201 | Pick | 안정 |
| 202 | Place | 안정 |
| 250 | Speed Ratio | 안정 |
| 302 | Takt Time | 안정 |
| 50 | Python | PC/제조사 확장 주의 |
| 300 | Conveyor | 현장 매핑 확인 |
| 400 | Detect | PC 확장 주의 |
| 401 | Retrieve | PC 확장 주의 |
| 901 | Call | PC 확장 주의 |
| 902 | Force | PC 확장 주의 |
| 903 | Comment | 실행 의미 없음 |

## 13. Save-Time Validation Checklist

저장 전 또는 AI 생성 후 반드시 검사한다.

```text
[ ] JSON root에 info/program/wpList/moveList가 있는가
[ ] type=999, type=2가 있는가
[ ] 모든 program 노드가 id/pId/type/enable을 갖는가
[ ] pId가 존재하는 부모를 가리키는가
[ ] Move program.name과 moveList.name이 일치하는가
[ ] moveList.wpList id가 wpList에 존재하는가
[ ] Pick/Place target.point.p/q가 비어 있지 않은가
[ ] 팔레트 target.pallet.palletId가 palletInfo에 존재하는가
[ ] mm 입력이 m로 저장됐는가
[ ] TCP X/Y/Z도 m로 저장됐는가
[ ] If/Elif/Else 체인이 같은 부모에서 연속 배치됐는가
[ ] Wait DI와 If DI 용도가 분리됐는가
[ ] Tool Command를 쓰면 toolInfo 매핑이 있는가
[ ] 104/105/106은 원본 moveList 보존 또는 별도 검증이 됐는가
```

## 14. AI Teaching Output Contract

AI가 자연어를 JSON으로 바꿀 때는 바로 JSON을 만들지 말고, 먼저 아래 중간 표현을 만든 뒤 JSON으로 변환한다.

```yaml
robot: Robot A
tcp_mm: [0, 0, 210, 0, 0, 0]
variables:
  Red: 0
  Blue: 0
  Green: 0
logic:
  - loop: 6
    children:
      - wait_di: {idx: 10, value: 1, timeout_s: 1}
      - if_di: {idx: 11, value: 1}
        children:
          - if_var: {name: Red, op: "==", value: 0}
            children:
              - pick: {x_mm: 206, y_mm: -370, z_mm: 120}
              - place: {x_mm: 552, y_mm: -99, z_mm: 129}
              - assign: {name: Red, value: "Red+1"}
```

변환 규칙:

```text
wait_di -> type 28
if_di -> type 29
elif_di -> type 30
if_var -> type 24
elif_var -> type 25
else -> type 26
assign -> type 3
pick -> type 201
place -> type 202
move_joint -> type 102 + moveList/wpList
move_frame -> type 103 + moveList/wpList
```

## 15. Practical Test Flow

현장 적용 전 권장 순서:

```text
1. PC 프로그램에서 작성
2. 저장
3. JSON 호환성 검사 OK/WARN 확인
4. Page2 Play 가상 확인
5. Page3 로봇 점검 Data수집에서 대기 DI만 적용
6. 선택 DI를 하나씩 켜면서 분기 확인
7. 실제 로봇 저속 1회 실행
8. 생산 속도 적용
```

2026-05-16 기준 전수 점검 결과:

```text
대상: /Users/leejaeheung/Documents/Busan_Project/학습 파일 모음
파일: 225개
OK: 198개
WARN: 27개
ERROR: 0개
상세: docs/conty_json_roundtrip_audit_20260516.md
```
