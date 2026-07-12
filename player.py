import struct
import time
import threading
from typing import Optional, Callable
from models import parse_telemetry_packet, GT7TelemetryPacket

class GT7SessionPlayer:
    def __init__(self):
        self.running = False
        self.filename = None
        
        self.on_packet_received: Optional[Callable[[GT7TelemetryPacket], None]] = None
        self.on_playback_finished: Optional[Callable[[], None]] = None
        
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
                    # Read header
                    header_bytes = f.read(12)
                    if not header_bytes or len(header_bytes) < 12:
                        break
                        
                    packet_timestamp, packet_size = struct.unpack('<dI', header_bytes)
                    
                    # Read payload
                    payload = f.read(packet_size)
                    if not payload or len(payload) < packet_size:
                        break
                        
                    # Sync timing
                    current_time = time.time() - start_time
                    time_to_wait = packet_timestamp - current_time
                    if time_to_wait > 0:
                        time.sleep(time_to_wait)
                        
                    if not self.running:
                        break
                        
                    # Parse and emit
                    packet = parse_telemetry_packet(payload, 'C') # assuming C for now
                    if packet and self.on_packet_received:
                        self.on_packet_received(packet)
                        
        except Exception as e:
            print("Playback error:", e)
            
        self.running = False
        if self.on_playback_finished:
            self.on_playback_finished()
