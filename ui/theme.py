from __future__ import annotations
"""
GT7 Telemetry Pro — Sistema Centralizado de Tokens de Diseño (Daylight Mode)
=============================================================================
Todas las constantes de diseño del proyecto viven aquí. Ningún archivo UI
debe contener colores mágicos sueltos; en su lugar, importará Theme.
"""


class Theme:
    """Design tokens para el tema Daylight (modo diurno) de ingeniería."""

    # ── Fondos ──────────────────────────────────────────────────────────
    BG_WINDOW = "#F0F0F0"
    BG_PANEL  = "#FAFAFA"
    BG_CARD   = "#FFFFFF"
    BG_INPUT  = "#FFFFFF"
    BG_ALT_ROW = "#F8F9FA"

    # ── Texto ───────────────────────────────────────────────────────────
    TEXT_PRIMARY   = "#1A1A1A"
    TEXT_SECONDARY = "#666666"
    TEXT_MUTED     = "#999999"

    # ── Bordes ──────────────────────────────────────────────────────────
    BORDER       = "#CCCCCC"
    BORDER_LIGHT = "#DDDDDD"
    BORDER_GRID  = "#EEEEEE"

    # ── Colores de Acento ───────────────────────────────────────────────
    ACCENT_BLUE   = "#2A82DA"
    ACCENT_GREEN  = "#27AE60"
    ACCENT_ORANGE = "#E67E22"
    ACCENT_RED    = "#E74C3C"
    ACCENT_DARK   = "#2C3E50"

    # ── Colores Funcionales ─────────────────────────────────────────────
    STATUS_CONNECTED  = "#27AE60"
    STATUS_RECORDING  = "#E74C3C"
    STATUS_SEARCHING  = "#F2A900"
    STATUS_ERROR      = "#E74C3C"
    FUEL_NORMAL       = "#3498DB"
    FUEL_WARNING      = "#F1C40F"
    FUEL_CRITICAL     = "#E74C3C"
    WOT_ACTIVE        = "#27AE60"

    # ── Tipografía ──────────────────────────────────────────────────────
    FONT_MONO = "Menlo"
    FONT_SANS = "Arial"

    # ── Botones (macOS-safe defaults) ───────────────────────────────────
    BTN_RADIUS    = "6px"
    BTN_BORDER    = f"1px solid {BORDER}"
    BTN_PADDING   = "8px 16px"
    BTN_PADDING_SM = "6px 12px"

    # ── Gráficos (pyqtgraph) ───────────────────────────────────────────
    CHART_BG = "#FAFAFA"
    CHART_FG = "#1A1A1A"

    # ── Helpers de Estilo ───────────────────────────────────────────────

    @staticmethod
    def btn_style(bg: str, text: str = "#FFFFFF",
                  border_color: str | None = None,
                  hover_bg: str | None = None,
                  pressed_bg: str | None = None,
                  padding: str | None = None) -> str:
        """Genera un stylesheet completo para QPushButton, compatible con macOS.

        Todos los botones necesitan border-radius, borde explícito y padding
        para no romperse con el motor de dibujado nativo de Apple (ver AGENTS.md §9).
        """
        bc = border_color or Theme.BORDER
        pd = padding or Theme.BTN_PADDING
        base = (
            f"QPushButton {{ "
            f"background-color: {bg}; color: {text}; "
            f"border: 1px solid {bc}; border-radius: {Theme.BTN_RADIUS}; "
            f"padding: {pd}; font-weight: bold; "
            f"}}"
        )
        hover = ""
        if hover_bg:
            hover = (
                f" QPushButton:hover {{ "
                f"background-color: {hover_bg}; "
                f"}}"
            )
        pressed = ""
        if pressed_bg:
            pressed = (
                f" QPushButton:pressed {{ "
                f"background-color: {pressed_bg}; "
                f"}}"
            )
        return base + hover + pressed

    @staticmethod
    def progress_style(chunk_color: str, text_color: str = "#1A1A1A") -> str:
        """Genera un stylesheet consistente para QProgressBar."""
        return (
            f"QProgressBar {{ "
            f"border: 1px solid {Theme.BORDER}; border-radius: 4px; "
            f"text-align: center; font-weight: bold; color: {text_color}; "
            f"background-color: {Theme.BG_CARD}; "
            f"}} "
            f"QProgressBar::chunk {{ "
            f"background-color: {chunk_color}; border-radius: 3px; "
            f"}}"
        )

    @staticmethod
    def table_style() -> str:
        """Genera un stylesheet unificado para QTableWidget."""
        return (
            f"QTableWidget {{ "
            f"background-color: {Theme.BG_CARD}; "
            f"alternate-background-color: {Theme.BG_ALT_ROW}; "
            f"border: 1px solid {Theme.BORDER_LIGHT}; "
            f"border-radius: 4px; "
            f"gridline-color: {Theme.BORDER_GRID}; "
            f"color: {Theme.TEXT_PRIMARY}; "
            f"}} "
            f"QHeaderView::section {{ "
            f"background-color: {Theme.BG_PANEL}; "
            f"font-weight: bold; "
            f"border: none; "
            f"border-bottom: 2px solid {Theme.BORDER_LIGHT}; "
            f"padding: 6px; "
            f"color: {Theme.TEXT_PRIMARY}; "
            f"}}"
        )

    @staticmethod
    def combo_style() -> str:
        """Genera un stylesheet unificado para QComboBox."""
        return (
            f"QComboBox {{ "
            f"border: 1px solid {Theme.BORDER}; "
            f"border-radius: {Theme.BTN_RADIUS}; "
            f"padding: 6px 12px; "
            f"background-color: {Theme.BG_INPUT}; "
            f"font-size: 13px; "
            f"color: {Theme.TEXT_PRIMARY}; "
            f"}} "
            f"QComboBox::drop-down {{ "
            f"border-left: 1px solid {Theme.BORDER}; "
            f"width: 30px; "
            f"}} "
            f"QComboBox QAbstractItemView {{ "
            f"background-color: {Theme.BG_CARD}; "
            f"color: {Theme.TEXT_PRIMARY}; "
            f"selection-background-color: {Theme.ACCENT_BLUE}; "
            f"selection-color: white; "
            f"}}"
        )
