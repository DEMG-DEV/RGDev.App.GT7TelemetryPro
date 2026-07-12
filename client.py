import socket
import struct
import threading
import queue
import time
import select
from typing import Optional, Callable
from models import parse_telemetry_packet, GT7TelemetryPacket
from crypto import decrypt_telemetry

class GT7TelemetryClient:
    def __init__(self, console_ip: Optional[str] = None):
        """
        Initializes the GT7 Telemetry Client.
        If console_ip is None, the client will attempt to auto-discover it via broadcast.
        """
        self.console_ip = console_ip
        self.console_port = 33739
        self.listen_port = 33740
        
        self.packet_type = 'C' # Full racing telemetry packet
        self.running = False
        
        # Thread-safe queue for raw network packets
        self.raw_queue = queue.Queue(maxsize=1000)
        
        # Threads
        self.net_thread = None
        self.parse_thread = None
        self.heartbeat_thread = None
        
        # Callbacks
        self.on_packet_received: Optional[Callable[[GT7TelemetryPacket], None]] = None
        self.on_connection_established: Optional[Callable[[str], None]] = None
        self.on_connection_lost: Optional[Callable[[], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        
        self.last_packet_time = 0
        
        self.recording = False
        self.record_file = None
        self.record_start_time = 0.0

    def start_recording(self, filename: str):
        import logging
        if not self.recording:
            try:
                self.record_file = open(filename, 'wb')
                self.record_start_time = time.time()
                self.recording = True
                logging.info(f"Successfully started recording to {filename}")
                return True
            except Exception as e:
                logging.error(f"Failed to start recording to {filename}: {e}")
                if self.on_error:
                    self.on_error(f"Failed to start recording: {e}")
                return False
        return False
        
    def stop_recording(self):
        """Stops recording the telemetry session."""
        import logging
        if self.recording:
            self.recording = False
            if self.record_file:
                logging.info("Stopping recording, flushing and fsyncing...")
                try:
                    self.record_file.flush()
                    import os
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
        try:
            # Create shared socket for threads
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except AttributeError:
                pass
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.bind(('0.0.0.0', self.listen_port))
            
            # Start Threads
            self.net_thread = threading.Thread(target=self._network_capture_loop, args=(sock,), daemon=True)
            self.parse_thread = threading.Thread(target=self._parser_loop, daemon=True)
            self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
            
            self.net_thread.start()
            self.parse_thread.start()
            self.heartbeat_thread.start()
        except Exception as e:
            self.running = False
            if self.on_error:
                self.on_error(f"Failed to start client: {e}")
            print(f"Failed to start client: {e}")

    def stop(self):
        self.running = False
        self.stop_recording()
        
        # Unblock queues and threads if necessary
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

    def _network_capture_loop(self, sock: socket.socket):
        import logging
        # Maximize buffer to avoid dropped packets
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)
        except Exception:
            pass # Ignore if OS restricts buffer size
            
        sock.settimeout(1.0)
        logging.info("Network capture loop started.")
        
        while self.running:
            try:
                data, addr = sock.recvfrom(4096)
                logging.debug(f"Received {len(data)} bytes from {addr}")
                
                # If we were auto-discovering, set the IP once we receive a packet
                if not self.console_ip:
                    self.console_ip = addr[0]
                    logging.info(f"Auto-discovered console IP: {self.console_ip}")
                    if self.on_connection_established:
                        self.on_connection_established(self.console_ip)
                
                if addr[0] == self.console_ip:
                    self.last_packet_time = time.time()
                    try:
                        self.raw_queue.put_nowait(data)
                    except queue.Full:
                        logging.warning("Raw queue is full, dropping packet!")
            except socket.timeout:
                if self.console_ip and (time.time() - self.last_packet_time > 3.0):
                    logging.warning("Connection lost due to timeout (no packets for >3s).")
                    if self.on_connection_lost:
                        self.on_connection_lost()
                    self.console_ip = None # Reset to auto-discover mode
                continue
            except Exception as e:
                logging.error(f"Network error: {e}")
                if self.running and self.on_error:
                    self.on_error(f"Network error: {e}")
                    
        sock.close()
        logging.info("Network capture loop ended.")

    def _parser_loop(self):
        import logging
        logging.info("Parser loop started.")
        while self.running:
            try:
                data = self.raw_queue.get(timeout=1.0)
                if data is None:
                    continue
                    
                decrypted = decrypt_telemetry(data, self.packet_type)
                if decrypted:
                    logging.debug(f"Packet decrypted successfully, size: {len(decrypted)}")
                    if self.recording and self.record_file:
                        try:
                            timestamp = time.time() - self.record_start_time
                            header = struct.pack('<dI', timestamp, len(decrypted))
                            self.record_file.write(header + decrypted)
                        except Exception as e:
                            logging.error(f"Recording error: {e}")
                            
                    packet = parse_telemetry_packet(decrypted, self.packet_type)
                    if packet:
                        if self.on_packet_received:
                            self.on_packet_received(packet)
                    else:
                        logging.error("parse_telemetry_packet returned None")
                else:
                    logging.error("decrypt_telemetry returned None")
            except queue.Empty:
                continue
            except Exception as e:
                logging.exception(f"Exception in parser loop: {e}")
        logging.info("Parser loop ended.")

    def _heartbeat_loop(self):
        import logging
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        payload = self.packet_type.encode('ascii')
        logging.info("Heartbeat loop started.")
        
        while self.running:
            target_ip = self.console_ip if self.console_ip else '255.255.255.255'
            try:
                sock.sendto(payload, (target_ip, self.console_port))
                logging.debug(f"Sent heartbeat '{self.packet_type}' to {target_ip}:{self.console_port}")
            except Exception as e:
                logging.error(f"Failed to send heartbeat to {target_ip}: {e}")
            
            # Heartbeat every 1.5 seconds (or 100 packets at 60Hz = ~1.6s)
            time.sleep(1.5)
            
        sock.close()
        logging.info("Heartbeat loop ended.")
