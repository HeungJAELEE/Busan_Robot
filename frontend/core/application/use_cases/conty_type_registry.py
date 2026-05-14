from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple


STABLE_TAG = "compat_stable"
UNSTABLE_TAG = "compat_unstable"
SYSTEM_TAG = "compat_system"

STABLE_TEXT_COLOR = "#000000"
UNSTABLE_TEXT_COLOR = "#FFFFFF"


@dataclass(frozen=True)
class ContyTypeInfo:
    type_id: int
    label: str
    stable: bool
    note: str = ""


@dataclass(frozen=True)
class ContyCommand:
    ui_name: str
    label: str
    type_id: int
    color: str
    stable: bool


TYPE_REGISTRY: Dict[int, ContyTypeInfo] = {
    1: ContyTypeInfo(1, "Stop", True),
    2: ContyTypeInfo(2, "Variables", True),
    3: ContyTypeInfo(3, "Var Assign", True),
    4: ContyTypeInfo(4, "SmartDO", True),
    5: ContyTypeInfo(5, "SmartAO", True),
    6: ContyTypeInfo(6, "EndTool DO", True),
    20: ContyTypeInfo(20, "Loop", True),
    21: ContyTypeInfo(21, "Loop Break", True),
    22: ContyTypeInfo(22, "Wait", True),
    23: ContyTypeInfo(23, "Wait For", True),
    24: ContyTypeInfo(24, "If", True),
    25: ContyTypeInfo(25, "Elif", True),
    26: ContyTypeInfo(26, "Else", True),
    28: ContyTypeInfo(28, "Wait DI", True),
    29: ContyTypeInfo(29, "If DI", True),
    30: ContyTypeInfo(30, "Elif DI", True),
    40: ContyTypeInfo(40, "Tool Command", True),
    41: ContyTypeInfo(41, "Tool Sensing", True),
    50: ContyTypeInfo(50, "Exec Python", False, "Manufacturer-only command; APK sample coverage is missing."),
    100: ContyTypeInfo(100, "Home", True),
    101: ContyTypeInfo(101, "Move Zero", False, "Manufacturer-only command; direct editor support is limited."),
    102: ContyTypeInfo(102, "JointMove", True),
    103: ContyTypeInfo(103, "FrameMove", True),
    104: ContyTypeInfo(104, "Move 104", False, "Observed in APK samples, but editor/export semantics need confirmation."),
    105: ContyTypeInfo(105, "Move 105", False, "Observed in APK samples, but editor/export semantics need confirmation."),
    106: ContyTypeInfo(106, "Move 106", False, "Manufacturer example uses 106 for shake move; APK mapping is not proven."),
    200: ContyTypeInfo(200, "Pick Group", True),
    201: ContyTypeInfo(201, "Pick", True),
    202: ContyTypeInfo(202, "Place", True),
    250: ContyTypeInfo(250, "Speed Ratio", True),
    300: ContyTypeInfo(300, "IndyCARE Count", False, "Manufacturer-only IndyCARE command."),
    301: ContyTypeInfo(301, "IndyCARE Monitoring", False, "Manufacturer-only IndyCARE command."),
    302: ContyTypeInfo(302, "Takt Time", True),
    400: ContyTypeInfo(400, "Detect", False, "PC-only extension."),
    401: ContyTypeInfo(401, "Retrieve", False, "PC-only extension."),
    901: ContyTypeInfo(901, "Call", False, "PC-only placeholder; do not export as APK-compatible Call yet."),
    902: ContyTypeInfo(902, "Force", False, "PC-only placeholder; APK type is not confirmed."),
    903: ContyTypeInfo(903, "Comment", False, "PC-only annotation."),
}


COMMAND_SECTIONS: List[Tuple[str, str, List[ContyCommand]]] = [
    (
        "▸ 모션 명령어",
        "#2E7D32",
        [
            ContyCommand("Joint Move", "JointMove", 102, "#1565C0", True),
            ContyCommand("Frame Move", "FrameMove", 103, "#2E7D32", True),
            ContyCommand("Move C", "Move C", 106, "#00796B", False),
            ContyCommand("Move Home", "Home", 100, "#0277BD", True),
            ContyCommand("Move B", "Move 104", 104, "#E65100", False),
            ContyCommand("Move By", "Move 105", 105, "#6A1B9A", False),
        ],
    ),
    (
        "▸ 흐름제어 명령어",
        "#FF9800",
        [
            ContyCommand("Loop", "Loop", 20, "#C62828", True),
            ContyCommand("Wait", "Wait", 22, "#546E7A", True),
            ContyCommand("Wait For", "Wait For", 23, "#26A69A", True),
            ContyCommand("Wait DI", "Wait DI", 28, "#455A64", True),
            ContyCommand("If (DI)", "If DI", 29, "#AD1457", True),
            ContyCommand("If Var", "If Var", 24, "#880E4F", True),
            ContyCommand("Else", "Else", 26, "#4A148C", True),
            ContyCommand("Math", "Math", 3, "#BF360C", True),
            ContyCommand("Loop Break", "Loop Break", 21, "#EF5350", True),
            ContyCommand("Speed Ratio", "Speed", 250, "#FFB300", True),
            ContyCommand("Folder", "Folder", 100, "#E65100", False),
            ContyCommand("Comment", "Comment", 903, "#757575", False),
            ContyCommand("Stop", "Stop", 1, "#B71C1C", True),
        ],
    ),
    (
        "▸ 입출력 명령어",
        "#03A9F4",
        [
            ContyCommand("DO", "Tool Command", 40, "#7B1FA2", True),
            ContyCommand("Tool Sensing", "Tool Sensing", 41, "#42A5F5", True),
            ContyCommand("EndTool DO", "EndTool DO", 6, "#512DA8", True),
            ContyCommand("Smart DO", "Smart DO", 4, "#6A1B9A", True),
            ContyCommand("AO", "Smart AO", 5, "#827717", True),
        ],
    ),
    (
        "▸ 응용 명령어",
        "#4CAF50",
        [
            ContyCommand("Pick", "Pick", 201, "#00838F", True),
            ContyCommand("Place", "Place", 202, "#00695C", True),
            ContyCommand("Pallet", "Pick Group", 200, "#004D40", True),
            ContyCommand("Conveyor", "Conveyor", 300, "#F9A825", False),
            ContyCommand("TaktTime", "TaktTime", 302, "#AB47BC", True),
            ContyCommand("Detect", "Detect", 400, "#29B6F6", False),
            ContyCommand("Retrieve", "Retrieve", 401, "#66BB6A", False),
            ContyCommand("Python", "Python Script", 50, "#FFA726", False),
            ContyCommand("Call", "Call", 901, "#37474F", False),
            ContyCommand("Force", "Force", 902, "#4E342E", False),
        ],
    ),
]

COMMANDS_BY_NAME: Dict[str, ContyCommand] = {
    command.ui_name: command
    for _, _, commands in COMMAND_SECTIONS
    for command in commands
}


def get_type_info(type_id: Optional[int]) -> ContyTypeInfo:
    if type_id is None:
        return ContyTypeInfo(-1, "Unknown", False, "Missing type id.")
    return TYPE_REGISTRY.get(type_id, ContyTypeInfo(type_id, f"Unknown ({type_id})", False, "Unknown Conty type."))


def get_command(ui_name: str) -> Optional[ContyCommand]:
    return COMMANDS_BY_NAME.get(ui_name)


def type_label(type_id: Optional[int]) -> str:
    return get_type_info(type_id).label


def is_stable_type(type_id: Optional[int]) -> bool:
    return get_type_info(type_id).stable


def tag_for_type(type_id: Optional[int]) -> str:
    if type_id in (None, 0):
        return SYSTEM_TAG
    return STABLE_TAG if is_stable_type(type_id) else UNSTABLE_TAG


def text_color_for_stability(stable: bool) -> str:
    return STABLE_TEXT_COLOR if stable else UNSTABLE_TEXT_COLOR


def iter_type_labels() -> Iterable[Tuple[int, str]]:
    for type_id, info in sorted(TYPE_REGISTRY.items()):
        yield type_id, info.label
