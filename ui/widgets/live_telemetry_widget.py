import sys
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QProgressBar, QGridLayout, QFrame)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from core.models import GT7TelemetryPacket

class LiveTelemetryWidget(QFrame):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("""
            QFrame {
                background-color: #121820;
                border: 1px solid #45a29e;
                border-radius: 10px;
            }
            QLabel {
                border: none;
                background-color: transparent;
                color: #c5c6c7;
            }
        """)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Titulo
        lbl_title = QLabel("Telemetry Dashboard")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #66fcf1;")
        layout.addWidget(lbl_title, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Grid Principal
        grid = QGridLayout()
        grid.setSpacing(15)
        
        # VELOCIDAD Y MARCHA
        self.lbl_speed = QLabel("0")
        self.lbl_speed.setStyleSheet("font-size: 36px; font-weight: bold; color: white;")
        self.lbl_speed.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_speed_title = QLabel("km/h")
        lbl_speed_title.setStyleSheet("font-size: 14px; color: #888;")
        lbl_speed_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        speed_layout = QVBoxLayout()
        speed_layout.addWidget(self.lbl_speed)
        speed_layout.addWidget(lbl_speed_title)
        
        self.lbl_gear = QLabel("-")
        self.lbl_gear.setStyleSheet("font-size: 42px; font-weight: bold; color: #ffeb3b;")
        self.lbl_gear.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_gear_title = QLabel("GEAR")
        lbl_gear_title.setStyleSheet("font-size: 14px; color: #888;")
        lbl_gear_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        gear_layout = QVBoxLayout()
        gear_layout.addWidget(self.lbl_gear)
        gear_layout.addWidget(lbl_gear_title)
        
        grid.addLayout(speed_layout, 0, 0)
        grid.addLayout(gear_layout, 0, 1)
        
        # PEDALES (Acelerador y Freno)
        pedal_layout = QHBoxLayout()
        pedal_layout.setSpacing(20)
        
        # Acelerador
        accel_container = QVBoxLayout()
        self.bar_throttle = QProgressBar()
        self.bar_throttle.setOrientation(Qt.Orientation.Vertical)
        self.bar_throttle.setRange(0, 255)
        self.bar_throttle.setValue(0)
        self.bar_throttle.setTextVisible(False)
        self.bar_throttle.setStyleSheet("""
            QProgressBar {
                border: 2px solid #333;
                border-radius: 5px;
                background-color: #1a1a2e;
                width: 30px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:1, x2:0, y2:0, 
                                            stop:0 #00ff7f, stop:1 #00b359);
                border-radius: 3px;
            }
        """)
        lbl_accel = QLabel("THR")
        lbl_accel.setStyleSheet("font-weight: bold; font-size: 12px;")
        lbl_accel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        accel_container.addWidget(self.bar_throttle, alignment=Qt.AlignmentFlag.AlignCenter)
        accel_container.addWidget(lbl_accel)
        
        # Freno
        brake_container = QVBoxLayout()
        self.bar_brake = QProgressBar()
        self.bar_brake.setOrientation(Qt.Orientation.Vertical)
        self.bar_brake.setRange(0, 255)
        self.bar_brake.setValue(0)
        self.bar_brake.setTextVisible(False)
        self.bar_brake.setStyleSheet("""
            QProgressBar {
                border: 2px solid #333;
                border-radius: 5px;
                background-color: #1a1a2e;
                width: 30px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:1, x2:0, y2:0, 
                                            stop:0 #ff3333, stop:1 #cc0000);
                border-radius: 3px;
            }
        """)
        lbl_brake = QLabel("BRK")
        lbl_brake.setStyleSheet("font-weight: bold; font-size: 12px;")
        lbl_brake.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brake_container.addWidget(self.bar_brake, alignment=Qt.AlignmentFlag.AlignCenter)
        brake_container.addWidget(lbl_brake)
        
        pedal_layout.addLayout(accel_container)
        pedal_layout.addLayout(brake_container)
        
        grid.addLayout(pedal_layout, 0, 2, 2, 1)
        
        # RPM Bar
        self.bar_rpm = QProgressBar()
        self.bar_rpm.setRange(0, 10000)
        self.bar_rpm.setValue(0)
        self.bar_rpm.setTextVisible(False)
        self.bar_rpm.setStyleSheet("""
            QProgressBar {
                border: 2px solid #333;
                border-radius: 8px;
                background-color: #1a1a2e;
                height: 15px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                                            stop:0 #4facfe, stop:0.7 #00f2fe, stop:1 #ff0844);
                border-radius: 6px;
            }
        """)
        
        self.lbl_rpm_text = QLabel("0 RPM")
        self.lbl_rpm_text.setStyleSheet("font-size: 14px; font-weight: bold; color: white;")
        
        rpm_layout = QHBoxLayout()
        rpm_layout.addWidget(self.lbl_rpm_text)
        rpm_layout.addWidget(self.bar_rpm, stretch=1)
        
        grid.addLayout(rpm_layout, 1, 0, 1, 2)
        
        layout.addLayout(grid)
        layout.addStretch()

    def update_data(self, packet: GT7TelemetryPacket):
        if not packet:
            return
            
        # Velocidad y Marcha
        self.lbl_speed.setText(f"{int(packet.speed_kmh)}")
        gear_val = packet.current_gear
        if gear_val == 0:
            gear_str = "R" if packet.speed_kmh < -1 else "N"
        elif gear_val == 15:
            gear_str = "N"
        else:
            gear_str = str(gear_val)
        self.lbl_gear.setText(gear_str)
        
        # Pedales
        self.bar_throttle.setValue(packet.throttle)
        self.bar_brake.setValue(packet.brake)
        
        # RPM
        rpm = int(packet.engine_rpm)
        self.lbl_rpm_text.setText(f"{rpm} RPM")
        
        # Calcular max rpm dinamico para la barra
        max_rpm = max(10000, packet.calc_max_speed if packet.calc_max_speed > 0 else 10000)
        
        # Como calc_max_speed a veces no es RPM sino Top Speed, si vemos RPM > max_rpm, autoajustamos
        if rpm > self.bar_rpm.maximum():
            self.bar_rpm.setMaximum(int(rpm * 1.1))
            
        self.bar_rpm.setValue(rpm)
        
        # Alerta RPM (Shift Light)
        if packet.rev_limit_alert_active:
            self.setStyleSheet(self.styleSheet().replace("border-radius: 10px;", "border-radius: 10px; border: 2px solid #ff0844;"))
        else:
            self.setStyleSheet(self.styleSheet().replace("border: 2px solid #ff0844;", "border: 1px solid #45a29e;"))
