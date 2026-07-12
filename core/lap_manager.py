from typing import List, Dict, Optional, Tuple
from core.models import GT7TelemetryPacket

class LapData:
    def __init__(self, lap_number: int):
        self.lap_number = lap_number
        self.lap_time_ms = 0
        # distance -> time_ms map for delta interpolation
        self.distance_to_time: List[Tuple[float, int]] = []

class LapManager:
    """
    Gestor de Vueltas. Segmenta la telemetría continua en bloques por vuelta.
    Permite comparar la vuelta actual con la mejor vuelta (Delta-T).
    """
    def __init__(self):
        self.current_lap_num = -1
        self.best_laptime_ms = -1
        
        self.current_lap_data: Optional[LapData] = None
        self.best_lap_data: Optional[LapData] = None
        
        self.current_lap_time_ms = 0
        
    def process_packet(self, packet: GT7TelemetryPacket) -> Optional[float]:
        """
        Ingiere un paquete y devuelve el Delta en milisegundos contra la mejor vuelta.
        Positivo = Más lento, Negativo = Más rápido.
        """
        # Ignorar si estamos pausados o no estamos en carrera/pista válida
        if packet.is_paused or packet.lap_count <= 0:
            return None
            
        # Detectar cambio de vuelta
        if packet.lap_count != self.current_lap_num:
            # Finalizar vuelta actual
            if self.current_lap_data is not None:
                self.current_lap_data.lap_time_ms = packet.last_laptime
                
                # Chequear si es la mejor vuelta (o si es la primera vuelta completa)
                if self.best_lap_data is None or (packet.last_laptime > 0 and packet.last_laptime < self.best_laptime_ms):
                    self.best_lap_data = self.current_lap_data
                    self.best_laptime_ms = packet.last_laptime
                    
            # Iniciar nueva vuelta
            self.current_lap_num = packet.lap_count
            self.current_lap_data = LapData(self.current_lap_num)
            
        # Actualizar tiempo actual (usamos current_lap_time si viene en C, si no, lo emulamos,
        # pero para el delta dependemos de packet.day_progression o calculamos el timer del sistema)
        # GT7 Telemetry envia current_lap_time en milisegundos solo en el paquete extendido (C).
        # Si no lo tenemos, no podemos hacer un delta exacto sin medir tiempo real.
        time_elapsed = packet.current_lap_time if packet.current_lap_time is not None else 0
        
        # Guardar en matriz de la vuelta actual (distancia -> tiempo)
        if self.current_lap_data is not None and time_elapsed > 0:
            # Solo añadir si la distancia avanzó (evitar parados en boxes o trompos reversos)
            if not self.current_lap_data.distance_to_time or packet.road_distance > self.current_lap_data.distance_to_time[-1][0]:
                self.current_lap_data.distance_to_time.append((packet.road_distance, time_elapsed))
            
        # Calcular Delta si tenemos una mejor vuelta
        if self.best_lap_data and self.best_lap_data.distance_to_time and time_elapsed > 0:
            return self._compute_delta(packet.road_distance, time_elapsed)
            
        return None

    def _compute_delta(self, current_distance: float, current_time: int) -> Optional[float]:
        # Encontrar el tiempo en la mejor vuelta a esta distancia (interpolación simple o vecina más cercana)
        best_lap_array = self.best_lap_data.distance_to_time
        
        # Búsqueda binaria aproximada o lineal rápida (optimizada al asumir que la distancia siempre crece)
        # Para evitar bloquear, usamos búsqueda binaria
        import bisect
        # Extraer solo distancias
        distances = [x[0] for x in best_lap_array]
        idx = bisect.bisect_left(distances, current_distance)
        
        if idx == 0:
            best_time = best_lap_array[0][1]
        elif idx == len(distances):
            best_time = best_lap_array[-1][1]
        else:
            # Interpolación lineal entre idx-1 e idx
            d1, t1 = best_lap_array[idx-1]
            d2, t2 = best_lap_array[idx]
            
            if d2 == d1:
                best_time = t1
            else:
                ratio = (current_distance - d1) / (d2 - d1)
                best_time = t1 + (t2 - t1) * ratio
                
        # Delta = Tiempo actual - Tiempo mejor vuelta en misma distancia
        return current_time - best_time
