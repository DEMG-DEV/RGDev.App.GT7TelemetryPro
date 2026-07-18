import os
import datetime
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QGridLayout, 
                             QGroupBox, QFileDialog, QMessageBox, QProgressDialog, QProgressBar)
from PyQt6.QtCore import Qt, pyqtSlot, QTimer
from core.db_portability import export_database, validate_import_file, import_database_merge, import_database_replace
from PyQt6.QtGui import QFont

from core.models import GT7TelemetryPacket
from core.car_database import CarDatabase
from core.math_channels import MathEngine
from core.lap_manager import LapManager
from core.alert_engine import AlertEngine
from services.live_client import GT7LiveClient
from ui.widgets.map_widget import MapWidget
from ui.widgets.gforce_widget import GForceWidget
from ui.widgets.telemetry_graphs import TelemetryGraphsWidget
from ui.widgets.delta_widget import DeltaWidget
from core.config import APP_VERSION
from ui.widgets.alert_widget import AlertWidget
from ui.workspace import ProfessionalWorkspace
from ui.widgets.circular_gauge import CircularGaugeWidget
from ui.widgets.tyre_temp_gauge import TyreTempGauge
from ui.theme import Theme
from services.updater import UpdateChecker, UpdateDownloader, apply_update_and_restart
import math

class TelemetryMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"GT7 Telemetry Pro - Native Interface v{APP_VERSION}")
        from PyQt6.QtGui import QIcon
        import os
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'app_icon.png')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.setGeometry(50, 50, 1600, 900)
        self.load_styles()
        
        self.car_db = CarDatabase()
        
        self.math_engine = MathEngine()
        self.lap_manager = LapManager()
        self.alert_engine = AlertEngine()
        
        self.latest_delta_ms = None
        self.latest_packet = None
        self.current_lap = -1
        self.laps_measured = 0
        self.fuel_at_lap_start = -1.0
        self.last_fuel_consumed = 0.0
        
        self.client = GT7LiveClient()
        self.client.packet_signal.connect(self._cache_packet)
        self.client.connection_established.connect(self.on_connected)
        self.client.connection_lost.connect(self.on_disconnected)
        self.client.error_occurred.connect(self.on_client_error)
        
        self.latest_packet = None
        self.ui_timer = QTimer()
        self.ui_timer.timeout.connect(self.update_dashboard_ui)
        self.ui_timer.start(33) 
        
        self.init_ui()
        self.check_for_updates()
        
    def check_for_updates(self):
        self.updater = UpdateChecker()
        self.updater.update_available.connect(self.on_update_available)
        self.updater.error_occurred.connect(lambda e: print(f"Update Check Error: {e}"))
        self.updater.start()

    def on_update_available(self, version, download_url):
        msg = QMessageBox()
        msg.setWindowTitle("¡Actualización Disponible!")
        msg.setText(f"Una nueva versión (v{version}) de GT7 Telemetry Pro está disponible.")
        msg.setInformativeText("¿Deseas descargar e instalar la actualización ahora? El programa se reiniciará automáticamente.")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.Yes)
        
        if msg.exec() == QMessageBox.StandardButton.Yes:
            self.start_download(download_url)

    def start_download(self, url):
        self.progress_dialog = QProgressDialog("Descargando actualización...", "Cancelar", 0, 100, self)
        self.progress_dialog.setWindowTitle("Descargando")
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setValue(0)
        
        self.downloader = UpdateDownloader(url)
        self.downloader.progress_update.connect(self.progress_dialog.setValue)
        self.downloader.download_complete.connect(self.on_download_complete)
        self.downloader.error_occurred.connect(self.on_update_error)
        
        self.progress_dialog.canceled.connect(self.downloader.terminate)
        self.downloader.start()

    def on_download_complete(self, extract_dir):
        self.progress_dialog.setValue(100)
        QMessageBox.information(self, "Actualización Lista", "La actualización se ha descargado. El programa se cerrará para aplicarla y luego se reiniciará.")
        apply_update_and_restart(extract_dir)

    def on_update_error(self, err_msg):
        self.progress_dialog.close()
        QMessageBox.warning(self, "Error de Actualización", f"Hubo un problema al descargar la actualización:\\n{err_msg}")

    def load_styles(self):
        style_path = os.path.join(os.path.dirname(__file__), 'styles', 'daylight_theme.qss')
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
        self.lbl_status.setStyleSheet(f"color: {Theme.STATUS_ERROR}; font-weight: bold; font-size: 14px;")
        
        self.btn_record = QPushButton("⏺ Iniciar Grabación")
        self.btn_record.clicked.connect(self.toggle_recording)
        self.btn_record.setEnabled(False)
        self.btn_record.setFixedWidth(160)
        
        self.lbl_rec_status = QLabel("")
        self.lbl_rec_status.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 14px;")
        
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("Auto-detecting... or enter IP")
        self.ip_input.setFixedWidth(200)
        
        self.btn_connect = QPushButton("Connect Live")
        self.btn_connect.clicked.connect(self.toggle_connection)
        
        self.btn_analysis = QPushButton("Historial y Análisis")
        self.btn_analysis.clicked.connect(self.open_analysis)
        
        self.btn_pro_analysis = QPushButton("Pro Analysis")
        self.btn_pro_analysis.clicked.connect(self.open_pro_analysis)
        self.btn_pro_analysis.setStyleSheet(Theme.btn_style(
            Theme.ACCENT_BLUE, '#FFFFFF', border_color='#2471A3', hover_bg='#3498DB'
        ))
        
        header_layout.addWidget(self.lbl_status)
        header_layout.addWidget(self.btn_record)
        header_layout.addWidget(self.lbl_rec_status)
        header_layout.addStretch()
        self.btn_export = QPushButton("📦 Exportar BD")
        self.btn_export.clicked.connect(self.export_database_action)
        self.btn_export.setStyleSheet(Theme.btn_style(
            '#E0E0E0', Theme.TEXT_PRIMARY, hover_bg='#D0D0D0'
        ))

        self.btn_import = QPushButton("📥 Importar BD")
        self.btn_import.clicked.connect(self.import_database_action)
        self.btn_import.setStyleSheet(Theme.btn_style(
            '#E0E0E0', Theme.TEXT_PRIMARY, hover_bg='#D0D0D0'
        ))

        self.btn_sync = QPushButton("🔄 Sync LAN")
        self.btn_sync.clicked.connect(self.open_sync_dialog)
        self.btn_sync.setStyleSheet(Theme.btn_style(
            Theme.ACCENT_DARK, '#FFFFFF', border_color='#1A252F', hover_bg='#34495E'
        ))

        header_layout.addWidget(QLabel("PS IP:"))
        header_layout.addWidget(self.ip_input)
        header_layout.addWidget(self.btn_connect)
        header_layout.addWidget(self.btn_analysis)
        header_layout.addWidget(self.btn_pro_analysis)
        header_layout.addWidget(self.btn_export)
        header_layout.addWidget(self.btn_import)
        header_layout.addWidget(self.btn_sync)
        layout.addLayout(header_layout)
        
        # --- MAIN 3-COLUMN LAYOUT ---
        content_layout = QHBoxLayout()
        
        # LEFT COLUMN (20%): Map & G-Force
        left_layout = QVBoxLayout()
        
        info_panel = QGroupBox("Información de Vuelta")
        info_l = QVBoxLayout()
        self.lbl_car_id = QLabel("Auto: ---")
        self.lbl_car_id.setStyleSheet("color: #1A1A1A; font-weight: bold;")
        self.lbl_lap = QLabel("Vuelta: -/-")
        self.lbl_lap.setStyleSheet(f"background-color: #E0E0E0; color: {Theme.TEXT_PRIMARY}; padding: 4px; font-weight: bold; border-radius: 4px;")
        self.lbl_time = QLabel("0:00.000")
        self.lbl_time.setFont(QFont(Theme.FONT_MONO, 18, QFont.Weight.Bold))
        self.lbl_time.setStyleSheet(f"color: {Theme.TEXT_PRIMARY};")
        self.lbl_fuel_est = QLabel("Vueltas Restantes: ---")
        self.lbl_fuel_est.setStyleSheet(f"color: {Theme.ACCENT_ORANGE}; font-weight: bold;")
        
        self.fuel_bar = QProgressBar()
        self.fuel_bar.setRange(0, 100)
        self.fuel_bar.setValue(100)
        self.fuel_bar.setTextVisible(True)
        self.fuel_bar.setFormat("Combustible: %v%")
        self.fuel_bar.setStyleSheet(Theme.progress_style(Theme.FUEL_NORMAL))
        
        self.lbl_fuel_usage = QLabel("Consumo/Vuelta: ---")
        self.lbl_fuel_usage.setStyleSheet(f"color: {Theme.ACCENT_RED}; font-weight: bold;")
        
        self.lbl_wot = QLabel("WOT: NO")
        self.lbl_wot.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        
        info_l.addWidget(self.lbl_car_id)
        info_l.addWidget(self.lbl_lap)
        info_l.addWidget(self.lbl_time)
        info_l.addWidget(self.lbl_fuel_est)
        info_l.addWidget(self.fuel_bar)
        info_l.addWidget(self.lbl_fuel_usage)
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
        
        # RIGHT COLUMN (40%): Instrumentación y Alertas
        right_panel = QGroupBox("Instrumentación en Tiempo Real")
        r_layout = QVBoxLayout()
        r_layout.setContentsMargins(10, 20, 10, 10)
        
        # Grid para relojes circulares
        gauges_grid = QGridLayout()
        self.gauge_speed = CircularGaugeWidget("Velocidad", "km/h", 0, 350, Theme.ACCENT_BLUE)
        self.gauge_rpm = CircularGaugeWidget("RPM", "rpm", 0, 10000, Theme.ACCENT_ORANGE)
        self.gauge_boost = CircularGaugeWidget("Turbo/Boost", "bar", 0, 2.0, Theme.ACCENT_RED)
        self.gauge_water_temp = CircularGaugeWidget("Temp. Agua", "°C", 50, 130, Theme.ACCENT_GREEN)
        
        gauges_grid.addWidget(self.gauge_speed, 0, 0)
        gauges_grid.addWidget(self.gauge_rpm, 0, 1)
        gauges_grid.addWidget(self.gauge_boost, 1, 0)
        gauges_grid.addWidget(self.gauge_water_temp, 1, 1)
        r_layout.addLayout(gauges_grid, 3)
        
        # Tyre temps + Pedals layout
        bars_layout = QHBoxLayout()
        bars_layout.setContentsMargins(0, 15, 0, 15)
        
        # Columna izquierda: semicírculos de temp neumáticos FL y RL
        l_tires = QVBoxLayout()
        l_tires.setSpacing(4)
        self.gauge_tl = TyreTempGauge("FL")
        self.gauge_bl = TyreTempGauge("RL")
        l_tires.addWidget(self.gauge_tl)
        l_tires.addWidget(self.gauge_bl)
        bars_layout.addLayout(l_tires)
        
        # Columna central: pedales
        pedals_grid = QGridLayout()
        self.bar_thr = self.create_custom_bar("#00ff7f")
        self.bar_brk = self.create_custom_bar("#ff003c")
        
        self.lbl_thr_txt = QLabel("Acelerador\n0%")
        self.lbl_thr_txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_thr_txt.setStyleSheet(f"color: {Theme.ACCENT_GREEN}; font-weight: bold;")
        
        self.lbl_brk_txt = QLabel("Freno\n0%")
        self.lbl_brk_txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_brk_txt.setStyleSheet(f"color: {Theme.ACCENT_RED}; font-weight: bold;")
        
        pedals_grid.addWidget(self.lbl_thr_txt, 0, 0)
        pedals_grid.addWidget(self.bar_thr, 1, 0, alignment=Qt.AlignmentFlag.AlignHCenter)
        pedals_grid.addWidget(self.lbl_brk_txt, 0, 1)
        pedals_grid.addWidget(self.bar_brk, 1, 1, alignment=Qt.AlignmentFlag.AlignHCenter)
        bars_layout.addLayout(pedals_grid)
        
        # Columna derecha: semicírculos de temp neumáticos FR y RR
        r_tires = QVBoxLayout()
        r_tires.setSpacing(4)
        self.gauge_tr = TyreTempGauge("FR")
        self.gauge_br = TyreTempGauge("RR")
        self.lbl_gear = QLabel("Marcha: N")
        self.lbl_gear.setFont(QFont(Theme.FONT_MONO, 24, QFont.Weight.Bold))
        r_tires.addWidget(self.gauge_tr)
        r_tires.addWidget(self.gauge_br)
        bars_layout.addLayout(r_tires)
        
        r_layout.addLayout(bars_layout, 1)
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
        bar.setFixedSize(30, 180)
        bar.setTextVisible(False)
        bar.setStyleSheet(f"""
            QProgressBar {{ border: 1px solid {Theme.BORDER}; border-radius: 4px; background-color: #E0E0E0; }}
            QProgressBar::chunk {{ background-color: {color}; border-radius: 3px; }}
        """)
        return bar

    def toggle_recording(self):
        if self.client.recording:
            self.client.stop_recording()
            self.btn_record.setText("⏺ Iniciar Grabación")
            self.btn_record.setStyleSheet(Theme.btn_style('#004400', '#FFFFFF', border_color='#003300', hover_bg='#005500'))
            self.lbl_rec_status.setText("Grabación detenida")
            self.lbl_rec_status.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 14px;")
        else:
            if not self.latest_packet:
                self.lbl_rec_status.setText("Espera a recibir telemetría...")
                return
            
            filename = "telemetry_master.sqlite"
            save_path = os.path.join(os.getcwd(), filename)
            
            car_name = self.car_db.get_car_name(self.latest_packet.car_code)
            
            if self.client.start_recording(save_path, self.latest_packet.car_code, car_name):
                self.btn_record.setText("⏹ Detener Grabación")
                self.btn_record.setStyleSheet(Theme.btn_style('#550000', '#FFFFFF', border_color='#440000', hover_bg='#660000'))
                self.lbl_rec_status.setText(f"Grabando (Master DB)")
                self.lbl_rec_status.setStyleSheet(f"color: {Theme.STATUS_CONNECTED}; font-weight: bold; font-size: 14px;")
            else:
                self.lbl_rec_status.setText("Error al grabar")
                self.lbl_rec_status.setStyleSheet(f"color: {Theme.STATUS_ERROR}; font-weight: bold; font-size: 14px;")

    def toggle_connection(self):
        if self.client.running:
            self.client.stop()
            self.lbl_status.setText("Status: Disconnected")
            self.lbl_status.setStyleSheet(f"color: {Theme.STATUS_ERROR}; font-weight: bold; font-size: 14px;")
            self.btn_connect.setText("Connect Live")
            
            self.btn_record.setEnabled(False)
            self.btn_record.setText("⏺ Iniciar Grabación")
            self.btn_record.setStyleSheet("")
            self.lbl_rec_status.setText("")
        else:

            ip = self.ip_input.text().strip()
            self.client.console_ip = ip if ip else None
            self.client.start()
            if ip:
                self.lbl_status.setText(f"Status: Esperando telemetría de {ip} (Entra a pista)...")
            else:
                self.lbl_status.setText("Status: Buscando consola (Entra a pista)...")
            self.lbl_status.setStyleSheet(f"color: {Theme.STATUS_SEARCHING}; font-weight: bold; font-size: 14px;")
            self.btn_connect.setText("Disconnect")
            self.clear_graphs()

    def open_analysis(self):
        master_db = os.path.join(os.getcwd(), 'telemetry_master.sqlite')
        
        if not os.path.exists(master_db):
            self.lbl_status.setText("Status: No Master DB found")
            return
            
        from ui.widgets.advanced_analysis_dialog import AdvancedAnalysisDialog
        
        try:
            dialog = AdvancedAnalysisDialog(db_path=master_db, session_id=None, parent=self)
            dialog.exec()
        except Exception as e:
            self.lbl_status.setText(f"Status: Error opening analysis ({e})")
            import logging
            logging.error(f"Failed to open analysis: {e}")

    def open_pro_analysis(self):
        db_path = os.path.join(os.getcwd(), 'telemetry_master.sqlite')
        if not os.path.exists(db_path):
            QMessageBox.warning(self, "No Database", "No telemetry database found. Please record a session first.")
            return
            
        # In this prototype, we open the pro workspace with a mock session_id=1
        self.pro_workspace = ProfessionalWorkspace(db_path=db_path, session_id=1, live_mode=False)
        self.pro_workspace.show()

    def clear_graphs(self):
        self.map_widget.clear()
        self.gforce_widget.clear()
        self.graphs_widget.clear()
        
        # Resetear motores al limpiar gráficas (ej. cambio de pista/coche)
        self.math_engine = MathEngine()
        self.lap_manager = LapManager()
        self.alert_engine = AlertEngine()
        self.latest_delta_ms = None

    @pyqtSlot(str)
    def on_connected(self, ip):
        self.lbl_status.setText(f"Status: Connected to {ip}")
        self.lbl_status.setStyleSheet(f"color: {Theme.STATUS_CONNECTED}; font-weight: bold; font-size: 14px;")
        if not self.ip_input.text():
            self.ip_input.setText(ip)
            
    @pyqtSlot()
    def on_disconnected(self):
        self.lbl_status.setText("Status: Connection Lost")
        self.lbl_status.setStyleSheet(f"color: {Theme.STATUS_ERROR}; font-weight: bold; font-size: 14px;")

    @pyqtSlot(str)
    def on_client_error(self, err_msg):
        self.lbl_status.setText(f"Error: {err_msg}")
        self.lbl_status.setStyleSheet(f"color: {Theme.STATUS_ERROR}; font-weight: bold; font-size: 14px;")
            
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
        
        # El ángulo de dirección extraído de packet.wheel_steer_angle está en radianes, y puede ser 0.0 o NaN
        if packet.wheel_steer_angle is not None and not math.isnan(packet.wheel_steer_angle):
            steer_deg = (packet.wheel_steer_angle * 180.0 / math.pi)
        else:
            steer_deg = 0
            
        self.graphs_widget.add_data(packet.speed_kmh, t_perc, b_perc, packet.engine_rpm)
        
        if not self.btn_record.isEnabled():
            self.btn_record.setEnabled(True)
            self.btn_record.setStyleSheet(Theme.btn_style('#004400', '#FFFFFF', border_color='#003300', hover_bg='#005500'))
            
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
        self.lbl_fuel_est.setText(f"Vueltas Restantes: {est_str}")
        
        if metrics.get('is_wot', False):
            self.lbl_wot.setText("WOT: YES")
            self.lbl_wot.setStyleSheet(f"color: #FFFFFF; font-weight: bold; background-color: {Theme.WOT_ACTIVE}; padding: 2px; border-radius: 4px;")
        else:
            self.lbl_wot.setText("WOT: NO")
            self.lbl_wot.setStyleSheet(f"color: {Theme.TEXT_MUTED}; padding: 2px;")
        
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
        
        self.gauge_speed.set_value(packet.speed_kmh)
        
        # Fuel usage per lap logic
        if hasattr(packet, 'lap_count') and packet.lap_count != -1:
            if self.current_lap == -1:
                self.current_lap = packet.lap_count
                if hasattr(packet, 'fuel_level'):
                    self.fuel_at_lap_start = packet.fuel_level
            elif packet.lap_count != self.current_lap:
                if self.fuel_at_lap_start > 0 and hasattr(packet, 'fuel_level'):
                    self.last_fuel_consumed = max(0.0, self.fuel_at_lap_start - packet.fuel_level)
                    self.fuel_at_lap_start = packet.fuel_level
                self.current_lap = packet.lap_count
                self.laps_measured += 1
                
            if self.laps_measured > 0 and hasattr(packet, 'fuel_capacity') and packet.fuel_capacity > 0:
                usage_perc = (self.last_fuel_consumed / packet.fuel_capacity) * 100.0
                self.lbl_fuel_usage.setText(f"Consumo/Vuelta: {usage_perc:.1f}%")
            else:
                self.lbl_fuel_usage.setText("Consumo/Vuelta: Midiendo...")

        # Fuel bar
        if hasattr(packet, 'fuel_capacity') and hasattr(packet, 'fuel_level') and packet.fuel_capacity > 0:
            fuel_perc = (packet.fuel_level / packet.fuel_capacity) * 100.0
            self.fuel_bar.setValue(int(fuel_perc))
            if fuel_perc < 10.0:
                self.fuel_bar.setStyleSheet(Theme.progress_style(Theme.FUEL_CRITICAL, 'white'))
            elif fuel_perc < 30.0:
                self.fuel_bar.setStyleSheet(Theme.progress_style(Theme.FUEL_WARNING, Theme.TEXT_PRIMARY))
            else:
                self.fuel_bar.setStyleSheet(Theme.progress_style(Theme.FUEL_NORMAL, 'white'))
        
        # Ajuste dinámico de RPM max
        if packet.engine_rpm > self.gauge_rpm.max_val:
            self.gauge_rpm.set_max(packet.engine_rpm + 500)
        self.gauge_rpm.set_value(packet.engine_rpm)
        
        self.gauge_boost.set_value(packet.boost - 1.0) # Convertir de absolutos a relativos (bar aprox)
        
        # Temp. de Agua
        water_t = packet.water_temp if hasattr(packet, 'water_temp') else 0
        self.gauge_water_temp.set_value(water_t)
        
        self.bar_thr.setValue(int(t_perc))
        self.lbl_thr_txt.setText(f"Acelerador\n{int(t_perc)}%")
        self.bar_brk.setValue(int(b_perc))
        self.lbl_brk_txt.setText(f"Freno\n{int(b_perc)}%")
        
        gear = packet.current_gear
        gear_str = str(gear) if 0 < gear < 15 else ("R" if gear == 15 else "N")
        self.lbl_gear.setText(f"Marcha: {gear_str}")
        
        self.gauge_tl.set_temp(packet.tyre_temp[0])
        self.gauge_tr.set_temp(packet.tyre_temp[1])
        self.gauge_bl.set_temp(packet.tyre_temp[2])
        self.gauge_br.set_temp(packet.tyre_temp[3])

    def export_database_action(self):
        """Exporta la base de datos a un archivo .gt7db portátil."""
        master_db = os.path.join(os.getcwd(), 'telemetry_master.sqlite')
        if not os.path.exists(master_db):
            QMessageBox.warning(self, "Sin Datos", "No hay base de datos de telemetría para exportar.")
            return

        dest_path, _ = QFileDialog.getSaveFileName(
            self, "Exportar Base de Datos de Telemetría",
            os.path.expanduser("~/Desktop/telemetry_export.gt7db"),
            "GT7 Telemetry Database (*.gt7db);;Todos los archivos (*)"
        )
        if not dest_path:
            return

        try:
            count = export_database(master_db, dest_path)
            QMessageBox.information(
                self, "Exportación Exitosa",
                f"Se exportaron {count} sesiones correctamente.\n\nArchivo: {dest_path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error de Exportación", f"No se pudo exportar:\n{e}")

    def import_database_action(self):
        """Importa una base de datos desde un archivo .gt7db."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Importar Base de Datos de Telemetría",
            os.path.expanduser("~/Desktop"),
            "GT7 Telemetry Database (*.gt7db *.sqlite);;Todos los archivos (*)"
        )
        if not file_path:
            return

        # Validar el archivo
        is_valid, msg = validate_import_file(file_path)
        if not is_valid:
            QMessageBox.warning(self, "Archivo Inválido", f"El archivo seleccionado no es válido:\n{msg}")
            return

        # Preguntar modo de importación
        reply = QMessageBox.question(
            self, "Modo de Importación",
            f"{msg}\n\n¿Cómo deseas importar?\n\n"
            "• Sí = Fusionar (agregar sesiones nuevas sin borrar las existentes)\n"
            "• No = Reemplazar (sobrescribir toda la base de datos, se hará backup)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
        )

        if reply == QMessageBox.StandardButton.Cancel:
            return

        master_db = os.path.join(os.getcwd(), 'telemetry_master.sqlite')

        try:
            if reply == QMessageBox.StandardButton.Yes:
                sessions, rows = import_database_merge(file_path, master_db)
                QMessageBox.information(
                    self, "Fusión Exitosa",
                    f"Se importaron {sessions} sesiones nuevas ({rows:,} puntos de telemetría)."
                )
            else:
                sessions, rows = import_database_replace(file_path, master_db)
                QMessageBox.information(
                    self, "Reemplazo Exitoso",
                    f"Base de datos reemplazada. Contiene {sessions} sesiones ({rows:,} puntos).\n"
                    "Se creó un backup automático de tu BD anterior."
                )
        except Exception as e:
            QMessageBox.critical(self, "Error de Importación", f"No se pudo importar:\n{e}")

    def open_sync_dialog(self):
        """Abre el diálogo de sincronización LAN."""
        master_db = os.path.join(os.getcwd(), 'telemetry_master.sqlite')
        if not os.path.exists(master_db):
            QMessageBox.warning(
                self, "Sin Datos",
                "No hay base de datos de telemetría. Graba al menos una sesión primero."
            )
            return

        from ui.sync_dialog import SyncDialog
        dialog = SyncDialog(db_path=master_db, parent=self)
        dialog.exec()

    def closeEvent(self, event):
        self.client.stop()
        event.accept()
