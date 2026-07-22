import sys
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QProgressBar, QGridLayout, QFrame)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from core.models import GT7TelemetryPacket
from ui.widgets.circular_gauge import CircularGaugeWidget
from ui.widgets.tyre_temp_gauge import TyreTempGauge
from ui.theme import Theme

class LiveTelemetryWidget(QFrame):
    """
    Dashboard de instrumentación en tiempo real idéntico al del panel principal.
    Incluye 4 medidores circulares, semicírculos de neumáticos, pedales e indicador de marcha.
    """
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {Theme.BG_CARD};
                border: 1px solid {Theme.BORDER};
                border-radius: 6px;
            }}
            QLabel {{
                border: none;
                background-color: transparent;
                color: {Theme.TEXT_PRIMARY};
            }}
        """)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # Titulo
        lbl_title = QLabel("Instrumentación en Tiempo Real")
        lbl_title.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {Theme.TEXT_PRIMARY};")
        layout.addWidget(lbl_title, alignment=Qt.AlignmentFlag.AlignLeft)
        
        # 1. GRID 2x2 DE MEDIDORES CIRCULARES
        grid_gauges = QGridLayout()
        grid_gauges.setSpacing(10)
        
        self.gauge_speed = CircularGaugeWidget("Velocidad", "km/h", 0, 350, Theme.ACCENT_BLUE)
        self.gauge_rpm = CircularGaugeWidget("RPM", "rpm", 0, 10000, Theme.ACCENT_ORANGE)
        self.gauge_boost = CircularGaugeWidget("Turbo/Boost", "bar", 0, 2.0, Theme.ACCENT_RED)
        self.gauge_water = CircularGaugeWidget("Temp. Agua", "°C", 50, 130, Theme.ACCENT_GREEN)
        
        grid_gauges.addWidget(self.gauge_speed, 0, 0)
        grid_gauges.addWidget(self.gauge_rpm, 0, 1)
        grid_gauges.addWidget(self.gauge_boost, 1, 0)
        grid_gauges.addWidget(self.gauge_water, 1, 1)
        
        layout.addLayout(grid_gauges, stretch=6)
        
        # 2. NEUMÁTICOS Y PEDALES
        tyre_pedal_layout = QHBoxLayout()
        tyre_pedal_layout.setSpacing(10)
        
        # Izquierda: FL + RL
        col_left_tyres = QVBoxLayout()
        self.tyre_fl = TyreTempGauge("FL")
        self.tyre_rl = TyreTempGauge("RL")
        col_left_tyres.addWidget(self.tyre_fl)
        col_left_tyres.addWidget(self.tyre_rl)
        
        # Centro: Pedales (Acelerador + Freno)
        pedals_layout = QHBoxLayout()
        pedals_layout.setSpacing(12)
        
        # Acelerador
        accel_box = QVBoxLayout()
        lbl_accel = QLabel("Acelerador\n0%")
        lbl_accel.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {Theme.ACCENT_GREEN};")
        lbl_accel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_accel_pct = lbl_accel
        
        self.bar_throttle = QProgressBar()
        self.bar_throttle.setOrientation(Qt.Orientation.Vertical)
        self.bar_throttle.setRange(0, 100)
        self.bar_throttle.setValue(0)
        self.bar_throttle.setTextVisible(False)
        self.bar_throttle.setStyleSheet("""
            QProgressBar {
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                background-color: #E0E0E0;
                width: 26px;
            }
            QProgressBar::chunk {
                background: #27AE60;
                border-radius: 3px;
            }
        """)
        accel_box.addWidget(self.lbl_accel_pct)
        accel_box.addWidget(self.bar_throttle, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Freno
        brake_box = QVBoxLayout()
        lbl_brake = QLabel("Freno\n0%")
        lbl_brake.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {Theme.ACCENT_RED};")
        lbl_brake.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_brake_pct = lbl_brake
        
        self.bar_brake = QProgressBar()
        self.bar_brake.setOrientation(Qt.Orientation.Vertical)
        self.bar_brake.setRange(0, 100)
        self.bar_brake.setValue(0)
        self.bar_brake.setTextVisible(False)
        self.bar_brake.setStyleSheet("""
            QProgressBar {
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                background-color: #E0E0E0;
                width: 26px;
            }
            QProgressBar::chunk {
                background: #E74C3C;
                border-radius: 3px;
            }
        """)
        brake_box.addWidget(self.lbl_brake_pct)
        brake_box.addWidget(self.bar_brake, alignment=Qt.AlignmentFlag.AlignCenter)
        
        pedals_layout.addLayout(accel_box)
        pedals_layout.addLayout(brake_box)
        
        # Derecha: FR + RR
        col_right_tyres = QVBoxLayout()
        self.tyre_fr = TyreTempGauge("FR")
        self.tyre_rr = TyreTempGauge("RR")
        col_right_tyres.addWidget(self.tyre_fr)
        col_right_tyres.addWidget(self.tyre_rr)
        
        tyre_pedal_layout.addLayout(col_left_tyres, stretch=3)
        tyre_pedal_layout.addLayout(pedals_layout, stretch=4)
        tyre_pedal_layout.addLayout(col_right_tyres, stretch=3)
        
        layout.addLayout(tyre_pedal_layout, stretch=4)
        
        # 3. INDICADOR DE MARCHA
        self.lbl_gear = QLabel("Marcha: N")
        self.lbl_gear.setStyleSheet(f"font-size: 22px; font-weight: bold; font-family: {Theme.FONT_MONO}; color: {Theme.TEXT_PRIMARY};")
        self.lbl_gear.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_gear)

    def update_data(self, packet: GT7TelemetryPacket):
        if not packet:
            return
            
        # Medidores circulares
        self.gauge_speed.set_value(packet.speed_kmh)
        self.gauge_rpm.set_value(packet.engine_rpm)
        self.gauge_boost.set_value(packet.boost)
        self.gauge_water.set_value(packet.water_temp)
        
        # Neumáticos
        if hasattr(packet, 'tyre_temp') and len(packet.tyre_temp) >= 4:
            self.tyre_fl.set_temp(packet.tyre_temp[0])
            self.tyre_fr.set_temp(packet.tyre_temp[1])
            self.tyre_rl.set_temp(packet.tyre_temp[2])
            self.tyre_rr.set_temp(packet.tyre_temp[3])
            
        # Pedales
        thr_pct = int(packet.throttle / 255.0 * 100.0) if packet.throttle is not None else 0
        brk_pct = int(packet.brake / 255.0 * 100.0) if packet.brake is not None else 0
        self.bar_throttle.setValue(thr_pct)
        self.bar_brake.setValue(brk_pct)
        self.lbl_accel_pct.setText(f"Acelerador\n{thr_pct}%")
        self.lbl_brake_pct.setText(f"Freno\n{brk_pct}%")
        
        # Marcha
        gear_val = packet.current_gear
        if gear_val == 0:
            gear_str = "R" if packet.speed_kmh < -1 else "N"
        elif gear_val == 15:
            gear_str = "N"
        else:
            gear_str = str(gear_val)
        self.lbl_gear.setText(f"Marcha: {gear_str}")
