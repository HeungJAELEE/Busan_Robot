import copy

class MotionMath:
    """
    로봇 모션 제어를 위한 순수 수학적 좌표 연산을 담당하는 모듈
    """
    
    @staticmethod
    def compute_offset_position(base_p: list, dist_mm: float, direction) -> list:
        """
        base_p에서 지정된 축(Z, X, Y)으로 dist_mm 만큼 오프셋된 좌표를 반환합니다.
        Approach/Retract 모두 정위치에서 멀어지는 방향(+ 방향)으로 오프셋합니다.
        direction 코드: 0=Z, 1=-Z → 둘 다 Z축이며, 항상 +Z(위쪽)으로 이동
        direction 코드: 2=X, 3=-X → 둘 다 X축이며, 항상 +X 방향
        direction 코드: 4=Y, 5=-Y → 둘 다 Y축이며, 항상 +Y 방향
        """
        if not base_p or len(base_p) < 6: return base_p
        
        p = copy.deepcopy(base_p)
        val = dist_mm / 1000.0  # mm to m
        
        dir_str = str(direction)
        # Approach/Retract 모두 타겟에서 멀어지는 방향 (+) 으로 오프셋
        if dir_str in ["Z", "0", "-Z", "1"]: p[2] += val
        elif dir_str in ["X", "2", "-X", "3"]: p[0] += val
        elif dir_str in ["Y", "4", "-Y", "5"]: p[1] += val
        
        return p

    @staticmethod
    def compute_pallet_point(p1: list, p2: list, p3: list, size_m: int, size_n: int, current_m: int, current_n: int) -> list:
        """
        팔레타이징 3점 기반 그리드 보간
        """
        if not (p1 and p2 and p3) or len(p1) < 6 or len(p2) < 6 or len(p3) < 6:
            return p1 if p1 else [0.0]*6
            
        result = [0.0] * 6
        m_steps = max(1, size_m - 1)
        n_steps = max(1, size_n - 1)
        
        for i in range(6):
            dm = (p2[i] - p1[i]) / m_steps
            dn = (p3[i] - p1[i]) / n_steps
            result[i] = p1[i] + (dm * current_m) + (dn * current_n)
            
        return result
