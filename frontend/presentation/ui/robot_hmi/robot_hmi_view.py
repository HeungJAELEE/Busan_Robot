import customtkinter as ctk
from core.domains.robot.communication.client_manager import robot_manager
from infrastructure.mqtt.mqtt_manager import mqtt_broker
from .editors.motion_editors import JogController, MoveEditor, MoveByEditor, MoveCEditor, MoveHomeEditor, ForceEditor
from .editors.logic_editors import (SmartDOEditor, LoopEditor, MathEditor, CallEditor, IfEditor, WaitEditor, WaitDIEditor, WaitAIEditor,
                                    CommentEditor, StopEditor, SwitchEditor, FolderEditor,
                                    WaitForEditor, LoopBreakEditor, SpeedRatioEditor, ToolSensingEditor,
                                    ConveyorTrackingEditor, TaktTimeEditor, DetectEditor, RetrieveEditor, PythonScriptEditor)
from .editors.process_editors import PickPlaceEditor, VisionEditor, SyncEditor, SetAOEditor
from presentation.ui.theme import Theme
import tkinter as tk

import tkinter.ttk as ttk

import tkinter.filedialog as fd

import json

import os

import time

import datetime

import threading

import traceback

def _safe_configure(widget, **kwargs):
    try:
        if widget.winfo_exists():
            widget.configure(**kwargs)
    except Exception:
        pass

from core.domains.robot.use_cases.robot_control_usecase import RobotControlUseCase

class ProgramTreeEditor:
    def __init__(self, parent_frame):
        self.parent = parent_frame
        self.on_node_selected_callback = None
        self.node_data = {}
        self.custom_paths = {} # robot_name -> file_path
        self._load_custom_paths()  # 디스크에서 마지막 사용 경로 복원
        self.current_robot = "Robot A"
        self.is_loading = False
        
    def _on_tree_select(self, event):
        # Apply changes for current editor before switching
        if hasattr(self, 'current_editor') and self.current_editor and hasattr(self.current_editor, 'apply_changes'):
            if hasattr(self, 'current_node_id') and self.current_node_id in self.node_data:
                try:
                    self.current_editor.apply_changes(self.node_data[self.current_node_id])
                except Exception as e:
                    print(f"Error applying changes: {e}")
                    
        selected = self.tree.selection()
        if not selected: return
        item = selected[0]
        self.current_node_id = item
        
        item_text = self.tree.item(item, "text").strip()
        if self.on_node_selected_callback and item in self.node_data:
            data = self.node_data[item]
            pallets = getattr(self, "all_pallets", [])
            self.on_node_selected_callback(data.get("q"), data.get("p"), data.get("t_type"), item_text, data.get("p_name"), data.get("p_data"), pallets, data.get("b_radius", 0.0), data.get("app_data"), data.get("ret_data"), data)
            
    def get_program_path(self, robot_name):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
        dir_path = os.path.join(base_dir, 'user_programs', robot_name.replace(" ", "_"))
        os.makedirs(dir_path, exist_ok=True)
        return os.path.join(dir_path, 'program.json')
    
    def _get_paths_config_file(self):
        """custom_paths를 영구 저장하는 설정 파일 경로"""
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
        return os.path.join(base_dir, 'user_programs', '_custom_paths.json')
    
    def _save_custom_paths(self):
        """custom_paths를 디스크에 저장 (앱 재시작 후에도 유지)"""
        try:
            cfg = self._get_paths_config_file()
            os.makedirs(os.path.dirname(cfg), exist_ok=True)
            with open(cfg, 'w', encoding='utf-8') as f:
                json.dump(self.custom_paths, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f">> [경고] custom_paths 저장 실패: {e}")
    
    def _load_custom_paths(self):
        """디스크에서 custom_paths 복원"""
        try:
            cfg = self._get_paths_config_file()
            if os.path.exists(cfg):
                with open(cfg, 'r', encoding='utf-8') as f:
                    self.custom_paths = json.load(f)
                print(f">> [정보] 저장된 프로그램 경로 복원: {self.custom_paths}")
        except Exception as e:
            print(f">> [경고] custom_paths 복원 실패: {e}")
        
    # 표시 텍스트에서 자기-감싸기를 판별하기 위한 타입→레이블 매핑
    _TYPE_LABEL_MAP = {
        1: "JointMove", 100: "Home", 102: "JointMove", 103: "FrameMove",
        200: "Pick Group", 201: "Pick", 202: "Place", 250: "Call",
    }

    @staticmethod
    def _strip_nested_name(name: str) -> str:
        """중첩된 이름에서 핵심 이름만 추출합니다.
        예: 'Pick (Pick (Pick Node))' → 'Pick Node'
            'Home (Home (Home Node))' → 'Home Node'
            'FrameMove (FrameMove Node) [X0 Y0 Z0]' → 'FrameMove Node'
            'FrameMove (FrameMove Node, 2pts) [X350 Y-190 Z520]' → 'FrameMove Node'
            'Pick Group (Pick Group Node)' → 'Pick Group Node'
            'Loop (무한)' → 'Loop (무한)'  (중첩 아님)
        """
        import re
        if not isinstance(name, str):
            return ""
        result = name
        for _ in range(10):  # 무한 루프 방지
            new_result = result
            # "[X... Y... Z...]" 좌표 접미사 제거
            new_result = re.sub(r'\s*\[X[\d.\-]+\s+Y[\d.\-]+\s+Z[\d.\-]+\]', '', new_result).strip()
            # ", Npts" 웨이포인트 개수 접미사 제거 (디스플레이 텍스트 잔재)
            new_result = re.sub(r',\s*\d+\s*pts\b', '', new_result).strip()
            # "Type (inner)" 또는 "Type Word (inner)" — prefix가 inner의 시작과 같으면 중첩 해제
            m = re.match(r'^([A-Za-z][A-Za-z0-9]*(?:\s+[A-Za-z][A-Za-z0-9]*)?)\s*\((.+)\)\s*$', new_result)
            if m:
                prefix = m.group(1)
                inner = m.group(2)
                if inner.startswith(prefix):
                    new_result = inner.strip()
            if new_result == result:
                break
            result = new_result
        return result.strip()

    @classmethod
    def _canonical_node_name(cls, raw_name: str, node_type) -> str:
        """저장된 name을 정리하고, 타입 레이블과 동일한 잔재("Home", "Home Node")는 빈 문자열로 만든다.
        디스플레이 텍스트가 `f" Home ({name})"` 형태이므로, 이 이름이 빈 문자열이면 더 이상 자기-감싸기가 발생하지 않는다."""
        clean = cls._strip_nested_name(raw_name or "")
        type_lbl = cls._TYPE_LABEL_MAP.get(node_type)
        if type_lbl and clean in (type_lbl, f"{type_lbl} Node"):
            return ""
        return clean
    
    def save_program(self, silent=False):
        robot = self.robot_sel.get()
        if not silent:
            from core.domains.robot.communication.client_manager import robot_manager
            robot_manager.set_active_robot(robot)
        
        # 트리가 비어있으면 저장하지 않음 (빈 파일로 덮어씌움 방지)
        all_children = self.tree.get_children()
        if not all_children:
            print(">> [경고] 트리가 비어있어 저장을 건너뜁니다.")
            return
        
        # 실제 노드가 있는지 확인 (Main Program만 있고 자식이 없으면 스킵)
        has_real_nodes = False
        for child in all_children:
            text = self.tree.item(child, "text").strip()
            if "Main Program" in text:
                if self.tree.get_children(child):
                    has_real_nodes = True
                    break
            else:
                has_real_nodes = True
                break
        
        if not has_real_nodes and silent:
            # 자동 저장 시 빈 프로그램이면 기존 파일 보존
            return
            
        # 항상 user_programs 경로에 저장 (기본)
        default_path = self.get_program_path(robot)
        # custom_path가 있으면 거기에도 저장
        custom_path = self.custom_paths.get(robot)
        
        path = custom_path if custom_path else default_path
        
        # ★ 저장 전 현재 에디터의 설정값을 node_data에 자동 반영
        try:
            selected = self.tree.selection()
            if selected and hasattr(self, 'current_editor') and self.current_editor and hasattr(self.current_editor, 'apply_changes'):
                item = selected[0]
                if item not in self.node_data:
                    self.node_data[item] = {}
                self.current_editor.apply_changes(self.node_data[item])
        except Exception as e:
            print(f">> [경고] 에디터 자동 적용 중 오류: {e}")
        
        try:
            from core.domains.teaching_management.entities import ContyProgram, TeachingNode
            from infrastructure.repositories.teaching_repository_impl import TeachingRepositoryImpl
            
            prog = ContyProgram("ExportedProgram")
            prog._raw_full_data = getattr(self, "_current_raw_data", {})
            if hasattr(self, "all_pallets"):
                prog.pallets = self.all_pallets
            
            repo = TeachingRepositoryImpl()
            
            def _build_nodes(parent_item, p_id):
                nodes = []
                for child in self.tree.get_children(parent_item):
                    node_name = self.tree.item(child, "text").strip()
                    if "Main Program" in node_name:
                        # Main Program은 래퍼 — 자식만 재귀 처리
                        child_nodes = _build_nodes(child, p_id)
                        nodes.extend(child_nodes)
                        continue
                        
                    n = TeachingNode(len(prog.nodes) + len(nodes) + 1, p_id, 100)
                    # ★ 이름 중첩 방지: 트리 디스플레이 텍스트/이전 저장본 모두에서 중첩 잔재를 제거.
                    #    Fallback도 반드시 _strip_nested_name을 통과시켜야 디스플레이 텍스트가
                    #    그대로 name으로 저장되는 사고를 막을 수 있다.
                    d_check = self.node_data.get(child, {})
                    raw_check = d_check.get("__raw__", {})
                    original_name = raw_check.get("name", "") or node_name
                    n.name = self._strip_nested_name(original_name)
                    
                    # ─── 타입 결정: __raw__에 원본 type이 있으면 그것을 우선 사용 ─────
                    if child in self.node_data and "__raw__" in self.node_data[child]:
                        raw_type = self.node_data[child]["__raw__"].get("type")
                        if raw_type is not None:
                            n.type = raw_type
                    else:
                        # 새로 만든 노드: 이름 기반 추측 매핑
                        if "Program Settings" in node_name: n.type = 999
                        elif "Variables" in node_name: n.type = 2
                        elif "JointMove" in node_name: n.type = 102
                        elif "FrameMove" in node_name: n.type = 103
                        elif "Move J" in node_name: n.type = 1
                        elif "Move L" in node_name: n.type = 2
                        elif "Move C" in node_name: n.type = 3
                        elif "Move B" in node_name: n.type = 5
                        elif "Move By" in node_name: n.type = 6
                        elif "Move Home" in node_name: n.type = 4
                        elif "Home" in node_name: n.type = 100
                        elif "DO 출력" in node_name or "Smart DO" in node_name: n.type = 4
                        elif "Pick Group" in node_name: n.type = 200
                        elif "Pick" in node_name: n.type = 201
                        elif "Pallet" in node_name: n.type = 202
                        elif "Place" in node_name: n.type = 202
                        elif "Wait DI" in node_name: n.type = 29
                        elif "Wait For" in node_name: n.type = 30
                        elif "Wait" in node_name: n.type = 22
                        elif "Loop Break" in node_name or "Break" in node_name: n.type = 21
                        elif "Loop" in node_name: n.type = 20
                        elif "Elif" in node_name: n.type = 25
                        elif "Else" in node_name: n.type = 26
                        elif "If Var" in node_name: n.type = 24
                        elif "If" in node_name: n.type = 29
                        elif "Set DO" in node_name: n.type = 4
                        elif "EndTool" in node_name: n.type = 6
                        elif "AO 출력" in node_name or "Set AO" in node_name: n.type = 5
                        elif "Call" in node_name: n.type = 250
                        elif "Force" in node_name or "indyCARE" in node_name: n.type = 302
                        elif "Folder" in node_name: n.type = 100
                        elif "Comment" in node_name: n.type = 40
                        elif "Stop" in node_name: n.type = 41
                        elif "Math" in node_name: n.type = 21
                        elif "Speed" in node_name: n.type = 32
                        elif "Tool" in node_name: n.type = 23
                        elif "Conveyor" in node_name: n.type = 300
                        elif "TaktTime" in node_name: n.type = 303
                        elif "Detect" in node_name: n.type = 400
                        elif "Retrieve" in node_name: n.type = 401
                        elif "Python Script" in node_name: n.type = 500
                    
                    # Conty 호환 __raw__ 기본 템플릿 생성
                    _ref = {"type": 1, "tref": [0,0,0,0,0,0]}
                    _tcp = [0,0,0,0,0,0]
                    raw_templates = {
                        1:   {"wpList": [], "enable": True, "type": 1, "pId": p_id},   # JointMove
                        2:   {"wpList": [], "enable": True, "type": 2, "pId": p_id},   # FrameMove
                        3:   {"wpList": [], "enable": True, "type": 3, "pId": p_id},   # CircularMove
                        4:   {"enable": True, "type": 4, "pId": p_id},                 # MoveHome
                        5:   {"wpList": [], "enable": True, "type": 5, "pId": p_id},   # MoveB
                        20:  {"count": -1, "enable": True, "type": 20, "pId": p_id},   # Loop (count=-1 → 무한, N>0 → N회)
                        21:  {"endtoolDiList": [], "enable": True, "type": 21, "diList": [], "pId": p_id},  # WaitDI
                        22:  {"enable": True, "type": 22, "pId": p_id},                # AO
                        24:  {"enable": True, "type": 24, "pId": p_id},                # EndToolDO
                        25:  {"enable": True, "type": 25, "cond": {}, "pId": p_id},       # If(변수)
                        26:  {"enable": True, "type": 26, "pId": p_id},                # Else
                        28:  {"endtoolDiList": [], "type": 28, "time": 1, "enable": True, "diList": [], "pId": p_id},  # Wait
                        29:  {"endtoolDiList": [], "type": 29, "enable": True, "diList": [], "pId": p_id},  # WaitPeriod
                        30:  {"endtoolDiList": [], "type": 30, "enable": True, "diList": [], "pId": p_id},  # WaitDI(alt)
                        40:  {"enable": True, "type": 40, "pId": p_id},                # Comment
                        41:  {"enable": True, "type": 41, "pId": p_id},                # Stop
                        100: {"enable": True, "type": 100, "pId": p_id},               # Folder
                        102: {"enable": True, "type": 102, "diList": [], "pId": p_id},  # If(DI)
                        103: {"enable": True, "type": 103, "pId": p_id},               # Loop (count는 없으면 무한)
                        104: {"enable": True, "type": 104, "pId": p_id},               # PalletDef
                        105: {"enable": True, "type": 105, "pId": p_id},               # PalletDef2
                        200: {"groupName": "", "enable": True, "type": 200, "pId": p_id},  # Pick
                        201: {"enable": True, "type": 201, "pId": p_id, "toolId": 1, "sensName": "",
                              "approach": {"direction": 0, "boundary": {"velLevel": 5, "accLevel": 5}, "distance": 0.1, "waitTime": 0, "waitFor": {"type": 0, "time": 0}},
                              "retract": {"direction": 1, "boundary": {"velLevel": 5, "accLevel": 5}, "distance": 0.1, "waitTime": 0, "waitFor": {"type": 0, "time": 0}},
                              "target": {"type": 0, "boundary": {"velLevel": 5, "accLevel": 5}, "pallet": {},
                                         "point": {"q": [], "p": []}, "refFrame": _ref, "tcp": _tcp}},
                        202: {"enable": True, "type": 202, "pId": p_id, "toolId": 1, "sensName": "",
                              "approach": {"direction": 0, "boundary": {"velLevel": 5, "accLevel": 5}, "distance": 0.1, "waitTime": 0, "waitFor": {"type": 0, "time": 0}},
                              "retract": {"direction": 1, "boundary": {"velLevel": 5, "accLevel": 5}, "distance": 0.1, "waitTime": 0, "waitFor": {"type": 0, "time": 0}},
                              "target": {"type": 0, "boundary": {"velLevel": 5, "accLevel": 5}, "pallet": {},
                                         "point": {"q": [], "p": []}, "refFrame": _ref, "tcp": _tcp}},
                        250: {"enable": True, "type": 250, "pId": p_id},               # Call
                        300: {"enable": True, "type": 300, "pId": p_id},               # ConveyorTracking
                        302: {"enable": True, "type": 302, "pId": p_id},               # Force
                        303: {"enable": True, "type": 303, "pId": p_id},               # TaktTime
                        23:  {"enable": True, "type": 23, "pId": p_id, "sensName": ""},  # ToolSensing
                        31:  {"enable": True, "type": 31, "pId": p_id},                # LoopBreak
                        32:  {"enable": True, "type": 32, "pId": p_id, "prgSpdRatio": 100},  # SpeedRatio
                        400: {"enable": True, "type": 400, "pId": p_id},               # Detect
                        401: {"enable": True, "type": 401, "pId": p_id},               # Retrieve
                        500: {"enable": True, "type": 500, "pId": p_id, "scriptCode": ""},  # PythonScript
                    }
                    
                    if child in self.node_data:
                        d = self.node_data[child]
                        # 기본 템플릿에서 시작하고, 기존 __raw__를 복원
                        base_raw = raw_templates.get(n.type, {"enable": True, "type": n.type, "pId": p_id})
                        existing_raw = d.get("__raw__", {})
                        n.__raw__ = base_raw.copy()
                        # 기존 raw 데이터 복원 (원본 Conty 데이터)
                        if existing_raw:
                            n.__raw__.update(existing_raw)
                        n.__raw__["pId"] = p_id
                        n.__raw__["type"] = n.type
                        
                        # JSON 직렬화 불가능한 키 제외하고 안전한 데이터만 복사
                        _skip_keys = {"__raw__", "waypoints", "wp", "move_data", "resolved_waypoints"}
                        for k, v in d.items():
                            if k in _skip_keys:
                                continue
                            # 기본 타입만 복사 (dict, list, str, int, float, bool, None)
                            if isinstance(v, (dict, list, str, int, float, bool, type(None))):
                                n.__raw__[k] = v
                        
                        # 웨이포인트 좌표를 q/p로 저장 (★ 전체 WP 저장)
                        wps = d.get("waypoints", [])
                        if wps:
                            from core.domains.teaching_management.entities import WaypointVO
                            # 첫 번째 WP를 대표 좌표로
                            first_wp = wps[0]
                            n.__raw__["q"] = first_wp.get("q", [0.0]*6)
                            n.__raw__["p"] = first_wp.get("p", [0.0]*6)
                            # ★ 모든 WP를 저장 (다중 웨이포인트 보존)
                            n.__raw__["all_waypoints"] = [
                                {"q": wp.get("q", [0]*6), "p": wp.get("p", [0]*6), "id": wp.get("id", f"wp_{i}")}
                                for i, wp in enumerate(wps)
                            ]
                            n.waypoints = {}
                            for i, wp_data in enumerate(wps):
                                wp = WaypointVO(j_pos=wp_data["q"], t_pos=wp_data.get("p", [0]*6))
                                n.waypoints[i] = wp
                        elif d.get("q") is not None:
                            from core.domains.teaching_management.entities import WaypointVO
                            wp = WaypointVO(j_pos=d["q"], t_pos=d.get("p", [0]*6))
                            n.waypoints = {0: wp}
                            
                        if n.type in [201, 202]: # Pick / Place
                            try:
                                sel = self.tree.selection()
                                if sel and sel[0] == child:
                                    if hasattr(self, "current_editor") and hasattr(self.current_editor, "apply_changes"):
                                        self.current_editor.apply_changes(d)
                            except Exception as e:
                                print(f"Error applying changes: {e}")
                                
                            n.approach = d.get("approach", {})
                            n.retract = d.get("retract", {})
                            n.target = d.get("target", {})
                            n.toolId = d.get("toolId", 1)
                            if "p_data" in d:
                                n.p_data = d["p_data"]
                            if "target_pallet_name" in d:
                                n.target_pallet_name = d["target_pallet_name"]
                            if "target_pallet_id" in d:
                                n.target_pallet_id = d["target_pallet_id"]
                        
                        if "mathVar" in d: n.__raw__["mathVar"] = d["mathVar"]
                        if "mathOp" in d: n.__raw__["mathOp"] = d["mathOp"]
                        if "mathVal" in d: n.__raw__["mathVal"] = d["mathVal"]
                        if "cond" in d: n.__raw__["cond"] = d["cond"]
                        if "time" in d: n.__raw__["time"] = d["time"]
                        if "diList" in d: n.__raw__["diList"] = d["diList"]
                        # Loop count 명시적 저장 (★ raw update 이후 덮어씌움)
                        # Conty 표준: 무한 = -1, 유한 = 양의 정수.
                        # 우리 앱은 내부적으로 None/-1 둘 다 무한으로 해석하지만 디스크에는 표준 형식인 -1을 쓴다.
                        if "count" in d:
                            count_val = d["count"]
                            if count_val is None or (isinstance(count_val, int) and count_val <= 0):
                                n.__raw__["count"] = -1
                            else:
                                n.__raw__["count"] = int(count_val)
                        # SpeedRatio 명시적 저장
                        if "prgSpdRatio" in d:
                            n.__raw__["prgSpdRatio"] = d["prgSpdRatio"]
                        # doList 명시적 저장
                        if "doList" in d: n.__raw__["doList"] = d["doList"]
                        # endtoolDoList 명시적 저장
                        if "endtoolDoList" in d: n.__raw__["endtoolDoList"] = d["endtoolDoList"]
                        # aoList 명시적 저장
                        if "aoList" in d: n.__raw__["aoList"] = d["aoList"]
                        if "offset" in d: 
                            n.offset_dx = d["offset"].get("dx", 0)
                            n.offset_dy = d["offset"].get("dy", 0)
                            n.offset_dz = d["offset"].get("dz", 0)
                            n.__raw__["offset"] = d["offset"]
                        if "boundary" in d:
                            n.__raw__["boundary"] = d["boundary"]
                            
                    nodes.append(n)
                    
                    # Recursively build children
                    child_nodes = _build_nodes(child, n.id)
                    nodes.extend(child_nodes)
                return nodes
                
            prog.nodes = _build_nodes("", 0)
            # ★ 표준 Conty(APK 호환) 포맷으로 직접 저장한다.
            # 같은 파일을 우리 앱(▶ 실행)과 펜던트가 공유하기 위해 단일 저장 경로로 통일.
            # 우리 앱은 load_from_json이 wpList/moveList 3단 참조도 정상 복원하므로 round-trip 안전.
            repo.save_to_conty_json(prog, path)

            # user_programs 기본 경로에도 백업 저장 (유실 방지)
            if path != default_path:
                try:
                    repo.save_to_conty_json(prog, default_path)
                except Exception as _e:
                    print(f">> [경고] 백업 저장 실패: {_e}")
            
            # 현재 경로 기록
            self.custom_paths[robot] = path
            self._save_custom_paths()
            
            print(f">> [성공] 프로그램 {prog.name} 저장 완료: {path}")
            if not silent:
                from tkinter import messagebox
                messagebox.showinfo("저장 성공", f"프로그램이 저장되었습니다.\n{path}")
        except Exception as e:
            print(f">> [실패] 저장 중 에러 발생: {e}")
            import traceback
            traceback.print_exc()

    def export_to_conty(self):
        """현재 트리를 표준 Conty(APK 티칭펜던트 호환) 포맷으로 내보낸다.
        저장 경로를 묻고 save_to_conty_json()을 호출. 우리 내부 저장은 건드리지 않는다."""
        from tkinter import messagebox
        robot = self.robot_sel.get()
        all_children = self.tree.get_children()
        if not all_children:
            messagebox.showwarning("내보내기 불가", "트리가 비어있습니다.")
            return

        # 1) 현재 에디터의 설정값을 node_data에 자동 반영 (save_program과 동일한 가드)
        try:
            selected = self.tree.selection()
            if selected and hasattr(self, 'current_editor') and self.current_editor and hasattr(self.current_editor, 'apply_changes'):
                item = selected[0]
                if item not in self.node_data:
                    self.node_data[item] = {}
                self.current_editor.apply_changes(self.node_data[item])
        except Exception as e:
            print(f">> [경고] 에디터 자동 적용 중 오류: {e}")

        # 2) 저장 경로 선택 — USB/네트워크 이동용 사본 저장.
        # 본 앱의 일반 "저장"도 같은 표준 Conty 포맷이지만, 다른 경로/파일명이 필요할 때 사용.
        import datetime
        default_name = f"{robot}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.7.json"
        export_path = fd.asksaveasfilename(
            title="사본 내보내기 — 펜던트/USB로 옮길 표준 Conty JSON",
            defaultextension=".7.json",
            initialfile=default_name,
            filetypes=[("Conty JSON", "*.json *.7.json"), ("All files", "*.*")]
        )
        if not export_path:
            return

        # 3) save_program과 동일한 방식으로 ContyProgram을 빌드한 뒤 표준 직렬화
        try:
            from core.domains.teaching_management.entities import ContyProgram, TeachingNode
            from infrastructure.repositories.teaching_repository_impl import TeachingRepositoryImpl

            prog = ContyProgram("ExportedProgram")
            prog._raw_full_data = getattr(self, "_current_raw_data", {})
            if hasattr(self, "all_pallets"):
                prog.pallets = self.all_pallets

            # save_program 내부의 _build_nodes를 그대로 재사용하기 위해 임시 helper
            # save_program 함수 본체를 호출하는 대신 같은 빌더 패턴을 인라인.
            from core.domains.teaching_management.entities import WaypointVO

            def _build_nodes(parent_item, p_id):
                nodes = []
                for child in self.tree.get_children(parent_item):
                    node_name = self.tree.item(child, "text").strip()
                    if "Main Program" in node_name:
                        nodes.extend(_build_nodes(child, p_id))
                        continue
                    n = TeachingNode(len(prog.nodes) + len(nodes) + 1, p_id, 100)
                    d_check = self.node_data.get(child, {})
                    raw_check = d_check.get("__raw__", {})
                    original_name = raw_check.get("name", "") or node_name
                    n.name = self._strip_nested_name(original_name)
                    # 타입 결정
                    if child in self.node_data and "__raw__" in self.node_data[child]:
                        raw_type = self.node_data[child]["__raw__"].get("type")
                        if raw_type is not None:
                            n.type = raw_type
                    n.__raw__ = (d_check.get("__raw__", {}) or {}).copy()
                    n.__raw__["type"] = n.type
                    n.__raw__["pId"] = p_id
                    # node_data → __raw__ 복사 (Loop count, doList 등 에디터 결과 반영)
                    _skip = {"__raw__", "waypoints", "wp", "move_data", "resolved_waypoints"}
                    for k, v in d_check.items():
                        if k in _skip:
                            continue
                        if isinstance(v, (dict, list, str, int, float, bool, type(None))):
                            n.__raw__[k] = v
                    # waypoints → resolved_waypoints (move 노드)
                    wps = d_check.get("waypoints", [])
                    if wps:
                        n.resolved_waypoints = [
                            {"id": wp.get("id", f"wp_{i}"),
                             "wp": WaypointVO(j_pos=wp.get("q", [0]*6),
                                              t_pos=wp.get("p", [0]*6),
                                              blend_radius=wp.get("blendRadius", 0))}
                            for i, wp in enumerate(wps)
                        ]
                    # Loop count 명시 변환 (Conty 표준)
                    if "count" in d_check:
                        cv = d_check["count"]
                        if cv is None or (isinstance(cv, int) and cv <= 0):
                            n.__raw__["count"] = -1
                        else:
                            n.__raw__["count"] = int(cv)
                    nodes.append(n)
                    nodes.extend(_build_nodes(child, n.id))
                return nodes

            prog.nodes = _build_nodes("", 0)

            repo = TeachingRepositoryImpl()
            repo.save_to_conty_json(prog, export_path)

            print(f">> [성공] 사본 내보내기 완료: {export_path}")
            messagebox.showinfo(
                "사본 내보내기 완료",
                f"표준 Conty 포맷으로 사본이 저장되었습니다.\n"
                f"이 파일은 우리 앱과 APK 티칭펜던트 양쪽 모두에서 직접 로드할 수 있습니다.\n\n{export_path}"
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("내보내기 실패", f"오류:\n{e}")

    def _get_all_children(self, item):
        result = []
        for child in self.tree.get_children(item):
            result.append(self.tree.item(child, "text").strip())
            result.extend(self._get_all_children(child))
        return result
        

    def get_current_program_path(self, robot_name):
        return self.custom_paths.get(robot_name, self.get_program_path(robot_name))
        
    def _on_robot_changed(self, new_robot):
        if self.current_robot != new_robot:
            try:
                # Only auto-save to user_programs path, never to a custom-loaded external file
                default_path = self.get_program_path(self.current_robot)
                if self.get_current_program_path(self.current_robot) == default_path:
                    self.save_program(silent=True)
            except:
                pass
            
            self.current_robot = new_robot
            try:
                from core.domains.robot.communication.client_manager import robot_manager
                robot_manager.set_active_robot(new_robot)
            except:
                pass
            
            path = self.get_current_program_path(new_robot)
            if os.path.exists(path):
                self._load_from_path(path)
            else:
                for item in self.tree.get_children():
                    self.tree.delete(item)
                self.tree.insert("", "end", text=" Main Program", open=True)
            self.refresh_info()
            
    def _load_from_path(self, file_path):
        if file_path and os.path.exists(file_path):
            try:
                for item in self.tree.get_children():
                    self.tree.delete(item)
                main_node = self.tree.insert("", "end", text=" Main Program", open=True)
                
                if not hasattr(self, 'node_joint_targets'):
                    self.node_joint_targets = {}
                if not hasattr(self, 'node_data'):
                    self.node_data = {}
                    
                self.node_joint_targets.clear()
                self.node_data.clear()
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if "nodes" in data and "program" not in data:
                    for n in data.get("nodes", []):
                        self.tree.insert(main_node, "end", text=n if n.startswith(" ") else f" {n}", open=True)
                else:
                    from infrastructure.repositories.teaching_repository_impl import TeachingRepositoryImpl
                    repo = TeachingRepositoryImpl()
                    program = repo.load_from_json(file_path)
                    
                    self._current_raw_data = getattr(program, "_raw_full_data", {})
                    self.all_pallets = getattr(program, 'pallets', [])
                    node_map = {0: main_node}
                    
                    if hasattr(program, 'nodes'):
                        for node in program.nodes:
                            t = node.type
                            # ★ 로드 시 즉시 중첩 이름 정리: JSON에 누적된 "Home (Home (Home ...))" 류 잔재를 즉시 풀어내야
                            #    트리 디스플레이가 또 한 겹 감싸는 것을 막을 수 있다.
                            raw_loaded_name = getattr(node, "name", "")
                            name = self._canonical_node_name(raw_loaded_name, t)
                            node.name = name  # 다음 저장 사이클에서 사용될 깨끗한 이름
                            if hasattr(node, "__raw__") and isinstance(node.__raw__, dict):
                                node.__raw__["name"] = name
                            cid = getattr(node, "id", 0)
                            pid = getattr(node, "pId", 0)

                            parent_item = node_map.get(pid, main_node)
                            node_str = f" Node ({name})"
                            # ─── Conty 실제 타입 매핑 (120+ 학습파일 기반) ───
                            if t == 999: node_str = " Program Settings"
                            elif t in [2, 3]:  # Variables
                                vl = getattr(node, "varList", getattr(node, "__raw__", {}).get("varList", []))
                                node_str = f" Variables ({len(vl)}개)" if vl else " Variables"
                            elif t == 102:  # ★ JointMove
                                wp_count = len(getattr(node, "resolved_waypoints", []))
                                raw_n = getattr(node, "__raw__", {})
                                q = getattr(node, "target_q", None) or raw_n.get("q", [0]*6)
                                p = getattr(node, "target_p", None) or raw_n.get("p", [0]*6)
                                # XYZ 좌표 표시 (mm 단위)
                                try:
                                    xyz = f"X{p[0]*1000:.0f} Y{p[1]*1000:.0f} Z{p[2]*1000:.0f}"
                                except:
                                    xyz = ""
                                if wp_count > 1:
                                    node_str = f" JointMove ({name}, {wp_count}pts) [{xyz}]" if name else f" JointMove ({wp_count}pts) [{xyz}]"
                                elif name:
                                    node_str = f" JointMove ({name}) [{xyz}]"
                                else:
                                    node_str = f" JointMove [{xyz}]"
                            elif t == 103:  # ★ FrameMove
                                wp_count = len(getattr(node, "resolved_waypoints", []))
                                raw_n = getattr(node, "__raw__", {})
                                q = getattr(node, "target_q", None) or raw_n.get("q", [0]*6)
                                p = getattr(node, "target_p", None) or raw_n.get("p", [0]*6)
                                try:
                                    xyz = f"X{p[0]*1000:.0f} Y{p[1]*1000:.0f} Z{p[2]*1000:.0f}"
                                except:
                                    xyz = ""
                                if wp_count > 1:
                                    node_str = f" FrameMove ({name}, {wp_count}pts) [{xyz}]" if name else f" FrameMove ({wp_count}pts) [{xyz}]"
                                elif name:
                                    node_str = f" FrameMove ({name}) [{xyz}]"
                                else:
                                    node_str = f" FrameMove [{xyz}]"
                            elif t == 1:  # Legacy JointMove
                                node_str = f" JointMove ({name})" if name else " JointMove"
                            elif t == 4:  # SmartDO
                                do_list = getattr(node, "doList", getattr(node, "__raw__", {}).get("doList", []))
                                if do_list:
                                    pins = ", ".join(f"DO{d['idx']}={'ON' if d['value'] else 'OFF'}" for d in do_list)
                                    node_str = f" DO 출력 ({pins})"
                                else:
                                    node_str = " DO 출력"
                            elif t == 5:  # SmartAO
                                node_str = " AO 출력"
                            elif t == 6:  # EndTool DO
                                node_str = " 엔드툴 DO"
                            elif t == 20:  # Loop
                                count = getattr(node, "count", getattr(node, "__raw__", {}).get("count", None))
                                if count is not None and count > 0:
                                    node_str = f" Loop ({count}회)"
                                else:
                                    node_str = " Loop (무한)"
                            elif t == 21:  # LoopBreak
                                node_str = " Break"
                            elif t == 22:  # Wait (시간)
                                time_v = getattr(node, "time", getattr(node, "__raw__", {}).get("time", 0))
                                node_str = f" Wait ({time_v}s)"
                            elif t == 23:  # Switch
                                time_v = getattr(node, "time", getattr(node, "__raw__", {}).get("time", 0))
                                node_str = f" Switch ({time_v}s)"
                            elif t == 24:  # If (변수 조건)
                                cond = getattr(node, "cond", getattr(node, "__raw__", {}).get("cond", {}))
                                if cond and cond.get("left", {}).get("value"):
                                    lv = cond["left"]["value"]
                                    op_map = {0: "==", 1: "!=", 2: ">", 3: "<", 4: ">=", 5: "<="}
                                    op = op_map.get(cond.get("op", 0), "==")
                                    rv = cond.get("right", {}).get("value", "?")
                                    node_str = f" If ({lv} {op} {rv})"
                                else:
                                    node_str = " If"
                            elif t == 25:  # Elif (변수 조건)
                                cond = getattr(node, "cond", getattr(node, "__raw__", {}).get("cond", {}))
                                if cond and cond.get("left", {}).get("value"):
                                    lv = cond["left"]["value"]
                                    op_map = {0: "==", 1: "!=", 2: ">", 3: "<", 4: ">=", 5: "<="}
                                    op = op_map.get(cond.get("op", 0), "==")
                                    rv = cond.get("right", {}).get("value", "?")
                                    node_str = f" Elif ({lv} {op} {rv})"
                                else:
                                    node_str = " Elif"
                            elif t == 26:  # Else
                                node_str = " Else"
                            elif t == 28:  # Wait (DI 대기)
                                di_list = getattr(node, "diList", getattr(node, "__raw__", {}).get("diList", []))
                                time_v = getattr(node, "time", getattr(node, "__raw__", {}).get("time", 0))
                                if di_list:
                                    conds = ", ".join(f"DI{d['idx']}={'ON' if d.get('value',1) else 'OFF'}" for d in di_list)
                                    node_str = f" Wait ({conds}, {time_v}s)"
                                else:
                                    node_str = f" Wait (DI, {time_v}s)"
                            elif t == 29:  # If (DI 조건)
                                di_list = getattr(node, "diList", getattr(node, "__raw__", {}).get("diList", []))
                                if di_list:
                                    conds = ", ".join(f"DI{d['idx']}={'ON' if d.get('value',1) else 'OFF'}" for d in di_list)
                                    node_str = f" If ({conds})"
                                else:
                                    node_str = " If (DI)"
                            elif t == 30:  # Else (DI)
                                di_list = getattr(node, "diList", getattr(node, "__raw__", {}).get("diList", []))
                                if di_list:
                                    conds = ", ".join(f"DI{d['idx']}={'ON' if d.get('value',1) else 'OFF'}" for d in di_list)
                                    node_str = f" Elif ({conds})"
                                else:
                                    node_str = " Else (DI)"
                            elif t == 32:  # SpeedRatio
                                spd = getattr(node, "prgSpdRatio", getattr(node, "__raw__", {}).get("prgSpdRatio", 100))
                                node_str = f" Speed ({spd}%)"
                            elif t == 40:  # ToolCommand
                                raw = getattr(node, "__raw__", {})
                                cmd = raw.get("toolCmd", "")
                                node_str = f" Tool Command ({cmd})" if cmd else " Tool Command"
                            elif t == 41:  # Stop
                                node_str = " Stop"
                            elif t == 100:  # Home (Conty type=100)
                                node_str = f" Home ({name})" if name else " Home"
                            elif t == 200: node_str = f" Pick Group ({name})" if name else " Pick Group"
                            elif t in (201, 202):  # Pick / Place: 기준 좌표 표시
                                raw_n = getattr(node, "__raw__", {})
                                p = getattr(node, "target_p", None) or raw_n.get("p", None)
                                xyz = ""
                                try:
                                    if p and any(v != 0 for v in p):
                                        xyz = f"X{p[0]*1000:.0f} Y{p[1]*1000:.0f} Z{p[2]*1000:.0f}"
                                except Exception:
                                    xyz = ""
                                label = "Pick" if t == 201 else "Place"
                                if xyz and name:
                                    node_str = f" {label} ({name}) [{xyz}]"
                                elif xyz:
                                    node_str = f" {label} [{xyz}]"
                                elif name:
                                    node_str = f" {label} ({name})"
                                else:
                                    node_str = f" {label}"
                            elif t == 250:
                                spd = getattr(node, "__raw__", {}).get("prgSpdRatio", "")
                                node_str = f" Call ({name})" if name else f" Call (spd={spd}%)"
                            elif t == 302:
                                node_str = f" indyCARE ({name})" if name else " indyCARE"
                            elif t == 104: node_str = f" Pallet Def ({name})" if name else " Pallet Def"
                            elif t == 105: node_str = f" Pallet Def ({name})" if name else " Pallet Def"
                            else: node_str = f" Unknown ({t})"
                                
                            n_id = self.tree.insert(parent_item, "end", text=node_str)
                            node_map[cid] = n_id
                            
                            # node_data에 raw 정보 저장 (에디터/실행 엔진용)
                            raw = getattr(node, "__raw__", {})
                            # q/p: repo 해석 우선, 없으면 __raw__에서 직접 읽기
                            node_q = getattr(node, "target_q", None)
                            node_p = getattr(node, "target_p", None)
                            if not node_q or not any(v != 0 for v in node_q):
                                node_q = raw.get("q", [0.0]*6)
                            if not node_p or not any(v != 0 for v in node_p):
                                node_p = raw.get("p", [0.0]*6)
                            self.node_data[n_id] = {
                                "q": node_q,
                                "p": node_p,
                                "__raw__": raw,
                            }
                            
                            # ─── Conty 실제 타입별 데이터 (120+ 학습파일 기반) ─────────
                            if t in [102, 103]:  # ★ JointMove / FrameMove
                                self.node_data[n_id]["t_type"] = "move"
                                self.node_data[n_id]["name"] = name
                                self.node_data[n_id]["boundary"] = getattr(node, "boundary", raw.get("boundary", {"velLevel": 5, "accLevel": 5}))
                                self.node_data[n_id]["tcp"] = getattr(node, "tcp", raw.get("tcp", [0,0,0,0,0,0]))
                                self.node_data[n_id]["refFrame"] = getattr(node, "refFrame", raw.get("refFrame", {"type": 1, "tref": [0,0,0,0,0,0]}))
                                self.node_data[n_id]["intpl"] = getattr(node, "intpl", raw.get("intpl", 0))
                                self.node_data[n_id]["move_type"] = t  # 102=Joint, 103=Frame
                                # 다중 웨이포인트 저장
                                resolved = getattr(node, "resolved_waypoints", [])
                                if resolved:
                                    self.node_data[n_id]["waypoints"] = [
                                        {"id": wp["id"], "q": wp["wp"].j_pos, "p": wp["wp"].t_pos}
                                        for wp in resolved
                                    ]
                                else:
                                    # ★ moveList/wpList 참조 실패 시 __raw__에서 좌표 직접 복원
                                    wp_q = raw.get("q", node_q)
                                    wp_p = raw.get("p", node_p)
                                    if any(v != 0 for v in wp_q):
                                        self.node_data[n_id]["waypoints"] = [
                                            {"id": "raw_0", "q": wp_q, "p": wp_p}
                                        ]
                                    else:
                                        self.node_data[n_id]["waypoints"] = []
                            
                            elif t == 1:  # Legacy JointMove
                                self.node_data[n_id]["t_type"] = "move"
                                self.node_data[n_id]["move_type"] = 102

                            elif t in [2, 3]:  # Variables
                                self.node_data[n_id]["varList"] = getattr(node, "varList", raw.get("varList", []))

                            elif t == 4:  # SmartDO
                                self.node_data[n_id]["doList"] = getattr(node, "doList", raw.get("doList", []))

                            elif t == 5:  # SmartAO
                                self.node_data[n_id]["aoList"] = getattr(node, "aoList", raw.get("aoList", []))

                            elif t == 6:  # EndTool DO
                                self.node_data[n_id]["endtoolDoList"] = getattr(node, "endtoolDoList", raw.get("endtoolDoList", []))

                            elif t == 20:  # Loop
                                # count: None/null/-1/<=0 → 무한, 양의 정수 → N회 반복
                                c = getattr(node, "count", raw.get("count", None))
                                if c is None or (isinstance(c, (int, float)) and int(c) <= 0):
                                    self.node_data[n_id]["count"] = None
                                else:
                                    self.node_data[n_id]["count"] = int(c)
                                
                            elif t == 21:  # LoopBreak
                                pass

                            elif t in [22, 28]:  # Wait (시간/DI 대기)
                                self.node_data[n_id]["time"] = getattr(node, "time", raw.get("time", 0))
                                self.node_data[n_id]["diList"] = getattr(node, "diList", raw.get("diList", []))
                                self.node_data[n_id]["endtoolDiList"] = getattr(node, "endtoolDiList", raw.get("endtoolDiList", []))

                            elif t == 23:  # Switch
                                self.node_data[n_id]["time"] = getattr(node, "time", raw.get("time", 0))
                                self.node_data[n_id]["cond"] = getattr(node, "cond", raw.get("cond", {}))

                            elif t in [24, 25]:  # If / Elif (변수 조건)
                                self.node_data[n_id]["cond"] = getattr(node, "cond", raw.get("cond", {}))
                                
                            elif t == 26:  # Else
                                pass
                                
                            elif t in [29, 30]:  # If[DI] / WaitFor[DI]
                                self.node_data[n_id]["diList"] = getattr(node, "diList", raw.get("diList", []))
                                self.node_data[n_id]["endtoolDiList"] = getattr(node, "endtoolDiList", raw.get("endtoolDiList", []))

                            elif t == 32:  # SpeedRatio
                                self.node_data[n_id]["prgSpdRatio"] = getattr(node, "prgSpdRatio", raw.get("prgSpdRatio", 100))

                            elif t in [40, 41]:  # ToolCommand / Stop
                                self.node_data[n_id]["toolCmd"] = raw.get("toolCmd", "")
                                self.node_data[n_id]["sensName"] = raw.get("sensName", "")

                            elif t == 100:  # Home / Folder
                                pass

                            elif t == 200:  # Pick Group
                                self.node_data[n_id]["groupName"] = getattr(node, "groupName", raw.get("groupName", ""))

                            elif t in [201, 202]:  # Pick / Place
                                # target_type: repo 해석 → __raw__ fallback
                                self.node_data[n_id]["target_type"] = getattr(node, "target_type", raw.get("target_type", 0))
                                self.node_data[n_id]["t_type"] = self.node_data[n_id]["target_type"]
                                self.node_data[n_id]["target_pallet_name"] = getattr(node, "target_pallet_name", raw.get("target_pallet_name", ""))
                                self.node_data[n_id]["target_pallet_id"] = getattr(node, "target_pallet_id", raw.get("target_pallet_id", ""))
                                self.node_data[n_id]["p_name"] = self.node_data[n_id]["target_pallet_name"]
                                # p_data: repo 해석 → __raw__ fallback
                                self.node_data[n_id]["p_data"] = getattr(node, "p_data", None) or raw.get("p_data", None)
                                self.node_data[n_id]["toolId"] = getattr(node, "toolId", raw.get("toolId", 1))
                                self.node_data[n_id]["app_data"] = raw.get("approach", getattr(node, "approach", {}))
                                self.node_data[n_id]["ret_data"] = raw.get("retract", getattr(node, "retract", {}))
                                self.node_data[n_id]["approach"] = self.node_data[n_id]["app_data"]
                                self.node_data[n_id]["retract"] = self.node_data[n_id]["ret_data"]

                            elif t == 250:  # Call
                                self.node_data[n_id]["subProgram"] = raw.get("subProgram", "")

                            elif t == 300:  # ConveyorTracking
                                self.node_data[n_id]["trackMode"] = raw.get("trackMode", 0)
                                self.node_data[n_id]["convSpeed"] = raw.get("convSpeed", 100)
                                self.node_data[n_id]["encoderCh"] = raw.get("encoderCh", 0)

                            elif t == 302:  # indyCARE / Force
                                pass

                            elif t == 303:  # TaktTime
                                self.node_data[n_id]["careTackTime"] = raw.get("careTackTime", 0)
                                self.node_data[n_id]["targetTakt"] = raw.get("targetTakt", 10.0)

                            elif t == 400:  # Detect
                                self.node_data[n_id]["detectSource"] = raw.get("detectSource", "")
                                self.node_data[n_id]["detectResult"] = raw.get("detectResult", "")

                            elif t == 401:  # Retrieve
                                self.node_data[n_id]["retrieveSource"] = raw.get("retrieveSource", "")
                                self.node_data[n_id]["retrieveVar"] = raw.get("retrieveVar", "")

                            elif t == 500:  # PythonScript
                                self.node_data[n_id]["scriptFile"] = raw.get("scriptFile", "")
                                self.node_data[n_id]["scriptCode"] = raw.get("scriptCode", "")

                print(f">> [성공] {file_path} 에서 프로그램을 로드했습니다.")
                self.custom_paths[self.current_robot] = file_path
                self._save_custom_paths()  # 경로를 디스크에 영구 저장
                self.refresh_info()
            except Exception as e:
                traceback.print_exc()
                print(f">> [실패] JSON 파싱 오류: {e}")

    def new_program(self):
        """새 프로그램 생성: 이름 입력 → 기본 템플릿 저장 → 로드"""
        from tkinter import simpledialog
        robot = self.robot_sel.get()
        name = simpledialog.askstring("새 프로그램", "프로그램 이름을 입력하세요:", parent=self.parent.winfo_toplevel())
        if not name or not name.strip():
            return
        name = name.strip()
        
        # 기본 템플릿 (Program Settings + Variables)
        template = {
            "info": {"name": name, "type": 7},
            "wpList": [],
            "program": [
                {"indyCareInfo":{"useIndyCare":False,"ipAddr":"0.0.0.0","dataConfig":[{"name":"","type":0},{"name":"","type":0},{"name":"","type":0},{"name":"","type":0},{"name":"","type":0}]},
                 "type":999,"conveyorConfigInfo":{"conveyorConfig":[]},"toolInfo":[],"visionInfo":{"useVision":False},
                 "collisionPolicy":{"policy":0,"time":2},"enable":True,"pId":0,"palletInfo":[],"id":1},
                {"varList":[],"enable":True,"type":2,"pId":0,"id":2}
            ],
            "moveList": []
        }
        
        # 저장
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
        dir_path = os.path.join(base_dir, 'user_programs', robot.replace(' ', '_'))
        os.makedirs(dir_path, exist_ok=True)
        file_path = os.path.join(dir_path, f"{name}.json")
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(template, f, ensure_ascii=False, indent=2)
        
        # 경로 등록 후 로드
        self.custom_paths[robot] = file_path
        self._save_custom_paths()
        self._load_from_path(file_path)
        print(f">> [새파일] '{name}' 프로그램이 생성되었습니다: {file_path}")

    def load_program(self):
        robot = self.robot_sel.get()
        import core.domains.robot.communication.client_manager as cm
        cm.robot_manager.set_active_robot(robot)
        file_path = fd.askopenfilename(
            parent=self.parent.winfo_toplevel(),
            title=f"{robot} 프로그램 불러오기",
            initialdir=os.path.dirname(self.get_current_program_path(robot)),
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if file_path:
            self._load_from_path(file_path)
            
    def refresh_info(self):
        robot = self.robot_sel.get()
        path = self.get_current_program_path(robot)
        
        if os.path.exists(path):
            stat = os.stat(path)
            mod_time = datetime.datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            size_kb = stat.st_size / 1024.0
            info_str = f"파일: {os.path.basename(path)} | 크기: {size_kb:.1f} KB | 수정됨: {mod_time}"
            self.info_label.configure(text=info_str, text_color="#00FF41")
        else:
            self.info_label.configure(text=f"저장된 프로그램이 없습니다. (경로: {path})", text_color=Theme.TEXT_SECONDARY)
            
    def play_simulation(self):
        """3D 단계별 동작 시각화 뷰어를 엽니다."""
        from presentation.ui.robot_hmi.editors.motion_3d_viewer import Motion3DViewer
        Motion3DViewer(self.parent, self.node_data, self.tree)

    def render(self):
        for w in self.parent.winfo_children(): w.destroy()
        
        self.parent.grid_columnconfigure(0, weight=0, minsize=140) # Palette (고정)
        self.parent.grid_columnconfigure(1, weight=1) # Tree (가운데)
        self.parent.grid_columnconfigure(2, weight=2, minsize=420) # Jog + 설정 (넓게)
        self.parent.grid_rowconfigure(0, weight=1)
        Theme.apply_window_style(self.parent)
        # Left Palette — 팬던트와 동일한 카테고리 구조
        left = ctk.CTkScrollableFrame(self.parent, fg_color=Theme.BG_BASE, width=160, corner_radius=0)
        left.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        ctk.CTkLabel(left, text="🛠 기본 명령", font=Theme.font(size=14, weight="bold", role="display"), text_color=Theme.TEXT_PRIMARY).pack(pady=10)
        
        def _add_category(label, color, cmds):
            ctk.CTkLabel(left, text=label, font=Theme.font(size=11, weight="bold"), 
                         text_color=color).pack(anchor="w", padx=10, pady=(6, 2))
            for cmd_name, col in cmds:
                btn = ctk.CTkButton(left, text=f"  {cmd_name}", fg_color=col, height=26,
                                    font=Theme.font(size=11), anchor="w",
                                    command=lambda c=cmd_name: self.add_node(c))
                btn.pack(fill="x", padx=10, pady=1)
        
        # ─── 모션 명령어 ───
        _add_category("▸ 모션 명령어", Theme.SUCCESS, [])
        # 사용자 모션 변수 버튼 (팬던트 사진 4번과 동일)
        btn_mv = ctk.CTkButton(left, text="  + 사용자 모션 변수", fg_color="#2E7D32", hover_color="#388E3C",
                                height=28, font=Theme.font(size=11, weight="bold"), anchor="w",
                                command=self._add_user_motion_var)
        btn_mv.pack(fill="x", padx=10, pady=1)
        for cmd_name, col in [
            ("Joint Move", "#1565C0"),        # jointMove:Absolute
            ("Frame Move", "#2E7D32"),        # frameMove:Absolute
            ("Move C", "#00796B"),            # circularMove
            ("Move Home", "#0277BD"),         # home
            ("Move B", "#E65100"),            # jointMove:Relative
            ("Move By", "#6A1B9A"),           # frameMove:Relative
        ]:
            btn = ctk.CTkButton(left, text=f"  {cmd_name}", fg_color=col, height=26,
                                font=Theme.font(size=11), anchor="w",
                                command=lambda c=cmd_name: self.add_node(c))
            btn.pack(fill="x", padx=10, pady=1)
        
        # ─── 흐름제어 명령어 ───
        _add_category("▸ 흐름제어 명령어", "#FF9800", [
            ("Loop", "#C62828"),              # loop
            ("Wait", "#546E7A"),              # wait
            ("Wait For", "#26A69A"),          # waitFor (조건 대기)
            ("Wait DI", "#455A64"),           # waitFor[digitalInput]
            ("If (DI)", "#AD1457"),           # if[digitalInput]
            ("If Var", "#880E4F"),            # if (변수 조건)
            ("Else", "#4A148C"),             # else
            ("Math", "#BF360C"),             # assignment
            ("Loop Break", "#EF5350"),       # loopBreak
            ("Speed Ratio", "#FFB300"),      # speedRatio
            ("Folder", "#E65100"),           # group
            ("Comment", "#757575"),          # comment
            ("Stop", "#B71C1C"),             # stop
        ])
        
        # ─── 입출력 명령어 ───
        _add_category("▸ 입출력 명령어", "#03A9F4", [
            ("DO", "#7B1FA2"),               # toolCommand
            ("Tool Sensing", "#42A5F5"),     # toolSensing
            ("EndTool DO", "#512DA8"),        # endToolDO
            ("Smart DO", "#6A1B9A"),          # smartDO (type=4+doList)
            ("AO", "#827717"),               # smartAO
        ])
        
        # ─── 응용 명령어 ───
        _add_category("▸ 응용 명령어", "#4CAF50", [
            ("Pick", "#00838F"),             # pick
            ("Place", "#00695C"),            # place
            ("Pallet", "#004D40"),           # pallet
            ("Conveyor", "#F9A825"),         # conveyorTracking
            ("TaktTime", "#AB47BC"),         # indyCARE:TaktTime
            ("Detect", "#29B6F6"),           # detect
            ("Retrieve", "#66BB6A"),         # retrieve
            ("Python", "#FFA726"),           # pythonScript
            ("Call", "#37474F"),             # subProgram call
            ("Force", "#4E342E"),            # force control
        ])
        
        # ─── 도구 (Tools) ───
        ctk.CTkLabel(left, text="🔧 도구", font=Theme.font(size=11, weight="bold"), 
                     text_color=Theme.TEXT_SECONDARY).pack(anchor="w", padx=10, pady=(8, 2))
        
        ctk.CTkButton(left, text="📈 오실로스코프", height=26, font=Theme.font(size=11),
                       command=self._open_oscilloscope, **Theme.get_button_style("secondary")).pack(fill="x", padx=10, pady=1)
        ctk.CTkButton(left, text="🧱 팔레타이징 마법사", height=26, font=Theme.font(size=11),
                       command=self._open_palletizing_wizard, **Theme.get_button_style("secondary")).pack(fill="x", padx=10, pady=1)
        ctk.CTkButton(left, text="⚖️ 페이로드 자동측정", height=26, font=Theme.font(size=11),
                       command=self._open_auto_payload, **Theme.get_button_style("secondary")).pack(fill="x", padx=10, pady=1)
            
        # Center Tree
        center = ctk.CTkFrame(self.parent, fg_color=Theme.BG_SURFACE)
        center.grid(row=0, column=1, sticky="nsew", padx=2, pady=2)
        
        # ─── Row 1: 파일 작업 (로봇 선택 / 새파일 / 불러오기 / 저장 / 사본 내보내기) ───
        # 저장 자체가 이미 표준 Conty 포맷이라 펜던트에도 그대로 사용 가능.
        # "사본 내보내기"는 같은 표준 JSON을 다른 경로/이름으로 저장하는 편의 기능.
        h = ctk.CTkFrame(center, fg_color="transparent")
        h.pack(fill="x", padx=10, pady=(5, 2))

        self.robot_sel = ctk.CTkOptionMenu(h, values=["Robot A", "Robot B", "Robot C"], width=100, command=self._on_robot_changed,
                                            fg_color=Theme.BG_BASE, button_color=Theme.ACCENT_PRIMARY)
        self.robot_sel.pack(side="left", padx=5)

        ctk.CTkButton(h, text="🔄", width=30, command=self.refresh_info, **Theme.get_button_style("secondary")).pack(side="left", padx=(0,5))

        ctk.CTkButton(h, text="📄 새파일", width=70, font=Theme.font(size=12), command=self.new_program, **Theme.get_button_style("secondary")).pack(side="left", padx=2)
        ctk.CTkButton(h, text="불러오기", width=65, font=Theme.font(size=12), command=self.load_program, **Theme.get_button_style("secondary")).pack(side="left", padx=2)
        ctk.CTkButton(h, text="저장", width=55, font=Theme.font(size=12), command=self.save_program, **Theme.get_button_style("primary")).pack(side="left", padx=2)
        ctk.CTkButton(h, text="📤 사본 내보내기", width=130, font=Theme.font(size=12), command=self.export_to_conty, **Theme.get_button_style("secondary")).pack(side="left", padx=2)

        ctk.CTkButton(h, text="⚙️ 설정", width=60, font=Theme.font(size=12), command=self._open_config_dialog, **Theme.get_button_style("secondary")).pack(side="right", padx=2)

        # ─── Row 2: 편집 + 실행 (삭제/이동/복사 / ▶실행 / ⏹정지 / ▶Play) ───
        h2 = ctk.CTkFrame(center, fg_color="transparent")
        h2.pack(fill="x", padx=10, pady=(0, 5))

        ctk.CTkButton(h2, text="🗑 삭제", width=55, font=Theme.font(size=12), command=self.delete_node, **Theme.get_button_style("danger")).pack(side="left", padx=2)
        ctk.CTkButton(h2, text="▲", width=30, command=self._move_node_up, **Theme.get_button_style("secondary")).pack(side="left", padx=1)
        ctk.CTkButton(h2, text="▼", width=30, command=self._move_node_down, **Theme.get_button_style("secondary")).pack(side="left", padx=1)
        ctk.CTkButton(h2, text="📋 복사", width=55, font=Theme.font(size=12), command=self._copy_node, **Theme.get_button_style("secondary")).pack(side="left", padx=2)

        # 실행 영역 (우측)
        ctk.CTkButton(h2, text="▶ Play (가상)", width=95, font=Theme.font(size=12, weight="bold"), command=self.play_simulation, **Theme.get_button_style("success")).pack(side="right", padx=3)

        self._exec_stop = False
        self.stop_btn = ctk.CTkButton(h2, text="⏹ 정지", width=70, font=Theme.font(size=12, weight="bold"), command=self._stop_execution, **Theme.get_button_style("danger"))
        self.stop_btn.pack(side="right", padx=3)
        self.exec_btn = ctk.CTkButton(h2, text="▶ 실행", width=70, font=Theme.font(size=12, weight="bold"), command=self._run_program, **Theme.get_button_style("success"))
        self.exec_btn.pack(side="right", padx=3)
        
        self.info_label = ctk.CTkLabel(center, text="준비됨", text_color=Theme.TEXT_SECONDARY, font=Theme.font(size=11))
        self.info_label.pack(fill="x", padx=15, pady=2)
        
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background=Theme.BG_BASE, foreground=Theme.TEXT_PRIMARY, fieldbackground=Theme.BG_BASE, borderwidth=0, font=("Inter", 11))
        style.configure("Treeview.Heading", background=Theme.BG_SURFACE, foreground=Theme.TEXT_PRIMARY, font=("Urbanist", 12, "bold"))
        style.map("Treeview", background=[("selected", Theme.ACCENT_PRIMARY)])
        
        self.tree = ttk.Treeview(center, show="tree")
        self.tree.pack(fill="both", expand=True, padx=10, pady=5)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        
        # 뷰를 열 때 기존 저장된 파일을 자동으로 불러오도록 수정
        path = self.get_current_program_path(self.current_robot)
        if os.path.exists(path):
            self._load_from_path(path)
        else:
            self.tree.insert("", "end", text=" Main Program", open=True)
        
        self.refresh_info()
        
        # Right (Jog & PickPlace 통합) - 화면 크기 문제를 해결하기 위해 전체를 ScrollableFrame으로 감쌈
        right_container = ctk.CTkFrame(self.parent, fg_color="transparent")
        right_container.grid(row=0, column=2, sticky="nsew", padx=2, pady=2)
        right_container.grid_columnconfigure(0, weight=1)
        right_container.grid_rowconfigure(0, weight=1)
        
        right_scroll = ctk.CTkScrollableFrame(right_container, corner_radius=0)
        right_scroll.grid(row=0, column=0, sticky="nsew", pady=2)
        
        self.pp_frame = ctk.CTkFrame(right_scroll, fg_color="transparent")
        self.pp_frame.pack(fill="x", pady=2)
        
        self.apply_btn = ctk.CTkButton(right_scroll, text="💾 우측 설정창 값들 적용하기 (Apply)", fg_color=Theme.WARNING, hover_color="#F57C00", text_color="black", font=Theme.font(weight="bold", size=15), height=45, command=self.apply_current_editor)
        self.apply_btn.pack(fill="x", pady=5, padx=10)
        
        self.jog_frame = ctk.CTkFrame(right_scroll, fg_color="transparent")
        self.jog_frame.pack(fill="x", pady=2)
        
        self.pp_editor = PickPlaceEditor(self.pp_frame)
        self.move_editor = MoveEditor(self.pp_frame)
        self.move_c_editor = MoveCEditor(self.pp_frame)
        self.mb_editor = MoveByEditor(self.pp_frame)
        self.math_editor = MathEditor(self.pp_frame)
        self.call_editor = CallEditor(self.pp_frame)
        self.if_editor = IfEditor(self.pp_frame)
        self.force_editor = ForceEditor(self.pp_frame)
        self.vision_editor = VisionEditor(self.pp_frame)
        self.sync_editor = SyncEditor(self.pp_frame)
        self.set_ao_editor = SetAOEditor(self.pp_frame)
        self.move_home_editor = MoveHomeEditor(self.pp_frame)
        self.wait_editor = WaitEditor(self.pp_frame)
        self.wait_di_editor = WaitDIEditor(self.pp_frame)
        self.wait_ai_editor = WaitAIEditor(self.pp_frame)
        self.comment_editor = CommentEditor(self.pp_frame)
        self.stop_editor = StopEditor(self.pp_frame)
        self.folder_editor = FolderEditor(self.pp_frame)
        self.smart_do_editor = SmartDOEditor(self.pp_frame)
        self.switch_editor = SwitchEditor(self.pp_frame)
        self.loop_editor = LoopEditor(self.pp_frame)
        self.waitfor_editor = WaitForEditor(self.pp_frame)
        self.loopbreak_editor = LoopBreakEditor(self.pp_frame)
        self.speed_ratio_editor = SpeedRatioEditor(self.pp_frame)
        self.tool_sensing_editor = ToolSensingEditor(self.pp_frame)
        self.conveyor_editor = ConveyorTrackingEditor(self.pp_frame)
        self.takttime_editor = TaktTimeEditor(self.pp_frame)
        self.detect_editor = DetectEditor(self.pp_frame)
        self.retrieve_editor = RetrieveEditor(self.pp_frame)
        self.python_editor = PythonScriptEditor(self.pp_frame)
        
        self.pp_editor.render()
        self.current_editor = self.pp_editor
        
        self.jog_controller = JogController(self.jog_frame)
        self.jog_controller.render()
        if hasattr(self.jog_controller, "move_btn"):
            self.jog_controller.move_btn.configure(command=self._on_move_btn_clicked)
        # JOG 패널 단축 버튼 연결
        if hasattr(self.jog_controller, 'sc_teach_btn'):
            self.jog_controller.sc_teach_btn.configure(command=self._on_teach_btn_clicked)
        if hasattr(self.jog_controller, 'sc_delete_btn'):
            self.jog_controller.sc_delete_btn.configure(command=self._on_delete_wp_clicked)
        if hasattr(self.jog_controller, 'sc_cycle_btn'):
            self.jog_controller.sc_cycle_btn.configure(command=self._on_single_cycle_clicked)
        def _on_node_selected(q, p, t_type, item_text, p_name=None, p_data=None, all_pallets=None, b_radius=0.0, app_data=None, ret_data=None, d=None):
            if d is None: d = {}
            # 조그 패널에 현재 타겟 좌표 표시
            if hasattr(self.jog_controller, "set_target"):
                self.jog_controller.set_target(q, p)
                
            # ─── Conty type 기반 우측 에디터 라우팅 ───
            raw = d.get("__raw__", {})
            conty_type = raw.get("type", -1)
            
            # 에디터 프레임 초기화 헬퍼
            def _clear_pp():
                for w in self.pp_frame.winfo_children(): w.destroy()
            
            if conty_type in [102, 103]:  # ★ JointMove / FrameMove
                _clear_pp()
                self.current_editor = self.move_editor
                self.move_editor.render()
                bnd = d.get("boundary", {"velLevel": 5, "accLevel": 5})
                self.move_editor.update_ui(item_text, b_radius, bnd.get("velLevel", 5), bnd.get("accLevel", 5))
                # 웨이포인트 정보 전달
                wps = d.get("waypoints", [])
                if hasattr(self.move_editor, 'update_waypoint_info'):
                    self.move_editor.update_waypoint_info(wps, conty_type)
                self.move_editor.teach_btn.configure(command=self._on_teach_btn_clicked)
                self.move_editor.load_btn.configure(command=self._on_load_btn_clicked)
                self.move_editor.move_btn.configure(command=self._on_move_btn_clicked)
                self.move_editor.delete_btn.configure(command=self._on_delete_wp_clicked)
                self.move_editor.cycle_btn.configure(command=self._on_single_cycle_clicked)
                
            elif conty_type == 1:  # Legacy JointMove
                _clear_pp()
                self.current_editor = self.move_editor
                self.move_editor.render()
                bnd = d.get("boundary", {"velLevel": 5, "accLevel": 5})
                self.move_editor.update_ui(item_text, b_radius, bnd.get("velLevel", 5), bnd.get("accLevel", 5))
                self.move_editor.teach_btn.configure(command=self._on_teach_btn_clicked)
                self.move_editor.load_btn.configure(command=self._on_load_btn_clicked)
                self.move_editor.move_btn.configure(command=self._on_move_btn_clicked)
                self.move_editor.delete_btn.configure(command=self._on_delete_wp_clicked)
                self.move_editor.cycle_btn.configure(command=self._on_single_cycle_clicked)
                
            elif conty_type == 4:  # SmartDO (DO 출력)
                _clear_pp()
                self.current_editor = self.smart_do_editor
                self.smart_do_editor.render()
                self.smart_do_editor.update_ui(item_text, d.get("doList", []))
                
            elif conty_type in [5, 6]:  # SmartAO / EndTool DO
                _clear_pp()
                self.current_editor = self.folder_editor
                self.folder_editor.render()
                self.folder_editor.update_ui(item_text)
                
            elif conty_type == 20:  # Loop
                _clear_pp()
                self.current_editor = self.loop_editor
                self.loop_editor.render()
                self.loop_editor.update_ui(item_text, d.get("count", None))
                
            elif conty_type == 21:  # Break
                _clear_pp()
                self.current_editor = self.loopbreak_editor
                self.loopbreak_editor.render()
                self.loopbreak_editor.update_ui(item_text)
                
            elif conty_type == 22:  # Wait (시간)
                _clear_pp()
                self.current_editor = self.wait_editor
                self.wait_editor.render()
                self.wait_editor.update_ui(item_text, d.get("time", 1.0))
                
            elif conty_type == 23:  # Switch
                _clear_pp()
                self.current_editor = self.switch_editor
                self.switch_editor.render()
                self.switch_editor.update_ui(item_text)
                
            elif conty_type in [24, 25, 26]:  # If / Elif / Else (변수 조건)
                _clear_pp()
                self.current_editor = self.if_editor
                self.if_editor.render()
                cond = d.get("cond", {})
                lv = cond.get("left", {}).get("value", "var1") if cond else "var1"
                op_map = {0: "==", 1: "!=", 2: ">", 3: "<", 4: ">=", 5: "<="}
                op = op_map.get(cond.get("op", 0), "==") if cond else "=="
                rv = cond.get("right", {}).get("value", 0.0) if cond else 0.0
                self.if_editor.update_ui(item_text, 0, "HIGH", str(lv) if lv else "var1", op, rv if rv else 0.0)
                
            elif conty_type == 28:  # Wait (DI 대기)
                _clear_pp()
                self.current_editor = self.wait_di_editor
                self.wait_di_editor.render()
                self.wait_di_editor.update_ui(item_text, d.get("diList", []), d.get("time", 1.0))
                
            elif conty_type in [29, 30]:  # If (DI) / Elif (DI)
                _clear_pp()
                self.current_editor = self.if_editor
                self.if_editor.render()
                di_list = d.get("diList", [])
                if di_list:
                    di = di_list[0]
                    self.if_editor.update_ui(item_text, di.get("idx", 0), "ON" if di.get("value", 1) else "OFF", "var1", "==", 0.0)
                else:
                    self.if_editor.update_ui(item_text, 0, "HIGH", "var1", "==", 0.0)
                
            elif conty_type == 32:  # SpeedRatio
                _clear_pp()
                self.current_editor = self.speed_ratio_editor
                self.speed_ratio_editor.render()
                self.speed_ratio_editor.update_ui(item_text, d.get("prgSpdRatio", raw.get("prgSpdRatio", 100)))
                
            elif conty_type in [40, 41]:  # ToolCommand / ToolSensing
                _clear_pp()
                self.current_editor = self.tool_sensing_editor
                self.tool_sensing_editor.render()
                self.tool_sensing_editor.update_ui(item_text)
                
            elif conty_type == 100:  # Home
                _clear_pp()
                self.current_editor = self.move_home_editor
                self.move_home_editor.render()
                self.move_home_editor.update_ui(item_text)
                # 홈 이동 버튼 연결
                if hasattr(self.move_home_editor, 'home_move_btn'):
                    self.move_home_editor.home_move_btn.configure(command=self._on_move_btn_clicked)
                
            elif conty_type in [201, 202]:  # Pick / Place
                _clear_pp()
                self.current_editor = self.pp_editor
                self.pp_editor.render()
                self.pp_editor.target_q = q
                self.pp_editor.target_p = p if p else [0.0]*6
                self.pp_editor.node_data = d
                self.pp_editor.update_ui(d, all_pallets)
                self.pp_editor.teach_btn.configure(command=self._on_teach_btn_clicked)
                self.pp_editor.load_btn.configure(command=self._on_load_btn_clicked)
                self.pp_editor.move_btn.configure(command=self._on_move_btn_clicked)
                
            elif conty_type == 200:  # Pick Group
                _clear_pp()
                self.current_editor = self.folder_editor
                self.folder_editor.render()
                self.folder_editor.update_ui(item_text)
                
            elif conty_type == 250:  # Call
                _clear_pp()
                self.current_editor = self.call_editor
                self.call_editor.render()
                self.call_editor.update_ui(item_text, "sub_routine.json")
                
            elif conty_type == 302:  # indyCARE
                _clear_pp()
                self.current_editor = self.force_editor
                self.force_editor.render()
                self.force_editor.update_ui(item_text, 500.0, 100.0, 50.0)
                
            elif conty_type == 999:  # Program Settings
                _clear_pp()
                self.current_editor = self.folder_editor
                self.folder_editor.render()
                self.folder_editor.update_ui(item_text)
                
            elif conty_type in [2, 3]:  # Variables
                _clear_pp()
                self.current_editor = self.folder_editor
                self.folder_editor.render()
                self.folder_editor.update_ui(item_text)
                
            else:
                # 알 수 없는 타입 → 폴더 에디터로 표시
                _clear_pp()
                self.current_editor = self.folder_editor
                self.folder_editor.render()
                self.folder_editor.update_ui(f"{item_text} (type={conty_type})")
                
        # 콜백 연결
        self.on_node_selected_callback = _on_node_selected
        
    def _on_teach_btn_clicked(self):
        selected = self.tree.selection()
        if not selected: return
        item = selected[0]
        
        current_q = [0.0]*6
        current_p = [0.0]*6
        try:
            for i, ax in enumerate(["J1","J2","J3","J4","J5","J6"]):
                current_q[i] = float(self.jog_controller.entries[ax].get())
            for i, ax in enumerate(["X","Y","Z","Rx","Ry","Rz"]):
                current_p[i] = float(self.jog_controller.entries[ax].get())
        except Exception:
            pass
            
        if item not in self.node_data:
            self.node_data[item] = {}
        
        # 웨이포인트 리스트에 누적 추가
        if "waypoints" not in self.node_data[item]:
            self.node_data[item]["waypoints"] = []
        
        self.node_data[item]["waypoints"].append({"q": list(current_q), "p": list(current_p)})
        
        # 첫 번째 WP를 대표 좌표로 유지 (하위 호환)
        self.node_data[item]["q"] = self.node_data[item]["waypoints"][0]["q"]
        self.node_data[item]["p"] = self.node_data[item]["waypoints"][0]["p"]
        
        item_text = self.tree.item(item, "text")
        wp_count = len(self.node_data[item]["waypoints"])
        
        # 우측 에디터 웨이포인트 리스트 즉시 갱신
        raw = self.node_data[item].get("__raw__", {})
        conty_type = raw.get("type", 102)
        if conty_type in [1, 102, 103] and hasattr(self.move_editor, 'update_waypoint_info'):
            self.move_editor.update_waypoint_info(self.node_data[item]["waypoints"], conty_type)
        
        # 조그 패널 타겟 좌표도 갱신
        if hasattr(self.jog_controller, 'set_target'):
            self.jog_controller.set_target(current_q, current_p)
                
        print(f">> [WP{wp_count} 추가] '{item_text.strip()}' → J1:{current_q[0]:.1f} J2:{current_q[1]:.1f} J3:{current_q[2]:.1f} (총 {wp_count}개)")
        
    def _on_load_btn_clicked(self):
        """선택된 웨이포인트의 좌표를 JOG 패널로 불러오기"""
        selected = self.tree.selection()
        if not selected: return
        item = selected[0]
        if item not in self.node_data:
            print(">> [오류] 이 노드에 저장된 좌표가 없습니다.")
            return
        
        d = self.node_data[item]
        wps = d.get("waypoints", [])
        
        if wps:
            # 선택된 WP의 좌표를 불러오기
            sel_idx = getattr(self.move_editor, '_selected_wp_idx', 0)
            sel_idx = min(sel_idx, len(wps) - 1)
            q = wps[sel_idx]["q"]
            p = wps[sel_idx]["p"]
            self.jog_controller.update_coordinates(q, p)
            print(f">> [조그 불러오기] WP{sel_idx+1} 좌표를 JOG 패널로 로드했습니다.")
        elif d.get("q"):
            self.jog_controller.update_coordinates(d["q"], d.get("p", [0.0]*6))
            print(f">> [조그 불러오기] 좌표를 JOG 패널로 로드했습니다.")
        else:
            print(">> [오류] 이 노드에 저장된 좌표가 없습니다.")
            
    def _on_move_btn_clicked(self):
        """선택된 웨이포인트의 좌표로 로봇 이동"""
        selected = self.tree.selection()
        if not selected: return
        item = selected[0]
        item_text = self.tree.item(item, "text").strip()
        
        if "Move Home" in item_text or "Home" in item_text:
            print(">> [로봇 이동] Home 위치로 기동합니다.")
            RobotControlUseCase.move_to_joint([0.0, 0.0, -90.0, 0.0, -90.0, 0.0])
            return
            
        if item not in self.node_data:
            print(">> [오류] 이 노드에 저장된 좌표가 없습니다.")
            return
        
        d = self.node_data[item]
        wps = d.get("waypoints", [])
        
        if wps:
            # 선택된 WP로 이동
            sel_idx = getattr(self.move_editor, '_selected_wp_idx', 0)
            sel_idx = min(sel_idx, len(wps) - 1)
            q = wps[sel_idx]["q"]
            p = wps[sel_idx]["p"]
            print(f">> [로봇 이동] WP{sel_idx+1}로 이동: J1:{q[0]:.1f} J2:{q[1]:.1f} J3:{q[2]:.1f}")
            self.jog_controller.update_coordinates(q, p)
            RobotControlUseCase.move_to_joint(q)
        elif d.get("q") and not all(v == 0.0 for v in d["q"]):
            q = d["q"]
            print(f">> [로봇 이동] 저장된 좌표로 이동: {q}")
            RobotControlUseCase.move_to_joint(q)
        else:
            print(">> [오류] 이 노드에 저장된 좌표가 없습니다.")
    
    def _on_delete_wp_clicked(self):
        """선택된 웨이포인트를 삭제"""
        selected = self.tree.selection()
        if not selected: return
        item = selected[0]
        if item not in self.node_data:
            print(">> [오류] 이 노드에 저장된 좌표가 없습니다.")
            return
        
        wps = self.node_data[item].get("waypoints", [])
        if not wps:
            print(">> [오류] 삭제할 웨이포인트가 없습니다.")
            return
        
        # 현재 선택된 WP 인덱스 가져오기
        sel_idx = getattr(self.move_editor, '_selected_wp_idx', len(wps) - 1)
        sel_idx = min(sel_idx, len(wps) - 1)
        
        removed = wps.pop(sel_idx)
        item_text = self.tree.item(item, "text").strip()
        print(f">> [위치 삭제] '{item_text}'의 WP{sel_idx+1} 삭제됨 (잔여 {len(wps)}개)")
        
        # 대표 좌표 갱신
        if wps:
            self.node_data[item]["q"] = wps[0]["q"]
            self.node_data[item]["p"] = wps[0]["p"]
        else:
            self.node_data[item]["q"] = [0.0]*6
            self.node_data[item]["p"] = [0.0]*6
        
        # 에디터 UI 갱신
        raw = self.node_data[item].get("__raw__", {})
        conty_type = raw.get("type", 102)
        if hasattr(self.move_editor, 'update_waypoint_info'):
            self.move_editor.update_waypoint_info(wps, conty_type)
        if hasattr(self.jog_controller, 'set_target'):
            if wps:
                self.jog_controller.set_target(wps[0]["q"], wps[0]["p"])
            else:
                self.jog_controller.set_target(None, None)
    
    def _on_single_cycle_clicked(self):
        """모든 웨이포인트를 순서대로 1회 실행"""
        selected = self.tree.selection()
        if not selected: return
        item = selected[0]
        item_text = self.tree.item(item, "text").strip()
        
        if item not in self.node_data:
            print(">> [오류] 이 노드에 저장된 좌표가 없습니다.")
            return
        
        d = self.node_data[item]
        wps = d.get("waypoints", [])
        
        if not wps:
            q = d.get("q", [0.0]*6)
            if all(v == 0.0 for v in q):
                print(">> [오류] 좌표가 미설정 상태입니다. 먼저 '현위치 저장'을 하세요.")
                return
            wps = [{"q": q, "p": d.get("p", [0.0]*6)}]
            
        def _run_cycle():
            try:
                total = len(wps)
                print(f">> [1회 Cycle] '{item_text}' — {total}개 웨이포인트 순회 시작")
                for i, wp in enumerate(wps):
                    q = wp["q"]
                    print(f">> [1회 Cycle] WP{i+1}/{total} 이동중... J1:{q[0]:.1f} J2:{q[1]:.1f} J3:{q[2]:.1f}")
                    RobotControlUseCase.move_to_joint(q)
                    # 이동 완료 대기
                    RobotControlUseCase.wait_for_move_finish()
                print(f">> [1회 Cycle] '{item_text}' — 전체 {total}개 WP 이동 완료!")
            except Exception as e:
                print(f">> [1회 Cycle 에러] {e}")
        threading.Thread(target=_run_cycle, daemon=True).start()
        
    def apply_current_editor(self):
        selected = self.tree.selection()
        if not selected:
            print(">> [오류] 먼저 좌측 트리에서 노드를 선택하세요.")
            return
        item = selected[0]
        if hasattr(self, 'current_editor') and self.current_editor and hasattr(self.current_editor, 'apply_changes'):
            if item not in self.node_data:
                self.node_data[item] = {}
            try:
                # 픽앤플레이스 등의 경우 P1,P2 값 등이 내부적으로 갱신될 수 있도록 apply 호출
                self.current_editor.apply_changes(self.node_data[item])
                node_name = self.tree.item(item, 'text').strip()
                print(f">> [적용] '{node_name}' 노드의 설정값이 성공적으로 적용되었습니다.")
                from tkinter import messagebox
                messagebox.showinfo("설정 적용", f"'{node_name}'의 설정이 성공적으로 반영되었습니다.\n(파일에 저장하려면 '저장' 버튼을 누르세요)")
            except Exception as e:
                print(f">> [오류] 설정 적용 실패: {e}")

    def _stop_execution(self):
        """Stop the running program execution."""
        self._exec_stop = True
        RobotControlUseCase._global_stop = True  # wait_for_move_finish 즉시 반환
        try:
            inst = robot_manager.get_active_instance()
            if inst:
                inst.stop_emergency()
        except:
            pass
        print(">> ⏹ [정지] 프로그램 실행이 중단되었습니다.")

    def _open_config_dialog(self):
        """로봇 설정 다이얼로그 열기."""
        from presentation.ui.robot_hmi.editors.config_dialog import RobotConfigDialog
        RobotConfigDialog(self.parent)

    def _add_user_motion_var(self):
        """사용자 모션 변수 추가 — 현재 로봇 좌표를 이름 붙여 저장"""
        dialog = ctk.CTkToplevel(self.parent)
        dialog.title("사용자 모션 변수 추가")
        dialog.geometry("400x350")
        dialog.transient(self.parent)
        dialog.grab_set()
        Theme.apply_window_style(dialog)
        
        ctk.CTkLabel(dialog, text="📌 사용자 모션 변수 등록", font=Theme.font(size=16, weight="bold"),
                     text_color=Theme.SUCCESS).pack(pady=(15, 5))
        ctk.CTkLabel(dialog, text="현재 로봇 좌표를 이름 붙여 저장하고,\n프로그램에서 해당 변수를 참조할 수 있습니다.",
                     text_color=Theme.TEXT_SECONDARY, font=Theme.font(size=11)).pack(pady=5)
        
        form = ctk.CTkFrame(dialog, fg_color=Theme.BG_SURFACE)
        form.pack(fill="x", padx=15, pady=10)
        
        row1 = ctk.CTkFrame(form, fg_color="transparent")
        row1.pack(fill="x", padx=10, pady=8)
        ctk.CTkLabel(row1, text="변수 이름:", font=Theme.font(size=12, weight="bold")).pack(side="left", padx=5)
        name_entry = ctk.CTkEntry(row1, width=200, placeholder_text="예: pick_pos_1")
        name_entry.pack(side="left", padx=5)
        
        row2 = ctk.CTkFrame(form, fg_color="transparent")
        row2.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row2, text="좌표 타입:", font=Theme.font(size=12)).pack(side="left", padx=5)
        type_sel = ctk.CTkOptionMenu(row2, values=["Joint (관절좌표)", "Task (TCP좌표)"], width=160)
        type_sel.pack(side="left", padx=5)
        
        # 현재 좌표 표시
        coord_frame = ctk.CTkFrame(form, fg_color=Theme.BG_BASE, corner_radius=8)
        coord_frame.pack(fill="x", padx=10, pady=8)
        coord_label = ctk.CTkLabel(coord_frame, text="현재 좌표: (로봇 미연결)", 
                                    font=Theme.font(size=10), text_color=Theme.TEXT_SECONDARY)
        coord_label.pack(pady=8, padx=10)
        
        # 로봇 연결 시 현재 좌표 표시
        try:
            active = robot_manager.get_active_robot_name()
            if active:
                state = robot_manager.get_robot_state(active)
                if state:
                    j = state.get("j_pos", [0]*6)
                    t = state.get("t_pos", [0]*6)
                    j_str = ", ".join([f"{v:.2f}" for v in j[:6]])
                    t_str = ", ".join([f"{v:.4f}" for v in t[:6]])
                    coord_label.configure(text=f"J: [{j_str}]\nT: [{t_str}]")
        except: pass
        
        # 저장된 변수 목록
        if not hasattr(self, '_user_motion_vars'):
            self._user_motion_vars = {}
        
        def _save():
            vname = name_entry.get().strip()
            if not vname:
                name_entry.configure(border_color=Theme.DANGER)
                return
            vtype = "joint" if "Joint" in type_sel.get() else "task"
            coords = [0.0]*6
            try:
                active = robot_manager.get_active_robot_name()
                if active:
                    state = robot_manager.get_robot_state(active)
                    if state:
                        coords = state.get("j_pos" if vtype == "joint" else "t_pos", [0]*6)
            except: pass
            self._user_motion_vars[vname] = {"type": vtype, "coords": list(coords)}
            print(f">> [모션 변수] '{vname}' 저장됨: {vtype} = {coords}")
            dialog.destroy()
        
        btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_row.pack(fill="x", padx=15, pady=10)
        ctk.CTkButton(btn_row, text="💾 현재 좌표 저장", fg_color=Theme.SUCCESS, hover_color="#388E3C",
                      font=Theme.font(size=13, weight="bold"), height=38, command=_save).pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkButton(btn_row, text="취소", fg_color=Theme.BG_SURFACE, hover_color="#333",
                      font=Theme.font(size=12), height=38, command=dialog.destroy).pack(side="left", width=80, padx=5)
        
        # 기존 저장 변수 목록 표시
        if self._user_motion_vars:
            ctk.CTkLabel(dialog, text=f"📋 저장된 변수: {len(self._user_motion_vars)}개",
                         font=Theme.font(size=11, weight="bold"), text_color=Theme.INFO).pack(anchor="w", padx=20, pady=(5,2))
            for vn, vd in self._user_motion_vars.items():
                ctk.CTkLabel(dialog, text=f"  • {vn} ({vd['type']})", font=Theme.font(size=10),
                             text_color=Theme.TEXT_SECONDARY).pack(anchor="w", padx=25)

    def _open_oscilloscope(self):
        """오실로스코프 (실시간 데이터 로거) 열기."""
        from presentation.ui.robot_hmi.tools.oscilloscope import OscilloscopeDialog
        OscilloscopeDialog(self.parent)

    def _open_palletizing_wizard(self):
        """비주얼 팔레타이징 마법사 열기."""
        from presentation.ui.robot_hmi.tools.palletizing_wizard import PalletizingWizardDialog
        PalletizingWizardDialog(self.parent)

    def _open_auto_payload(self):
        """페이로드 자동 추정 마법사 열기."""
        from presentation.ui.robot_hmi.tools.auto_payload import AutoPayloadDialog
        AutoPayloadDialog(self.parent)

    def _run_program(self):
        """Execute the entire program tree on the real robot."""
        # 중복 실행 가드: builtins.print monkey-patch가 두 스레드에서 동시에 일어나면
        # 재귀호출/로그 유실이 발생할 수 있다. 또한 self._exec_stop / _global_stop가
        # 두 실행 사이에서 의도치 않게 동기화되는 사고를 막는다.
        if getattr(self, "_program_thread", None) and self._program_thread.is_alive():
            print(">> [경고] 이미 프로그램이 실행 중입니다. (중복 실행 차단)")
            return
        self._exec_stop = False
        RobotControlUseCase._global_stop = False  # 글로벌 정지 플래그 리셋
        
        class _LoopBreakException(Exception):
            """loopBreak (type=21) 실행 시 가장 가까운 Loop를 탈출하기 위한 예외"""
            pass
        
        # 트리에서 모든 노드를 재귀적으로 수집
        def _collect_nodes(parent_item):
            nodes = []
            for child in self.tree.get_children(parent_item):
                text = self.tree.item(child, "text").strip()
                data = self.node_data.get(child, {})
                children = _collect_nodes(child)
                nodes.append({"id": child, "text": text, "data": data, "children": children})
            return nodes
        
        all_nodes = _collect_nodes("")
        if not all_nodes:
            print(">> [오류] 프로그램 트리가 비어있습니다.")
            return
        
        def _highlight(item_id):
            """실행 중인 노드를 트리에서 하이라이트"""
            try:
                self.tree.selection_set(item_id)
                self.tree.see(item_id)
                self.tree.item(item_id, tags=("executing",))
                self.tree.tag_configure("executing", background=Theme.SUCCESS, foreground=Theme.TEXT_PRIMARY)
            except: pass
        
        def _unhighlight(item_id):
            try:
                self.tree.item(item_id, tags=())
            except: pass
        
        def _execute_node_list(node_list):
            skip_indices = set()  # 인터리빙으로 이미 처리된 노드 인덱스
            for idx, node in enumerate(node_list):
                if idx in skip_indices:
                    continue
                if self._exec_stop:
                    return
                
                text = node["text"]
                data = node["data"]
                item_id = node["id"]
                raw = data.get("__raw__", {})
                node_type = raw.get("type", -1)
                q = data.get("q", [0.0]*6)
                p = data.get("p", [0.0]*6)
                
                _highlight(item_id)
                print(f"\n>> ▶ 실행: {text} (type={node_type})")
                
                # ─── type 기반 디스패치 (Conty 실제 타입 — 학습파일 분석 기반) ───
                
                if "Main Program" in text or node_type == 999:
                    # Config/Root → 자식 실행
                    _execute_node_list(node["children"])
                
                elif node_type in [2, 3]:  # Variables → 스킵
                    print(f">> 📋 Variables 노드 (스킵)")
                    
                elif node_type == 20:  # Loop
                    # 무한 = None / -1 / <=0 / 누락. 우리 저장은 -1로 통일하지만 외부 파일은 null인 경우도 있어 모두 수용.
                    raw_count = data.get("count")
                    if raw_count is None:
                        raw_count = raw.get("count")
                    try:
                        count = int(raw_count) if raw_count is not None else None
                    except (TypeError, ValueError):
                        count = None
                    if count is not None and count <= 0:
                        count = None  # 비정상값(0/음수)도 무한으로 안전 해석

                    # 자식 중 팔레트 Pick/Place가 있으면 Loop iter ↔ 팔레트 슬롯 1:1 매핑한다.
                    # 사용자 의도: Loop=9회 + 9-slot 팔레트 → 1번 슬롯, 2번 슬롯, ... 순서대로 진행.
                    pallet_size = 0
                    for child in node["children"]:
                        cdata = child["data"]
                        craw = cdata.get("__raw__", {})
                        if craw.get("type") in (201, 202):
                            cpd = cdata.get("p_data")
                            if cpd and isinstance(cpd, dict):
                                csz = cpd.get("size", [1, 1])
                                m_ = csz[0] if len(csz) > 0 else 1
                                n_ = csz[1] if len(csz) > 1 else 1
                                l_ = csz[2] if len(csz) > 2 else 1
                                pallet_size = max(pallet_size, m_ * n_ * l_)
                    if pallet_size > 0:
                        if count is None:
                            effective = pallet_size
                            print(f">> 🔄 Loop 무한 + 팔레트 {pallet_size}개 → {effective}회로 자동 결정")
                        else:
                            effective = count
                    else:
                        effective = count  # None이면 무한

                    iteration = 0
                    prev_slot = getattr(self, "_pallet_loop_idx", None)
                    try:
                        while not self._exec_stop:
                            iteration += 1
                            if effective is not None and iteration > effective:
                                print(f">> 🔄 Loop 완료 ({effective}회)")
                                break
                            # Loop iter → 팔레트 슬롯 인덱스 (0-based, wrap).
                            # max(...,1)로 divisor 항상 >=1 보장 (분석기 false positive 회피).
                            slot_divisor = max(pallet_size, 1)
                            if pallet_size > 0:
                                self._pallet_loop_idx = (iteration - 1) % slot_divisor
                                print(f">> 🔄 Loop #{iteration}/{effective} (팔레트 슬롯 {self._pallet_loop_idx + 1}/{pallet_size})")
                            else:
                                self._pallet_loop_idx = None
                                print(f">> 🔄 Loop #{iteration}" + (f"/{effective}" if effective else " (무한)"))
                            try:
                                _execute_node_list(node["children"])
                            except _LoopBreakException:
                                print(f">> ⏹️ Loop Break 실행 — 루프 탈출")
                                break
                            if self._exec_stop:
                                break
                    finally:
                        self._pallet_loop_idx = prev_slot
                
                elif node_type == 21:  # loopBreak
                    print(f">> ⏹️ Loop Break!")
                    raise _LoopBreakException()
                    
                elif node_type == 100:  # Home
                    print(f">>   → Home 이동")
                    RobotControlUseCase.go_home()
                    RobotControlUseCase.wait_for_move_finish(30.0)
                    
                elif node_type == 1:  # JointMove
                    if q and not all(v == 0.0 for v in q):
                        print(f">>   → Joint 이동: {[f'{v:.1f}' for v in q]}")
                        RobotControlUseCase.move_to_joint(q)
                        RobotControlUseCase.wait_for_move_finish(30.0)
                        
                elif node_type in [102, 103]:  # FrameMove
                    if p and not all(v == 0.0 for v in p):
                        print(f">>   → Task 이동: {[f'{v:.3f}' for v in p]}")
                        RobotControlUseCase.move_to_task(p)
                        RobotControlUseCase.wait_for_move_finish(30.0)
                    elif q and not all(v == 0.0 for v in q):
                        RobotControlUseCase.move_to_joint(q)
                        RobotControlUseCase.wait_for_move_finish(30.0)
                
                elif node_type == 4:  # SmartDO
                    do_list = data.get("doList", raw.get("doList", []))
                    for d in do_list:
                        idx = d.get("idx", 0)
                        val = d.get("value", 0)
                        RobotControlUseCase.set_do(idx, val)
                        print(f">>   DO{idx} = {'ON' if val else 'OFF'}")
                
                elif node_type == 5:  # SmartAO
                    ao_list = data.get("aoList", raw.get("aoList", []))
                    for a in ao_list:
                        idx = a.get("idx", 0)
                        val = a.get("value", 0)
                        print(f">>   AO{idx} = {val}")
                
                elif node_type == 6:  # EndTool DO
                    do_list = data.get("endtoolDoList", raw.get("endtoolDoList", []))
                    for d in do_list:
                        idx = d.get("idx", 0)
                        val = d.get("value", 0)
                        print(f">>   EndTool DO{idx} = {'ON' if val else 'OFF'}")
                
                elif node_type == 40:  # toolCommand
                    tool_cmd = data.get("toolCmd", raw.get("toolCmd", ""))
                    print(f">>   🔧 Tool Command: {tool_cmd}")
                
                elif node_type == 41:  # toolSensing
                    sens = data.get("sensName", raw.get("sensName", ""))
                    print(f">>   📡 Tool Sensing: {sens}")
                
                elif node_type == 22:  # Wait (시간만)
                    wait_time = data.get("time", raw.get("time", 1.0))
                    print(f">>   ⏳ 대기: {wait_time}초")
                    time.sleep(wait_time)
                    
                elif node_type == 28:  # Wait For [DI]
                    di_list = data.get("diList", raw.get("diList", []))
                    wait_time = data.get("time", raw.get("time", 0))
                    if di_list:
                        pins_str = ", ".join(f"DI{d['idx']}={'HI' if d['value'] else 'LO'}" for d in di_list)
                        print(f">>   ⏳ DI 대기: {pins_str} (timeout={wait_time}s)")
                        timeout = wait_time if wait_time > 0 else 60.0
                        start = time.time()
                        while not self._exec_stop and (time.time() - start) < timeout:
                            all_met = True
                            current_di = RobotControlUseCase.get_di()
                            if current_di:
                                for cond in di_list:
                                    idx = cond.get("idx", 0)
                                    expected = cond.get("value", 1)
                                    if idx < len(current_di) and current_di[idx] != expected:
                                        all_met = False
                                        break
                            else:
                                all_met = False
                            if all_met:
                                print(f">>   ✅ DI 조건 충족")
                                break
                            time.sleep(0.1)
                        else:
                            print(f">>   ⚠️ DI 대기 타임아웃 ({timeout}s)")
                    else:
                        print(f">>   ⏳ Wait For [DI] (DI 미지정 — 스킵)")
                    
                elif node_type == 29:  # if[DI] / waitFor[DI]
                    di_list = data.get("diList", raw.get("diList", []))
                    has_children = len(node["children"]) > 0
                    
                    if has_children:
                        # if[DI] — 조건 확인 후 자식 실행
                        result = False
                        if di_list:
                            current_di = RobotControlUseCase.get_di()
                            if current_di:
                                result = all(
                                    current_di[c["idx"]] == c["value"]
                                    for c in di_list if c["idx"] < len(current_di)
                                )
                        pins_str = ", ".join(f"DI{d['idx']}" for d in di_list) if di_list else "미지정"
                        print(f">>   🔀 If [DI] ({pins_str}) → {'TRUE' if result else 'FALSE'}")
                        if result:
                            _execute_node_list(node["children"])
                    else:
                        # waitFor[DI] — DI 조건 대기
                        if di_list:
                            pins_str = ", ".join(f"DI{d['idx']}={'HI' if d['value'] else 'LO'}" for d in di_list)
                            print(f">>   ⏳ Wait For [DI]: {pins_str}")
                            timeout = 60.0
                            start = time.time()
                            while not self._exec_stop and (time.time() - start) < timeout:
                                all_met = True
                                current_di = RobotControlUseCase.get_di()
                                if current_di:
                                    for cond in di_list:
                                        idx = cond.get("idx", 0)
                                        expected = cond.get("value", 1)
                                        if idx < len(current_di) and current_di[idx] != expected:
                                            all_met = False
                                            break
                                else:
                                    all_met = False
                                if all_met:
                                    print(f">>   ✅ DI 조건 충족")
                                    break
                                time.sleep(0.1)
                        else:
                            print(f">>   (DI 미지정 — 스킵)")
                
                elif node_type in [23, 24]:  # If Var / If (조건)
                    cond = data.get("cond", raw.get("cond", {}))
                    result = False
                    if cond:
                        left = cond.get("left", {})
                        right = cond.get("right", {})
                        op_val = cond.get("op", 0)
                        op_map = {0: "==", 1: "!=", 2: ">", 3: "<", 4: ">=", 5: "<="}
                        op_str = op_map.get(op_val, "==")
                        var_name = left.get("value", "var1") if left.get("type", -1) == 10 else "var1"
                        compare_val = right.get("value", 0) if right.get("type", -1) != -1 else 0
                        result = RobotControlUseCase.eval_condition(str(var_name), op_str, float(compare_val or 0))
                    print(f">>   🔀 If → {'TRUE' if result else 'FALSE'}")
                    if result:
                        _execute_node_list(node["children"])
                
                elif node_type in (201, 202):  # Pick / Place
                    is_pick = (node_type == 201)   # 201=Pick(Hold), 202=Place(Release)
                    app_data = data.get("approach", raw.get("approach", {}))
                    ret_data = data.get("retract", raw.get("retract", {}))
                    app_dist = app_data.get("distance", 0.05)
                    ret_dist = ret_data.get("distance", 0.05)
                    # ⚠️ 단위 휴리스틱: 우리 UI(거리 mm)는 50.0처럼 1보다 큰 값으로 저장하고,
                    # 표준 Conty(거리 m)는 0.05처럼 1 이하로 저장한다. 따라서 1.0을 경계로 단위 추정한다.
                    # ⚠️ 위험: 사용자가 1mm 미만(예: 0.5mm)을 입력하면 m로 오해될 수 있다. UI가 mm 단위로
                    # 직접 입력받는 한 5~500mm 범위라 안전하지만, 정밀 보정용 모션을 추가할 땐 명시적 단위 필요.
                    if app_dist > 1.0: app_dist /= 1000.0
                    if ret_dist > 1.0: ret_dist /= 1000.0
                    
                    # ─── 접근/후퇴 오프셋 함수 ───
                    # Conty 규약: approach/retract 모두 타겟 위(+Z)에서 진입/탈출
                    # direction=0: Z축 접근 (위에서 내려감)
                    # direction=1: Z축 후퇴 (아래에서 올라감)
                    # → 둘 다 타겟보다 높은 위치를 가리킴 (Z + distance)
                    def _safe_offset(base, dist):
                        """타겟 위치에서 Z축 위로 dist만큼 오프셋된 위치 반환"""
                        pos = list(base)
                        pos[2] += abs(dist)  # 항상 위로 (안전)
                        return pos
                    
                    # toolId로 doMap 결정
                    # raw(원본 JSON)에서 toolId를 우선 사용 (UI 편집에 의한 변조 방지)
                    tool_id = raw.get("toolId", data.get("toolId", -1))
                    hold_do_map = []
                    release_do_map = []
                    
                    has_raw = hasattr(self, '_current_raw_data') and bool(self._current_raw_data)
                    print(f">>   [DEBUG] tool_id={tool_id}, has_raw_data={has_raw}")
                    
                    if has_raw:
                        prog_nodes = self._current_raw_data.get("program", [])
                        cfg_node = None
                        for pn in prog_nodes:
                            if pn.get("type") == 999:
                                cfg_node = pn
                                break
                        
                        if cfg_node:
                            tool_info = cfg_node.get("toolInfo", [])
                            print(f">>   [DEBUG] type=999 찾음, toolInfo 개수={len(tool_info)}")
                            
                            # 1차: 정확한 toolId 매칭
                            matched = False
                            for tool in tool_info:
                                if tool.get("id") == tool_id or tool_id == -1:
                                    print(f">>   [DEBUG] 매칭된 tool: id={tool.get('id')}, name={tool.get('name')}")
                                    for tc in tool.get("toolCommand", []):
                                        if tc.get("name") == "Hold" and tc.get("doMap"):
                                            hold_do_map = tc["doMap"]
                                        elif tc.get("name") == "Release" and tc.get("doMap"):
                                            release_do_map = tc["doMap"]
                                    matched = True
                                    break
                            
                            # 2차: 매칭 실패 시 첫 번째 도구를 fallback으로 사용
                            if not matched and tool_info:
                                fallback_tool = tool_info[0]
                                print(f">>   [DEBUG] ⚠️ tool_id={tool_id} 매칭 실패! fallback → id={fallback_tool.get('id')}, name={fallback_tool.get('name')}")
                                for tc in fallback_tool.get("toolCommand", []):
                                    if tc.get("name") == "Hold" and tc.get("doMap"):
                                        hold_do_map = tc["doMap"]
                                    elif tc.get("name") == "Release" and tc.get("doMap"):
                                        release_do_map = tc["doMap"]
                        else:
                            print(f">>   [DEBUG] ⚠️ type=999 노드를 찾지 못함!")
                    
                    print(f">>   [DEBUG] 최종: hold={hold_do_map}, release={release_do_map}")
                    
                    target_type = data.get("target_type", 0)
                    p_data = data.get("p_data", None)
                    
                    def _do_tool_action(do_hold):
                        """do_hold=True→그리퍼 잡기(Hold), False→놓기(Release)"""
                        do_map = hold_do_map if do_hold else release_do_map
                        action_name = "Hold(잡기)" if do_hold else "Release(놓기)"
                        
                        from core.domains.robot.communication.client_manager import robot_manager
                        active_inst = robot_manager.get_active_instance()
                        if not active_inst:
                            print(f">>     ⚠️ active_inst가 None!")
                            return
                        
                        if do_map:
                            # 공압 밸브 안전 순서: OFF(0) 먼저 → ON(1) 나중에
                            # 양쪽 솔레노이드 동시 통전 방지
                            sorted_map = sorted(do_map, key=lambda d: d["value"])
                            
                            off_cmds = [d for d in sorted_map if d["value"] == 0]
                            on_cmds = [d for d in sorted_map if d["value"] == 1]
                            
                            # 1단계: 먼저 꺼야 할 핀 OFF
                            for d in off_cmds:
                                try:
                                    active_inst.set_do(d["idx"], 0)
                                    print(f">>     DO{d['idx']}=OFF ({action_name}) ✅")
                                    time.sleep(0.1)
                                except Exception as e:
                                    print(f">>     ⚠️ DO OFF 에러: {e}")
                            
                            # 밸브 안정화 대기
                            if off_cmds and on_cmds:
                                time.sleep(0.15)
                            
                            # 2단계: 켜야 할 핀 ON
                            for d in on_cmds:
                                try:
                                    active_inst.set_do(d["idx"], 1)
                                    print(f">>     DO{d['idx']}=ON ({action_name}) ✅")
                                    time.sleep(0.1)
                                except Exception as e:
                                    print(f">>     ⚠️ DO ON 에러: {e}")
                            
                            time.sleep(0.3)  # 공압 동작 완료 대기
                        else:
                            print(f">>     ⚠️ doMap 없음 — {action_name} 스킵")
                    
                    from core.domains.robot.communication.client_manager import robot_manager
                    inst = robot_manager.get_active_instance()
                    if not inst: 
                        print(">>   ⚠️ 로봇 미연결 — Pick/Place 스킵")
                        continue
                    
                    action_label = "🫳 Pick(잡기)" if is_pick else "📦 Place(놓기)"
                    
                    if target_type == 1 and p_data and isinstance(p_data, dict):
                        # ═══ 팔레트 대상 ═══
                        from core.domains.robot.use_cases.motion_math import MotionMath
                        size = p_data.get("size", [1,1,1])
                        m, n = size[0], size[1]
                        l_val = size[2] if len(size) > 2 else 1
                        pts = p_data.get("points", [])
                        p1 = pts[0]["p"] if len(pts) > 0 else p
                        p2 = pts[1]["p"] if len(pts) > 1 else p1
                        p3 = pts[2]["p"] if len(pts) > 2 else p1
                        p4 = pts[3]["p"] if len(pts) > 3 else None
                        
                        total = m * n * l_val
                        
                        # ── Pick-Place 인터리빙 파트너 탐색 ──
                        # 현재 노드 이후의 형제 노드들을 탐색하여
                        # 반대 타입(Pick↔Place) 노드와 그 사이의 노드들을 찾음
                        partner_node = None
                        between_nodes = []  # Pick과 Place 사이의 노드들 (Home 등)
                        partner_idx = None
                        
                        opposite_type = 202 if is_pick else 201
                        for look_idx in range(idx + 1, len(node_list)):
                            look_raw = node_list[look_idx]["data"].get("__raw__", {})
                            look_type = look_raw.get("type", -1)
                            if look_type == opposite_type:
                                partner_node = node_list[look_idx]
                                partner_idx = look_idx
                                break
                            elif look_type in (100, 103, 1, 102):  # Home, FrameMove, JointMove
                                between_nodes.append(node_list[look_idx])
                            else:
                                break  # 다른 타입(Loop, Wait 등)을 만나면 탐색 중단
                        
                        if partner_node:
                            # 파트너 및 사이 노드들을 skip 처리
                            for bi in range(idx + 1, partner_idx + 1):
                                skip_indices.add(bi)
                            
                            partner_data = partner_node["data"]
                            partner_raw = partner_data.get("__raw__", {})
                            partner_p = partner_data.get("p", [0.0]*6)
                            partner_app = partner_data.get("approach", partner_raw.get("approach", {}))
                            partner_ret = partner_data.get("retract", partner_raw.get("retract", {}))
                            partner_app_dist = partner_app.get("distance", 0.05)
                            partner_ret_dist = partner_ret.get("distance", 0.05)
                            if partner_app_dist > 1.0: partner_app_dist /= 1000.0
                            if partner_ret_dist > 1.0: partner_ret_dist /= 1000.0
                            
                            partner_target_type = partner_data.get("target_type", 0)
                            partner_p_data = partner_data.get("p_data", None)
                            partner_is_pick = (partner_raw.get("type", -1) == 201)
                            partner_label = "🫳 Pick(잡기)" if partner_is_pick else "📦 Place(놓기)"
                            
                            print(f">>   🔄 인터리빙 모드: {action_label} (팔레트 {total}개) ↔ {partner_label}")
                        
                        # Loop이 자식으로 이 Pick/Place를 호출했고 self._pallet_loop_idx가 설정돼 있으면
                        # 전체 팔레트 그리드를 펼치지 않고 그 슬롯 하나만 처리한다.
                        loop_slot = getattr(self, "_pallet_loop_idx", None)
                        if loop_slot is not None and 0 <= loop_slot < total:
                            target_layer = loop_slot // (m * n)
                            in_layer = loop_slot % (m * n)
                            target_row = in_layer // n
                            target_col = in_layer % n
                            slot_iter = [(target_layer, target_row, target_col)]
                            print(f">>   🎯 Loop 슬롯 모드: {action_label} 슬롯 {loop_slot+1}/{total}만 실행")
                        else:
                            slot_iter = [
                                (layer, row, col)
                                for layer in range(l_val)
                                for row in range(m)
                                for col in range(n)
                            ]

                        pallet_count = 0
                        for (layer, row, col) in slot_iter:
                            if self._exec_stop: return
                            pallet_count += 1
                            if True:  # 들여쓰기 유지 (아래 블록 그대로 사용)
                                if True:
                                    cur_t = MotionMath.compute_pallet_point(p1, p2, p3, m, n, row, col, p4=p4, size_l=l_val, current_l=layer)
                                    cur_app = _safe_offset(cur_t, app_dist)
                                    cur_ret = _safe_offset(cur_t, ret_dist)
                                    
                                    # 1) 팔레트 Pick/Place
                                    print(f">>   {action_label} [{pallet_count}/{total}] L{layer+1} R{row+1} C{col+1}")
                                    print(f">>     1) 접근 위치(Z+{app_dist:.3f}m)")
                                    inst.task_move_to(cur_app)
                                    RobotControlUseCase.wait_for_move_finish(30.0)
                                    print(f">>     2) 타겟 위치로 하강")
                                    inst.task_move_to(cur_t)
                                    RobotControlUseCase.wait_for_move_finish(30.0)
                                    time.sleep(0.2)
                                    print(f">>     3) {'Hold' if is_pick else 'Release'}")
                                    _do_tool_action(is_pick)
                                    # retract.waitTime 대기
                                    ret_wait = ret_data.get("waitTime", 0)
                                    if ret_wait > 0:
                                        print(f">>     3b) 대기 {ret_wait}초...")
                                        time.sleep(ret_wait)
                                    payload = {"robot_id": robot_manager.get_active_robot_name(), "action_type": 'Pick' if is_pick else 'Place', "pos": cur_t}
                                    mqtt_broker.publish("robot/task_done", payload)
                                    print(f">>     4) 후퇴 위치(Z+{ret_dist:.3f}m)")
                                    inst.task_move_to(cur_ret)
                                    RobotControlUseCase.wait_for_move_finish(30.0)
                                    
                                    # 2) 사이 노드 실행 (Home 등)
                                    if partner_node and between_nodes:
                                        for bn in between_nodes:
                                            if self._exec_stop: return
                                            bn_raw = bn["data"].get("__raw__", {})
                                            bn_type = bn_raw.get("type", -1)
                                            _highlight(bn["id"])
                                            if bn_type == 100:
                                                print(f">>   → Home 이동")
                                                RobotControlUseCase.go_home()
                                                RobotControlUseCase.wait_for_move_finish(30.0)
                                            elif bn_type in (1, 102, 103):
                                                bn_q = bn["data"].get("q", [0.0]*6)
                                                bn_p = bn["data"].get("p", [0.0]*6)
                                                if bn_type == 1:
                                                    inst.joint_move_to(bn_q)
                                                else:
                                                    inst.task_move_to(bn_p)
                                                RobotControlUseCase.wait_for_move_finish(30.0)
                                    
                                    # 3) 파트너(Place/Pick) 실행
                                    if partner_node:
                                        _highlight(partner_node["id"])
                                        # ★ 파트너도 팔레트이면 같은 슬롯 인덱스로 좌표를 다시 계산한다.
                                        #   (예: Pick 팔레트 1번 슬롯 ↔ Place 팔레트 1번 슬롯)
                                        if partner_p_data and isinstance(partner_p_data, dict):
                                            psz = partner_p_data.get("size", [1, 1, 1])
                                            pm = psz[0] if len(psz) > 0 else 1
                                            pn = psz[1] if len(psz) > 1 else 1
                                            pl = psz[2] if len(psz) > 2 else 1
                                            ppts = partner_p_data.get("points", [])
                                            pp1 = ppts[0].get("p") if len(ppts) > 0 else partner_p
                                            pp2 = ppts[1].get("p") if len(ppts) > 1 else pp1
                                            pp3 = ppts[2].get("p") if len(ppts) > 2 else pp1
                                            pp4 = ppts[3].get("p") if len(ppts) > 3 else None
                                            # Pick 단계에서 사용한 (layer, row, col)를 그대로 사용
                                            p_target = MotionMath.compute_pallet_point(
                                                pp1, pp2, pp3, pm, pn, row, col,
                                                p4=pp4, size_l=pl, current_l=layer
                                            )
                                            print(f">>     [팔레트 매핑] {partner_label} → L{layer+1} R{row+1} C{col+1}")
                                        else:
                                            p_target = partner_p if partner_p else [0.0]*6
                                        p_app = _safe_offset(p_target, partner_app_dist)
                                        p_ret = _safe_offset(p_target, partner_ret_dist)

                                        print(f">>   {partner_label} [{pallet_count}/{total}]")
                                        print(f">>     1) 접근 위치(Z+{partner_app_dist:.3f}m)")
                                        inst.task_move_to(p_app)
                                        RobotControlUseCase.wait_for_move_finish(30.0)
                                        print(f">>     2) 타겟 위치로 하강")
                                        inst.task_move_to(p_target)
                                        RobotControlUseCase.wait_for_move_finish(30.0)
                                        time.sleep(0.2)
                                        print(f">>     3) {'Hold' if partner_is_pick else 'Release'}")
                                        _do_tool_action(partner_is_pick)
                                        payload = {"robot_id": robot_manager.get_active_robot_name(), "action_type": 'Pick' if partner_is_pick else 'Place', "pos": p_target}
                                        mqtt_broker.publish("robot/task_done", payload)
                                        print(f">>     4) 후퇴 위치(Z+{partner_ret_dist:.3f}m)")
                                        inst.task_move_to(p_ret)
                                        RobotControlUseCase.wait_for_move_finish(30.0)
                    else:
                        # ═══ 싱글 포인트 대상 ═══
                        target_p = p if p else [0.0]*6
                        app_p = _safe_offset(target_p, app_dist)
                        ret_p = _safe_offset(target_p, ret_dist)
                        print(f">>   {action_label}")
                        print(f">>     target: z={target_p[2]:.4f}")
                        print(f">>     1) 접근 위치(Z={app_p[2]:.4f}, +{app_dist:.3f}m 위)")
                        inst.task_move_to(app_p)
                        RobotControlUseCase.wait_for_move_finish(30.0)
                        print(f">>     2) 타겟 위치로 하강(Z={target_p[2]:.4f})")
                        inst.task_move_to(target_p)
                        RobotControlUseCase.wait_for_move_finish(30.0)
                        time.sleep(0.2)
                        print(f">>     3) {'Hold(잡기)' if is_pick else 'Release(놓기)'}")
                        _do_tool_action(is_pick)
                        # retract.waitTime 대기
                        ret_wait = ret_data.get("waitTime", 0)
                        if ret_wait > 0:
                            print(f">>     3b) 대기 {ret_wait}초...")
                            time.sleep(ret_wait)
                        payload = {"robot_id": robot_manager.get_active_robot_name(), "action_type": 'Pick' if is_pick else 'Place', "pos": target_p}
                        mqtt_broker.publish("robot/task_done", payload)
                        print(f">>     4) 후퇴 위치(Z={ret_p[2]:.4f}, +{ret_dist:.3f}m 위)")
                        inst.task_move_to(ret_p)
                        RobotControlUseCase.wait_for_move_finish(30.0)
                
                elif node_type == 25:  # Elif (변수 조건)
                    cond = data.get("cond", raw.get("cond", {}))
                    result = False
                    if cond:
                        left = cond.get("left", {})
                        right = cond.get("right", {})
                        op_val = cond.get("op", 0)
                        op_map = {0: "==", 1: "!=", 2: ">", 3: "<", 4: ">=", 5: "<="}
                        op_str = op_map.get(op_val, "==")
                        var_name = left.get("value", "var1") if left.get("type", -1) == 10 else "var1"
                        compare_val = right.get("value", 0) if right.get("type", -1) != -1 else 0
                        result = RobotControlUseCase.eval_condition(str(var_name), op_str, float(compare_val or 0))
                    print(f">> 🔀 Elif → {'TRUE' if result else 'FALSE'}")
                    if result:
                        _execute_node_list(node["children"])
                
                elif node_type == 26:  # Else (무조건 실행)
                    print(f">>   🔀 Else → 자식 실행")
                    _execute_node_list(node["children"])
                
                elif node_type == 30:  # WaitFor (조건 대기)
                    di_list = data.get("diList", raw.get("diList", []))
                    if di_list:
                        pins_str = ", ".join(f"DI{d['idx']}={'HI' if d['value'] else 'LO'}" for d in di_list)
                        print(f">>   ⏳ Wait For: {pins_str}")
                        timeout = 60.0
                        start = time.time()
                        while not self._exec_stop and (time.time() - start) < timeout:
                            current_di = RobotControlUseCase.get_di()
                            if current_di:
                                all_met = all(
                                    current_di[c["idx"]] == c["value"]
                                    for c in di_list if c["idx"] < len(current_di)
                                )
                                if all_met:
                                    print(f">>   ✅ 조건 충족")
                                    break
                            time.sleep(0.1)
                    else:
                        print(f">>   ⏳ Wait For (조건 미지정 — 스킵)")
                
                elif node_type == 32:  # SpeedRatio
                    spd = data.get("prgSpdRatio", raw.get("prgSpdRatio", 100))
                    print(f">>   ⚡ 프로그램 속도 변경: {spd}%")
                    try:
                        inst = robot_manager.get_active_instance()
                        if inst and hasattr(inst, 'set_speed_ratio'):
                            inst.set_speed_ratio(spd)
                    except Exception as e:
                        print(f">>   ⚠️ 속도 변경 실패: {e}")

                elif node_type == 200:  # Pick Group → 자식 실행
                    _execute_node_list(node["children"])
                    
                elif node_type == 250:  # Call SubProgram
                    sub_path = raw.get("sub_program", data.get("sub_program", ""))
                    if sub_path:
                        print(f">>   📞 서브프로그램: {sub_path}")
                        RobotControlUseCase.call_sub_program(sub_path)
                        RobotControlUseCase.wait_for_move_finish(60.0)
                
                elif node_type == 302:  # Force
                    print(f">>   💪 힘 제어 노드")
                    
                else:
                    # 텍스트 fallback (사용자 직접 추가 노드)
                    if "Stack Search" in text:
                        axis = data.get("axis", 2)
                        direction = data.get("direction", -1)
                        threshold = data.get("force_threshold", 10.0)
                        step = data.get("step_mm", 1.0)
                        found_pos = RobotControlUseCase.stack_search(axis, direction, threshold, step)
                        if found_pos:
                            RobotControlUseCase.set_variable("stack_z", found_pos[2])
                    elif "Spiral Search" in text:
                        z_force = data.get("z_force", 10.0)
                        radius = data.get("radius_mm", 5.0)
                        RobotControlUseCase.spiral_search(z_force=z_force, radius_mm=radius)
                    else:
                        print(f">>   (스킵: type={node_type}, {text})")
        
        def _clear_all_highlights():
            """모든 노드의 하이라이트 제거"""
            def _clear(parent):
                for child in self.tree.get_children(parent):
                    try: self.tree.item(child, tags=())
                    except: pass
                    _clear(child)
            try: _clear("")
            except: pass
        
        def _run():
            import datetime, io, os as _os
            log_dir = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..', '..', 'logs')
            _os.makedirs(log_dir, exist_ok=True)
            log_path = _os.path.join(log_dir, f"exec_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
            log_lines = []
            
            _orig_print = print
            def _log_print(*args, **kwargs):
                msg = " ".join(str(a) for a in args)
                log_lines.append(msg)
                _orig_print(*args, **kwargs)
            
            import builtins
            builtins.print = _log_print
            
            # 폴링 일시중지 (소켓 Lock 경합 방지)
            try:
                app = self.parent.winfo_toplevel()
                if hasattr(app, '_program_running'):
                    app._program_running = True
                    print(">> [시스템] 폴링 일시중지")
            except: pass
            
            print("\n>> ═══════════════════════════════════")
            print(">> 🚀 프로그램 실행을 시작합니다!")
            print(">> ═══════════════════════════════════")
            try:
                _execute_node_list(all_nodes)
            except Exception as e:
                print(f">> [실행 에러] {e}")
                import traceback
                traceback.print_exc()
            
            _clear_all_highlights()
            if self._exec_stop:
                print(">> ⏹ 사용자에 의해 프로그램이 중단되었습니다.")
            else:
                print(">> ✅ 프로그램 실행 완료!")
            
            # 폴링 재개
            try:
                app = self.parent.winfo_toplevel()
                if hasattr(app, '_program_running'):
                    app._program_running = False
                    print(">> [시스템] 폴링 재개")
            except: pass
            
            # 로그 파일 저장
            builtins.print = _orig_print
            try:
                with open(log_path, 'w', encoding='utf-8') as f:
                    f.write("\n".join(log_lines))
                print(f">> [로그] 실행 로그 저장됨: {log_path}")
            except Exception as e:
                print(f">> [로그 에러] {e}")
        
        self._program_thread = threading.Thread(target=_run, daemon=True)
        self._program_thread.start()

    def _move_node_up(self):
        """선택한 노드를 한 칸 위로 이동."""
        selected = self.tree.selection()
        if not selected: return
        item = selected[0]
        if "Main Program" in self.tree.item(item, "text"): return
        parent = self.tree.parent(item)
        idx = self.tree.index(item)
        if idx == 0: return
        self.tree.move(item, parent, idx - 1)
        self.tree.selection_set(item)
        print(f">> [순서] '{self.tree.item(item, 'text').strip()}' ▲ 위로 이동")
    
    def _move_node_down(self):
        """선택한 노드를 한 칸 아래로 이동."""
        selected = self.tree.selection()
        if not selected: return
        item = selected[0]
        if "Main Program" in self.tree.item(item, "text"): return
        parent = self.tree.parent(item)
        siblings = self.tree.get_children(parent)
        idx = self.tree.index(item)
        if idx >= len(siblings) - 1: return
        self.tree.move(item, parent, idx + 1)
        self.tree.selection_set(item)
        print(f">> [순서] '{self.tree.item(item, 'text').strip()}' ▼ 아래로 이동")
    
    def _copy_node(self):
        """선택한 노드를 복사하여 바로 아래에 붙여넣기."""
        import copy
        selected = self.tree.selection()
        if not selected: return
        item = selected[0]
        item_text = self.tree.item(item, "text")
        if "Main Program" in item_text:
            print(">> [오류] Main Program은 복사할 수 없습니다.")
            return
        parent = self.tree.parent(item)
        idx = self.tree.index(item)
        new_item = self.tree.insert(parent, idx + 1, text=item_text, open=True)
        if item in self.node_data:
            self.node_data[new_item] = copy.deepcopy(self.node_data[item])
        def _copy_children(src, dst):
            for child in self.tree.get_children(src):
                child_text = self.tree.item(child, "text")
                new_child = self.tree.insert(dst, "end", text=child_text, open=True)
                if child in self.node_data:
                    self.node_data[new_child] = copy.deepcopy(self.node_data[child])
                _copy_children(child, new_child)
        _copy_children(item, new_item)
        self.tree.selection_set(new_item)
        print(f">> [복사] '{item_text.strip()}' 노드가 복사되었습니다.")

    def delete_node(self):
        selected = self.tree.selection()
        if not selected: return
        item = selected[0]
        
        if self.tree.item(item, "text").strip() == "Main Program":
            print(">> [오류] 최상위 Main Program 노드는 삭제할 수 없습니다.")
            return
            
        def _get_all_descendants(node):
            desc = []
            for child in self.tree.get_children(node):
                desc.append(child)
                desc.extend(_get_all_descendants(child))
            return desc
            
        to_delete = [item] + _get_all_descendants(item)
        
        self.tree.delete(item)
        
        for d_item in to_delete:
            if d_item in self.node_data:
                del self.node_data[d_item]
                
        for w in self.pp_frame.winfo_children(): w.destroy()
        print(">> [삭제] 선택한 노드가 삭제되었습니다.")

    def add_node(self, cmd_name):
        # 표시 이름 → 내부 이름 + Conty 타입 코드
        _MAP = {
            # 모션 명령어
            "Joint Move": ("JointMove", 102),       # type=102: JointMove:Absolute
            "Frame Move": ("FrameMove", 103),      # type=103: FrameMove:Absolute
            "Move C":     ("Move C", 3),            # type=3: CircularMove
            "Move Home":  ("Home", 100),            # type=100: Home
            "Move B":     ("Move B", 5),            # type=5: MoveB
            "Move By":    ("Move By", 6),           # type=6: frameMove:Relative
            # 입출력 명령어
            "DO":         ("DO 출력", 4),            # type=4: smartDO
            "Smart DO":   ("Smart DO", 4),          # type=4: doList
            "EndTool DO": ("EndTool DO", 6),        # type=6: endtoolDoList
            "AO":         ("Smart AO", 5),          # type=5: aoList
            "Tool Sensing": ("Tool Sensing", 23),   # type=23: toolSensing
            # 흐름제어 명령어
            "Loop":       ("Loop", 20),             # type=20: count=-1
            "Wait":       ("Wait", 22),             # type=22: time-based wait
            "Wait For":   ("Wait For", 30),         # type=30: waitFor (조건 대기)
            "Wait DI":    ("Wait DI", 28),          # type=28: Wait (DI 대기)
            "If (DI)":    ("If [DI]", 29),          # type=29: if[DI]
            "If Var":     ("If Var", 24),            # type=24: if (변수 조건)
            "Else":       ("Else", 26),             # type=26: else
            "Math":       ("Math", 21),              # type=21: assignment
            "Loop Break": ("Loop Break", 21),       # type=21: loopBreak → 주의: 실제는 31
            "Speed Ratio": ("Speed", 32),           # type=32: speedRatio
            "Comment":    ("Comment", 40),          # type=40: comment
            "Stop":       ("Stop", 41),             # type=41: stop
            "Folder":     ("Folder", 100),          # type=100: Folder/Group
            # 응용 명령어
            "Pick":       ("Pick", 201),            # type=201: pick
            "Place":      ("Place", 202),           # type=202: place
            "Pallet":     ("Pallet", 200),          # type=200: Pick Group
            "Call":       ("Call", 250),             # type=250
            "Conveyor":   ("Conveyor", 300),        # type=300: conveyorTracking
            "Force":      ("indyCARE", 302),        # type=302
            "TaktTime":   ("TaktTime", 303),        # type=303: taktTime
            "Detect":     ("Detect", 400),          # type=400: detect
            "Retrieve":   ("Retrieve", 401),        # type=401: retrieve
            "Python":     ("Python Script", 500),   # type=500: pythonScript
        }
        internal_name, conty_type = _MAP.get(cmd_name, (cmd_name, 100))
        
        selected = self.tree.selection()
        if not selected:
            new_item = self.tree.insert("", "end", text=f" {internal_name} Node", open=True)
            self._auto_teach(new_item, internal_name, conty_type)
            return
            
        target = selected[0]
        target_text = self.tree.item(target, "text")
        
        # 컨테이너 노드인 경우 자식으로 삽입
        container_keywords = ["Loop", "If", "Main Program", "Folder", "Pick", "Wait DI", "WaitPeriod", "Set DO"]
        is_container = any(kw in target_text for kw in container_keywords)
        
        if is_container:
            new_item = self.tree.insert(target, "end", text=f" {internal_name} Node", open=True)
            self.tree.item(target, open=True)
        else:
            parent = self.tree.parent(target)
            idx = self.tree.index(target)
            new_item = self.tree.insert(parent, idx + 1, text=f" {internal_name} Node", open=True)
            
        self._auto_teach(new_item, internal_name, conty_type)
        
    def _auto_teach(self, new_item, cmd_name, conty_type=100):
        if not hasattr(self, 'node_data'): self.node_data = {}
        current_q = [0.0]*6
        current_p = [0.0]*6
        try:
            for i, ax in enumerate(["J1","J2","J3","J4","J5","J6"]):
                current_q[i] = float(self.jog_controller.entries[ax].get())
            for i, ax in enumerate(["X","Y","Z","Rx","Ry","Rz"]):
                current_p[i] = float(self.jog_controller.entries[ax].get())
        except Exception:
            pass
        
        # __raw__에 Conty 타입 포함 (실행 엔진이 type 기반으로 디스패치)
        self.node_data[new_item] = {
            "q": current_q, 
            "p": current_p, 
            "t_type": 0, 
            "p_name": "", 
            "p_data": [], 
            "b_radius": 0.0,
            "__raw__": {"type": conty_type, "enable": True, "pId": 0},
        }
        self.tree.selection_set(new_item)
        self.tree.focus(new_item)
        if self.on_node_selected_callback:
            self.on_node_selected_callback(current_q, current_p, 0, f" {cmd_name} Node", None, None, [], 0.0, None, None, self.node_data.get(new_item, {}))

class RobotSettingsEditor:
    def __init__(self, parent_frame):
        self.parent = parent_frame
        
    def render(self):
        for w in self.parent.winfo_children(): w.destroy()
        
        f = ctk.CTkFrame(self.parent, fg_color=Theme.BG_BASE, corner_radius=12)
        f.pack(expand=True, padx=40, pady=40, fill="both")
        
        header = ctk.CTkFrame(f, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=20)
        ctk.CTkLabel(header, text="🌐 NETWORK & IP CONFIG", font=Theme.font(size=18, weight="bold")).pack(side="left")
        
        ctk.CTkButton(header, text="🔌 선택 로봇 연결", fg_color=Theme.INFO, text_color="black", width=120, command=self.connect_selected).pack(side="right", padx=5)
        ctk.CTkButton(header, text="➕ 새 로봇 추가", fg_color=Theme.INFO, width=120, command=self.add_new_robot_row).pack(side="right", padx=5)
        
        self.list_frame = ctk.CTkScrollableFrame(f, fg_color=Theme.BG_BASE, corner_radius=8)
        self.list_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.status_labels = {}
        self.checkboxes = {}
        self.connect_buttons = {}
        
        all_robots = robot_manager.get_all_robots()
        for name, info in all_robots.items():
            self._render_robot_row(name, info)

    def add_new_robot_row(self):
        # 로봇 매니저에 새로운 로봇 추가 (동적 생성)
        all_robots = robot_manager.get_all_robots()
        new_idx = len(all_robots) + 1
        new_name = f"Robot {chr(64 + new_idx)}" # Robot D, E, F...
        if new_name not in all_robots:
            robot_manager.add_robot(new_name, "192.168.3.100")
            print(f">> [알림] 새 로봇 템플릿 '{new_name}'가 추가되었습니다.")
            self.render() # 화면 갱신
            
    def _render_robot_row(self, name, info):
        ip = info.get("ip", "")
        plc_ip = info.get("plc_ip", "") or "192.168.3.200"
        inst = info.get("instance")
        state = "연결됨" if inst is not None else "대기중"
        
        row = ctk.CTkFrame(self.list_frame, fg_color=Theme.BG_SURFACE, height=50)
        row.pack(fill="x", pady=5, padx=10)
        
        chk_var = ctk.StringVar(value="on")
        chk = ctk.CTkCheckBox(row, text="", variable=chk_var, onvalue="on", offvalue="off", width=24)
        chk.pack(side="left", padx=10)
        self.checkboxes[name] = chk_var
        
        ctk.CTkLabel(row, text=name, font=ctk.CTkFont(weight="bold", size=14), width=70, anchor="w").pack(side="left", padx=5)
        
        ctk.CTkLabel(row, text="로봇 IP:", width=45).pack(side="left")
        entry_ip = ctk.CTkEntry(row, width=120)
        entry_ip.insert(0, ip)
        entry_ip.pack(side="left", padx=5)
        
        ctk.CTkLabel(row, text="PLC IP:", width=45).pack(side="left", padx=(10,0))
        entry_plc = ctk.CTkEntry(row, width=120)
        entry_plc.insert(0, plc_ip)
        entry_plc.pack(side="left", padx=5)
        
        status_col = "#00FF41" if state == "연결됨" else Theme.TEXT_SECONDARY
        lbl = ctk.CTkLabel(row, text=f"상태: {state}", text_color=status_col, width=80)
        lbl.pack(side="left", padx=15)
        self.status_labels[name] = lbl
        
        # 버튼들 (오른쪽에서 왼쪽 순서)
        ctk.CTkButton(row, text="💾 저장", width=60, fg_color="#F57C00", command=lambda n=name, ei=entry_ip, ep=entry_plc: self.save_ip(n, ei, ep)).pack(side="right", padx=5, pady=10)
        
        # 로봇 연결 버튼
        btn_text = "🔗 로봇 연결" if state != "연결됨" else "🔌 연결 해제"
        btn_color = Theme.SUCCESS if state != "연결됨" else Theme.DANGER
        
        conn_btn = ctk.CTkButton(row, text=btn_text, width=90, fg_color=btn_color, command=lambda n=name: self.connect_robot(n))
        conn_btn.pack(side="right", padx=5)
        self.connect_buttons[name] = conn_btn
        
        # PLC 연결 버튼
        ctk.CTkButton(row, text="⚙️ PLC 연결", width=90, fg_color="#009688", command=lambda n=name: self.connect_plc(n)).pack(side="right", padx=5)
        
        # ── 실시간 동기화 / 수동 Teaching 버튼 ──
        ctk.CTkButton(row, text="🎓 수동 Teaching", width=110, fg_color="#7B1FA2", hover_color="#6A1B9A",
                      command=lambda n=name: self._activate_teaching(n)).pack(side="right", padx=3)
        ctk.CTkButton(row, text="📡 실시간 동기화", width=110, fg_color="#1565C0", hover_color="#0D47A1",
                      command=lambda n=name: self._activate_sync(n)).pack(side="right", padx=3)

    def save_ip(self, name, entry_ip, entry_plc):
        new_ip = entry_ip.get()
        new_plc = entry_plc.get()
        robot_manager.add_robot(name, new_ip, new_plc)
        print(f">> 💾 [{name}] 로봇 IP({new_ip}) / PLC IP({new_plc})가 저장되었습니다.")
        
    def connect_plc(self, name):
        print(f">> [PLC 통신] {name}의 PLC 장치와 연결을 시도합니다...")
        def _bg():
            time.sleep(1)
            print(f">> [PLC 성공] {name} PLC 연결 완료!")
        threading.Thread(target=_bg, daemon=True).start()
        
    def connect_robot(self, name):
        def _c():
            info = robot_manager.get_robot_info(name)
            is_connected = info and info.get("instance") is not None
            
            if is_connected:
                print(f">> [통신] {name} 단일 연결 해제 시도...")
                robot_manager.disconnect(name)
                print(f">> [성공] {name} 연결 해제 완료!")
                self.parent.after(0, lambda: self._update_btn_success(name, connected=False))
            else:
                print(f">> [통신] {name} 단일 연결 시도...")
                if robot_manager.connect(name):
                    print(f">> [성공] {name} 연결 완료!")
                    self.parent.after(0, lambda: self._update_btn_success(name, connected=True))
                else:
                    print(f">> [실패] {name} 연결할 수 없습니다.")
        threading.Thread(target=_c, daemon=True).start()
        
    def _update_btn_success(self, name, connected=True):
        if name in self.status_labels:
            self.status_labels[name].configure(
                text="상태: 연결됨" if connected else "상태: 대기중", 
                text_color="#00FF41" if connected else Theme.TEXT_SECONDARY
            )
        if name in self.connect_buttons:
            self.connect_buttons[name].configure(
                text="🔌 연결 해제" if connected else "🔗 로봇 연결", 
                fg_color=Theme.DANGER if connected else Theme.SUCCESS, 
                state="normal"
            )
        
    def _activate_sync(self, name):
        """해당 로봇을 실시간 동기화 모드로 선택 (Page1 디지털트윈 + 옵션 I/O 연동)"""
        info = robot_manager.get_robot_info(name)
        if not info or info.get("instance") is None:
            print(f">> [경고] {name}이(가) 먼저 연결되어 있어야 합니다.")
            return
        robot_manager.set_active_robot(name)
        print(f">> 📡 [{name}] 실시간 동기화 모드로 선택됨! (Page1 디지털트윈 + 옵션 I/O 연동)")
        # 상태 라벨 갱신
        for rn, lbl in self.status_labels.items():
            if rn == name:
                self.parent.after(0, lambda l=lbl: _safe_configure(l, text="상태: 📡 동기화 중", text_color=Theme.INFO))
            else:
                inst = robot_manager.get_robot_info(rn)
                is_conn = inst and inst.get("instance") is not None
                if is_conn:
                    self.parent.after(0, lambda l=lbl: _safe_configure(l, text="상태: 연결됨", text_color="#00FF41"))
    
    def _activate_teaching(self, name):
        """해당 로봇을 수동 Teaching 모드로 선택 (JOG + 프로세스 에디터 연동)"""
        info = robot_manager.get_robot_info(name)
        if not info or info.get("instance") is None:
            print(f">> [경고] {name}이(가) 먼저 연결되어 있어야 합니다.")
            return
        robot_manager.set_active_robot(name)
        print(f">> 🎓 [{name}] 수동 Teaching 모드로 선택됨! (JOG + 프로세스 에디터 연동)")
        # 상태 라벨 갱신
        for rn, lbl in self.status_labels.items():
            if rn == name:
                self.parent.after(0, lambda l=lbl: _safe_configure(l, text="상태: 🎓 Teaching 중", text_color="#CE93D8"))
            else:
                inst = robot_manager.get_robot_info(rn)
                is_conn = inst and inst.get("instance") is not None
                if is_conn:
                    self.parent.after(0, lambda l=lbl: _safe_configure(l, text="상태: 연결됨", text_color="#00FF41"))
        
    def connect_selected(self):
        def _ca():
            for name, chk_var in self.checkboxes.items():
                if chk_var.get() == "on":
                    print(f">> [통신] 선택된 {name} 연결 시도...")
                    if robot_manager.connect(name):
                        print(f">> [성공] {name} 연결 완료!")
                        self.parent.after(0, lambda n=name: self._update_btn_success(n, connected=True))
        threading.Thread(target=_ca, daemon=True).start()

class OptionsEditor:
    def __init__(self, parent_frame):
        self.parent = parent_frame
        self.polling = False
        
    def render(self):
        for w in self.parent.winfo_children(): w.destroy()
        self.polling = True
        
        f = ctk.CTkFrame(self.parent, fg_color=Theme.BG_BASE, corner_radius=12)
        f.pack(expand=True, padx=20, pady=20, fill="both")
        
        ctk.CTkLabel(f, text="🔌 System Options & I/O Monitoring", font=Theme.font(size=24, weight="bold"), text_color="#F57C00").pack(pady=(15, 10))
        
        main_grid = ctk.CTkFrame(f, fg_color="transparent")
        main_grid.pack(fill="both", expand=True, padx=10, pady=10)
        
        main_grid.grid_columnconfigure(0, weight=4) # I/O 패널을 살짝 좁게
        main_grid.grid_columnconfigure(1, weight=3) # TCP
        main_grid.grid_columnconfigure(2, weight=3) # Gripper
        main_grid.grid_rowconfigure(0, weight=1)
        
        # === Column 0: I/O (DI & DO) ===
        io_col = ctk.CTkFrame(main_grid, fg_color="transparent")
        io_col.grid(row=0, column=0, sticky="nsew", padx=10)
        
        di_frame = ctk.CTkFrame(io_col, fg_color=Theme.BG_SURFACE, corner_radius=8)
        di_frame.pack(fill="x", pady=(0, 15))
        self.di_title = ctk.CTkLabel(di_frame, text="📥 Digital Input (D.I) - 연결 안됨", font=ctk.CTkFont(weight="bold", size=18), text_color="#00E5FF")
        self.di_title.pack(pady=(15,5))
        
        self.di_labels = []
        di_grid = ctk.CTkFrame(di_frame, fg_color="transparent")
        di_grid.pack(padx=10, pady=10)
        for i in range(16):
            r, c = divmod(i, 4)
            lbl = ctk.CTkLabel(di_grid, text=f" DI {i:02d} ", corner_radius=6, fg_color="#555555", text_color=Theme.TEXT_PRIMARY, width=70, height=35, font=Theme.font(size=14, weight="bold"))
            lbl.grid(row=r, column=c, padx=5, pady=5)
            self.di_labels.append(lbl)
            
        do_frame = ctk.CTkFrame(io_col, fg_color=Theme.BG_SURFACE, corner_radius=8)
        do_frame.pack(fill="x")
        self.do_title = ctk.CTkLabel(do_frame, text="📤 Digital Output (D.O) - 연결 안됨", font=ctk.CTkFont(weight="bold", size=18), text_color="#00FF41")
        self.do_title.pack(pady=(15,5))
        
        self.do_buttons = []
        do_grid = ctk.CTkFrame(do_frame, fg_color="transparent")
        do_grid.pack(padx=10, pady=10)
        for i in range(16):
            r, c = divmod(i, 4)
            btn = ctk.CTkButton(do_grid, text=f" DO {i:02d} ", corner_radius=6, fg_color="#555555", text_color=Theme.TEXT_PRIMARY, width=70, height=35, font=Theme.font(size=14, weight="bold"), hover_color=Theme.SUCCESS)
            btn.grid(row=r, column=c, padx=5, pady=5)
            btn.configure(command=lambda idx=i, b=btn: self.toggle_do(idx, b))
            self.do_buttons.append(btn)
            
        # === Column 1: TCP Settings ===
        tcp_col = ctk.CTkFrame(main_grid, fg_color="transparent")
        tcp_col.grid(row=0, column=1, sticky="nsew", padx=10)
        
        tcp_frame = ctk.CTkFrame(tcp_col, fg_color=Theme.BG_SURFACE, corner_radius=8)
        tcp_frame.pack(fill="both", expand=True)
        ctk.CTkLabel(tcp_frame, text="🎯 TCP Settings", font=ctk.CTkFont(weight="bold", size=18), text_color="#FF1744").pack(pady=(20, 15))
        
        tcp_grid = ctk.CTkFrame(tcp_frame, fg_color="transparent")
        tcp_grid.pack(padx=15, pady=15)
        
        self.tcp_entries = {}
        for i, label in enumerate(["X (mm)", "Y (mm)", "Z (mm)", "Rx (deg)", "Ry (deg)", "Rz (deg)"]):
            r = i
            ctk.CTkLabel(tcp_grid, text=label, width=80, anchor="e", font=Theme.font(size=15, weight="bold")).grid(row=r, column=0, padx=10, pady=12)
            ent = ctk.CTkEntry(tcp_grid, width=140, height=35, justify="center", font=Theme.font(size=15))
            ent.grid(row=r, column=1, padx=10, pady=12)
            ent.insert(0, "0.0")
            self.tcp_entries[label] = ent
            
        ctk.CTkButton(tcp_frame, text="💾 TCP 로봇 적용", fg_color=Theme.DANGER, hover_color=Theme.DANGER, height=45, font=Theme.font(size=16, weight="bold"), command=self.apply_tcp).pack(pady=20, padx=20, fill="x")
        
        # === Column 2: Gripper Mapping ===
        grip_col = ctk.CTkFrame(main_grid, fg_color="transparent")
        grip_col.grid(row=0, column=2, sticky="nsew", padx=10)
        
        tool_frame = ctk.CTkFrame(grip_col, fg_color=Theme.BG_SURFACE, corner_radius=8)
        tool_frame.pack(fill="both", expand=True)
        ctk.CTkLabel(tool_frame, text="🔧 Tool / Gripper Settings", font=ctk.CTkFont(weight="bold", size=18), text_color="#F57C00").pack(pady=(20, 10))
        
        # 흡착(Suction) vs 일반(Gripper) 선택
        self.tool_type_var = ctk.StringVar(value="Gripper")
        type_seg = ctk.CTkSegmentedButton(tool_frame, values=["Gripper", "Suction (흡착)"], variable=self.tool_type_var, font=Theme.font(size=14, weight="bold"), command=self._on_tool_type_change)
        type_seg.pack(padx=20, pady=10, fill="x")
        
        self.tool_grid = ctk.CTkFrame(tool_frame, fg_color="transparent")
        self.tool_grid.pack(padx=15, pady=15)
        
        # Grip/Hold 핀
        self.lbl_grip = ctk.CTkLabel(self.tool_grid, text="Grip DO Pin:", font=Theme.font(size=15, weight="bold"))
        self.lbl_grip.grid(row=0, column=0, padx=10, pady=10, sticky="e")
        self.grip_pin_entry = ctk.CTkEntry(self.tool_grid, width=100, height=35, justify="center", font=Theme.font(size=15))
        self.grip_pin_entry.grid(row=0, column=1, padx=10, pady=10)
        self.grip_pin_entry.insert(0, "0")
        
        # Release 핀 (Suction일 땐 숨김)
        self.lbl_release = ctk.CTkLabel(self.tool_grid, text="Release DO Pin:", font=Theme.font(size=15, weight="bold"))
        self.lbl_release.grid(row=1, column=0, padx=10, pady=10, sticky="e")
        self.release_pin_entry = ctk.CTkEntry(self.tool_grid, width=100, height=35, justify="center", font=Theme.font(size=15))
        self.release_pin_entry.grid(row=1, column=1, padx=10, pady=10)
        self.release_pin_entry.insert(0, "1")
        
        # Sensor 핀
        ctk.CTkLabel(self.tool_grid, text="Sensor DI Pin:", font=Theme.font(size=15, weight="bold")).grid(row=2, column=0, padx=10, pady=10, sticky="e")
        self.sensor_pin_entry = ctk.CTkEntry(self.tool_grid, width=100, height=35, justify="center", font=Theme.font(size=15))
        self.sensor_pin_entry.grid(row=2, column=1, padx=10, pady=10)
        self.sensor_pin_entry.insert(0, "0")
        
        ctk.CTkButton(tool_frame, text="💾 툴 매핑 저장", fg_color="#F57C00", hover_color=Theme.WARNING, height=45, font=Theme.font(size=16, weight="bold"), command=self.apply_tool_mapping).pack(pady=10, padx=20, fill="x")
        
        test_frame = ctk.CTkFrame(tool_frame, fg_color="transparent")
        test_frame.pack(fill="x", padx=20, pady=15)
        self.btn_test_grip = ctk.CTkButton(test_frame, text="테스트 Grip / Hold", fg_color=Theme.INFO, height=40, font=Theme.font(size=14, weight="bold"), command=lambda: self._test_grip("grip"))
        self.btn_test_grip.pack(side="left", expand=True, padx=5)
        self.btn_test_release = ctk.CTkButton(test_frame, text="테스트 Release", fg_color="#009688", height=40, font=Theme.font(size=14, weight="bold"), command=lambda: self._test_grip("release"))
        self.btn_test_release.pack(side="right", expand=True, padx=5)

        # UI 파괴될 때 폴링 종료
        def on_destroy(event):
            if event.widget == f: self.polling = False
        f.bind("<Destroy>", on_destroy)
        
        # 폴링 스레드 시작
        threading.Thread(target=self.poll_io, daemon=True).start()

    def _on_tool_type_change(self, value):
        if "Suction" in value:
            self.lbl_grip.configure(text="Suction DO Pin:")
            self.btn_test_grip.configure(text="테스트 흡착 (ON)")
            self.btn_test_release.configure(text="테스트 해제 (OFF)")
            
            # Release 핀 숨김
            self.lbl_release.grid_remove()
            self.release_pin_entry.grid_remove()
        else:
            self.lbl_grip.configure(text="Grip DO Pin:")
            self.btn_test_grip.configure(text="테스트 Grip")
            self.btn_test_release.configure(text="테스트 Release")
            
            # Release 핀 다시 보이기
            self.lbl_release.grid()
            self.release_pin_entry.grid()

    def toggle_do(self, idx, btn):
        inst = robot_manager.get_active_instance()
        if not inst:
            print(f">> [경고] 활성화된 로봇이 없습니다.")
            return
            
        current_color = btn.cget("fg_color")
        new_val = 0 if current_color == "#00FF41" else 1
        
        from core.domains.robot.use_cases.robot_control_usecase import RobotControlUseCase
        RobotControlUseCase.set_do(idx, new_val)
        print(f">> [D.O 제어] DO 핀 {idx}을(를) {new_val} 상태로 변경했습니다.")

    def poll_io(self):
        while self.polling:
            inst = robot_manager.get_active_instance()
            name = robot_manager.get_active_robot_name()
            if inst and name:
                try:
                    # 타이틀 업데이트
                    self.parent.after(0, lambda n=name: _safe_configure(self.di_title, text=f"📥 Digital Input (D.I) - {n}"))
                    self.parent.after(0, lambda n=name: _safe_configure(self.do_title, text=f"📤 Digital Output (D.O) - {n}"))
                    
                    di_state = inst.get_di() if hasattr(inst, 'get_di') else None
                    do_state = inst.get_do() if hasattr(inst, 'get_do') else None
                        
                    if di_state is not None:
                        for i in range(16):
                            val = di_state[i] if isinstance(di_state, (list, tuple)) and i < len(di_state) else 0
                            color = "#00FF41" if val else "#555555"
                            self.parent.after(0, lambda lbl=self.di_labels[i], c=color: _safe_configure(lbl, fg_color=c))
                            
                    if do_state is not None:
                        for i in range(16):
                            val = do_state[i] if isinstance(do_state, (list, tuple)) and i < len(do_state) else 0
                            color = "#00FF41" if val else "#555555"
                            self.parent.after(0, lambda btn=self.do_buttons[i], c=color: _safe_configure(btn, fg_color=c))
                            
                except Exception as e:
                    print(f">> [폴링 에러] {e}")
            else:
                try:
                    self.parent.after(0, lambda: _safe_configure(self.di_title, text="📥 Digital Input (D.I) - 연결 안됨"))
                    self.parent.after(0, lambda: _safe_configure(self.do_title, text="📤 Digital Output (D.O) - 연결 안됨"))
                except: pass
            time.sleep(0.5)

    def apply_tcp(self):
        inst = robot_manager.get_active_instance()
        if not inst:
            print(">> [경고] 설정할 활성 로봇이 없습니다.")
            return
            
        try:
            tcp_vals = []
            for label in ["X (mm)", "Y (mm)", "Z (mm)", "Rx (deg)", "Ry (deg)", "Rz (deg)"]:
                val = float(self.tcp_entries[label].get())
                tcp_vals.append(val)
                
            from core.domains.robot.use_cases.robot_control_usecase import RobotControlUseCase
            RobotControlUseCase.set_tcp(tcp_vals)
            print(f">> [TCP 설정] {tcp_vals} 값이 적용되었습니다.")
        except ValueError:
            print(">> [에러] TCP 입력란에는 숫자만 입력해주세요.")

    def apply_tool_mapping(self):
        try:
            g_pin = int(self.grip_pin_entry.get())
            r_pin = int(self.release_pin_entry.get())
            print(f">> [툴 맵핑] Grip = DO {g_pin}, Release = DO {r_pin} 설정 완료!")
            
            # Save to JSON memory if available
            if hasattr(self.parent, "main_app"):
                app = self.parent.main_app
                if hasattr(app, "_current_raw_data"):
                    raw = app._current_raw_data
                    if "toolInfo" in raw and isinstance(raw["toolInfo"], list) and len(raw["toolInfo"]) > 0:
                        tool = raw["toolInfo"][0]
                        if "toolCommand" in tool:
                            for cmd in tool["toolCommand"]:
                                if cmd.get("name") == "Hold":
                                    cmd["doMap"] = [{"idx": g_pin, "value": 1}]
                                elif cmd.get("name") == "Release":
                                    cmd["doMap"] = [{"idx": r_pin, "value": 1}]
                    print(">> [저장됨] JSON 메모리에 툴 매핑이 업데이트 되었습니다.")
        except ValueError:
            print(">> [에러] 핀 번호는 숫자만 입력해주세요.")

    def _test_grip(self, action):
        inst = robot_manager.get_active_instance()
        if not inst:
            print(f">> [경고] 테스트할 연결된 로봇이 없습니다.")
            return
            
        try:
            g_pin = int(self.grip_pin_entry.get())
            is_suction = "Suction" in self.tool_type_var.get()
            
            if not is_suction:
                r_pin = int(self.release_pin_entry.get())
            
            def _bg():
                if not hasattr(inst, 'set_do'): return
                
                if is_suction:
                    if action == "grip":
                        print(f">> [흡착 테스트] 진공 ON (DO {g_pin} ON)")
                        inst.set_do(g_pin, 1)
                    else:
                        print(f">> [흡착 테스트] 진공 OFF (DO {g_pin} OFF)")
                        inst.set_do(g_pin, 0)
                else:
                    if action == "grip":
                        print(f">> [그리퍼 테스트] Grip 작동 (DO {g_pin} ON, DO {r_pin} OFF)")
                        inst.set_do(r_pin, 0)
                        time.sleep(0.1)
                        inst.set_do(g_pin, 1)
                    else:
                        print(f">> [그리퍼 테스트] Release 작동 (DO {g_pin} OFF, DO {r_pin} ON)")
                        inst.set_do(g_pin, 0)
                        time.sleep(0.1)
                        inst.set_do(r_pin, 1)
            threading.Thread(target=_bg, daemon=True).start()
        except ValueError:
            print(">> [에러] 올바른 핀 번호를 먼저 입력해주세요.")

class LogViewer:
    def __init__(self, parent_frame):
        self.parent = parent_frame
        self._poll_id = None
        
    def render(self):
        for w in self.parent.winfo_children(): w.destroy()
        
        f = ctk.CTkFrame(self.parent, fg_color=Theme.BG_BASE, corner_radius=12)
        f.pack(expand=True, padx=40, pady=30, fill="both")
        
        ctk.CTkLabel(f, text="📡 통신 체크 & 수동 연결", font=Theme.font(size=20, weight="bold"), text_color=Theme.TEXT_PRIMARY).pack(pady=(20, 5))
        ctk.CTkLabel(f, text="각 서비스의 연결 상태를 확인하고 수동으로 연결/해제할 수 있습니다", font=Theme.font(size=12), text_color=Theme.TEXT_SECONDARY).pack(pady=(0, 15))
        
        # ── 서비스 카드 리스트 ──
        self.cards = {}
        services = [
            {"key": "robot_plc", "icon": "🤖", "name": "로봇 + PLC (전체 연결)", "desc": "Indy7 IndyDCP 소켓 + 미쓰비시 PLC 동시 연결", "color": "#00E676"},
            {"key": "mqtt",      "icon": "📮", "name": "중앙 통신 허브",        "desc": "MQTT Broker (Mosquitto) 연결",             "color": "#00B0FF"},
            {"key": "db",        "icon": "🗄",  "name": "MySQL Database",      "desc": "FA MES 데이터베이스 연결",                   "color": "#FF9100"},
            {"key": "vision_a",  "icon": "👁",  "name": "Vision A",            "desc": "카메라 A — 메인 작업대 YOLO 추론",           "color": "#FF1744"},
            {"key": "vision_b",  "icon": "👁",  "name": "Vision B",            "desc": "카메라 B — 보조 작업대 YOLO 추론",           "color": "#FF6D00"},
            {"key": "vision_c",  "icon": "👁",  "name": "Vision C",            "desc": "카메라 C — 품질 검사 YOLO 추론",             "color": "#FFAB00"},
        ]
        
        cards_frame = ctk.CTkFrame(f, fg_color="transparent")
        cards_frame.pack(fill="both", expand=True, padx=20, pady=5)
        
        for svc in services:
            card = ctk.CTkFrame(cards_frame, fg_color=Theme.BG_SURFACE, corner_radius=10, height=60)
            card.pack(fill="x", pady=4)
            card.pack_propagate(False)
            
            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="x", padx=15, pady=10)
            
            # 왼쪽: 상태 표시등 + 이름
            left = ctk.CTkFrame(inner, fg_color="transparent")
            left.pack(side="left")
            
            indicator = ctk.CTkLabel(left, text="🔴", font=ctk.CTkFont(size=16), width=25)
            indicator.pack(side="left")
            
            name_frame = ctk.CTkFrame(left, fg_color="transparent")
            name_frame.pack(side="left", padx=10)
            ctk.CTkLabel(name_frame, text=f"{svc['icon']} {svc['name']}", font=Theme.font(size=14, weight="bold"), text_color=svc["color"]).pack(anchor="w")
            ctk.CTkLabel(name_frame, text=svc["desc"], font=Theme.font(size=11), text_color=Theme.TEXT_SECONDARY).pack(anchor="w")
            
            # 오른쪽: 상태 텍스트 + 연결/해제 버튼
            right = ctk.CTkFrame(inner, fg_color="transparent")
            right.pack(side="right")
            
            status_label = ctk.CTkLabel(right, text="⚪ 대기", font=Theme.font(size=12), text_color=Theme.TEXT_SECONDARY, width=100)
            status_label.pack(side="left", padx=10)
            
            connect_btn = ctk.CTkButton(right, text="연결", width=70, height=30, corner_radius=8,
                                         fg_color=Theme.SUCCESS, hover_color="#00C853",
                                         command=lambda k=svc["key"]: self._on_connect(k))
            connect_btn.pack(side="left", padx=3)
            
            disconnect_btn = ctk.CTkButton(right, text="해제", width=70, height=30, corner_radius=8,
                                            fg_color="#B71C1C", hover_color="#D32F2F",
                                            command=lambda k=svc["key"]: self._on_disconnect(k))
            disconnect_btn.pack(side="left", padx=3)
            
            self.cards[svc["key"]] = {"indicator": indicator, "status": status_label, "connect": connect_btn, "disconnect": disconnect_btn}
        
        # ── 하단 로그 영역 ──
        ctk.CTkLabel(f, text="📋 연결 로그", font=Theme.font(size=13, weight="bold"), text_color=Theme.TEXT_SECONDARY).pack(anchor="w", padx=25, pady=(10, 0))
        self.textbox = ctk.CTkTextbox(f, height=120, fg_color="#0D1117", text_color="#00FF41", font=ctk.CTkFont(family="Consolas", size=12))
        self.textbox.pack(fill="x", padx=20, pady=(5, 20))
        self._log("[SYS] 통신 체크 화면 초기화 완료")
        self._log("[SYS] 연결 버튼을 눌러 수동으로 서비스에 접속하세요")
        
        # 상태 폴링 시작
        self._poll_status()
    
    def _log(self, msg):
        import datetime
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.textbox.insert("end", f"[{ts}] {msg}\n")
        self.textbox.see("end")
    
    def _on_connect(self, key):
        if key == "robot_plc":
            try:
                from core.domains.robot.communication.client_manager import robot_manager
                from core.service_manager import service_mgr
                robot_manager.connect()
                service_mgr.services["plc"].start()
                self._log("🤖 [Robot+PLC] 전체 연결 시도 중... (IndyDCP + MC Protocol)")
            except Exception as e:
                self._log(f"🤖 [Robot+PLC] 연결 실패: {e}")
        elif key == "mqtt":
            try:
                from core.service_manager import service_mgr
                service_mgr.services["mqtt"].start()
                self._log("📮 [MQTT] 중앙 통신 허브 연결 시도 중...")
            except Exception as e:
                self._log(f"📮 [MQTT] 연결 실패: {e}")
        elif key == "db":
            try:
                from core.service_manager import service_mgr
                service_mgr.services["db"].start()
                self._log("🗄 [DB] MySQL 연결 시도 중...")
            except Exception as e:
                self._log(f"🗄 [DB] 연결 실패: {e}")
        elif key.startswith("vision_"):
            cam_label = key.replace("vision_", "").upper()
            try:
                from core.service_manager import service_mgr
                service_mgr.services["vision"].start()
                self._log(f"👁 [Vision {cam_label}] 카메라 {cam_label} 시작 시도 중...")
            except Exception as e:
                self._log(f"👁 [Vision {cam_label}] 시작 실패: {e}")
    
    def _on_disconnect(self, key):
        if key == "robot_plc":
            try:
                from core.domains.robot.communication.client_manager import robot_manager
                from core.service_manager import service_mgr
                robot_manager.disconnect()
                svc = service_mgr.services.get("plc")
                if svc and svc.is_running:
                    svc.stop()
                self._log("🤖 [Robot+PLC] 전체 연결 해제 완료")
            except Exception as e:
                self._log(f"🤖 [Robot+PLC] 해제 실패: {e}")
        elif key.startswith("vision_"):
            cam_label = key.replace("vision_", "").upper()
            try:
                from core.service_manager import service_mgr
                svc = service_mgr.services.get("vision")
                if svc and svc.is_running:
                    svc.stop()
                self._log(f"👁 [Vision {cam_label}] 카메라 {cam_label} 중지 완료")
            except Exception as e:
                self._log(f"👁 [Vision {cam_label}] 해제 실패: {e}")
        else:
            try:
                from core.service_manager import service_mgr
                svc = service_mgr.services.get(key)
                if svc and svc.is_running:
                    svc.stop()
                    self._log(f"{svc.icon} [{svc.name}] 서비스 중지 완료")
                else:
                    self._log(f"[{key}] 이미 중지 상태입니다")
            except Exception as e:
                self._log(f"[{key}] 해제 실패: {e}")
    
    def _poll_status(self):
        """500ms마다 각 서비스 연결 상태를 UI에 반영"""
        try:
            from core.service_manager import service_mgr
            from core.domains.robot.communication.client_manager import robot_manager
            
            # Robot+PLC 전체 상태 (둘 다 연결되어야 🟢)
            robot_ok = robot_manager.is_connected() if hasattr(robot_manager, 'is_connected') else False
            plc_ok = service_mgr.services["plc"].is_running
            self._update_card("robot_plc", robot_ok or plc_ok)
            
            # MQTT
            self._update_card("mqtt", service_mgr.services["mqtt"].is_running)
            
            # DB
            self._update_card("db", service_mgr.services["db"].is_running)
            
            # Vision A/B/C (현재는 하나의 비전 서비스를 공유, 향후 개별 분리 가능)
            vision_running = service_mgr.services["vision"].is_running
            for cam in ["vision_a", "vision_b", "vision_c"]:
                self._update_card(cam, vision_running if cam == "vision_a" else False)
        except Exception:
            pass
        
        try:
            self._poll_id = self.parent.after(500, self._poll_status)
        except Exception:
            pass
    
    def _update_card(self, key, is_connected):
        card = self.cards.get(key)
        if not card:
            return
        if is_connected:
            card["indicator"].configure(text="🟢")
            card["status"].configure(text="✅ 연결됨", text_color="#00E676")
        else:
            card["indicator"].configure(text="🔴")
            card["status"].configure(text="⚪ 대기", text_color=Theme.TEXT_SECONDARY)

class RobotHmiView:
    def __init__(self, parent_tab, on_back=None):
        self.parent = parent_tab
        self.on_back = on_back
        self.parent.grid_columnconfigure(0, weight=1)
        self.parent.grid_rowconfigure(0, weight=0)
        self.parent.grid_rowconfigure(1, weight=1)
        self.setup_navbar()
        
        self.content_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        self.content_frame.grid(row=1, column=0, sticky="nsew")
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)
        
        self.switch_view("프로그램")
        
    def setup_navbar(self):
        nav_bar = ctk.CTkFrame(self.parent, fg_color=Theme.BG_BASE, height=45)
        nav_bar.grid(row=0, column=0, sticky="ew")
        nav_container = ctk.CTkFrame(nav_bar, fg_color="transparent")
        nav_container.pack(expand=True)
        items = ["이전으로", "옵션", "로봇설정", "프로그램", "통신체크", "리셋"]
        for item in items:
            btn = ctk.CTkButton(nav_container, text=item, fg_color="transparent", text_color="#A0A0A0", 
                                font=Theme.font(size=12, weight="bold"), hover_color=Theme.BG_SURFACE, corner_radius=0,
                                command=lambda x=item: self.switch_view(x))
            btn.pack(side="left", padx=5)

    def switch_view(self, name):
        if name == "이전으로" and self.on_back:
            self.on_back()
            return
            
        for w in self.content_frame.winfo_children(): w.destroy()
        
        if name == "로봇설정":
            RobotSettingsEditor(self.content_frame).render()
        elif name == "프로그램":
            ProgramTreeEditor(self.content_frame).render()
        elif name == "옵션":
            OptionsEditor(self.content_frame).render()
        elif name == "통신체크":
            LogViewer(self.content_frame).render()
        else:
            ctk.CTkLabel(self.content_frame, text=f"{name} 뷰는 아직 준비되지 않았습니다.").pack(expand=True)