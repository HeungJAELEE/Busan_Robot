# Robot A Dry Run Recording 분석 보고서 (2026-05-18)

## 1. 결론

2026-05-18 기준 Robot A의 `class3_test.7.json` Dry Run Recording은 **로직 파싱과 DI 조건 분기는 정상**으로 보입니다. 다만 공통 Place 위치로 내려가는 구간에서 Robot A가 충돌 플래그를 발생시켰고, 18 loop pass 조건의 장시간 반복 테스트는 완료하지 못했습니다.

현 시점에서는 JSON 문법 오류보다는 아래 세 가지 가능성이 더 큽니다.

- 공통 Place 좌표 `X552 / Y-99` 부근의 실제 설비/레일/차량 지그 간섭
- Robot A 자세에서 Place 하강 중 특정 관절 자세 또는 토크 피크가 충돌 감지로 이어지는 문제
- 고속 반복 중 상태 읽기 timeout과 충돌 플래그가 같이 발생하는 통신/상태 폴링 타이밍 문제

로봇은 각 N.G 이후 `stop_motion -> stop_current_program -> reset_robot -> Home` 순서로 복구했고, 마지막 상태는 Home 복귀 완료입니다.

## 2. 테스트 조건

대상 파일:

```text
/Users/leejaeheung/Downloads/class3_test.7.json
```

주요 조건:

```text
Robot: Robot A
TCP: 테스트 중 미적용/무시
Speed: 100%
가상 DI: DI10, DI11, DI12, DI13 ON
Dry Run: DO/Tool 출력은 실제 핀 구동 대신 이벤트/기록 중심
저장: 로컬 JSONL + MySQL
```

JSON 내부 로직:

```text
Loop count = 6
DI10 = 대기 게이트
DI11 = Red 선택
DI12 = Blue 선택
DI13 = Green 선택
Red/Blue/Green 변수는 0 -> 1 -> 2로 증가
각 색상은 1번 위치, 2번 위치까지만 Pick/Place 수행
```

## 3. 주요 세션 요약

### 3-1. 원본 높이 테스트

```text
Session: DRR_RA_CLASS3_100_20260518_200250
Place target Z: 원본 129mm
Samples: 807
Result: N.G
```

진행 결과:

```text
Red 1 Pick/Place OK
Blue 1 Pick/Place OK
Green 1 Pick/Place OK
Red 2 Pick/Place OK
Blue 2 Pick OK
Blue 2 Place 하강 중 충돌 감지
```

관찰 지점:

```text
충돌 발생 부근: X545~552 / Y-99 / Z 약 235mm
관절 자세: q2 약 -27.6도, q3 약 -66.1도, q5 약 -90.5도
상태: collision=1, error=0
```

### 3-2. Place Zone 단독 스캔

```text
Session: PLACE_ZONE_SCAN_RA_20260518_201019
목표: 공통 Place XY에서 Z 단계별 접근
Result: OK
```

테스트 포인트:

```text
Z279.3 OK
Z270 OK
Z260 OK
Z250 OK
Z245 OK
Home OK
```

해석:

```text
단독 수동/분리 접근에서는 Z245까지 안전했다.
따라서 원본 Z129만 문제가 아니라, 전체 프로그램 순서에서 들어오는 경로/자세/속도/상태 폴링까지 같이 봐야 한다.
```

### 3-3. 18 loop pass 조건 테스트

```text
Session: DRR_RA_CLASS3_SAFE18_20260518_201641
Target cycles: 3
JSON internal Loop: 6
Expected loop passes: 18
Place target Z: 테스트용 복사본에서 245mm로 상향
Samples: 826
MySQL: session 1건, events 3건, samples 826건 저장 확인
Result: N.G
```

N.G 사유:

```text
이동 완료 대기 실패/타임아웃(240.0초)
이후 collision=1 상태 확인
```

마지막 정상 샘플:

```text
Sample: RA-000811
좌표: X551.6 / Y-98.9 / Z366.7mm
관절: J1 8.24 / J2 -30.47 / J3 -39.34 / J4 1.36 / J5 -113.65 / J6 11.30
Torque: [3.68, 70.09, 14.37, -7.66, 15.08, -3.58]
Status: busy=1, collision=0
```

충돌 플래그 이후 샘플:

```text
Sample: RA-000812 이후
Status: collision=1
주의: q/p 일부 값이 깨진 형태로 기록됨. 충돌 이후 통신 버퍼/상태 응답 불안정 구간으로 보고 분석에서 제외한다.
```

## 4. 현재 코드 반영 사항

2026-05-19 기준 3D 가상화 화면에는 아래 가이드 존을 추가했다.

- Robot A/B/C 간격: 1850mm
- Rail과 로봇 전면 거리: 500mm
- Robot A 기준 rail 끝단 여유: 약 1000mm
- 공통 Place 하강 감시 존: `X552 / Y-99 / Z220~420mm` 주변
- Robot A/B, B/C 사이 작업영역 겹침 감시 존

표시는 실제 티칭 좌표를 바꾸지 않는 **투명 권장 가이드**다.

```text
녹색: 권장 안전
주황: 감속/확인 권장
빨강: 회피/분리 테스트 권장
```

참고한 제조사 ROS 자료:

- https://github.com/neuromeka-robotics/indy-ros
- `indy_description/urdf/config/indy7/kinematics.yaml`
- `indy_description/urdf/config/indy7/visual_parameters.yaml`
- `indy_moveit/config/indy_macro.srdf.xacro`
- `indy_moveit/launch/ompl_planning_pipeline.launch.xml`

확인 내용:

- URDF/Xacro는 Indy7 링크 구조와 collision mesh 경로를 제공한다.
- SRDF는 self-collision에서 인접 링크와 일부 Never collision 링크쌍을 제외한다.
- MoveIt launch에는 `FixStartStateCollision`, `FixWorkspaceBounds`, `FixStartStateBounds` adapter가 포함되어 있다.
- 이 정보는 HMI 내부에서 완전한 충돌판정을 하기보다, 가벼운 시각 가이드 존을 만드는 기준으로 사용했다.

## 5. 내일 테스트 레시피

내일은 전체 프로그램 반복부터 다시 밀어붙이지 말고, 충돌 추정 원인을 작게 쪼개서 확인한다.

### Recipe A. Place 하강 구간 단독 재현

목적:

```text
공통 Place 위치가 실제로 어느 Z에서 충돌 플래그를 발생시키는지 확인
```

순서:

```text
1. Robot A 에러 리셋
2. Robot A Home
3. TCP 미적용 상태 확인
4. 속도 50%
5. Place 접근 위치로 이동: X552 / Y-99 / Z400
6. Z360 -> Z330 -> Z300 -> Z280 -> Z260 -> Z245 순서로 하강
7. 각 지점에서 q/p/torque/status를 3초 이상 기록
8. collision이 뜨면 즉시 정지, 리셋, Home
```

판정:

```text
단독 하강에서도 충돌 발생: 실제 설비/자세/감도 문제 가능성 큼
단독 하강은 OK, 프로그램에서만 충돌: 경로 전환/속도/상태 폴링/연속 명령 타이밍 가능성 큼
```

### Recipe B. 속도별 비교

목적:

```text
속도 100%에서만 감지되는 동적 충돌/토크 피크인지 확인
```

조건:

```text
속도 50%, 70%, 100% 순서로 같은 Place 하강만 테스트
각 속도별로 torque peak와 collision flag 비교
```

### Recipe C. Blue 2 Place 직전 자세 재현

목적:

```text
Blue 2 Pick 후 공통 Place로 넘어가는 자세 전환이 문제인지 확인
```

순서:

```text
1. Home
2. Blue 2 Pick 접근/동작/후퇴까지만 실행
3. 공통 Place 접근으로 이동
4. 하강하지 않고 Z400~Z360에서 상태/토크 안정성 확인
5. 이후 Z 단계 하강
```

### Recipe D. Page3 기록 안정성 확인

목적:

```text
충돌 이후 q/p 값이 깨지는 구간을 기록에서 구분하고, DB 분석 데이터 오염을 줄인다.
```

확인할 것:

```text
1. collision=1 이후 q=[0,0,0...] 또는 비정상 p 값은 분석 제외
2. N.G 발생 시 samples.jsonl 마지막 정상값과 results.jsonl command_id를 함께 묶어 저장
3. MySQL metadata에 exec_ng_reason, sample_count, final_status를 summary와 동일하게 남기는지 확인
```

## 6. 작업 중지 기준

다음 중 하나라도 발생하면 즉시 테스트를 중지한다.

```text
collision=1
error=1
status_read_failed
busy가 장시간 해제되지 않음
토크가 평소 대비 급격히 튐
로봇 동작음/진동이 평소와 다름
```

중지 후 조치:

```text
stop_motion
stop_current_program
reset_robot
Home
로그 백업
```
