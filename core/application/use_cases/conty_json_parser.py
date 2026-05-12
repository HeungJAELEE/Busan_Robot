import json

class ContyJsonParser:
    """
    Parses Neuromeka Conty App exported JSON files.
    Translates the flat list of program nodes into a tree structure compatible with our ttk.Treeview
    and Ouroboros seed.yaml.
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
        201: "Tool Action (Point)",
        202: "Palletizing Action (Pallet)",
        250: "Set Speed Ratio",
        302: "Set Care/Collision Policy"
    }

    @staticmethod
    def parse_to_tree_nodes(filepath: str):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            return {"error": f"Failed to load JSON: {str(e)}"}

        program = data.get("program", [])
        if not program:
            return {"error": "No 'program' array found in JSON."}

        # Build tree from flat list (id -> pId)
        nodes = {}
        root_nodes = []

        for cmd in program:
            node_id = cmd.get("id")
            pid = cmd.get("pId")
            cmd_type = cmd.get("type")
            
            # Generate human-readable text
            type_name = ContyJsonParser.TYPE_MAP.get(cmd_type, f"Unknown (Type {cmd_type})")
            
            text = type_name
            if cmd_type == 20: # Loop
                count = cmd.get("count", 0)
                text = f"Loop ({'Infinite' if count == -1 else count} times)"
            elif cmd_type in [22, 28]: # Wait
                time = cmd.get("time", 0)
                text = f"Wait ({time} sec)"
            elif cmd_type in [23]: # Wait Signal
                text = f"Wait (DI Signal)"
            elif cmd_type in [24, 29]: # If Signal
                text = f"If (DI Signal)"
            elif cmd_type == 201: # Tool Action
                target = cmd.get("target", {}).get("point", {}).get("p", [])
                text = f"Tool Action (Target: {[round(x, 2) for x in target[:3]] if target else 'Unknown'})"
            elif cmd_type == 202: # Palletizing Action
                pallet_id = cmd.get("target", {}).get("pallet", {}).get("palletId", "Unknown")
                text = f"Palletizing Action (Pallet ID: {pallet_id})"
            elif cmd_type in [100, 101, 102, 103]: # Move
                text = f"{type_name} Command"
                
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
                # Root nodes usually have pId 0, but sometimes Config(999) and Start(2) are roots.
                root_nodes.append(node)
            else:
                nodes[pid]["children"].append(node)

        return {"status": "success", "tree": root_nodes}

