from PyQt6.QtWidgets import QGroupBox, QVBoxLayout
import pyqtgraph as pg
from collections import deque
import numpy as np

class MapWidget(QGroupBox):
    def __init__(self, title="Heatmap Pista (Le Mans / F1)"):
        super().__init__(title)
        
        # Buffer más grande para pistas largas como Nurburgring
        self.max_len = 10000 
        self.map_x = deque(maxlen=self.max_len)
        self.map_z = deque(maxlen=self.max_len)
        self.colors = deque(maxlen=self.max_len)
        
        layout = QVBoxLayout()
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#FAFAFA')
        self.plot_widget.hideAxis('bottom')
        self.plot_widget.hideAxis('left')
        self.plot_widget.setAspectLocked(True)
        
        # Usamos ScatterPlotItem porque permite colores individuales por punto
        self.scatter = pg.ScatterPlotItem(size=4, pen=None)
        self.plot_widget.addItem(self.scatter)
        
        self.car_dot = self.plot_widget.plot(pen=None, symbol='o', symbolBrush='k', symbolSize=10)
        self.crosshair = self.plot_widget.plot(pen=None, symbol='+', symbolBrush='r', symbolSize=15)

        
        layout.addWidget(self.plot_widget)
        self.setLayout(layout)
        
    def add_point(self, x: float, z: float, throttle: int, brake: int):
        self.map_x.append(x)
        self.map_z.append(z)
        
        # Lógica de color Heatmap
        if brake > 0:
            intensity = int((brake / 255.0) * 255)
            # Rojo para frenos
            color = pg.mkBrush(255, 255 - intensity, 255 - intensity, 200)
        elif throttle > 0:
            intensity = int((throttle / 255.0) * 255)
            # Verde para acelerador
            color = pg.mkBrush(255 - intensity, 255, 255 - intensity, 200)
        else:
            # Amarillo/Gris para Lift & Coast
            color = pg.mkBrush(200, 200, 200, 150)
            
        self.colors.append(color)
        
    def update_plot(self):
        if len(self.map_x) > 0:
            self.scatter.setData(x=list(self.map_x), y=list(self.map_z), brush=list(self.colors))
            self.car_dot.setData([self.map_x[-1]], [self.map_z[-1]])
            
    def set_crosshair(self, x: float, z: float):
        if hasattr(self, 'crosshair'):
            self.crosshair.setData([x], [z])
            
    def clear(self):
        self.map_x.clear()
        self.map_z.clear()
        self.colors.clear()
        self.scatter.setData([], [])
        self.car_dot.setData([], [])
        if hasattr(self, 'crosshair'):
            self.crosshair.setData([], [])
