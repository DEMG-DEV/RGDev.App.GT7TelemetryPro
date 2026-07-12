import socket
import struct
import threading
import queue
import time
import os
import logging
from typing import Optional
from PyQt6.QtCore import pyqtSignal

from services.provider import TelemetryProvider
from core.models import parse_telemetry_packet, GT7TelemetryPacket
from services.crypto import decrypt_telemetry

class GT7LiveClient(TelemetryProvider):
    connection_established = pyqtSignal(str)
    connection_lost = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, console_ip: Optional[str] = None):
        super().__init__()
        self.console_ip = console_ip
        self.console_port = 33739
        self.listen_port = 33740
        
        self.packet_type = 'C'
        self.running = False
        
        self.raw_queue = queue.Queue(maxsize=1000)
        
        self.net_thread = None
        self.parse_thread = None
        self.heartbeat_thread = None
        
        self.last_packet_time = 0
        
        self.recording = False
        self.record_file = None
        self.record_start_time = 0.0

    def start_recording(self, filename: str):
        if not self.recording:
            try:
                self.record_file = open(filename, 'wb')
                self.record_start_time = time.time()
                self.recording = True
                logging.info(f"Successfully started recording to {filename}")
                return True
            except Exception as e:
                logging.error(f"Failed to start recording to {filename}: {e}")
                self.error_occurred.emit(f"Failed to start recording: {e}")
                return False
        return False
        
    def stop_recording(self):
        if self.recording:
            self.recording = False
            if self.record_file:
                logging.info("Stopping recording, flushing and fsyncing...")
                try:
                    self.record_file.flush()
                    os.fsync(self.record_file.fileno())
                    logging.info("Flush and fsync successful.")
                except Exception as e:
                    logging.error(f"Error flushing record file: {e}")
                self.record_file.close()
                self.record_file = None
                
    def start(self):
        if self.running:
            return
            
        self.running = True
        self.is_connected = False
        self.last_packet_time = time.time()
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except AttributeError:
                pass
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.sock.bind(('0.0.0.0', self.listen_port))
            
            self.net_thread = threading.Thread(target=self._network_capture_loop, daemon=True)
            self.parse_thread = threading.Thread(target=self._parser_loop, daemon=True)
            self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
            
            self.net_thread.start()
            self.parse_thread.start()
            self.heartbeat_thread.start()
        except Exception as e:
            self.running = False
            self.error_occurred.emit(f"Failed to start client: {e}")
            logging.error(f"Failed to start client: {e}")

    def stop(self):
        self.running = False
        self.is_connected = False
        self.last_packet_time = 0
        self.stop_recording()
        
        try:
            if hasattr(self, 'sock') and self.sock:
                self.sock.close()
        except Exception:
            pass
        
        try:
            self.raw_queue.put_nowait(None)
        except queue.Full:
            pass

        if self.net_thread and self.net_thread.is_alive():
            self.net_thread.join(timeout=1.0)
        if self.parse_thread and self.parse_thread.is_alive():
            self.parse_thread.join(timeout=1.0)
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=1.0)

    def _network_capture_loop(self):
        try:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)
        except Exception:
            pass 
            
        self.sock.settimeout(1.0)
        
        while self.running:
            try:
                data, addr = self.sock.recvfrom(4096)
                
                if not self.is_connected:
                    self.is_connected = True
                    self.console_ip = addr[0]
                    self.connection_established.emit(self.console_ip)
                    
                self.last_packet_time = time.time()
                try:
                    self.raw_queue.put_nowait(data)
                except queue.Full:
                    pass
            except socket.timeout:
                if self.is_connected and (time.time() - self.last_packet_time > 3.0):
                    self.is_connected = False
                    self.connection_lost.emit()
                    self.console_ip = None 
                continue
            except Exception as e:
                # Only log error if we are still supposed to be running (ignore closing errors)
                if self.running and not isinstance(e, OSError):
                    self.error_occurred.emit(f"Network error: {e}")
                    
        try:
            self.sock.close()
        except Exception:
            pass

    def _parser_loop(self):
        while self.running:
            try:
                data = self.raw_queue.get(timeout=1.0)
                if data is None:
                    continue
                    
                decrypted = decrypt_telemetry(data, self.packet_type)
                if decrypted:
                    if self.recording and self.record_file:
                        try:
                            timestamp = time.time() - self.record_start_time
                            header = struct.pack('<dI', timestamp, len(decrypted))
                            self.record_file.write(header + decrypted)
                        except Exception as e:
                            logging.error(f"Recording error: {e}")
                            
                    packet = parse_telemetry_packet(decrypted, self.packet_type)
                    if packet:
                        self.packet_signal.emit(packet)
            except queue.Empty:
                continue
            except Exception as e:
                logging.exception(f"Exception in parser loop: {e}")

    def _heartbeat_loop(self):
        payload = self.packet_type.encode('ascii')
        
        while self.running:
            try:
                # Always send a broadcast heartbeat (this is what GT7 typically expects)
                self.sock.sendto(payload, ('255.255.255.255', self.console_port))
                
                # If a specific IP is provided, also send a unicast heartbeat to it
                if self.console_ip and self.console_ip != '255.255.255.255':
                    self.sock.sendto(payload, (self.console_ip, self.console_port))
            except Exception:
                pass
            time.sleep(1.5)

