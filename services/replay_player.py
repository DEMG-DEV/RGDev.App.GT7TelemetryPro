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
        self.play_thread = None
        
    def load(self, filename: str):
        self.filename = filename
        
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
        try:
            with open(self.filename, 'rb') as f:
                start_time = time.time()
                while self.running:
                    header_bytes = f.read(12)
                    if not header_bytes or len(header_bytes) < 12:
                        break
                        
                    packet_timestamp, packet_size = struct.unpack('<dI', header_bytes)
                    
                    payload = f.read(packet_size)
                    if not payload or len(payload) < packet_size:
                        break
                        
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
