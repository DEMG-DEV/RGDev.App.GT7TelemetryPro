"""
Lanza la UI completa de GT7 Telemetry Pro con telemetría simulada
inyectada directamente, como si viniera de un PS4 real.
"""
import sys
import math
import random
sys.path.insert(0, '.')

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from core.models import GT7TelemetryPacket
from ui.main_window import TelemetryMainWindow


def make_fake_packet(tick: int) -> GT7TelemetryPacket:
    """Genera un paquete de telemetría simulado que varía con el tiempo."""
    t = tick * 0.016  # simular 60Hz

    # Velocidad: sube y baja simulando aceleración/frenado
    speed_cycle = math.sin(t * 0.3) * 0.5 + 0.5  # 0..1
    speed_ms = 20 + speed_cycle * 60  # 72-288 km/h

    rpm = 2000 + speed_cycle * 6500
    accel_phase = math.sin(t * 0.3)
    throttle = max(0, int(accel_phase * 255))
    brake = max(0, int(-accel_phase * 200))
    gear = min(6, max(1, int(speed_cycle * 6) + 1))

    # Temperaturas de neumáticos con calentamiento progresivo
    base_temp = min(95, 40 + t * 0.8)
    tyre_fl = base_temp + 5 * math.sin(t * 0.7) + random.uniform(-0.3, 0.3)
    tyre_fr = base_temp + 8 * math.sin(t * 0.9 + 1.0) + random.uniform(-0.3, 0.3) + 6
    tyre_rl = base_temp + 4 * math.sin(t * 0.5 + 0.5) + random.uniform(-0.3, 0.3) - 2
    tyre_rr = base_temp + 7 * math.sin(t * 0.8 + 2.0) + random.uniform(-0.3, 0.3) + 9

    # Posición circular
    radius = 200
    px = radius * math.cos(t * 0.2)
    pz = radius * math.sin(t * 0.2)

    boost = 1.0 + max(0, speed_cycle * 0.8)
    fuel_cap = 100.0
    fuel_level = max(5.0, fuel_cap - t * 0.3)
    lap_time_ms = int((t % 90) * 1000)
    lap_count = int(t / 90) + 1

    susp_base = 0.1
    susp = (
        susp_base + 0.02 * math.sin(t * 5),
        susp_base + 0.02 * math.sin(t * 5 + 0.5),
        susp_base + 0.015 * math.sin(t * 4),
        susp_base + 0.015 * math.sin(t * 4 + 0.5),
    )

    return GT7TelemetryPacket(
        magic=0x47375330,
        position=(px, 0.0, pz),
        world_velocity=(speed_ms * math.cos(t * 0.2), 0, speed_ms * math.sin(t * 0.2)),
        rotation=(0.0, t * 0.2, 0.0),
        orientation_north=t * 0.2,
        angular_velocity=(0.3 * math.sin(t * 2), 0.5 * math.sin(t * 1.5), 0.0),
        body_height=0.15,
        engine_rpm=rpm,
        iv_seed=0,
        fuel_level=fuel_level,
        fuel_capacity=fuel_cap,
        speed=speed_ms,
        boost=boost,
        oil_pressure=4.5,
        water_temp=85 + 10 * math.sin(t * 0.1),
        oil_temp=90 + 8 * math.sin(t * 0.08),
        tyre_temp=(tyre_fl, tyre_fr, tyre_rl, tyre_rr),
        packet_id=tick,
        lap_count=lap_count,
        total_laps=10,
        best_laptime=89500,
        last_laptime=lap_time_ms if lap_count > 1 else 0,
        day_progression=0,
        start_position=1,
        pre_race_num_cars=16,
        min_alert_rpm=6500,
        max_alert_rpm=8500,
        calc_max_speed=320,
        flags=0x02,
        gears=gear | (min(gear + 1, 6) << 4),
        throttle=throttle,
        brake=brake,
        road_plane=(0.0, 1.0, 0.0),
        road_distance=0.0,
        wheel_rps=(speed_ms / 0.33,) * 4,
        tyre_radius=(0.33, 0.33, 0.33, 0.33),
        susp_height=susp,
        clutch=1.0,
        clutch_engagement=1.0,
        clutch_rpm=rpm * 0.95,
        top_gear_ratio=0.85,
        gear_ratios=(3.5, 2.3, 1.7, 1.3, 1.0, 0.85, 0.0, 0.0),
        car_code=847,
        wheel_steer_angle=0.3 * math.sin(t * 0.5),
    )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = TelemetryMainWindow()
    win.show()

    # Simular estado "conectado"
    win.ip_input.setText("192.168.1.100")
    win.lbl_status.setText("🟢 SIMULACIÓN ACTIVA — Telemetría sintética a 60 FPS")
    win.lbl_status.setStyleSheet("color: #27AE60; font-weight: bold;")

    tick = [0]

    def inject_packet():
        try:
            tick[0] += 1
            packet = make_fake_packet(tick[0])
            # Inyectar directamente al cache y a los sub-widgets
            win.latest_packet = packet

            # Alimentar los widgets que necesitan datos frame a frame
            if packet.position:
                win.map_widget.add_point(packet.position[0], packet.position[2], packet.throttle, packet.brake)
            
            lat_g = packet.angular_velocity[1] * 2 if packet.angular_velocity else 0
            lon_g = packet.angular_velocity[0] * 2 if packet.angular_velocity else 0
            win.gforce_widget.add_point(lat_g, lon_g)

            t_perc = (packet.throttle / 255.0) * 100.0
            b_perc = (packet.brake / 255.0) * 100.0
            win.graphs_widget.add_data(packet.speed_kmh, t_perc, b_perc, packet.engine_rpm)
        except Exception as e:
            print(f"Error en inject_packet: {e}")

    # Inyectar datos a 60fps, el ui_timer del main_window ya actualiza la UI a 30fps
    timer = QTimer()
    timer.timeout.connect(inject_packet)
    timer.start(16)  # 60 FPS

    sys.exit(app.exec())
