# services/sync_service.py
"""
Servicio de sincronización LAN para GT7 Telemetry Pro.
Descubre peers en la red local mediante UDP broadcast y sincroniza
sesiones de telemetría mediante TCP.
"""

import os
import sys
import json
import socket
import struct
import logging
import threading
from PyQt6.QtCore import QThread, pyqtSignal

from core.config import APP_VERSION
from core.db_portability import (
    get_session_fingerprints,
    export_sessions_to_buffer,
    import_sessions_from_buffer,
)

UDP_PORT = 33741
TCP_PORT = 33742
BEACON_INTERVAL = 3.0  # segundos
PEER_TIMEOUT = 10.0    # segundos sin beacon = peer perdido
BUFFER_SIZE = 65536


def _get_local_ips() -> set:
    """Retorna todas las IPs locales del dispositivo."""
    ips = set()
    try:
        # Truco para obtener la IP LAN sin depender de netifaces
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        try:
            s.connect(("10.255.255.255", 1))
            ips.add(s.getsockname()[0])
        except Exception:
            pass
        finally:
            s.close()
        ips.add("127.0.0.1")
    except Exception:
        pass
    return ips


class PeerDiscovery(QThread):
    """
    Descubre otros dispositivos con GT7 Telemetry Pro en la red local
    mediante UDP broadcast.
    """
    peer_found = pyqtSignal(str, str, int, int)   # hostname, ip, session_count, tcp_port
    peer_lost = pyqtSignal(str)                    # ip

    def __init__(self, db_path: str):
        super().__init__()
        self.db_path = db_path
        self._running = False
        self._peers = {}  # ip -> last_seen timestamp
        self._local_ips = _get_local_ips()

    def run(self):
        self._running = True

        # Socket para enviar beacons
        send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        send_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        send_sock.settimeout(0.5)

        # Socket para recibir beacons
        recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if sys.platform == 'darwin':
            recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        recv_sock.bind(('', UDP_PORT))
        recv_sock.settimeout(1.0)

        import time
        last_beacon = 0

        while self._running:
            now = time.time()

            # Enviar beacon periódicamente
            if now - last_beacon >= BEACON_INTERVAL:
                try:
                    fingerprints = get_session_fingerprints(self.db_path)
                    beacon = json.dumps({
                        'app': 'GT7TP',
                        'version': APP_VERSION,
                        'hostname': socket.gethostname(),
                        'sessions': len(fingerprints),
                        'port': TCP_PORT,
                    }).encode('utf-8')
                    send_sock.sendto(beacon, ('255.255.255.255', UDP_PORT))
                except Exception as e:
                    logging.debug(f"Error enviando beacon: {e}")
                last_beacon = now

            # Recibir beacons de otros peers
            try:
                data, addr = recv_sock.recvfrom(BUFFER_SIZE)
                sender_ip = addr[0]

                # Ignorar nuestros propios beacons
                if sender_ip in self._local_ips:
                    continue

                payload = json.loads(data.decode('utf-8'))
                if payload.get('app') != 'GT7TP':
                    continue

                hostname = payload.get('hostname', 'Unknown')
                sessions = payload.get('sessions', 0)
                port = payload.get('port', TCP_PORT)

                is_new = sender_ip not in self._peers
                self._peers[sender_ip] = now

                if is_new:
                    self.peer_found.emit(hostname, sender_ip, sessions, port)

            except socket.timeout:
                pass
            except Exception as e:
                logging.debug(f"Error recibiendo beacon: {e}")

            # Limpiar peers expirados
            expired = [ip for ip, ts in self._peers.items() if now - ts > PEER_TIMEOUT]
            for ip in expired:
                del self._peers[ip]
                self.peer_lost.emit(ip)

        send_sock.close()
        recv_sock.close()

    def stop(self):
        self._running = False


class SyncServer(QThread):
    """
    Servidor TCP que responde a solicitudes de sincronización de peers.
    Corre en background mientras el diálogo de sync está abierto.
    """
    sync_request_received = pyqtSignal(str)  # ip del peer que solicita sync

    def __init__(self, db_path: str):
        super().__init__()
        self.db_path = db_path
        self._running = False
        self._server_socket = None

    def run(self):
        self._running = True
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if sys.platform == 'darwin':
            self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self._server_socket.settimeout(1.0)
        self._server_socket.bind(('', TCP_PORT))
        self._server_socket.listen(5)

        logging.info(f"SyncServer escuchando en TCP:{TCP_PORT}")

        while self._running:
            try:
                client_sock, addr = self._server_socket.accept()
                # Manejar cada conexión en un hilo separado
                handler = threading.Thread(
                    target=self._handle_client,
                    args=(client_sock, addr),
                    daemon=True
                )
                handler.start()
            except socket.timeout:
                continue
            except Exception as e:
                if self._running:
                    logging.error(f"SyncServer error: {e}")

        self._server_socket.close()
        logging.info("SyncServer detenido")

    def _handle_client(self, client_sock: socket.socket, addr: tuple):
        """Maneja una conexión entrante de un peer."""
        try:
            client_sock.settimeout(30.0)

            while True:
                # Leer longitud del mensaje (4 bytes, big-endian)
                length_data = self._recv_exact(client_sock, 4)
                if not length_data:
                    break
                msg_len = struct.unpack('>I', length_data)[0]

                # Leer el mensaje
                msg_data = self._recv_exact(client_sock, msg_len)
                if not msg_data:
                    break

                request = json.loads(msg_data.decode('utf-8'))
                cmd = request.get('cmd')

                if cmd == 'LIST_SESSIONS':
                    fingerprints = get_session_fingerprints(self.db_path)
                    response = {
                        'sessions': [
                            {
                                'start_time': fp[0],
                                'car_id': fp[1],
                                'car_name': fp[2],
                                'total_laps': fp[3],
                                'best_laptime': fp[4],
                            }
                            for fp in fingerprints
                        ]
                    }
                    self._send_json(client_sock, response)

                elif cmd == 'REQUEST_SESSIONS':
                    keys = [tuple(k) for k in request.get('keys', [])]
                    buffer = export_sessions_to_buffer(self.db_path, keys)
                    # Enviar tamaño del buffer + buffer
                    client_sock.sendall(struct.pack('>I', len(buffer)))
                    client_sock.sendall(buffer)

                elif cmd == 'PUSH_SESSIONS':
                    # El peer quiere enviarnos sesiones que nos faltan
                    buf_len_data = self._recv_exact(client_sock, 4)
                    buf_len = struct.unpack('>I', buf_len_data)[0]
                    buffer = self._recv_exact(client_sock, buf_len)
                    sessions, rows = import_sessions_from_buffer(buffer, self.db_path)
                    self._send_json(client_sock, {'imported_sessions': sessions, 'imported_rows': rows})

                elif cmd == 'DONE':
                    break
                else:
                    self._send_json(client_sock, {'error': f'Unknown command: {cmd}'})

        except Exception as e:
            logging.error(f"Error manejando peer {addr}: {e}")
        finally:
            client_sock.close()

    def _send_json(self, sock: socket.socket, obj: dict):
        """Envía un objeto JSON precedido por su longitud (4 bytes)."""
        data = json.dumps(obj).encode('utf-8')
        sock.sendall(struct.pack('>I', len(data)))
        sock.sendall(data)

    def _recv_exact(self, sock: socket.socket, n: int) -> bytes:
        """Recibe exactamente n bytes del socket."""
        data = b''
        while len(data) < n:
            chunk = sock.recv(n - len(data))
            if not chunk:
                return None
            data += chunk
        return data

    def stop(self):
        self._running = False


class SyncClient(QThread):
    """
    Cliente TCP que se conecta a un peer y ejecuta la sincronización
    bidireccional de sesiones.
    """
    # Señales para la UI
    comparison_ready = pyqtSignal(int, int)   # (sessions_to_send, sessions_to_receive)
    transfer_progress = pyqtSignal(int)       # porcentaje 0-100
    sync_complete = pyqtSignal(int, int)      # (total_sent, total_received)
    error_occurred = pyqtSignal(str)

    def __init__(self, db_path: str, peer_ip: str, peer_port: int = TCP_PORT):
        super().__init__()
        self.db_path = db_path
        self.peer_ip = peer_ip
        self.peer_port = peer_port
        self._cancelled = False

    def run(self):
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(30.0)
            sock.connect((self.peer_ip, self.peer_port))

            # Paso 1: Obtener lista de sesiones del peer
            self._send_json(sock, {'cmd': 'LIST_SESSIONS'})
            peer_response = self._recv_json(sock)
            peer_sessions = peer_response.get('sessions', [])
            peer_keys = set()
            for s in peer_sessions:
                peer_keys.add((s['start_time'], s['car_id']))

            # Paso 2: Obtener nuestras sesiones
            local_fingerprints = get_session_fingerprints(self.db_path)
            local_keys = set()
            for fp in local_fingerprints:
                local_keys.add((fp[0], fp[1]))

            # Paso 3: Calcular diferencias
            we_need = peer_keys - local_keys     # Sesiones que el peer tiene y nosotros no
            they_need = local_keys - peer_keys   # Sesiones que nosotros tenemos y el peer no

            self.comparison_ready.emit(len(they_need), len(we_need))
            self.transfer_progress.emit(10)

            if self._cancelled:
                self._send_json(sock, {'cmd': 'DONE'})
                return

            total_received = 0
            total_sent = 0

            # Paso 4: Solicitar las sesiones que nos faltan
            if we_need:
                self._send_json(sock, {
                    'cmd': 'REQUEST_SESSIONS',
                    'keys': [list(k) for k in we_need]
                })
                # Recibir buffer comprimido
                buf_len_data = self._recv_exact(sock, 4)
                buf_len = struct.unpack('>I', buf_len_data)[0]
                buffer = self._recv_exact(sock, buf_len)
                sessions_imported, rows_imported = import_sessions_from_buffer(buffer, self.db_path)
                total_received = sessions_imported
                self.transfer_progress.emit(50)

            # Paso 5: Enviar las sesiones que el peer necesita
            if they_need:
                buffer = export_sessions_to_buffer(self.db_path, list(they_need))
                self._send_json(sock, {'cmd': 'PUSH_SESSIONS'})
                sock.sendall(struct.pack('>I', len(buffer)))
                sock.sendall(buffer)
                # Esperar confirmación
                response = self._recv_json(sock)
                total_sent = response.get('imported_sessions', 0)
                self.transfer_progress.emit(90)

            # Paso 6: Cerrar
            self._send_json(sock, {'cmd': 'DONE'})
            self.transfer_progress.emit(100)
            self.sync_complete.emit(total_sent, total_received)

        except Exception as e:
            logging.error(f"SyncClient error: {e}")
            self.error_occurred.emit(str(e))
        finally:
            if sock:
                sock.close()

    def cancel(self):
        self._cancelled = True

    def _send_json(self, sock: socket.socket, obj: dict):
        """Envía un objeto JSON precedido por su longitud (4 bytes)."""
        data = json.dumps(obj).encode('utf-8')
        sock.sendall(struct.pack('>I', len(data)))
        sock.sendall(data)

    def _recv_json(self, sock: socket.socket) -> dict:
        """Recibe un mensaje JSON precedido por su longitud."""
        length_data = self._recv_exact(sock, 4)
        if not length_data:
            return {}
        msg_len = struct.unpack('>I', length_data)[0]
        msg_data = self._recv_exact(sock, msg_len)
        if not msg_data:
            return {}
        return json.loads(msg_data.decode('utf-8'))

    def _recv_exact(self, sock: socket.socket, n: int) -> bytes:
        """Recibe exactamente n bytes del socket."""
        data = b''
        while len(data) < n:
            chunk = sock.recv(min(n - len(data), BUFFER_SIZE))
            if not chunk:
                return None
            data += chunk
        return data
