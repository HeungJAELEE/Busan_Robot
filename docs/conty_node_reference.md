# Conty JSON 노드 타입 사전 (AI-Readable Reference)

> 이 문서는 Indy7 로봇의 Conty 프로그램 JSON 구조를 설명합니다.
> AI가 사용자 JSON 파일을 분석할 때 참조하는 공식 레퍼런스입니다.

## 1. 파일 최상위 구조

```json
{
  "info": { "name": "프로그램명", "type": 7, "version": "..." },
  "wpList": [ ... ],      // 웨이포인트 목록 (좌표 저장소)
  "program": [ ... ],     // 실행 노드 리스트 (트리 구조)
  "moveList": [ ... ]     // 이동 명령 목록 (웨이포인트 참조)
}
```

### 참조 구조 (3-Level Reference Resolution)
```
program[].moveListIdx → moveList[idx].wpList → wpList[wpIdx].{j_pos, t_pos}
```

## 2. 노드 공통 필드

모든 program 노드에 존재하는 필드:

| 필드 | 타입 | 설명 |
|------|------|------|
| `type` | int | 노드 타입 번호 (아래 표 참조) |
| `id` | int | 노드 고유 ID |
| `pId` | int | 부모 노드 ID (-1이면 루트) |
| `name` | string | 노드 이름 |
| `comment` | string | 사용자 코멘트 (대부분 빈 문자열) |
| `intpl` | int | 보간 방식 (시스템 고정, 편집 불필요) |
| `tcp` | array[6] | TCP 오프셋 (시스템 고정) |
| `refFrame` | array[6] | 기준 프레임 (시스템 고정) |
| `collisionPolicy` | int | 충돌 정책 (시스템 고정) |

## 3. 노드 타입 상세

### 🔧 시스템 노드

#### type=999: 프로그램 설정 (Program Settings)
프로그램 전체 설정. **항상 1개만 존재.**
```json
{
  "type": 999,
  "toolInfo": [
    {
      "id": 0, "name": "Tool1",
      "toolCommand": [
        {"name": "Hold", "doMap": [{"idx": 1, "value": 1}, {"idx": 2, "value": 0}]},
        {"name": "Release", "doMap": [{"idx": 1, "value": 0}, {"idx": 2, "value": 1}]}
      ]
    }
  ],
  "palletInfo": [
    {
      "id": 0, "name": "pallet1",
      "size": [2, 3],  // [행(M), 열(N)]  ※ Z레이어 없음 (2D만)
      "points": [
        {"p": [x,y,z,rx,ry,rz], "q": [j1,j2,j3,j4,j5,j6]},  // P1 시작점
        {"p": [...], "q": [...]},  // P2 행 끝점
        {"p": [...], "q": [...]}   // P3 열 끝점
      ]
    }
  ]
}
```

#### type=2: 변수 정의 (Variables)
```json
{"type": 2, "varList": []}  // 대부분 빈 배열
```

#### type=3: 변수 초기화 (Variable Init)
```json
{"type": 3, "varList": [{"name": "count", "value": 0}]}
```

---

### 🚗 이동 노드 (Motion)

#### type=100: Home
원점 복귀. 추가 파라미터 없음.
```json
{"type": 100, "name": "Home Node"}
```

#### type=102: JointMove (관절 이동)
**내부에 1~N개 웨이포인트를 가짐. 개수 제한 없음.**
```json
{
  "type": 102,
  "name": "JointMove Node",
  "moveListIdx": 0,           // moveList[0] 참조
  "boundary": {
    "velLevel": 5,             // 속도 레벨 (1~9) ★ 편집 가능
    "accLevel": 5              // 가감속 레벨 (1~9) ★ 편집 가능
  }
}
```
- `moveList[moveListIdx].wpList` → 여러 웨이포인트 인덱스 배열
- 각 웨이포인트: `wpList[idx].{j_pos, t_pos}` (6축 관절/태스크 좌표)

#### type=103: FrameMove (직교 이동)
JointMove와 동일 구조. 직교 좌표 기반 이동.

#### type=1: JointMovePoint (단일 포인트)
moveList 없이 직접 좌표 포함.

#### type=104: PalletMove (팔레트 이동)
```json
{"type": 104, "name": "PalletMove", "moveListIdx": 0}
```

#### type=105: FrameMove (Pallet용)
```json
{"type": 105, "moveListIdx": 0}
```

#### type=106: MoveC (원호 이동)
```json
{"type": 106, "moveListIdx": 0, "boundary": {"velLevel": 5, "accLevel": 5}}
```

---

### ⚡ 입출력 노드 (I/O)

#### type=4: SmartDO (디지털 출력)
**DO 핀에 ON/OFF 신호 출력. ★ 편집 가능.**
```json
{
  "type": 4,
  "doList": [
    {"idx": 1, "value": 1},   // DO1 = ON  ★ 편집: 포트번호 + ON/OFF
    {"idx": 2, "value": 0}    // DO2 = OFF
  ]
}
```
- `idx`: DO 포트 번호 (0~31)
- `value`: 0=OFF, 1=ON
- 1~2개 핀을 동시에 제어 가능

#### type=5: SmartAO (아날로그 출력)
```json
{"type": 5, "aoList": [{"idx": 0, "value": 0}]}  // 빈도 매우 낮음
```

#### type=6: EndToolDO (엔드툴 출력)
```json
{"type": 6, "endtoolDiList": [...]}  // 빈도 매우 낮음
```

---

### 🧠 로직 노드 (Logic/Flow)

#### type=20: Loop (반복)
```json
{
  "type": 20,
  "count": 5,         // 반복 횟수 ★ 편집 가능
  "loopType": 0       // 0=횟수반복, 1=무한반복
}
```

#### type=21: EndLoop
Loop 종료 마커. 편집 불필요.

#### type=22: Wait (시간 대기)
```json
{
  "type": 22,
  "time": 1.0     // 대기 시간(초) ★ 편집 가능
}
```

#### type=24: If (조건 분기)
```json
{
  "type": 24,
  "cond": {
    "lhs": {"type": "var", "name": "count"},
    "op": ">=",
    "rhs": {"type": "const", "value": 5}
  }
}
```

#### type=25: Elif (추가 조건)
If와 동일 구조.

#### type=26: Else
추가 필드 없음.

#### type=27: EndIf
조건 종료 마커.

#### type=28: WaitDI (DI 대기)
**DI 신호가 특정 상태가 될 때까지 대기. ★ 편집 가능.**
```json
{
  "type": 28,
  "diList": [{"idx": 0, "value": 1}],  // DI0 = ON 대기 ★ 포트+ON/OFF
  "time": 3.0                          // 타임아웃(초) ★ 편집 가능 (0=무한대기)
}
```

#### type=29: If(DI) — DI 조건 분기
```json
{"type": 29, "diList": [{"idx": 0, "value": 1}]}
```

#### type=30: Elif(DI)
If(DI)와 동일 구조.

#### type=31: WaitAI (AI 대기)
```json
{"type": 31, "aiList": [{"idx": 0, "value": 500, "op": ">="}]}
```

#### type=32: If(AI) — AI 조건 분기
```json
{"type": 32, "aiList": [{"idx": 0, "value": 500, "op": ">="}]}
```

#### type=33: Elif(AI)
If(AI)와 동일 구조.

#### type=34: Switch
```json
{"type": 34, "cond": {...}}
```

#### type=35: Case
```json
{"type": 35, "caseValue": 1}
```

#### type=36: Default, type=37: EndSwitch
마커 노드.

#### type=40: Comment
```json
{"type": 40, "comment": "사용자 메모"}  // ★ 편집 가능
```

#### type=42: Stop
프로그램 정지. 추가 필드 없음.

#### type=43: LoopBreak
Loop 탈출.

#### type=44: WaitFor
```json
{"type": 44, "waitFor": {"type": 1, "time": 2.0}}
```

#### type=50: Math (연산)
```json
{
  "type": 50,
  "math": {
    "lhs": "count",
    "op": "+",
    "rhs": "1",
    "result": "count"
  }
}
```

---

### 📦 Pick & Place 노드

#### type=200: PickGroup (Pick/Place 그룹)
자식으로 Pick/Place 노드들을 포함하는 컨테이너.
```json
{"type": 200, "groupName": "Pick&Place 1"}
```

#### type=201: Pick (집기)
**TCP Hold 동작 + approach/retract Z 이동. ★ 편집 가능.**
```json
{
  "type": 201,
  "toolId": 0,                         // toolInfo[].id 참조
  "target": {
    "type": 0,                         // 0=단일포인트, 1=팔레트 ★ 선택
    "point": {"p": [x,y,z,rx,ry,rz], "q": [...]},  // type=0일 때
    "pallet": {"id": 0, "name": "pallet1"}           // type=1일 때
  },
  "approach": {
    "direction": 0,                    // 0=Z축(위→아래) ★ 편집
    "distance": 0.15,                  // 접근 거리(미터) ★ 편집
    "boundary": {"velLevel": 1, "accLevel": 1},  // 접근 속도 ★ 편집
    "waitTime": 0,
    "waitFor": {"type": 0, "time": 0}
  },
  "retract": {
    "direction": 1,                    // 1=Z축(아래→위) ★ 편집
    "distance": 0.15,                  // 후퇴 거리(미터) ★ 편집
    "boundary": {"velLevel": 1, "accLevel": 1},
    "waitTime": 1,                     // Hold 후 대기시간(초) ★ 편집
    "waitFor": {"type": 0, "time": 0}
  }
}
```

**동작 순서:**
1. approach 위치로 이동 (target + Z offset 위)
2. target 위치로 하강
3. Hold(TCP 잡기) — toolCommand.Hold.doMap 실행
4. waitTime 대기 (retract.waitTime)
5. retract 위치로 상승 (target + Z offset 위)

#### type=202: Place (놓기)
Pick과 동일 구조. Release(TCP 놓기) 동작.

**Pick vs Place 차이:**
- Pick: Hold(doMap의 Hold 실행) → 물체 집기
- Place: Release(doMap의 Release 실행) → 물체 놓기

---

### 🔧 고급 노드

#### type=70: SpeedRatio
```json
{"type": 70, "speedRatio": 50}  // 전체 속도 비율(%) ★ 편집 가능
```

#### type=72: ToolSensing
```json
{"type": 72, "sensName": "tool_sensor_1"}
```

#### type=73: ConveyorTracking
```json
{"type": 73, "conveyorId": 0}
```

#### type=74: TaktTime
```json
{"type": 74, "taktTime": 10.0}  // 택타임(초)
```

#### type=75: Detect
```json
{"type": 75, "detectType": 0}
```

#### type=76: Retrieve
```json
{"type": 76}
```

#### type=80: PythonScript
```json
{"type": 80, "script": "print('hello')"}  // ★ 편집 가능
```

#### type=250: Call (서브프로그램 호출)
```json
{"type": 250, "sub_program": "sub_routine.json"}
```

#### type=302: Force Control (indyCARE)
```json
{"type": 302, "forceLevel": 500}
```

---

## 4. 팔레트 좌표 계산 규칙

Conty 팔레트는 **2D 그리드** (M행 × N열):

```
P1(시작점) ────────→ P2(행 끝점)
  │                     │
  │   [0,0] [1,0] [2,0] │
  │   [0,1] [1,1] [2,1] │
  │                     │
  ↓                     ↓
P3(열 끝점)
```

각 포인트 계산:
```
point(row, col) = P1 + (row/(M-1)) × (P2-P1) + (col/(N-1)) × (P3-P1)
```

### Z 레이어 확장 (HMI 커스텀 기능)
Conty에는 Z축 레이어 기능이 없음. HMI에서 이지 티칭으로 추가:
- L(층) 설정 시 각 레이어의 Z 오프셋 = 제품높이(Iz) × 레이어번호
- JSON 저장 시 Place 노드가 레이어 수만큼 자동 전개됨

---

## 5. 고정값 vs 가변값 가이드

| 분류 | 필드 | 설명 |
|------|------|------|
| **고정 (편집 불필요)** | tcp, refFrame, intpl, collisionPolicy, sensName, blendOpt | 시스템 기본값 |
| **가변 (★ 편집 필요)** | doList, diList, time, count, velLevel, accLevel, approach, retract, target | 사용자 설정 |
| **참조 (읽기)** | moveListIdx, toolId, pId | 다른 노드/리스트 참조 |

---

## 6. 자주 사용되는 패턴

### 패턴 1: 기본 Pick & Place
```
Home → JointMove → Pick(단일) → Home → Place(단일) → Home
```

### 패턴 2: 팔레트 Pick → 단일 Place
```
Home → Loop(N) → Pick(팔레트) → Home → Place(단일) → Home → EndLoop
```

### 패턴 3: DO 제어 + 대기
```
SmartDO(DO1=ON) → Wait(1초) → WaitDI(DI0=ON, timeout=3초) → SmartDO(DO1=OFF)
```

### 패턴 4: 조건 분기
```
If(DI0=ON) → JointMove(A) → Elif(DI1=ON) → JointMove(B) → Else → Home → EndIf
```
