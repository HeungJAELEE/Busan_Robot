"""
Deep Space Command Center Design Tokens
FlutterFlow 스타일 기반의 테마 정의 파일
"""
import customtkinter as ctk

class Theme:
    # ─── Colors ───
    # Primary Backgrounds
    BG_BASE = "#060311"        # Midnight Ink: Primary background, deep cards
    BG_SURFACE = "#161320"     # Slate Deep: Secondary background, UI panels
    
    # Text
    TEXT_PRIMARY = "#ffffff"   # White Star: Primary text, critical UI elements
    TEXT_SECONDARY = "#9ba1ae" # Mist Gray: Secondary text, subtle descriptions
    TEXT_TERTIARY = "#333333"  # Dark Star: Tertiary text
    
    # Accents (Violets)
    ACCENT_PRIMARY = "#5800fd" # Deep Violet: Interactive elements, primary links, active states
    ACCENT_HOVER = "#7066ed"   # Dawn Violet: Interactive hover states
    ACCENT_SECONDARY = "#2415c6" # Cosmic Indigo: Muted violet for depth
    ACCENT_FLARE = "#882fe8"   # Flare Violet: Minor illustrative accents
    
    # Semantic Colors (Added for Robot App context)
    SUCCESS = "#4CAF50"        # Green for success, execution, ON
    SUCCESS_HOVER = "#2E7D32"
    DANGER = "#F44336"         # Red for stop, errors, OFF
    DANGER_HOVER = "#B71C1C"
    WARNING = "#FF9800"        # Orange for alerts, manual mode
    INFO = "#00BCD4"           # Cyan for info, general active
    
    # ─── Fonts ───
    FONT_FAMILY_DISPLAY = "Urbanist"
    FONT_FAMILY_BODY = "Inter"
    FONT_FALLBACK = "Helvetica"
    
    @classmethod
    def font(cls, size: int, weight: str = "normal", role: str = "body") -> ctk.CTkFont:
        """
        테마 규격에 맞는 폰트 객체 반환.
        role: "display" (큰 헤딩, 버튼 등), "body" (일반 텍스트, 네비게이션)
        """
        family = cls.FONT_FAMILY_DISPLAY if role == "display" else cls.FONT_FAMILY_BODY
        try:
            return ctk.CTkFont(family=family, size=size, weight=weight)
        except Exception:
            # 해당 폰트가 시스템에 없을 경우 Fallback
            return ctk.CTkFont(family=cls.FONT_FALLBACK, size=size, weight=weight)
            
    # ─── Style Helpers ───
    @classmethod
    def apply_window_style(cls, window):
        """기본 윈도우 배경색 적용"""
        window.configure(fg_color=cls.BG_BASE)
        
    @classmethod
    def get_button_style(cls, variant="primary"):
        """자주 쓰이는 버튼 스타일 프리셋 반환"""
        if variant == "primary":
            return {"fg_color": cls.ACCENT_PRIMARY, "hover_color": cls.ACCENT_HOVER, "text_color": cls.TEXT_PRIMARY}
        elif variant == "danger":
            return {"fg_color": cls.DANGER, "hover_color": cls.DANGER_HOVER, "text_color": cls.TEXT_PRIMARY}
        elif variant == "success":
            return {"fg_color": cls.SUCCESS, "hover_color": cls.SUCCESS_HOVER, "text_color": cls.TEXT_PRIMARY}
        elif variant == "secondary":
            return {"fg_color": cls.BG_SURFACE, "hover_color": cls.ACCENT_SECONDARY, "text_color": cls.TEXT_PRIMARY}
        elif variant == "ghost":
            return {"fg_color": "transparent", "hover_color": cls.BG_SURFACE, "text_color": cls.TEXT_SECONDARY}
        else:
            return {"fg_color": cls.BG_SURFACE, "hover_color": cls.TEXT_TERTIARY, "text_color": cls.TEXT_PRIMARY}
