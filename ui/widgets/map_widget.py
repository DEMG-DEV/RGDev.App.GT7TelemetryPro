from PyQt6.QtWidgets import QGroupBox, QVBoxLayout
import pyqtgraph as pg
from collections import deque

class MapWidget(QGroupBox):
    def __init__(self, title="Circuito Completo"):
        super().__init__(title)
        
        self.map_x = deque(maxlen=4000)
        self.map_z = deque(maxlen=4000)
        
        layout = QVBoxLayout()
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#14161a')
        self.plot_widget.hideAxis('bottom')
        self.plot_widget.hideAxis('left')
        self.plot_widget.setAspectLocked(True)
        
        self.map_plot = self.plot_widget.plot(pen=pg.mkPen('#66fcf1', width=2))
        self.car_dot = self.plot_widget.plot(pen=None, symbol='o', symbolBrush='#ff003c', symbolSize=8)
        
        layout.addWidget(self.plot_widget)
        self.setLayout(layout)
        
    def add_point(self, x: float, z: float):
        self.map_x.append(x)
        self.map_z.append(z)
        
    def update_plot(self):
        self.map_plot.setData(list(self.map_x), list(self.map_z))
        if self.map_x and self.map_z:
            self.car_dot.setData([self.map_x[-1]], [self.map_z[-1]])
            
    def clear(self):
        self.map_x.clear()
        self.map_z.clear()
        self.map_plot.setData([], [])
        self.car_dot.setData([], [])
