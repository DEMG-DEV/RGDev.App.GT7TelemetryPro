from typing import Dict, Any, Optional
import math
from core.models import GT7TelemetryPacket

class MathEngine:
    """
    Motor de cálculo de canales virtuales.
    Genera métricas avanzadas a partir de la telemetría en crudo (DAQ).
    """
    def __init__(self):
        self.initial_fuel: Optional[float] = None
        self.lap_fuel_starts: Dict[int, float] = {}
        
    def process_packet(self, packet: GT7TelemetryPacket) -> Dict[str, Any]:
        """
        Toma el paquete crudo y devuelve un diccionario con métricas adicionales.
        """
        metrics = {}
        
        # 1. Delta de Combustible
        if self.initial_fuel is None and packet.fuel_capacity > 0:
            self.initial_fuel = packet.fuel_level
            self.lap_fuel_starts[packet.lap_count] = packet.fuel_level
            
        # Registrar combustible al inicio de cada vuelta nueva
        if packet.lap_count not in self.lap_fuel_starts and packet.fuel_capacity > 0:
            self.lap_fuel_starts[packet.lap_count] = packet.fuel_level
            
        # Calcular consumo de la vuelta anterior (si existe)
        last_lap = packet.lap_count - 1
        if last_lap in self.lap_fuel_starts and packet.lap_count in self.lap_fuel_starts:
            fuel_used_last_lap = self.lap_fuel_starts[last_lap] - self.lap_fuel_starts[packet.lap_count]
            metrics['fuel_used_last_lap'] = max(0.0, fuel_used_last_lap)
            
            # Estimación de vueltas restantes
            if fuel_used_last_lap > 0:
                metrics['estimated_laps_remaining'] = packet.fuel_level / fuel_used_last_lap
            else:
                metrics['estimated_laps_remaining'] = 999.0
        else:
            metrics['fuel_used_last_lap'] = 0.0
            metrics['estimated_laps_remaining'] = 999.0
            
        # 2. Porcentaje de uso de frenos y acelerador (0.0 a 1.0)
        metrics['throttle_pct'] = packet.throttle / 255.0
        metrics['brake_pct'] = packet.brake / 255.0
        
        # 3. Fuerzas G Laterales y Longitudinales (Aproximación por yaw rate y velocidad si no viene directo)
        # GT7 Telemetry no da G-forces directos en la spec principal (paquete A), pero podemos usar rotation o calcular derivadas.
        # Aquí pasaremos los valores brutos a Gs asumiendo que ya calculamos derivadas, o pasaremos placeholders
        
        # Wide Open Throttle (WOT) instantáneo
        metrics['is_wot'] = packet.throttle >= 250
        
        # 4. Aproximación de Deriva (Slip Angle Básico)
        # yaw_rate = angular_velocity Y (vertical)
        yaw_rate = packet.angular_velocity[1]
        
        # Steering angle aproximado (normalizado -1 a 1)
        # GT7 spec no tiene steering exacto en el paquete base, usa rotacion, pero en C si
        steer = packet.wheel_steer_angle if packet.wheel_steer_angle is not None else 0.0
        
        # Simulando slip visual
        metrics['slip_angle_indicator'] = abs(yaw_rate * packet.speed_kmh) # Placeholder visual
        
        return metrics
