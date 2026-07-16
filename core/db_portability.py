# core/db_portability.py
"""
Módulo de portabilidad de la base de datos de telemetría.
Permite exportar, importar, fusionar y sincronizar bases de datos
entre dispositivos de forma segura.
"""

import os
import sqlite3
import shutil
import zlib
import json
import datetime
import logging


def export_database(source_db_path: str, dest_path: str) -> int:
    """
    Exporta la base de datos de telemetría a un archivo .gt7db limpio.
    Usa VACUUM INTO para generar un snapshot atómico sin WAL journal.
    
    Returns:
        Número de sesiones exportadas.
    """
    if not os.path.exists(source_db_path):
        raise FileNotFoundError(f"Base de datos no encontrada: {source_db_path}")
    
    # Eliminar destino si ya existe (VACUUM INTO falla si el archivo existe)
    if os.path.exists(dest_path):
        os.remove(dest_path)
    
    conn = sqlite3.connect(source_db_path)
    try:
        conn.execute("VACUUM INTO ?", (dest_path,))
        
        # Contar sesiones exportadas
        cursor = conn.execute("SELECT COUNT(*) FROM sessions")
        session_count = cursor.fetchone()[0]
    finally:
        conn.close()
    
    logging.info(f"Base de datos exportada a {dest_path} ({session_count} sesiones)")
    return session_count


def validate_import_file(file_path: str) -> tuple:
    """
    Verifica que el archivo sea un SQLite válido con las tablas correctas.
    
    Returns:
        (is_valid: bool, message: str)
    """
    if not os.path.exists(file_path):
        return False, "El archivo no existe."
    
    if os.path.getsize(file_path) < 100:
        return False, "El archivo es demasiado pequeño para ser una base de datos válida."
    
    try:
        conn = sqlite3.connect(file_path)
        cursor = conn.cursor()
        
        # Verificar que existan las tablas requeridas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        
        if 'sessions' not in tables:
            conn.close()
            return False, "La tabla 'sessions' no existe en el archivo."
        
        if 'telemetry' not in tables:
            conn.close()
            return False, "La tabla 'telemetry' no existe en el archivo."
        
        # Verificar columnas mínimas de sessions
        cursor.execute("PRAGMA table_info(sessions)")
        session_cols = {row[1] for row in cursor.fetchall()}
        required_session_cols = {'id', 'start_time', 'car_id', 'car_name'}
        missing = required_session_cols - session_cols
        if missing:
            conn.close()
            return False, f"Columnas faltantes en 'sessions': {missing}"
        
        # Verificar columnas mínimas de telemetry
        cursor.execute("PRAGMA table_info(telemetry)")
        telem_cols = {row[1] for row in cursor.fetchall()}
        required_telem_cols = {'id', 'session_id', 'raw_packet'}
        missing = required_telem_cols - telem_cols
        if missing:
            conn.close()
            return False, f"Columnas faltantes en 'telemetry': {missing}"
        
        # Contar sesiones para info
        cursor.execute("SELECT COUNT(*) FROM sessions")
        count = cursor.fetchone()[0]
        
        conn.close()
        return True, f"Archivo válido. Contiene {count} sesiones."
        
    except sqlite3.DatabaseError as e:
        return False, f"No es un archivo SQLite válido: {e}"


def get_session_fingerprints(db_path: str) -> list:
    """
    Retorna las 'huellas digitales' de todas las sesiones para comparación.
    Usa (start_time, car_id) como clave natural única.
    
    Returns:
        Lista de tuplas: [(start_time, car_id, car_name, total_laps, best_laptime), ...]
    """
    if not os.path.exists(db_path):
        return []
    
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute(
            "SELECT start_time, car_id, car_name, total_laps, best_laptime FROM sessions ORDER BY id"
        )
        fingerprints = cursor.fetchall()
    finally:
        conn.close()
    
    return fingerprints


def import_database_merge(source_path: str, target_db_path: str) -> tuple:
    """
    Fusiona las sesiones del archivo importado a la BD existente.
    Re-mapea los session_id para evitar colisiones.
    Evita duplicados comparando (start_time, car_id).
    
    Returns:
        (sessions_imported: int, telemetry_rows: int)
    """
    # Obtener huellas existentes en el destino
    existing_fingerprints = set()
    if os.path.exists(target_db_path):
        for fp in get_session_fingerprints(target_db_path):
            existing_fingerprints.add((fp[0], fp[1]))  # (start_time, car_id)
    
    source_conn = sqlite3.connect(source_path)
    target_conn = sqlite3.connect(target_db_path)
    
    sessions_imported = 0
    telemetry_rows = 0
    
    try:
        # Asegurar que la BD destino tenga el esquema
        _ensure_schema(target_conn)
        
        # Leer todas las sesiones del origen
        source_sessions = source_conn.execute(
            "SELECT id, start_time, end_time, car_id, car_name, total_laps, best_laptime, is_locked FROM sessions"
        ).fetchall()
        
        for session in source_sessions:
            old_id, start_time, end_time, car_id, car_name, total_laps, best_laptime, is_locked = session
            
            # Verificar si ya existe (duplicado)
            if (start_time, car_id) in existing_fingerprints:
                logging.info(f"Sesión duplicada omitida: {start_time} / car_id={car_id}")
                continue
            
            # Insertar la sesión en el destino con nuevo ID
            cursor = target_conn.execute(
                "INSERT INTO sessions (start_time, end_time, car_id, car_name, total_laps, best_laptime, is_locked) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (start_time, end_time, car_id, car_name, total_laps, best_laptime, is_locked)
            )
            new_id = cursor.lastrowid
            
            # Copiar telemetría con el nuevo session_id
            telem_rows = source_conn.execute(
                "SELECT timestamp, lap_count, speed_kmh, engine_rpm, throttle, brake, current_gear, raw_packet FROM telemetry WHERE session_id = ?",
                (old_id,)
            ).fetchall()
            
            if telem_rows:
                target_conn.executemany(
                    "INSERT INTO telemetry (session_id, timestamp, lap_count, speed_kmh, engine_rpm, throttle, brake, current_gear, raw_packet) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [(new_id,) + row for row in telem_rows]
                )
                telemetry_rows += len(telem_rows)
            
            sessions_imported += 1
            existing_fingerprints.add((start_time, car_id))
        
        target_conn.commit()
        
    finally:
        source_conn.close()
        target_conn.close()
    
    logging.info(f"Importación completada: {sessions_imported} sesiones, {telemetry_rows} filas de telemetría")
    return sessions_imported, telemetry_rows


def import_database_replace(source_path: str, target_db_path: str) -> tuple:
    """
    Reemplaza la BD actual con la importada. Hace backup automático.
    
    Returns:
        (sessions_count: int, telemetry_rows: int)
    """
    # Crear backup de la BD actual
    if os.path.exists(target_db_path):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = target_db_path.replace('.sqlite', f'_backup_{timestamp}.sqlite')
        shutil.copy2(target_db_path, backup_path)
        logging.info(f"Backup creado: {backup_path}")
    
    # Reemplazar
    shutil.copy2(source_path, target_db_path)
    
    # Contar contenido importado
    conn = sqlite3.connect(target_db_path)
    try:
        sessions = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        telemetry = conn.execute("SELECT COUNT(*) FROM telemetry").fetchone()[0]
    finally:
        conn.close()
    
    logging.info(f"BD reemplazada: {sessions} sesiones, {telemetry} filas de telemetría")
    return sessions, telemetry


def export_sessions_to_buffer(db_path: str, session_keys: list) -> bytes:
    """
    Serializa sesiones específicas + su telemetría en un buffer comprimido
    para transferencia por red.
    
    Args:
        db_path: Ruta a la base de datos.
        session_keys: Lista de tuplas (start_time, car_id) a exportar.
    
    Returns:
        Buffer de bytes comprimido con zlib.
    """
    conn = sqlite3.connect(db_path)
    payload = {'sessions': []}
    
    try:
        for start_time, car_id in session_keys:
            # Buscar la sesión
            session = conn.execute(
                "SELECT id, start_time, end_time, car_id, car_name, total_laps, best_laptime, is_locked FROM sessions WHERE start_time = ? AND car_id = ?",
                (start_time, car_id)
            ).fetchone()
            
            if not session:
                continue
            
            session_id = session[0]
            session_data = {
                'start_time': session[1],
                'end_time': session[2],
                'car_id': session[3],
                'car_name': session[4],
                'total_laps': session[5],
                'best_laptime': session[6],
                'is_locked': session[7],
                'telemetry': []
            }
            
            # Leer telemetría
            rows = conn.execute(
                "SELECT timestamp, lap_count, speed_kmh, engine_rpm, throttle, brake, current_gear, raw_packet FROM telemetry WHERE session_id = ? ORDER BY id",
                (session_id,)
            ).fetchall()
            
            for row in rows:
                session_data['telemetry'].append({
                    'timestamp': row[0],
                    'lap_count': row[1],
                    'speed_kmh': row[2],
                    'engine_rpm': row[3],
                    'throttle': row[4],
                    'brake': row[5],
                    'current_gear': row[6],
                    'raw_packet': row[7].hex() if row[7] else None
                })
            
            payload['sessions'].append(session_data)
    finally:
        conn.close()
    
    # Serializar y comprimir
    json_bytes = json.dumps(payload).encode('utf-8')
    compressed = zlib.compress(json_bytes, level=6)
    
    logging.info(f"Buffer exportado: {len(payload['sessions'])} sesiones, {len(json_bytes)} bytes -> {len(compressed)} bytes comprimidos")
    return compressed


def import_sessions_from_buffer(buffer: bytes, target_db_path: str) -> tuple:
    """
    Deserializa y fusiona sesiones recibidas por red.
    
    Returns:
        (sessions_imported: int, telemetry_rows: int)
    """
    # Descomprimir y deserializar
    json_bytes = zlib.decompress(buffer)
    payload = json.loads(json_bytes.decode('utf-8'))
    
    # Obtener huellas existentes
    existing_fingerprints = set()
    if os.path.exists(target_db_path):
        for fp in get_session_fingerprints(target_db_path):
            existing_fingerprints.add((fp[0], fp[1]))
    
    conn = sqlite3.connect(target_db_path)
    _ensure_schema(conn)
    
    sessions_imported = 0
    telemetry_rows = 0
    
    try:
        for session_data in payload.get('sessions', []):
            start_time = session_data['start_time']
            car_id = session_data['car_id']
            
            # Evitar duplicados
            if (start_time, car_id) in existing_fingerprints:
                continue
            
            # Insertar sesión
            cursor = conn.execute(
                "INSERT INTO sessions (start_time, end_time, car_id, car_name, total_laps, best_laptime, is_locked) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (start_time, session_data.get('end_time'), car_id,
                 session_data.get('car_name'), session_data.get('total_laps', 0),
                 session_data.get('best_laptime', -1), session_data.get('is_locked', 0))
            )
            new_id = cursor.lastrowid
            
            # Insertar telemetría
            telem_data = session_data.get('telemetry', [])
            if telem_data:
                rows = []
                for t in telem_data:
                    raw = bytes.fromhex(t['raw_packet']) if t.get('raw_packet') else None
                    rows.append((
                        new_id, t['timestamp'], t['lap_count'],
                        t['speed_kmh'], t['engine_rpm'], t['throttle'],
                        t['brake'], t['current_gear'], raw
                    ))
                conn.executemany(
                    "INSERT INTO telemetry (session_id, timestamp, lap_count, speed_kmh, engine_rpm, throttle, brake, current_gear, raw_packet) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    rows
                )
                telemetry_rows += len(rows)
            
            sessions_imported += 1
            existing_fingerprints.add((start_time, car_id))
        
        conn.commit()
    finally:
        conn.close()
    
    logging.info(f"Buffer importado: {sessions_imported} sesiones, {telemetry_rows} filas de telemetría")
    return sessions_imported, telemetry_rows


def _ensure_schema(conn: sqlite3.Connection):
    """Asegura que las tablas existan en la conexión dada."""
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
