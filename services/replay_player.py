import struct
import time
import threading
import logging
from PyQt6.QtCore import pyqtSignal

from services.provider import TelemetryProvider
from core.models import parse_telemetry_packet

class GT7SessionPlayer(TelemetryProvider):
    playback_finished = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.running = False
        self.filename = None
        self.session_id = None
        self.play_thread = None
        
    def load(self, filename: str, session_id: int = None):
        self.filename = filename
        self.session_id = session_id
        
    def play(self):
        if self.running or not self.filename:
            return
            
        self.running = True
        self.play_thread = threading.Thread(target=self._playback_loop, daemon=True)
        self.play_thread.start()
        
    def stop(self):
        self.running = False
        if self.play_thread and self.play_thread.is_alive():
            self.play_thread.join(timeout=1.0)
            
    def _playback_loop(self):
        import sqlite3
        start_time = time.time()
        
        try:
            with sqlite3.connect(self.filename) as conn:
                cursor = conn.cursor()
                if self.session_id is not None:
                    cursor.execute("SELECT timestamp, raw_packet FROM telemetry WHERE session_id = ? ORDER BY id", (self.session_id,))
                else:
                    # Fallback for old single-file DBs without session_id
                    cursor.execute("SELECT timestamp, raw_packet FROM telemetry ORDER BY id")
                
                for row in cursor:
                    if not self.running:
                        break
                        
                    packet_timestamp, payload = row
                    
                    current_time = time.time() - start_time
                    time_to_wait = packet_timestamp - current_time
                    if time_to_wait > 0:
                        time.sleep(time_to_wait)
                        
                    if not self.running:
                        break
                        
                    packet = parse_telemetry_packet(payload, 'C')
                    if packet:
                        self.packet_signal.emit(packet)
                        
        except Exception as e:
            logging.error(f"Playback error: {e}")
            
        self.running = False
        self.playback_finished.emit()

