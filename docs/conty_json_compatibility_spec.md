# Conty JSON Compatibility Spec

이 문서는 `/Users/leejaeheung/Documents/Busan_Project/학습 파일 모음`의 APK Teaching Pendant 원본 JSON 225개와 `/Users/leejaeheung/Documents/Busan_Project/indydcp_example_참고자료`의 제조사 PC 제어 예제를 기준으로 다시 정리한 PC 프로그램 호환 기준이다.

목표는 두 가지다.

1. APK에서 Teaching 완료 후 저장한 `.7.json`을 PC 프로그램에서 바로 읽고 실행/수정할 수 있어야 한다.
2. PC 프로그램에서 Teaching/편집 후 저장한 `.7.json`을 APK에 그대로 넣어도 동일한 의미로 동작해야 한다.

## 1. 검증 기준

- 분석 대상: APK 원본 JSON 225개
- 보조 기준: 제조사 제공 `JsonProgramComponent`, `IndyDCPClient.set_and_start_json_program`
- JSON 파싱 실패: 0건
- `program[].id` 중복: 0건
- `program[].pId` 부모 참조 오류: 0건
- `moveList[].wpList[].id -> wpList[].id` 참조 오류: 0건
- `program` 모션 노드와 `moveList` 연결 오류: 0건

따라서 APK 샘플 폴더를 PC 프로그램의 golden sample로 사용하고, 제조사 예제는 PC 생성 JSON과 로봇 전송 방식의 기준으로 사용한다.

## 2. 최상위 구조

실제 APK 파일의 최상위 구조는 대부분 다음과 같다.

```json
{
  "info": { "name": "program_name" },
  "wpList": [],
  "program": [],
  "moveList": []
}
```

관찰된 최상위 key 조합:

| key 조합 | 파일 수 | 비고 |
|---|---:|---|
| `info`, `wpList`, `program`, `moveList` | 197 | 표준 |
| `wpList`, `program`, `moveList` | 26 | `info` 없음 |
| `info`, `wpList`, `program`, `moveList`, `palletInfo` | 2 | root `palletInfo` 존재 |

호환 규칙:

- `info`가 없어도 로드해야 한다.
- root `palletInfo`가 있으면 저장 시 보존해야 한다.
- 새 파일 생성 시에는 `info`, `wpList`, `program`, `moveList`를 포함한다.
- PC 내부 전용 필드는 최상위에 추가하지 않는다.

## 3. 참조 규칙

### 3.1 프로그램 트리

`program[]`은 `id`와 `pId`로 트리 구조를 만든다.

```json
{ "id": 5, "type": 103, "pId": 4, "name": "m1", "enable": true }
```

호환 규칙:

- 기존 JSON을 저장할 때는 가능한 한 기존 `id`, `pId`, 노드 순서를 보존한다.
- 새 노드만 새 `id`를 발급한다.
- 부모가 삭제된 노드가 생기면 저장 전에 검증 오류로 막는다.

### 3.2 모션 참조

실제 APK 샘플에서는 `program[].moveListIdx`가 사용되지 않았다. 모션 노드는 `program[].name == moveList[].name`으로 연결된다.

```json
{
  "program": [
    { "type": 103, "id": 5, "pId": 4, "name": "m1", "enable": true }
  ],
  "moveList": [
    { "type": 103, "name": "m1", "wpList": [{ "t": 2, "id": 0 }] }
  ],
  "wpList": [
    { "id": 0, "q": [0, 0, 0, 0, 0, 0], "p": [0, 0, 0, 0, 0, 0] }
  ]
}
```

호환 규칙:

- 모션 로드 우선순위는 `name -> moveList.name`이다.
- `moveListIdx`는 외부 변형 파일 대응용 fallback으로만 둔다.
- 같은 이름의 `moveList`가 여러 개 있으면 검증 오류로 표시한다.
- `wpList` 좌표는 `moveList[].wpList[].id -> root wpList[].id`로 찾는다.
- 모션 노드의 좌표를 `program[]`에 직접 `q/p`로 저장하지 않는다.

## 4. 좌표와 단위

실제 APK 파일 기준:

- `q`: joint angle, degree
- `p[0:3]`: task position, meter
- `p[3:6]`: task orientation, degree
- `approach.distance`, `retract.distance`: meter
- UI 표시 단위가 mm이면 로드 시 `m -> mm`, 저장 시 `mm -> m`을 명시적으로 변환한다.

금지:

- `distance > 1.0`이면 mm로 간주하는 휴리스틱에 의존하지 않는다.
- 내부 UI 값과 APK JSON 값을 같은 필드에 단위 구분 없이 섞지 않는다.

## 5. 실제 APK 타입 사전

아래 표는 225개 APK 샘플에서 실제 관찰된 타입과 제조사 `JsonProgramComponent` 타입 상수를 함께 반영한 기준이다.

| type | 의미 | 주요 필드 | 출현 노드 | 지원 정책 |
|---:|---|---|---:|---|
| 1 | Stop | `enable`, `id`, `pId`, `type` | 7 | Stop으로 지원, JointMove로 해석 금지 |
| 2 | 변수 선언 | `varList` | 219 | 지원 |
| 3 | 변수 대입/연산 | `varList` | 54 | 지원 필요 |
| 4 | SmartDO | `doList` | 216 | 지원 |
| 5 | SmartAO | `aoList` | 2 | 지원 |
| 6 | EndToolDO | `endtoolDoList` | 2 | 지원 |
| 20 | Loop | `count` | 198 | 지원 |
| 21 | LoopBreak | 없음 | 34 | 지원 |
| 22 | Wait Time | `time` | 198 | 지원 |
| 23 | WaitFor | `time`, `cond` | 2 | 지원 필요 |
| 24 | If 변수 조건 | `cond` | 54 | 지원 |
| 25 | Elif 변수 조건 | `cond` | 28 | 지원 |
| 26 | Else | 없음 | 16 | 지원 |
| 28 | WaitDI | `time`, `diList`, `endtoolDiList` | 94 | 지원 |
| 29 | If(DI) | `diList`, `endtoolDiList` | 113 | 지원 |
| 30 | Elif(DI) | `diList`, `endtoolDiList` | 48 | 지원 |
| 40 | ToolCommand | `toolCmd` | 2 | 지원 필요 |
| 41 | ToolSensing | `toolCmd`, `sensName` | 3 | 지원 필요 |
| 100 | Home | 없음 | 261 | 지원 |
| 102 | JointMove | `name` + `moveList` | 239 | 지원 |
| 103 | FrameMove | `name` + `moveList` | 226 | 지원 |
| 104 | Move 계열 | `name` + `moveList`, `wpListOrigin` | 2 | 파서 추가 필요 |
| 105 | Move 계열 | `name` + `moveList`, `wpListOrigin`, `offset` | 14 | 파서 추가 필요 |
| 200 | PickGroup | `groupName` | 16 | 지원 |
| 201 | Pick | `toolId`, `approach`, `retract`, `target` | 293 | 지원 |
| 202 | Place | `toolId`, `approach`, `retract`, `target` | 302 | 지원 |
| 250 | SpeedRatio 계열 | `prgSpdRatio` | 2 | Call로 해석 금지 |
| 302 | TaktTime/care 계열 | `careTackTime` | 2 | Force로 해석 금지 |
| 999 | Program Settings | `toolInfo`, `palletInfo`, `visionInfo`, `collisionPolicy` | 219 | 지원 |

제조사 예제에만 명확히 존재하고 APK 샘플에서는 아직 관찰되지 않은 타입:

| type | 제조사 기준 의미 | 지원 정책 |
|---:|---|---|
| 50 | ExecPython | APK 호환 export는 사용자 확인 필요 |
| 101 | MoveZero | 로봇 native 실행 우선, 직접 실행은 별도 구현 |
| 106 | ShakeMove 계열 | raw 보존, 직접 실행 보류 |
| 300 | IndyCARE Count | raw 보존 또는 전용 지원 |
| 301 | IndyCARE Monitoring | raw 보존 또는 전용 지원 |

## 6. 현재 PC 코드에서 바로 고쳐야 할 타입 해석

현재 코드가 실제 APK 타입과 충돌하는 부분:

| 현재 해석 | 현재 type | 실제 APK 기준 | 수정 방향 |
|---|---:|---|---|
| Math | 21 | 21은 LoopBreak | Math는 3으로 저장/실행 |
| WaitFor | 30 | 23이 WaitFor, 30은 Elif(DI) | 30은 조건 체인의 Elif로 처리 |
| Comment | 40 | 40은 ToolCommand | Comment는 별도 검증 전 export 금지 또는 raw 보존 |
| Stop | 41 | 1이 Stop, 41은 ToolSensing | 41을 Stop으로 해석 금지 |
| SpeedRatio | 32 | 샘플상 250이 `prgSpdRatio` | 250 우선 지원 |
| Call SubProgram | 250 | 250은 `prgSpdRatio` | Call 의미 재검증 전 raw 보존 |
| Force/indyCARE | 302 | 302는 `careTackTime` | Force로 실행 금지 |
| JointMove legacy | 1 | 1은 Stop | JointMove로 실행 금지 |

## 7. 변수 노드 규칙

### 7.1 type 2: 변수 선언

```json
{
  "type": 2,
  "varList": [
    { "name": "count", "type": 1, "value": 0 }
  ]
}
```

### 7.2 type 3: 변수 대입/연산

```json
{
  "type": 3,
  "varList": [
    { "name": "count", "type": 1, "value": "count+1" }
  ]
}
```

호환 규칙:

- `type=3`은 Math/Assignment로 처리한다.
- `type=21`을 Math로 사용하지 않는다.
- 식 문자열은 APK 원문을 보존한다.

## 8. 흐름 제어 규칙

### 8.1 Loop

```json
{ "type": 20, "count": -1 }
```

- `count = -1`: 무한 루프
- `count > 0`: 지정 횟수 반복

### 8.2 LoopBreak

```json
{ "type": 21 }
```

`type=21`은 가장 가까운 Loop를 탈출한다.

### 8.3 WaitFor

```json
{
  "type": 23,
  "time": 1,
  "cond": {
    "left": { "type": 10, "value": "flag" },
    "right": { "type": 1, "value": 1 },
    "op": 0
  }
}
```

제조사 기준 `op`는 `0: ==`, `1: !=`, `2: >`, `3: >=`, `4: <`, `5: <=`이다.

### 8.4 If/Elif/Else

변수 조건:

- `24`: If
- `25`: Elif
- `26`: Else

DI 조건:

- `29`: If(DI)
- `30`: Elif(DI)

호환 실행 규칙:

- 같은 부모 아래 연속된 If/Elif/Else 체인은 하나의 조건 체인으로 실행한다.
- 첫 번째 true 분기만 실행한다.
- true 분기가 없을 때만 Else를 실행한다.
- 각 노드를 독립 실행하면 APK와 동작이 달라질 수 있다.

## 9. 모션 노드 규칙

### 9.1 type 102: JointMove

- `moveList[].wpList`의 모든 waypoint를 순서대로 실행한다.
- PC 직접 실행 시 `q` 기준 `joint_move`가 우선이다.
- `p`가 있어도 `task_move`로 실행하지 않는다.

### 9.2 type 103: FrameMove

- `moveList[].wpList`의 모든 waypoint를 순서대로 실행한다.
- PC 직접 실행 시 `p` 기준 `task_move`가 우선이다.

### 9.3 type 104/105

실제 샘플에서 `104`, `105`는 `moveList`와 연결되는 Move 계열이다.

관찰 필드:

- `type`
- `boundary`
- `wpList`
- `wpListOrigin`
- `intpl`
- `refFrame`
- `name`
- `tcp`
- `offset`는 주로 type 105에 존재

호환 규칙:

- `104/105`도 `102/103`과 같은 방식으로 `moveList -> wpList`를 해석한다.
- `wpListOrigin`은 원본 보존한다.
- 의미가 완전히 확정되기 전까지 PC 직접 실행은 보수적으로 막거나 사용자 확인이 필요하다.

## 10. Pick/Place 규칙

실제 구조:

```json
{
  "type": 201,
  "toolId": 0,
  "sensName": "",
  "approach": {
    "direction": 0,
    "distance": 0.1,
    "boundary": { "velLevel": 3, "accLevel": 3 },
    "waitTime": 0,
    "waitFor": { "type": 0, "time": 0 }
  },
  "retract": {
    "direction": 1,
    "distance": 0.1,
    "boundary": { "velLevel": 3, "accLevel": 3 },
    "waitTime": 0,
    "waitFor": { "type": 0, "time": 0 }
  },
  "target": {
    "type": 0,
    "point": { "q": [], "p": [] },
    "pallet": {},
    "refFrame": { "type": 1, "tref": [0, 0, 0, 0, 0, 0] },
    "tcp": [0, 0, 0, 0, 0, 0],
    "boundary": { "velLevel": 5, "accLevel": 5 }
  }
}
```

관찰:

- `target.type = 0`: 단일 포인트
- `target.type = 1`: 팔레트
- `toolId`는 `0`이 가장 많이 사용된다.
- `approach.direction`은 대부분 `0`
- `retract.direction`은 대부분 `1`
- `distance`는 meter 단위다.

호환 규칙:

- 기존 `toolId`를 임의로 `1`로 바꾸지 않는다.
- `direction`을 무시하고 항상 Z+ 오프셋으로 실행하지 않는다.
- `approach/retract`는 원본 필드 전체를 보존한다.
- 단일 포인트 Pick/Place는 `target.point.q/p`를 기준으로 한다.
- 팔레트 Pick/Place는 `target.pallet`이 참조하는 `type=999.palletInfo`를 기준으로 한다.

## 11. ToolInfo 규칙

실제 `toolInfo`는 최상위가 아니라 `program[]` 내부 `type=999` 노드에 있다.

```json
{
  "type": 999,
  "toolInfo": [
    {
      "id": 0,
      "name": "tool",
      "toolCommand": [
        { "name": "Init", "doMap": [] },
        { "name": "Reset", "doMap": [] },
        { "name": "Hold", "doMap": [] },
        { "name": "Release", "doMap": [] },
        { "name": "Idle", "doMap": [] }
      ],
      "toolSensing": []
    }
  ]
}
```

호환 규칙:

- `toolInfo` 읽기/쓰기는 반드시 `type=999` 노드 내부에서 한다.
- root `toolInfo`를 만들지 않는다.
- `Hold`, `Release` 명령 이름은 그대로 보존한다.
- `toolId = -1`은 원본 의미를 보존하고, 실행 fallback은 로그 경고와 함께 별도 처리한다.

## 12. PalletInfo 규칙

실제 APK 샘플의 `palletInfo`는 대부분 `type=999` 노드 내부에 있다.

```json
{
  "palletizingOrder": 0,
  "points": [
    { "q": [], "p": [] },
    { "q": [], "p": [] },
    { "q": [], "p": [] }
  ],
  "size": [3, 2],
  "name": "p1",
  "id": 0
}
```

호환 규칙:

- APK 표준 저장 시 `size`를 우선 사용한다.
- PC 내부 편의 필드 `m`, `n`, `l`, `prod_size`, `gap_size`, `expanded_layer_nodes`는 APK export에 직접 쓰지 않는다.
- 기존 `palletizingOrder`는 보존한다.
- root `palletInfo`가 원본에 있으면 보존하되, 기준 데이터는 `type=999.palletInfo`로 둔다.

## 13. 저장 정책

### 13.1 APK 호환 저장

APK로 이식할 파일은 다음 원칙을 따른다.

- 원본 raw JSON을 최대한 보존한다.
- 변경한 노드만 해당 필드를 갱신한다.
- 알 수 없는 타입은 필드 제거 없이 통과시킨다.
- PC 내부 필드는 제거한다.
- `q/p`를 `program[]` 루트에 추가하지 않는다.
- 모션 좌표는 `wpList`와 `moveList`에만 저장한다.
- `toolInfo`, `palletInfo`는 `type=999` 내부를 기준으로 저장한다.

### 13.2 PC 내부 저장

PC UI 편의를 위해 내부 캐시 필드를 둘 수 있다.

예:

- `resolved_waypoints`
- `p_data`
- `app_data`
- `ret_data`
- `target_pallet_name`
- `expanded_layer_nodes`

단, 이 필드는 APK export 결과에 그대로 노출하지 않는다.

## 14. PC 직접 실행 정책

가장 안전한 실행 기준은 로봇 컨트롤러의 native JSON 실행이다.

제조사 예제의 기본 흐름도 `JsonProgramComponent`로 JSON 문자열을 만든 뒤 `IndyDCPClient.set_and_start_json_program(json_string)`으로 컨트롤러에 넘기는 방식이다. 따라서 실제 로봇 구동은 PC가 노드를 하나씩 직접 해석하기보다, 검증된 JSON을 컨트롤러에 전달하는 경로를 우선한다.

PC 직접 해석 실행은 다음 조건에서만 사용한다.

- 디버그
- 시뮬레이션
- 로봇 컨트롤러가 native JSON 실행을 지원하지 않는 경우

직접 실행기가 반드시 지켜야 할 규칙:

- type별 실행은 이 문서의 타입 사전을 따른다.
- `102`는 joint move, `103`은 task move로 분리한다.
- 모든 waypoint를 순서대로 실행한다.
- Pick/Place, Frame Move, Joint Move 실행 전 JSON에 들어있는 TCP를 로봇에 적용하고 `get_default_tcp`로 read-back 확인한다.
- TCP 확인값이 요청값과 맞지 않으면 동작을 보내지 않고 N.G로 정지한다.
- If/Elif/Else 체인은 하나의 체인으로 실행한다.
- `If DI`는 조건이 참일 때만 자식을 실행하고, `Wait DI`/자식 없는 `type=29`는 조건이 들어올 때까지 대기한다.
- `Wait DI` 타임아웃이 발생하면 다음 명령을 보내지 않고 N.G로 정지한다.
- `approach.direction`, `retract.direction`을 반영한다.
- 알 수 없는 타입은 실행하지 말고 로그에 남긴다.

## 15. 목표 아키텍처

최종 목표는 PC 편집기, APK JSON, 로컬 로봇 실행이 같은 프로그램 의미를 공유하는 것이다.

```text
APK JSON / PC UI / AI 생성 로직
        -> Canonical Program Model
        -> APK-compatible JSON Exporter
        -> Validator
        -> IndyDCP Native JSON Deploy
        -> Program State Monitor
```

핵심 규칙:

- PC UI와 AI는 바로 JSON 문자열을 조작하지 않고 내부 표준 모델을 수정한다.
- export 단계에서만 APK 호환 JSON 구조로 변환한다.
- validator는 golden sample과 PC 생성 파일을 같은 규칙으로 검사한다.
- 로컬 로봇 전송은 `set_and_start_json_program` 경로를 우선한다.
- 가상 환경 실행은 같은 내부 모델을 사용하되, 실제 로봇 전송 전 dry-run과 안전 검사를 통과해야 한다.
- 로봇 IP, tool mapping, pallet mapping, workspace limit, collision policy는 실행 전 명시적으로 확정한다.

## 16. 검증 테스트 기준

다음 자동 검사를 golden test로 둔다.

1. 225개 APK 샘플이 모두 파싱되어야 한다.
2. `program[].id` 중복이 없어야 한다.
3. 모든 `pId`가 존재하는 부모를 참조해야 한다.
4. 모든 `moveList[].wpList[].id`가 root `wpList[].id`에 존재해야 한다.
5. 모든 `102/103/104/105` 노드는 같은 이름의 `moveList`를 가져야 한다.
6. `load -> export -> validate` 후에도 위 조건이 유지되어야 한다.
7. 알 수 없는 타입은 export 후에도 원본 필드가 보존되어야 한다.
8. PC 생성 JSON도 같은 validator를 통과해야 한다.

2026-05-19 추가 검증 기준:

- APK 원본 파일을 열었다가 다시 내보낼 때, 프로그램 노드에서 직접 참조하지 않는 기존 `moveList`/`wpList` 항목도 보존한다.
- 이는 과거 티칭 파일에 남아 있는 예비 waypoint, 복사 move, 미사용 move 자산을 임의 삭제하지 않기 위한 보수적 정책이다.
- Robot C처럼 실제 program에서는 `midmove__copy1`, `finalmove__copy1`만 참조하더라도 원본 파일의 나머지 move/wp 자산은 그대로 유지한다.
- 2026-05-19 검증 파일 `260519robotc1.7 (1).json`, `20260519robotB1.7 (1).json`, `intel5_prj_color_1.7 (1).json`은 `program`, `moveList`, `wpList`, Pick/Place TCP round-trip이 모두 일치해야 한다.

## 17. 코드 수정 우선순위

1. 타입 사전을 단일 모듈로 분리한다.
2. `robot_hmi_view.py` 내부의 하드코딩 타입 매핑을 제거하고 타입 사전을 참조한다.
3. `TeachingRepositoryImpl`에 `104/105` move parser를 추가한다.
4. `save_to_conty_json`에서 `type=999.palletInfo.size` 보존을 우선하고 `m/n/l` export를 중단한다.
5. Pick/Place editor는 distance를 UI mm와 JSON m로 명확히 분리한다.
6. Tool mapping 저장은 root가 아니라 `type=999.toolInfo`를 수정한다.
7. PC 직접 실행기를 native JSON 실행과 분리하고, 직접 실행은 타입 사전 기반으로 재작성한다.
8. 225개 샘플 validator 테스트를 추가한다.
9. PC/AI 생성 프로그램을 위한 `Canonical Program Model -> APK JSON Exporter -> Validator -> IndyDCP Deploy` 파이프라인을 추가한다.
