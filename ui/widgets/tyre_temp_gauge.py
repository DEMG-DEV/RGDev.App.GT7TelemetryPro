from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QFontMetrics, QLinearGradient
from PyQt6.QtCore import Qt, QRectF

from ui.theme import Theme


class TyreTempGauge(QWidget):
    """
    Semicírculo de temperatura de neumático con gradiente de color
    que va de azul (frío) → verde (óptimo) → rojo (sobrecalentamiento).
    
    Rangos de referencia GT7:
      - < 50°C  : Azul (frío, sin agarre)
      - 50-80°C : Verde (ventana óptima)
      - 80-100°C: Naranja (caliente, buen agarre pero al límite)
      - > 100°C : Rojo (sobrecalentamiento, degradación)
    """

    # Rango absoluto del gauge
    MIN_TEMP = 20.0
    MAX_TEMP = 140.0

    # Zonas de color por temperatura
    COLOR_COLD = QColor(66, 133, 244)      # Azul — frío
    COLOR_OPTIMAL = QColor(46, 204, 113)   # Verde — óptimo
    COLOR_HOT = QColor(243, 156, 18)       # Naranja — caliente
    COLOR_OVERHEAT = QColor(231, 76, 60)   # Rojo — sobrecalentamiento

    def __init__(self, label="FL", parent=None):
        super().__init__(parent)
        self.label = label
        self.temp = 0.0
        self.setMinimumSize(60, 45)

    def set_temp(self, temp: float):
        """Actualiza la temperatura mostrada."""
        self.temp = temp
        self.update()

    def _temp_to_color(self, temp: float) -> QColor:
        """Retorna un color interpolado según la temperatura."""
        if temp < 50:
            t = max(0.0, (temp - self.MIN_TEMP) / (50 - self.MIN_TEMP))
            return self._lerp_color(self.COLOR_COLD, self.COLOR_OPTIMAL, t)
        elif temp < 80:
            t = (temp - 50) / 30.0
            return self._lerp_color(self.COLOR_OPTIMAL, self.COLOR_OPTIMAL, t)
        elif temp < 100:
            t = (temp - 80) / 20.0
            return self._lerp_color(self.COLOR_OPTIMAL, self.COLOR_HOT, t)
        else:
            t = min(1.0, (temp - 100) / 40.0)
            return self._lerp_color(self.COLOR_HOT, self.COLOR_OVERHEAT, t)

    @staticmethod
    def _lerp_color(c1: QColor, c2: QColor, t: float) -> QColor:
        """Interpolación lineal entre dos colores."""
        t = max(0.0, min(1.0, t))
        return QColor(
            int(c1.red() + (c2.red() - c1.red()) * t),
            int(c1.green() + (c2.green() - c1.green()) * t),
            int(c1.blue() + (c2.blue() - c1.blue()) * t),
        )

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        # El semicírculo ocupa la parte superior, el texto va abajo
        arc_size = min(w - 10, (h - 20) * 2)
        arc_size = max(arc_size, 40)
        pen_width = max(6, int(arc_size * 0.09))

        # Centrar el arco horizontalmente, posicionarlo arriba
        arc_rect = QRectF(
            (w - arc_size) / 2,
            5,
            arc_size,
            arc_size
        )

        # --- Fondo del arco (gris claro) ---
        pen_bg = QPen(QColor(220, 220, 220))
        pen_bg.setWidth(pen_width)
        pen_bg.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_bg)
        # Semicírculo: de 0° a 180° (parte superior)
        painter.drawArc(arc_rect, 0 * 16, 180 * 16)

        # --- Arco de valor (color según temperatura) ---
        clamped = max(self.MIN_TEMP, min(self.temp, self.MAX_TEMP))
        ratio = (clamped - self.MIN_TEMP) / (self.MAX_TEMP - self.MIN_TEMP)

        arc_color = self._temp_to_color(self.temp)
        pen_val = QPen(arc_color)
        pen_val.setWidth(pen_width)
        pen_val.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_val)

        # El arco crece de izquierda (180°) hacia derecha (0°)
        val_span = int(-180 * ratio * 16)
        painter.drawArc(arc_rect, 180 * 16, val_span)

        # --- Texto de temperatura ---
        painter.setPen(QColor(Theme.TEXT_PRIMARY))
        font_val = QFont(Theme.FONT_MONO, max(10, int(arc_size * 0.18)), QFont.Weight.Bold)
        painter.setFont(font_val)

        temp_str = f"{self.temp:.0f}°"
        fm = QFontMetrics(font_val)
        t_rect = fm.boundingRect(temp_str)
        text_y = int(5 + arc_size / 2 + t_rect.height() / 3)
        painter.drawText(
            int((w - t_rect.width()) / 2),
            text_y,
            temp_str
        )

        # --- Etiqueta (FL, FR, RL, RR) ---
        font_label = QFont(Theme.FONT_SANS, max(8, int(arc_size * 0.10)))
        painter.setFont(font_label)
        painter.setPen(QColor(Theme.TEXT_MUTED))
        fm_l = QFontMetrics(font_label)
        l_rect = fm_l.boundingRect(self.label)
        label_y = text_y + l_rect.height() + 2
        painter.drawText(
            int((w - l_rect.width()) / 2),
            label_y,
            self.label
        )

        painter.end()
