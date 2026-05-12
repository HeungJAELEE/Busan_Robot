class BaseNodeEditor:
    """
    모든 노드 에디터 UI 클래스가 상속받아야 하는 베이스 클래스 (인터페이스 역할).
    다형성을 보장하여 HMI 메인 뷰가 구체적인 에디터 구현에 의존하지 않게 합니다.
    """
    def __init__(self, parent_frame):
        self.parent = parent_frame
        
    def render(self):
        """
        부모 프레임을 지우고 에디터 UI 컴포넌트들을 화면에 배치합니다.
        """
        raise NotImplementedError("Subclasses must implement render()")
        
    def update_ui(self, *args, **kwargs):
        """
        주어진 데이터를 사용해 에디터 내부의 입력값/상태를 갱신합니다.
        """
        raise NotImplementedError("Subclasses must implement update_ui()")
