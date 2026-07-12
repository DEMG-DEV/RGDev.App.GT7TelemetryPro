import time
from typing import List, Tuple, Dict, Any
from core.models import GT7TelemetryPacket

class AlertEngine:
    """
    Motor de Alertas (Pit-Wall).
    Evalúa los datos en crudo y métricas matemáticas para disparar advertencias.
    """
    def __init__(self):
        # Cooldowns para no espamear alertas (key -> timestamp)
        self.last_alerts: Dict[str, float] = {}
        
        # Configuraciones de umbrales
        self.TYRE_TEMP_MAX = 105.0 # Grados C
        self.TYRE_TEMP_MIN = 60.0
        
        # En F1/WEC el enfriamiento de agua es vital
        self.WATER_TEMP_MAX = 110.0
        
    def check_alerts(self, packet: GT7TelemetryPacket, metrics: Dict[str, Any]) -> List[Tuple[str, str, str]]:
        """
        Retorna una lista de tuplas (Severidad, Titulo, Mensaje).
        Severidad: "INFO", "WARNING", "CRITICAL"
        """
        alerts = []
        now = time.time()
        
        def _add_alert(alert_id: str, severity: str, title: str, msg: str, cooldown: float = 5.0):
            if now - self.last_alerts.get(alert_id, 0) > cooldown:
                alerts.append((severity, title, msg))
                self.last_alerts[alert_id] = now
                
        # 1. Over-Rev (Revoluciones pasadas de vuelta)
        if packet.min_alert_rpm > 0 and packet.max_alert_rpm > 0:
            if packet.engine_rpm > packet.max_alert_rpm + 500:
                _add_alert('over_rev', 'CRITICAL', 'ENGINE DAMAGE RISK', f'Over-Rev detectado: {int(packet.engine_rpm)} RPM', 10.0)
                
        # 2. Temperatura de Neumáticos
        for i, pos in enumerate(["FL", "FR", "RL", "RR"]):
            temp = packet.tyre_temp[i]
            if temp > self.TYRE_TEMP_MAX:
                _add_alert(f'tyre_hot_{pos}', 'WARNING', 'TYRE OVERHEATING', f'Neumático {pos} a {temp:.1f}°C', 15.0)
            elif temp > 0 and temp < self.TYRE_TEMP_MIN:
                # Solo alertar neumáticos fríos si el coche se está moviendo a más de 50km/h
                if packet.speed_kmh > 50:
                    _add_alert(f'tyre_cold_{pos}', 'INFO', 'COLD TYRES', f'Neumático {pos} a {temp:.1f}°C', 15.0)
                    
        # 3. Nivel de Combustible
        if packet.fuel_capacity > 0:
            fuel_pct = (packet.fuel_level / packet.fuel_capacity) * 100
            if 0 < fuel_pct < 10:
                _add_alert('fuel_low', 'CRITICAL', 'LOW FUEL', f'Queda {fuel_pct:.1f}% de combustible. ¡Box, Box!', 30.0)
                
        # 4. Temperatura de Agua
        if packet.water_temp > self.WATER_TEMP_MAX:
            _add_alert('water_hot', 'CRITICAL', 'WATER TEMP HIGH', f'Temp: {packet.water_temp:.1f}°C', 20.0)

        return alerts
