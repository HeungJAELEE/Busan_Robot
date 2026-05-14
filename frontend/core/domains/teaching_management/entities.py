from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass(frozen=True)
class WaypointVO:
    """Value Object representing coordinates for a teaching node."""
    t_pos: List[float] = field(default_factory=lambda: [0.0]*6)
    j_pos: List[float] = field(default_factory=lambda: [0.0]*6)
    blend_radius: float = 0.0

class TeachingNode:
    """Entity representing a single Conty command/node."""
    def __init__(self, node_id: int, pId: int, internal_type: int):
        self.id = node_id
        self.pId = pId
        self.type = internal_type
        
        # Data fields based on type
        self.enable = True
        self.wp_id: Optional[int] = None
        self.waypoint: Optional[WaypointVO] = None
        
        self.count: Optional[int] = None
        self.time: Optional[float] = None
        self.diList: Optional[list] = None
        self.endtoolDiList: Optional[list] = None
        
        # Target details (for Palletizing, Tool action)
        self.toolId: Optional[int] = None
        self.target: Optional[dict] = None
        self.approach: Optional[dict] = None
        self.retract: Optional[dict] = None
        
        # Extracted parsed properties for OOD/HMI rendering
        self.name: str = ""
        self.target_q: Optional[List[float]] = None
        self.target_p: Optional[List[float]] = None
        self.target_type: Optional[int] = None
        self.target_pallet_name: Optional[str] = None
        self.target_pallet_data: Optional[dict] = None
        self.blending_radius: float = 0.0
        
        # Move By Detailed Properties
        self.offset_dx: float = 0.0
        self.offset_dy: float = 0.0
        self.offset_dz: float = 0.0
        
        # Math & Condition Properties
        self.math_var_name: Optional[str] = None
        self.math_operator: Optional[str] = None
        self.math_value: Optional[float] = None
        
        self.cond_var_name: Optional[str] = None
        self.cond_operator: Optional[str] = None
        self.cond_value: Optional[float] = None
        
        # Sub-program Call Properties
        self.sub_program_name: Optional[str] = None
        
        # Force Control / Compliance Properties
        self.force_stiffness: float = 0.0
        self.force_damping: float = 0.0
        self.force_f_max: float = 0.0
        
        # Missing Command Properties (Move C, Vision, Sync, Set AO)
        self.wp2_id: Optional[int] = None
        self.waypoint2: Optional[WaypointVO] = None
        self.vision_cam_id: int = 1
        self.vision_template_id: int = 1
        self.sync_conveyor_id: int = 1
        self.sync_start: bool = True
        self.ao_port: int = 0
        self.ao_voltage: float = 0.0
        self.switch_var_name: str = "var1"
        
        # Pallet Detailed Properties
        self.pallet_p1: dict = {}
        self.pallet_p2: dict = {}
        self.pallet_p3: dict = {}
        self.pallet_m: int = 1
        self.pallet_n: int = 1
        self.pallet_l: int = 1
        self.pallet_layer_h: float = 0.0
        self.retract_z: float = 0.15
        self.pallet_do_idx: int = -1
        self.pallet_do_wait: float = 0.5
        self.__raw__ = {}
        
    def attach_waypoint(self, wp_id: int, waypoint: WaypointVO):
        self.wp_id = wp_id
        self.waypoint = waypoint

class ContyProgram:
    """Aggregate Root representing the entire Teaching Program."""
    def __init__(self, name: str = "DigitalTwin_Export"):
        self.name = name
        self.nodes: List[TeachingNode] = []
        self.pallets: List[dict] = []
        self.variables: Dict[str, float] = {}
        self.next_node_id = 3
        self.next_wp_id = 0
        
        # Keep raw structures that are not mapped to entities yet (for full schema compatibility)
        self._raw_info = {"name": name}
        self._raw_wpList = []
        self._raw_moveList = []
        self._raw_full_data = {} # Will hold the fully parsed JSON
        
        # Default nodes
        self._add_system_config_node()
        self._add_program_start_node()
        
    def _add_system_config_node(self):
        node = TeachingNode(1, 0, 999)
        node.__raw__ = {
            "indyCareInfo": {
                "useIndyCare": False,
                "ipAddr": "0.0.0.0",
                "dataConfig": [
                    {"name": "", "type": 0},
                    {"name": "", "type": 0},
                    {"name": "", "type": 0},
                    {"name": "", "type": 0},
                    {"name": "", "type": 0}
                ]
            },
            "type": 999,
            "conveyorConfigInfo": {"conveyorConfig": []},
            "toolInfo": [],
            "visionInfo": {"useVision": False},
            "collisionPolicy": {"policy": 0, "time": 2},
            "enable": True,
            "pId": 0,
            "palletInfo": [],
            "id": 1
        }
        self.nodes.append(node)
        
    def _add_program_start_node(self):
        node = TeachingNode(2, 0, 2)
        node.__raw__ = {
            "varList": [],
            "enable": True,
            "type": 2,
            "pId": 0,
            "id": 2
        }
        self.nodes.append(node)

    def add_node(self, internal_type: int, pId: int, waypoint: Optional[WaypointVO] = None) -> TeachingNode:
        """Adds a new node following DDD business rules."""
        node_id = self.next_node_id
        self.next_node_id += 1
        
        node = TeachingNode(node_id, pId, internal_type)
        
        # Apply type-specific business rules
        if internal_type in [100, 101, 102, 103, 104, 105, 106, 110]: # Move commands require a waypoint
            if not waypoint:
                waypoint = WaypointVO()
            wp_id = self.next_wp_id
            self.next_wp_id += 1
            node.attach_waypoint(wp_id, waypoint)
        elif internal_type == 20: # Loop
            node.count = 3
        elif internal_type in [22, 23, 28]: # Wait Time / WaitFor / Wait DI
            node.time = 1.0
            if internal_type == 23:
                node.cond = {
                    "left": {"type": 10, "value": "var1"},
                    "right": {"type": 1, "value": 1},
                    "op": 0,
                }
        elif internal_type == 24: # If Condition
            node.cond_var_name = "var1"
            node.cond_operator = "=="
            node.cond_value = 0.0
        elif internal_type == 29: # Legacy Wait DI, but keeping for compatibility
            node.diList = []
            node.endtoolDiList = []
        elif internal_type == 202: # Palletizing
            node.toolId = 1
            node.target = {
                "type": 1,
                "pallet": {"palletId": 1}
            }
            node.approach = {"distance": 0.1}
            node.retract = {"distance": 0.1}
            
        self.nodes.append(node)
        return node
