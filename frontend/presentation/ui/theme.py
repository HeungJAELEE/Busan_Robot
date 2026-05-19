"""Factory studio design tokens for the Indy7 HMI."""
import customtkinter as ctk

class Theme:
    # ─── Colors ───
    # Primary Backgrounds
    BG_BASE = "#D0D0CB"        # Warm grey studio background
    BG_SURFACE = "#F6F7F3"     # Raised panels
    BG_PANEL = "#FFFFFF"       # Cards and tool surfaces
    BG_CANVAS = "#ECEDE8"      # Plot/canvas surfaces
    BORDER = "#D5D9D2"
    
    # Text
    TEXT_PRIMARY = "#202524"
    TEXT_SECONDARY = "#59615F"
    TEXT_TERTIARY = "#7A8380"
    
    # Accents
    ACCENT_PRIMARY = "#20A963"
    ACCENT_HOVER = "#35BA76"
    ACCENT_SECONDARY = "#DDF2E6"
    ACCENT_FLARE = "#D79927"
    
    # Semantic Colors
    SUCCESS = "#20A963"
    SUCCESS_HOVER = "#168A51"
    DANGER = "#D8453E"
    DANGER_HOVER = "#B9322D"
    WARNING = "#D79927"
    INFO = "#2B78D4"
    
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
    def card_style(cls):
        return {"fg_color": cls.BG_SURFACE, "border_color": cls.BORDER, "border_width": 1}
        
    @classmethod
    def get_button_style(cls, variant="primary"):
        """자주 쓰이는 버튼 스타일 프리셋 반환"""
        if variant == "primary":
            return {"fg_color": cls.ACCENT_PRIMARY, "hover_color": cls.ACCENT_HOVER, "text_color": "#FFFFFF"}
        elif variant == "danger":
            return {"fg_color": cls.DANGER, "hover_color": cls.DANGER_HOVER, "text_color": "#FFFFFF"}
        elif variant == "success":
            return {"fg_color": cls.SUCCESS, "hover_color": cls.SUCCESS_HOVER, "text_color": "#FFFFFF"}
        elif variant == "secondary":
            return {"fg_color": "#EEF1EC", "hover_color": "#E1E6DF", "text_color": cls.TEXT_PRIMARY}
        elif variant == "ghost":
            return {"fg_color": "transparent", "hover_color": "#E6EAE4", "text_color": cls.TEXT_SECONDARY}
        else:
            return {"fg_color": cls.BG_PANEL, "hover_color": "#E6EAE4", "text_color": cls.TEXT_PRIMARY}
