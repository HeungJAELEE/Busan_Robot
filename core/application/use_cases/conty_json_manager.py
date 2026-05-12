from core.domains.teaching_management.entities import ContyProgram, WaypointVO
from infrastructure.repositories.teaching_repository_impl import TeachingRepositoryImpl

class ContyJsonManager:
    """
    Application Service that orchestrates teaching logic.
    Acts as a facade for the GUI to interact with the Teaching Domain Entities.
    Maintains DDD purity by delegating to ContyProgram (Aggregate Root) and Repository.
    """
    
    TYPE_MAP = {
        999: "System Config",
        1: "Move Home",
        2: "Program Start",
        3: "Program End",
        4: "Set DO",
        5: "Set AO",
        6: "Set Tool DO",
        20: "Loop",
        22: "Wait (Condition)",
        23: "Wait (DI Signal)",
        24: "If (Condition)",
        28: "Wait (Time)",
        29: "If (DI Signal)",
        40: "Tool Command",
        41: "Sensor Command",
        100: "Move J",
        101: "Move L",
        102: "Move B",
        103: "Move B (Advanced)",
        200: "Call Subprogram",
        201: "Pick (Single Point)",
        202: "Place (Palletizing)",
        250: "Set Speed Ratio",
        302: "Set Care/Collision Policy"
    }

    def __init__(self):
        self.repository = TeachingRepositoryImpl()
        self.program = ContyProgram()
        
    def reset(self):
        self.program = ContyProgram()
        
    def load_from_file(self, filepath: str):
        try:
            self.program = self.repository.load_from_json(filepath)
            return {"status": "success"}
        except ValueError as ve:
            return {"error": str(ve)}
        except Exception as e:
            return {"error": f"Failed to load JSON: {str(e)}"}
            
    def save_to_file(self, filepath: str):
        try:
            self.repository.save_to_json(self.program, filepath)
            return {"status": "success"}
        except Exception as e:
            return {"error": f"Failed to save JSON: {str(e)}"}

    def add_node(self, cmd_name: str, pId: int, t_pos=None, j_pos=None) -> int:
        """Translates UI command into a Domain Entity addition."""
        internal_type = 2
        for k, v in self.TYPE_MAP.items():
            if cmd_name.replace(" ", "") in v.replace(" ", "") or cmd_name.split(" ")[0] in v:
                internal_type = k
                break
                
        if cmd_name == "Move J": internal_type = 100
        elif cmd_name == "Move L": internal_type = 101
        elif cmd_name == "Move B": internal_type = 102
        elif cmd_name == "Set DO": internal_type = 4
        elif cmd_name == "Wait": internal_type = 28
        elif cmd_name == "Loop": internal_type = 20
        elif cmd_name == "Call": internal_type = 200
        elif cmd_name == "If (DI)": internal_type = 29
        elif cmd_name == "Palletizing": internal_type = 202
        
        wp = WaypointVO(t_pos or [0]*6, j_pos or [0]*6) if t_pos or j_pos else None
        
        node = self.program.add_node(internal_type, pId, wp)
        return node.id
        
    def get_ui_tree(self):
        """Converts Domain Entities to UI tree format."""
        nodes = {}
        root_nodes = []

        for node in self.program.nodes:
            type_name = self.TYPE_MAP.get(node.type, f"Unknown (Type {node.type})")
            text = type_name
            
            # Reconstruct contextual text
            if node.type == 20:
                raw_dict = getattr(node, '__raw__', {})
                count = node.count if node.count is not None else raw_dict.get('count', 0)
                text = f"Loop ({'Infinite' if count == -1 else count} times)"
            elif node.type in [22, 28]:
                raw_dict = getattr(node, '__raw__', {})
                time_val = node.time if getattr(node, 'time', None) is not None else raw_dict.get('time', 0)
                text = f"Wait ({time_val} sec)"
            elif node.type in [23]: text = "Wait (DI Signal)"
            elif node.type in [24, 29]: text = "If (DI Signal)"
            elif node.type == 201:
                raw_dict = getattr(node, '__raw__', {})
                target_dict = raw_dict.get("target") or {}
                point_dict = target_dict.get("point") or {}
                target = point_dict.get("p", [])
                text = f"Pick (Target: {[round(x, 2) for x in target[:3]] if target else 'Unknown'})"
            elif node.type == 202:
                raw_dict = getattr(node, '__raw__', {})
                target_dict = node.target if node.target is not None else (raw_dict.get("target") or {})
                pallet_dict = target_dict.get("pallet") or {}
                pallet_id = pallet_dict.get("palletId", "Unknown")
                text = f"Place (Palletizing) (Pallet ID: {pallet_id})"
            elif node.type in [100, 101, 102, 103]:
                text = f"{type_name} Command"
                
            ui_node = {
                "id": node.id,
                "pid": node.pId,
                "text": text,
                "children": [],
                "raw": getattr(node, '__raw__', {"type": node.type})
            }
            nodes[node.id] = ui_node

        for node_id, ui_node in nodes.items():
            pid = ui_node["pid"]
            if pid == 0 or pid not in nodes:
                root_nodes.append(ui_node)
            else:
                nodes[pid]["children"].append(ui_node)

        return root_nodes
