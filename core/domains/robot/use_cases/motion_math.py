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

