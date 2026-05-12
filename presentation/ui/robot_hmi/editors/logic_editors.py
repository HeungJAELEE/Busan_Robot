import customtkinter as ctk
from .base_editor import BaseNodeEditor
from presentation.ui.theme import Theme


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
        ctk.CTkLabel(main_frame, text="포트 번호 (DI):").pack(anchor="w")
        self.port_entry = ctk.CTkEntry(main_frame)
        self.port_entry.insert(0, "0")
        self.port_entry.pack(fill="x", pady=5)
        
    def apply_changes(self, node_data):
        try:
            port = int(self.port_entry.get())
            if "diList" not in node_data: node_data["diList"] = []
            if len(node_data["diList"]) > 0:
                node_data["diList"][0]["idx"] = port
            else:
                node_data["diList"].append({"idx": port, "value": 1})
        except Exception: pass
        
    def update_ui(self, node_name, diList=None):
        if self.header_label:
            name_only = node_name.replace("Node", "").strip()
            self.header_label.configure(text=f"사용자 {name_only} 설정")
        if hasattr(self, 'port_entry'):
            self.port_entry.delete(0, "end")
            port = 0
            if diList and len(diList) > 0:
                port = diList[0].get("idx", 0)
            self.port_entry.insert(0, str(port))

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