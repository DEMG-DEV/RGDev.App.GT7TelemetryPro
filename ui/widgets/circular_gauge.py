from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QFontMetrics
from PyQt6.QtCore import Qt, QRectF

class CircularGaugeWidget(QWidget):
    def __init__(self, title="Gauge", unit="", min_val=0, max_val=100, color="#2A82DA"):
        super().__init__()
        self.title = title
        self.unit = unit
        self.min_val = min_val
        self.max_val = max_val
        self.value = min_val
        self.color = QColor(color)
        
        # Determinar decimales según el rango
        self.decimals = 0
        if max_val - min_val <= 10:
            self.decimals = 2
            
        self.setMinimumSize(120, 120)
        
    def set_value(self, val):
        self.value = max(self.min_val, min(val, self.max_val))
        self.update()
        
    def set_max(self, val):
        self.max_val = val
        if self.value > self.max_val:
            self.value = self.max_val
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        size = min(width, height) - 20
        rect = QRectF((width - size) / 2, (height - size) / 2, size, size)
        
        # Background arc (Gray)
        pen_bg = QPen(QColor(220, 220, 220))
        pen_bg.setWidth(8)
        pen_bg.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_bg)
        
        # Start at 225 degrees, span -270 degrees (clockwise)
        # PyQt6 uses 1/16th of a degree increments
        start_angle = 225 * 16 
        span_angle = -270 * 16 
        painter.drawArc(rect, start_angle, span_angle)
        
        # Value arc (Color)
        if self.max_val > self.min_val:
            ratio = (self.value - self.min_val) / (self.max_val - self.min_val)
        else:
            ratio = 0
            
        pen_val = QPen(self.color)
        pen_val.setWidth(8)
        pen_val.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_val)
        
        val_span_angle = int(-270 * ratio * 16)
        painter.drawArc(rect, start_angle, val_span_angle)
        
        # Draw Text (Value)
        painter.setPen(QColor(26, 26, 26))
        font_val = QFont("Menlo", int(size * 0.22), QFont.Weight.Bold)
        painter.setFont(font_val)
        
        if self.decimals > 0:
            val_str = f"{self.value:.{self.decimals}f}"
        else:
            val_str = str(int(self.value))
            
        fm = QFontMetrics(font_val)
        val_rect = fm.boundingRect(val_str)
        painter.drawText(
            int((width - val_rect.width()) / 2),
            int(height / 2 + val_rect.height() / 3),
            val_str
        )
        
        # Draw Title
        font_title = QFont("Arial", int(size * 0.08), QFont.Weight.Bold)
        painter.setFont(font_title)
        fm_t = QFontMetrics(font_title)
        t_rect = fm_t.boundingRect(self.title)
        painter.drawText(
            int((width - t_rect.width()) / 2),
            int(height / 2 - size * 0.25),
            self.title
        )
        
        # Draw Unit
        font_unit = QFont("Arial", int(size * 0.08))
        painter.setFont(font_unit)
        fm_u = QFontMetrics(font_unit)
        u_rect = fm_u.boundingRect(self.unit)
        painter.drawText(
            int((width - u_rect.width()) / 2),
            int(height / 2 + size * 0.35),
            self.unit
        )
        
        painter.end()
