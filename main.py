import sys
import numpy as np
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QProgressBar, QLineEdit, 
                             QPushButton, QGridLayout, QGroupBox)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QFont, QColor
import pyqtgraph as pg

from client import GT7TelemetryClient
from models import GT7TelemetryPacket

# --- STYLESHEET ---
DARK_STYLE = """
QMainWindow {
    background-color: #121212;
    color: #FFFFFF;
}
QGroupBox {
    border: 1px solid #333333;
    border-radius: 5px;
    margin-top: 10px;
    color: #AAAAAA;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 3px 0 3px;
}
QLabel {
    color: #FFFFFF;
}
QLineEdit {
    background-color: #1E1E1E;
    color: #FFFFFF;
    border: 1px solid #333333;
    padding: 5px;
    border-radius: 3px;
}
QPushButton {
    background-color: #2D2D2D;
    color: #FFFFFF;
    border: 1px solid #444444;
    padding: 5px 15px;
    border-radius: 3px;
}
QPushButton:hover {
    background-color: #3D3D3D;
}
QProgressBar {
    border: 1px solid #333333;
    border-radius: 2px;
    text-align: center;
    background-color: #1E1E1E;
    color: transparent;
}
QProgressBar::chunk {
    background-color: #00FF00;
}
#rpmBar::chunk {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00FF00, stop:0.7 #FFFF00, stop:1 #FF0000);
}
"""

class TelemetryMainWindow(QMainWindow):
    # Signals to communicate between network thread and GUI thread
    packet_signal = pyqtSignal(GT7TelemetryPacket)
    connection_signal = pyqtSignal(str)
    lost_signal = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GT7 Telemetry Pro - Track Engineer Dashboard")
        self.setGeometry(100, 100, 1280, 800)
        self.setStyleSheet(DARK_STYLE)
        
        self.client = GT7TelemetryClient()
        self.client.on_packet_received = self.packet_signal.emit
        self.client.on_connection_established = self.connection_signal.emit
        self.client.on_connection_lost = self.lost_signal.emit
        
        self.packet_signal.connect(self.update_dashboard)
        self.connection_signal.connect(self.on_connected)
        self.lost_signal.connect(self.on_disconnected)
        
        # History arrays for plotting
        self.history_size = 300 # 5 seconds at 60fps
        self.time_data = np.linspace(-5, 0, self.history_size)
        self.speed_data = np.zeros(self.history_size)
        self.rpm_data = np.zeros(self.history_size)
        self.throttle_data = np.zeros(self.history_size)
        self.brake_data = np.zeros(self.history_size)
        
        self.init_ui()
        
    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # Main Layout
        layout = QVBoxLayout()
        main_widget.setLayout(layout)
        
        # --- HEADER (Connection) ---
        header_layout = QHBoxLayout()
        self.lbl_status = QLabel("Status: Disconnected")
        self.lbl_status.setStyleSheet("color: #FF5555; font-weight: bold; font-size: 16px;")
        
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("Auto-detecting... or enter IP here")
        self.ip_input.setFixedWidth(250)
        
        self.btn_connect = QPushButton("Connect / Auto-Detect")
        self.btn_connect.clicked.connect(self.toggle_connection)
        
        header_layout.addWidget(self.lbl_status)
        header_layout.addStretch()
        header_layout.addWidget(self.ip_input)
        header_layout.addWidget(self.btn_connect)
        layout.addLayout(header_layout)
        
        # --- DASHBOARD (RPM & GEAR) ---
        dash_layout = QVBoxLayout()
        
        # RPM Bar
        self.rpm_bar = QProgressBar()
        self.rpm_bar.setObjectName("rpmBar")
        self.rpm_bar.setFixedHeight(30)
        self.rpm_bar.setRange(0, 10000) # Will be updated dynamically
        dash_layout.addWidget(self.rpm_bar)
        
        info_layout = QHBoxLayout()
        
        # Gear
        self.lbl_gear = QLabel("N")
        self.lbl_gear.setFont(QFont("Consolas", 60, QFont.Weight.Bold))
        self.lbl_gear.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_gear.setFixedWidth(150)
        
        # Speed
        speed_layout = QVBoxLayout()
        self.lbl_speed = QLabel("0")
        self.lbl_speed.setFont(QFont("Consolas", 48, QFont.Weight.Bold))
        self.lbl_speed.setAlignment(Qt.AlignmentFlag.AlignRight)
        lbl_kmh = QLabel("km/h")
        lbl_kmh.setAlignment(Qt.AlignmentFlag.AlignRight)
        speed_layout.addWidget(self.lbl_speed)
        speed_layout.addWidget(lbl_kmh)
        
        info_layout.addWidget(self.lbl_gear)
        info_layout.addStretch()
        info_layout.addLayout(speed_layout)
        
        dash_layout.addLayout(info_layout)
        layout.addLayout(dash_layout)
        
        # --- PEDALS & TYRES ---
        mid_layout = QHBoxLayout()
        
        # Pedals
        pedals_group = QGroupBox("Driver Inputs")
        pedals_layout = QVBoxLayout()
        
        self.bar_throttle = self.create_vertical_bar("#00FF00")
        self.bar_brake = self.create_vertical_bar("#FF0000")
        self.bar_clutch = self.create_vertical_bar("#00AAFF")
        
        p_bars_layout = QHBoxLayout()
        p_bars_layout.addWidget(self.create_bar_container("THR", self.bar_throttle))
        p_bars_layout.addWidget(self.create_bar_container("BRK", self.bar_brake))
        p_bars_layout.addWidget(self.create_bar_container("CLT", self.bar_clutch))
        
        pedals_layout.addLayout(p_bars_layout)
        pedals_group.setLayout(pedals_layout)
        mid_layout.addWidget(pedals_group, 1)
        
        # Tyres
        tyres_group = QGroupBox("Tyre Surface Temps")
        tyres_layout = QGridLayout()
        
        self.lbl_fl_temp = QLabel("FL: 0°C")
        self.lbl_fr_temp = QLabel("FR: 0°C")
        self.lbl_rl_temp = QLabel("RL: 0°C")
        self.lbl_rr_temp = QLabel("RR: 0°C")
        
        tyres_layout.addWidget(self.lbl_fl_temp, 0, 0)
        tyres_layout.addWidget(self.lbl_fr_temp, 0, 1)
        tyres_layout.addWidget(self.lbl_rl_temp, 1, 0)
        tyres_layout.addWidget(self.lbl_rr_temp, 1, 1)
        
        tyres_group.setLayout(tyres_layout)
        mid_layout.addWidget(tyres_group, 2)
        
        layout.addLayout(mid_layout)
        
        # --- REAL-TIME GRAPHS ---
        graphs_group = QGroupBox("Telemetry Live Plots")
        graphs_layout = QVBoxLayout()
        
        pg.setConfigOptions(antialias=True)
        self.plot_widget = pg.GraphicsLayoutWidget()
        
        self.p1 = self.plot_widget.addPlot(title="Speed (km/h) & RPM (x100)")
        self.p1.showGrid(x=True, y=True, alpha=0.3)
        self.curve_speed = self.p1.plot(pen=pg.mkPen('#00FFFF', width=2), name="Speed")
        self.curve_rpm = self.p1.plot(pen=pg.mkPen('#FFFF00', width=2), name="RPM")
        
        self.plot_widget.nextRow()
        
        self.p2 = self.plot_widget.addPlot(title="Throttle / Brake (%)")
        self.p2.showGrid(x=True, y=True, alpha=0.3)
        self.p2.setYRange(0, 100)
        self.curve_throttle = self.p2.plot(pen=pg.mkPen('#00FF00', width=2), fillLevel=0, brush=(0,255,0,50))
        self.curve_brake = self.p2.plot(pen=pg.mkPen('#FF0000', width=2), fillLevel=0, brush=(255,0,0,50))
        
        graphs_layout.addWidget(self.plot_widget)
        graphs_group.setLayout(graphs_layout)
        
        layout.addWidget(graphs_group, 3)

    def create_vertical_bar(self, color):
        bar = QProgressBar()
        bar.setOrientation(Qt.Orientation.Vertical)
        bar.setRange(0, 255)
        bar.setTextVisible(False)
        bar.setStyleSheet(f"""
            QProgressBar {{ border: 1px solid #333; background-color: #111; }}
            QProgressBar::chunk {{ background-color: {color}; }}
        """)
        return bar
        
    def create_bar_container(self, label_text, bar_widget):
        container = QWidget()
        l = QVBoxLayout()
        l.addWidget(bar_widget, alignment=Qt.AlignmentFlag.AlignHCenter)
        lbl = QLabel(label_text)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(lbl)
        container.setLayout(l)
        return container

    def toggle_connection(self):
        if self.client.running:
            self.client.stop()
            self.lbl_status.setText("Status: Disconnected")
            self.lbl_status.setStyleSheet("color: #FF5555; font-weight: bold; font-size: 16px;")
            self.btn_connect.setText("Connect / Auto-Detect")
        else:
            ip = self.ip_input.text().strip()
            self.client.console_ip = ip if ip else None
            self.client.start()
            self.lbl_status.setText("Status: Searching / Listening...")
            self.lbl_status.setStyleSheet("color: #FFAA00; font-weight: bold; font-size: 16px;")
            self.btn_connect.setText("Disconnect")
            
    @pyqtSlot(str)
    def on_connected(self, ip):
        self.lbl_status.setText(f"Status: Connected to {ip}")
        self.lbl_status.setStyleSheet("color: #00FF00; font-weight: bold; font-size: 16px;")
        if not self.ip_input.text():
            self.ip_input.setText(ip)
            
    @pyqtSlot()
    def on_disconnected(self):
        self.lbl_status.setText("Status: Connection Lost (Timeout)")
        self.lbl_status.setStyleSheet("color: #FF5555; font-weight: bold; font-size: 16px;")
            
    @pyqtSlot(GT7TelemetryPacket)
    def update_dashboard(self, packet: GT7TelemetryPacket):
        # Update Gear
        gear = packet.current_gear
        gear_str = str(gear) if gear > 0 and gear < 15 else ("R" if gear == 15 else "N")
        self.lbl_gear.setText(gear_str)
        
        # Update Speed
        self.lbl_speed.setText(f"{int(packet.speed_kmh)}")
        
        # Update RPM Bar
        max_rpm = packet.max_alert_rpm if packet.max_alert_rpm > 0 else 10000
        self.rpm_bar.setMaximum(max_rpm)
        self.rpm_bar.setValue(int(packet.engine_rpm))
        
        # Update Pedals
        self.bar_throttle.setValue(packet.throttle)
        self.bar_brake.setValue(packet.brake)
        self.bar_clutch.setValue(int(packet.clutch * 255))
        
        # Update Tyres
        self.lbl_fl_temp.setText(f"FL: {packet.tyre_temp[0]:.1f}°C")
        self.lbl_fr_temp.setText(f"FR: {packet.tyre_temp[1]:.1f}°C")
        self.lbl_rl_temp.setText(f"RL: {packet.tyre_temp[2]:.1f}°C")
        self.lbl_rr_temp.setText(f"RR: {packet.tyre_temp[3]:.1f}°C")
        
        # Shift data arrays
        self.speed_data = np.roll(self.speed_data, -1)
        self.rpm_data = np.roll(self.rpm_data, -1)
        self.throttle_data = np.roll(self.throttle_data, -1)
        self.brake_data = np.roll(self.brake_data, -1)
        
        # Update latest point
        self.speed_data[-1] = packet.speed_kmh
        self.rpm_data[-1] = packet.engine_rpm / 100.0 # Scale RPM to fit on same graph as speed roughly
        self.throttle_data[-1] = (packet.throttle / 255.0) * 100.0
        self.brake_data[-1] = (packet.brake / 255.0) * 100.0
        
        # Re-plot
        self.curve_speed.setData(self.time_data, self.speed_data)
        self.curve_rpm.setData(self.time_data, self.rpm_data)
        self.curve_throttle.setData(self.time_data, self.throttle_data)
        self.curve_brake.setData(self.time_data, self.brake_data)

    def closeEvent(self, event):
        self.client.stop()
        event.accept()

def main():
    app = QApplication(sys.argv)
    window = TelemetryMainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
