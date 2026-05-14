import math

import numpy as np


class SingularityAnalyzer:
    """Singularity risk guide for Indy7-like 6-axis motion previews.

    This is intentionally advisory. It never blocks or rewrites teaching data.
    Joint angles use the current HMI DH model when available; TCP-only samples
    fall back to a conservative workspace-boundary estimate.
    """

    COLOR_SAFE = "#81C784"
    COLOR_WARN = "#FFB74D"
    COLOR_DANGER = "#EF5350"

    DEFAULT_DH = [
        {"a": 0.0, "alpha": 0.0, "d": 0.3, "theta_offset": 0.0},
        {"a": 0.0, "alpha": math.pi / 2, "d": 0.0, "theta_offset": math.pi / 2},
        {"a": 0.45, "alpha": 0.0, "d": 0.0035, "theta_offset": math.pi / 2},
        {"a": 0.0, "alpha": math.pi / 2, "d": 0.35, "theta_offset": math.pi},
        {"a": 0.0, "alpha": math.pi / 2, "d": 0.1835, "theta_offset": 0.0},
        {"a": 0.0, "alpha": -math.pi / 2, "d": 0.228, "theta_offset": 0.0},
    ]

    def __init__(self, dh_params=None, tcp_offset=None):
        self.dh_params = dh_params or self.DEFAULT_DH
        tcp_offset = tcp_offset if tcp_offset is not None else [0.0, 0.0, 0.21, 0.0, 0.0, 0.0]
        self.tcp_offset = np.array(list(tcp_offset[:3]) + [1.0], dtype=float)
        self._cache = {}
        self._cache_limit = 4096

    def analyze(self, joint_angles=None, tcp_pos_mm=None, tcp_pos_m=None):
        q = self._clean_q(joint_angles)
        if q:
            key = ("q", tuple(round(v, 1) for v in q))
            return self._cached(key, lambda: self._analyze_joint(q))
        p_mm = self._tcp_mm(tcp_pos_mm=tcp_pos_mm, tcp_pos_m=tcp_pos_m)
        key = ("tcp", tuple(round(v / 20.0) for v in p_mm[:3])) if p_mm else ("tcp", None)
        return self._cached(key, lambda: self._analyze_tcp(tcp_pos_mm=p_mm))

    def _cached(self, key, factory):
        if key in self._cache:
            return dict(self._cache[key])
        value = factory()
        if len(self._cache) >= self._cache_limit:
            self._cache.clear()
        self._cache[key] = dict(value)
        return value

    def _analyze_joint(self, q):
        manip = 0.0
        sigma_min = 0.0
        condition = 0.0
        manip_score = 0.0
        try:
            jac_t = self.translational_jacobian(q)
            singular_values = np.linalg.svd(jac_t, compute_uv=False)
            manip = float(np.prod(singular_values))
            sigma_min = float(singular_values[-1])
            condition = float(singular_values[0] / max(sigma_min, 1e-9))
            manip_score = self._manipulability_score(manip, condition)
        except Exception:
            pass

        wrist_score = self._angle_singularity_score(q[4], red_deg=8.0, warn_deg=25.0)
        elbow_score = self._angle_singularity_score(q[2], red_deg=8.0, warn_deg=22.0) * 0.85
        score = max(manip_score, wrist_score, elbow_score)
        return self._result(score, "joint_jacobian", manip, sigma_min, condition)

    def _analyze_tcp(self, tcp_pos_mm=None, tcp_pos_m=None):
        p_mm = self._tcp_mm(tcp_pos_mm=tcp_pos_mm, tcp_pos_m=tcp_pos_m)
        score = 0.0
        radius = None
        z = None
        if p_mm:
            radius = math.sqrt((p_mm[0] ** 2) + (p_mm[1] ** 2) + (p_mm[2] ** 2))
            z = p_mm[2]
            if radius >= 900.0:
                score = 95.0
            elif radius >= 760.0:
                score = 70.0 + (radius - 760.0) / 140.0 * 20.0
            if z < 40.0:
                score = max(score, 78.0)
        result = self._result(score, "tcp_workspace_hint", 0.0, 0.0, 0.0)
        result["tcp_radius_mm"] = radius
        result["tcp_z_mm"] = z
        return result

    def forward_kinematics(self, q):
        transforms = [np.eye(4)]
        t = np.eye(4)
        for idx, q_deg in enumerate(q[:6]):
            param = self.dh_params[idx]
            theta = math.radians(float(q_deg)) + float(param["theta_offset"])
            a = float(param["a"])
            alpha = float(param["alpha"])
            d = float(param["d"])
            ct, st = math.cos(theta), math.sin(theta)
            ca, sa = math.cos(alpha), math.sin(alpha)
            t_i = np.array([
                [ct, -st, 0.0, a],
                [st * ca, ct * ca, -sa, -d * sa],
                [st * sa, ct * sa, ca, d * ca],
                [0.0, 0.0, 0.0, 1.0],
            ], dtype=float)
            t = t @ t_i
            transforms.append(t.copy())
        return transforms

    def translational_jacobian(self, q):
        transforms = self.forward_kinematics(q)
        tcp = (transforms[-1] @ self.tcp_offset)[:3]
        jac = np.zeros((3, 6), dtype=float)
        for idx in range(6):
            axis = transforms[idx][:3, 2]
            origin = transforms[idx][:3, 3]
            jac[:, idx] = np.cross(axis, tcp - origin)
        return jac

    @classmethod
    def zone_color(cls, score):
        score = float(score or 0.0)
        if score >= 90.0:
            return cls.COLOR_DANGER
        if score >= 70.0:
            return cls.COLOR_WARN
        return cls.COLOR_SAFE

    @staticmethod
    def _clean_q(joint_angles):
        if not joint_angles or len(joint_angles) < 6:
            return None
        try:
            q = [float(v or 0.0) for v in joint_angles[:6]]
        except (TypeError, ValueError):
            return None
        return q

    @staticmethod
    def _wrap_abs_deg(deg):
        value = abs(((float(deg) + 180.0) % 360.0) - 180.0)
        return min(value, abs(180.0 - value))

    @classmethod
    def _angle_singularity_score(cls, deg, red_deg, warn_deg):
        dist = cls._wrap_abs_deg(deg)
        if dist <= red_deg:
            return 90.0 + (red_deg - dist) / max(red_deg, 1e-6) * 10.0
        if dist <= warn_deg:
            return 70.0 + (warn_deg - dist) / max(warn_deg - red_deg, 1e-6) * 20.0
        return 0.0

    @staticmethod
    def _manipulability_score(manip, condition):
        score = 0.0
        if manip <= 0.03:
            score = 90.0 + (0.03 - manip) / 0.03 * 10.0
        elif manip <= 0.08:
            score = 70.0 + (0.08 - manip) / 0.05 * 20.0
        elif manip <= 0.12:
            score = (0.12 - manip) / 0.04 * 45.0
        if condition >= 30.0:
            score = max(score, 92.0)
        elif condition >= 10.0:
            score = max(score, 72.0 + min((condition - 10.0) / 20.0, 1.0) * 18.0)
        return max(0.0, min(100.0, score))

    def _result(self, score, source, manipulability, sigma_min, condition):
        score = max(0.0, min(100.0, float(score or 0.0)))
        if score >= 90.0:
            level = "DANGER"
            label = "위험 권장 회피"
        elif score >= 70.0:
            level = "WARN"
            label = "주의 권장 감속"
        else:
            level = "SAFE"
            label = "안전 권장"
        return {
            "score": score,
            "level": level,
            "label": label,
            "color": self.zone_color(score),
            "source": source,
            "manipulability": float(manipulability or 0.0),
            "sigma_min": float(sigma_min or 0.0),
            "condition": float(condition or 0.0),
        }

    @staticmethod
    def _tcp_mm(tcp_pos_mm=None, tcp_pos_m=None):
        if tcp_pos_mm and len(tcp_pos_mm) >= 3:
            try:
                return [float(v or 0.0) for v in tcp_pos_mm[:3]]
            except (TypeError, ValueError):
                return None
        if tcp_pos_m and len(tcp_pos_m) >= 3:
            try:
                return [float(v or 0.0) * 1000.0 for v in tcp_pos_m[:3]]
            except (TypeError, ValueError):
                return None
        return None
