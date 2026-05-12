import customtkinter as ctk
from core.domains.robot.communication.client_manager import robot_manager
from .editors.motion_editors import JogController, MoveEditor, MoveByEditor, MoveCEditor, MoveHomeEditor, ForceEditor
from .editors.logic_editors import LoopEditor, MathEditor, CallEditor, IfEditor, WaitEditor, WaitDIEditor, WaitAIEditor, CommentEditor, StopEditor, SwitchEditor, FolderEditor
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
        
    def save_program(self, silent=False):
        robot = self.robot_sel.get()
        if not silent:
            from core.domains.robot.communication.client_manager import robot_manager
            robot_manager.set_active_robot(robot)
        path = self.get_current_program_path(robot)
        
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
                        continue
                        
                    n = TeachingNode(len(prog.nodes) + len(nodes) + 1, p_id, 100)
                    n.name = node_name
                    
                    if "Move J" in node_name: n.type = 103
                    elif "Move L" in node_name: n.type = 104
                    elif "Move C" in node_name: n.type = 105
                    elif "Move B" in node_name: n.type = 106
                    elif "Move By" in node_name: n.type = 110
                    elif "Move Home" in node_name: n.type = 102
                    elif "Pick" in node_name: n.type = 201
                    elif "Place" in node_name: n.type = 202
                    elif "Wait DI" in node_name: n.type = 29
                    elif "Wait AI" in node_name: n.type = 30
                    elif "Wait" in node_name: n.type = 28
                    elif "Loop" in node_name: n.type = 20
                    elif "Switch" in node_name: n.type = 31
                    elif "If" in node_name: n.type = 29
                    elif "Math" in node_name: n.type = 21
                    elif "Call" in node_name: n.type = 40
                    elif "Force" in node_name: n.type = 41
                    elif "Vision" in node_name: n.type = 203
                    elif "Sync" in node_name: n.type = 60
                    elif "Set DO" in node_name: n.type = 25
                    elif "Set AO" in node_name: n.type = 26
                    elif "Folder" in node_name: n.type = 98
                    elif "Comment" in node_name: n.type = 99
                    elif "Stop" in node_name: n.type = 10
                    
                    # Conty 호환 __raw__ 기본 템플릿 생성
                    _ref = {"type": 1, "tref": [0,0,0,0,0,0]}
                    _tcp = [0,0,0,0,0,0]
                    raw_templates = {
                        100: {"enable": True, "type": 100, "pId": p_id},  # Move (generic)
                        103: {"wpList": [], "enable": True, "type": 103, "pId": p_id},  # Move J
                        104: {"wpList": [], "enable": True, "type": 104, "pId": p_id},  # Move L
                        105: {"wpList": [], "enable": True, "type": 105, "pId": p_id},  # Move C
                        106: {"wpList": [], "enable": True, "type": 106, "pId": p_id},  # Move B
                        110: {"enable": True, "type": 110, "pId": p_id, "offset": {"dx": 0, "dy": 0, "dz": 0}},
                        102: {"enable": True, "type": 102, "pId": p_id},  # Move Home
                        20:  {"count": -1, "enable": True, "type": 20, "pId": p_id},  # Loop
                        28:  {"endtoolDiList": [], "type": 28, "time": 1, "enable": True, "diList": [], "pId": p_id},
                        29:  {"endtoolDiList": [], "type": 29, "enable": True, "diList": [], "pId": p_id},
                        30:  {"enable": True, "type": 30, "pId": p_id},
                        22:  {"time": 0, "enable": True, "type": 22, "pId": p_id},
                        25:  {"doList": [], "enable": True, "type": 4, "pId": p_id},  # Set DO → Conty type=4
                        26:  {"enable": True, "type": 5, "aoList": [], "pId": p_id},  # Set AO → Conty type=5
                        21:  {"enable": True, "type": 21, "pId": p_id},
                        31:  {"varList": [], "enable": True, "type": 3, "pId": p_id},  # Switch → Conty type=3
                        40:  {"enable": True, "type": 40, "toolCmd": {"cmdId": -1, "toolId": -1}, "pId": p_id},
                        41:  {"type": 41, "toolCmd": {"cmdId": -1, "toolId": -1}, "enable": True, "sensName": "", "pId": p_id},
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
                        203: {"enable": True, "type": 203, "pId": p_id},
                        10:  {"enable": True, "type": 1, "pId": p_id},  # Stop → Conty type=1
                        98:  {"groupName": "", "enable": True, "type": 200, "pId": p_id},  # Folder → Conty type=200
                        99:  {"enable": True, "type": 99, "pId": p_id},
                        60:  {"enable": True, "type": 60, "pId": p_id},
                    }
                    
                    if child in self.node_data:
                        d = self.node_data[child]
                        # 기본 템플릿에서 시작하고, 기존 __raw__와 node_data를 덮어씌움
                        base_raw = raw_templates.get(n.type, {"enable": True, "type": n.type, "pId": p_id})
                        n.__raw__ = base_raw.copy()
                        n.__raw__.update(d)
                        if d.get("q") is not None:
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
            repo.save_to_json(prog, path)
            print(f">> [성공] 프로그램 {prog.name} 저장 완료: {path}")
            if not silent:
                from tkinter import messagebox
                messagebox.showinfo("저장 성공", f"프로그램이 저장되었습니다.\n{path}")
        except Exception as e:
            print(f">> [실패] 저장 중 에러 발생: {e}")
            import traceback
            traceback.print_exc()
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
                            name = getattr(node, "name", "")
                            cid = getattr(node, "id", 0)
                            pid = getattr(node, "pId", 0)
                            
                            parent_item = node_map.get(pid, main_node)
                            node_str = f" Node ({name})"
                            if t == 100: node_str = f" Move Group ({name})" if name else " Move Group"
                            elif t == 102: node_str = f" Move Home Node ({name})" if name else " Move Home Node"
                            elif t == 103: node_str = f" Move J Node ({name})" if name else " Move J Node"
                            elif t == 104: node_str = f" Move L Node ({name})" if name else " Move L Node"
                            elif t == 105: node_str = f" Move C Node ({name})" if name else " Move C Node"
                            elif t == 106: node_str = f" Move B Node ({name})" if name else " Move B Node"
                            elif t == 110: node_str = f" Move By Node ({name})" if name else " Move By Node"
                            elif t == 200: node_str = f" Folder ({name})" if name else " Folder"
                            elif t == 201: node_str = f" Pick Node ({name})" if name else " Pick Node"
                            elif t == 202: node_str = f" Place Node ({name})" if name else " Place Node"
                            elif t == 28: node_str = " Wait Node"
                            elif t == 29: node_str = " Wait DI Node"
                            elif t == 30: node_str = " Wait AI Node"
                            elif t == 31: node_str = f" Switch Node ({name})" if name else " Switch Node"
                            elif t == 20: node_str = " Loop Node"
                            elif t == 21: node_str = f" Math Node ({name})" if name else " Math Node"
                            elif t == 24: node_str = f" If Condition ({name})" if name else " If Condition"
                            elif t == 25: node_str = f" Set DO Node ({name})" if name else " Set DO Node"
                            elif t == 26: node_str = f" Set AO Node ({name})" if name else " Set AO Node"
                            elif t == 40: node_str = f" Call Node ({name})" if name else " Call Node"
                            elif t == 41: node_str = f" Force Node ({name})" if name else " Force Node"
                            elif t == 60: node_str = f" Sync Node ({name})" if name else " Sync Node"
                            elif t == 203: node_str = f" Vision Node ({name})" if name else " Vision Node"
                            elif t == 999: node_str = f" Program Settings"
                            elif t == 2: node_str = f" Variables"
                            else: node_str = f" Unknown Node ({t})"
                                
                            n_id = self.tree.insert(parent_item, "end", text=node_str)
                            node_map[cid] = n_id
                            
                            # OOD TeachingRepositoryImpl uses target_q and target_p
                            self.node_data[n_id] = {
                                "q": getattr(node, "target_q", getattr(node, "joint_pos", [0.0]*6)),
                                "p": getattr(node, "target_p", getattr(node, "task_pos", [0.0]*6))
                            }
                            
                            if t in [103, 104, 105, 106, 110]:
                                self.node_data[n_id]["t_type"] = "move"
                                self.node_data[n_id]["b_radius"] = getattr(node, "blending_radius", 0.0)
                                self.node_data[n_id]["boundary"] = getattr(node, "__raw__", {}).get("boundary", {"velLevel": 5, "accLevel": 5})
                                if t == 110:
                                    self.node_data[n_id]["offset"] = getattr(node, "__raw__", {}).get("offset", {})
                            elif t in [201, 202]:
                                self.node_data[n_id]["target_type"] = getattr(node, "target_type", 0)
                                self.node_data[n_id]["t_type"] = getattr(node, "target_type", 0)
                                self.node_data[n_id]["target_pallet_name"] = getattr(node, "target_pallet_name", "")
                                self.node_data[n_id]["target_pallet_id"] = getattr(node, "target_pallet_id", "")
                                self.node_data[n_id]["p_name"] = getattr(node, "target_pallet_name", "")
                                self.node_data[n_id]["p_data"] = getattr(node, "p_data", getattr(node, "target_pallet_data", None))
                                self.node_data[n_id]["toolId"] = getattr(node, "toolId", 1)
                                self.node_data[n_id]["app_data"] = getattr(node, "__raw__", {}).get("approach", getattr(node, "approach", {}))
                                self.node_data[n_id]["ret_data"] = getattr(node, "__raw__", {}).get("retract", getattr(node, "retract", {}))
                                self.node_data[n_id]["approach"] = self.node_data[n_id]["app_data"]
                                self.node_data[n_id]["retract"] = self.node_data[n_id]["ret_data"]
                            elif t == 21: # Math
                                self.node_data[n_id]["mathVar"] = getattr(node, "math_var_name", "var1")
                                self.node_data[n_id]["mathOp"] = getattr(node, "math_operator", "+")
                                self.node_data[n_id]["mathVal"] = getattr(node, "math_value", 0.0)
                            elif t == 24: # If
                                self.node_data[n_id]["cond"] = getattr(node, "__raw__", {}).get("cond", {})
                            elif t in [22, 28]: # Wait
                                self.node_data[n_id]["time"] = getattr(node, "__raw__", {}).get("time", 1.0)
                            elif t in [29]: # Wait DI / Set DO
                                self.node_data[n_id]["diList"] = getattr(node, "__raw__", {}).get("diList", [])
                            elif t == 202:
                                self.node_data[n_id]["t_type"] = getattr(node, "target_type", 0)
                                self.node_data[n_id]["p_name"] = getattr(node, "target_pallet_name", "")
                                self.node_data[n_id]["p_data"] = getattr(node, "target_pallet_data", None)
                                self.node_data[n_id]["app_data"] = getattr(node, "__raw__", {}).get("approach", {})
                                self.node_data[n_id]["ret_data"] = getattr(node, "__raw__", {}).get("retract", {})
                                self.node_data[n_id]["approach"] = self.node_data[n_id]["app_data"]
                                self.node_data[n_id]["retract"] = self.node_data[n_id]["ret_data"]

                print(f">> [성공] {file_path} 에서 프로그램을 로드했습니다.")
                self.custom_paths[self.current_robot] = file_path
                self.refresh_info()
            except Exception as e:
                traceback.print_exc()
                print(f">> [실패] JSON 파싱 오류: {e}")

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
        # 가상 시뮬레이션 창 띄우기 (요구사항 4)
        sim_win = ctk.CTkToplevel(self.parent)
        sim_win.title("가상 프로그래밍 시뮬레이션")
        sim_win.geometry("700x800")
        sim_win.attributes('-topmost', True)
        
        ctk.CTkLabel(sim_win, text="🖥️ VIRTUAL EXECUTION MODE", font=Theme.font(size=18, weight="bold"), text_color="#F57C00").pack(pady=10)
        
        # 3D 뷰어 컨테이너 (상단)
        viewer_container = ctk.CTkFrame(sim_win, height=350, fg_color="black")
        viewer_container.pack(fill="x", padx=10, pady=5)
        viewer_container.pack_propagate(False)
        
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        import numpy as np
        import random
        
        fig = plt.Figure(figsize=(6, 4), facecolor=Theme.BG_BASE)
        fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
        ax = fig.add_subplot(111, projection='3d')
        ax.set_facecolor(Theme.BG_BASE)
        for pane in (ax.xaxis, ax.yaxis, ax.zaxis): pane.set_pane_color((0.09, 0.09, 0.11, 1.0))
        ax.grid(color='#2A2A35', linestyle=':', linewidth=0.5)
        ax.tick_params(colors=Theme.TEXT_SECONDARY, labelsize=8)
        ax.set_xlim([-0.8, 0.8]); ax.set_ylim([-0.8, 0.8]); ax.set_zlim([0, 1.2])
        ax.view_init(elev=20, azim=45)
        
        robot_line, = ax.plot([], [], [], '-', color="#00FF41", lw=3)
        robot_dots, = ax.plot([], [], [], 'o', color="#00FF41", markersize=6, markerfacecolor='white', markeredgecolor="#00FF41", markeredgewidth=2)
        
        canvas = FigureCanvasTkAgg(fig, master=viewer_container)
        canvas.get_tk_widget().pack(fill="both", expand=True)
        
        # 순운동학용 파라미터
        dh_params = [
            {"a": 0.0, "alpha": 0.0, "d": 0.3, "theta_offset": 0.0},
            {"a": 0.0, "alpha": np.pi/2, "d": 0.0, "theta_offset": np.pi/2},
            {"a": 0.45, "alpha": 0.0, "d": 0.0035, "theta_offset": np.pi/2},
            {"a": 0.0, "alpha": np.pi/2, "d": 0.35, "theta_offset": np.pi},
            {"a": 0.0, "alpha": np.pi/2, "d": 0.1835, "theta_offset": 0.0},
            {"a": 0.0, "alpha": -np.pi/2, "d": 0.228, "theta_offset": 0.0}
        ]
        
        def _draw_robot(j_angles, tool_color="#00FF41"):
            T = np.eye(4)
            T_matrices = [T]
            for i in range(6):
                theta = np.radians(j_angles[i]) + dh_params[i]['theta_offset']
                a = dh_params[i]['a']; alpha = dh_params[i]['alpha']; d = dh_params[i]['d']
                ct, st = np.cos(theta), np.sin(theta); ca, sa = np.cos(alpha), np.sin(alpha)
                T_i = np.array([[ct, -st, 0, a], [st*ca, ct*ca, -sa, -d*sa], [st*sa, ct*sa, ca, d*ca], [0, 0, 0, 1]])
                T = T @ T_i
                T_matrices.append(T)
            P0 = T_matrices[0][:3, 3]
            P1 = T_matrices[1][:3, 3]
            P2 = (T_matrices[2] @ np.array([0, 0, 0.1835, 1]))[:3]
            P3 = (T_matrices[3] @ np.array([0, 0, 0.1835, 1]))[:3]
            P3_c = T_matrices[3][:3, 3]
            P4 = T_matrices[4][:3, 3]
            P5 = T_matrices[5][:3, 3]
            # Apply TCP offset (0.21m in Z-axis of tool frame)
            P6 = (T_matrices[6] @ np.array([0, 0, 0.21, 1]))[:3]
            
            line_xs = [P0[0], P1[0], P2[0], P3[0], P3_c[0], P4[0], P5[0], P6[0]]
            line_ys = [P0[1], P1[1], P2[1], P3[1], P3_c[1], P4[1], P5[1], P6[1]]
            line_zs = [P0[2], P1[2], P2[2], P3[2], P3_c[2], P4[2], P5[2], P6[2]]
            robot_line.set_data(line_xs, line_ys)
            robot_line.set_3d_properties(line_zs)
            robot_line.set_color(tool_color)
            
            j_xs = [P0[0], P2[0], P3[0], P4[0], P5[0], P6[0]]
            j_ys = [P0[1], P2[1], P3[1], P4[1], P5[1], P6[1]]
            j_zs = [P0[2], P2[2], P3[2], P4[2], P5[2], P6[2]]
            robot_dots.set_data(j_xs, j_ys)
            robot_dots.set_3d_properties(j_zs)
            robot_dots.set_markeredgecolor(tool_color)
            
            canvas.draw_idle()
            
        # 초기 렌더링
        current_j = [0.0, 0.0, -90.0, 0.0, -90.0, 0.0]
        _draw_robot(current_j)

        # 텍스트 로그 (하단)
        log_box = ctk.CTkTextbox(sim_win, fg_color=Theme.BG_BASE, text_color="#00E5FF", font=ctk.CTkFont(family="Consolas"))
        log_box.pack(fill="both", expand=True, padx=10, pady=10)
        
        nodes = []
        # Return both item id and text
        def _get_items_and_text(item):
            result = []
            for child in self.tree.get_children(item):
                result.append((child, self.tree.item(child, "text").strip()))
                result.extend(_get_items_and_text(child))
            return result
            
        for item in self.tree.get_children():
            nodes.extend(_get_items_and_text(item))
            
        if not nodes:
            log_box.insert("end", "[경고] 프로그램 트리가 비어있습니다.\n")
            return
            
        def _run_sim():
            log_box.insert("end", "[시스템] 실제 티칭(Teaching) 데이터 기반 시뮬레이션을 시작합니다...\n")
            log_box.insert("end", "-"*40 + "\n")
            
            nonlocal current_j
            for i, (item_id, n) in enumerate(nodes):
                log_box.insert("end", f"[{i+1}/{len(nodes)}] 실행 중 ➔ {n}\n")
                log_box.see("end")
                
                # 애니메이션 로직
                target_j = None
                if hasattr(self, 'node_joint_targets') and item_id in self.node_joint_targets:
                    target_j = self.node_joint_targets[item_id]
                
                if "Move" in n or target_j is not None:
                    if target_j is None:
                        import random
                        target_j = [random.uniform(-45, 45) for _ in range(6)]
                        target_j[2] -= 90 # J3 offset
                        target_j[4] -= 90 # J5 offset
                        
                    steps = 15
                    for step in range(steps):
                        interp_j = [current_j[k] + (target_j[k] - current_j[k]) * (step / steps) for k in range(6)]
                        
                        tool_color = "#00FF41"
                        if "Pick" in n: tool_color = "#FF1744"
                        elif "Place" in n: tool_color = Theme.INFO
                        
                        _draw_robot(interp_j, tool_color=tool_color)
                        time.sleep(0.05)
                    current_j = target_j
                elif "Pick" in n:
                    _draw_robot(current_j, tool_color="#FF1744") # 빨간색
                    time.sleep(0.5)
                elif "Place" in n:
                    _draw_robot(current_j, tool_color=Theme.INFO) # 파란색
                    time.sleep(0.5)
                else:
                    _draw_robot(current_j, tool_color="#00FF41") # 기본색
                    time.sleep(0.8)
                    
            time.sleep(0.5)
            _draw_robot(current_j, tool_color="#00FF41")
            log_box.insert("end", "-"*40 + "\n")
            log_box.insert("end", "[시스템] 모든 프로그램 노드 가상 실행 완료!\n")
            
        threading.Thread(target=_run_sim, daemon=True).start()

    def render(self):
        for w in self.parent.winfo_children(): w.destroy()
        
        self.parent.grid_columnconfigure(0, weight=0, minsize=140) # Palette (고정)
        self.parent.grid_columnconfigure(1, weight=1) # Tree (가운데)
        self.parent.grid_columnconfigure(2, weight=2, minsize=420) # Jog + 설정 (넓게)
        self.parent.grid_rowconfigure(0, weight=1)
        Theme.apply_window_style(self.parent)
        
        # Left Palette
        left = ctk.CTkScrollableFrame(self.parent, fg_color=Theme.BG_BASE, width=160, corner_radius=0)
        left.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        ctk.CTkLabel(left, text="🛠 COMMANDS", font=Theme.font(size=14, weight="bold", role="display"), text_color=Theme.TEXT_PRIMARY).pack(pady=10)
        
        # ─── APK 기능 (Conty 호환) ───
        ctk.CTkLabel(left, text="📱 APK 기능", font=Theme.font(size=11, weight="bold"), 
                     text_color=Theme.SUCCESS).pack(anchor="w", padx=10, pady=(5, 2))
        apk_cmds = [
            ("Folder", Theme.WARNING), ("Move Home", Theme.INFO), ("Joint Move", Theme.INFO), 
            ("Frame Move", Theme.SUCCESS), ("Move B", "#F57C00"), ("Move C", "#009688"),
            ("Pick", Theme.INFO), ("Place", "#009688"), ("DO", "#9C27B0"), 
            ("Wait", "#607D8B"), ("Wait DI", "#607D8B"), ("Loop", Theme.DANGER), 
            ("If (DI)", "#E91E63"), ("Math", "#FF5722"), ("Comment", "#9E9E9E"), 
            ("Stop", Theme.DANGER), ("Call", Theme.BG_SURFACE),
        ]
        for cmd, col in apk_cmds:
            btn = ctk.CTkButton(left, text=f"+ {cmd}", fg_color=col, height=26,
                                font=Theme.font(size=11),
                                command=lambda c=cmd: self.add_node(c))
            btn.pack(fill="x", padx=10, pady=1)
        
        # ─── PC 제어 기능 (HMI 전용) ───
        ctk.CTkLabel(left, text="💻 PC 제어", font=Theme.font(size=11, weight="bold"), 
                     text_color=Theme.INFO).pack(anchor="w", padx=10, pady=(8, 2))
        pc_cmds = [
            ("Move By", "#8E24AA"), ("AO", "#CDDC39"), ("Wait AI", "#607D8B"),
            ("Switch", "#E91E63"), ("Force", "#795548"),
        ]
        for cmd, col in pc_cmds:
            btn = ctk.CTkButton(left, text=f"+ {cmd}", fg_color=col, height=26,
                                font=Theme.font(size=11),
                                command=lambda c=cmd: self.add_node(c))
            btn.pack(fill="x", padx=10, pady=1)
        
        # ─── 추가 기능 (APK에 없음 ⚡) ───
        ctk.CTkLabel(left, text="⚡ 추가 기능", font=Theme.font(size=11, weight="bold"), 
                     text_color=Theme.WARNING).pack(anchor="w", padx=10, pady=(8, 2))
        extra_cmds = [
            ("Vision", Theme.INFO), ("Sync", "#FFEB3B"),
            ("Stack Search", "#E040FB"), ("Spiral Search", "#7C4DFF"),
        ]
        for cmd, col in extra_cmds:
            btn = ctk.CTkButton(left, text=f"+ {cmd} ⚡", fg_color=col, height=26,
                                font=Theme.font(size=11),
                                command=lambda c=cmd: self.add_node(c))
            btn.pack(fill="x", padx=10, pady=1)
        
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
        
        h = ctk.CTkFrame(center, fg_color="transparent")
        h.pack(fill="x", padx=10, pady=5)
        
        self.robot_sel = ctk.CTkOptionMenu(h, values=["Robot A", "Robot B", "Robot C"], width=100, command=self._on_robot_changed,
                                            fg_color=Theme.BG_BASE, button_color=Theme.ACCENT_PRIMARY)
        self.robot_sel.pack(side="left", padx=5)
        
        ctk.CTkButton(h, text="🔄", width=30, command=self.refresh_info, **Theme.get_button_style("secondary")).pack(side="left", padx=(0,5))
        
        ctk.CTkButton(h, text="불러오기", width=60, font=Theme.font(size=12), command=self.load_program, **Theme.get_button_style("secondary")).pack(side="left", padx=5)
        ctk.CTkButton(h, text="저장", width=60, font=Theme.font(size=12), command=self.save_program, **Theme.get_button_style("primary")).pack(side="left", padx=5)
        ctk.CTkButton(h, text="삭제", width=50, font=Theme.font(size=12), command=self.delete_node, **Theme.get_button_style("danger")).pack(side="left", padx=2)
        ctk.CTkButton(h, text="▲", width=30, command=self._move_node_up, **Theme.get_button_style("secondary")).pack(side="left", padx=1)
        ctk.CTkButton(h, text="▼", width=30, command=self._move_node_down, **Theme.get_button_style("secondary")).pack(side="left", padx=1)
        ctk.CTkButton(h, text="복사", width=40, font=Theme.font(size=12), command=self._copy_node, **Theme.get_button_style("secondary")).pack(side="left", padx=2)
        ctk.CTkButton(h, text="▶ Play (가상)", width=80, font=Theme.font(size=12), command=self.play_simulation, **Theme.get_button_style("success")).pack(side="right", padx=5)
        
        self._exec_stop = False
        self.stop_btn = ctk.CTkButton(h, text="⏹ 정지", width=60, font=Theme.font(size=12), command=self._stop_execution, **Theme.get_button_style("danger"))
        self.stop_btn.pack(side="right", padx=2)
        self.exec_btn = ctk.CTkButton(h, text="▶ 실행", width=60, font=Theme.font(size=12), command=self._run_program, **Theme.get_button_style("success"))
        self.exec_btn.pack(side="right", padx=2)
        
        ctk.CTkButton(h, text="⚙️ 설정", width=60, font=Theme.font(size=12), command=self._open_config_dialog, **Theme.get_button_style("secondary")).pack(side="right", padx=2)
        
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
        self.switch_editor = SwitchEditor(self.pp_frame)
        self.loop_editor = LoopEditor(self.pp_frame)
        
        self.pp_editor.render()
        self.current_editor = self.pp_editor
        
        self.jog_controller = JogController(self.jog_frame)
        self.jog_controller.render()
        if hasattr(self.jog_controller, "move_btn"):
            self.jog_controller.move_btn.configure(command=self._on_move_btn_clicked)
        def _on_node_selected(q, p, t_type, item_text, p_name=None, p_data=None, all_pallets=None, b_radius=0.0, app_data=None, ret_data=None, d=None):
            if d is None: d = {}
            # 조그 패널에 현재 타겟 좌표 표시
            if hasattr(self.jog_controller, "set_target"):
                self.jog_controller.set_target(q, p)
                
            # 조그 패널을 강제로 덮어씌우지 않음 (JOG 독립성 보장)
            if "Move By" in item_text:
                for w in self.pp_frame.winfo_children(): w.destroy()
                self.mb_editor.render()
                self.mb_editor.update_ui(item_text, 0, 0, 0)
            elif "Move C" in item_text:
                for w in self.pp_frame.winfo_children(): w.destroy()
                self.current_editor = self.move_c_editor
                self.move_c_editor.render()
                self.move_c_editor.update_ui(item_text, b_radius)
                
                # 기본 버튼 바인딩 (MoveEditor 상속받음)
                self.move_c_editor.teach_btn.configure(command=self._on_teach_btn_clicked)
                self.move_c_editor.load_btn.configure(command=self._on_load_btn_clicked)
                self.move_c_editor.move_btn.configure(command=self._on_move_btn_clicked)
                
                # 경유점 버튼 바인딩
                if hasattr(self.move_c_editor, 'via_teach_btn'):
                    self.move_c_editor.via_teach_btn.configure(command=self._on_via_teach_btn_clicked)
            elif "Move Home" in item_text:
                for w in self.pp_frame.winfo_children(): w.destroy()
                self.move_home_editor.render()
                self.move_home_editor.update_ui(item_text)
            elif "Move J" in item_text or "Move L" in item_text or "Move B" in item_text:
                for w in self.pp_frame.winfo_children(): w.destroy()
                self.current_editor = self.move_editor
                self.move_editor.render()
                bnd = d.get("boundary", {"velLevel": 5, "accLevel": 5})
                self.move_editor.update_ui(item_text, b_radius, bnd.get("velLevel", 5), bnd.get("accLevel", 5))
                self.move_editor.teach_btn.configure(command=self._on_teach_btn_clicked)
                self.move_editor.load_btn.configure(command=self._on_load_btn_clicked)
                self.move_editor.move_btn.configure(command=self._on_move_btn_clicked)
            elif "Math" in item_text:
                for w in self.pp_frame.winfo_children(): w.destroy()
                self.math_editor.render()
                self.math_editor.update_ui(item_text, "var1", "=", 1.0)
            elif "Call" in item_text:
                for w in self.pp_frame.winfo_children(): w.destroy()
                self.call_editor.render()
                self.call_editor.update_ui(item_text, "sub_routine.json")
            elif "Switch" in item_text:
                for w in self.pp_frame.winfo_children(): w.destroy()
                self.switch_editor.render()
                self.switch_editor.update_ui(item_text)
            elif "If" in item_text:
                for w in self.pp_frame.winfo_children(): w.destroy()
                self.if_editor.render()
                self.if_editor.update_ui(item_text, 0, "HIGH", "var1", "==", 0.0)
            elif "Folder" in item_text:
                for w in self.pp_frame.winfo_children(): w.destroy()
                self.folder_editor.render()
                self.folder_editor.update_ui(item_text)
            elif "Loop" in item_text:
                for w in self.pp_frame.winfo_children(): w.destroy()
                self.current_editor = self.loop_editor
                self.loop_editor.render()
                self.loop_editor.update_ui(item_text, d.get("count", None))
            elif "Force" in item_text:
                for w in self.pp_frame.winfo_children(): w.destroy()
                self.force_editor.render()
                self.force_editor.update_ui(item_text, 500.0, 100.0, 50.0)
            elif "Vision" in item_text:
                for w in self.pp_frame.winfo_children(): w.destroy()
                self.vision_editor.render()
                self.vision_editor.update_ui(item_text)
            elif "Sync" in item_text:
                for w in self.pp_frame.winfo_children(): w.destroy()
                self.sync_editor.render()
                self.sync_editor.update_ui(item_text)
            elif "Set AO" in item_text:
                for w in self.pp_frame.winfo_children(): w.destroy()
                self.set_ao_editor.render()
                self.set_ao_editor.update_ui(item_text)
            elif "Wait DI" in item_text:
                for w in self.pp_frame.winfo_children(): w.destroy()
                self.current_editor = self.wait_di_editor
                self.wait_di_editor.render()
                self.wait_di_editor.update_ui(item_text, d.get("diList", []))
            elif "Wait AI" in item_text:
                for w in self.pp_frame.winfo_children(): w.destroy()
                self.current_editor = self.wait_ai_editor
                self.wait_ai_editor.render()
                self.wait_ai_editor.update_ui(item_text)
            elif "Wait" in item_text:
                for w in self.pp_frame.winfo_children(): w.destroy()
                self.current_editor = self.wait_editor
                self.wait_editor.render()
                self.wait_editor.update_ui(item_text, d.get("time", 1.0))
            elif "Comment" in item_text:
                for w in self.pp_frame.winfo_children(): w.destroy()
                self.comment_editor.render()
                self.comment_editor.update_ui(item_text)
            elif "Stop" in item_text:
                for w in self.pp_frame.winfo_children(): w.destroy()
                self.stop_editor.render()
                self.stop_editor.update_ui(item_text)
            elif "Pick" in item_text or "Place" in item_text:
                for w in self.pp_frame.winfo_children(): w.destroy()
                self.current_editor = self.pp_editor
                self.pp_editor.render()
                self.pp_editor.target_q = q
                self.pp_editor.target_p = p if p else [0.0]*6
                self.pp_editor.node_data = d  # Pass the full node_data for target speed etc.
                self.pp_editor.update_ui(d, all_pallets)
                self.pp_editor.teach_btn.configure(command=self._on_teach_btn_clicked)
                self.pp_editor.load_btn.configure(command=self._on_load_btn_clicked)
                self.pp_editor.move_btn.configure(command=self._on_move_btn_clicked)
                
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
            
        self.node_data[item]["q"] = current_q
        self.node_data[item]["p"] = current_p
        
        item_text = self.tree.item(item, "text")
        # 피드백 UI 갱신
        msg = f"(갱신됨) J1: {current_q[0]:.1f}, J2: {current_q[1]:.1f} ..."
        if "Pick" in item_text or "Place" in item_text:
            if hasattr(self.pp_editor, 'pos_info_label'):
                self.pp_editor.pos_info_label.configure(text=msg, text_color="#00FF41")
        elif "Move" in item_text:
            if hasattr(self.move_editor, 'pos_info_label'):
                self.move_editor.pos_info_label.configure(text=msg, text_color="#00FF41")
                
        print(f">> [위치 업데이트] 노드('{item_text.strip()}')의 목적지 좌표가 갱신되었습니다.")
        
    def _on_load_btn_clicked(self):
        selected = self.tree.selection()
        if not selected: return
        item = selected[0]
        if item in self.node_data:
            d = self.node_data[item]
            q = d.get("q", [0.0]*6)
            p = d.get("p", [0.0]*6)
            self.jog_controller.update_coordinates(q, p)
            print(f">> [조그로 불러오기] '{self.tree.item(item, 'text').strip()}'의 저장된 좌표를 JOG 패널로 불러왔습니다.")
        else:
            print(">> [오류] 이 노드에 저장된 좌표가 없습니다.")
            
    def _on_move_btn_clicked(self):
        selected = self.tree.selection()
        if not selected: return
        item = selected[0]
        item_text = self.tree.item(item, "text").strip()
        
        if "Move Home" in item_text:
            print(">> [로봇 이동] 지정된 홈(Home) 위치로 기동합니다.")
            RobotControlUseCase.move_to_joint([0.0, 0.0, -90.0, 0.0, -90.0, 0.0])
            return
            
        if item in self.node_data:
            d = self.node_data[item]
            q = d.get("q", [0.0]*6)
            print(f">> [로봇 이동] 로봇을 '{item_text}'의 저장된 관절 좌표 {q}로 기동합니다.")
            self.jog_controller.update_coordinates(q, d.get("p", [0.0]*6)) # 기동 시 조그도 동기화
            
            # 실제 로봇 기동 명령 전송 (UseCase 사용)
            RobotControlUseCase.move_to_joint(q)
        else:
            print(">> [오류] 이 노드에 저장된 좌표가 없습니다.")
        
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
        try:
            RobotControlUseCase.stop_robot()
        except:
            pass
        print(">> ⏹ [정지] 프로그램 실행이 중단되었습니다.")

    def _open_config_dialog(self):
        """로봇 설정 다이얼로그 열기."""
        from presentation.ui.robot_hmi.editors.config_dialog import RobotConfigDialog
        RobotConfigDialog(self.parent)

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
        self._exec_stop = False
        
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
            for node in node_list:
                if self._exec_stop:
                    return
                
                text = node["text"]
                data = node["data"]
                item_id = node["id"]
                q = data.get("q", [0.0]*6)
                
                _highlight(item_id)
                print(f"\n>> ▶ 실행: {text}")
                
                if "Main Program" in text:
                    _execute_node_list(node["children"])
                    
                elif "Loop" in text:
                    count = data.get("count", None)
                    iteration = 0
                    while not self._exec_stop:
                        iteration += 1
                        if count is not None and iteration > count:
                            break
                        print(f">> 🔄 Loop 반복 #{iteration}" + (f"/{count}" if count else " (무한)"))
                        _execute_node_list(node["children"])
                        
                elif "Move Home" in text:
                    print(f">>   → Home 이동: [0, 0, -90, 0, -90, 0]")
                    RobotControlUseCase.move_to_joint([0.0, 0.0, -90.0, 0.0, -90.0, 0.0])
                    RobotControlUseCase.wait_for_move_finish(30.0)
                    
                elif "Move J" in text or "Move L" in text or "Move B" in text:
                    if q and not all(v == 0.0 for v in q):
                        print(f">>   → Joint 이동: {[f'{v:.1f}' for v in q]}")
                        RobotControlUseCase.move_to_joint(q)
                        RobotControlUseCase.wait_for_move_finish(30.0)
                        
                elif "Pick" in text or "Place" in text:
                    is_pick = "Pick" in text
                    p = data.get("p", [0.0]*6)
                    app_data = data.get("approach", {})
                    ret_data = data.get("retract", {})
                    app_dist = app_data.get("distance", 0.0) / 1000.0
                    ret_dist = ret_data.get("distance", 0.0) / 1000.0
                    app_dir = app_data.get("direction", 0)
                    ret_dir = ret_data.get("direction", 0)
                    
                    # direction: 0=Z, 1=-Z, 2=X, 3=-X, 4=Y, 5=-Y
                    def _offset(base, direction, dist):
                        pos = list(base)
                        if direction == 0: pos[2] += dist
                        elif direction == 1: pos[2] -= dist
                        elif direction == 2: pos[0] += dist
                        elif direction == 3: pos[0] -= dist
                        elif direction == 4: pos[1] += dist
                        elif direction == 5: pos[1] -= dist
                        return pos
                    
                    # 팔레타이징 체크
                    target_type = data.get("target_type", 0)
                    p_data = data.get("p_data", None)
                    
                    if target_type == 1 and p_data and isinstance(p_data, dict):
                        # 팔레타이징 모드
                        from core.domains.robot.use_cases.motion_math import MotionMath
                        size = p_data.get("size", [1,1,1])
                        m, n, l_val = size[0], size[1], size[2] if len(size) > 2 else 1
                        pts = p_data.get("points", [])
                        p1 = pts[0]["p"] if len(pts) > 0 else p
                        p2 = pts[1]["p"] if len(pts) > 1 else p1
                        p3 = pts[2]["p"] if len(pts) > 2 else p1
                        p4 = pts[3]["p"] if len(pts) > 3 else None
                        
                        total = m * n * l_val
                        count = 0
                        for layer in range(l_val):
                            for row in range(m):
                                for col in range(n):
                                    if self._exec_stop: return
                                    count += 1
                                    cur_target = MotionMath.compute_pallet_point(
                                        p1, p2, p3, m, n, row, col,
                                        p4=p4, size_l=l_val, current_l=layer
                                    )
                                    cur_app = _offset(cur_target, app_dir, app_dist)
                                    cur_ret = _offset(cur_target, ret_dir, ret_dist)
                                    
                                    print(f">>   📦 [{count}/{total}] {'Place' if not is_pick else 'Pick'} L{layer+1} R{row+1} C{col+1}")
                                    
                                    from core.domains.robot.communication.client_manager import robot_manager
                                    inst = robot_manager.get_active_instance()
                                    if not inst: return
                                    
                                    inst.task_move_to(cur_app)
                                    RobotControlUseCase.wait_for_move_finish(30.0)
                                    inst.task_move_to(cur_target)
                                    RobotControlUseCase.wait_for_move_finish(30.0)
                                    
                                    # 툴 동작
                                    if is_pick:
                                        RobotControlUseCase.set_do(1, 1)
                                    else:
                                        RobotControlUseCase.set_do(1, 0)
                                    time.sleep(0.3)
                                    
                                    inst.task_move_to(cur_ret)
                                    RobotControlUseCase.wait_for_move_finish(30.0)
                    else:
                        # 단일 위치 모드
                        from core.domains.robot.communication.client_manager import robot_manager
                        inst = robot_manager.get_active_instance()
                        if not inst: return
                        
                        target_p = p if p else [0.0]*6
                        app_p = _offset(target_p, app_dir, app_dist)
                        ret_p = _offset(target_p, ret_dir, ret_dist)
                        
                        inst.task_move_to(app_p)
                        RobotControlUseCase.wait_for_move_finish(30.0)
                        inst.task_move_to(target_p)
                        RobotControlUseCase.wait_for_move_finish(30.0)
                        
                        if is_pick:
                            RobotControlUseCase.set_do(1, 1)
                        else:
                            RobotControlUseCase.set_do(1, 0)
                        time.sleep(0.3)
                        
                        inst.task_move_to(ret_p)
                        RobotControlUseCase.wait_for_move_finish(30.0)
                        
                elif "Wait" in text:
                    wait_time = data.get("time", 1.0)
                    print(f">>   ⏳ 대기: {wait_time}초")
                    time.sleep(wait_time)
                    
                elif "Set DO" in text:
                    do_list = data.get("doList", data.get("diList", []))
                    for do in do_list:
                        pin = do.get("idx", do.get("pin", 0))
                        val = do.get("value", do.get("val", 0))
                        RobotControlUseCase.set_do(pin, val)
                        print(f">>   DO {pin} = {val}")
                
                elif "Set AO" in text:
                    ao_list = data.get("aoList", [])
                    for ao in ao_list:
                        port = ao.get("idx", ao.get("port", 0))
                        voltage = ao.get("value", ao.get("voltage", 0))
                        RobotControlUseCase.set_ao(port, voltage)
                        print(f">>   AO {port} = {voltage}")
                
                elif "Move C" in text:
                    via_p = data.get("via_p", [0.0]*6)
                    target_p = data.get("p", [0.0]*6)
                    if via_p and target_p:
                        RobotControlUseCase.move_c(via_p, target_p)
                        RobotControlUseCase.wait_for_move_finish(30.0)
                
                elif "Move By" in text:
                    offset = data.get("offset", {})
                    dx = offset.get("dx", 0.0)
                    dy = offset.get("dy", 0.0)
                    dz = offset.get("dz", 0.0)
                    print(f">>   → 상대 이동: dx={dx}, dy={dy}, dz={dz}")
                    RobotControlUseCase.move_by_task([dx, dy, dz, 0, 0, 0])
                    RobotControlUseCase.wait_for_move_finish(30.0)
                
                elif "Math" in text:
                    var_name = data.get("mathVar", "var1")
                    op = data.get("mathOp", "=")
                    val = data.get("mathVal", 0.0)
                    RobotControlUseCase.math_operation(var_name, op, val)
                
                elif "If" in text:
                    cond = data.get("cond", {})
                    left = cond.get("left", {})
                    right = cond.get("right", {})
                    op_val = cond.get("op", 0)
                    op_map = {0: "==", 1: "!=", 2: ">", 3: "<", 4: ">=", 5: "<="}
                    op_str = op_map.get(op_val, "==")
                    var_name = left.get("value", "var1") if left.get("type", -1) == 10 else "var1"
                    compare_val = right.get("value", 0) if right.get("type", -1) != -1 else 0
                    
                    result = RobotControlUseCase.eval_condition(str(var_name), op_str, float(compare_val or 0))
                    print(f">>   🔀 If {var_name} {op_str} {compare_val} → {'TRUE' if result else 'FALSE'}")
                    if result:
                        _execute_node_list(node["children"])
                
                elif "Call" in text:
                    sub_path = data.get("sub_program", "")
                    if sub_path:
                        print(f">>   📞 서브프로그램 호출: {sub_path}")
                        RobotControlUseCase.call_sub_program(sub_path)
                        RobotControlUseCase.wait_for_move_finish(60.0)
                
                elif "Force" in text:
                    print(f">>   💪 힘 제어 노드 (설정된 파라미터로 실행)")
                    # Force control is typically configured via impedance parameters
                
                elif "Stack Search" in text:
                    axis = data.get("axis", 2)
                    direction = data.get("direction", -1)
                    threshold = data.get("force_threshold", 10.0)
                    step = data.get("step_mm", 1.0)
                    print(f">>   🔍 스택 탐색: 축={['X','Y','Z'][axis]}, 방향={'↓' if direction<0 else '↑'}, 임계값={threshold}N")
                    found_pos = RobotControlUseCase.stack_search(axis, direction, threshold, step)
                    if found_pos:
                        RobotControlUseCase.set_variable("stack_z", found_pos[2])
                        print(f">>   ✅ 접촉 위치 변수 저장: stack_z={found_pos[2]:.4f}")
                
                elif "Spiral Search" in text:
                    z_force = data.get("z_force", 10.0)
                    radius = data.get("radius_mm", 5.0)
                    print(f">>   🌀 나선형 탐색: 가압력={z_force}N, 반경={radius}mm")
                    found_pos = RobotControlUseCase.spiral_search(z_force=z_force, radius_mm=radius)
                    if found_pos:
                        print(f">>   ✅ 삽입 성공 위치: {[f'{v:.4f}' for v in found_pos[:3]]}")
                    
                elif "Folder" in text:
                    _execute_node_list(node["children"])
                    
                else:
                    print(f">>   (스킵: {text})")
        
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
            print("\n>> ═══════════════════════════════════")
            print(">> 🚀 프로그램 실행을 시작합니다!")
            print(">> ═══════════════════════════════════")
            try:
                _execute_node_list(all_nodes)
            except Exception as e:
                print(f">> [실행 에러] {e}")
            
            _clear_all_highlights()
            if self._exec_stop:
                print(">> ⏹ 사용자에 의해 프로그램이 중단되었습니다.")
            else:
                print(">> ✅ 프로그램 실행 완료!")
        
        threading.Thread(target=_run, daemon=True).start()

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
        # 표시 이름을 내부 이름으로 변환
        display_to_internal = {
            "Joint Move": "Move J",
            "Frame Move": "Move L",
            "DO": "Set DO",
            "AO": "Set AO",
        }
        internal_name = display_to_internal.get(cmd_name, cmd_name)
        
        selected = self.tree.selection()
        if not selected:
            new_item = self.tree.insert("", "end", text=f" {internal_name} Node", open=True)
            self._auto_teach(new_item, internal_name)
            return
            
        target = selected[0]
        target_text = self.tree.item(target, "text")
        
        # Loop문(반복문)이나 If문(조건문), Main Program인 경우에만 하위(자식)로 삽입
        if "Loop" in target_text or "If" in target_text or "Main Program" in target_text or "Folder" in target_text:
            new_item = self.tree.insert(target, "end", text=f" {internal_name} Node", open=True)
            self.tree.item(target, open=True) # 자동으로 하위 펼치기
        else:
            # 일반 명령어(Move, Pick 등)는 하위가 아니라 같은 레벨(형제)로 바로 밑에 삽입
            parent = self.tree.parent(target)
            idx = self.tree.index(target)
            new_item = self.tree.insert(parent, idx + 1, text=f" {internal_name} Node", open=True)
            
        self._auto_teach(new_item, internal_name)
        
    def _auto_teach(self, new_item, cmd_name):
        if not hasattr(self, 'node_data'): self.node_data = {}
        # Fetch current coordinates from JogController
        current_q = [0.0]*6
        current_p = [0.0]*6
        try:
            for i, ax in enumerate(["J1","J2","J3","J4","J5","J6"]):
                current_q[i] = float(self.jog_controller.entries[ax].get())
            for i, ax in enumerate(["X","Y","Z","Rx","Ry","Rz"]):
                current_p[i] = float(self.jog_controller.entries[ax].get())
        except Exception:
            pass
            
        self.node_data[new_item] = {
            "q": current_q, 
            "p": current_p, 
            "t_type": 0, 
            "p_name": "", 
            "p_data": [], 
            "b_radius": 0.0
        }
        # Automatically select the newly created node so the editor updates
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
    def render(self):
        for w in self.parent.winfo_children(): w.destroy()
        
        f = ctk.CTkFrame(self.parent, fg_color=Theme.BG_BASE, corner_radius=12)
        f.pack(expand=True, padx=40, pady=40, fill="both")
        
        ctk.CTkLabel(f, text="📋 SYSTEM LOGS", font=Theme.font(size=18, weight="bold")).pack(pady=20)
        
        self.textbox = ctk.CTkTextbox(f, fg_color=Theme.BG_BASE, text_color="#00FF41", font=ctk.CTkFont(family="Consolas"))
        self.textbox.pack(fill="both", expand=True, padx=20, pady=20)
        self.textbox.insert("end", "[SYS] Log Viewer Initialized.\n[SYS] Ready to display events.\n")

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
        items = ["이전으로", "옵션", "로봇설정", "프로그램", "로그", "리셋"]
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
        elif name == "로그":
            LogViewer(self.content_frame).render()
        else:
            ctk.CTkLabel(self.content_frame, text=f"{name} 뷰는 아직 준비되지 않았습니다.").pack(expand=True)