from PyQt6.QtWidgets import QGroupBox, QVBoxLayout
import pyqtgraph as pg
import numpy as np

class TelemetryGraphsWidget(QGroupBox):
    def __init__(self, title="Telemetría en Vivo (Últimos 10s)", history_size=600):
        super().__init__(title)
        self.history_size = history_size
        
        self.time_data = np.linspace(-10, 0, self.history_size)
        self.speed_data = np.zeros(self.history_size)
        self.throttle_data = np.zeros(self.history_size)
        self.brake_data = np.zeros(self.history_size)
        self.rpm_data = np.zeros(self.history_size)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0,10,0,0)
        layout.setSpacing(0)
        
        self.plot_stack = pg.GraphicsLayoutWidget()
        self.plot_stack.setBackground('#FAFAFA')
        
        # 1. Velocidad
        self.p_vel = self.plot_stack.addPlot(title="Velocidad (km/h)")
        self.p_vel.showGrid(x=True, y=True, alpha=0.2)
        self.p_vel.enableAutoRange(axis='xy')
        self.p_vel.getAxis('left').setPen('#CCCCCC')
        self.p_vel.getAxis('bottom').setStyle(showValues=False)
        self.curve_vel = self.p_vel.plot(pen=pg.mkPen('#0000FF', width=2))
        
        self.plot_stack.nextRow()
        
        # 2. Acelerador / Freno
        self.p_pedal = self.plot_stack.addPlot(title="Acelerador / Freno (%)")
        self.p_pedal.showGrid(x=True, y=True, alpha=0.2)
        self.p_pedal.enableAutoRange(axis='xy')
        self.p_pedal.getAxis('left').setPen('#CCCCCC')
        self.p_pedal.getAxis('bottom').setStyle(showValues=False)
        self.curve_thr = self.p_pedal.plot(pen=pg.mkPen('#008000', width=2), fillLevel=0, brush=(0,128,0,60))
        self.curve_brk = self.p_pedal.plot(pen=pg.mkPen('#FF0000', width=2), fillLevel=0, brush=(255,0,0,60))
        
        self.plot_stack.nextRow()
        
        # 3. RPM
        self.p_rpm = self.plot_stack.addPlot(title="R.P.M.")
        self.p_rpm.showGrid(x=True, y=True, alpha=0.2)
        self.p_rpm.enableAutoRange(axis='xy')
        self.p_rpm.getAxis('left').setPen('#CCCCCC')
        self.p_rpm.getAxis('bottom').setPen('#CCCCCC')
        self.curve_rpm = self.p_rpm.plot(pen=pg.mkPen('#FF8C00', width=2))
        
        layout.addWidget(self.plot_stack)
        self.setLayout(layout)
        
    def add_data(self, speed, throttle, brake, rpm):
        self.speed_data = np.roll(self.speed_data, -1)
        self.throttle_data = np.roll(self.throttle_data, -1)
        self.brake_data = np.roll(self.brake_data, -1)
        self.rpm_data = np.roll(self.rpm_data, -1)
        
        self.speed_data[-1] = speed
        self.throttle_data[-1] = throttle
        self.brake_data[-1] = brake
        self.rpm_data[-1] = rpm
        
    def update_plot(self):
        self.curve_vel.setData(self.time_data, self.speed_data)
        self.curve_thr.setData(self.time_data, self.throttle_data)
        self.curve_brk.setData(self.time_data, self.brake_data)
        self.curve_rpm.setData(self.time_data, self.rpm_data)
        
    def clear(self):
        self.speed_data.fill(0)
        self.throttle_data.fill(0)
        self.brake_data.fill(0)
        self.rpm_data.fill(0)
        self.update_plot()
