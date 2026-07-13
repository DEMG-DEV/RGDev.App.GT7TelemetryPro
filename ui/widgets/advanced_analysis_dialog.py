import sqlite3
import json
import os
import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QLabel,
                             QSplitter, QWidget, QListWidgetItem, QPushButton,
                             QAbstractItemView, QSlider, QApplication, QProgressDialog)
from PyQt6.QtCore import Qt, QTimer
from ui.widgets.map_widget import MapWidget
from ui.widgets.live_telemetry_widget import LiveTelemetryWidget
from core.models import parse_telemetry_packet
from PyQt6.QtGui import QFont, QColor

class LapAnalysisData:
    def __init__(self, lap_number):
        self.lap_number = lap_number
        self.packets = []
        self.distance = []
        self.time_ms = []
        self.speed = []
        self.throttle = []
        self.brake = []
        self.rpm = []
        self.steer = []
        self.pos_x = []
        self.pos_y = []
        self.pos_z = []
        self.lap_time = 999999999
        self.is_valid = False

class AdvancedAnalysisDialog(QDialog):
    def __init__(self, db_path, session_id=None, parent=None):
        super().__init__(parent)
        self.db_path = db_path
        self.session_id = session_id
        
        self.track_name = "Pista Desconocida"
        self.laps_data = {}  
        self.best_lap = None
        self.active_lap_data = None
        self.selected_id = session_id
        
        self.all_packets = []
        self.current_packet_index = 0
        self.playback_timer = QTimer(self)
        self.playback_timer.timeout.connect(self.playback_tick)
        
        self.setWindowTitle(f"Análisis Avanzado & Explorador de Sesiones")
        self.setGeometry(50, 50, 1600, 900)
        self.setStyleSheet("background-color: #F0F0F0; color: #1A1A1A;")
        
        self.init_ui()
        self._load_sessions()
        
        if self.session_id:
            self._load_data(self.session_id)
        
    def _load_sessions(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, start_time, car_name, total_laps, best_laptime, is_locked FROM sessions ORDER BY id DESC")
                sessions = cursor.fetchall()
                
            self.table_sessions.setRowCount(0)
            for row_idx, row_data in enumerate(sessions):
                self.table_sessions.insertRow(row_idx)
                
                # ID and Lock status
                is_locked = row_data[5]
                lock_str = " 🔒" if is_locked else ""
                id_item = QTableWidgetItem(f"#{row_data[0]}{lock_str}")
                id_item.setData(Qt.ItemDataRole.UserRole, row_data[0])
                id_item.setData(Qt.ItemDataRole.UserRole + 1, is_locked)
                id_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
                id_item.setForeground(QColor('#0000FF') if not is_locked else QColor('#CC0000'))
                self.table_sessions.setItem(row_idx, 0, id_item)
                
                # Fecha
                dt_str = row_data[1][:16] if row_data[1] else "---"
                self.table_sessions.setItem(row_idx, 1, QTableWidgetItem(dt_str))
                
                # Auto
                self.table_sessions.setItem(row_idx, 2, QTableWidgetItem(str(row_data[2])))
                
                # Vueltas
                laps_item = QTableWidgetItem(str(row_data[3]))
                laps_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table_sessions.setItem(row_idx, 3, laps_item)
                
                # Mejor Vuelta
                best_lap = row_data[4]
                if best_lap and best_lap > 0:
                    mins = int(best_lap // 60000)
                    secs = (best_lap % 60000) / 1000.0
                    bl_str = f"{mins:02d}:{secs:06.3f}"
                    bl_item = QTableWidgetItem(bl_str)
                    bl_item.setForeground(QColor('#008080'))
                else:
                    bl_item = QTableWidgetItem("N/A")
                    bl_item.setForeground(QColor('#666666'))
                bl_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table_sessions.setItem(row_idx, 4, bl_item)
                
            # If we had a session_id, select it
            if self.session_id:
                for i in range(self.table_sessions.rowCount()):
                    item = self.table_sessions.item(i, 0)
                    if item.data(Qt.ItemDataRole.UserRole) == self.session_id:
                        self.table_sessions.selectRow(i)
                        break
                        
            self._update_action_buttons()
            
        except Exception as e:
            import logging
            logging.error(f"Error loading sessions: {e}")

    def on_session_selected(self):
        items = self.table_sessions.selectedItems()
        if not items:
            self._update_action_buttons()
            return
            
        row = items[0].row()
        id_item = self.table_sessions.item(row, 0)
        session_id = id_item.data(Qt.ItemDataRole.UserRole)
        
        self.btn_play_pause.setEnabled(True)
        self.playback_slider.setEnabled(True)
        self._update_action_buttons()
        
        if session_id != self.session_id:
            self.session_id = session_id
            self.selected_id = session_id
            self._load_data(self.session_id)
            
    def _update_action_buttons(self):
        if not hasattr(self, 'btn_delete'):
            return
            
        items = self.table_sessions.selectedItems()
        if not items:
            self.btn_delete.setEnabled(False)
            self.btn_lock.setEnabled(False)
            self.btn_lock.setText("🔒 Bloquear")
            return
            
        row = items[0].row()
        id_item = self.table_sessions.item(row, 0)
        is_locked = id_item.data(Qt.ItemDataRole.UserRole + 1)
        
        self.btn_lock.setEnabled(True)
        if is_locked:
            self.btn_delete.setEnabled(False)
            self.btn_lock.setText("🔓 Desbloquear")
            self.btn_lock.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; border-radius: 5px;")
        else:
            self.btn_delete.setEnabled(True)
            self.btn_lock.setText("🔒 Bloquear")
            self.btn_lock.setStyleSheet("background-color: #f6a623; color: black; font-weight: bold; border-radius: 5px;")
            
    def toggle_lock_session(self):
        items = self.table_sessions.selectedItems()
        if not items: return
        row = items[0].row()
        id_item = self.table_sessions.item(row, 0)
        session_id = id_item.data(Qt.ItemDataRole.UserRole)
        is_locked = id_item.data(Qt.ItemDataRole.UserRole + 1)
        
        new_status = 0 if is_locked else 1
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE sessions SET is_locked = ? WHERE id = ?", (new_status, session_id))
            self._load_sessions()
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Fallo al actualizar estado de bloqueo: {e}")
            
    def delete_session(self):
        items = self.table_sessions.selectedItems()
        if not items: return
        row = items[0].row()
        id_item = self.table_sessions.item(row, 0)
        session_id = id_item.data(Qt.ItemDataRole.UserRole)
        is_locked = id_item.data(Qt.ItemDataRole.UserRole + 1)
        
        if is_locked: return
        
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(self, "Eliminar Sesión", 
                                     f"¿Estás seguro que deseas eliminar permanentemente la sesión #{session_id}?\n\nEsto borrará todos sus datos de telemetría y reducirá el tamaño del archivo de la base de datos.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
                                     
        if reply == QMessageBox.StandardButton.Yes:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM telemetry WHERE session_id = ?", (session_id,))
                    cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
                
                # Vacuum cannot run within a transaction, so we run it separately in autocommit mode
                with sqlite3.connect(self.db_path) as conn:
                    conn.isolation_level = None 
                    conn.execute("VACUUM")
                
                self.session_id = None
                self._load_sessions()
                self.laps_data.clear()
                self.list_laps.clear()
                self.p_speed.clear()
                self.map_widget.clear()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Fallo al eliminar sesión: {e}")
        
    def _load_data(self, session_id):
        self.setWindowTitle(f"Análisis Avanzado - Cargando Sesión #{session_id}...")
        self.laps_data.clear()
        self.list_laps.clear()
        self.p_speed.clear()
        self.table_summary.setColumnCount(1)
        self.map_widget.clear()
        self.best_lap = None
        self.active_lap_data = None
        self.track_name = "Pista Desconocida"
        self.all_packets.clear()
        self.current_packet_index = 0
        
        QApplication.processEvents()
        progress = QProgressDialog("Cargando y procesando telemetría...", "Cancelar", 0, 100, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setWindowTitle("Cargando Sesión")
        progress.setStyleSheet("QProgressDialog { background-color: #F0F0F0; color: #1A1A1A; } QLabel { color: #1A1A1A; }")
        progress.show()
        QApplication.processEvents()
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT count(*) FROM telemetry WHERE session_id = ?", (session_id,))
                total_rows = cursor.fetchone()[0]
                
                cursor.execute("SELECT raw_packet FROM telemetry WHERE session_id = ? ORDER BY id ASC", (session_id,))
                rows = cursor.fetchall()
                
                for i, row in enumerate(rows):
                    if i % 1000 == 0:
                        progress.setValue(int((i / total_rows) * 50))
                        QApplication.processEvents()
                        if progress.wasCanceled():
                            return
                            
                    blob = row[0]
                    packet = parse_telemetry_packet(blob, 'C')
                    if not packet:
                        continue
                    
                    self.all_packets.append(packet)
                    lap = packet.lap_count
                    if lap not in self.laps_data:
                        self.laps_data[lap] = LapAnalysisData(lap)
                    self.laps_data[lap].packets.append(packet)
                    
            best_time = 999999999
            
            for i, (lap, data) in enumerate(list(self.laps_data.items())):
                progress.setValue(50 + int((i / len(self.laps_data)) * 50))
                QApplication.processEvents()
                if progress.wasCanceled():
                    return
                if len(data.packets) < 100:
                    del self.laps_data[lap]
                    continue
                data.lap_time = len(data.packets) * (1000.0 / 60.0)
                data.is_valid = True

            # Filter out Out-Laps (<=0) and In-Laps (max_lap)
            if len(self.laps_data) >= 3:
                max_lap = max(self.laps_data.keys())
                for lap in list(self.laps_data.keys()):
                    if lap <= 0 or lap == max_lap:
                        del self.laps_data[lap]
            elif len(self.laps_data) == 2:
                for lap in list(self.laps_data.keys()):
                    if lap <= 0:
                        del self.laps_data[lap]

            for lap, data in self.laps_data.items():
                if data.lap_time < best_time:
                    best_time = data.lap_time
                    self.best_lap = lap
                
                data.distance.append(0.0)
                data.time_ms.append(0.0)
                data.speed.append(data.packets[0].speed_kmh)
                data.throttle.append(data.packets[0].throttle / 255.0 * 100.0)
                data.brake.append(data.packets[0].brake / 255.0 * 100.0)
                data.rpm.append(data.packets[0].engine_rpm)
                data.steer.append(data.packets[0].wheel_steer_angle)
                data.pos_x.append(data.packets[0].position[0])
                data.pos_y.append(data.packets[0].position[1])
                data.pos_z.append(data.packets[0].position[2])
                
                curr_dist = 0.0
                curr_time = 0.0
                
                for i in range(1, len(data.packets)):
                    p = data.packets[i]
                    dt = 1.0 / 60.0
                    curr_time += dt
                    curr_dist += (p.speed_kmh / 3.6) * dt
                    
                    data.distance.append(curr_dist)
                    data.time_ms.append(curr_time)
                    data.speed.append(p.speed_kmh)
                    data.throttle.append(p.throttle / 255.0 * 100.0)
                    data.brake.append(p.brake / 255.0 * 100.0)
                    data.rpm.append(p.engine_rpm)
                    data.steer.append(p.wheel_steer_angle)
                    data.pos_x.append(p.position[0])
                    data.pos_y.append(p.position[1])
                    data.pos_z.append(p.position[2])
                    
                data.distance = np.array(data.distance)
                data.time_ms = np.array(data.time_ms)
                data.speed = np.array(data.speed)
                data.throttle = np.array(data.throttle)
                data.brake = np.array(data.brake)
                data.rpm = np.array(data.rpm)
                data.steer = np.array(data.steer)
                data.pos_x = np.array(data.pos_x)
                data.pos_y = np.array(data.pos_y)
                data.pos_z = np.array(data.pos_z)
                
            # Track detection
            valid_laps_for_detection = list(self.laps_data.keys())
            if not valid_laps_for_detection and self.best_lap in self.laps_data:
                valid_laps_for_detection = [self.best_lap]
                
            if valid_laps_for_detection:
                dists = []
                elevs = []
                corns = []
                
                for l in valid_laps_for_detection:
                    data_l = self.laps_data[l]
                    dists.append(data_l.distance[-1])
                    elevs.append(np.max(data_l.pos_y) - np.min(data_l.pos_y))
                    corns.append(len(self._detect_corners(data_l)))
                    
                total_dist = np.median(dists)
                elev_diff = np.median(elevs)
                num_corners = np.median(corns)
                
                tracks_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "tracks.json"))
                if os.path.exists(tracks_file):
                    with open(tracks_file, 'r') as f:
                        tracks = json.load(f)
                    
                    best_match = None
                    highest_score = 0
                    
                    for t in tracks:
                        length_diff = abs(t.get('length_m', 0) - total_dist)
                        if length_diff > 300:
                            continue
                        
                        score = 1000 - length_diff
                        score -= abs(t.get('elevation_diff_m', 0) - elev_diff) * 2.0
                        score -= abs(t.get('num_corners', 0) - num_corners) * 5.0
                        
                        if score > highest_score:
                            highest_score = score
                            best_match = t
                            
                    if best_match and highest_score > 0:
                        self.track_name = best_match['name']
            
            self.setWindowTitle(f"Análisis Avanzado - {self.track_name} (Sesión #{session_id})")
            self._populate_laps_list()
            
            if self.all_packets:
                self.playback_slider.setRange(0, len(self.all_packets) - 1)
                self.playback_slider.setValue(0)
                self.update_playback_ui(0)
            
            if self.best_lap in self.laps_data:
                bt = self.laps_data[self.best_lap].lap_time
                if bt < 999999:
                    mins = int(bt // 60000)
                    secs = int((bt % 60000) / 1000)
                    mils = int(bt % 1000)
                    self.lbl_playback_best.setText(f"Best L{self.best_lap}: {mins}:{secs:02d}.{mils:03d}")
            else:
                self.lbl_playback_best.setText("Best: --:--.---")
                
            progress.setValue(100)
            
        except Exception as e:
            import logging
            logging.error(f"Error loading telemetry for analysis: {e}")
            self.setWindowTitle(f"Análisis Avanzado - Error (Sesión #{session_id})")

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        lbl_sessions_title = QLabel("Historial de Sesiones")
        lbl_sessions_title.setStyleSheet("font-weight: bold; font-size: 16px; color: #1A1A1A;")
        
        self.table_sessions = QTableWidget()
        self.table_sessions.setColumnCount(5)
        self.table_sessions.setHorizontalHeaderLabels(["ID", "Fecha / Hora", "Auto", "Vueltas", "Mejor Vuelta"])
        
        header = self.table_sessions.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        self.table_sessions.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_sessions.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table_sessions.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_sessions.setStyleSheet("""
            QTableWidget { background-color: #FFFFFF; color: #000000; border: 1px solid #CCCCCC; font-size: 13px; }
            QHeaderView::section { background-color: #E0E0E0; color: #1A1A1A; font-weight: bold; }
            QTableWidget::item:selected { background-color: #007ACC; color: white; }
        """)
        self.table_sessions.itemSelectionChanged.connect(self.on_session_selected)
        
        btn_action_layout = QHBoxLayout()
        
        self.btn_lock = QPushButton("🔒 Bloquear")
        self.btn_lock.setStyleSheet("background-color: #f6a623; color: black; font-weight: bold; border-radius: 5px; padding: 10px;")
        self.btn_lock.setEnabled(False)
        self.btn_lock.clicked.connect(self.toggle_lock_session)
        
        self.btn_delete = QPushButton("🗑️ Eliminar")
        self.btn_delete.setStyleSheet("background-color: #c5c6c7; color: black; font-weight: bold; border-radius: 5px; padding: 10px;")
        self.btn_delete.setEnabled(False)
        self.btn_delete.clicked.connect(self.delete_session)
        
        btn_action_layout.addWidget(self.btn_lock)
        btn_action_layout.addWidget(self.btn_delete)
        
        playback_layout = QVBoxLayout()
        self.btn_play_pause = QPushButton("▶ Reproducir Sesión")
        self.btn_play_pause.setStyleSheet("background-color: #CCCCCC; color: #000000; font-weight: bold; padding: 12px; border-radius: 5px;")
        self.btn_play_pause.setEnabled(False)
        self.btn_play_pause.clicked.connect(self.toggle_playback)
        
        slider_layout = QHBoxLayout()
        self.lbl_playback_time = QLabel("00:00.000")
        self.lbl_playback_time.setStyleSheet("color: #1A1A1A; font-weight: bold; font-family: Consolas;")
        
        self.playback_slider = QSlider(Qt.Orientation.Horizontal)
        self.playback_slider.setEnabled(False)
        self.playback_slider.valueChanged.connect(self.on_slider_moved)
        self.playback_slider.setStyleSheet("QSlider::handle:horizontal { background-color: #1A1A1A; width: 12px; margin: -4px 0; border-radius: 6px; } QSlider::groove:horizontal { background: #CCCCCC; height: 4px; }")
        
        self.lbl_playback_best = QLabel("Best: --:--.---")
        self.lbl_playback_best.setStyleSheet("color: #FF8C00; font-weight: bold; font-family: Consolas;")
        
        slider_layout.addWidget(self.lbl_playback_time)
        slider_layout.addWidget(self.playback_slider)
        slider_layout.addWidget(self.lbl_playback_best)
        
        playback_layout.addWidget(self.btn_play_pause)
        playback_layout.addLayout(slider_layout)
        
        lbl_list_title = QLabel("Vueltas (Multiselección)")
        lbl_list_title.setStyleSheet("font-weight: bold; font-size: 16px; color: #1A1A1A; padding-top: 15px;")
        
        self.list_laps = QListWidget()
        self.list_laps.setStyleSheet("background-color: #FFFFFF; color: #1A1A1A; font-size: 14px; border: 1px solid #CCCCCC;")
        self.list_laps.itemSelectionChanged.connect(self.on_lap_selected)
        self.list_laps.itemChanged.connect(self.refresh_plot)
        
        self.colors = ['#0000FF', '#FF00FF', '#008000', '#FF0000', '#800080', '#000000', '#FF8C00']
        
        sessions_container = QWidget()
        s_layout = QVBoxLayout(sessions_container)
        s_layout.setContentsMargins(0,0,0,10)
        s_layout.addWidget(lbl_sessions_title)
        s_layout.addWidget(self.table_sessions)
        s_layout.addLayout(btn_action_layout)
        s_layout.addLayout(playback_layout)
        
        laps_container = QWidget()
        l_layout = QVBoxLayout(laps_container)
        l_layout.setContentsMargins(0,0,0,0)
        l_layout.addWidget(lbl_list_title)
        l_layout.addWidget(self.list_laps)
        
        left_layout.addWidget(sessions_container, stretch=6)
        left_layout.addWidget(laps_container, stretch=4)
        
        self.map_widget = MapWidget("Mapa Interactivo")
        
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        graphs_widget = QWidget()
        graphs_layout = QVBoxLayout(graphs_widget)
        graphs_layout.setContentsMargins(0, 0, 0, 0)
        
        self.p_speed = pg.PlotWidget(title="Velocidad (km/h)")
        self.p_speed.addLegend()
        self.p_speed.showGrid(x=True, y=True, alpha=0.3)
        self.p_speed.setBackground('#FAFAFA')
        self.p_speed.setLabel('bottom', "Distancia de la vuelta (Metros)")
        
        self.vline = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('w', width=1, style=Qt.PenStyle.DashLine))
        
        self.table_summary = QTableWidget()
        self.table_summary.setColumnCount(1)
        self.table_summary.setRowCount(4)
        self.table_summary.horizontalHeader().setVisible(True)
        self.table_summary.verticalHeader().setVisible(False)
        self.table_summary.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_summary.setStyleSheet("QTableWidget { background-color: #FFFFFF; color: #1A1A1A; font-size: 14px; } QHeaderView::section { background-color: #E0E0E0; color: #1A1A1A; }")
        
        graphs_layout.addWidget(self.p_speed, stretch=2)
        
        lbl_res = QLabel("📋 Resumen de Vueltas (Overlay)")
        lbl_res.setStyleSheet("font-size: 16px; font-weight: bold; color: #1A1A1A; padding-top: 10px;")
        graphs_layout.addWidget(lbl_res)
        graphs_layout.addWidget(self.table_summary, stretch=1)
        
        self.proxy = pg.SignalProxy(self.p_speed.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)
        
        self.telemetry_dashboard = LiveTelemetryWidget()
        
        right_layout.addWidget(self.map_widget, stretch=6)
        right_layout.addWidget(self.telemetry_dashboard, stretch=4)
        
        layout.addWidget(left_panel, stretch=25)
        layout.addWidget(graphs_widget, stretch=50)
        layout.addWidget(right_panel, stretch=25)
        
    def _populate_laps_list(self):
        for lap in sorted(self.laps_data.keys()):
            data = self.laps_data[lap]
            t_str = f"{int(data.lap_time // 60000):02d}:{((data.lap_time % 60000) / 1000):06.3f}"
            marker = "★ " if lap == self.best_lap else ""
            item = QListWidgetItem(f"{marker}Vuelta {lap} ({t_str})")
            item.setData(Qt.ItemDataRole.UserRole, lap)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if lap == self.best_lap else Qt.CheckState.Unchecked)
            self.list_laps.addItem(item)
            
        if self.list_laps.count() > 0:
            items = self.list_laps.findItems("★", Qt.MatchFlag.MatchContains)
            if items:
                items[0].setSelected(True)
            else:
                self.list_laps.item(0).setSelected(True)
            
        self.refresh_plot()
        
    def toggle_playback(self):
        if self.playback_timer.isActive():
            self.playback_timer.stop()
            self.btn_play_pause.setText("▶ Reproducir Sesión")
        else:
            if not self.all_packets: return
            self.playback_timer.start(16)
            self.btn_play_pause.setText("⏸ Pausar")
            
    def playback_tick(self):
        if not self.all_packets: return
        self.current_packet_index += 1
        if self.current_packet_index >= len(self.all_packets):
            self.current_packet_index = 0
            self.toggle_playback()
            
        self.playback_slider.blockSignals(True)
        self.playback_slider.setValue(self.current_packet_index)
        self.playback_slider.blockSignals(False)
        self.update_playback_ui(self.current_packet_index)
        
    def on_slider_moved(self, value):
        self.current_packet_index = value
        self.update_playback_ui(self.current_packet_index)
        
    def update_playback_ui(self, index):
        if not self.all_packets or index >= len(self.all_packets): return
        packet = self.all_packets[index]
        
        if packet.position:
            self.map_widget.set_crosshair(packet.position[0], packet.position[2])
            
        self.telemetry_dashboard.update_data(packet)
        
        # Calculate time based on packet index assuming 60fps
        # Or even better, if we have active_lap_data and the packet belongs to it, we can get precise time
        cur_time_ms = index * (1000.0 / 60.0)
        
        if self.active_lap_data and len(self.active_lap_data.distance) > 0:
            lap = packet.lap_count
            if lap == self.active_lap_data.lap_number:
                for i, p in enumerate(self.active_lap_data.packets):
                    if p == packet or i == len(self.active_lap_data.packets)-1:
                        if i < len(self.active_lap_data.distance):
                            dist = self.active_lap_data.distance[i]
                            self.vline.setPos(dist)
                        if i < len(self.active_lap_data.time_ms):
                            cur_time_ms = self.active_lap_data.time_ms[i] * 1000.0
                        break
                        
        mins = int(cur_time_ms // 60000)
        secs = int((cur_time_ms % 60000) / 1000)
        mils = int(cur_time_ms % 1000)
        self.lbl_playback_time.setText(f"L{packet.lap_count} - {mins}:{secs:02d}.{mils:03d}")

    def keyPressEvent(self, event):
        if not self.all_packets:
            super().keyPressEvent(event)
            return
            
        if event.key() == Qt.Key.Key_Space:
            self.toggle_playback()
            event.accept()
        elif event.key() == Qt.Key.Key_Right:
            new_idx = min(self.current_packet_index + 60, len(self.all_packets) - 1)
            self.playback_slider.setValue(new_idx)
            event.accept()
        elif event.key() == Qt.Key.Key_Left:
            new_idx = max(self.current_packet_index - 60, 0)
            self.playback_slider.setValue(new_idx)
            event.accept()
        else:
            super().keyPressEvent(event)        
    def mouseMoved(self, evt):
        pos = evt[0]
        if self.p_speed.sceneBoundingRect().contains(pos):
            mousePoint = self.p_speed.plotItem.vb.mapSceneToView(pos)
            x_dist = mousePoint.x()
            
            self.vline.setPos(x_dist)
                
            if self.active_lap_data and len(self.active_lap_data.distance) > 0:
                idx = (np.abs(self.active_lap_data.distance - x_dist)).argmin()
                pos_x = self.active_lap_data.pos_x[idx]
                pos_z = self.active_lap_data.pos_z[idx]
                self.map_widget.set_crosshair(pos_x, pos_z)
        
    def on_lap_selected(self):
        items = self.list_laps.selectedItems()
        if not items:
            return
        item = items[0]
        lap = item.data(Qt.ItemDataRole.UserRole)
        
        data = self.laps_data.get(lap)
        if not data: return
        self.active_lap_data = data
        
        self.map_widget.clear()
        for p in data.packets:
            self.map_widget.add_point(p.position[0], p.position[2], p.throttle, p.brake)
        self.map_widget.update_plot()
        
    def refresh_plot(self, changed_item=None):
        self.p_speed.clear()
        self.p_speed.addItem(self.vline)
        
        checked_data = []
        
        color_idx = 0
        for i in range(self.list_laps.count()):
            item = self.list_laps.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                lap = item.data(Qt.ItemDataRole.UserRole)
                data = self.laps_data.get(lap)
                if data and len(data.distance) > 0:
                    color = self.colors[color_idx % len(self.colors)]
                    self.p_speed.plot(
                        data.distance, 
                        data.speed, 
                        pen=pg.mkPen(color, width=2), 
                        name=f"Vuelta {lap}"
                    )
                    checked_data.append((data, color))
                    color_idx += 1
                    
        self._update_tables(checked_data)

    def _update_tables(self, checked_data):
        import numpy as np
        
        self.table_summary.setColumnCount(1 + len(checked_data))
        headers = ["Métrica"] + [f"Vuelta {d.lap_number}" for d, _ in checked_data]
        self.table_summary.setHorizontalHeaderLabels(headers)
        
        self.table_summary.setItem(0, 0, QTableWidgetItem("Velocidad Máxima"))
        self.table_summary.setItem(1, 0, QTableWidgetItem("Velocidad Mínima en Curva"))
        self.table_summary.setItem(2, 0, QTableWidgetItem("Tiempo a fondo (>95%)"))
        self.table_summary.setItem(3, 0, QTableWidgetItem("Tiempo Frenando"))
        
        for row in range(4):
            item0 = self.table_summary.item(row, 0)
            if item0:
                item0.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        
        for col_idx, (data, color_str) in enumerate(checked_data):
            col = col_idx + 1
            if len(data.speed) == 0:
                continue
                
            max_speed = np.max(data.speed)
            min_speed = np.min(data.speed)
            total_pts = len(data.packets)
            ft_pct = (np.sum(data.throttle > 95) / total_pts) * 100 if total_pts > 0 else 0
            brk_pct = (np.sum(data.brake > 5) / total_pts) * 100 if total_pts > 0 else 0
            
            items = [
                QTableWidgetItem(f"{max_speed:.1f} km/h"),
                QTableWidgetItem(f"{min_speed:.1f} km/h"),
                QTableWidgetItem(f"{ft_pct:.1f}%"),
                QTableWidgetItem(f"{brk_pct:.1f}%")
            ]
            
            for row, it in enumerate(items):
                it.setFont(QFont("Arial", 13, QFont.Weight.Bold))
                it.setForeground(QColor(color_str))
                it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table_summary.setItem(row, col, it)
                
        if not checked_data:
            return

    def _detect_corners(self, data):
        corners = []
        in_corner = False
        corner_start_speed = 0.0
        corner_min_speed = 999.0
        corner_max_brake = 0
        
        for speed, brake, throttle in zip(data.speed, data.brake, data.throttle):
            if brake > 0 and speed > 50:
                if not in_corner:
                    in_corner = True
                    corner_start_speed = speed
                    corner_min_speed = speed
                    corner_max_brake = brake
                else:
                    if speed < corner_min_speed: corner_min_speed = speed
                    if brake > corner_max_brake: corner_max_brake = brake
            elif throttle > 0 and in_corner:
                if corner_start_speed - corner_min_speed > 10:
                    corners.append({
                        'entry_speed': corner_start_speed,
                        'apex_speed': corner_min_speed,
                        'max_brake': corner_max_brake
                    })
                in_corner = False
        return corners
