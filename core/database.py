import sqlite3
import threading
import queue
import time
import datetime
import logging
from typing import Optional, Tuple
from core.models import GT7TelemetryPacket

class SessionDatabaseWriter:
    """
    Escritor de Base de Datos SQLite asíncrono para telemetría.
    Usa transacciones (executemany) para alto rendimiento sin bloquear la red.
    """
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.queue = queue.Queue(maxsize=5000)
        self.running = False
        self.worker_thread = None
        self.session_id = None
        
        # Meta-tracking during session
        self.best_laptime = -1
        self.total_laps = 0
        self.car_id_counts = {}
        
        self._init_db()

    def _init_db(self):
        # Configurar esquema inicial de la base de datos de sesión
        with sqlite3.connect(self.db_path) as conn:
            # Optimizaciones extremas para inserciones masivas en SQLite
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            conn.execute("PRAGMA cache_size = -64000;") # 64MB cache
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_time TEXT,
                    end_time TEXT,
                    car_id INTEGER,
                    car_name TEXT,
                    total_laps INTEGER,
                    best_laptime INTEGER,
                    is_locked INTEGER DEFAULT 0
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS telemetry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    timestamp REAL,
                    lap_count INTEGER,
                    speed_kmh REAL,
                    engine_rpm REAL,
                    throttle INTEGER,
                    brake INTEGER,
                    current_gear INTEGER,
                    raw_packet BLOB,
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                )
            """)
            conn.commit()

    def start(self, car_id: int, car_name: str):
        if self.running:
            return
            
        self.best_laptime = -1
        self.total_laps = 0
        self.car_id_counts = {car_id: 1}
            
        # Crear la nueva sesión
        start_time = datetime.datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO sessions (start_time, car_id, car_name, total_laps, best_laptime) VALUES (?, ?, ?, ?, ?)",
                (start_time, car_id, car_name, 0, -1)
            )
            self.session_id = cursor.lastrowid
            conn.commit()
            
        logging.info(f"Started Master DB Session #{self.session_id} for {car_name}")
            
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

    def stop(self):
        if not self.running:
            return
        self.running = False
        self.queue.put(None) # Señal de parada
        if self.worker_thread:
            self.worker_thread.join(timeout=2.0)
            
        # Cerrar la sesión
        final_car_id = max(self.car_id_counts, key=self.car_id_counts.get) if self.car_id_counts else None
        end_time = datetime.datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            if final_car_id is not None:
                from core.car_database import CarDatabase
                car_db = CarDatabase()
                final_car_name = car_db.get_car_name(final_car_id)
                conn.execute(
                    "UPDATE sessions SET end_time = ?, total_laps = ?, best_laptime = ?, car_id = ?, car_name = ? WHERE id = ?",
                    (end_time, self.total_laps, self.best_laptime, final_car_id, final_car_name, self.session_id)
                )
            else:
                conn.execute(
                    "UPDATE sessions SET end_time = ?, total_laps = ?, best_laptime = ? WHERE id = ?",
                    (end_time, self.total_laps, self.best_laptime, self.session_id)
                )
            conn.commit()
        logging.info(f"Closed Master DB Session #{self.session_id} (Car: {final_car_name if final_car_id else 'Unknown'})")

    def insert_packet(self, timestamp: float, packet: GT7TelemetryPacket, raw_blob: bytes):
        """
        Encola el paquete para ser insertado en la base de datos de manera asíncrona.
        """
        if not self.running or self.session_id is None:
            return
            
        # Track metadata
        if packet.lap_count > self.total_laps:
            self.total_laps = packet.lap_count
        if packet.best_laptime > 0 and (self.best_laptime == -1 or packet.best_laptime < self.best_laptime):
            self.best_laptime = packet.best_laptime
            
        cid = packet.car_code
        self.car_id_counts[cid] = self.car_id_counts.get(cid, 0) + 1
            
        data = (
            self.session_id,
            timestamp,
            packet.lap_count,
            packet.speed_kmh,
            packet.engine_rpm,
            packet.throttle,
            packet.brake,
            packet.current_gear,
            raw_blob
        )
        try:
            self.queue.put_nowait(data)
        except queue.Full:
            logging.warning("Database queue is full! Dropping telemetry frame.")

    def _worker_loop(self):
        """Hilo dedicado a hacer batch inserts en SQLite."""
        batch = []
        batch_size = 60 # 1 segundo de telemetría a 60Hz
        
        # Conexión dedicada para este hilo
        with sqlite3.connect(self.db_path) as conn:
            while self.running or not self.queue.empty():
                try:
                    # Esperar 0.5s max para agrupar paquetes si la cola está semivacía
                    item = self.queue.get(timeout=0.5)
                    if item is None:
                        # Si llega None y running es False, salir
                        if not self.running:
                            break
                        continue
                        
                    batch.append(item)
                    
                except queue.Empty:
                    pass
                    
                # Si llegamos al batch size o la cola está vacía pero tenemos paquetes cacheados, hacemos commit
                if len(batch) >= batch_size or (not self.running and len(batch) > 0):
                    try:
                        conn.executemany("""
                            INSERT INTO telemetry (
                                session_id, timestamp, lap_count, speed_kmh, engine_rpm, throttle, brake, current_gear, raw_packet
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, batch)
                        conn.commit()
                        batch.clear()
                    except Exception as e:
                        logging.error(f"Error inserting into SQLite: {e}")
                        # En caso de error crítico, limpiamos el batch para no atascar
                        batch.clear()

        logging.info("SessionDatabaseWriter worker thread finished cleanly.")

def get_lap_data_vectorized(db_path: str, session_id: int, lap_numbers: list) -> dict:
    """
    Optimized SQLite query for multi-lap processing. Returns a dictionary of numpy arrays
    representing the telemetry channels for the requested laps.
    """
    import numpy as np
    from core.models import parse_telemetry_packet
    
    try:
        with sqlite3.connect(db_path) as conn:
            placeholders = ','.join('?' for _ in lap_numbers)
            query = f"SELECT lap_count, timestamp, raw_packet FROM telemetry WHERE session_id = ? AND lap_count IN ({placeholders}) ORDER BY id"
            cursor = conn.cursor()
            cursor.execute(query, [session_id] + lap_numbers)
            rows = cursor.fetchall()
    except Exception as e:
        import logging
        logging.error(f"Error executing SQLite vectorization query: {e}", exc_info=True)
        raise

    data = {
        'lap_count': [], 'timestamp': [], 'speed': [], 'throttle': [], 'brake': [],
        'engineRPM': [], 'currentGear': [], 'suspHeight_FL': [], 'suspHeight_FR': [],
        'suspHeight_RL': [], 'suspHeight_RR': [], 'wheelRPS_FL': [], 'wheelRPS_FR': [],
        'wheelRPS_RL': [], 'wheelRPS_RR': [], 'tyreRadius_FL': [], 'tyreRadius_FR': [],
        'tyreRadius_RL': [], 'tyreRadius_RR': [], 'sway': [], 'surge': [], 'heave': [],
        'wheel_steer_angle': [], 'position_x': [], 'position_y': [], 'position_z': [],
        'world_vel_x': [], 'world_vel_y': [], 'world_vel_z': []
    }
    
    for row in rows:
        lap = row[0]
        ts = row[1]
        blob = row[2]
        
        packet = parse_telemetry_packet(blob, 'C')
        if not packet:
            continue
            
        data['lap_count'].append(lap)
        data['timestamp'].append(ts)
        data['speed'].append(packet.speed_kmh)
        data['throttle'].append(packet.throttle / 255.0)
        data['brake'].append(packet.brake / 255.0)
        data['engineRPM'].append(packet.engine_rpm)
        data['currentGear'].append(packet.current_gear)
        
        data['suspHeight_FL'].append(packet.susp_height[0])
        data['suspHeight_FR'].append(packet.susp_height[1])
        data['suspHeight_RL'].append(packet.susp_height[2])
        data['suspHeight_RR'].append(packet.susp_height[3])
        
        data['wheelRPS_FL'].append(packet.wheel_rps[0])
        data['wheelRPS_FR'].append(packet.wheel_rps[1])
        data['wheelRPS_RL'].append(packet.wheel_rps[2])
        data['wheelRPS_RR'].append(packet.wheel_rps[3])
        
        data['tyreRadius_FL'].append(packet.tyre_radius[0])
        data['tyreRadius_FR'].append(packet.tyre_radius[1])
        data['tyreRadius_RL'].append(packet.tyre_radius[2])
        data['tyreRadius_RR'].append(packet.tyre_radius[3])
        
        data['sway'].append(packet.sway or 0.0)
        data['surge'].append(packet.surge or 0.0)
        data['heave'].append(packet.heave or 0.0)
        data['wheel_steer_angle'].append(packet.wheel_steer_angle or 0.0)
        
        data['position_x'].append(packet.position[0])
        data['position_y'].append(packet.position[1])
        data['position_z'].append(packet.position[2])
        
        data['world_vel_x'].append(packet.world_velocity[0])
        data['world_vel_y'].append(packet.world_velocity[1])
        data['world_vel_z'].append(packet.world_velocity[2])

    for key in data:
        data[key] = np.array(data[key], dtype=np.float32)
        
    return data
