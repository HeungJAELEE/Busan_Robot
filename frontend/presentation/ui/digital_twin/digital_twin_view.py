import customtkinter as ctk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from matplotlib import colors as mcolors
from matplotlib import font_manager
from core.domains.robot.communication.client_manager import robot_manager
import math
from presentation.ui.theme import Theme
from presentation.ui.robot_hmi.robot_hmi_view import ProgramTreeEditor, RobotSettingsEditor
from core.domains.robot.use_cases.robot_control_usecase import RobotControlUseCase
from core.domains.robot.use_cases.factory_safety_zones import FactorySafetyZones
from core.domains.robot.use_cases.singularity_analyzer import SingularityAnalyzer
from core.runtime_config import plc_config, robot_defaults

class DigitalTwinView:
    def __init__(self, parent_tab):
        self.parent = parent_tab
        self.parent.grid_columnconfigure(0, weight=0, minsize=250)
        self.parent.grid_columnconfigure(1, weight=1)
        self.parent.grid_columnconfigure(2, weight=0, minsize=350)
        self.parent.grid_rowconfigure(0, weight=1)
        
        self.robot_arm_lines = {}
        self.robot_shadow_lines = {}
        self.robot_shell_lines = {}
        self.robot_joints_dots = {}
        self.robot_trails = {}
        self.robot_zone_scatters = {}
        self.robot_tcp_dots = {}
        self.robot_base_colors = {}
        self.robot_pos_labels = {}
        self.program_runners = {}
        self.program_runner_hosts = {}
        self.program_status_labels = {}
        self.program_status_boxes = {}
        self.program_toggle_buttons = {}
        self.executor = None
        
        self.history_x = {n: [] for n in ["Robot A", "Robot B", "Robot C"]}
        self.history_y = {n: [] for n in ["Robot A", "Robot B", "Robot C"]}
        self.history_z = {n: [] for n in ["Robot A", "Robot B", "Robot C"]}
        self.history_zone_colors = {n: [] for n in ["Robot A", "Robot B", "Robot C"]}
        self.last_singularity_guides = {}
        self.max_trail_points = 160
        self.zone_sample_distance_m = 0.02
        
        self.dh_params = [
            {"a": 0.0,    "alpha": 0.0,       "d": 0.3,    "theta_offset": 0.0},
            {"a": 0.0,    "alpha": np.pi/2,   "d": 0.0,    "theta_offset": np.pi/2},
            {"a": 0.45,   "alpha": 0.0,       "d": 0.0035, "theta_offset": np.pi/2},
            {"a": 0.0,    "alpha": np.pi/2,   "d": 0.35,   "theta_offset": np.pi},
            {"a": 0.0,    "alpha": np.pi/2,   "d": 0.1835, "theta_offset": 0.0},
            {"a": 0.0,    "alpha": -np.pi/2,  "d": 0.228,  "theta_offset": 0.0}
        ]
        
        # TCP offset (Tool Center Point) - loaded from JSON or default Indy7 gripper
        self.tcp_offset = np.array([0.0, 0.0, 0.21, 0.0, 0.0, 0.0])
        self.singularity_analyzer = SingularityAnalyzer(self.dh_params, self.tcp_offset)
        self.factory_safety_zones = FactorySafetyZones()
        
        self.setup_ui()
        self._init_3d_viewer()
        self._poll_program_status()
        
    def setup_ui(self):
        self.left_panel = ctk.CTkFrame(self.parent, corner_radius=12, **Theme.card_style())
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        ctk.CTkLabel(self.left_panel, text="QUICK CONTROLS", font=Theme.font(size=14, weight="bold"), text_color=Theme.TEXT_SECONDARY).pack(pady=(15, 10))
        
        self.robot_selector = ctk.CTkOptionMenu(self.left_panel, values=["Robot A", "Robot B", "Robot C"], command=self.change_target_robot)
        self.robot_selector.pack(pady=5, padx=20, fill="x")
        self.robot_selector.set("Robot A")
        
        ctk.CTkButton(self.left_panel, text="Home 위치", height=40, command=lambda: self._safe_action("go_home"), **Theme.get_button_style("primary")).pack(pady=5, padx=20, fill="x")
        ctk.CTkButton(self.left_panel, text="Zero 위치", height=40, command=lambda: self._safe_action("go_zero"), **Theme.get_button_style("secondary")).pack(pady=5, padx=20, fill="x")
        ctk.CTkButton(self.left_panel, text="에러 리셋", height=40, command=lambda: self._safe_action("reset_robot"), **Theme.get_button_style("secondary")).pack(pady=5, padx=20, fill="x")
        ctk.CTkButton(self.left_panel, text="궤적 초기화", height=34, command=self.clear_trajectories, **Theme.get_button_style("secondary")).pack(pady=5, padx=20, fill="x")
        ctk.CTkButton(self.left_panel, text="🚨 비상정지 (E-STOP)", height=50, font=ctk.CTkFont(weight="bold", size=15), fg_color="#D32F2F", hover_color="#B71C1C", command=self.emergency_stop).pack(pady=(15, 5), padx=20, fill="x")

        program_box = ctk.CTkFrame(self.left_panel, fg_color=Theme.BG_PANEL, corner_radius=8, border_width=1, border_color=Theme.BORDER)
        program_box.pack(fill="x", padx=15, pady=(10, 5))
        ctk.CTkLabel(program_box, text="PROGRAM RUN", font=Theme.font(size=13, weight="bold"), text_color=Theme.TEXT_SECONDARY).pack(pady=(10, 6))

        for name in ["Robot A", "Robot B", "Robot C"]:
            row = ctk.CTkFrame(program_box, fg_color="transparent")
            row.pack(fill="x", padx=8, pady=3)

            box = ctk.CTkFrame(row, width=10, height=10, corner_radius=2, fg_color="#A7AEA9")
            box.pack(side="left", padx=(0, 5))
            box.pack_propagate(False)

            ctk.CTkLabel(row, text=name.replace("Robot ", ""), width=18, font=ctk.CTkFont(size=12, weight="bold")).pack(side="left")
            status = ctk.CTkLabel(row, text="대기", width=48, font=Theme.font(size=11), text_color=Theme.TEXT_SECONDARY)
            status.pack(side="left", padx=4)

            toggle = ctk.CTkButton(
                row,
                text="동작",
                width=58,
                height=26,
                command=lambda n=name: self._toggle_saved_program(n),
                fg_color="#2E7D32",
                hover_color="#388E3C",
            )
            toggle.pack(side="left", padx=2)

            self.program_status_boxes[name] = box
            self.program_status_labels[name] = status
            self.program_toggle_buttons[name] = toggle

        batch = ctk.CTkFrame(program_box, fg_color="transparent")
        batch.pack(fill="x", padx=8, pady=(6, 10))
        ctk.CTkButton(batch, text="3대 동시 동작", height=28, command=self._run_all_saved_programs,
                      **Theme.get_button_style("success")).pack(side="left", expand=True, fill="x", padx=(0, 4))
        ctk.CTkButton(batch, text="3대 동시 정지", height=28, command=self._stop_all_saved_programs,
                      **Theme.get_button_style("danger")).pack(side="left", expand=True, fill="x", padx=(4, 0))
        
        self.right_panel = ctk.CTkFrame(self.parent, corner_radius=12, **Theme.card_style())
        self.right_panel.grid(row=0, column=2, sticky="nsew", padx=10, pady=10)
        ctk.CTkLabel(self.right_panel, text="TELEMETRY DATA", font=Theme.font(size=14, weight="bold"), text_color=Theme.TEXT_SECONDARY).pack(pady=15)
        
        task_box = ctk.CTkFrame(self.right_panel, fg_color=Theme.BG_PANEL, border_width=1, border_color=Theme.BORDER)
        task_box.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(task_box, text="TCP POS (Base ➔ Tool)").pack(anchor="w", padx=10, pady=5)
        self.task_label = ctk.CTkLabel(task_box, text="WAITING SIGNAL...", text_color="#73A5DD", font=ctk.CTkFont(family="Consolas", size=14, weight="bold"), justify="left")
        self.task_label.pack(anchor="w", padx=10, pady=(0, 10))

        joint_box = ctk.CTkFrame(self.right_panel, fg_color=Theme.BG_PANEL, border_width=1, border_color=Theme.BORDER)
        joint_box.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(joint_box, text="JOINT ANGLES (J1 ~ J6)").pack(anchor="w", padx=10, pady=5)
        self.joint_label = ctk.CTkLabel(joint_box, text="WAITING SIGNAL...", text_color="#68C596", font=ctk.CTkFont(family="Consolas", size=14, weight="bold"), justify="left")
        self.joint_label.pack(anchor="w", padx=10, pady=(0, 10))

        zone_box = ctk.CTkFrame(self.right_panel, fg_color=Theme.BG_PANEL, border_width=1, border_color=Theme.BORDER)
        zone_box.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(zone_box, text="SINGULARITY GUIDE ZONE").pack(anchor="w", padx=10, pady=5)
        self.singularity_label = ctk.CTkLabel(
            zone_box,
            text="녹색 <70 권장 안전\n주황 70~90 주의\n빨강 90~100 위험\nRail/Place 투명 존 표시",
            text_color=SingularityAnalyzer.COLOR_SAFE,
            font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
            justify="left",
        )
        self.singularity_label.pack(anchor="w", padx=10, pady=(0, 10))
        
        # 네트워크 및 연결 설정 추가
        ctk.CTkFrame(self.right_panel, height=2, fg_color=Theme.BORDER).pack(fill="x", padx=15, pady=15)
        self.network_editor = RobotSettingsEditor(self.right_panel)
        
        self.center_panel = ctk.CTkFrame(self.parent, corner_radius=12, **Theme.card_style())
        self.center_panel.grid(row=0, column=1, sticky="nsew", padx=5, pady=10)
        ctk.CTkLabel(self.center_panel, text="3D DIGITAL TWIN VIEWER (LIVE)", font=Theme.font(size=14, weight="bold"), text_color=Theme.TEXT_PRIMARY).pack(pady=10)
        
        self.viewer_container = ctk.CTkFrame(self.center_panel, fg_color=Theme.BG_CANVAS, border_width=1, border_color=Theme.BORDER)
        self.viewer_container.pack(fill="both", expand=True, padx=10, pady=10)
        
    def _init_3d_viewer(self):
        self.fig = plt.Figure(figsize=(8, 6), facecolor=Theme.BG_CANVAS)
        self.fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.ax.set_facecolor(Theme.BG_CANVAS)
        available_fonts = {font.name for font in font_manager.fontManager.ttflist}
        preferred_fonts = ["AppleGothic", "Malgun Gothic", "NanumGothic", "DejaVu Sans"]
        plt.rcParams["font.family"] = [font for font in preferred_fonts if font in available_fonts] or ["DejaVu Sans"]
        plt.rcParams["axes.unicode_minus"] = False
        
        for pane in (self.ax.xaxis, self.ax.yaxis, self.ax.zaxis):
            pane.set_pane_color((0.93, 0.94, 0.91, 1.0))
        
        self.ax.grid(color='#D5D9D2', linestyle=':', linewidth=0.5)
        self.ax.tick_params(colors=Theme.TEXT_SECONDARY, labelsize=8)
        self.ax.set_xlim([-0.8, 1.0])
        self.ax.set_ylim([-3.2, 2.5])
        self.ax.set_zlim([0, 1.2])
        self.ax.set_xlabel("Front X (m)", color=Theme.TEXT_SECONDARY)
        self.ax.set_ylabel("Robot Line Y (m)", color=Theme.TEXT_SECONDARY)
        self.ax.set_zlabel("Height Z (m)", color=Theme.TEXT_SECONDARY)
        self.ax.view_init(elev=24, azim=-30)
        self.ax.set_axis_off()
        
        self.robot_offsets = self.factory_safety_zones.robot_offsets_np()
        self._draw_process_scene()
        self._draw_static_safety_zones()

        color_map = {"Robot C": "#E07A73", "Robot B": "#73A5DD", "Robot A": "#68C596"}
        self.robot_base_colors = dict(color_map)
        
        label_frame = ctk.CTkFrame(self.center_panel, fg_color="transparent")
        label_frame.pack(side="bottom", fill="x", pady=5)

        for name in ["Robot A", "Robot B", "Robot C"]:
            col = color_map.get(name, "#FFFFFF")
            self.robot_shadow_lines[name], = self.ax.plot(
                [], [], [], '-',
                color="#B9C1BC",
                lw=13.5,
                alpha=0.82,
                solid_capstyle="round",
                zorder=7,
            )
            self.robot_shell_lines[name], = self.ax.plot(
                [], [], [], '-',
                color="#FDFDF9",
                lw=10.2,
                alpha=0.96,
                solid_capstyle="round",
                zorder=8,
            )
            self.robot_arm_lines[name], = self.ax.plot(
                [], [], [], '-',
                color=col,
                lw=1.1,
                alpha=0.58,
                solid_capstyle="round",
                zorder=9,
            )
            self.robot_joints_dots[name], = self.ax.plot([], [], [], 'o', color=col, markersize=8, markerfacecolor='#FDFDF9', markeredgecolor=col, markeredgewidth=1.6)
            self.robot_trails[name], = self.ax.plot([], [], [], color=col, alpha=0.38, lw=1.5, linestyle='--')
            self.robot_zone_scatters[name] = self.ax.scatter([], [], [], c=[], s=18, alpha=0.25, depthshade=False)
            self.robot_tcp_dots[name], = self.ax.plot([], [], [], 'o', color=col, markersize=9, markerfacecolor=col, markeredgecolor='white', markeredgewidth=1.2, alpha=0.9)
            
            wrapper = ctk.CTkFrame(label_frame, fg_color="transparent")
            wrapper.pack(side="left", expand=True)
            status_box = ctk.CTkFrame(wrapper, width=12, height=12, corner_radius=2, fg_color="#555555")
            status_box.pack(side="left", padx=5)
            status_box.pack_propagate(False)
            lbl = ctk.CTkLabel(wrapper, text=f"{name}: 연결 대기중", font=ctk.CTkFont(size=12, weight="bold"), text_color=col)
            lbl.pack(side="left")
            self.robot_pos_labels[name] = {"label": lbl, "box": status_box}
            
        self.robot_pos_labels["Robot A"]["box"].configure(fg_color="#68C596")
        self._draw_default_robot_poses()
            
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.viewer_container)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=2, pady=2)

    def _draw_process_scene(self):
        """Draw the Page 1 factory process scene: narrow rail, cars, stations."""
        y_values = [v[1] for v in self.factory_safety_zones.robot_offsets_m.values()]
        y_min = min(y_values) - self.factory_safety_zones.ROBOT_A_TO_RAIL_END_M
        y_max = max(y_values) + 0.55
        y_center = (y_min + y_max) / 2.0
        y_size = y_max - y_min
        rail_x = self.factory_safety_zones.RAIL_FRONT_DISTANCE_M
        rail_width = self.factory_safety_zones.RAIL_WIDTH_M

        self._add_box((rail_x, y_center, 0.015), (0.90, y_size + 0.28, 0.03), "#F9FAF7", alpha=0.34, edgecolor="#D5D9D2")
        for x in np.linspace(rail_x - 0.34, rail_x + 0.34, 7):
            self.ax.plot([x, x], [y_min, y_max], [0.047, 0.047], color="#CCD2CB", lw=0.8, alpha=0.85)

        self._add_box((rail_x, y_center, 0.085), (rail_width, y_size, 0.04), "#252B2A", alpha=0.95, edgecolor="#252B2A")
        guide_offset = rail_width / 2.0 + 0.045
        for x in (rail_x - guide_offset, rail_x + guide_offset):
            self._add_box((x, y_center, 0.12), (0.025, y_size + 0.08, 0.045), "#8B918D", alpha=0.95, edgecolor="#6E7671")
        for y in np.linspace(y_min + 0.15, y_max - 0.15, 18):
            self._add_box((rail_x, y, 0.145), (0.24, 0.025, 0.025), "#D7DDD6", alpha=0.95, edgecolor="#BFC7BF")

        stations = [
            ("Robot A", "차체 결합", -self.factory_safety_zones.ROBOT_SPACING_M, "#F0A09A"),
            ("Robot B", "전면 유리창 조립", 0.0, "#91B9E8"),
            ("Robot C", "양품 배출", self.factory_safety_zones.ROBOT_SPACING_M, "#8DD7B1"),
        ]
        display_labels = {
            "차체 결합": "Body Join",
            "전면 유리창 조립": "Glass Fit",
            "양품 배출": "Good Out",
        }
        for robot, label, y, color in stations:
            self._add_box((rail_x, y, 0.172), (0.26, 0.62, 0.012), color, alpha=0.16, edgecolor=color)
            self.ax.text(
                rail_x - 0.32,
                y - 0.24,
                0.36,
                f"{robot}\n{display_labels.get(label, label)}",
                color="#202524",
                fontsize=8,
                weight="bold",
            )
            self._add_robot_base((0.0, y, 0.0), color)

        self._add_toy_car(rail_x, -self.factory_safety_zones.ROBOT_SPACING_M, "#F0A09A", with_glass=False)
        self._add_toy_car(rail_x, 0.0, "#9DD2F0", with_glass=True)
        self._add_toy_car(rail_x, self.factory_safety_zones.ROBOT_SPACING_M, "#9AE3BC", with_glass=True)
        self._add_toy_car(rail_x, y_max - 0.10, "#F1C846", with_glass=True, scale=0.75)

        for y0, y1, color in [
            (y_min + 0.35, -self.factory_safety_zones.ROBOT_SPACING_M - 0.35, "#D79927"),
            (-0.95, 0.95, "#D79927"),
            (self.factory_safety_zones.ROBOT_SPACING_M - 0.55, y_max - 0.35, "#68C596"),
        ]:
            self.ax.quiver(rail_x + 0.22, y0, 0.24, 0, y1 - y0, 0, color=color, alpha=0.7, arrow_length_ratio=0.08, linewidth=1.2)

    def _add_toy_car(self, x, y, color, with_glass=True, scale=1.0):
        length = 0.30 * scale
        width = 0.16 * scale
        height = 0.065 * scale
        self._add_box((x, y, 0.22), (width, length, height), color, alpha=0.95, edgecolor="#BFC7BF")
        self._add_box((x - 0.01, y + 0.02 * scale, 0.27), (width * 0.72, length * 0.48, height * 0.75), color, alpha=0.92, edgecolor="#BFC7BF")
        if with_glass:
            self._add_box((x + 0.002, y - length * 0.03, 0.305), (width * 0.62, length * 0.17, height * 0.22), "#CFEFFF", alpha=0.7, edgecolor="#9ACCE7")
        for wx in (x - width * 0.45, x + width * 0.45):
            for wy in (y - length * 0.36, y + length * 0.36):
                self.ax.scatter([wx], [wy], [0.18], s=10 * scale, c="#59615F", depthshade=False)

    def _add_robot_base(self, center, accent_color):
        x, y, z = center
        self._add_cylinder_z((x, y, z + 0.035), 0.115, 0.07, "#FDFDF9", alpha=0.98, edgecolor="#BFC7BF")
        self._add_cylinder_z((x, y, z + 0.087), 0.078, 0.035, "#E9ECE7", alpha=0.98, edgecolor="#BFC7BF")
        self.ax.plot(
            [x - 0.095, x + 0.095],
            [y, y],
            [z + 0.11, z + 0.11],
            color=accent_color,
            alpha=0.65,
            lw=2.0,
        )

    def _add_cylinder_z(self, center, radius, height, color, alpha=1.0, edgecolor=None, segments=24):
        cx, cy, cz = center
        theta = np.linspace(0, 2 * np.pi, segments)
        z_vals = np.array([cz - height / 2.0, cz + height / 2.0])
        theta_grid, z_grid = np.meshgrid(theta, z_vals)
        x_grid = cx + radius * np.cos(theta_grid)
        y_grid = cy + radius * np.sin(theta_grid)
        surface = self.ax.plot_surface(
            x_grid,
            y_grid,
            z_grid,
            color=color,
            edgecolor=edgecolor or color,
            linewidth=0.25,
            alpha=alpha,
            shade=True,
        )
        return surface

    def _draw_default_robot_poses(self):
        defaults = {
            "Robot A": [7.7, -29.0, -87.2, 0.1, -64.3, 7.5],
            "Robot B": [-4.0, -33.7, -96.0, -28.6, -54.8, 13.0],
            "Robot C": [7.7, -29.0, -87.2, 0.1, -64.3, 7.5],
        }
        for name, joints in defaults.items():
            try:
                points, tcp = self._joint_points_world(name, joints)
                self.robot_shadow_lines[name].set_data(points[:, 0], points[:, 1])
                self.robot_shadow_lines[name].set_3d_properties(points[:, 2])
                self.robot_shell_lines[name].set_data(points[:, 0], points[:, 1])
                self.robot_shell_lines[name].set_3d_properties(points[:, 2])
                self.robot_arm_lines[name].set_data(points[:, 0], points[:, 1])
                self.robot_arm_lines[name].set_3d_properties(points[:, 2])
                joint_points = points[[0, 2, 3, 4, 5, 6]]
                self.robot_joints_dots[name].set_data(joint_points[:, 0], joint_points[:, 1])
                self.robot_joints_dots[name].set_3d_properties(joint_points[:, 2])
                self.robot_tcp_dots[name].set_data([tcp[0]], [tcp[1]])
                self.robot_tcp_dots[name].set_3d_properties([tcp[2]])
            except Exception:
                pass

    def _add_box(self, center, size, color, alpha=1.0, edgecolor=None, linewidth=0.45):
        faces = self._box_faces(center, size)
        collection = Poly3DCollection(
            faces,
            facecolors=color,
            edgecolors=edgecolor or color,
            linewidths=linewidth,
            alpha=alpha,
        )
        self.ax.add_collection3d(collection)
        return collection

    def _draw_static_safety_zones(self):
        for zone in self.factory_safety_zones.static_zone_boxes_m():
            zone_id = zone.get("id", "")
            if zone_id == "rail_body":
                continue
            if zone_id == "rail_keepout":
                self._draw_box_wireframe(zone["center"], zone["size"], zone["color"], alpha=0.13, linewidth=0.55)
                continue
            if zone_id.endswith("_place_watch"):
                self._draw_box_wireframe(zone["center"], zone["size"], zone["color"], alpha=0.18, linewidth=0.7)
                self._draw_floor_zone(zone["center"], zone["size"], zone["color"], alpha=0.045)
                continue
            self._draw_box_wireframe(zone["center"], zone["size"], zone["color"], alpha=0.09, linewidth=0.45)

    def _draw_floor_zone(self, center, size, color, alpha=0.05):
        cx, cy, _ = center
        sx, sy, _ = [float(v) / 2.0 for v in size]
        z = 0.175
        verts = [
            (cx - sx, cy - sy, z),
            (cx + sx, cy - sy, z),
            (cx + sx, cy + sy, z),
            (cx - sx, cy + sy, z),
        ]
        collection = Poly3DCollection(
            [verts],
            facecolors=mcolors.to_rgba(color, alpha),
            edgecolors=mcolors.to_rgba(color, min(alpha * 2.5, 0.16)),
            linewidths=0.45,
        )
        self.ax.add_collection3d(collection)

    def _draw_box_wireframe(self, center, size, color, alpha=0.12, linewidth=0.55):
        cx, cy, cz = center
        sx, sy, sz = [float(v) / 2.0 for v in size]
        corners = [
            (cx - sx, cy - sy, cz - sz), (cx + sx, cy - sy, cz - sz),
            (cx + sx, cy + sy, cz - sz), (cx - sx, cy + sy, cz - sz),
            (cx - sx, cy - sy, cz + sz), (cx + sx, cy - sy, cz + sz),
            (cx + sx, cy + sy, cz + sz), (cx - sx, cy + sy, cz + sz),
        ]
        edges = [
            (0, 1), (1, 2), (2, 3), (3, 0),
            (4, 5), (5, 6), (6, 7), (7, 4),
            (0, 4), (1, 5), (2, 6), (3, 7),
        ]
        for a, b in edges:
            xs = [corners[a][0], corners[b][0]]
            ys = [corners[a][1], corners[b][1]]
            zs = [corners[a][2], corners[b][2]]
            self.ax.plot(xs, ys, zs, color=color, alpha=alpha, lw=linewidth)

    @staticmethod
    def _box_faces(center, size):
        cx, cy, cz = center
        sx, sy, sz = [float(v) / 2.0 for v in size]
        corners = [
            (cx - sx, cy - sy, cz - sz), (cx + sx, cy - sy, cz - sz),
            (cx + sx, cy + sy, cz - sz), (cx - sx, cy + sy, cz - sz),
            (cx - sx, cy - sy, cz + sz), (cx + sx, cy - sy, cz + sz),
            (cx + sx, cy + sy, cz + sz), (cx - sx, cy + sy, cz + sz),
        ]
        return [
            [corners[i] for i in (0, 1, 2, 3)],
            [corners[i] for i in (4, 5, 6, 7)],
            [corners[i] for i in (0, 1, 5, 4)],
            [corners[i] for i in (2, 3, 7, 6)],
            [corners[i] for i in (1, 2, 6, 5)],
            [corners[i] for i in (0, 3, 7, 4)],
        ]
        
    def compute_forward_kinematics(self, joint_angles):
        T_matrices = [np.eye(4)] 
        T = np.eye(4)
        for i in range(6):
            theta = np.radians(joint_angles[i]) + self.dh_params[i]['theta_offset']
            a = self.dh_params[i]['a']
            alpha = self.dh_params[i]['alpha']
            d = self.dh_params[i]['d']
            ct, st = np.cos(theta), np.sin(theta)
            ca, sa = np.cos(alpha), np.sin(alpha)
            T_i = np.array([
                [           ct,            -st,   0,             a],
                [        st*ca,          ct*ca, -sa,         -d*sa],
                [        st*sa,          ct*sa,  ca,          d*ca],
                [            0,              0,   0,             1]
            ])
            T = T @ T_i 
            T_matrices.append(T)
        return T_matrices
        
    def clear_trajectories(self):
        for name in ["Robot A", "Robot B", "Robot C"]:
            self.history_x[name].clear()
            self.history_y[name].clear()
            self.history_z[name].clear()
            self.history_zone_colors[name].clear()
            if name in self.robot_trails:
                self.robot_trails[name].set_data([], [])
                self.robot_trails[name].set_3d_properties([])
            if name in self.robot_zone_scatters:
                self.robot_zone_scatters[name]._offsets3d = ([], [], [])
                self.robot_zone_scatters[name].set_color([])
        try:
            self.canvas.draw_idle()
        except Exception:
            pass

    def _joint_points_world(self, name, j_pos):
        try:
            T = self.compute_forward_kinematics(j_pos)
            offset_y = 0.1835  
            P0 = T[0][:3, 3]
            P1 = T[1][:3, 3] 
            P2 = (T[2] @ np.array([0, 0, offset_y, 1]))[:3] 
            P3 = (T[3] @ np.array([0, 0, offset_y, 1]))[:3] 
            P3_corner = T[3][:3, 3]
            P4 = T[4][:3, 3]
            P5 = T[5][:3, 3]
            P6_flange = T[6][:3, 3] 
            
            # Apply TCP offset to get actual tool tip position
            tcp_local = np.array([self.tcp_offset[0], self.tcp_offset[1], self.tcp_offset[2], 1.0])
            P6 = (T[6] @ tcp_local)[:3]

            offset = self.robot_offsets.get(name, np.array([0, 0, 0]))
            P0 += offset; P1 += offset; P2 += offset; P3 += offset; P3_corner += offset
            P4 += offset; P5 += offset; P6 += offset

            points = np.array([P0, P1, P2, P3, P3_corner, P4, P5, P6], dtype=float)
            return points, P6
        except Exception:
            raise

    def update_3d_graph(self, name, j_pos, task_pos=None):
        if not j_pos: return
        try:
            points, P6 = self._joint_points_world(name, j_pos)
            line_xs = points[:, 0].tolist()
            line_ys = points[:, 1].tolist()
            line_zs = points[:, 2].tolist()
            if name in self.robot_shadow_lines:
                self.robot_shadow_lines[name].set_data(line_xs, line_ys)
                self.robot_shadow_lines[name].set_3d_properties(line_zs)
            if name in self.robot_shell_lines:
                self.robot_shell_lines[name].set_data(line_xs, line_ys)
                self.robot_shell_lines[name].set_3d_properties(line_zs)
            self.robot_arm_lines[name].set_data(line_xs, line_ys)
            self.robot_arm_lines[name].set_3d_properties(line_zs)

            joint_points = points[[0, 2, 3, 4, 5, 6]]
            joint_xs = joint_points[:, 0].tolist()
            joint_ys = joint_points[:, 1].tolist()
            joint_zs = joint_points[:, 2].tolist()
            self.robot_joints_dots[name].set_data(joint_xs, joint_ys)
            self.robot_joints_dots[name].set_3d_properties(joint_zs)

            hx, hy, hz = self.history_x[name], self.history_y[name], self.history_z[name]
            hc = self.history_zone_colors[name]
            should_append = True
            if hx:
                dist = float(np.linalg.norm(np.array([P6[0]-hx[-1], P6[1]-hy[-1], P6[2]-hz[-1]])))
                should_append = dist > self.zone_sample_distance_m
            guide = self.last_singularity_guides.get(name)
            if should_append or not guide:
                singularity_guide = self.singularity_analyzer.analyze(j_pos, tcp_pos_m=P6)
                factory_guide = self.factory_safety_zones.evaluate_world_m(P6, name)
                guide = self.factory_safety_zones.combine(singularity_guide, factory_guide)
                self.last_singularity_guides[name] = guide
            zone_color = guide["color"]
            self.robot_tcp_dots[name].set_data([P6[0]], [P6[1]])
            self.robot_tcp_dots[name].set_3d_properties([P6[2]])
            self.robot_tcp_dots[name].set_color(self.robot_base_colors.get(name, "#FFFFFF"))
            self.robot_tcp_dots[name].set_markerfacecolor(self.robot_base_colors.get(name, "#FFFFFF"))
            self.robot_tcp_dots[name].set_markeredgecolor(zone_color)

            if should_append:
                hx.append(float(P6[0]))
                hy.append(float(P6[1]))
                hz.append(float(P6[2]))
                hc.append(zone_color)
                if len(hx) > self.max_trail_points:
                    del hx[:-self.max_trail_points]
                    del hy[:-self.max_trail_points]
                    del hz[:-self.max_trail_points]
                    del hc[:-self.max_trail_points]
                self.robot_trails[name].set_data(hx, hy)
                self.robot_trails[name].set_3d_properties(hz)
                if name in self.robot_zone_scatters:
                    self.robot_zone_scatters[name]._offsets3d = (hx, hy, hz)
                    self.robot_zone_scatters[name].set_color(hc)

            if name == robot_manager.get_active_robot_name() or name == self.robot_selector.get():
                self.singularity_label.configure(
                    text=(
                        f"{guide['label']}  risk={guide['score']:.0f}/100\n"
                        f"Sing={guide.get('singularity_score', guide['score']):.0f}  "
                        f"Zone={guide.get('factory_score', 0):.0f}\n"
                        f"Manip={guide.get('manipulability', 0):.4f}  "
                        f"Cond={guide.get('condition', 0):.1f}\n"
                        "Rail 550mm / 폭 100mm / Robot 간격 1850mm"
                    ),
                    text_color=zone_color,
                )

            self.canvas.draw_idle()
        except Exception as e:
            pass

    def change_target_robot(self, name):
        robot_manager.set_active_robot(name)
        print(f"\n>> 🎯 제어 타겟 로봇 변경: {name}")
        for n in ["Robot A", "Robot B", "Robot C"]:
            self.history_x[n].clear()
            self.history_y[n].clear()
            self.history_z[n].clear()
            if n in self.robot_pos_labels:
                box = self.robot_pos_labels[n]["box"]
                if n == name:
                    box.configure(fg_color="#68C596")
                else:
                    box.configure(fg_color="#555555")
                    
    def emergency_stop(self):
        print("\n🚨 [긴급] 사용자가 비상정지(E-STOP) 버튼을 눌렀습니다!")
        target = self.robot_selector.get()
        RobotControlUseCase.emergency_stop(target)
        print(f">> 🚨 {target} 정지 명령이 전송되었습니다.")

    def _safe_action(self, func_name):
        """IndyDCP 내부 lock이 thread-safety를 보장하므로 외부 lock 불필요"""
        target = self.robot_selector.get()
        action_map = {
            "go_home": RobotControlUseCase.go_home,
            "go_zero": RobotControlUseCase.go_zero,
            "reset_robot": RobotControlUseCase.reset_robot,
        }
        action = action_map.get(func_name)
        if action:
            action(target)
        else:
            # Fallback: 직접 inst 호출 (lock 없이 — IndyDCP 내부 lock이 보호)
            def _bg():
                info = robot_manager.get_robot_info(target)
                inst = info.get("instance") if info else None
                if inst:
                    try:
                        getattr(inst, func_name)()
                    except Exception as e:
                        print(f"❌ [에러] 명령 실행 실패: {e}")
            import threading
            threading.Thread(target=_bg, daemon=True).start()

    def _get_program_runner(self, name):
        runner = self.program_runners.get(name)
        if runner:
            return runner
        host = ctk.CTkFrame(self.parent, fg_color="transparent")
        self.program_runner_hosts[name] = host
        runner = ProgramTreeEditor(host)
        runner.current_robot = name
        self.program_runners[name] = runner
        return runner

    def _run_saved_program(self, name):
        info = robot_manager.get_robot_info(name)
        if not info or info.get("instance") is None:
            print(f">> [오류] {name} 로봇이 연결되지 않았습니다.")
            self._set_program_status(name, "미연결", "#F44336")
            return
        runner = self._get_program_runner(name)
        if runner.is_execution_running():
            print(f">> [경고] {name} 프로그램이 이미 실행 중입니다.")
            return
        print(f">> [Page 1] {name} 저장 JSON 프로그램 실행")
        runner.run_program_for_robot(name)
        self._set_program_status(name, "실행중", "#00E676")

    def _toggle_saved_program(self, name):
        runner = self.program_runners.get(name)
        if runner and runner.is_execution_running():
            self._stop_saved_program(name)
        else:
            self._run_saved_program(name)

    def _run_all_saved_programs(self):
        for name in ["Robot A", "Robot B", "Robot C"]:
            self._run_saved_program(name)

    def _stop_all_saved_programs(self):
        for name in ["Robot A", "Robot B", "Robot C"]:
            self._stop_saved_program(name)

    def _stop_saved_program(self, name):
        print(f">> [Page 1] {name} 프로그램 정지 요청")
        RobotControlUseCase.request_stop(name)
        runner = self.program_runners.get(name)
        if runner:
            runner.current_robot = name
            runner._stop_execution()
        else:
            RobotControlUseCase.emergency_stop(name)
        self._set_program_status(name, "정지", "#FF9800")

    def _set_program_status(self, name, text, color):
        label = self.program_status_labels.get(name)
        box = self.program_status_boxes.get(name)
        button = self.program_toggle_buttons.get(name)
        if label:
            label.configure(text=text, text_color=color)
        if box:
            box.configure(fg_color=color)
        if button:
            if text == "실행중":
                button.configure(text="정지", fg_color="#B71C1C", hover_color="#D32F2F")
            else:
                button.configure(text="동작", fg_color="#2E7D32", hover_color="#388E3C")

    def _poll_program_status(self):
        for name in ["Robot A", "Robot B", "Robot C"]:
            runner = self.program_runners.get(name)
            if runner and runner.is_execution_running():
                self._set_program_status(name, "실행중", "#00E676")
            elif RobotControlUseCase.is_stop_requested(name):
                self._set_program_status(name, "정지", "#FF9800")
            else:
                connected = robot_manager.is_connected(name)
                self._set_program_status(name, "대기", "#8B8B96" if connected else "#555555")
        try:
            self.parent.after(300, self._poll_program_status)
        except Exception:
            pass

    def _update_lamp(self, addr, state):
        color = "#424242" # Off
        if state == 1:
            if addr == "M102": color = "#F44336" # Red for Alarm
            elif addr in ["M100", "M105"]: color = "#2196F3" # Blue for Inputs
            else: color = "#4CAF50" # Green for Outputs
            
        if addr in self.lamps:
            self.lamps[addr].configure(fg_color=color)

    def _on_plc_state_change(self, addr, state):
        if hasattr(self.parent, "after"):
            self.parent.after(0, lambda: self._update_lamp(addr, state))

    def _start_auto_mode(self):
        from infrastructure.robot_control.conty_executor import ContyExecutor
        import os, json
        
        active_robot = robot_manager.get_active_robot_name()
        if not active_robot:
            print(">> [에러] 선택된 활성 로봇이 없습니다.")
            return
            
        config = plc_config()
        ip_entry = getattr(self, "plc_ip_entry", None)
        port_entry = getattr(self, "plc_port_entry", None)
        ip = ip_entry.get() if ip_entry else config["process_ip"]
        port = int(port_entry.get()) if port_entry else config["process_port"]
        robot_ip = robot_manager.get_all_robots().get(active_robot, {}).get("ip", "")
        if not robot_ip:
            robot_ip = robot_defaults().get(active_robot, {}).get("ip", "")
        
        # Load the latest program for the active robot
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
        path = os.path.join(base_dir, 'user_programs', active_robot.replace(" ", "_"), 'program.json')
        
        if not os.path.exists(path):
            print(f">> [에러] 프로그램 파일을 찾을 수 없습니다: {path}")
            return
            
        with open(path, "r", encoding="utf-8") as f:
            json_str = f.read()
            
        self.executor = ContyExecutor(robot_ip=robot_ip, plc_ip=ip, plc_port=port, robot_name=active_robot)
        self.executor.state_callback = self._on_plc_state_change
        
        if self.executor.connect():
            self.btn_auto_start.configure(state="disabled", fg_color="#424242")
            self.btn_auto_stop.configure(state="normal")
            print(">> [UI] PLC 연동 엔진 구동을 시작합니다.")
            self.executor.start_auto_mode(json_str)
        else:
            print(">> [에러] PLC 연동 엔진 연결에 실패했습니다.")

    def _stop_auto_mode(self):
        if self.executor:
            print(">> [UI] PLC 연동 엔진 구동을 정지합니다.")
            self.executor.stop()
            self.executor.disconnect()
            self.executor = None
            
        self.btn_auto_start.configure(state="normal", fg_color="#2E7D32")
        self.btn_auto_stop.configure(state="disabled")
        for addr in self.lamps:
            self._update_lamp(addr, 0)
