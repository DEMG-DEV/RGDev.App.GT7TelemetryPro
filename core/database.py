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
                    best_laptime INTEGER
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
        end_time = datetime.datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE sessions SET end_time = ?, total_laps = ?, best_laptime = ? WHERE id = ?",
                (end_time, self.total_laps, self.best_laptime, self.session_id)
            )
            conn.commit()
        logging.info(f"Closed Master DB Session #{self.session_id}")

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
