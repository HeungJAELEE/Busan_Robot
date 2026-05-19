import math


class FactorySafetyZones:
    """Lightweight advisory factory-layout zones for the 3D previews.

    These zones are visual guides only. They do not rewrite Conty JSON and do
    not replace the robot controller's collision detection or a MoveIt scene.
    """

    COLOR_SAFE = "#81C784"
    COLOR_WARN = "#FFB74D"
    COLOR_DANGER = "#EF5350"
    COLOR_RAIL = "#90A4AE"

    ROBOT_SPACING_M = 1.85
    RAIL_FRONT_DISTANCE_M = 0.55
    RAIL_WIDTH_M = 0.10
    ROBOT_A_TO_RAIL_END_M = 1.00

    PLACE_WATCH_LOCAL_M = (0.552, -0.099, 0.315)
    PLACE_WATCH_SIZE_M = (0.30, 0.30, 0.34)
    PLACE_WATCH_Z_RANGE_M = (0.22, 0.42)

    def __init__(self):
        self.robot_offsets_m = {
            "Robot A": (0.0, -self.ROBOT_SPACING_M, 0.0),
            "Robot B": (0.0, 0.0, 0.0),
            "Robot C": (0.0, self.ROBOT_SPACING_M, 0.0),
        }

    def robot_offsets_np(self):
        try:
            import numpy as np
            return {name: np.array(value, dtype=float) for name, value in self.robot_offsets_m.items()}
        except Exception:
            return dict(self.robot_offsets_m)

    def static_zone_boxes_m(self):
        """Return factory layout guide boxes in world meters."""
        ys = [v[1] for v in self.robot_offsets_m.values()]
        y_min = min(ys) - self.ROBOT_A_TO_RAIL_END_M
        y_max = max(ys) + 0.45
        y_center = (y_min + y_max) / 2.0
        y_size = y_max - y_min

        zones = [
            {
                "id": "rail_body",
                "label": "Rail 100mm",
                "center": (self.RAIL_FRONT_DISTANCE_M, y_center, 0.045),
                "size": (self.RAIL_WIDTH_M, y_size, 0.09),
                "color": self.COLOR_RAIL,
                "alpha": 0.22,
            },
            {
                "id": "rail_keepout",
                "label": "Rail clearance guide",
                "center": (self.RAIL_FRONT_DISTANCE_M, y_center, 0.36),
                "size": (0.36, y_size, 0.72),
                "color": self.COLOR_WARN,
                "alpha": 0.075,
            },
        ]

        for name, offset in self.robot_offsets_m.items():
            cx = offset[0] + self.PLACE_WATCH_LOCAL_M[0]
            cy = offset[1] + self.PLACE_WATCH_LOCAL_M[1]
            cz = self.PLACE_WATCH_LOCAL_M[2]
            zones.append({
                "id": f"{name.lower().replace(' ', '_')}_place_watch",
                "label": f"{name} Place watch",
                "center": (cx, cy, cz),
                "size": self.PLACE_WATCH_SIZE_M,
                "color": self.COLOR_DANGER if name == "Robot A" else self.COLOR_WARN,
                "alpha": 0.08 if name == "Robot A" else 0.045,
            })

        for lower, upper in (("Robot A", "Robot B"), ("Robot B", "Robot C")):
            y_mid = (self.robot_offsets_m[lower][1] + self.robot_offsets_m[upper][1]) / 2.0
            zones.append({
                "id": f"{lower[-1]}_{upper[-1]}_overlap",
                "label": f"{lower[-1]}/{upper[-1]} reach overlap",
                "center": (0.28, y_mid, 0.62),
                "size": (1.10, 0.28, 1.10),
                "color": self.COLOR_WARN,
                "alpha": 0.045,
            })
        return zones

    def static_zone_boxes_mm(self, robot_name="Robot A"):
        """Return local robot-frame boxes in millimeters for Page 2 preview."""
        zones = []
        for zone in self.static_zone_boxes_m():
            center = list(zone["center"])
            if zone["id"] in ("rail_body", "rail_keepout"):
                # Page 2 is a single-robot local preview. Show the rail in the
                # selected robot's local frame instead of the full three-robot row.
                center = [
                    self.RAIL_FRONT_DISTANCE_M,
                    0.0,
                    zone["center"][2],
                ]
                size = [zone["size"][0], 2.20, zone["size"][2]]
            elif zone["id"].endswith("_place_watch"):
                expected_id = f"{robot_name.lower().replace(' ', '_')}_place_watch"
                if zone["id"] != expected_id:
                    continue
                center = list(self.PLACE_WATCH_LOCAL_M)
                size = list(self.PLACE_WATCH_SIZE_M)
            else:
                continue
            zones.append({
                "id": zone["id"],
                "label": zone["label"],
                "center": [v * 1000.0 for v in center],
                "size": [v * 1000.0 for v in size],
                "color": zone["color"],
                "alpha": zone["alpha"],
            })
        return zones

    def evaluate_world_m(self, tcp_world_m, robot_name=None):
        if not tcp_world_m or len(tcp_world_m) < 3:
            return self._result(0.0, "factory_layout", "공장 존 영향 없음")
        try:
            px, py, pz = [float(v) for v in tcp_world_m[:3]]
        except (TypeError, ValueError):
            return self._result(0.0, "factory_layout", "공장 존 영향 없음")

        score = 0.0
        labels = []

        rail_score = self._rail_score(px, pz)
        if rail_score >= 70.0:
            labels.append("Rail 근접")
        score = max(score, rail_score)

        place_score = self._place_watch_score_world(px, py, pz, robot_name)
        if place_score >= 70.0:
            labels.append("Place 하강 주의")
        score = max(score, place_score)

        overlap_score = self._inter_robot_overlap_score(px, py, pz)
        if overlap_score >= 70.0:
            labels.append("로봇 간 작업영역 겹침")
        score = max(score, overlap_score)

        label = " / ".join(labels) if labels else "공장 존 영향 없음"
        return self._result(score, "factory_layout", label)

    def evaluate_local_mm(self, tcp_local_mm, robot_name="Robot A"):
        if not tcp_local_mm or len(tcp_local_mm) < 3:
            return self._result(0.0, "factory_layout_local", "공장 존 영향 없음")
        try:
            px, py, pz = [float(v) / 1000.0 for v in tcp_local_mm[:3]]
        except (TypeError, ValueError):
            return self._result(0.0, "factory_layout_local", "공장 존 영향 없음")
        offset = self.robot_offsets_m.get(robot_name, (0.0, 0.0, 0.0))
        return self.evaluate_world_m((px + offset[0], py + offset[1], pz + offset[2]), robot_name)

    @classmethod
    def combine(cls, singularity_guide, factory_guide):
        base = dict(singularity_guide or {})
        other = dict(factory_guide or {})
        base_score = float(base.get("score", 0.0) or 0.0)
        other_score = float(other.get("score", 0.0) or 0.0)
        if other_score > base_score:
            result = dict(base)
            result.update({
                "score": other_score,
                "level": other.get("level", "SAFE"),
                "label": other.get("label", "공장 존 영향 없음"),
                "color": other.get("color", cls.COLOR_SAFE),
                "source": other.get("source", "factory_layout"),
                "singularity_score": base_score,
                "factory_score": other_score,
                "singularity_label": base.get("label", ""),
                "factory_label": other.get("label", ""),
            })
            return result
        base["singularity_score"] = base_score
        base["factory_score"] = other_score
        base["singularity_label"] = base.get("label", "")
        base["factory_label"] = other.get("label", "")
        return base

    def _rail_score(self, x_m, z_m):
        # The rail is about 550mm in front of each robot and roughly 100mm
        # wide. Low TCP motion near that
        # line is advisory-warning because physical rail/object fixtures can
        # differ from the light HMI model.
        dx = abs(float(x_m) - self.RAIL_FRONT_DISTANCE_M)
        if z_m > 0.85:
            return 0.0
        if dx <= 0.07:
            return 90.0
        if dx <= 0.16:
            return 70.0 + (0.16 - dx) / 0.09 * 20.0
        return 0.0

    def _place_watch_score_world(self, x_m, y_m, z_m, robot_name=None):
        candidates = [robot_name] if robot_name in self.robot_offsets_m else list(self.robot_offsets_m.keys())
        best = 0.0
        for name in candidates:
            ox, oy, oz = self.robot_offsets_m[name]
            cx = ox + self.PLACE_WATCH_LOCAL_M[0]
            cy = oy + self.PLACE_WATCH_LOCAL_M[1]
            horizontal = math.hypot(x_m - cx, y_m - cy)
            z_min, z_max = self.PLACE_WATCH_Z_RANGE_M
            if horizontal <= 0.16 and z_min <= z_m <= z_max:
                best = max(best, 92.0)
            elif horizontal <= 0.22 and 0.18 <= z_m <= 0.48:
                best = max(best, 76.0)
        return best

    def _inter_robot_overlap_score(self, x_m, y_m, z_m):
        if z_m < 0.12 or z_m > 1.20 or x_m < -0.20 or x_m > 0.95:
            return 0.0
        boundaries = [
            (self.robot_offsets_m["Robot A"][1] + self.robot_offsets_m["Robot B"][1]) / 2.0,
            (self.robot_offsets_m["Robot B"][1] + self.robot_offsets_m["Robot C"][1]) / 2.0,
        ]
        best = 0.0
        for boundary in boundaries:
            dy = abs(y_m - boundary)
            if dy <= 0.10:
                best = max(best, 82.0)
            elif dy <= 0.20:
                best = max(best, 70.0)
        return best

    @classmethod
    def _result(cls, score, source, label):
        score = max(0.0, min(100.0, float(score or 0.0)))
        if score >= 90.0:
            level = "DANGER"
            color = cls.COLOR_DANGER
        elif score >= 70.0:
            level = "WARN"
            color = cls.COLOR_WARN
        else:
            level = "SAFE"
            color = cls.COLOR_SAFE
        return {
            "score": score,
            "level": level,
            "label": label,
            "color": color,
            "source": source,
        }
