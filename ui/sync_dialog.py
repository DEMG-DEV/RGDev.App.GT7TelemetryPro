# ui/sync_dialog.py
"""
Diálogo de sincronización LAN para GT7 Telemetry Pro.
Permite descubrir otros dispositivos en la red local y sincronizar
las bases de datos de telemetría bidireccionalmente.
"""

import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QProgressBar, QMessageBox,
    QGroupBox, QWidget
)
from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QFont, QIcon

from ui.theme import Theme
from services.sync_service import PeerDiscovery, SyncServer, SyncClient


class SyncDialog(QDialog):
    """Diálogo modal para sincronización de datos por red local."""

    def __init__(self, db_path: str, parent=None):
        super().__init__(parent)
        self.db_path = db_path
        self.setWindowTitle("🔄 Sincronización LAN")
        self.setMinimumSize(520, 480)
        self.setModal(True)

        # Servicios de red
        self.discovery = None
        self.sync_server = None
        self.sync_client = None
        self._peers = {}  # ip -> (hostname, sessions, port)

        self._init_ui()
        self._start_services()

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # --- Encabezado ---
        header = QLabel("Dispositivos en tu Red Local")
        header.setFont(QFont(Theme.FONT_SANS, 16, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {Theme.TEXT_PRIMARY};")
        layout.addWidget(header)

        self.lbl_searching = QLabel("🔍 Buscando dispositivos con GT7 Telemetry Pro...")
        self.lbl_searching.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 13px;")
        layout.addWidget(self.lbl_searching)

        # --- Lista de peers ---
        self.peer_list = QListWidget()
        self.peer_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {Theme.BG_PANEL};
                border: 1px solid {Theme.BORDER};
                border-radius: 6px;
                font-size: 14px;
                padding: 4px;
            }}
            QListWidget::item {{
                padding: 10px;
                border-bottom: 1px solid {Theme.BORDER};
                border-radius: 4px;
            }}
            QListWidget::item:selected {{
                background-color: {Theme.ACCENT_BLUE};
                color: white;
            }}
        """)
        self.peer_list.setMinimumHeight(200)
        self.peer_list.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.peer_list)

        # --- Resumen de comparación ---
        self.summary_group = QGroupBox("Resumen de Sincronización")
        self.summary_group.setVisible(False)
        summary_layout = QVBoxLayout()
        
        self.lbl_to_send = QLabel("→ Sesiones a enviar: —")
        self.lbl_to_send.setStyleSheet(f"color: {Theme.ACCENT_BLUE}; font-weight: bold; font-size: 13px;")
        self.lbl_to_receive = QLabel("← Sesiones a recibir: —")
        self.lbl_to_receive.setStyleSheet(f"color: {Theme.ACCENT_GREEN}; font-weight: bold; font-size: 13px;")
        
        summary_layout.addWidget(self.lbl_to_send)
        summary_layout.addWidget(self.lbl_to_receive)
        self.summary_group.setLayout(summary_layout)
        layout.addWidget(self.summary_group)

        # --- Barra de progreso ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet(Theme.progress_style(Theme.ACCENT_BLUE))
        layout.addWidget(self.progress_bar)

        # --- Estado ---
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 13px;")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_status)

        # --- Botones ---
        btn_layout = QHBoxLayout()

        self.btn_sync = QPushButton("🔄 Sincronizar")
        self.btn_sync.setEnabled(False)
        self.btn_sync.setStyleSheet(Theme.btn_style(
            Theme.ACCENT_GREEN, '#FFFFFF',
            border_color='#229954', hover_bg='#2ECC71',
            pressed_bg='#1E8449', padding='10px 24px'
        ))
        self.btn_sync.clicked.connect(self._start_sync)

        self.btn_close = QPushButton("Cerrar")
        self.btn_close.setStyleSheet(Theme.btn_style(
            '#E0E0E0', Theme.TEXT_PRIMARY,
            hover_bg='#D0D0D0', padding='10px 24px'
        ))
        self.btn_close.clicked.connect(self.close)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_sync)
        btn_layout.addWidget(self.btn_close)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def _start_services(self):
        """Inicia el descubrimiento UDP y el servidor TCP."""
        # Servidor TCP (para responder a solicitudes de otros peers)
        self.sync_server = SyncServer(self.db_path)
        self.sync_server.start()

        # Descubrimiento UDP
        self.discovery = PeerDiscovery(self.db_path)
        self.discovery.peer_found.connect(self._on_peer_found)
        self.discovery.peer_lost.connect(self._on_peer_lost)
        self.discovery.start()

    @pyqtSlot(str, str, int, int)
    def _on_peer_found(self, hostname: str, ip: str, session_count: int, port: int):
        """Se encontró un nuevo peer en la red."""
        if ip in self._peers:
            return

        self._peers[ip] = (hostname, session_count, port)

        item = QListWidgetItem(f"🖥️  {hostname}  ({ip})  —  {session_count} sesiones")
        item.setData(Qt.ItemDataRole.UserRole, ip)
        self.peer_list.addItem(item)

        self.lbl_searching.setText(f"✅ {len(self._peers)} dispositivo(s) encontrado(s)")
        self.lbl_searching.setStyleSheet(f"color: {Theme.ACCENT_GREEN}; font-size: 13px; font-weight: bold;")

    @pyqtSlot(str)
    def _on_peer_lost(self, ip: str):
        """Un peer dejó de responder."""
        if ip not in self._peers:
            return

        del self._peers[ip]

        # Remover de la lista visual
        for i in range(self.peer_list.count()):
            item = self.peer_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == ip:
                self.peer_list.takeItem(i)
                break

        if not self._peers:
            self.lbl_searching.setText("🔍 Buscando dispositivos con GT7 Telemetry Pro...")
            self.lbl_searching.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 13px;")

    def _on_selection_changed(self):
        """Habilita el botón de sync cuando se selecciona un peer."""
        has_selection = len(self.peer_list.selectedItems()) > 0
        self.btn_sync.setEnabled(has_selection)

    def _start_sync(self):
        """Inicia la sincronización con el peer seleccionado."""
        selected = self.peer_list.selectedItems()
        if not selected:
            return

        ip = selected[0].data(Qt.ItemDataRole.UserRole)
        peer_info = self._peers.get(ip)
        if not peer_info:
            return

        hostname, _, port = peer_info

        self.btn_sync.setEnabled(False)
        self.peer_list.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.lbl_status.setText(f"Conectando con {hostname}...")
        self.lbl_status.setStyleSheet(f"color: {Theme.ACCENT_BLUE}; font-size: 13px; font-weight: bold;")

        # Crear y lanzar el cliente de sync
        self.sync_client = SyncClient(self.db_path, ip, port)
        self.sync_client.comparison_ready.connect(self._on_comparison_ready)
        self.sync_client.transfer_progress.connect(self._on_transfer_progress)
        self.sync_client.sync_complete.connect(self._on_sync_complete)
        self.sync_client.error_occurred.connect(self._on_sync_error)
        self.sync_client.start()

    @pyqtSlot(int, int)
    def _on_comparison_ready(self, to_send: int, to_receive: int):
        """El cliente terminó de comparar sesiones."""
        self.summary_group.setVisible(True)
        self.lbl_to_send.setText(f"→ Sesiones a enviar al peer: {to_send}")
        self.lbl_to_receive.setText(f"← Sesiones a recibir del peer: {to_receive}")

        if to_send == 0 and to_receive == 0:
            self.lbl_status.setText("✅ Ambos dispositivos ya están sincronizados.")
            self.lbl_status.setStyleSheet(f"color: {Theme.ACCENT_GREEN}; font-size: 13px; font-weight: bold;")
        else:
            self.lbl_status.setText(f"Transfiriendo {to_send + to_receive} sesiones...")

    @pyqtSlot(int)
    def _on_transfer_progress(self, percent: int):
        """Actualiza la barra de progreso."""
        self.progress_bar.setValue(percent)

    @pyqtSlot(int, int)
    def _on_sync_complete(self, total_sent: int, total_received: int):
        """Sincronización completada exitosamente."""
        self.progress_bar.setValue(100)

        total = total_sent + total_received
        if total == 0:
            msg = "✅ Ambos dispositivos ya están sincronizados. No se transfirieron datos."
        else:
            msg = f"✅ ¡Sincronización completa! Enviadas: {total_sent}, Recibidas: {total_received}"

        self.lbl_status.setText(msg)
        self.lbl_status.setStyleSheet(f"color: {Theme.ACCENT_GREEN}; font-size: 14px; font-weight: bold;")

        self.btn_sync.setEnabled(True)
        self.peer_list.setEnabled(True)

    @pyqtSlot(str)
    def _on_sync_error(self, error_msg: str):
        """Error durante la sincronización."""
        self.progress_bar.setVisible(False)
        self.lbl_status.setText(f"❌ Error: {error_msg}")
        self.lbl_status.setStyleSheet(f"color: {Theme.ACCENT_RED}; font-size: 13px; font-weight: bold;")

        self.btn_sync.setEnabled(True)
        self.peer_list.setEnabled(True)

        QMessageBox.warning(self, "Error de Sincronización",
                            f"No se pudo completar la sincronización:\n{error_msg}")

    def closeEvent(self, event):
        """Detiene todos los servicios de red al cerrar el diálogo."""
        if self.sync_client:
            self.sync_client.cancel()
            self.sync_client.wait(2000)

        if self.discovery:
            self.discovery.stop()
            self.discovery.wait(2000)

        if self.sync_server:
            self.sync_server.stop()
            self.sync_server.wait(2000)

        event.accept()
