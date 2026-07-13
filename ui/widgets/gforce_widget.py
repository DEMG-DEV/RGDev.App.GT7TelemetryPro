from PyQt6.QtWidgets import QGroupBox, QVBoxLayout
import pyqtgraph as pg
from collections import deque

class GForceWidget(QGroupBox):
    def __init__(self, title="Aceleración Centrípeta"):
        super().__init__(title)
        
        self.g_x = deque(maxlen=100)
        self.g_y = deque(maxlen=100)
        
        layout = QVBoxLayout()
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#FAFAFA')
        self.plot_widget.hideAxis('bottom')
        self.plot_widget.hideAxis('left')
        self.plot_widget.setAspectLocked(True)
        self.plot_widget.setXRange(-2, 2)
        self.plot_widget.setYRange(-2, 2)
        
        # Draw crosshairs
        self.plot_widget.addLine(x=0, pen=pg.mkPen('#CCCCCC'))
        self.plot_widget.addLine(y=0, pen=pg.mkPen('#CCCCCC'))
        
        # Draw circles at 1G and 2G
        circle1 = pg.QtGui.QPainterPath()
        circle1.addEllipse(pg.QtCore.QRectF(-1, -1, 2, 2))
        path_item1 = pg.QtWidgets.QGraphicsPathItem(circle1)
        path_item1.setPen(pg.mkPen('#CCCCCC'))
        self.plot_widget.addItem(path_item1)
        
        self.g_plot = self.plot_widget.plot(pen=None, symbol='o', symbolBrush='#FF8C00', symbolSize=5, alpha=0.5)
        self.g_dot_latest = self.plot_widget.plot(pen=None, symbol='o', symbolBrush='#FF0000', symbolSize=10)
        
        layout.addWidget(self.plot_widget)
        self.setLayout(layout)
        
    def add_point(self, x: float, y: float):
        self.g_x.append(x)
        self.g_y.append(y)
        
    def update_plot(self):
        self.g_plot.setData(list(self.g_x), list(self.g_y))
        if self.g_x and self.g_y:
            self.g_dot_latest.setData([self.g_x[-1]], [self.g_y[-1]])
            
    def clear(self):
        self.g_x.clear()
        self.g_y.clear()
        self.g_plot.setData([], [])
        self.g_dot_latest.setData([], [])
