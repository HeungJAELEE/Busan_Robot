from typing import List, Tuple

class PalletGridCalculator:
    """
    도메인 서비스: 팔레타이징 그리드의 3차원 공간 좌표를 계산합니다.
    기존 test123에 하드코딩되었던 OFFSET 연산 로직을 3점 교시 기반으로 추상화합니다.
    """
    @staticmethod
    def calculate_offsets(p1: List[float], p2: List[float], p3: List[float], m: int, n: int) -> Tuple[List[float], List[float]]:
        """
        P1(원점), P2(행방향 끝), P3(열방향 끝) 좌표와 M(행), N(열)을 기반으로
        각 요소당 거리를 나타내는 X벡터(행벡터)와 Y벡터(열벡터)를 계산합니다.
        
        :param p1: 시작점 [x, y, z, rx, ry, rz]
        :param p2: 행 방향 끝점 [x, y, z, rx, ry, rz]
        :param p3: 열 방향 끝점 [x, y, z, rx, ry, rz]
        :param m: 행(Row) 총 개수 (X축)
        :param n: 열(Column) 총 개수 (Y축)
        :return: (vector_x, vector_y) - 각 3차원 float 리스트
        """
        # 보호 로직: 점이 부족하거나 잘못된 경우 기본 0 반환
        if not p1 or not p2 or not p3 or len(p1) < 3 or len(p2) < 3 or len(p3) < 3:
            return [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]

        # m 또는 n이 1인 경우, 간격을 0으로 처리 (나누기 0 방지)
        div_m = max(1, m - 1)
        div_n = max(1, n - 1)

        vector_x = [
            (p2[0] - p1[0]) / div_m,
            (p2[1] - p1[1]) / div_m,
            (p2[2] - p1[2]) / div_m
        ]
        
        vector_y = [
            (p3[0] - p1[0]) / div_n,
            (p3[1] - p1[1]) / div_n,
            (p3[2] - p1[2]) / div_n
        ]
        
        return vector_x, vector_y

    @staticmethod
    def generate_3d_grid(p1: List[float], p2: List[float], p3: List[float], m: int, n: int, layers: int = 1, layer_h: float = 0.0) -> List[List[float]]:
        """
        계산된 오프셋을 바탕으로 m x n x layers 개의 모든 3차원 그리드 좌표를 생성합니다.
        순서는 Z단 -> X행 -> Y열 (지그재그 아님, 단방향 기준)
        """
        if not p1 or len(p1) < 6:
            return []

        vector_x, vector_y = PalletGridCalculator.calculate_offsets(p1, p2, p3, m, n)
        coords = []
        
        for layer in range(layers):
            z_offset = layer * layer_h
            for row in range(n):  # Y축
                for col in range(m):  # X축
                    x = p1[0] + (col * vector_x[0]) + (row * vector_y[0])
                    y = p1[1] + (col * vector_x[1]) + (row * vector_y[1])
                    z = p1[2] + (col * vector_x[2]) + (row * vector_y[2]) + z_offset
                    # 회전(Rx, Ry, Rz)은 P1의 방향을 기준으로 고정
                    coords.append([x, y, z, p1[3], p1[4], p1[5]])
                    
        return coords
