import sqlite3
import json
import os
import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QLabel,
                             QSplitter, QWidget, QListWidgetItem)
from PyQt6.QtCore import Qt
from ui.widgets.map_widget import MapWidget
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
    def __init__(self, db_path, session_id, parent=None):
        super().__init__(parent)
        self.db_path = db_path
        self.session_id = session_id
        
        self.track_name = "Pista Desconocida"
        self.laps_data = {}  
        self.best_lap = None
        self.active_lap_data = None
        
        self._load_data()
        
        self.setWindowTitle(f"Análisis Avanzado - {self.track_name} (Sesión #{session_id})")
        self.setGeometry(50, 50, 1600, 900)
        self.setStyleSheet("background-color: #0b0c10; color: #c5c6c7;")
        
        self.init_ui()
        
    def _load_data(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT raw_packet FROM telemetry WHERE session_id = ? ORDER BY id ASC", (self.session_id,))
                rows = cursor.fetchall()
                
                for row in rows:
                    blob = row[0]
                    packet = parse_telemetry_packet(blob, 'C')
                    if not packet:
                        continue
                    
                    lap = packet.lap_count
                    if lap not in self.laps_data:
                        self.laps_data[lap] = LapAnalysisData(lap)
                    self.laps_data[lap].packets.append(packet)
                    
            best_time = 999999999
            
            for lap, data in list(self.laps_data.items()):
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
                            
                    import logging
                    logging.info(f"Track Detection: dist={total_dist:.1f} elev={elev_diff:.1f} corners={num_corners}. Best Match: {best_match['name'] if best_match else 'None'} (score: {highest_score})")
                    
                    if best_match and highest_score > 0:
                        self.track_name = best_match['name']
                
        except Exception as e:
            import logging
            logging.error(f"Error loading telemetry for analysis: {e}")
            
    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        lbl_list_title = QLabel("Vueltas (Multiselección)")
        lbl_list_title.setStyleSheet("font-weight: bold; font-size: 16px; color: #66fcf1;")
        
        self.list_laps = QListWidget()
        self.list_laps.setStyleSheet("background-color: #1f2833; color: white; font-size: 14px; border: 1px solid #45a29e;")
        self.list_laps.itemSelectionChanged.connect(self.on_lap_selected)
        self.list_laps.itemChanged.connect(self.refresh_plot)
        
        self.colors = ['#00ffff', '#ff00ff', '#ffff00', '#00ff00', '#ff0000', '#ffffff', '#0000ff']
        
        for lap in sorted(self.laps_data.keys()):
            data = self.laps_data[lap]
            t_str = f"{int(data.lap_time // 60000):02d}:{((data.lap_time % 60000) / 1000):06.3f}"
            marker = "★ " if lap == self.best_lap else ""
            item = QListWidgetItem(f"{marker}Vuelta {lap} ({t_str})")
            item.setData(Qt.ItemDataRole.UserRole, lap)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if lap == self.best_lap else Qt.CheckState.Unchecked)
            self.list_laps.addItem(item)
            
        left_layout.addWidget(lbl_list_title)
        left_layout.addWidget(self.list_laps)
        
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
        self.p_speed.setBackground('#0b0c10')
        self.p_speed.setLabel('bottom', "Distancia de la vuelta (Metros)")
        
        self.vline = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('w', width=1, style=Qt.PenStyle.DashLine))
        self.p_speed.addItem(self.vline)
        
        self.table_summary = QTableWidget()
        self.table_summary.setColumnCount(2)
        self.table_summary.setRowCount(4)
        self.table_summary.horizontalHeader().setVisible(True)
        self.table_summary.verticalHeader().setVisible(False)
        self.table_summary.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_summary.setStyleSheet("QTableWidget { background-color: #1f2833; color: white; font-size: 14px; } QHeaderView::section { background-color: #0b0c10; color: #66fcf1; }")
        
        graphs_layout.addWidget(self.p_speed, stretch=2)
        
        lbl_res = QLabel("📋 Resumen de Vueltas (Overlay)")
        lbl_res.setStyleSheet("font-size: 16px; font-weight: bold; color: #66fcf1; padding-top: 10px;")
        graphs_layout.addWidget(lbl_res)
        graphs_layout.addWidget(self.table_summary, stretch=1)
        
        self.proxy = pg.SignalProxy(self.p_speed.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)
        
        self.table_corners = QTableWidget()
        self.table_corners.setColumnCount(4)
        self.table_corners.setHorizontalHeaderLabels(["Curva", "Vel. Entrada", "Vel. Ápice", "Freno Max"])
        header = self.table_corners.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_corners.setStyleSheet("QTableWidget { color: white; background-color: #1f2833; border: 1px solid #45a29e; } QHeaderView::section { background-color: #0b0c10; color: #66fcf1; font-weight: bold; }")
        
        right_sub_splitter = QSplitter(Qt.Orientation.Vertical)
        right_sub_splitter.addWidget(self.map_widget)
        right_sub_splitter.addWidget(self.table_corners)
        right_sub_splitter.setStretchFactor(0, 3)
        right_sub_splitter.setStretchFactor(1, 2)
        
        right_layout.addWidget(right_sub_splitter)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(graphs_widget)
        splitter.addWidget(right_panel)
        
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)
        splitter.setStretchFactor(2, 3)
        
        layout.addWidget(splitter)
        
        # Auto select best lap
        if self.list_laps.count() > 0:
            items = self.list_laps.findItems("★", Qt.MatchFlag.MatchContains)
            if items:
                items[0].setSelected(True)
            else:
                self.list_laps.item(0).setSelected(True)
            
            self.refresh_plot()
        
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
        
        # Only update the map. Tables are updated via refresh_plot (checked laps)
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
        
        # 1. Update Summary Table
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
                
        # 2. Update Corners Table
        if not checked_data:
            self.table_corners.setRowCount(0)
            return
            
        all_corners = [self._detect_corners(d) for d, _ in checked_data]
        max_corners = max([len(c) for c in all_corners]) if all_corners else 0
        
        self.table_corners.setColumnCount(1 + len(checked_data))
        headers_corners = ["Curva"] + [f"V. {d.lap_number} (In / Ápice / Freno)" for d, _ in checked_data]
        self.table_corners.setHorizontalHeaderLabels(headers_corners)
        self.table_corners.setRowCount(max_corners)
        
        for row in range(max_corners):
            c_item = QTableWidgetItem(f"Curva {row+1}")
            c_item.setFont(QFont("Arial", 11, QFont.Weight.Bold))
            self.table_corners.setItem(row, 0, c_item)
            
            for col_idx, (corners, (_, color_str)) in enumerate(zip(all_corners, checked_data)):
                col = col_idx + 1
                if row < len(corners):
                    c = corners[row]
                    txt = f"{c['entry_speed']:.0f} / {c['apex_speed']:.0f} / {c['max_brake']:.0f}%"
                    it = QTableWidgetItem(txt)
                    it.setForeground(QColor(color_str))
                    it.setFont(QFont("Arial", 11, QFont.Weight.Bold))
                else:
                    it = QTableWidgetItem("-")
                    it.setForeground(QColor(color_str))
                it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table_corners.setItem(row, col, it)

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
