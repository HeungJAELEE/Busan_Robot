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
                    node.target_q = [0]*6
                    node.target_p = [0]*6
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
                node.target_type = target.get("type", 0)
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
                else:
                    node.target_q = target.get("point", {}).get("q", [0]*6)
                    node.target_p = target.get("point", {}).get("p", [0]*6)
                    
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
                raw_count = getattr(node, "__raw__", {}).get("count")
                if raw_count is not None:
                    n_dict["count"] = getattr(node, "count", raw_count)
                elif hasattr(node, "count") and node.count is not None:
                    n_dict["count"] = node.count
                    
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
