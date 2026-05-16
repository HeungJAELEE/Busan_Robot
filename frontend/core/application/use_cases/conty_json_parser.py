import json

class ContyJsonParser:
    """
    Parses Neuromeka Conty App exported JSON files (.7.json).
    Translates the flat list of program nodes into a tree structure.
    
    실제 Conty APK의 type 번호 매핑 (학습 파일 11개 기반 검증):
    ──────────────────────────────────────────────────
    999  Config/Root    - 프로그램 설정 (toolInfo, indyCareInfo 등)
    1    JointMove      - 관절 좌표 절대 이동
    2    FrameMove      - Task 좌표 절대 이동 (TCP 기준)
    3    CircularMove   - 원호 이동
    4    MoveHome       - 홈 위치 이동
    5    MoveB          - 블렌딩 이동
    6    MoveC          - 원호 이동 (변형)
    20   DO             - Digital Output 설정 (count → toolCommand id → doMap)
    21   WaitDI         - DI 신호 대기 (diList 없으면 조건 대기)
    22   AO             - Analog Output 설정
    23   WaitAI         - AI 신호 대기
    24   EndToolDO      - EndTool Digital Output 설정
    28   Wait           - 시간 대기 (time 초)
    29   WaitPeriod     - 주기적 대기 / DI 신호 대기 (diList 기반)
    40   Comment        - 주석
    41   Stop           - 프로그램 정지
    100  Folder         - 노드 그룹 (자식 노드 포함)
    102  If(DI)         - DI 조건 분기
    103  Loop           - 반복문 (count=-1: 무한, 양수: 횟수)
    200  Pick           - 픽업 동작 그룹 (groupName)
    201  Place          - 플레이스 동작 (approach → target → retract)
    202  Pallet         - 팔레타이징 동작 (palletId 참조)
    250  Call           - 서브프로그램 호출
    302  Force          - 힘 제어 / 충돌 정책
    """
    
    # 실제 Conty APK type 번호 → 표시 이름
    TYPE_MAP = {
        999: "Config",
        1:   "JointMove",
        2:   "FrameMove",
        3:   "CircularMove",
        4:   "MoveHome",
        5:   "MoveB",
        6:   "MoveC",
        20:  "DO",
        21:  "WaitDI",
        22:  "AO",
        23:  "WaitAI",
        24:  "EndToolDO",
        28:  "Wait",
        29:  "WaitPeriod",
        40:  "Comment",
        41:  "Stop",
        100: "Folder",
        102: "If(DI)",
        103: "Loop",
        200: "Pick",
        201: "Place",
        202: "Pallet",
        250: "Call",
        302: "Force",
    }

    @staticmethod
    def parse_to_tree_nodes(filepath: str):
        """Conty JSON을 트리 노드로 파싱"""
        try:
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                data = json.load(f)
        except Exception as e:
            return {"error": f"Failed to load JSON: {str(e)}"}

        program = data.get("program", [])
        if not program:
            return {"error": "No 'program' array found in JSON."}

        # Build tree from flat list (id -> pId)
        nodes = {}
        root_nodes = []

        # toolInfo 추출 (DO 명령 해석에 필요)
        tool_info = []
        for cmd in program:
            if cmd.get("type") == 999:
                tool_info = cmd.get("toolInfo", [])
                break

        for cmd in program:
            node_id = cmd.get("id")
            pid = cmd.get("pId")
            cmd_type = cmd.get("type")
            
            type_name = ContyJsonParser.TYPE_MAP.get(cmd_type, f"Unknown({cmd_type})")
            text = type_name
            
            if cmd_type == 999:
                text = "Program Settings"
            elif cmd_type in (1, 2):  # JointMove / FrameMove
                point = cmd.get("target", {}).get("point", {})
                p = point.get("p", [])
                blend = cmd.get("blendRadius", 0)
                coord_str = f"[{', '.join(f'{v:.1f}' for v in p[:3])}]" if p else "[]"
                text = f"{'JointMove' if cmd_type == 1 else 'FrameMove'} {coord_str}"
                if blend: text += f" B={blend}"
            elif cmd_type == 3:
                text = "CircularMove"
            elif cmd_type == 4:
                text = "MoveHome"
            elif cmd_type in (5, 6):
                text = f"Move{'B' if cmd_type == 5 else 'C'}"
            elif cmd_type == 20:  # DO
                count = cmd.get("count", -1)
                # toolCommand id에서 실제 명령 이름을 찾기
                do_name = f"ToolCmd(id={count})"
                for tool in tool_info:
                    for tc in tool.get("toolCommand", []):
                        if tc.get("id") == count:
                            do_name = tc.get("name", do_name)
                            do_map = tc.get("doMap", [])
                            if do_map:
                                pins = ", ".join(f"DO{d['idx']}={'ON' if d['value'] else 'OFF'}" for d in do_map)
                                do_name += f" ({pins})"
                            break
                text = f"DO: {do_name}"
            elif cmd_type == 21:  # WaitDI
                text = "WaitDI"
            elif cmd_type == 22:  # AO
                text = "AO"
            elif cmd_type == 24:  # EndToolDO
                text = "EndToolDO"
            elif cmd_type == 28:  # Wait
                t = cmd.get("time", 0)
                text = f"Wait ({t}s)"
            elif cmd_type == 29:  # WaitPeriod
                di_list = cmd.get("diList", [])
                if di_list:
                    pins = ", ".join(f"DI{d['idx']}={'HI' if d['value'] else 'LO'}" for d in di_list)
                    text = f"WaitDI ({pins})"
                else:
                    text = "WaitPeriod"
            elif cmd_type == 40:
                text = f"Comment: {cmd.get('name', '')}"
            elif cmd_type == 41:
                text = "Stop"
            elif cmd_type == 100:  # Folder
                name = cmd.get("name", "")
                text = f"Folder ({name})" if name else "Folder"
            elif cmd_type == 102:  # If(DI)
                name = cmd.get("name", "")
                text = f"If ({name})" if name else "If(DI)"
            elif cmd_type == 103:  # Loop
                name = cmd.get("name", "")
                text = f"Loop ({name})" if name else "Loop"
            elif cmd_type == 200:  # Pick
                name = cmd.get("groupName", cmd.get("name", ""))
                text = f"Pick ({name})" if name else "Pick"
            elif cmd_type == 201:  # Place
                target = cmd.get("target", {})
                point = target.get("point", {})
                p = point.get("p", [])
                coord_str = f"[{', '.join(f'{v:.2f}' for v in p[:3])}]" if p else ""
                text = f"Place {coord_str}" if coord_str else "Place"
            elif cmd_type == 202:  # Pallet
                pallet_id = cmd.get("target", {}).get("pallet", {}).get("palletId", "")
                text = f"Pallet (id={pallet_id})" if pallet_id else "Pallet"
            elif cmd_type == 250:
                text = "Call SubProgram"
            elif cmd_type == 302:
                text = "Force Control"
                
            node = {
                "id": node_id,
                "pid": pid,
                "text": text,
                "children": [],
                "raw": cmd
            }
            nodes[node_id] = node

        # Link children
        for node_id, node in nodes.items():
            pid = node["pid"]
            if pid == 0 or pid not in nodes:
                root_nodes.append(node)
            else:
                nodes[pid]["children"].append(node)

        return {"status": "success", "tree": root_nodes, "toolInfo": tool_info}
