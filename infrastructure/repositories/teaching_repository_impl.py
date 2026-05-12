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
        
        max_node_id = -1
        
        for raw_node in data.get("program", []):
            t = raw_node.get("type", 0)
            node_id = raw_node.get("id", 0)
            if node_id > max_node_id:
                max_node_id = node_id
                
            node = TeachingNode(node_id, raw_node.get("pId", 0), t)
            node.__raw__ = raw_node.copy()  # <--- MAGIC HAPPENS HERE: Lossless persistence
            
            node.name = raw_node.get("name", "")
            node.enable = raw_node.get("enable", True)
            
            if t in [100, 102, 103, 104, 105, 106, 110]:
                if "wpList" in raw_node and len(raw_node["wpList"]) > 0:
                    wp_ref = raw_node["wpList"][0]
                    if wp_ref.get("t") == 2:
                        w_id = wp_ref.get("id")
                        wp_raw = next((w for w in prog._raw_wpList if w.get("id") == w_id), None)
                        if wp_raw:
                            wp = WaypointVO(t_pos=wp_raw.get("p", [0]*6), j_pos=wp_raw.get("q", [0]*6), blend_radius=wp_raw.get("blendRadius", 0))
                            node.attach_waypoint(w_id, wp)
                            node.target_q = wp.j_pos
                            node.target_p = wp.t_pos
                            node.blending_radius = wp.blend_radius
                            
                if t == 110: # Move By
                    offset = raw_node.get("offset", {})
                    if "dx" in offset:
                        node.offset_dx = offset.get("dx", 0.0)
                        node.offset_dy = offset.get("dy", 0.0)
                        node.offset_dz = offset.get("dz", 0.0)
                        
            elif t == 20: # Loop
                node.count = raw_node.get("count", 3)
            elif t == 22: # Wait Time
                node.time = raw_node.get("time", 1.0)
            elif t == 28: # Wait DI
                node.time = raw_node.get("time", 1.0)
                node.diList = raw_node.get("diList", [])
            elif t == 24: # If Condition
                cond = raw_node.get("cond", {})
                node.cond_value = cond.get("right", {}).get("value", 0.0)
                op_val = cond.get("op", 0)
                op_map = {0: "==", 1: "!=", 2: ">", 3: "<", 4: ">=", 5: "<="}
                node.cond_operator = op_map.get(op_val, "==")
            elif t in [201, 202]: # Pick/Place
                node.toolId = raw_node.get("toolId", 1)
                target = raw_node.get("target", {})
                node.target_type = target.get("type", 0)
                if node.target_type == 1:
                    raw_pallet_id = target.get("pallet", {}).get("palletId", "")
                    
                    # Extract pallet info to populate UI and resolve name
                    pallet_info_array = []
                    main_prog = next((n for n in data.get("program", []) if n.get("type") == 999), None)
                    if main_prog and "palletInfo" in main_prog:
                        pallet_info_array = main_prog["palletInfo"]
                    elif "palletInfo" in data:
                        pallet_info_array = data["palletInfo"]
                        
                    # Find pallet by ID
                    p_info = next((p for p in pallet_info_array if str(p.get("id")) == str(raw_pallet_id)), None)
                    # Fallback to matching by name if ID fails
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
                                
                        node.p_data = {
                            "size": sz,
                            "points": p_info.get("points", [])
                        }
                    else:
                        node.target_pallet_name = str(raw_pallet_id)
                        node.target_pallet_id = raw_pallet_id
                else:
                    node.target_q = target.get("point", {}).get("q", [0]*6)
                    node.target_p = target.get("point", {}).get("p", [0]*6)
                    
                app = raw_node.get("approach", {})
                ret = raw_node.get("retract", {})
                node.approach = app
                node.retract = ret
                node.retract_z = app.get("distance", 0.15)
                
            elif t == 31: # Switch
                node.switch_var_name = raw_node.get("switchVar", "var1")
            elif t == 21: # Math
                node.math_var_name = raw_node.get("mathVar", "var1")
                node.math_operator = raw_node.get("mathOp", "+")
                node.math_value = raw_node.get("mathVal", 0.0)
                
            prog.nodes.append(node)
            
        prog.next_node_id = max_node_id + 1
        
        max_wp_id = -1
        for w in prog._raw_wpList:
            if w.get("id", -1) > max_wp_id: max_wp_id = w.get("id")
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
            if node.type in [103, 104, 105, 106, 110]:
                # If UI modified boundary, we must sync it to moveList
                if "boundary" in n_dict and "moveList" in data:
                    for mv in data["moveList"]:
                        if mv.get("name") == node.name or mv.get("id") == node.id:
                            mv["boundary"] = n_dict["boundary"]
                            break
                            
            if node.wp_id is not None and node.waypoint is not None:
                n_dict["wpList"] = [{"t": 2, "id": node.wp_id}]
                # We need to update wpList array in the root data as well
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
                    
            if node.type == 20: n_dict["count"] = getattr(node, "count", 3)
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
                
            elif node.type == 22: n_dict["time"] = getattr(node, "time", 1.0)
            elif node.type == 28: 
                n_dict["time"] = getattr(node, "time", 1.0)
                n_dict["diList"] = getattr(node, "diList", [])
            elif node.type == 110:
                n_dict["offset"] = {
                    "dx": getattr(node, "offset_dx", 0.0),
                    "dy": getattr(node, "offset_dy", 0.0),
                    "dz": getattr(node, "offset_dz", 0.0)
                }

            # Preserve original boundary values as-is (do not clamp)
            # The user sets velLevel/accLevel intentionally; overriding them causes
            # unexpected slowdowns on the real controller.

            data["program"].append(n_dict)
            
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
