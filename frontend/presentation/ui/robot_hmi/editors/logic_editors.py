import customtkinter as ctk
from .base_editor import BaseNodeEditor
from presentation.ui.theme import Theme


class SmartDOEditor:
    """SmartDO (type 4) — 디지털 출력 포트 설정"""
    def __init__(self, parent_frame): self.parent = parent_frame
    def render(self):
        for w in self.parent.winfo_children(): w.destroy()
        header = ctk.CTkFrame(self.parent, fg_color=Theme.BG_SURFACE, height=40)
        header.pack(fill="x")
        self.header_label = ctk.CTkLabel(header, text="디지털 출력(DO) 설정", font=Theme.font(size=16, weight="bold"), text_color="#4CAF50")
        self.header_label.pack(pady=10)
        main_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        main_frame.pack(fill="x", padx=10, pady=10)
        
        # DO 포트 1
        self.do_rows = []
        for i in range(2):
            frame = ctk.CTkFrame(main_frame, fg_color=Theme.BG_SURFACE)
            frame.pack(fill="x", pady=3)
            row = ctk.CTkFrame(frame, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=5)
            
            ctk.CTkLabel(row, text=f"DO {i+1}:", font=Theme.font(size=12, weight="bold")).pack(side="left", padx=5)
            ctk.CTkLabel(row, text="포트:").pack(side="left", padx=(10, 3))
            port_entry = ctk.CTkEntry(row, width=50)
            port_entry.insert(0, str(i))
            port_entry.pack(side="left", padx=3)
            
            ctk.CTkLabel(row, text="상태:").pack(side="left", padx=(10, 3))
            state_sel = ctk.CTkOptionMenu(row, values=["ON (1)", "OFF (0)"], width=85)
            state_sel.set("ON (1)")
            state_sel.pack(side="left", padx=3)
            
            enable_var = ctk.StringVar(value="on" if i == 0 else "off")
            enable_check = ctk.CTkCheckBox(row, text="사용", variable=enable_var, onvalue="on", offvalue="off", width=50)
            enable_check.pack(side="left", padx=(10, 5))
            
            self.do_rows.append({"port": port_entry, "state": state_sel, "enable": enable_var, "check": enable_check})
        
        ctk.CTkLabel(main_frame, text="💡 디지털 출력 포트의 ON/OFF를 설정합니다.\n그리퍼, 솔레노이드 밸브 등을 제어합니다.", 
                     text_color=Theme.TEXT_SECONDARY, font=Theme.font(size=11), justify="left", wraplength=300).pack(anchor="w", pady=10)
    
    def apply_changes(self, node_data):
        try:
            do_list = []
            for row in self.do_rows:
                if row["enable"].get() == "on":
                    port = int(row["port"].get())
                    value = 1 if "ON" in row["state"].get() else 0
                    do_list.append({"idx": port, "value": value})
            node_data["doList"] = do_list
        except Exception: pass
    
    def update_ui(self, node_name, doList=None):
        if self.header_label:
            name_only = node_name.replace("Node", "").strip()
            self.header_label.configure(text=f"사용자 {name_only} 설정")
        if not doList: doList = []
        for i, row in enumerate(self.do_rows):
            if i < len(doList):
                do = doList[i]
                row["port"].delete(0, "end")
                row["port"].insert(0, str(do.get("idx", i)))
                row["state"].set("ON (1)" if do.get("value", 0) else "OFF (0)")
                row["enable"].set("on")
                row["check"].select()
            else:
                row["enable"].set("off")
                row["check"].deselect()


class LoopEditor:
    def __init__(self, parent_frame):
        self.parent = parent_frame
        self.header_label = None
        
    def render(self):
        for w in self.parent.winfo_children(): w.destroy()
        header = ctk.CTkFrame(self.parent, fg_color=Theme.BG_SURFACE, height=40)
        header.pack(fill="x")
        self.header_label = ctk.CTkLabel(header, text="반복문(Loop) 설정", font=Theme.font(size=16, weight="bold"), text_color=Theme.DANGER)
        self.header_label.pack(pady=10)
        
        main_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        main_frame.pack(fill="x", padx=10, pady=10)
        
        row = ctk.CTkFrame(main_frame, fg_color="transparent")
        row.pack(fill="x", pady=5)
        ctk.CTkLabel(row, text="반복 횟수:").pack(side="left", padx=5)
        self.count_entry = ctk.CTkEntry(row, width=80, placeholder_text="무한")
        self.count_entry.pack(side="left", padx=5)
        ctk.CTkLabel(row, text="(비워두면 무한 반복)", text_color=Theme.TEXT_SECONDARY, font=Theme.font(size=11)).pack(side="left", padx=5)
        
        self.infinite_var = ctk.StringVar(value="on")
        self.inf_check = ctk.CTkCheckBox(main_frame, text="무한 반복 (∞)", variable=self.infinite_var, 
                                          onvalue="on", offvalue="off", command=self._toggle_infinite)
        self.inf_check.pack(anchor="w", pady=5)
        
        info = ctk.CTkLabel(main_frame, text="💡 Loop 노드 하위에 있는 모든 명령이\n설정된 횟수만큼 반복 실행됩니다.", 
                           text_color=Theme.TEXT_SECONDARY, font=Theme.font(size=11), justify="left")
        info.pack(anchor="w", pady=10)
    
    def _toggle_infinite(self):
        if self.infinite_var.get() == "on":
            self.count_entry.delete(0, "end")
            self.count_entry.configure(state="disabled", placeholder_text="무한")
        else:
            self.count_entry.configure(state="normal", placeholder_text="횟수 입력")
        
    def apply_changes(self, node_data):
        try:
            if self.infinite_var.get() == "on" or not self.count_entry.get().strip():
                node_data["count"] = None
            else:
                node_data["count"] = int(self.count_entry.get())
        except Exception:
            node_data["count"] = None
            
    def update_ui(self, node_name, count=None):
        if self.header_label:
            name_only = node_name.replace("Node", "").strip()
            self.header_label.configure(text=f"사용자 {name_only} 설정")
        if hasattr(self, 'count_entry'):
            self.count_entry.configure(state="normal")
            self.count_entry.delete(0, "end")
            if count is not None:
                self.count_entry.insert(0, str(count))
                self.infinite_var.set("off")
                self.inf_check.deselect()
            else:
                self.infinite_var.set("on")
                self.inf_check.select()
                self.count_entry.configure(state="disabled")




class MathEditor:
    def __init__(self, parent_frame):
        self.parent = parent_frame
        self.header_label = None
        
    def render(self):
        for w in self.parent.winfo_children(): w.destroy()
        header = ctk.CTkFrame(self.parent, fg_color=Theme.BG_SURFACE, height=40)
        header.pack(fill="x")
        self.header_label = ctk.CTkLabel(header, text="수학 연산(Math) 설정", font=Theme.font(size=16, weight="bold"), text_color="#FF5722")
        self.header_label.pack(pady=10)
        
        main_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        main_frame.pack(fill="x", padx=10, pady=20)
        
        row = ctk.CTkFrame(main_frame, fg_color="transparent")
        row.pack(fill="x", pady=10)
        
        ctk.CTkLabel(row, text="변수명:").pack(side="left", padx=5)
        self.var_entry = ctk.CTkEntry(row, width=100)
        self.var_entry.insert(0, "var1")
        self.var_entry.pack(side="left", padx=5)
        
        self.op_sel = ctk.CTkOptionMenu(row, values=["=", "+=", "-=", "*=", "/="], width=60)
        self.op_sel.pack(side="left", padx=5)
        
        self.val_entry = ctk.CTkEntry(row, width=80)
        self.val_entry.insert(0, "1")
        self.val_entry.pack(side="left", padx=5)

    def apply_changes(self, node_data):
        try:
            node_data["mathVar"] = self.var_entry.get()
            node_data["mathOp"] = self.op_sel.get()
            node_data["mathVal"] = float(self.val_entry.get())
        except Exception: pass

    def update_ui(self, node_name, var_name="var1", op="=", val=1.0):
        if self.header_label:
            name_only = node_name.replace("Node", "").strip()
            self.header_label.configure(text=f"사용자 {name_only} 설정")
        if hasattr(self, 'var_entry'):
            self.var_entry.delete(0, "end")
            self.var_entry.insert(0, str(var_name))
            self.op_sel.set(op)
            self.val_entry.delete(0, "end")
            self.val_entry.insert(0, str(val))

class CallEditor:
    def __init__(self, parent_frame):
        self.parent = parent_frame
        self.header_label = None
        
    def render(self):
        for w in self.parent.winfo_children(): w.destroy()
        header = ctk.CTkFrame(self.parent, fg_color=Theme.BG_SURFACE, height=40)
        header.pack(fill="x")
        self.header_label = ctk.CTkLabel(header, text="서브프로그램 호출(Call) 설정", font=Theme.font(size=16, weight="bold"), text_color=Theme.BG_SURFACE)
        self.header_label.pack(pady=10)
        
        main_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        main_frame.pack(fill="x", padx=10, pady=20)
        
        row = ctk.CTkFrame(main_frame, fg_color="transparent")
        row.pack(fill="x", pady=10)
        
        ctk.CTkLabel(row, text="프로그램 경로/이름:").pack(side="left", padx=5)
        self.prog_entry = ctk.CTkEntry(row, width=200)
        self.prog_entry.insert(0, "sub_routine.json")
        self.prog_entry.pack(side="left", padx=5)
        
        ctk.CTkButton(row, text="찾기", width=50).pack(side="left", padx=5)
        
    def update_ui(self, node_name, sub_program=""):
        if self.header_label:
            name_only = node_name.replace("Node", "").strip()
            self.header_label.configure(text=f"사용자 {name_only} 설정")
        if hasattr(self, 'prog_entry'):
            self.prog_entry.delete(0, "end")
            self.prog_entry.insert(0, str(sub_program))

class IfEditor:
    def __init__(self, parent_frame):
        self.parent = parent_frame
        self.header_label = None
        
    def render(self):
        for w in self.parent.winfo_children(): w.destroy()
        header = ctk.CTkFrame(self.parent, fg_color=Theme.BG_SURFACE, height=40)
        header.pack(fill="x")
        self.header_label = ctk.CTkLabel(header, text="조건문(If) 설정", font=Theme.font(size=16, weight="bold"), text_color="#E91E63")
        self.header_label.pack(pady=10)
        
        main_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        main_frame.pack(fill="x", padx=10, pady=10)
        
        # 1. DI Condition
        di_frame = ctk.CTkFrame(main_frame, fg_color=Theme.BG_SURFACE)
        di_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(di_frame, text="디지털 입력(DI) 조건", text_color=Theme.INFO).pack(anchor="w", padx=10, pady=5)
        
        row1 = ctk.CTkFrame(di_frame, fg_color="transparent")
        row1.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row1, text="포트 번호:").pack(side="left", padx=5)
        self.di_port_entry = ctk.CTkEntry(row1, width=60)
        self.di_port_entry.insert(0, "0")
        self.di_port_entry.pack(side="left", padx=5)
        
        ctk.CTkLabel(row1, text="상태:").pack(side="left", padx=5)
        self.di_state_sel = ctk.CTkOptionMenu(row1, values=["HIGH", "LOW"], width=80)
        self.di_state_sel.pack(side="left", padx=5)
        
        # 2. Variable Condition
        var_frame = ctk.CTkFrame(main_frame, fg_color=Theme.BG_SURFACE)
        var_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(var_frame, text="변수 비교 조건", text_color=Theme.WARNING).pack(anchor="w", padx=10, pady=5)
        
        row2 = ctk.CTkFrame(var_frame, fg_color="transparent")
        row2.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row2, text="변수명:").pack(side="left", padx=5)
        self.var_entry = ctk.CTkEntry(row2, width=80)
        self.var_entry.insert(0, "var1")
        self.var_entry.pack(side="left", padx=5)
        
        self.op_sel = ctk.CTkOptionMenu(row2, values=["==", ">", "<", ">=", "<=", "!="], width=60)
        self.op_sel.pack(side="left", padx=5)
        
        self.val_entry = ctk.CTkEntry(row2, width=60)
        self.val_entry.insert(0, "0")
        self.val_entry.pack(side="left", padx=5)
        
    def apply_changes(self, node_data):
        try:
            if "cond" not in node_data: node_data["cond"] = {"right": {}}
            op_map_rev = {"==": 0, "!=": 1, ">": 2, "<": 3, ">=": 4, "<=": 5}
            node_data["cond"]["op"] = op_map_rev.get(self.op_sel.get(), 0)
            node_data["cond"]["right"]["value"] = float(self.val_entry.get())
            # For simplicity, saving the variable part in custom fields
            node_data["di_port"] = int(self.di_port_entry.get())
        except Exception: pass

    def update_ui(self, node_name, di_port=0, di_state="HIGH", var_name="var1", op="==", val=0.0):
        if self.header_label:
            name_only = node_name.replace("Node", "").strip()
            self.header_label.configure(text=f"사용자 {name_only} 설정")
        if hasattr(self, 'di_port_entry'):
            self.di_port_entry.delete(0, "end")
            self.di_port_entry.insert(0, str(di_port))
            self.di_state_sel.set(di_state)
            self.var_entry.delete(0, "end")
            self.var_entry.insert(0, str(var_name))
            self.op_sel.set(op)
            self.val_entry.delete(0, "end")
            self.val_entry.insert(0, str(val))

class WaitEditor:
    def __init__(self, parent_frame): self.parent = parent_frame
    def render(self):
        for w in self.parent.winfo_children(): w.destroy()
        header = ctk.CTkFrame(self.parent, fg_color=Theme.BG_SURFACE, height=40)
        header.pack(fill="x")
        self.header_label = ctk.CTkLabel(header, text="대기 시간(Wait) 설정", font=Theme.font(size=16, weight="bold"), text_color="#607D8B")
        self.header_label.pack(pady=10)
        main_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        main_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(main_frame, text="대기 시간 (초):").pack(anchor="w")
        self.time_entry = ctk.CTkEntry(main_frame)
        self.time_entry.insert(0, "1.0")
        self.time_entry.pack(fill="x", pady=5)
        
    def apply_changes(self, node_data):
        try:
            node_data["time"] = float(self.time_entry.get())
        except Exception: pass
        
    def update_ui(self, node_name, time_val=1.0):
        if self.header_label:
            name_only = node_name.replace("Node", "").strip()
            self.header_label.configure(text=f"사용자 {name_only} 설정")
        if hasattr(self, 'time_entry'):
            self.time_entry.delete(0, "end")
            self.time_entry.insert(0, str(time_val))

class WaitDIEditor:
    def __init__(self, parent_frame): self.parent = parent_frame
    def render(self):
        for w in self.parent.winfo_children(): w.destroy()
        header = ctk.CTkFrame(self.parent, fg_color=Theme.BG_SURFACE, height=40)
        header.pack(fill="x")
        self.header_label = ctk.CTkLabel(header, text="디지털 입력 대기(Wait DI)", font=Theme.font(size=16, weight="bold"), text_color="#607D8B")
        self.header_label.pack(pady=10)
        main_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        main_frame.pack(fill="x", padx=10, pady=10)
        
        # DI 포트 번호
        row1 = ctk.CTkFrame(main_frame, fg_color="transparent")
        row1.pack(fill="x", pady=5)
        ctk.CTkLabel(row1, text="DI 포트 번호:").pack(side="left", padx=5)
        self.port_entry = ctk.CTkEntry(row1, width=60)
        self.port_entry.insert(0, "0")
        self.port_entry.pack(side="left", padx=5)
        
        # ON/OFF 상태
        ctk.CTkLabel(row1, text="대기 상태:").pack(side="left", padx=(15, 5))
        self.state_sel = ctk.CTkOptionMenu(row1, values=["ON (1)", "OFF (0)"], width=90)
        self.state_sel.set("ON (1)")
        self.state_sel.pack(side="left", padx=5)
        
        # 타임아웃
        row2 = ctk.CTkFrame(main_frame, fg_color="transparent")
        row2.pack(fill="x", pady=5)
        ctk.CTkLabel(row2, text="타임아웃 (초):").pack(side="left", padx=5)
        self.time_entry = ctk.CTkEntry(row2, width=60)
        self.time_entry.insert(0, "1")
        self.time_entry.pack(side="left", padx=5)
        ctk.CTkLabel(row2, text="(0 = 무제한 대기)", text_color=Theme.TEXT_SECONDARY, font=Theme.font(size=10)).pack(side="left", padx=5)
        
        ctk.CTkLabel(main_frame, text="💡 지정한 DI 포트가 설정 상태가 될 때까지 대기합니다.\n타임아웃 시간이 지나면 다음 명령으로 넘어갑니다.", 
                     text_color=Theme.TEXT_SECONDARY, font=Theme.font(size=11), justify="left", wraplength=300).pack(anchor="w", pady=10)
        
    def apply_changes(self, node_data):
        try:
            port = int(self.port_entry.get())
            value = 1 if "ON" in self.state_sel.get() else 0
            node_data["diList"] = [{"idx": port, "value": value}]
            node_data["time"] = float(self.time_entry.get())
        except Exception: pass
        
    def update_ui(self, node_name, diList=None, time_val=1.0):
        if self.header_label:
            name_only = node_name.replace("Node", "").strip()
            self.header_label.configure(text=f"사용자 {name_only} 설정")
        if hasattr(self, 'port_entry'):
            self.port_entry.delete(0, "end")
            port = 0
            value = 1
            if diList and len(diList) > 0:
                port = diList[0].get("idx", 0)
                value = diList[0].get("value", 1)
            self.port_entry.insert(0, str(port))
            self.state_sel.set("ON (1)" if value else "OFF (0)")
        if hasattr(self, 'time_entry'):
            self.time_entry.delete(0, "end")
            self.time_entry.insert(0, str(time_val))

class WaitAIEditor:
    def __init__(self, parent_frame): self.parent = parent_frame
    def render(self):
        for w in self.parent.winfo_children(): w.destroy()
        header = ctk.CTkFrame(self.parent, fg_color=Theme.BG_SURFACE, height=40)
        header.pack(fill="x")
        ctk.CTkLabel(header, text="아날로그 입력 대기(Wait AI)", font=Theme.font(size=16, weight="bold"), text_color="#607D8B").pack(pady=10)
        main_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        main_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(main_frame, text="포트 번호 (AI):").pack(anchor="w")
        ctk.CTkEntry(main_frame).pack(fill="x", pady=5)
        ctk.CTkLabel(main_frame, text="전압 (V):").pack(anchor="w", pady=(10,0))
        ctk.CTkEntry(main_frame).pack(fill="x", pady=5)
    def apply_changes(self, node_data): pass
    def update_ui(self, node_name): pass

class CommentEditor:
    def __init__(self, parent_frame): self.parent = parent_frame
    def render(self):
        for w in self.parent.winfo_children(): w.destroy()
        header = ctk.CTkFrame(self.parent, fg_color=Theme.BG_SURFACE, height=40)
        header.pack(fill="x")
        ctk.CTkLabel(header, text="주석(Comment)", font=Theme.font(size=16, weight="bold"), text_color="#9E9E9E").pack(pady=10)
        ctk.CTkTextbox(self.parent, height=100).pack(fill="x", padx=10, pady=10)
    def apply_changes(self, node_data): pass
    def update_ui(self, node_name): pass

class StopEditor:
    def __init__(self, parent_frame): self.parent = parent_frame
    def render(self):
        for w in self.parent.winfo_children(): w.destroy()
        header = ctk.CTkFrame(self.parent, fg_color=Theme.BG_SURFACE, height=40)
        header.pack(fill="x")
        ctk.CTkLabel(header, text="프로그램 정지(Stop)", font=Theme.font(size=16, weight="bold"), text_color=Theme.DANGER).pack(pady=10)
        ctk.CTkLabel(self.parent, text="도달 시 프로그램 실행을 완전히 종료합니다.").pack(pady=20)
    def apply_changes(self, node_data): pass
    def update_ui(self, node_name): pass

class SwitchEditor:
    def __init__(self, parent_frame): self.parent = parent_frame
    def render(self):
        for w in self.parent.winfo_children(): w.destroy()
        header = ctk.CTkFrame(self.parent, fg_color=Theme.BG_SURFACE, height=40)
        header.pack(fill="x")
        ctk.CTkLabel(header, text="다중 분기(Switch) 설정", font=Theme.font(size=16, weight="bold"), text_color="#E91E63").pack(pady=10)
        
        main_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        main_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(main_frame, text="비교 변수명:").pack(anchor="w")
        self.var_entry = ctk.CTkEntry(main_frame)
        self.var_entry.insert(0, "var1")
        self.var_entry.pack(fill="x", pady=5)
    def apply_changes(self, node_data): pass
    def update_ui(self, node_name): pass

class FolderEditor:
    def __init__(self, parent_frame): self.parent = parent_frame
    def render(self):
        for w in self.parent.winfo_children(): w.destroy()
        header = ctk.CTkFrame(self.parent, fg_color=Theme.BG_SURFACE, height=40)
        header.pack(fill="x")
        ctk.CTkLabel(header, text="폴더(Folder/Group)", font=Theme.font(size=16, weight="bold"), text_color=Theme.WARNING).pack(pady=10)
        ctk.CTkLabel(self.parent, text="하위 명령어를 묶어서 관리하는 그룹 노드입니다.").pack(pady=20)
    def apply_changes(self, node_data): pass
    def update_ui(self, node_name): pass


class WaitForEditor:
    """조건 기반 대기 (waitFor) — 변수 조건이 충족될 때까지 대기"""
    def __init__(self, parent_frame): self.parent = parent_frame
    def render(self):
        for w in self.parent.winfo_children(): w.destroy()
        header = ctk.CTkFrame(self.parent, fg_color=Theme.BG_SURFACE, height=40)
        header.pack(fill="x")
        self.header_label = ctk.CTkLabel(header, text="조건 대기(WaitFor) 설정", font=Theme.font(size=16, weight="bold"), text_color="#26A69A")
        self.header_label.pack(pady=10)
        main = ctk.CTkFrame(self.parent, fg_color="transparent")
        main.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(main, text="대기 조건 타입:", font=Theme.font(size=12, weight="bold")).pack(anchor="w", pady=(0,5))
        self.cond_type = ctk.CTkOptionMenu(main, values=["변수 조건", "타이머", "DI 신호"], width=150)
        self.cond_type.pack(fill="x", pady=3)
        row = ctk.CTkFrame(main, fg_color="transparent")
        row.pack(fill="x", pady=8)
        ctk.CTkLabel(row, text="변수명:").pack(side="left", padx=5)
        self.var_entry = ctk.CTkEntry(row, width=80)
        self.var_entry.insert(0, "var1")
        self.var_entry.pack(side="left", padx=5)
        self.op_sel = ctk.CTkOptionMenu(row, values=["==", ">", "<", ">=", "<=", "!="], width=60)
        self.op_sel.pack(side="left", padx=5)
        self.val_entry = ctk.CTkEntry(row, width=60)
        self.val_entry.insert(0, "1")
        self.val_entry.pack(side="left", padx=5)
        row2 = ctk.CTkFrame(main, fg_color="transparent")
        row2.pack(fill="x", pady=5)
        ctk.CTkLabel(row2, text="타임아웃 (초):").pack(side="left", padx=5)
        self.timeout_entry = ctk.CTkEntry(row2, width=80)
        self.timeout_entry.insert(0, "0")
        self.timeout_entry.pack(side="left", padx=5)
        ctk.CTkLabel(row2, text="(0 = 무제한)", text_color=Theme.TEXT_SECONDARY, font=Theme.font(size=10)).pack(side="left", padx=5)
        ctk.CTkLabel(main, text="💡 설정한 조건이 충족될 때까지 프로그램 실행을 일시 중지합니다.", text_color=Theme.TEXT_SECONDARY, font=Theme.font(size=11), wraplength=300, justify="left").pack(anchor="w", pady=10)
    def apply_changes(self, node_data):
        try:
            node_data["condType"] = self.cond_type.get()
            node_data["condVar"] = self.var_entry.get()
            op_map = {"==": 0, "!=": 1, ">": 2, "<": 3, ">=": 4, "<=": 5}
            node_data["condOp"] = op_map.get(self.op_sel.get(), 0)
            node_data["condVal"] = float(self.val_entry.get())
            node_data["timeout"] = float(self.timeout_entry.get())
        except Exception: pass
    def update_ui(self, node_name, cond_type="변수 조건", var="var1", op="==", val=1, timeout=0):
        if hasattr(self, 'header_label'):
            self.header_label.configure(text=f"조건 대기(WaitFor) 설정")
        if hasattr(self, 'cond_type'): self.cond_type.set(cond_type)
        if hasattr(self, 'var_entry'):
            self.var_entry.delete(0, "end"); self.var_entry.insert(0, str(var))
            self.op_sel.set(op)
            self.val_entry.delete(0, "end"); self.val_entry.insert(0, str(val))
            self.timeout_entry.delete(0, "end"); self.timeout_entry.insert(0, str(timeout))


class LoopBreakEditor:
    """루프 탈출(loopBreak) — 현재 실행 중인 루프를 즉시 탈출"""
    def __init__(self, parent_frame): self.parent = parent_frame
    def render(self):
        for w in self.parent.winfo_children(): w.destroy()
        header = ctk.CTkFrame(self.parent, fg_color=Theme.BG_SURFACE, height=40)
        header.pack(fill="x")
        ctk.CTkLabel(header, text="루프 탈출(Loop Break)", font=Theme.font(size=16, weight="bold"), text_color="#EF5350").pack(pady=10)
        main = ctk.CTkFrame(self.parent, fg_color="transparent")
        main.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(main, text="⚠️ 이 노드에 도달하면 현재 실행 중인\n가장 안쪽 Loop를 즉시 탈출합니다.", font=Theme.font(size=13), text_color=Theme.WARNING, justify="left").pack(anchor="w", pady=10)
        ctk.CTkLabel(main, text="💡 일반적으로 If 조건문 내부에 배치하여\n특정 조건 충족 시 루프를 종료합니다.", text_color=Theme.TEXT_SECONDARY, font=Theme.font(size=11), justify="left", wraplength=300).pack(anchor="w", pady=5)
    def apply_changes(self, node_data): pass
    def update_ui(self, node_name): pass


class SpeedRatioEditor:
    """속도 비율(speedRatio) — 프로그램 실행 속도 비율 설정"""
    def __init__(self, parent_frame): self.parent = parent_frame
    def render(self):
        for w in self.parent.winfo_children(): w.destroy()
        header = ctk.CTkFrame(self.parent, fg_color=Theme.BG_SURFACE, height=40)
        header.pack(fill="x")
        self.header_label = ctk.CTkLabel(header, text="속도 비율(Speed Ratio) 설정", font=Theme.font(size=16, weight="bold"), text_color="#FFB300")
        self.header_label.pack(pady=10)
        main = ctk.CTkFrame(self.parent, fg_color="transparent")
        main.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(main, text="속도 비율 (%):", font=Theme.font(size=12, weight="bold")).pack(anchor="w")
        self.ratio_slider = ctk.CTkSlider(main, from_=1, to=100, number_of_steps=99)
        self.ratio_slider.set(100)
        self.ratio_slider.pack(fill="x", pady=5)
        self.ratio_label = ctk.CTkLabel(main, text="100%", font=Theme.font(size=18, weight="bold"), text_color=Theme.SUCCESS)
        self.ratio_label.pack(pady=5)
        self.ratio_slider.configure(command=self._on_slider)
        ctk.CTkLabel(main, text="💡 이 노드 이후의 모든 모션 명령에\n설정된 속도 비율이 적용됩니다.", text_color=Theme.TEXT_SECONDARY, font=Theme.font(size=11), justify="left", wraplength=300).pack(anchor="w", pady=10)
    def _on_slider(self, val):
        v = int(val)
        self.ratio_label.configure(text=f"{v}%")
    def apply_changes(self, node_data):
        try: node_data["prgSpdRatio"] = int(self.ratio_slider.get())
        except: pass
    def update_ui(self, node_name, ratio=100):
        if hasattr(self, 'ratio_slider'):
            self.ratio_slider.set(ratio)
            self.ratio_label.configure(text=f"{ratio}%")


class ToolSensingEditor:
    """도구 센서 읽기(toolSensing) — 도구에 부착된 센서 값을 읽어 변수에 저장"""
    def __init__(self, parent_frame): self.parent = parent_frame
    def render(self):
        for w in self.parent.winfo_children(): w.destroy()
        header = ctk.CTkFrame(self.parent, fg_color=Theme.BG_SURFACE, height=40)
        header.pack(fill="x")
        self.header_label = ctk.CTkLabel(header, text="도구 센서(Tool Sensing) 설정", font=Theme.font(size=16, weight="bold"), text_color="#42A5F5")
        self.header_label.pack(pady=10)
        main = ctk.CTkFrame(self.parent, fg_color="transparent")
        main.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(main, text="센서 이름:", font=Theme.font(size=12)).pack(anchor="w")
        self.sens_entry = ctk.CTkEntry(main, width=200)
        self.sens_entry.insert(0, "sensor1")
        self.sens_entry.pack(fill="x", pady=5)
        ctk.CTkLabel(main, text="저장 변수명:", font=Theme.font(size=12)).pack(anchor="w", pady=(8,0))
        self.var_entry = ctk.CTkEntry(main, width=200)
        self.var_entry.insert(0, "sensVal")
        self.var_entry.pack(fill="x", pady=5)
        ctk.CTkLabel(main, text="센서 타입:", font=Theme.font(size=12)).pack(anchor="w", pady=(8,0))
        self.type_sel = ctk.CTkOptionMenu(main, values=["DI (디지털)", "AI (아날로그)", "F/T (힘/토크)"], width=180)
        self.type_sel.pack(fill="x", pady=5)
        ctk.CTkLabel(main, text="💡 도구(엔드이펙터)에 부착된 센서 값을\n지정된 변수에 저장합니다.", text_color=Theme.TEXT_SECONDARY, font=Theme.font(size=11), justify="left", wraplength=300).pack(anchor="w", pady=10)
    def apply_changes(self, node_data):
        try:
            node_data["sensName"] = self.sens_entry.get()
            node_data["sensVar"] = self.var_entry.get()
            node_data["sensType"] = self.type_sel.get()
        except: pass
    def update_ui(self, node_name, sens="sensor1", var="sensVal", stype="DI (디지털)"):
        if hasattr(self, 'sens_entry'):
            self.sens_entry.delete(0, "end"); self.sens_entry.insert(0, sens)
            self.var_entry.delete(0, "end"); self.var_entry.insert(0, var)
            self.type_sel.set(stype)


class ConveyorTrackingEditor:
    """컨베이어 추적(conveyorTracking) — 이동 중인 컨베이어와 동기화"""
    def __init__(self, parent_frame): self.parent = parent_frame
    def render(self):
        for w in self.parent.winfo_children(): w.destroy()
        header = ctk.CTkFrame(self.parent, fg_color=Theme.BG_SURFACE, height=40)
        header.pack(fill="x")
        self.header_label = ctk.CTkLabel(header, text="컨베이어 추적(Conveyor Tracking)", font=Theme.font(size=16, weight="bold"), text_color="#FFEB3B")
        self.header_label.pack(pady=10)
        main = ctk.CTkFrame(self.parent, fg_color="transparent")
        main.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(main, text="트래킹 모드:", font=Theme.font(size=12)).pack(anchor="w")
        self.mode_sel = ctk.CTkOptionMenu(main, values=["시작(Start)", "종료(Stop)"], width=150)
        self.mode_sel.pack(fill="x", pady=5)
        ctk.CTkLabel(main, text="컨베이어 속도 (mm/s):", font=Theme.font(size=12)).pack(anchor="w", pady=(8,0))
        self.speed_entry = ctk.CTkEntry(main, width=120)
        self.speed_entry.insert(0, "100")
        self.speed_entry.pack(fill="x", pady=5)
        ctk.CTkLabel(main, text="엔코더 채널:", font=Theme.font(size=12)).pack(anchor="w", pady=(8,0))
        self.encoder_sel = ctk.CTkOptionMenu(main, values=["CH 0", "CH 1"], width=100)
        self.encoder_sel.pack(fill="x", pady=5)
        ctk.CTkLabel(main, text="💡 이동 중인 컨베이어 벨트 위의 물체를\n추적하면서 Pick/Place를 수행합니다.", text_color=Theme.TEXT_SECONDARY, font=Theme.font(size=11), justify="left", wraplength=300).pack(anchor="w", pady=10)
    def apply_changes(self, node_data):
        try:
            node_data["trackMode"] = 0 if "시작" in self.mode_sel.get() else 1
            node_data["convSpeed"] = float(self.speed_entry.get())
            node_data["encoderCh"] = int(self.encoder_sel.get().replace("CH ", ""))
        except: pass
    def update_ui(self, node_name, mode=0, speed=100, ch=0):
        if hasattr(self, 'mode_sel'):
            self.mode_sel.set("시작(Start)" if mode == 0 else "종료(Stop)")
            self.speed_entry.delete(0, "end"); self.speed_entry.insert(0, str(speed))
            self.encoder_sel.set(f"CH {ch}")


class TaktTimeEditor:
    """indyCARE 택타임(TaktTime) — 사이클 택타임 모니터링 및 제어"""
    def __init__(self, parent_frame): self.parent = parent_frame
    def render(self):
        for w in self.parent.winfo_children(): w.destroy()
        header = ctk.CTkFrame(self.parent, fg_color=Theme.BG_SURFACE, height=40)
        header.pack(fill="x")
        self.header_label = ctk.CTkLabel(header, text="indyCARE 택타임(TaktTime)", font=Theme.font(size=16, weight="bold"), text_color="#AB47BC")
        self.header_label.pack(pady=10)
        main = ctk.CTkFrame(self.parent, fg_color="transparent")
        main.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(main, text="택타임 모드:", font=Theme.font(size=12)).pack(anchor="w")
        self.mode_sel = ctk.CTkOptionMenu(main, values=["시작(Start)", "종료(Stop)", "리셋(Reset)"], width=150)
        self.mode_sel.pack(fill="x", pady=5)
        ctk.CTkLabel(main, text="목표 택타임 (초):", font=Theme.font(size=12)).pack(anchor="w", pady=(8,0))
        self.target_entry = ctk.CTkEntry(main, width=120)
        self.target_entry.insert(0, "10.0")
        self.target_entry.pack(fill="x", pady=5)
        ctk.CTkLabel(main, text="💡 프로그램 사이클의 택타임(Takt Time)을\n측정하고 모니터링합니다.\nindyCARE 시스템과 연동됩니다.", text_color=Theme.TEXT_SECONDARY, font=Theme.font(size=11), justify="left", wraplength=300).pack(anchor="w", pady=10)
    def apply_changes(self, node_data):
        try:
            modes = {"시작(Start)": 0, "종료(Stop)": 1, "리셋(Reset)": 2}
            node_data["careTackTime"] = modes.get(self.mode_sel.get(), 0)
            node_data["targetTakt"] = float(self.target_entry.get())
        except: pass
    def update_ui(self, node_name, mode=0, target=10.0):
        if hasattr(self, 'mode_sel'):
            modes = {0: "시작(Start)", 1: "종료(Stop)", 2: "리셋(Reset)"}
            self.mode_sel.set(modes.get(mode, "시작(Start)"))
            self.target_entry.delete(0, "end"); self.target_entry.insert(0, str(target))


class DetectEditor:
    """감지(detect) — 비전/센서 기반 물체 감지"""
    def __init__(self, parent_frame): self.parent = parent_frame
    def render(self):
        for w in self.parent.winfo_children(): w.destroy()
        header = ctk.CTkFrame(self.parent, fg_color=Theme.BG_SURFACE, height=40)
        header.pack(fill="x")
        self.header_label = ctk.CTkLabel(header, text="물체 감지(Detect) 설정", font=Theme.font(size=16, weight="bold"), text_color="#29B6F6")
        self.header_label.pack(pady=10)
        main = ctk.CTkFrame(self.parent, fg_color="transparent")
        main.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(main, text="감지 소스:", font=Theme.font(size=12)).pack(anchor="w")
        self.source_sel = ctk.CTkOptionMenu(main, values=["카메라(Vision)", "F/T 센서", "DI 신호", "AI 센서"], width=150)
        self.source_sel.pack(fill="x", pady=5)
        ctk.CTkLabel(main, text="결과 저장 변수:", font=Theme.font(size=12)).pack(anchor="w", pady=(8,0))
        self.result_entry = ctk.CTkEntry(main, width=200)
        self.result_entry.insert(0, "detectResult")
        self.result_entry.pack(fill="x", pady=5)
        ctk.CTkLabel(main, text="💡 비전 카메라 또는 센서를 통해 물체를\n감지하고 결과를 변수에 저장합니다.", text_color=Theme.TEXT_SECONDARY, font=Theme.font(size=11), justify="left", wraplength=300).pack(anchor="w", pady=10)
    def apply_changes(self, node_data):
        try:
            node_data["detectSource"] = self.source_sel.get()
            node_data["detectResult"] = self.result_entry.get()
        except: pass
    def update_ui(self, node_name, source="카메라(Vision)", result="detectResult"):
        if hasattr(self, 'source_sel'):
            self.source_sel.set(source)
            self.result_entry.delete(0, "end"); self.result_entry.insert(0, result)


class RetrieveEditor:
    """데이터 회수(retrieve) — 외부 소스에서 데이터를 가져와 변수에 저장"""
    def __init__(self, parent_frame): self.parent = parent_frame
    def render(self):
        for w in self.parent.winfo_children(): w.destroy()
        header = ctk.CTkFrame(self.parent, fg_color=Theme.BG_SURFACE, height=40)
        header.pack(fill="x")
        self.header_label = ctk.CTkLabel(header, text="데이터 회수(Retrieve) 설정", font=Theme.font(size=16, weight="bold"), text_color="#66BB6A")
        self.header_label.pack(pady=10)
        main = ctk.CTkFrame(self.parent, fg_color="transparent")
        main.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(main, text="데이터 소스:", font=Theme.font(size=12)).pack(anchor="w")
        self.source_sel = ctk.CTkOptionMenu(main, values=["로봇 상태", "센서 데이터", "외부 통신", "PLC"], width=150)
        self.source_sel.pack(fill="x", pady=5)
        ctk.CTkLabel(main, text="저장 변수명:", font=Theme.font(size=12)).pack(anchor="w", pady=(8,0))
        self.var_entry = ctk.CTkEntry(main, width=200)
        self.var_entry.insert(0, "retrievedData")
        self.var_entry.pack(fill="x", pady=5)
        ctk.CTkLabel(main, text="💡 외부 소스에서 데이터를 가져와\n프로그램 변수에 저장합니다.", text_color=Theme.TEXT_SECONDARY, font=Theme.font(size=11), justify="left", wraplength=300).pack(anchor="w", pady=10)
    def apply_changes(self, node_data):
        try:
            node_data["retrieveSource"] = self.source_sel.get()
            node_data["retrieveVar"] = self.var_entry.get()
        except: pass
    def update_ui(self, node_name, source="로봇 상태", var="retrievedData"):
        if hasattr(self, 'source_sel'):
            self.source_sel.set(source)
            self.var_entry.delete(0, "end"); self.var_entry.insert(0, var)


class PythonScriptEditor:
    """파이썬 스크립트(pythonScript) — 사용자 정의 파이썬 코드 실행"""
    def __init__(self, parent_frame): self.parent = parent_frame
    def render(self):
        for w in self.parent.winfo_children(): w.destroy()
        header = ctk.CTkFrame(self.parent, fg_color=Theme.BG_SURFACE, height=40)
        header.pack(fill="x")
        self.header_label = ctk.CTkLabel(header, text="파이썬 스크립트(Python Script)", font=Theme.font(size=16, weight="bold"), text_color="#FFA726")
        self.header_label.pack(pady=10)
        main = ctk.CTkFrame(self.parent, fg_color="transparent")
        main.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(main, text="스크립트 파일:", font=Theme.font(size=12)).pack(anchor="w")
        row = ctk.CTkFrame(main, fg_color="transparent")
        row.pack(fill="x", pady=5)
        self.file_entry = ctk.CTkEntry(row, width=200)
        self.file_entry.insert(0, "script.py")
        self.file_entry.pack(side="left", fill="x", expand=True, padx=(0,5))
        ctk.CTkButton(row, text="찾기", width=50).pack(side="left")
        ctk.CTkLabel(main, text="인라인 코드:", font=Theme.font(size=12)).pack(anchor="w", pady=(8,0))
        self.code_text = ctk.CTkTextbox(main, height=120, font=("Courier", 12))
        self.code_text.pack(fill="x", pady=5)
        self.code_text.insert("1.0", "# 여기에 파이썬 코드를 입력하세요\nprint('Hello from Indy7!')")
        ctk.CTkLabel(main, text="💡 로봇 실행 중 사용자 정의 파이썬 코드를\n실행합니다. 변수 접근 및 I/O 제어가 가능합니다.", text_color=Theme.TEXT_SECONDARY, font=Theme.font(size=11), justify="left", wraplength=300).pack(anchor="w", pady=10)
    def apply_changes(self, node_data):
        try:
            node_data["scriptFile"] = self.file_entry.get()
            node_data["scriptCode"] = self.code_text.get("1.0", "end-1c")
        except: pass
    def update_ui(self, node_name, script_file="script.py", code=""):
        if hasattr(self, 'file_entry'):
            self.file_entry.delete(0, "end"); self.file_entry.insert(0, script_file)
        if hasattr(self, 'code_text') and code:
            self.code_text.delete("1.0", "end")
            self.code_text.insert("1.0", code)