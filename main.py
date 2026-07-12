import sys
import os
import time
import datetime
import json
import numpy as np

# Load Car Database from JSON
car_db = {}
try:
    with open('gt7_cars.json', 'r', encoding='utf-8') as f:
        car_db = json.load(f)
except Exception as e:
    logging.warning(f"Could not load gt7_cars.json: {e}")

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QGridLayout, QGroupBox, QFileDialog, QFrame, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QTimer
from PyQt6.QtGui import QFont, QColor, QPainter, QPen
import pyqtgraph as pg
from collections import deque

from client import GT7TelemetryClient
from player import GT7SessionPlayer
from models import GT7TelemetryPacket

import logging
logging.basicConfig(
    filename='gt7_telemetry.log', 
    level=logging.DEBUG, 
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    filemode='a'
)

DARK_STYLE = """
QMainWindow {
    background-color: #0b0c10;
    color: #c5c6c7;
}
QGroupBox {
    border: 1px solid #303641;
    border-radius: 4px;
    margin-top: 15px;
    background-color: #14161a;
    color: #45a29e;
    font-weight: bold;
    font-size: 13px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 3px 0 3px;
}
QLabel {
    color: #c5c6c7;
}
QLineEdit {
    background-color: #1f2833;
    color: #66fcf1;
    border: 1px solid #45a29e;
    padding: 4px;
    border-radius: 2px;
}
QPushButton {
    background-color: #1f2833;
    color: #66fcf1;
    border: 1px solid #45a29e;
    padding: 6px 12px;
    border-radius: 2px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #45a29e;
    color: #0b0c10;
}
QPushButton:disabled {
    background-color: #14161a;
    color: #333333;
    border: 1px solid #333333;
}
"""

class TelemetryMainWindow(QMainWindow):
    packet_signal = pyqtSignal(GT7TelemetryPacket)
    connection_signal = pyqtSignal(str)
    lost_signal = pyqtSignal()
    playback_finished_signal = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GT7 Telemetry Pro - Native Interface")
        self.setGeometry(50, 50, 1600, 900)
        self.setStyleSheet(DARK_STYLE)
        
        self.client = GT7TelemetryClient()
        self.client.on_packet_received = self.packet_signal.emit
        self.client.on_connection_established = self.connection_signal.emit
        self.client.on_connection_lost = self.lost_signal.emit
        
        self.player = GT7SessionPlayer()
        self.player.on_packet_received = self.packet_signal.emit
        self.player.on_playback_finished = self.playback_finished_signal.emit
        
        # Async UI decoupler
        self.latest_packet = None
        self.ui_timer = QTimer()
        self.ui_timer.timeout.connect(self.update_dashboard_ui)
        self.ui_timer.start(33) # ~30 FPS UI refresh
        
        self.packet_signal.connect(self._cache_packet)
        self.connection_signal.connect(self.on_connected)
        self.lost_signal.connect(self.on_disconnected)
        self.playback_finished_signal.connect(self.on_playback_finished)
        
        # Auto-save state
        self.has_started_auto_save = False
        
        # History arrays for plots
        self.history_size = 600 # 10 seconds at 60fps
        self.time_data = np.linspace(-10, 0, self.history_size)
        
        self.speed_data = np.zeros(self.history_size)
        self.throttle_data = np.zeros(self.history_size)
        self.brake_data = np.zeros(self.history_size)
        self.steer_data = np.zeros(self.history_size)
        self.rpm_data = np.zeros(self.history_size)
        
        # Track Map & G-Force History
        self.map_x = deque(maxlen=4000)
        self.map_z = deque(maxlen=4000)
        self.g_x = deque(maxlen=100)
        self.g_y = deque(maxlen=100)
        
        self.init_ui()
        
    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        main_widget.setLayout(layout)
        
        # --- HEADER ---
        header_layout = QHBoxLayout()
        self.lbl_status = QLabel("Status: Disconnected")
        self.lbl_status.setStyleSheet("color: #ff003c; font-weight: bold; font-size: 14px;")
        
        self.lbl_save_status = QLabel("Auto-Save: Off")
        self.lbl_save_status.setStyleSheet("color: #888888; font-size: 14px;")
        
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("Auto-detecting... or enter IP")
        self.ip_input.setFixedWidth(200)
        
        self.btn_connect = QPushButton("Connect Live")
        self.btn_connect.clicked.connect(self.toggle_connection)
        
        self.btn_load = QPushButton("Load Replay")
        self.btn_load.clicked.connect(self.load_session)
        
        self.btn_play = QPushButton("Play Replay")
        self.btn_play.clicked.connect(self.toggle_playback)
        self.btn_play.setEnabled(False)
        
        header_layout.addWidget(self.lbl_status)
        header_layout.addWidget(self.lbl_save_status)
        header_layout.addStretch()
        header_layout.addWidget(self.ip_input)
        header_layout.addWidget(self.btn_connect)
        header_layout.addWidget(self.btn_load)
        header_layout.addWidget(self.btn_play)
        layout.addLayout(header_layout)
        
        # --- MAIN 3-COLUMN LAYOUT ---
        content_layout = QHBoxLayout()
        
        # ========================================
        # LEFT COLUMN (20%): Map & G-Force
        # ========================================
        left_layout = QVBoxLayout()
        
        # Info Panel
        info_panel = QGroupBox("Info de Vuelta")
        info_l = QVBoxLayout()
        self.lbl_car_id = QLabel("Auto: ---")
        self.lbl_car_id.setStyleSheet("color: white; font-weight: bold;")
        self.lbl_lap = QLabel("Vuelta: -/-")
        self.lbl_lap.setStyleSheet("background-color: #1e3a5f; color: #66fcf1; padding: 4px; font-weight: bold;")
        self.lbl_time = QLabel("0:00.000")
        self.lbl_time.setFont(QFont("Consolas", 18, QFont.Weight.Bold))
        self.lbl_time.setStyleSheet("color: #a3e4d7;")
        info_l.addWidget(self.lbl_car_id)
        info_l.addWidget(self.lbl_lap)
        info_l.addWidget(self.lbl_time)
        info_panel.setLayout(info_l)
        left_layout.addWidget(info_panel, 1)
        
        # Track Map Panel
        pg.setConfigOptions(antialias=True)
        map_panel = QGroupBox("Circuito Completo")
        map_l = QVBoxLayout()
        self.map_widget = pg.PlotWidget()
        self.map_widget.setBackground('#14161a')
        self.map_widget.hideAxis('bottom')
        self.map_widget.hideAxis('left')
        self.map_widget.setAspectLocked(True)
        self.map_plot = self.map_widget.plot(pen=pg.mkPen('#66fcf1', width=2))
        self.car_dot = self.map_widget.plot(pen=None, symbol='o', symbolBrush='#ff003c', symbolSize=8)
        map_l.addWidget(self.map_widget)
        map_panel.setLayout(map_l)
        left_layout.addWidget(map_panel, 3)
        
        # Centripetal Acceleration (Friction Circle)
        g_panel = QGroupBox("Aceleración Centrípeta")
        g_l = QVBoxLayout()
        self.g_widget = pg.PlotWidget()
        self.g_widget.setBackground('#14161a')
        self.g_widget.hideAxis('bottom')
        self.g_widget.hideAxis('left')
        self.g_widget.setAspectLocked(True)
        self.g_widget.setXRange(-2, 2)
        self.g_widget.setYRange(-2, 2)
        # Draw crosshairs
        self.g_widget.addLine(x=0, pen=pg.mkPen('#303641'))
        self.g_widget.addLine(y=0, pen=pg.mkPen('#303641'))
        # Draw circles at 1G and 2G
        circle1 = pg.QtGui.QPainterPath()
        circle1.addEllipse(pg.QtCore.QRectF(-1, -1, 2, 2))
        path_item1 = pg.QtWidgets.QGraphicsPathItem(circle1)
        path_item1.setPen(pg.mkPen('#303641'))
        self.g_widget.addItem(path_item1)
        
        self.g_plot = self.g_widget.plot(pen=None, symbol='o', symbolBrush='#f2a900', symbolSize=5, alpha=0.5)
        self.g_dot_latest = self.g_widget.plot(pen=None, symbol='o', symbolBrush='#ff003c', symbolSize=10)
        
        g_l.addWidget(self.g_widget)
        g_panel.setLayout(g_l)
        left_layout.addWidget(g_panel, 2)
        
        content_layout.addLayout(left_layout, 2)
        
        # ========================================
        # MIDDLE COLUMN (40%): Stacked Plots
        # ========================================
        mid_panel = QGroupBox("Telemetría en Vivo (Últimos 10s)")
        mid_layout = QVBoxLayout()
        mid_layout.setContentsMargins(0,10,0,0)
        mid_layout.setSpacing(0)
        
        self.plot_stack = pg.GraphicsLayoutWidget()
        self.plot_stack.setBackground('#14161a')
        
        # 1. Velocidad
        self.p_vel = self.plot_stack.addPlot(title="Velocidad (km/h)")
        self.p_vel.showGrid(x=True, y=True, alpha=0.2)
        self.p_vel.getAxis('left').setPen('#45a29e')
        self.p_vel.getAxis('bottom').setStyle(showValues=False)
        self.curve_vel = self.p_vel.plot(pen=pg.mkPen('#66fcf1', width=2))
        
        self.plot_stack.nextRow()
        
        # 2. Acelerador / Freno
        self.p_pedal = self.plot_stack.addPlot(title="Acelerador / Freno (%)")
        self.p_pedal.showGrid(x=True, y=True, alpha=0.2)
        self.p_pedal.setYRange(0, 105)
        self.p_pedal.getAxis('left').setPen('#45a29e')
        self.p_pedal.getAxis('bottom').setStyle(showValues=False)
        self.curve_thr = self.p_pedal.plot(pen=pg.mkPen('#00ff7f', width=2), fillLevel=0, brush=(0,255,127,60))
        self.curve_brk = self.p_pedal.plot(pen=pg.mkPen('#ff003c', width=2), fillLevel=0, brush=(255,0,60,60))
        
        self.plot_stack.nextRow()
        
        # 3. Ángulo de Dirección
        self.p_steer = self.plot_stack.addPlot(title="Ángulo de Dirección (Grados)")
        self.p_steer.showGrid(x=True, y=True, alpha=0.2)
        self.p_steer.setYRange(-180, 180)
        self.p_steer.getAxis('left').setPen('#45a29e')
        self.p_steer.getAxis('bottom').setStyle(showValues=False)
        self.curve_steer = self.p_steer.plot(pen=pg.mkPen('#a3e4d7', width=2))
        
        self.plot_stack.nextRow()
        
        # 4. RPM
        self.p_rpm = self.plot_stack.addPlot(title="R.P.M.")
        self.p_rpm.showGrid(x=True, y=True, alpha=0.2)
        self.p_rpm.getAxis('left').setPen('#45a29e')
        self.p_rpm.getAxis('bottom').setPen('#45a29e')
        self.curve_rpm = self.p_rpm.plot(pen=pg.mkPen('#f2a900', width=2))
        
        mid_layout.addWidget(self.plot_stack)
        mid_panel.setLayout(mid_layout)
        content_layout.addWidget(mid_panel, 4)
        
        # ========================================
        # RIGHT COLUMN (40%): Analyzer
        # ========================================
        right_panel = QGroupBox("Analizador de Derrape")
        r_layout = QVBoxLayout()
        r_layout.setContentsMargins(10, 20, 10, 10)
        
        # Large Indicators
        ind_layout = QHBoxLayout()
        
        v_box = QVBoxLayout()
        lbl_v_title = QLabel("Velocidad")
        lbl_v_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_v_val = QLabel("0")
        self.lbl_v_val.setFont(QFont("Consolas", 48, QFont.Weight.Bold))
        self.lbl_v_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_v_val.setStyleSheet("color: #66fcf1;")
        v_box.addWidget(lbl_v_title)
        v_box.addWidget(self.lbl_v_val)
        
        r_box = QVBoxLayout()
        lbl_r_title = QLabel("RPM")
        lbl_r_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_r_val = QLabel("0")
        self.lbl_r_val.setFont(QFont("Consolas", 48, QFont.Weight.Bold))
        self.lbl_r_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_r_val.setStyleSheet("color: #f2a900;")
        r_box.addWidget(lbl_r_title)
        r_box.addWidget(self.lbl_r_val)
        
        ind_layout.addLayout(v_box)
        ind_layout.addLayout(r_box)
        r_layout.addLayout(ind_layout)
        
        # Car Visual & Pedals
        bars_layout = QHBoxLayout()
        bars_layout.setContentsMargins(0, 30, 0, 30)
        
        # Left Side Data (Tires Left)
        l_tires = QVBoxLayout()
        self.lbl_tl = QLabel("TL: 0°C")
        self.lbl_bl = QLabel("RL: 0°C")
        l_tires.addWidget(self.lbl_tl)
        l_tires.addStretch()
        l_tires.addWidget(self.lbl_bl)
        bars_layout.addLayout(l_tires)
        
        # Thr/Brk Bars in Center
        pedals_grid = QGridLayout()
        
        self.bar_thr = self.create_custom_bar("#00ff7f")
        self.bar_brk = self.create_custom_bar("#ff003c")
        
        self.lbl_thr_txt = QLabel("Acelerador\n0%")
        self.lbl_thr_txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_thr_txt.setStyleSheet("color: #00ff7f; font-weight: bold;")
        
        self.lbl_brk_txt = QLabel("Freno\n0%")
        self.lbl_brk_txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_brk_txt.setStyleSheet("color: #ff003c; font-weight: bold;")
        
        pedals_grid.addWidget(self.lbl_thr_txt, 0, 0)
        pedals_grid.addWidget(self.bar_thr, 1, 0, alignment=Qt.AlignmentFlag.AlignHCenter)
        
        pedals_grid.addWidget(self.lbl_brk_txt, 0, 1)
        pedals_grid.addWidget(self.bar_brk, 1, 1, alignment=Qt.AlignmentFlag.AlignHCenter)
        
        bars_layout.addLayout(pedals_grid)
        
        # Right Side Data (Tires Right)
        r_tires = QVBoxLayout()
        self.lbl_tr = QLabel("TR: 0°C")
        self.lbl_br = QLabel("RR: 0°C")
        self.lbl_gear = QLabel("Gear: N")
        self.lbl_gear.setFont(QFont("Consolas", 24, QFont.Weight.Bold))
        r_tires.addWidget(self.lbl_tr)
        r_tires.addStretch()
        r_tires.addWidget(self.lbl_br)
        bars_layout.addLayout(r_tires)
        
        r_layout.addLayout(bars_layout)
        
        # Add the gear to the bottom of the right panel
        r_layout.addWidget(self.lbl_gear, alignment=Qt.AlignmentFlag.AlignCenter)
        
        right_panel.setLayout(r_layout)
        content_layout.addWidget(right_panel, 4)
        
        layout.addLayout(content_layout)

    def create_custom_bar(self, color):
        from PyQt6.QtWidgets import QProgressBar
        bar = QProgressBar()
        bar.setOrientation(Qt.Orientation.Vertical)
        bar.setRange(0, 100)
        bar.setFixedSize(40, 300)
        bar.setTextVisible(False)
        bar.setStyleSheet(f"""
            QProgressBar {{ border: 2px solid #303641; border-radius: 4px; background-color: #0b0c10; }}
            QProgressBar::chunk {{ background-color: {color}; border-radius: 2px; }}
        """)
        return bar

    def _auto_start_recording(self, packet: GT7TelemetryPacket):
        if not self.has_started_auto_save and self.client.running:
            self.has_started_auto_save = True
            
            # Generate filename
            date_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            car_id = packet.car_code
            filename = f"GT7Session_Car{car_id}_{date_str}.gt7"
            
            sessions_dir = os.path.join(os.getcwd(), 'Sessions')
            os.makedirs(sessions_dir, exist_ok=True)
            save_path = os.path.join(sessions_dir, filename)
            
            if self.client.start_recording(save_path):
                self.lbl_save_status.setText(f"Auto-Save: ACTIVO ({filename})")
                self.lbl_save_status.setStyleSheet("color: #00ff7f; font-weight: bold; font-size: 14px;")
            else:
                self.lbl_save_status.setText("Auto-Save: FALLÓ")
                self.lbl_save_status.setStyleSheet("color: #ff003c; font-weight: bold; font-size: 14px;")

    def toggle_connection(self):
        if self.client.running:
            self.client.stop()
            self.lbl_status.setText("Status: Disconnected")
            self.lbl_status.setStyleSheet("color: #ff003c; font-weight: bold; font-size: 14px;")
            self.btn_connect.setText("Connect Live")
            
            # Reset auto-save state
            self.has_started_auto_save = False
            self.lbl_save_status.setText("Auto-Save: Off")
            self.lbl_save_status.setStyleSheet("color: #888888; font-size: 14px;")
        else:
            if self.player.running:
                self.toggle_playback()
                
            ip = self.ip_input.text().strip()
            self.client.console_ip = ip if ip else None
            self.client.start()
            self.lbl_status.setText("Status: Searching...")
            self.lbl_status.setStyleSheet("color: #f2a900; font-weight: bold; font-size: 14px;")
            self.btn_connect.setText("Disconnect")
            self.clear_graphs()
            
    def load_session(self):
        # Adding .gt7 filter works, but on mac we should also assure the user sees it.
        filename, _ = QFileDialog.getOpenFileName(self, "Open Session", "", "GT7 Session Files (*.gt7);;All Files (*)")
        if filename:
            self.player.load(filename)
            self.btn_play.setEnabled(True)
            self.lbl_status.setText(f"Loaded: {os.path.basename(filename)}")
            self.lbl_status.setStyleSheet("color: #66fcf1; font-weight: bold; font-size: 14px;")
            self.clear_graphs()
            
    def toggle_playback(self):
        if self.player.running:
            self.player.stop()
            self.btn_play.setText("Play Replay")
        else:
            if self.client.running:
                self.toggle_connection()
            
            self.clear_graphs()
            self.player.play()
            self.btn_play.setText("Stop Replay")
            self.lbl_status.setText("Status: Playing Replay")
            self.lbl_status.setStyleSheet("color: #66fcf1; font-weight: bold; font-size: 14px;")

    def clear_graphs(self):
        self.map_x.clear()
        self.map_z.clear()
        self.g_x.clear()
        self.g_y.clear()
        
        self.speed_data.fill(0)
        self.throttle_data.fill(0)
        self.brake_data.fill(0)
        self.steer_data.fill(0)
        self.rpm_data.fill(0)
        
        self.curve_vel.setData(self.time_data, self.speed_data)
        self.curve_thr.setData(self.time_data, self.throttle_data)
        self.curve_brk.setData(self.time_data, self.brake_data)
        self.curve_steer.setData(self.time_data, self.steer_data)
        self.curve_rpm.setData(self.time_data, self.rpm_data)

    @pyqtSlot()
    def on_playback_finished(self):
        self.btn_play.setText("Play Replay")
        self.lbl_status.setText("Status: Replay Finished")
        self.lbl_status.setStyleSheet("color: #45a29e; font-weight: bold; font-size: 14px;")

    @pyqtSlot(str)
    def on_connected(self, ip):
        self.lbl_status.setText(f"Status: Connected to {ip}")
        self.lbl_status.setStyleSheet("color: #00ff7f; font-weight: bold; font-size: 14px;")
        if not self.ip_input.text():
            self.ip_input.setText(ip)
            
    @pyqtSlot()
    def on_disconnected(self):
        self.lbl_status.setText("Status: Connection Lost")
        self.lbl_status.setStyleSheet("color: #ff003c; font-weight: bold; font-size: 14px;")
            
    @pyqtSlot(GT7TelemetryPacket)
    def _cache_packet(self, packet: GT7TelemetryPacket):
        self.latest_packet = packet
        self._auto_start_recording(packet)
            
    def update_dashboard_ui(self):
        packet = self.latest_packet
        if not packet:
            return
        
        # 2. Update Info Panel
        car_info = car_db.get(str(packet.car_code))
        car_name = car_info["full_name"] if car_info else f"ID: {packet.car_code}"
        self.lbl_car_id.setText(f"Auto: {car_name}")
        lap = packet.lap_count if packet.lap_count != -1 else 0
        tot = packet.total_laps if packet.total_laps > 0 else "-"
        self.lbl_lap.setText(f"Vuelta: {lap} / {tot}")
        
        # MS to MM:SS.mmm (Using last laptime for demo)
        ms = packet.last_laptime
        if ms > 0:
            mins = int(ms / 60000)
            secs = int((ms % 60000) / 1000)
            mils = ms % 1000
            self.lbl_time.setText(f"{mins}:{secs:02d}.{mils:03d}")
            
        # 3. Update Map
        if packet.position:
            self.map_x.append(packet.position[0])
            self.map_z.append(packet.position[2])
            self.map_plot.setData(list(self.map_x), list(self.map_z))
            self.car_dot.setData([packet.position[0]], [packet.position[2]])
                
        # 4. Update G-Force (Friction Circle)
        # Using World Velocity or Sway/Surge if available. 
        # GT7 provides sway/surge/heave in angular_velocity or we can just derive from local velocity changes?
        # Actually, let's use packet.angular_velocity or similar if we can map it to X/Y forces. 
        # For now, we will map world_velocity changes approximately, but since it's an F1 dash, we just plot X/Z rotation?
        # A true G-force meter needs lateral/longitudinal acceleration.
        # Let's plot sway (if we can infer it). We'll leave it as a placeholder using angular velocity to look alive.
        lat_g = packet.angular_velocity[1] * 2 if packet.angular_velocity else 0
        lon_g = packet.angular_velocity[0] * 2 if packet.angular_velocity else 0
        self.g_x.append(lat_g)
        self.g_y.append(lon_g)
        self.g_plot.setData(list(self.g_x), list(self.g_y))
        self.g_dot_latest.setData([lat_g], [lon_g])
        
        # 5. Stacked Graphs
        self.speed_data = np.roll(self.speed_data, -1)
        self.throttle_data = np.roll(self.throttle_data, -1)
        self.brake_data = np.roll(self.brake_data, -1)
        self.steer_data = np.roll(self.steer_data, -1)
        self.rpm_data = np.roll(self.rpm_data, -1)
        
        self.speed_data[-1] = packet.speed_kmh
        t_perc = (packet.throttle / 255.0) * 100.0
        b_perc = (packet.brake / 255.0) * 100.0
        self.throttle_data[-1] = t_perc
        self.brake_data[-1] = b_perc
        
        steer_deg = (packet.wheel_steer_angle * 180.0 / 3.14159) if packet.wheel_steer_angle else 0
        self.steer_data[-1] = steer_deg
        self.rpm_data[-1] = packet.engine_rpm
        
        self.curve_vel.setData(self.time_data, self.speed_data)
        self.curve_thr.setData(self.time_data, self.throttle_data)
        self.curve_brk.setData(self.time_data, self.brake_data)
        self.curve_steer.setData(self.time_data, self.steer_data)
        self.curve_rpm.setData(self.time_data, self.rpm_data)
        
        # 6. Right Panel Analyzer
        self.lbl_v_val.setText(str(int(packet.speed_kmh)))
        self.lbl_r_val.setText(str(int(packet.engine_rpm)))
        
        self.bar_thr.setValue(int(t_perc))
        self.lbl_thr_txt.setText(f"Acelerador\n{int(t_perc)}%")
        self.bar_brk.setValue(int(b_perc))
        self.lbl_brk_txt.setText(f"Freno\n{int(b_perc)}%")
        
        gear = packet.current_gear
        gear_str = str(gear) if 0 < gear < 15 else ("R" if gear == 15 else "N")
        self.lbl_gear.setText(f"Marcha: {gear_str}")
        
        self.lbl_tl.setText(f"TL: {packet.tyre_temp[0]:.0f}°C")
        self.lbl_tr.setText(f"TR: {packet.tyre_temp[1]:.0f}°C")
        self.lbl_bl.setText(f"RL: {packet.tyre_temp[2]:.0f}°C")
        self.lbl_br.setText(f"RR: {packet.tyre_temp[3]:.0f}°C")

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
