import sqlite3
import json
import os
import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QLabel,
                             QSplitter, QWidget, QListWidgetItem, QPushButton,
                             QAbstractItemView, QSlider, QApplication, QProgressDialog,
                             QGroupBox)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor, QPixmap, QIcon

from ui.widgets.map_widget import MapWidget
from ui.widgets.live_telemetry_widget import LiveTelemetryWidget
from core.models import parse_telemetry_packet
from core.car_database import CarDatabase, resource_path
from ui.theme import Theme

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
        
        self.setWindowTitle("Análisis Avanzado de Sesión")
        icon_path = resource_path('app_icon.png')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.setGeometry(50, 50, 1600, 900)
        self.setStyleSheet(f"background-color: {Theme.BG_WINDOW}; color: {Theme.TEXT_PRIMARY};")
        
        self.init_ui()
        self._load_sessions()
        
        if self.session_id:
            self._load_data(self.session_id)
        
    def _load_sessions(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(sessions)")
                existing_cols = [c[1] for c in cursor.fetchall()]
                has_track_col = 'track_name' in existing_cols
                if not has_track_col:
                    try:
                        conn.execute("ALTER TABLE sessions ADD COLUMN track_name TEXT;")
                        conn.commit()
                        has_track_col = True
                    except Exception:
                        has_track_col = False
                    
                if has_track_col:
                    cursor.execute("SELECT id, start_time, car_id, car_name, track_name, total_laps, best_laptime, is_locked FROM sessions ORDER BY id DESC")
                    sessions = cursor.fetchall()
                else:
                    cursor.execute("SELECT id, start_time, car_id, car_name, total_laps, best_laptime, is_locked FROM sessions ORDER BY id DESC")
                    raw = cursor.fetchall()
                    sessions = [(r[0], r[1], r[2], r[3], None, r[4], r[5], r[6]) for r in raw]
                
            self.table_sessions.setRowCount(0)
            for row_idx, row_data in enumerate(sessions):
                self.table_sessions.insertRow(row_idx)
                
                # Column 0: ID and Lock status
                is_locked = row_data[7]
                lock_str = " 🔒" if is_locked else ""
                id_item = QTableWidgetItem(f"#{row_data[0]}{lock_str}")
                id_item.setData(Qt.ItemDataRole.UserRole, row_data[0])
                id_item.setData(Qt.ItemDataRole.UserRole + 1, is_locked)
                id_item.setData(Qt.ItemDataRole.UserRole + 2, row_data[2])  # car_id
                id_item.setData(Qt.ItemDataRole.UserRole + 3, row_data[3])  # car_name
                id_item.setFont(QFont(Theme.FONT_SANS, 10, QFont.Weight.Bold))
                id_item.setForeground(QColor('#0000FF') if not is_locked else QColor('#CC0000'))
                self.table_sessions.setItem(row_idx, 0, id_item)
                
                # Column 1: Fecha corta (YYYY-MM-DD)
                dt_str = row_data[1][:10] if row_data[1] else "---"
                self.table_sessions.setItem(row_idx, 1, QTableWidgetItem(dt_str))
                
                # Column 2: Auto
                self.table_sessions.setItem(row_idx, 2, QTableWidgetItem(str(row_data[3])))
                
                # Column 3: Pista (Cargada desde la base de datos o fallback)
                track_str = row_data[4] if row_data[4] else f"Pista #{row_data[0]}"
                track_item = QTableWidgetItem(track_str)
                self.table_sessions.setItem(row_idx, 3, track_item)
                
                # Column 4: Vueltas
                laps_item = QTableWidgetItem(str(row_data[5]))
                laps_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table_sessions.setItem(row_idx, 4, laps_item)
                
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

    def _update_car_thumbnail(self, car_id, car_name):
        """Actualiza la imagen fotográfica del vehículo seleccionado."""
        car_db = CarDatabase()
        thumb_path = car_db.get_car_thumbnail(car_id) if car_id else ""
        
        if not thumb_path or not os.path.exists(thumb_path):
            for code, info in car_db.car_db.items():
                if info.get('full_name') == car_name or info.get('name') == car_name:
                    rel = info.get('thumbnail', '')
                    if rel:
                        tp = resource_path(os.path.join('data', rel))
                        if os.path.exists(tp):
                            thumb_path = tp
                            break
                            
        if thumb_path and os.path.exists(thumb_path):
            pixmap = QPixmap(thumb_path).scaled(220, 110, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.lbl_car_image.setPixmap(pixmap)
            self.lbl_car_name.setText(car_name)
        else:
            self.lbl_car_image.clear()
            self.lbl_car_name.setText(f"🏎️ {car_name}")

    def on_session_selected(self):
        items = self.table_sessions.selectedItems()
        if not items:
            self._update_action_buttons()
            return
            
        row = items[0].row()
        id_item = self.table_sessions.item(row, 0)
        session_id = id_item.data(Qt.ItemDataRole.UserRole)
        car_id = id_item.data(Qt.ItemDataRole.UserRole + 2)
        car_name = id_item.data(Qt.ItemDataRole.UserRole + 3)
        
        self._update_car_thumbnail(car_id, car_name)
        
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
            if hasattr(self, 'btn_edit_track'):
                self.btn_edit_track.setEnabled(False)
            self.btn_lock.setText("🔒 Bloquear")
            return
            
        row = items[0].row()
        id_item = self.table_sessions.item(row, 0)
        is_locked = id_item.data(Qt.ItemDataRole.UserRole + 1)
        
        if hasattr(self, 'btn_edit_track'):
            self.btn_edit_track.setEnabled(True)
            
        self.btn_lock.setEnabled(True)
        if is_locked:
            self.btn_delete.setEnabled(False)
            self.btn_lock.setText("🔓 Desbloquear")
            self.btn_lock.setStyleSheet(Theme.btn_style(bg="#f44336", text="#FFFFFF", border_color="#d32f2f", padding="8px"))
        else:
            self.btn_delete.setEnabled(True)
            self.btn_lock.setText("🔒 Bloquear")
            self.btn_lock.setStyleSheet(Theme.btn_style(bg="#f6a623", text="#000000", border_color="#d48b1c", padding="8px"))

    def assign_track_manually(self):
        items = self.table_sessions.selectedItems()
        if not items:
            return
        row = items[0].row()
        id_item = self.table_sessions.item(row, 0)
        session_id = id_item.data(Qt.ItemDataRole.UserRole)
        
        track_names = []
        tracks_file = resource_path(os.path.join('data', 'tracks.json'))
        if os.path.exists(tracks_file):
            try:
                with open(tracks_file, 'r', encoding='utf-8') as f:
                    tracks = json.load(f)
                    track_names = sorted(list(set(t.get('name') for t in tracks if t.get('name'))))
            except Exception:
                pass
                
        if not track_names:
            track_names = ["Autodromo Nazionale Monza", "Fuji International Speedway", "Nürburgring GP", "Suzuka Circuit", "Spa-Francorchamps", "Daytona Tri-Oval"]
            
        track_names.insert(0, "✏️ Nombre personalizado...")
        
        from PyQt6.QtWidgets import QInputDialog, QMessageBox
        current_track_item = self.table_sessions.item(row, 3)
        current_track = current_track_item.text() if current_track_item else ""
        
        choice, ok = QInputDialog.getItem(
            self, "Asignar Pista Manualmente", 
            f"Selecciona el circuito para la Sesión #{session_id}:", 
            track_names, 0, False
        )
        
        if ok and choice:
            if choice == "✏️ Nombre personalizado...":
                custom_name, ok_custom = QInputDialog.getText(
                    self, "Nombre Personalizado de Pista",
                    f"Escribe el nombre del circuito para la Sesión #{session_id}:",
                    text=current_track if not current_track.startswith("Pista #") else ""
                )
                if ok_custom and custom_name.strip():
                    new_track = custom_name.strip()
                else:
                    return
            else:
                new_track = choice
                
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("UPDATE sessions SET track_name = ? WHERE id = ?", (new_track, session_id))
                    conn.commit()
                    
                self.track_name = new_track
                self.table_sessions.setItem(row, 3, QTableWidgetItem(new_track))
                self.setWindowTitle(f"Análisis Avanzado de Sesión - {new_track} (#{session_id})")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Fallo al guardar pista en la base de datos: {e}")
            
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
                
                with sqlite3.connect(self.db_path) as conn:
                    conn.isolation_level = None 
                    conn.execute("VACUUM")
                
                self.session_id = None
                self._load_sessions()
                self.laps_data.clear()
                self.list_laps.clear()
                self.p_speed.clear()
                self.p_rpm.clear()
                self.p_pedals.clear()
                self.p_delta.clear()
                self.map_widget.clear()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Fallo al eliminar sesión: {e}")
        
    def _load_data(self, session_id):
        self.setWindowTitle(f"Análisis Avanzado de Sesión - Cargando #{session_id}...")
        self.laps_data.clear()
        self.list_laps.clear()
        self.p_speed.clear()
        self.p_rpm.clear()
        self.p_pedals.clear()
        self.p_delta.clear()
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
        progress.setStyleSheet(f"QProgressDialog {{ background-color: {Theme.BG_WINDOW}; color: {Theme.TEXT_PRIMARY}; }} QLabel {{ color: {Theme.TEXT_PRIMARY}; }}")
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
                
                tracks_file = resource_path(os.path.join('data', 'tracks.json'))
                if os.path.exists(tracks_file):
                    with open(tracks_file, 'r') as f:
                        tracks = json.load(f)
                    
                    best_match = None
                    highest_score = 0
                    
                    for t in tracks:
                        track_len = t.get('length_m', 0)
                        length_diff = abs(track_len - total_dist)
                        dynamic_margin = max(50.0, track_len * 0.015)
                        
                        if length_diff > dynamic_margin:
                            continue
                        
                        score = 1000 - length_diff
                        score -= abs(t.get('elevation_diff_m', 0) - elev_diff) * 10.0
                        score -= abs(t.get('num_corners', 0) - num_corners) * 5.0
                        
                        if score > highest_score:
                            highest_score = score
                            best_match = t
                            
                    if best_match and highest_score > 0:
                        self.track_name = best_match['name']
                        
                        # Persistir el nombre de pista detectado en la base de datos SQLite
                        try:
                            with sqlite3.connect(self.db_path) as conn:
                                conn.execute("UPDATE sessions SET track_name = ? WHERE id = ?", (self.track_name, session_id))
                                conn.commit()
                        except Exception as e:
                            import logging
                            logging.error(f"Error actualizando track_name en BD: {e}")
                        
                        # Actualizar la columna 'Pista' en la tabla UI para la sesión activa
                        for i in range(self.table_sessions.rowCount()):
                            item = self.table_sessions.item(i, 0)
                            if item and item.data(Qt.ItemDataRole.UserRole) == session_id:
                                self.table_sessions.setItem(i, 3, QTableWidgetItem(self.track_name))
                                break
            
            self.setWindowTitle(f"Análisis Avanzado de Sesión - {self.track_name} (#{session_id})")
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
            self.setWindowTitle(f"Análisis Avanzado de Sesión - Error (#{session_id})")

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # ── PANEL IZQUIERDO (Sesiones, Auto, Vueltas) ──────────────────────
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        lbl_sessions_title = QLabel("Historial de Sesiones")
        lbl_sessions_title.setStyleSheet(f"font-weight: bold; font-size: 15px; color: {Theme.TEXT_PRIMARY};")
        
        # Tabla de Sesiones (Columnas minimizadas: ID, Fecha, Auto, Pista, Vueltas)
        self.table_sessions = QTableWidget()
        self.table_sessions.setColumnCount(5)
        self.table_sessions.setHorizontalHeaderLabels(["ID", "Fecha", "Auto", "Pista", "Vueltas"])
        
        header = self.table_sessions.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        self.table_sessions.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_sessions.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table_sessions.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_sessions.setStyleSheet(Theme.table_style())
        self.table_sessions.itemSelectionChanged.connect(self.on_session_selected)
        
        # Panel Visual de Fotografía del Auto
        car_box = QGroupBox("Vehículo Seleccionado")
        car_box.setStyleSheet(f"QGroupBox {{ font-weight: bold; color: {Theme.TEXT_PRIMARY}; border: 1px solid {Theme.BORDER}; border-radius: 6px; margin-top: 6px; padding-top: 6px; }}")
        car_box_layout = QVBoxLayout(car_box)
        car_box_layout.setContentsMargins(5, 5, 5, 5)
        
        self.lbl_car_image = QLabel()
        self.lbl_car_image.setFixedHeight(90)
        self.lbl_car_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_car_name = QLabel("Sin Selección")
        self.lbl_car_name.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {Theme.TEXT_PRIMARY};")
        self.lbl_car_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        car_box_layout.addWidget(self.lbl_car_image)
        car_box_layout.addWidget(self.lbl_car_name)
        
        btn_action_layout = QHBoxLayout()
        self.btn_edit_track = QPushButton("📍 Pista")
        self.btn_edit_track.setStyleSheet(Theme.btn_style(bg=Theme.BG_PANEL, text=Theme.TEXT_PRIMARY, padding="8px"))
        self.btn_edit_track.setEnabled(False)
        self.btn_edit_track.clicked.connect(self.assign_track_manually)
        
        self.btn_lock = QPushButton("🔒 Bloquear")
        self.btn_lock.setStyleSheet(Theme.btn_style(bg="#f6a623", text="#000000", border_color="#d48b1c", padding="8px"))
        self.btn_lock.setEnabled(False)
        self.btn_lock.clicked.connect(self.toggle_lock_session)
        
        self.btn_delete = QPushButton("🗑️ Eliminar")
        self.btn_delete.setStyleSheet(Theme.btn_style(bg=Theme.BG_PANEL, text=Theme.TEXT_PRIMARY, padding="8px"))
        self.btn_delete.setEnabled(False)
        self.btn_delete.clicked.connect(self.delete_session)
        
        btn_action_layout.addWidget(self.btn_edit_track)
        btn_action_layout.addWidget(self.btn_lock)
        btn_action_layout.addWidget(self.btn_delete)
        
        playback_layout = QVBoxLayout()
        self.btn_play_pause = QPushButton("▶ Reproducir Sesión")
        self.btn_play_pause.setStyleSheet(Theme.btn_style(bg=Theme.BG_PANEL, text=Theme.TEXT_PRIMARY, padding="10px"))
        self.btn_play_pause.setEnabled(False)
        self.btn_play_pause.clicked.connect(self.toggle_playback)
        
        slider_layout = QHBoxLayout()
        self.lbl_playback_time = QLabel("00:00.000")
        self.lbl_playback_time.setStyleSheet(f"color: {Theme.TEXT_PRIMARY}; font-weight: bold; font-family: {Theme.FONT_MONO};")
        
        self.playback_slider = QSlider(Qt.Orientation.Horizontal)
        self.playback_slider.setEnabled(False)
        self.playback_slider.valueChanged.connect(self.on_slider_moved)
        self.playback_slider.setStyleSheet(f"QSlider::handle:horizontal {{ background-color: {Theme.TEXT_PRIMARY}; width: 12px; margin: -4px 0; border-radius: 6px; }} QSlider::groove:horizontal {{ background: {Theme.BORDER}; height: 4px; }}")
        
        self.lbl_playback_best = QLabel("Best: --:--.---")
        self.lbl_playback_best.setStyleSheet(f"color: {Theme.ACCENT_ORANGE}; font-weight: bold; font-family: {Theme.FONT_MONO};")
        
        slider_layout.addWidget(self.lbl_playback_time)
        slider_layout.addWidget(self.playback_slider)
        slider_layout.addWidget(self.lbl_playback_best)
        
        playback_layout.addWidget(self.btn_play_pause)
        playback_layout.addLayout(slider_layout)
        
        lbl_list_title = QLabel("Vueltas (Multiselección)")
        lbl_list_title.setStyleSheet(f"font-weight: bold; font-size: 15px; color: {Theme.TEXT_PRIMARY}; padding-top: 5px;")
        
        self.list_laps = QListWidget()
        self.list_laps.setStyleSheet(f"background-color: {Theme.BG_CARD}; color: {Theme.TEXT_PRIMARY}; font-size: 13px; border: 1px solid {Theme.BORDER}; border-radius: 4px;")
        self.list_laps.itemSelectionChanged.connect(self.on_lap_selected)
        self.list_laps.itemChanged.connect(self.refresh_plot)
        
        self.colors = ['#0000FF', '#FF00FF', '#008000', '#FF0000', '#800080', '#000000', '#FF8C00']
        
        sessions_container = QWidget()
        s_layout = QVBoxLayout(sessions_container)
        s_layout.setContentsMargins(0, 0, 0, 5)
        s_layout.addWidget(lbl_sessions_title)
        s_layout.addWidget(self.table_sessions)
        s_layout.addWidget(car_box)
        s_layout.addLayout(btn_action_layout)
        s_layout.addLayout(playback_layout)
        
        self.table_summary = QTableWidget()
        self.table_summary.setColumnCount(1)
        self.table_summary.setRowCount(4)
        self.table_summary.horizontalHeader().setVisible(True)
        self.table_summary.verticalHeader().setVisible(False)
        self.table_summary.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_summary.setStyleSheet(Theme.table_style())
        self.table_summary.setFixedHeight(125)
        
        lbl_res = QLabel("📋 Resumen de Vueltas (Overlay)")
        lbl_res.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {Theme.TEXT_PRIMARY}; padding-top: 6px;")
        
        laps_container = QWidget()
        l_layout = QVBoxLayout(laps_container)
        l_layout.setContentsMargins(0, 0, 0, 0)
        l_layout.addWidget(lbl_list_title)
        l_layout.addWidget(self.list_laps, stretch=1)
        l_layout.addWidget(lbl_res)
        l_layout.addWidget(self.table_summary)
        
        left_layout.addWidget(sessions_container, stretch=5)
        left_layout.addWidget(laps_container, stretch=5)
        
        # ── PANEL CENTRO (4 Gráficas Apiladas MoTeC: Velocidad, RPM, Pedales, Delta-T) ──
        graphs_widget = QWidget()
        graphs_layout = QVBoxLayout(graphs_widget)
        graphs_layout.setContentsMargins(0, 0, 0, 0)
        graphs_layout.setSpacing(4)
        
        # Plot 1: Velocidad (km/h)
        self.p_speed = pg.PlotWidget(title="Velocidad (km/h)")
        
        # Plot 2: RPM
        self.p_rpm = pg.PlotWidget(title="R.P.M.")
        
        # Plot 3: Acelerador / Freno (%)
        self.p_pedals = pg.PlotWidget(title="Acelerador / Freno (%)")
        
        # Plot 4: Delta vs Mejor Vuelta (s)
        self.p_delta = pg.PlotWidget(title="Delta vs Mejor Vuelta (s)")
        
        self.plots = [self.p_speed, self.p_rpm, self.p_pedals, self.p_delta]
        
        for p in self.plots:
            p.addLegend()
            p.showGrid(x=True, y=True, alpha=0.3)
            p.setBackground('#FAFAFA')
            
        self.p_delta.setLabel('bottom', "Distancia de la vuelta (Metros)")
        
        # Enlazar ejes X entre las 4 gráficas
        self.p_rpm.setXLink(self.p_speed)
        self.p_pedals.setXLink(self.p_speed)
        self.p_delta.setXLink(self.p_speed)
        
        # Línea vertical sincronizada en todas las gráficas
        self.vlines = []
        for p in self.plots:
            vl = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('w', width=1, style=Qt.PenStyle.DashLine))
            p.addItem(vl)
            self.vlines.append(vl)
            
        for p in self.plots:
            graphs_layout.addWidget(p, stretch=1)
            
        self.proxy = pg.SignalProxy(self.p_speed.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)
        
        # ── PANEL DERECHO (Mapa Interactivo + Telemetry Dashboard Completo) ──
        self.map_widget = MapWidget("Mapa Interactivo")
        self.telemetry_dashboard = LiveTelemetryWidget()
        
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self.map_widget, stretch=4)
        right_layout.addWidget(self.telemetry_dashboard, stretch=6)
        
        layout.addWidget(left_panel, stretch=25)
        layout.addWidget(graphs_widget, stretch=48)
        layout.addWidget(right_panel, stretch=27)
        
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
        
        cur_time_ms = index * (1000.0 / 60.0)
        
        if self.active_lap_data and len(self.active_lap_data.distance) > 0:
            lap = packet.lap_count
            if lap == self.active_lap_data.lap_number:
                for i, p in enumerate(self.active_lap_data.packets):
                    if p == packet or i == len(self.active_lap_data.packets)-1:
                        if i < len(self.active_lap_data.distance):
                            dist = self.active_lap_data.distance[i]
                            for vl in self.vlines:
                                vl.setPos(dist)
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
        for p in self.plots:
            if p.sceneBoundingRect().contains(pos):
                mousePoint = p.plotItem.vb.mapSceneToView(pos)
                x_dist = mousePoint.x()
                
                for vl in self.vlines:
                    vl.setPos(x_dist)
                    
                if self.active_lap_data and len(self.active_lap_data.distance) > 0:
                    idx = (np.abs(self.active_lap_data.distance - x_dist)).argmin()
                    pos_x = self.active_lap_data.pos_x[idx]
                    pos_z = self.active_lap_data.pos_z[idx]
                    self.map_widget.set_crosshair(pos_x, pos_z)
                break
        
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
        for p in self.plots:
            p.clear()
            
        for i, p in enumerate(self.plots):
            p.addItem(self.vlines[i])
            
        checked_data = []
        
        best_data = self.laps_data.get(self.best_lap) if self.best_lap in self.laps_data else None
        
        color_idx = 0
        for i in range(self.list_laps.count()):
            item = self.list_laps.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                lap = item.data(Qt.ItemDataRole.UserRole)
                data = self.laps_data.get(lap)
                if data and len(data.distance) > 0:
                    color = self.colors[color_idx % len(self.colors)]
                    
                    # 1. Velocidad
                    self.p_speed.plot(data.distance, data.speed, pen=pg.mkPen(color, width=2), name=f"Vuelta {lap}")
                    
                    # 2. RPM
                    self.p_rpm.plot(data.distance, data.rpm, pen=pg.mkPen(color, width=2), name=f"Vuelta {lap}")
                    
                    # 3. Pedales (Acelerador sólido, Freno punteado)
                    self.p_pedals.plot(data.distance, data.throttle, pen=pg.mkPen(color, width=2), name=f"Acel V{lap}")
                    self.p_pedals.plot(data.distance, data.brake, pen=pg.mkPen(color, width=1.5, style=Qt.PenStyle.DashLine), name=f"Freno V{lap}")
                    
                    # 4. Delta vs Best Lap
                    if best_data and len(best_data.distance) > 0:
                        interp_best_time = np.interp(data.distance, best_data.distance, best_data.time_ms)
                        delta_sec = data.time_ms - interp_best_time
                        self.p_delta.plot(data.distance, delta_sec, pen=pg.mkPen(color, width=2), name=f"Delta V{lap}")
                        
                    checked_data.append((data, color))
                    color_idx += 1
                    
        self._update_tables(checked_data)

    def _update_tables(self, checked_data):
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
                item0.setFont(QFont(Theme.FONT_SANS, 11, QFont.Weight.Bold))
        
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
                it.setFont(QFont(Theme.FONT_SANS, 12, QFont.Weight.Bold))
                it.setForeground(QColor(color_str))
                it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table_summary.setItem(row, col, it)

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
