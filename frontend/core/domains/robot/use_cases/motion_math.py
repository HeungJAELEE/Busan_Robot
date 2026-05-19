import copy

class MotionMath:
    """
    로봇 모션 제어를 위한 순수 수학적 좌표 연산을 담당하는 모듈
    """
    
    @staticmethod
    def compute_offset_position(base_p: list, dist_mm: float, direction) -> list:
        """
        UI의 mm 입력값을 APK/Conty 접근/후퇴 규칙으로 변환합니다.
        direction 0/1은 둘 다 타겟 위(+Z)의 안전 위치이고,
        lateral direction 2/3/4/5는 부호 있는 X/Y 오프셋입니다.
        """
        try:
            distance_m = float(dist_mm or 0.0) / 1000.0
        except (TypeError, ValueError):
            distance_m = 0.0
        return MotionMath.compute_conty_offset_position(base_p, distance_m, direction)

    @staticmethod
    def normalize_distance_m(value) -> float:
        """Return Conty approach/retract distance in meters.

        APK/Conty JSON stores small distances as meters, for example 0.08
        means 80mm. Older HMI-edited values may already be in mm, such as 80.
        """
        try:
            dist = float(value or 0.0)
        except (TypeError, ValueError):
            return 0.0
        if abs(dist) > 1.0:
            return dist / 1000.0
        return dist

    @staticmethod
    def distance_m_to_ui_mm(value) -> float:
        """Convert Conty JSON distance to the editor's mm display value."""
        dist = MotionMath.normalize_distance_m(value)
        return dist * 1000.0

    @staticmethod
    def ui_mm_to_distance_m(value) -> float:
        """Convert the editor's mm entry back to APK-compatible meters."""
        try:
            return float(value or 0.0) / 1000.0
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def compute_conty_offset_position(base_p: list, distance_m: float, direction, role: str = "approach") -> list:
        """Compute APK-compatible Pick/Place approach/retract waypoint.

        In the teaching files, the common pair direction 0/1 is used for
        vertical approach/retract. Both waypoints must stay above the target:
        approach goes down to target, then retract goes back up. Lateral
        directions 2/3 and 4/5 keep their signed axis meaning.
        """
        if not base_p or len(base_p) < 6:
            return base_p

        pos = copy.deepcopy(base_p)
        dist = abs(MotionMath.normalize_distance_m(distance_m))
        if dist == 0.0:
            return pos

        dir_str = str(direction)
        dir_alias = {
            "Z": "0",
            "Z+": "0",
            "+Z": "0",
            "-Z": "1",
            "Z-": "1",
            "X": "2",
            "X+": "2",
            "+X": "2",
            "-X": "3",
            "X-": "3",
            "Y": "4",
            "Y+": "4",
            "+Y": "4",
            "-Y": "5",
            "Y-": "5",
        }
        code = dir_alias.get(dir_str, dir_str)

        if code in ("0", "1"):
            # Standard APK pattern: app=0, ret=1 means above target in both
            # stages. Do not interpret retract=1 as "go below target".
            pos[2] += dist
        elif code == "2":
            pos[0] += dist
        elif code == "3":
            pos[0] -= dist
        elif code == "4":
            pos[1] += dist
        elif code == "5":
            pos[1] -= dist
        else:
            pos[2] += dist
        return pos

    @staticmethod
    def compute_pallet_point(p1: list, p2: list, p3: list, size_m: int, size_n: int, current_m: int, current_n: int, p4: list = None, size_l: int = 1, current_l: int = 0) -> list:
        """
        팔레타이징 3점(+4점) 기반 그리드 보간
        p1: 시작점, p2: 행 끝점, p3: 열 끝점, p4: 층 끝점 (옵션)
        current_m: 현재 행 인덱스 (0-based)
        current_n: 현재 열 인덱스 (0-based)
        current_l: 현재 층 인덱스 (0-based)
        """
        if not (p1 and p2 and p3) or len(p1) < 6 or len(p2) < 6 or len(p3) < 6:
            return p1 if p1 else [0.0]*6
            
        result = [0.0] * 6
        
        for i in range(6):
            # M 방향 보간 (행) — M=1이면 행 이동 없음
            dm = 0.0
            if size_m > 1:
                dm = (p2[i] - p1[i]) / (size_m - 1)
            
            # N 방향 보간 (열) — N=1이면 열 이동 없음
            dn = 0.0
            if size_n > 1:
                dn = (p3[i] - p1[i]) / (size_n - 1)
            
            # L 방향 보간 (층) — P4가 있으면 P4 기준, 없으면 Z축 자동 오프셋
            dl = 0.0
            if size_l > 1:
                if p4 and len(p4) >= 6:
                    dl = (p4[i] - p1[i]) / (size_l - 1)
                elif i == 2:
                    # P4 없을 때: Z축만 자동 오프셋 (P2-P1의 Z 차이 또는 기본 0.1m 간격)
                    z_gap = abs(p2[2] - p1[2]) if abs(p2[2] - p1[2]) > 0.001 else 0.1
                    dl = z_gap
            
            result[i] = p1[i] + (dm * current_m) + (dn * current_n) + (dl * current_l)
            
        return result
