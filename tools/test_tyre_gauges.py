"""
Test visual de los semicírculos de temperatura de neumáticos.
Simula temperaturas oscilantes para verificar el widget en acción.
"""
import sys
import math
import random
sys.path.insert(0, '.')

from PyQt6.QtWidgets import QApplication, QWidget, QGridLayout, QLabel, QVBoxLayout
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont
from ui.widgets.tyre_temp_gauge import TyreTempGauge
from ui.theme import Theme


class TyreTempTestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Test — Semicírculos de Temperatura de Neumáticos")
        self.setFixedSize(500, 400)
        self.setStyleSheet(f"background-color: {Theme.BG_PANEL};")

        layout = QVBoxLayout(self)

        title = QLabel("Simulación de Temperaturas de Neumáticos")
        title.setFont(QFont(Theme.FONT_SANS, 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"color: {Theme.TEXT_PRIMARY}; margin-bottom: 10px;")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(10)

        self.gauge_fl = TyreTempGauge("FL")
        self.gauge_fr = TyreTempGauge("FR")
        self.gauge_rl = TyreTempGauge("RL")
        self.gauge_rr = TyreTempGauge("RR")

        # Etiquetas de posición
        lbl_front = QLabel("— Frente —")
        lbl_front.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_front.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 10px;")

        lbl_rear = QLabel("— Trasera —")
        lbl_rear.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_rear.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 10px;")

        grid.addWidget(lbl_front, 0, 0, 1, 2)
        grid.addWidget(self.gauge_fl, 1, 0)
        grid.addWidget(self.gauge_fr, 1, 1)
        grid.addWidget(lbl_rear, 2, 0, 1, 2)
        grid.addWidget(self.gauge_rl, 3, 0)
        grid.addWidget(self.gauge_rr, 3, 1)

        layout.addLayout(grid)

        # Timer de simulación a 30 FPS
        self.tick = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.simulate)
        self.timer.start(33)  # ~30 FPS

    def simulate(self):
        self.tick += 1
        t = self.tick * 0.05  # tiempo en "segundos" simulados

        # Simular calentamiento progresivo con oscilaciones
        base = min(95, 30 + t * 2)  # sube de 30 a 95°C progresivamente
        
        # Cada rueda tiene diferente offset y oscilación
        fl = base + 5 * math.sin(t * 0.7) + random.uniform(-0.5, 0.5)
        fr = base + 8 * math.sin(t * 0.9 + 1.0) + random.uniform(-0.5, 0.5) + 5
        rl = base + 4 * math.sin(t * 0.5 + 0.5) + random.uniform(-0.5, 0.5) - 3
        rr = base + 7 * math.sin(t * 0.8 + 2.0) + random.uniform(-0.5, 0.5) + 8

        self.gauge_fl.set_temp(fl)
        self.gauge_fr.set_temp(fr)
        self.gauge_rl.set_temp(rl)
        self.gauge_rr.set_temp(rr)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = TyreTempTestWindow()
    win.show()
    sys.exit(app.exec())
