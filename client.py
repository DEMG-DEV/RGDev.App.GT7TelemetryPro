import socket
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

    def start(self):
        if self.running:
            return
            
        self.running = True
        self.raw_queue.queue.clear()
        
        # Start Threads
        self.net_thread = threading.Thread(target=self._network_capture_loop, daemon=True)
        self.parse_thread = threading.Thread(target=self._parser_loop, daemon=True)
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        
        self.net_thread.start()
        self.parse_thread.start()
        self.heartbeat_thread.start()

    def stop(self):
        self.running = False
        
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

    def _network_capture_loop(self):
        # Setup UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Maximize buffer to avoid dropped packets
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)
        except Exception:
            pass # Ignore if OS restricts buffer size
            
        try:
            sock.bind(('0.0.0.0', self.listen_port))
        except Exception as e:
            if self.on_error:
                self.on_error(f"Failed to bind port {self.listen_port}: {e}")
            self.running = False
            return

        sock.settimeout(1.0)
        
        while self.running:
            try:
                data, addr = sock.recvfrom(4096)
                
                # If we were auto-discovering, set the IP once we receive a packet
                if not self.console_ip:
                    self.console_ip = addr[0]
                    if self.on_connection_established:
                        self.on_connection_established(self.console_ip)
                
                if addr[0] == self.console_ip:
                    self.last_packet_time = time.time()
                    try:
                        self.raw_queue.put_nowait(data)
                    except queue.Full:
                        pass # Drop packet if queue is full (parser is too slow)
            except socket.timeout:
                if self.console_ip and (time.time() - self.last_packet_time > 3.0):
                    if self.on_connection_lost:
                        self.on_connection_lost()
                    self.console_ip = None # Reset to auto-discover mode
                continue
            except Exception as e:
                if self.running and self.on_error:
                    self.on_error(f"Network error: {e}")
                    
        sock.close()

    def _parser_loop(self):
        while self.running:
            try:
                data = self.raw_queue.get(timeout=1.0)
                if data is None:
                    continue
                    
                decrypted = decrypt_telemetry(data, self.packet_type)
                if decrypted:
                    packet = parse_telemetry_packet(decrypted, self.packet_type)
                    if packet and self.on_packet_received:
                        self.on_packet_received(packet)
            except queue.Empty:
                continue
            except Exception as e:
                pass # Ignore parsing exceptions in real-time loop

    def _heartbeat_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        payload = self.packet_type.encode('ascii')
        
        while self.running:
            target_ip = self.console_ip if self.console_ip else '255.255.255.255'
            try:
                sock.sendto(payload, (target_ip, self.console_port))
            except Exception:
                pass
            
            # Heartbeat every 1.5 seconds (or 100 packets at 60Hz = ~1.6s)
            time.sleep(1.5)
            
        sock.close()
