import json
import os
from core.domains.teaching_management.entities import ContyProgram, TeachingNode, WaypointVO

class TeachingRepositoryImpl:
    """Repository handling persistence of Conty programs using JSON structure."""
    
    def load_from_json(self, filepath: str) -> ContyProgram:
        if not os.path.exists(filepath):
            return ContyProgram("New_Program")
            
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        prog_name = data.get("info", {}).get("name", "Loaded_Program")
        prog = ContyProgram(prog_name)
        prog.nodes = [] # Clear default nodes
        
        # Store full raw data for lossless saving
        prog._raw_info = data.get("info", {"name": prog_name})
        prog._raw_wpList = data.get("wpList", [])
        prog._raw_moveList = data.get("moveList", [])
        prog._raw_full_data = data
        prog.pallets = data.get("palletInfo", [])
        
        # ─── 3단계 참조 해석용 색인 구축 ───
        # moveList: name → move 정의 (boundary, tcp, refFrame, wpList[{id}])
        move_map = {}
        for mv in prog._raw_moveList:
            mv_name = mv.get("name", "")
            if mv_name:
                move_map[mv_name] = mv
        
        # wpList: id → 실제 좌표 (q[], p[])
        wp_map = {}
        for wp in prog._raw_wpList:
            wp_id = str(wp.get("id", ""))
            if wp_id:
                wp_map[wp_id] = wp
        
        max_node_id = -1
        
        for raw_node in data.get("program", []):
            t = raw_node.get("type", 0)
            node_id = raw_node.get("id", 0)
            if node_id > max_node_id:
                max_node_id = node_id
                
            node = TeachingNode(node_id, raw_node.get("pId", 0), t)
            node.__raw__ = raw_node.copy()  # <--- Lossless persistence
            
            node.name = raw_node.get("name", "")
            node.enable = raw_node.get("enable", True)
            
            # ─── Conty 실제 타입 매핑 (학습파일 120+ 분석 기반) ─────────
            # 999=ProgramSettings, 2=Variables, 3=Variables(alt)
            # 102=JointMove, 103=FrameMove (핵심! moveList→wpList 3단계 참조)
            # 100=Folder/Home, 4=SmartDO, 20=Loop, 22=Wait(시간), 28=Wait(DI)
            # 29=If/WaitFor(DI), 201=Pick, 202=Place, 200=PickGroup
            # 1=JointMove(legacy), 5=SmartAO, 6=EndToolDO
            # 24=If(조건), 25=Else, 26=If(변수)
            # 30=WaitFor, 21=LoopBreak, 23=ToolSensing
            
            if t in [102, 103]:
                # ★ JointMove(102) / FrameMove(103): 3단계 참조 해석
                # program[name] → moveList[name] → wpList[id] → q[], p[]
                mv = move_map.get(node.name, {})
                node.move_data = mv  # 이동 설정 전체 보존
                node.boundary = mv.get("boundary", {"velLevel": 5, "accLevel": 5})
                node.tcp = mv.get("tcp", [0,0,0,0,0,0])
                node.refFrame = mv.get("refFrame", {"type": 1, "tref": [0,0,0,0,0,0]})
                node.intpl = mv.get("intpl", 0)
                node.offset = mv.get("offset", None)
                node.blendOpt = mv.get("blendOpt", None)
                
                # 웨이포인트 해석 (다중 웨이포인트 지원)
                node.resolved_waypoints = []
                for wp_ref in mv.get("wpList", []):
                    wp_id = str(wp_ref.get("id", ""))
                    real_wp = wp_map.get(wp_id, {})
                    if real_wp:
                        wp_vo = WaypointVO(
                            j_pos=real_wp.get("q", [0]*6),
                            t_pos=real_wp.get("p", [0]*6),
                            blend_radius=real_wp.get("blendRadius", 0)
                        )
                        node.resolved_waypoints.append({"id": wp_id, "wp": wp_vo, "raw": real_wp})
                
                # 첫 번째 웨이포인트를 대표 좌표로 설정
                if node.resolved_waypoints:
                    first = node.resolved_waypoints[0]
                    node.target_q = first["wp"].j_pos
                    node.target_p = first["wp"].t_pos
                    node.blending_radius = first["wp"].blend_radius
                else:
                    # ★ moveList/wpList 3단계 참조 실패 시 __raw__에서 직접 읽기
                    all_wps = raw_node.get("all_waypoints", [])
                    if all_wps:
                        # ★ 다중 웨이포인트 복원
                        node.resolved_waypoints = []
                        for i, awp in enumerate(all_wps):
                            wp = WaypointVO(j_pos=awp.get("q", [0]*6), t_pos=awp.get("p", [0]*6))
                            node.resolved_waypoints.append({
                                "id": awp.get("id", f"wp_{i}"),
                                "wp": wp,
                                "raw": {"q": awp.get("q", [0]*6), "p": awp.get("p", [0]*6)}
                            })
                        first = node.resolved_waypoints[0]
                        node.target_q = first["wp"].j_pos
                        node.target_p = first["wp"].t_pos
                    else:
                        node.target_q = raw_node.get("q", [0]*6)
                        node.target_p = raw_node.get("p", [0]*6)
                        # __raw__에 좌표가 있으면 가상 waypoint 생성
                        if any(v != 0 for v in node.target_q):
                            node.resolved_waypoints = [{
                                "id": "raw_0",
                                "wp": WaypointVO(j_pos=node.target_q, t_pos=node.target_p),
                                "raw": {"q": node.target_q, "p": node.target_p}
                            }]
                    node.blending_radius = 0
            
            elif t in [1]:
                # Legacy JointMove (거의 안 씀, 하위호환)
                if "wpList" in raw_node and len(raw_node["wpList"]) > 0:
                    wp_ref = raw_node["wpList"][0]
                    w_id = str(wp_ref.get("id", ""))
                    wp_raw = wp_map.get(w_id, {})
                    if wp_raw:
                        wp = WaypointVO(t_pos=wp_raw.get("p", [0]*6), j_pos=wp_raw.get("q", [0]*6))
                        node.target_q = wp.j_pos
                        node.target_p = wp.t_pos
                elif "target" in raw_node:
                    target = raw_node["target"]
                    point = target.get("point", {})
                    node.target_q = point.get("q", [0]*6)
                    node.target_p = point.get("p", [0]*6)
                    
            elif t == 4:
                # SmartDO (디지털 출력)
                node.doList = raw_node.get("doList", [])
                
            elif t == 5:
                # SmartAO (아날로그 출력)
                node.aoList = raw_node.get("aoList", [])
                
            elif t == 6:
                # EndToolDO
                node.endtoolDoList = raw_node.get("endtoolDoList", [])
                
            elif t == 20:
                # Loop (반복문)
                # count 필드: 양수=N회, 없거나 음수=무한루프
                node.count = raw_node.get("count", None)
                # DO 참조 (toolCommand) — 일부 파일에서 count가 toolCmd ID로 사용됨
                # toolInfo에서 실제 DO 매핑 추출
                if node.count is not None and node.count >= 0:
                    # 진짜 Loop의 count는 보통 -1(무한) 또는 양수(반복횟수)
                    pass
                    
            elif t == 21:
                # LoopBreak
                pass
                
            elif t == 22:
                # Wait (시간 대기)
                node.time = raw_node.get("time", 1.0)
                node.diList = raw_node.get("diList", [])
                node.endtoolDiList = raw_node.get("endtoolDiList", [])
                
            elif t == 23:
                # Switch / 조건부 대기 (time + cond)
                node.time = raw_node.get("time", 0)
                node.cond = raw_node.get("cond", {})
                
            elif t == 24:
                # If (변수 조건 분기, 자식 有)
                node.cond = raw_node.get("cond", {})
                    
            elif t == 25:
                # Else If (변수 조건, cond 有, 자식 有)
                node.cond = raw_node.get("cond", {})
                
            elif t == 26:
                # Else (무조건, 키 없음, 자식 有)
                pass
                
            elif t == 28:
                # Wait (DI 대기 - 시간 포함)
                node.time = raw_node.get("time", 0)
                node.diList = raw_node.get("diList", [])
                node.endtoolDiList = raw_node.get("endtoolDiList", [])
                
            elif t == 29:
                # If[DI] / WaitFor[DI] (자식 유무로 구분)
                node.diList = raw_node.get("diList", [])
                node.endtoolDiList = raw_node.get("endtoolDiList", [])
                
            elif t == 30:
                # WaitFor (조건 대기)
                node.diList = raw_node.get("diList", [])
                node.endtoolDiList = raw_node.get("endtoolDiList", [])
                
            elif t == 40:
                # ToolCommand
                node.toolCmd = raw_node.get("toolCmd", "")
                
            elif t == 41:
                # ToolSensing (alt)
                node.sensName = raw_node.get("sensName", "")
                
            elif t == 100:
                # Folder (그룹 컨테이너 / Home)
                pass  # children은 pId로 자동 연결
                
            elif t in [200]:  # Pick Group
                node.groupName = raw_node.get("groupName", "")
                
            elif t in [201, 202]:  # Pick / Place
                node.toolId = raw_node.get("toolId", 1)
                node.sensName = raw_node.get("sensName", "")
                target = raw_node.get("target", {})
                node.target_type = target.get("type", None)
                
                # ★ target.type이 없거나 None이면 __raw__ 최상위에서 fallback
                if not node.target_type and raw_node.get("target_type") is not None:
                    node.target_type = raw_node.get("target_type", 0)
                
                if node.target_type == 1:
                    raw_pallet_id = target.get("pallet", {}).get("palletId", "")
                    
                    # Extract pallet info
                    pallet_info_array = []
                    main_prog = next((n for n in data.get("program", []) if n.get("type") == 999), None)
                    if main_prog and "palletInfo" in main_prog:
                        pallet_info_array = main_prog["palletInfo"]
                    elif "palletInfo" in data:
                        pallet_info_array = data["palletInfo"]
                        
                    p_info = next((p for p in pallet_info_array if str(p.get("id")) == str(raw_pallet_id)), None)
                    if not p_info:
                        p_info = next((p for p in pallet_info_array if str(p.get("name")) == str(raw_pallet_id)), None)
                        
                    if p_info:
                        node.target_pallet_name = p_info.get("name", str(raw_pallet_id))
                        node.target_pallet_id = p_info.get("id", raw_pallet_id)
                        sz = p_info.get("size", [2,2])
                        if "m" in p_info:
                            sz = [p_info.get("m", 2), p_info.get("n", 2)]
                            if "l" in p_info:
                                sz.append(p_info.get("l", 1))
                        node.p_data = {"size": sz, "points": p_info.get("points", [])}
                    else:
                        node.target_pallet_name = str(raw_pallet_id)
                        node.target_pallet_id = raw_pallet_id
                    
                    # ★ palletInfo에서 못 찾았으면 __raw__에서 직접 p_data 복원
                    if not getattr(node, "p_data", None) and raw_node.get("p_data"):
                        node.p_data = raw_node["p_data"]
                        node.target_pallet_name = raw_node.get("target_pallet_name", "")
                        node.target_pallet_id = raw_node.get("target_pallet_id", "")
                else:
                    node.target_q = target.get("point", {}).get("q", raw_node.get("q", [0]*6))
                    node.target_p = target.get("point", {}).get("p", raw_node.get("p", [0]*6))
                    
                node.approach = raw_node.get("approach", {})
                node.retract = raw_node.get("retract", {})
                node.retract_z = node.approach.get("distance", 0.15)
                
            elif t == 999:
                # Program Settings
                pass
                
            elif t == 2 or t == 3:
                # Variables
                node.varList = raw_node.get("varList", [])
                
            elif t == 250:  # Call
                pass
            elif t in [104, 105]:  # PalletDef
                pass
            elif t == 302:  # indyCARE / Force
                pass
            elif t == 32:   # SpeedRatio
                node.prgSpdRatio = raw_node.get("prgSpdRatio", 100)
                
            prog.nodes.append(node)
            
        prog.next_node_id = max_node_id + 1
        
        max_wp_id = -1
        for w in prog._raw_wpList:
            try:
                wid = int(w.get("id", -1))
                if wid > max_wp_id: max_wp_id = wid
            except (ValueError, TypeError):
                pass
        prog.next_wp_id = max_wp_id + 1
        
        return prog

    def save_to_json(self, program: ContyProgram, filepath: str):
        # We start with the full parsed data to retain keys like toolInfo, indyCareInfo, collisionPolicy
        data = program._raw_full_data.copy() if hasattr(program, "_raw_full_data") else {}
        
        data["info"] = program._raw_info
        data["wpList"] = program._raw_wpList.copy()
        data["moveList"] = program._raw_moveList
        # Only write palletInfo to root if the original data had it at root level
        if "palletInfo" in (program._raw_full_data if hasattr(program, "_raw_full_data") else {}):
            data["palletInfo"] = program.pallets
        data["program"] = []
        
        for node in program.nodes:
            # Baseline is __raw__, so we never lose attributes like sensName, tcp, refFrame etc.
            n_dict = getattr(node, "__raw__", {}).copy()
            
            # Apply essential DDD structural properties
            n_dict["enable"] = node.enable
            n_dict["type"] = node.type
            n_dict["pId"] = node.pId
            n_dict["id"] = node.id
            if hasattr(node, "name") and node.name:
                n_dict["name"] = node.name
                
            # Override specific properties handled by UI editors
            if node.type in [102, 103]:  # JointMove / FrameMove
                # UI에서 boundary를 수정했으면 moveList에도 반영
                boundary = getattr(node, "boundary", None)
                if boundary and "moveList" in data:
                    for mv in data["moveList"]:
                        if mv.get("name") == node.name:
                            mv["boundary"] = boundary
                            break
                # UI에서 웨이포인트 좌표를 수정했으면 wpList에도 반영
                resolved = getattr(node, "resolved_waypoints", [])
                for wp_entry in resolved:
                    wp_id = wp_entry["id"]
                    wp_vo = wp_entry["wp"]
                    existing_wp = next((w for w in data["wpList"] if str(w.get("id")) == str(wp_id)), None)
                    if existing_wp:
                        existing_wp["q"] = wp_vo.j_pos
                        existing_wp["p"] = wp_vo.t_pos
                        
            elif node.type in [1]:  # Legacy JointMove
                if node.wp_id is not None and node.waypoint is not None:
                    n_dict["wpList"] = [{"t": 2, "id": node.wp_id}]
                    existing_wp = next((w for w in data["wpList"] if w.get("id") == node.wp_id), None)
                    if not existing_wp:
                        data["wpList"].append({
                            "tBase": 0, "type": 0, "p": node.waypoint.t_pos,
                            "stopBlend": True, "q": node.waypoint.j_pos,
                            "blendRadius": node.waypoint.blend_radius,
                            "name": f"WP_{node.wp_id}", "id": node.wp_id
                        })
                    else:
                        existing_wp["p"] = node.waypoint.t_pos
                        existing_wp["q"] = node.waypoint.j_pos
                        existing_wp["blendRadius"] = node.waypoint.blend_radius
                    
            elif node.type == 20:  # Loop
                # ★ count는 _build_nodes에서 이미 __raw__에 올바르게 설정됨
                # n_dict는 __raw__.copy()이므로 이미 count가 포함됨
                pass
                    
            elif node.type in [201, 202]: # Pick / Place
                # Update approach/retract directly from DDD node
                n_dict["approach"] = getattr(node, "approach", n_dict.get("approach", {
                    "direction": 0, "boundary": {"velLevel": 3, "accLevel": 3},
                    "distance": getattr(node, "retract_z", 0.15), "waitTime": 0, "waitFor": {"type": 0, "time": 0}
                }))
                n_dict["retract"] = getattr(node, "retract", n_dict.get("retract", {
                    "direction": 1, "boundary": {"velLevel": 3, "accLevel": 3},
                    "distance": getattr(node, "retract_z", 0.15), "waitTime": 0, "waitFor": {"type": 0, "time": 0}
                }))
                n_dict["toolId"] = getattr(node, "toolId", 1)
                
                target = n_dict.get("target", {"type": 0, "boundary": {"velLevel": 3, "accLevel": 3}, "pallet": {}, "point": {"q": [], "p": []}})
                target["type"] = getattr(node, "target_type", target.get("type", 0))
                
                if target["type"] == 1:
                    target["pallet"]["palletId"] = getattr(node, "target_pallet_id", getattr(node, "target_pallet_name", target["pallet"].get("palletId", "")))
                    if hasattr(node, "start_idx_var"):
                        target["pallet"]["startingIdxVar"] = {"value": getattr(node, "start_idx_var", 0), "type": 1}
                    if hasattr(node, "curr_idx_var"):
                        target["pallet"]["currentIdxVar"] = {"value": getattr(node, "curr_idx_var", ""), "type": 10}
                    
                    # -----------------------------------------------------
                    # 팔레트 상세 정보(Points, Size 등) 전역 배열에 동기화
                    # -----------------------------------------------------
                    if hasattr(node, "p_data") and node.p_data:
                        pid = target["pallet"]["palletId"]
                        pname = getattr(node, "target_pallet_name", str(pid))
                        
                        # APK 호환: palletInfo는 반드시 Main Program (type 999) 내부에 있어야 함
                        main_prog_node = next((n for n in data["program"] if n.get("type") == 999), None)
                        if main_prog_node is not None:
                            if "palletInfo" not in main_prog_node:
                                main_prog_node["palletInfo"] = []
                            existing_p = next((p for p in main_prog_node["palletInfo"] if str(p.get("id")) == str(pid) or str(p.get("name")) == str(pname)), None)
                            if not existing_p:
                                existing_p = {"name": pname, "id": pid}
                                main_prog_node["palletInfo"].append(existing_p)
                                
                            if "points" in node.p_data:
                                existing_p["points"] = node.p_data["points"]
                            if "size" in node.p_data:
                                existing_p["m"] = node.p_data["size"][0]
                                existing_p["n"] = node.p_data["size"][1]
                                if len(node.p_data["size"]) >= 3:
                                    existing_p["l"] = node.p_data["size"][2]

                        # 루트에도 저장 (안전장치)
                        if "palletInfo" not in data:
                            data["palletInfo"] = []
                        
                        existing_p_root = next((p for p in data["palletInfo"] if str(p.get("id")) == str(pid) or str(p.get("name")) == str(pname)), None)
                        if not existing_p_root:
                            existing_p_root = {"name": pname, "id": pid}
                            data["palletInfo"].append(existing_p_root)
                            
                        if "points" in node.p_data:
                            existing_p_root["points"] = node.p_data["points"]
                        if "size" in node.p_data:
                            existing_p_root["m"] = node.p_data["size"][0]
                            existing_p_root["n"] = node.p_data["size"][1]
                            if len(node.p_data["size"]) >= 3:
                                existing_p_root["l"] = node.p_data["size"][2]
                            
                        target["pallet"]["currentIdxVar"] = {"value": getattr(node, "curr_idx_var", ""), "type": 10}
                else:
                    if not "point" in target: target["point"] = {}
                    target["point"]["q"] = getattr(node, "target_q", getattr(node, "joint_pos", target["point"].get("q", [0]*6)))
                    target["point"]["p"] = getattr(node, "target_p", getattr(node, "task_pos", target["point"].get("p", [0]*6)))
                n_dict["target"] = target
                
            elif node.type in [22, 28]:  # Wait (시간/DI)
                n_dict["time"] = getattr(node, "time", n_dict.get("time", 0))
                n_dict["diList"] = getattr(node, "diList", n_dict.get("diList", []))
            elif node.type in [29, 30]:  # If[DI] / Else[DI]
                n_dict["diList"] = getattr(node, "diList", n_dict.get("diList", []))
                n_dict["endtoolDiList"] = getattr(node, "endtoolDiList", n_dict.get("endtoolDiList", []))
            elif node.type in [24, 25]:  # If / Else If (변수 조건)
                n_dict["cond"] = getattr(node, "cond", n_dict.get("cond", {}))

            # Preserve original boundary values as-is (do not clamp)
            # The user sets velLevel/accLevel intentionally; overriding them causes
            # unexpected slowdowns on the real controller.

            data["program"].append(n_dict)
            
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    # ───────────────────────────────────────────────────────────────────
    # APK 호환 내보내기 (표준 Conty 포맷)
    #
    # 우리 앱 내부 저장(save_to_json)은 q/p를 노드 루트에 박는 비표준 형식이지만,
    # APK 티칭펜던트는 program/moveList/wpList 3단 분리 구조만 인식한다.
    # 이 메서드는 동일한 ContyProgram을 표준 형식으로 직렬화한다.
    #
    # 변환 규칙:
    #   - Config(type=999)은 id=1, Variables(type=2)는 id=2 강제 할당
    #   - 나머지 program 노드는 3부터 순차 id 할당 (구 id가 중복돼도 unique 보장)
    #   - JointMove(102)/FrameMove(103): waypoint를 모두 wpList[]로 분리, moveList[] 항목
    #     생성, program[]에는 메타({type,enable,pId,name,id})만 남김
    #   - Loop(20): count는 무한이면 -1, 유한이면 양의 정수
    #   - Pick(201)/Place(202): target.point에 좌표 채우기, 우리 자체 필드는 제거
    #   - pId 매핑: 부모 id 재매핑 (구 id 중복 가능성 때문에 객체 참조로 추적)
    # ───────────────────────────────────────────────────────────────────
    def save_to_conty_json(self, program: ContyProgram, filepath: str):
        """표준 Conty(APK 티칭펜던트 호환) JSON 포맷으로 저장."""
        if getattr(program, "name", None):
            prog_name = program.name
        elif hasattr(program, "_raw_info"):
            prog_name = program._raw_info.get("name", "ExportedProgram")
        else:
            prog_name = "ExportedProgram"
        out = {
            "info": {"name": prog_name},
            "wpList": [],
            "program": [],
            "moveList": [],
        }

        nodes = list(getattr(program, "nodes", []) or [])

        # ─── 1) Config(999) / Variables(2) 강제 첫 두 항목 ───────────
        config_node = next((n for n in nodes if n.type == 999), None)
        var_node = next((n for n in nodes if n.type == 2), None)

        config_raw = (getattr(config_node, "__raw__", {}) or {}).copy() if config_node else {}
        config_raw.update({"type": 999, "enable": True, "pId": 0, "id": 1})
        config_raw.setdefault("collisionPolicy", {"policy": 0, "time": 2})
        config_raw.setdefault("indyCareInfo", {})
        config_raw.setdefault("palletInfo", [])
        config_raw.setdefault("toolInfo", [])
        config_raw.setdefault("visionInfo", {"useVision": False})
        config_raw.setdefault("conveyorConfigInfo", {"conveyorConfig": []})
        # config 노드에 표준 외 필드(q, p, name, wpList 등) 잔재 정리
        for k in ("q", "p", "name", "wpList", "all_waypoints", "count", "t_type",
                  "p_name", "p_data", "move_type", "expanded_layer_nodes",
                  "target", "target_type", "approach", "retract", "boundary",
                  "tcp", "refFrame", "intpl", "b_radius", "toolId", "sensName"):
            config_raw.pop(k, None)
        out["program"].append(config_raw)

        var_raw = (getattr(var_node, "__raw__", {}) or {}).copy() if var_node else {}
        var_raw.update({"type": 2, "enable": True, "pId": 0, "id": 2})
        var_raw.setdefault("varList", [])
        # variables 노드도 비표준 필드 모두 제거 (varList만 유지)
        for k in ("q", "p", "name", "wpList", "all_waypoints", "count",
                  "t_type", "p_name", "p_data", "move_type",
                  "expanded_layer_nodes", "target", "target_type",
                  "approach", "retract", "boundary", "tcp", "refFrame",
                  "intpl", "b_radius", "toolId", "sensName"):
            var_raw.pop(k, None)
        out["program"].append(var_raw)

        # ─── 2) id 매핑 (object identity 기반: 구 id 중복 안전) ───
        next_id = 3
        next_wp_id = 0
        id_map = {id(config_node): 1} if config_node else {}
        if var_node:
            id_map[id(var_node)] = 2

        # 우리 자체 필드 (export 시 제거할 키)
        STRIP_KEYS = {
            "all_waypoints", "t_type", "p_name", "p_data", "move_type",
            "expanded_layer_nodes", "target_pallet_name", "target_pallet_id",
            "app_data", "ret_data", "b_radius",
        }

        def _resolve_parent_new_id(child) -> int:
            """child의 pId를 기준으로, 이미 처리된 가장 가까운 부모 노드의 새 id를 찾는다."""
            for prev in reversed(processed):
                if prev.id == child.pId:
                    return id_map.get(id(prev), 0)
            return 0

        processed = []
        if config_node: processed.append(config_node)
        if var_node: processed.append(var_node)

        for node in nodes:
            if node is config_node or node is var_node:
                continue

            new_id = next_id; next_id += 1
            id_map[id(node)] = new_id
            parent_id = _resolve_parent_new_id(node)
            processed.append(node)

            raw = (getattr(node, "__raw__", {}) or {}).copy()
            # 우리 자체 필드 모두 제거
            for k in STRIP_KEYS:
                raw.pop(k, None)

            t = node.type

            if t in (102, 103):
                # ─ Move: program 메타 + moveList + wpList 분리 ─
                name = node.name or (f"jmove-{new_id:02d}" if t == 102 else f"tmove-{new_id:02d}")

                # waypoint 수집: resolved_waypoints 우선, 없으면 raw q/p에서 단일 생성
                wps = getattr(node, "resolved_waypoints", []) or []
                wp_refs = []
                for wp_entry in wps:
                    wp_vo = wp_entry.get("wp") if isinstance(wp_entry, dict) else None
                    if wp_vo is not None:
                        q_v = list(wp_vo.j_pos) if wp_vo.j_pos else [0]*6
                        p_v = list(wp_vo.t_pos) if wp_vo.t_pos else [0]*6
                        blend_r = float(getattr(wp_vo, "blend_radius", 0) or 0)
                    else:
                        q_v = list(wp_entry.get("q", [0]*6))
                        p_v = list(wp_entry.get("p", [0]*6))
                        blend_r = float(wp_entry.get("blendRadius", 0) or 0)
                    out["wpList"].append({
                        "id": next_wp_id,
                        "type": 0,
                        "tBase": 0,
                        "stopBlend": True,
                        "blendRadius": blend_r,
                        "name": f"{name}-{next_wp_id:02d}",
                        "q": q_v,
                        "p": p_v,
                    })
                    wp_refs.append({"t": 2, "id": next_wp_id})
                    next_wp_id += 1

                if not wp_refs:
                    # all_waypoints fallback (제거된 raw에서 다시 한번 조회는 안 되므로 원본에서)
                    orig_raw = getattr(node, "__raw__", {}) or {}
                    aw = orig_raw.get("all_waypoints", [])
                    if aw:
                        for awp in aw:
                            out["wpList"].append({
                                "id": next_wp_id, "type": 0, "tBase": 0,
                                "stopBlend": True,
                                "blendRadius": float(awp.get("blendRadius", 0) or 0),
                                "name": f"{name}-{next_wp_id:02d}",
                                "q": list(awp.get("q", [0]*6)),
                                "p": list(awp.get("p", [0]*6)),
                            })
                            wp_refs.append({"t": 2, "id": next_wp_id})
                            next_wp_id += 1
                    else:
                        # 단일 q/p
                        q_v = raw.get("q") or [0]*6
                        p_v = raw.get("p") or [0]*6
                        out["wpList"].append({
                            "id": next_wp_id, "type": 0, "tBase": 0,
                            "stopBlend": True, "blendRadius": 0,
                            "name": f"{name}-{next_wp_id:02d}",
                            "q": list(q_v), "p": list(p_v),
                        })
                        wp_refs.append({"t": 2, "id": next_wp_id})
                        next_wp_id += 1

                # moveList 항목
                mv_entry = {
                    "type": t,
                    "name": name,
                    "intpl": raw.get("intpl", 1),
                    "tcp": raw.get("tcp", [0.0]*6),
                    "refFrame": raw.get("refFrame", {"type": 1, "tref": [0]*6}),
                    "boundary": raw.get("boundary", {"velLevel": 3, "accLevel": 3}),
                    "blendOpt": raw.get("blendOpt", {"processLoop": False, "constant": False}),
                    "wpList": wp_refs,
                }
                if t == 103:
                    mv_entry["offset"] = raw.get("offset", {"type": 0, "pos": [0, 0, 0]})
                out["moveList"].append(mv_entry)

                # program 메타
                out["program"].append({
                    "type": t, "enable": True, "pId": parent_id,
                    "name": name, "id": new_id,
                })

            elif t == 20:  # Loop
                cnt = raw.get("count")
                try:
                    cnt = int(cnt) if cnt is not None else -1
                except (TypeError, ValueError):
                    cnt = -1
                if cnt <= 0:
                    cnt = -1
                out["program"].append({
                    "type": 20, "enable": True, "pId": parent_id,
                    "count": cnt, "id": new_id,
                })

            elif t in (201, 202):  # Pick / Place
                # 거리 단위 정규화: UI는 mm(50.0)로 받지만 표준은 m(0.05). 1.0보다 크면 mm로 간주.
                def _dist_m(v, default=0.05):
                    try: v = float(v)
                    except (TypeError, ValueError): return default
                    return v / 1000.0 if v > 1.0 else v

                target = (raw.get("target") or {}).copy()
                target.setdefault("boundary", {"velLevel": 3, "accLevel": 3})
                target.setdefault("pallet", {})
                target.setdefault("refFrame", {"type": 1, "tref": [0]*6})
                target.setdefault("tcp", [0.0]*6)

                # target.type 정규화 (null → 0, "1"/"2" → int)
                tt = target.get("type")
                if tt is None:
                    tt = raw.get("target_type")
                try:
                    tt = int(tt) if tt is not None else 0
                except (TypeError, ValueError):
                    tt = 0
                target["type"] = tt

                # ★ 팔레트(target.type=1)이면 raw["p_data"]를 표준 palletInfo로 옮긴다.
                # 표준 펜던트는 palletInfo[]에 정의된 팔레트를 target.pallet.palletId로 참조한다.
                if tt == 1:
                    p_data_raw = raw.get("p_data") or getattr(node, "p_data", None)
                    if p_data_raw and isinstance(p_data_raw, dict):
                        # palletId 결정 — 기존 raw 값 우선, 없으면 새 ID 할당
                        existing_pid = (target.get("pallet") or {}).get("palletId")
                        if not existing_pid:
                            existing_pid = raw.get("target_pallet_id") or raw.get("target_pallet_name") or f"PLT_{new_id}"

                        # config_raw["palletInfo"]에서 동일 id/name 항목 탐색
                        pinfo_list = config_raw.get("palletInfo", [])
                        if not isinstance(pinfo_list, list):
                            pinfo_list = []
                        p_entry = next((p for p in pinfo_list if str(p.get("id")) == str(existing_pid)
                                        or str(p.get("name")) == str(existing_pid)), None)
                        if p_entry is None:
                            p_entry = {"id": existing_pid, "name": str(existing_pid)}
                            pinfo_list.append(p_entry)
                            config_raw["palletInfo"] = pinfo_list

                        # 크기/좌표 동기화
                        sz = p_data_raw.get("size", [1, 1, 1])
                        p_entry["m"] = sz[0] if len(sz) > 0 else 1
                        p_entry["n"] = sz[1] if len(sz) > 1 else 1
                        if len(sz) > 2:
                            p_entry["l"] = sz[2]
                        if "points" in p_data_raw:
                            p_entry["points"] = p_data_raw["points"]

                        # target.pallet 참조 채우기
                        target["pallet"] = dict(target.get("pallet") or {})
                        target["pallet"]["palletId"] = existing_pid

                # target.point.q/p 채우기 (null인 경우 노드 루트 q/p에서)
                point = (target.get("point") or {}).copy()
                if not point.get("q") or (isinstance(point["q"], list) and not point["q"]):
                    point["q"] = raw.get("q") or [0.0]*6
                if not point.get("p") or (isinstance(point["p"], list) and not point["p"]):
                    point["p"] = raw.get("p") or [0.0]*6
                target["point"] = point

                app_in = raw.get("approach", {}) or {}
                ret_in = raw.get("retract", {}) or {}
                approach_out = {
                    "direction": int(app_in.get("direction", 0)),
                    "distance": _dist_m(app_in.get("distance"), 0.05),
                    "boundary": app_in.get("boundary", {"velLevel": 3, "accLevel": 3}),
                    "waitTime": float(app_in.get("waitTime", 0) or 0),
                    "waitFor": app_in.get("waitFor", {"type": 0, "time": 0}),
                }
                retract_out = {
                    "direction": int(ret_in.get("direction", 1)),
                    "distance": _dist_m(ret_in.get("distance"), 0.05),
                    "boundary": ret_in.get("boundary", {"velLevel": 3, "accLevel": 3}),
                    "waitTime": float(ret_in.get("waitTime", 0) or 0),
                    "waitFor": ret_in.get("waitFor", {"type": 0, "time": 0}),
                }
                entry = {
                    "type": t, "enable": True, "pId": parent_id,
                    "id": new_id,
                    "toolId": raw.get("toolId", 1),
                    "sensName": raw.get("sensName", ""),
                    "approach": approach_out,
                    "retract": retract_out,
                    "target": target,
                }
                if node.name:
                    entry["name"] = node.name
                out["program"].append(entry)

            elif t == 22:  # Wait (time)
                out["program"].append({
                    "type": 22, "enable": True, "pId": parent_id,
                    "time": raw.get("time", 0),
                    "id": new_id,
                })

            elif t == 28:  # Wait (DI)
                out["program"].append({
                    "type": 28, "enable": True, "pId": parent_id,
                    "time": raw.get("time", 1),
                    "diList": raw.get("diList", []),
                    "id": new_id,
                })

            elif t == 4:  # SmartDO
                out["program"].append({
                    "type": 4, "enable": True, "pId": parent_id,
                    "doList": raw.get("doList", []),
                    "id": new_id,
                })

            elif t == 5:  # SmartAO
                out["program"].append({
                    "type": 5, "enable": True, "pId": parent_id,
                    "aoList": raw.get("aoList", []),
                    "id": new_id,
                })

            elif t == 6:  # Endtool DO
                out["program"].append({
                    "type": 6, "enable": True, "pId": parent_id,
                    "endtoolDoList": raw.get("endtoolDoList", []),
                    "id": new_id,
                })

            elif t == 100:  # Home / Folder
                # type=100은 실제로 Move Home (APK 표준). 이름이 있으면 Folder로 쓰는 경우가 있어 보존.
                e = {"type": 100, "enable": True, "pId": parent_id, "id": new_id}
                if node.name:
                    e["name"] = node.name
                out["program"].append(e)

            elif t == 101:  # Move Zero
                out["program"].append({
                    "type": 101, "enable": True, "pId": parent_id, "id": new_id,
                })

            elif t == 21:  # Loop Break
                out["program"].append({
                    "type": 21, "enable": True, "pId": parent_id, "id": new_id,
                })

            elif t in (24, 25):  # If / Elif (변수)
                out["program"].append({
                    "type": t, "enable": True, "pId": parent_id,
                    "cond": raw.get("cond", {}),
                    "id": new_id,
                })

            elif t == 26:  # Else
                out["program"].append({
                    "type": 26, "enable": True, "pId": parent_id, "id": new_id,
                })

            elif t in (29, 30):  # If/Else (DI)
                out["program"].append({
                    "type": t, "enable": True, "pId": parent_id,
                    "diList": raw.get("diList", []),
                    "endtoolDiList": raw.get("endtoolDiList", []),
                    "id": new_id,
                })

            elif t == 32:  # Speed Ratio
                out["program"].append({
                    "type": 32, "enable": True, "pId": parent_id,
                    "prgSpdRatio": raw.get("prgSpdRatio", 100),
                    "id": new_id,
                })

            elif t == 40:  # Tool Command
                out["program"].append({
                    "type": 40, "enable": True, "pId": parent_id,
                    "toolCmd": raw.get("toolCmd", {}),
                    "id": new_id,
                })

            elif t == 41:  # Stop
                out["program"].append({
                    "type": 41, "enable": True, "pId": parent_id, "id": new_id,
                })

            else:
                # 알려지지 않은 타입: raw에서 우리 비표준 키만 제거하고 통과
                raw.update({"type": t, "enable": True, "pId": parent_id, "id": new_id})
                if node.name:
                    raw["name"] = node.name
                out["program"].append(raw)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(out, f, ensure_ascii=False, indent=4)
        return filepath
