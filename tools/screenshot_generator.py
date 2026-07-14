#!/usr/bin/env python3
"""
Screenshot Generator for GT7 Telemetry Pro
==========================================
Genera capturas de pantalla de la aplicación para el README.

Captura 1 — Vista principal con datos sintéticos (simula PS4 conectada)
Captura 2 — Análisis Avanzado con datos reales del DB
Captura 3 — Pro Analysis Workspace con datos reales del DB
"""

import sys
import os
import time
import math

# Resolver directorio de la app antes de importar
app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, app_dir)

# Cambiar al directorio de datos de la app (donde vive la DB)
data_dir = os.path.expanduser("~/Library/Application Support/GT7TelemetryPro")
if os.path.exists(data_dir):
    os.chdir(data_dir)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import QTimer

from core.models import GT7TelemetryPacket


def create_synthetic_packet(t: float) -> GT7TelemetryPacket:
    """Genera un paquete de telemetría sintético basado en el tiempo t (segundos)."""
    speed_ms = 30 + 15 * math.sin(t * 0.3)  # Oscila entre 15 y 45 m/s
    speed_kmh = speed_ms * 3.6

    return GT7TelemetryPacket(
        magic=0x47375330,
        position=(100 * math.cos(t * 0.1), 0.0, 100 * math.sin(t * 0.1)),
        world_velocity=(speed_ms * math.cos(t * 0.1), 0.0, speed_ms * math.sin(t * 0.1)),
        rotation=(0.0, t * 0.1, 0.0),
        orientation_north=t * 0.1,
        angular_velocity=(0.3 * math.sin(t * 0.5), 0.5 * math.cos(t * 0.7), 0.0),
        body_height=0.15,
        engine_rpm=3000 + 4000 * abs(math.sin(t * 0.4)),
        iv_seed=0,
        fuel_level=80.0 - t * 0.1,
        fuel_capacity=100.0,
        speed=speed_ms,
        boost=1.0 + 0.5 * max(0, math.sin(t * 0.3)),
        oil_pressure=4.5,
        water_temp=75 + 10 * math.sin(t * 0.05),
        oil_temp=90 + 5 * math.sin(t * 0.05),
        tyre_temp=(72 + 3 * math.sin(t), 73 + 2 * math.sin(t + 1),
                   68 + 4 * math.sin(t + 2), 69 + 3 * math.sin(t + 3)),
        packet_id=int(t * 60),
        lap_count=3,
        total_laps=5,
        best_laptime=128431,
        last_laptime=131567,
        day_progression=50000,
        start_position=5,
        pre_race_num_cars=16,
        min_alert_rpm=6500,
        max_alert_rpm=7500,
        calc_max_speed=280,
        flags=0x02,  # In-race flag
        gears=0x34,
        throttle=int(200 * max(0, math.sin(t * 0.5))),
        brake=int(150 * max(0, -math.sin(t * 0.5))),
        road_plane=(0.0, 1.0, 0.0),
        road_distance=0.3,
        wheel_rps=(speed_ms / 0.33, speed_ms / 0.33, speed_ms / 0.33, speed_ms / 0.33),
        tyre_radius=(0.33, 0.33, 0.33, 0.33),
        susp_height=(0.12, 0.12, 0.13, 0.13),
        clutch=1.0,
        clutch_engagement=1.0,
        clutch_rpm=3000 + 4000 * abs(math.sin(t * 0.4)),
        top_gear_ratio=0.85,
        gear_ratios=(3.5, 2.1, 1.5, 1.1, 0.9, 0.78, 0.68, 0.0),
        car_code=3416,
    )


def setup_app():
    """Configura QApplication con el mismo tema que main.py."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(245, 245, 245))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(26, 26, 26))
    palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(240, 240, 240))
    palette.setColor(QPalette.ColorRole.Text, QColor(26, 26, 26))
    palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(26, 26, 26))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)

    return app


def capture_main_window(app):
    """Captura 1: Vista principal simulando conexión en vivo con PS4."""
    from ui.main_window import TelemetryMainWindow

    window = TelemetryMainWindow()
    window.setGeometry(50, 50, 1600, 900)
    window.show()

    # Simular estado de conexión
    window.lbl_status.setText("Status: Connected to 192.168.1.68")
    from ui.theme import Theme
    window.lbl_status.setStyleSheet(f"color: {Theme.STATUS_CONNECTED}; font-weight: bold; font-size: 14px;")
    window.btn_connect.setText("Disconnect")
    window.ip_input.setText("192.168.1.68")
    window.btn_record.setEnabled(True)
    window.btn_record.setStyleSheet(Theme.btn_style('#004400', '#FFFFFF', border_color='#003300', hover_bg='#005500'))

    # Inyectar 300 paquetes sintéticos (~5s de datos)
    for i in range(300):
        t = i / 60.0
        packet = create_synthetic_packet(t)
        window._cache_packet(packet)

    # Actualizar UI
    window.update_dashboard_ui()
    app.processEvents()

    # Esperar un frame y capturar
    QTimer.singleShot(500, lambda: None)
    app.processEvents()
    time.sleep(0.5)
    app.processEvents()

    docs_dir = os.path.join(app_dir, "docs")
    os.makedirs(docs_dir, exist_ok=True)
    pixmap = window.grab()
    path = os.path.join(docs_dir, "main_window.png")
    pixmap.save(path)
    print(f"✅ Captured: {path}")

    window.close()
    return True


def capture_analysis(app):
    """Captura 2: Herramienta de Análisis Avanzado con datos reales."""
    master_db = os.path.join(os.getcwd(), 'telemetry_master.sqlite')
    if not os.path.exists(master_db):
        print(f"⚠️  No DB found at {master_db}, skipping analysis capture")
        return False

    from ui.widgets.advanced_analysis_dialog import AdvancedAnalysisDialog
    from PyQt6.QtWidgets import QMainWindow

    parent = QMainWindow()
    dialog = AdvancedAnalysisDialog(db_path=master_db, session_id=None, parent=parent)
    dialog.setGeometry(50, 50, 1400, 800)
    dialog.show()
    app.processEvents()
    time.sleep(1)
    app.processEvents()

    docs_dir = os.path.join(app_dir, "docs")
    pixmap = dialog.grab()
    path = os.path.join(docs_dir, "analysis_mode.png")
    pixmap.save(path)
    print(f"✅ Captured: {path}")

    dialog.close()
    return True


def capture_pro_analysis(app):
    """Captura 3: Workspace Pro con datos reales."""
    master_db = os.path.join(os.getcwd(), 'telemetry_master.sqlite')
    if not os.path.exists(master_db):
        print(f"⚠️  No DB found at {master_db}, skipping pro analysis capture")
        return False

    from ui.workspace import ProfessionalWorkspace

    workspace = ProfessionalWorkspace(db_path=master_db, session_id=24, live_mode=False)
    workspace.setGeometry(50, 50, 1600, 900)
    workspace.show()
    app.processEvents()
    time.sleep(1)
    app.processEvents()

    docs_dir = os.path.join(app_dir, "docs")
    pixmap = workspace.grab()
    path = os.path.join(docs_dir, "pro_analysis.png")
    pixmap.save(path)
    print(f"✅ Captured: {path}")

    workspace.close()
    return True


if __name__ == "__main__":
    app = setup_app()

    print("🏁 GT7 Telemetry Pro — Screenshot Generator")
    print("=" * 50)

    capture_main_window(app)
    capture_analysis(app)
    capture_pro_analysis(app)

    print("=" * 50)
    print("🏁 Done! Screenshots saved to docs/")
