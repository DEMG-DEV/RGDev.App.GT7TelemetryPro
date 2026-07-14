import pyqtgraph as pg
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
import numpy as np

class DeltaWidget(QWidget):
    """
    Widget para mostrar el Delta-Time contra la mejor vuelta.
    Rojo = Más lento (positivo), Verde = Más rápido (negativo).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.title_label = QLabel("Delta (Current vs Best)")
        self.title_label.setStyleSheet("color: #1A1A1A; font-weight: bold; font-size: 14px;")
        self.layout.addWidget(self.title_label)
        
        # Gráfica de pyqtgraph
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#FAFAFA')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.enableAutoRange(axis='xy')
        self.plot_widget.setLabel('left', 'Delta (s)')
        
        self.layout.addWidget(self.plot_widget)
        
        # Curva de datos
        self.delta_curve = self.plot_widget.plot(pen=pg.mkPen('w', width=2))
        
        # Buffer de datos
        self.history_size = 600 # 10 segundos a 60Hz
        self.x_data = np.zeros(self.history_size)
        self.y_data = np.zeros(self.history_size)
        self.ptr = 0
        
    def update_data(self, delta_ms: float):
        """
        Actualiza el gráfico con el delta actual en milisegundos.
        """
        delta_s = delta_ms / 1000.0
        
        self.x_data = np.roll(self.x_data, -1)
        self.y_data = np.roll(self.y_data, -1)
        
        self.x_data[-1] = self.ptr
        self.y_data[-1] = delta_s
        self.ptr += 1
        
        # Cambiar el color basado en el último valor
        color = 'g' if delta_s < 0 else 'r'
        self.delta_curve.setData(self.x_data, self.y_data, pen=pg.mkPen(color, width=2))
