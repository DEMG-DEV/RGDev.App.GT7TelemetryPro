import os
import datetime
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QGridLayout, 
                             QGroupBox, QFileDialog)
from PyQt6.QtCore import Qt, pyqtSlot, QTimer
from PyQt6.QtGui import QFont

from core.models import GT7TelemetryPacket
from core.car_database import CarDatabase
from core.math_channels import MathEngine
from core.lap_manager import LapManager
from core.alert_engine import AlertEngine
from services.live_client import GT7LiveClient
from services.replay_player import GT7SessionPlayer

from ui.widgets.map_widget import MapWidget
from ui.widgets.gforce_widget import GForceWidget
from ui.widgets.telemetry_graphs import TelemetryGraphsWidget
from ui.widgets.delta_widget import DeltaWidget
from ui.widgets.alert_widget import AlertWidget

class TelemetryMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GT7 Telemetry Pro - Native Interface")
        self.setGeometry(50, 50, 1600, 900)
        self.load_styles()
        
        self.car_db = CarDatabase()
        
        self.math_engine = MathEngine()
        self.lap_manager = LapManager()
        self.alert_engine = AlertEngine()
        
        self.latest_delta_ms = None
        
        self.client = GT7LiveClient()
        self.client.packet_signal.connect(self._cache_packet)
        self.client.connection_established.connect(self.on_connected)
        self.client.connection_lost.connect(self.on_disconnected)
        self.client.error_occurred.connect(self.on_client_error)
        
        self.player = GT7SessionPlayer()
        self.player.packet_signal.connect(self._cache_packet)
        self.player.playback_finished.connect(self.on_playback_finished)
        
        self.latest_packet = None
        self.ui_timer = QTimer()
        self.ui_timer.timeout.connect(self.update_dashboard_ui)
        self.ui_timer.start(33) 
        
        self.has_started_auto_save = False
        
        self.init_ui()
        
    def load_styles(self):
        style_path = os.path.join(os.path.dirname(__file__), 'styles', 'dark_theme.qss')
        if os.path.exists(style_path):
            with open(style_path, 'r') as f:
                self.setStyleSheet(f.read())
        
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
        
        # LEFT COLUMN (20%): Map & G-Force
        left_layout = QVBoxLayout()
        
        info_panel = QGroupBox("Info de Vuelta")
        info_l = QVBoxLayout()
        self.lbl_car_id = QLabel("Auto: ---")
        self.lbl_car_id.setStyleSheet("color: white; font-weight: bold;")
        self.lbl_lap = QLabel("Vuelta: -/-")
        self.lbl_lap.setStyleSheet("background-color: #1e3a5f; color: #66fcf1; padding: 4px; font-weight: bold;")
        self.lbl_time = QLabel("0:00.000")
        self.lbl_time.setFont(QFont("Consolas", 18, QFont.Weight.Bold))
        self.lbl_time.setStyleSheet("color: #a3e4d7;")
        self.lbl_fuel_est = QLabel("Laps Restantes: ---")
        self.lbl_fuel_est.setStyleSheet("color: #f2a900; font-weight: bold;")
        self.lbl_wot = QLabel("WOT: NO")
        self.lbl_wot.setStyleSheet("color: gray;")
        
        info_l.addWidget(self.lbl_car_id)
        info_l.addWidget(self.lbl_lap)
        info_l.addWidget(self.lbl_time)
        info_l.addWidget(self.lbl_fuel_est)
        info_l.addWidget(self.lbl_wot)
        info_panel.setLayout(info_l)
        left_layout.addWidget(info_panel, 1)
        
        self.map_widget = MapWidget()
        left_layout.addWidget(self.map_widget, 3)
        
        self.gforce_widget = GForceWidget()
        left_layout.addWidget(self.gforce_widget, 2)
        
        content_layout.addLayout(left_layout, 2)
        
        # MIDDLE COLUMN (40%): Stacked Plots & Delta
        mid_layout = QVBoxLayout()
        self.graphs_widget = TelemetryGraphsWidget()
        self.delta_widget = DeltaWidget()
        self.delta_widget.setFixedHeight(150)
        
        mid_layout.addWidget(self.graphs_widget, 4)
        mid_layout.addWidget(self.delta_widget, 1)
        
        content_layout.addLayout(mid_layout, 4)
        
        # RIGHT COLUMN (40%): Analyzer & Alerts
        right_panel = QGroupBox("Analizador de Derrape")
        r_layout = QVBoxLayout()
        r_layout.setContentsMargins(10, 20, 10, 10)
        
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
        
        bars_layout = QHBoxLayout()
        bars_layout.setContentsMargins(0, 30, 0, 30)
        
        l_tires = QVBoxLayout()
        self.lbl_tl = QLabel("TL: 0°C")
        self.lbl_bl = QLabel("RL: 0°C")
        l_tires.addWidget(self.lbl_tl)
        l_tires.addStretch()
        l_tires.addWidget(self.lbl_bl)
        bars_layout.addLayout(l_tires)
        
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
        r_layout.addWidget(self.lbl_gear, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.alert_widget = AlertWidget()
        r_layout.addWidget(self.alert_widget)
        
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
            filename = "telemetry_master.sqlite"
            
            sessions_dir = os.path.join(os.getcwd(), 'Sessions')
            os.makedirs(sessions_dir, exist_ok=True)
            save_path = os.path.join(sessions_dir, filename)
            
            car_db = CarDatabase()
            car_name = car_db.get_car_name(packet.car_code)
            
            if self.client.start_recording(save_path, packet.car_code, car_name):
                self.lbl_save_status.setText(f"Auto-Save: ACTIVO (Master DB)")
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
            
            self.has_started_auto_save = False
            self.lbl_save_status.setText("Auto-Save: Off")
            self.lbl_save_status.setStyleSheet("color: #888888; font-size: 14px;")
        else:
            if self.player.running:
                self.toggle_playback()
                
            ip = self.ip_input.text().strip()
            self.client.console_ip = ip if ip else None
            self.client.start()
            if ip:
                self.lbl_status.setText(f"Status: Esperando telemetría de {ip} (Entra a pista)...")
            else:
                self.lbl_status.setText("Status: Buscando consola (Entra a pista)...")
            self.lbl_status.setStyleSheet("color: #f2a900; font-weight: bold; font-size: 14px;")
            self.btn_connect.setText("Disconnect")
            self.clear_graphs()
            
    def load_session(self):
        sessions_dir = os.path.join(os.getcwd(), 'Sessions')
        master_db = os.path.join(sessions_dir, 'telemetry_master.sqlite')
        
        if not os.path.exists(master_db):
            self.lbl_status.setText("Status: No Master DB found")
            return
            
        import sqlite3
        from PyQt6.QtWidgets import QInputDialog
        
        try:
            with sqlite3.connect(master_db) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, start_time, car_name, total_laps, best_laptime FROM sessions ORDER BY id DESC")
                sessions = cursor.fetchall()
                
            if not sessions:
                self.lbl_status.setText("Status: No sessions found")
                return
                
            session_items = []
            session_ids = []
            for s in sessions:
                s_id, s_time, c_name, t_laps, b_lap = s
                # Format b_lap from ms to MM:SS.ms
                if b_lap and b_lap > 0:
                    minutes = b_lap // 60000
                    seconds = (b_lap % 60000) / 1000
                    lap_str = f"{minutes:02d}:{seconds:06.3f}"
                else:
                    lap_str = "N/A"
                    
                display_text = f"#{s_id} - {s_time[:16]} | {c_name} | Laps: {t_laps} | Best: {lap_str}"
                session_items.append(display_text)
                session_ids.append(s_id)
                
            item, ok = QInputDialog.getItem(
                self, 
                "Select Session", 
                "Choose a historical session to replay:", 
                session_items, 
                0, 
                False
            )
            
            if ok and item:
                index = session_items.index(item)
                selected_id = session_ids[index]
                self.player.load(master_db, selected_id)
                self.player.play()
                self.btn_play.setEnabled(True)
                self.lbl_status.setText(f"Status: Playing Session #{selected_id}")
                self.lbl_status.setStyleSheet("color: #00ff7f; font-weight: bold; font-size: 14px;")
                self.btn_connect.setEnabled(False)
        except Exception as e:
            self.lbl_status.setText(f"Status: Error loading sessions ({e})")
            logging.error(f"Failed to load sessions: {e}")
            
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
        self.map_widget.clear()
        self.gforce_widget.clear()
        self.graphs_widget.clear()
        
        # Resetear motores al limpiar gráficas (ej. cambio de pista/coche)
        self.math_engine = MathEngine()
        self.lap_manager = LapManager()
        self.alert_engine = AlertEngine()
        self.latest_delta_ms = None

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

    @pyqtSlot(str)
    def on_client_error(self, err_msg):
        self.lbl_status.setText(f"Error: {err_msg}")
        self.lbl_status.setStyleSheet("color: #ff003c; font-weight: bold; font-size: 12px;")
            
    @pyqtSlot(GT7TelemetryPacket)
    def _cache_packet(self, packet: GT7TelemetryPacket):
        self.latest_packet = packet
        
        # Motores F1/Le Mans
        metrics = self.math_engine.process_packet(packet)
        delta = self.lap_manager.process_packet(packet)
        if delta is not None:
            self.latest_delta_ms = delta
            
        alerts = self.alert_engine.check_alerts(packet, metrics)
        for severity, title, msg in alerts:
            self.alert_widget.push_alert(severity, title, msg)
        
        # We must add to deques/arrays at 60Hz to not miss points
        if packet.position:
            self.map_widget.add_point(packet.position[0], packet.position[2], packet.throttle, packet.brake)
            
        lat_g = packet.angular_velocity[1] * 2 if packet.angular_velocity else 0
        lon_g = packet.angular_velocity[0] * 2 if packet.angular_velocity else 0
        self.gforce_widget.add_point(lat_g, lon_g)
        
        t_perc = (packet.throttle / 255.0) * 100.0
        b_perc = (packet.brake / 255.0) * 100.0
        steer_deg = (packet.wheel_steer_angle * 180.0 / 3.14159) if packet.wheel_steer_angle else 0
        self.graphs_widget.add_data(packet.speed_kmh, t_perc, b_perc, steer_deg, packet.engine_rpm)
        
        self._auto_start_recording(packet)
            
    def update_dashboard_ui(self):
        packet = self.latest_packet
        if not packet:
            return
            
        self.map_widget.update_plot()
        self.gforce_widget.update_plot()
        self.graphs_widget.update_plot()
        
        if self.latest_delta_ms is not None:
            self.delta_widget.update_data(self.latest_delta_ms)
            
        metrics = self.math_engine.process_packet(packet)
        est = metrics.get('estimated_laps_remaining', 999.0)
        est_str = "999+" if est >= 999.0 else f"{est:.1f}"
        self.lbl_fuel_est.setText(f"Laps Restantes: {est_str}")
        
        if metrics.get('is_wot', False):
            self.lbl_wot.setText("WOT: YES")
            self.lbl_wot.setStyleSheet("color: #00ff7f; font-weight: bold; background-color: #14161a; padding: 2px;")
        else:
            self.lbl_wot.setText("WOT: NO")
            self.lbl_wot.setStyleSheet("color: gray; padding: 2px;")
        
        car_name = self.car_db.get_car_name(packet.car_code)
        self.lbl_car_id.setText(f"Auto: {car_name}")
        
        lap = packet.lap_count if packet.lap_count != -1 else 0
        tot = packet.total_laps if packet.total_laps > 0 else "-"
        self.lbl_lap.setText(f"Vuelta: {lap} / {tot}")
        
        ms = packet.last_laptime
        if ms > 0:
            mins = int(ms / 60000)
            secs = int((ms % 60000) / 1000)
            mils = ms % 1000
            self.lbl_time.setText(f"{mins}:{secs:02d}.{mils:03d}")
            
        t_perc = (packet.throttle / 255.0) * 100.0
        b_perc = (packet.brake / 255.0) * 100.0
        
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
        self.player.stop()
        event.accept()
