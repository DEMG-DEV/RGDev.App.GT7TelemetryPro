import os
from PyQt6.QtWidgets import (QMainWindow, QDockWidget, QWidget, QVBoxLayout, 
                             QHBoxLayout, QComboBox, QLabel, QPushButton, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QInputDialog, QTabWidget)
import sqlite3
from PyQt6.QtCore import Qt, QSettings, QThread, pyqtSignal
import pyqtgraph as pg
import numpy as np
import logging

from core.dynamic_math import DynamicMathEngine
from core.database import get_lap_data_vectorized
from core.utils import safe_slot
from ui.formula_manager import FormulaManagerWidget
from ui.theme import Theme
from services.motec_exporter import MotecExporter

class MotecExportThread(QThread):
    export_finished = pyqtSignal(int, str)
    export_error = pyqtSignal(str)

    def __init__(self, data, session_info, export_path):
        super().__init__()
        self.data = data
        self.session_info = session_info
        self.export_path = export_path

    def run(self):
        try:
            exporter = MotecExporter(self.data, self.session_info, self.export_path, zip_output=True)
            num_laps = exporter.export()
            self.export_finished.emit(num_laps, self.export_path)
        except Exception as e:
            import traceback
            logging.error(f"MoTeC Export failed: {traceback.format_exc()}")
            self.export_error.emit(str(e))

class DataLoaderThread(QThread):
    data_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, db_path: str, session_id: int, lap_numbers: list):
        super().__init__()
        self.db_path = db_path
        self.session_id = session_id
        self.lap_numbers = lap_numbers
        
    def run(self):
        try:
            data = get_lap_data_vectorized(self.db_path, self.session_id, self.lap_numbers)
            self.data_ready.emit(data)
        except Exception as e:
            self.error_occurred.emit(str(e))

class ProfessionalWorkspace(QMainWindow):
    def __init__(self, db_path=None, session_id=None, live_mode=False):
        super().__init__()
        self.db_path = db_path
        self.session_id = session_id
        self.live_mode = live_mode
        self.math_engine = DynamicMathEngine()
        self.vectorized_data = None # Para Post-Race
        
        self.setWindowTitle(f"Pro Analysis Workspace - {'LIVE' if live_mode else f'Session #{session_id}'}")
        from PyQt6.QtGui import QIcon
        import os
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'app_icon.png')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.resize(1600, 900)
        
        # Color config
        self.setStyleSheet("QMainWindow { background-color: #FAFAFA; } QDockWidget { font-weight: bold; }")
        
        # Configurar pyqtgraph para modo claro
        pg.setConfigOption('background', '#FFFFFF')
        pg.setConfigOption('foreground', '#1A1A1A')
        
        self.init_docks()
        
        if not self.live_mode and self.session_id is not None:
            self.load_post_race_data()
            
        self.restore_layout()

    def init_docks(self):
        self.setDockOptions(QMainWindow.DockOption.AllowNestedDocks | QMainWindow.DockOption.AllowTabbedDocks)
        
        # 1. Telemetry Trace (Central Widget instead of Dock)
        self.trace_container = QWidget()
        trace_layout = QVBoxLayout(self.trace_container)
        
        # Toolbar for adding traces
        trace_toolbar = QHBoxLayout()
        self.combo_add_trace = QComboBox()
        btn_add_trace = QPushButton("Add Trace")
        btn_add_trace.setStyleSheet(Theme.btn_style('#E0E0E0', '#1A1A1A', hover_bg='#D0D0D0', padding='6px 12px'))
        btn_add_trace.clicked.connect(self.add_custom_trace)

        btn_clear_traces = QPushButton("Clear Custom Traces")
        btn_clear_traces.setStyleSheet(Theme.btn_style('#FFCDD2', '#1A1A1A', border_color='#E57373', hover_bg='#EF9A9A', padding='6px 12px'))
        btn_clear_traces.clicked.connect(self.clear_custom_traces)

        btn_restore_panels = QPushButton("Restore Panels")
        btn_restore_panels.setStyleSheet(Theme.btn_style('#E0E0E0', '#1A1A1A', hover_bg='#D0D0D0', padding='6px 12px'))
        btn_restore_panels.clicked.connect(self.restore_default_layout)

        trace_toolbar.addWidget(QLabel("Channel:"))
        trace_toolbar.addWidget(self.combo_add_trace)
        trace_toolbar.addWidget(btn_add_trace)
        trace_toolbar.addWidget(btn_clear_traces)
        trace_toolbar.addWidget(btn_restore_panels)
        trace_toolbar.addStretch()
        trace_layout.addLayout(trace_toolbar)
        
        self.widget_trace = pg.GraphicsLayoutWidget()
        trace_layout.addWidget(self.widget_trace)
        
        from PyQt6.QtWidgets import QGraphicsProxyWidget
        from PyQt6.QtCore import Qt
        
        def add_default_close_btn(plot_item):
            close_btn = QPushButton("X")
            close_btn.setFixedSize(20, 20)
            close_btn.setStyleSheet(Theme.btn_style('#FFCDD2', '#1A1A1A', border_color='#E57373', padding='4px 8px'))
            proxy = QGraphicsProxyWidget()
            proxy.setWidget(close_btn)
            plot_item.layout.addItem(proxy, 0, 2, alignment=Qt.AlignmentFlag.AlignRight)
            close_btn.clicked.connect(lambda: self.widget_trace.removeItem(plot_item))
            
        self.plot_speed = self.widget_trace.addPlot(title="Speed (km/h)")
        add_default_close_btn(self.plot_speed)
        
        self.widget_trace.nextRow()
        self.plot_inputs = self.widget_trace.addPlot(title="Inputs (%)")
        self.plot_inputs.setXLink(self.plot_speed)
        add_default_close_btn(self.plot_inputs)
        
        self.widget_trace.nextRow()
        self.plot_math = self.widget_trace.addPlot(title="Math Channel")
        self.plot_math.setXLink(self.plot_speed)
        add_default_close_btn(self.plot_math)
        
        # Crosshair cursor for Interactive Trace
        self.cursor_line = pg.InfiniteLine(angle=90, movable=True, pen=pg.mkPen('y', width=2, style=Qt.PenStyle.DashLine))
        self.plot_speed.addItem(self.cursor_line)
        self.cursor_line.sigPositionChanged.connect(self.on_cursor_moved)
        
        # Dot for the Map
        self.map_cursor_dot = pg.ScatterPlotItem(size=12, pen=pg.mkPen('w', width=2), brush=pg.mkBrush('r'))
        
        self.setCentralWidget(self.trace_container)
        
        # 2. X-Y Scatter Plot Dock
        self.dock_scatter = QDockWidget("X-Y Scatter", self)
        self.dock_scatter.setObjectName("dock_scatter")
        scatter_container = QWidget()
        sl = QVBoxLayout(scatter_container)
        
        ctrl_h = QHBoxLayout()
        self.combo_x = QComboBox()
        self.combo_y = QComboBox()
        ctrl_h.addWidget(QLabel("X:"))
        ctrl_h.addWidget(self.combo_x)
        ctrl_h.addWidget(QLabel("Y:"))
        ctrl_h.addWidget(self.combo_y)
        sl.addLayout(ctrl_h)
        
        self.plot_scatter_widget = pg.PlotWidget()
        self.scatter_item = pg.ScatterPlotItem(size=5, pen=pg.mkPen(None), brush=pg.mkBrush(0, 0, 255, 120))
        self.plot_scatter_widget.addItem(self.scatter_item)
        sl.addWidget(self.plot_scatter_widget)
        
        self.dock_scatter.setWidget(scatter_container)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_scatter)
        
        # 3. Suspension Histogram Dock (4 wheels)
        self.dock_hist = QDockWidget("Suspension Velocity Histogram", self)
        self.dock_hist.setObjectName("dock_hist")
        self.widget_hist = pg.GraphicsLayoutWidget()
        self.plot_hist_fl = self.widget_hist.addPlot(title="FL")
        self.plot_hist_fr = self.widget_hist.addPlot(title="FR")
        self.widget_hist.nextRow()
        self.plot_hist_rl = self.widget_hist.addPlot(title="RL")
        self.plot_hist_rr = self.widget_hist.addPlot(title="RR")
        
        self.dock_hist.setWidget(self.widget_hist)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_hist)
        
        # 4. Dynamic Track Map
        self.dock_map = QDockWidget("Dynamic Track Map", self)
        self.dock_map.setObjectName("dock_map")
        self.plot_map = pg.PlotWidget()
        self.plot_map.setAspectLocked(True)
        self.map_scatter = pg.ScatterPlotItem(size=6, pen=pg.mkPen(None))
        self.plot_map.addItem(self.map_scatter)
        self.plot_map.addItem(self.map_cursor_dot)
        self.dock_map.setWidget(self.plot_map)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dock_map)
        # 5. G-Force Traction Circle
        self.dock_gforce = QDockWidget("G-Force Traction Circle", self)
        self.dock_gforce.setObjectName("dock_gforce")
        self.plot_gforce = pg.PlotWidget()
        self.plot_gforce.setAspectLocked(True)
        self.plot_gforce.showGrid(x=True, y=True, alpha=0.5)
        self.plot_gforce.setLabel('bottom', "Lateral G (Sway)")
        self.plot_gforce.setLabel('left', "Longitudinal G (Surge)")
        self.gforce_scatter = pg.ScatterPlotItem(size=5, pen=pg.mkPen(None), brush=pg.mkBrush(255, 0, 0, 150))
        self.plot_gforce.addItem(self.gforce_scatter)
        # Crosshair para G-Force (0,0)
        self.plot_gforce.addItem(pg.InfiniteLine(pos=0, angle=90, pen=pg.mkPen('w', width=1, style=Qt.PenStyle.DashLine)))
        self.plot_gforce.addItem(pg.InfiniteLine(pos=0, angle=0, pen=pg.mkPen('w', width=1, style=Qt.PenStyle.DashLine)))
        self.dock_gforce.setWidget(self.plot_gforce)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dock_gforce)
        
        # 6. Tyre Temperatures
        self.dock_tyre_temp = QDockWidget("Tyre Temperatures (°C)", self)
        self.dock_tyre_temp.setObjectName("dock_tyre_temp")
        self.widget_tyre_temp = pg.GraphicsLayoutWidget()
        self.plot_temp_fl = self.widget_tyre_temp.addPlot(title="FL Temp")
        self.plot_temp_fr = self.widget_tyre_temp.addPlot(title="FR Temp")
        self.widget_tyre_temp.nextRow()
        self.plot_temp_rl = self.widget_tyre_temp.addPlot(title="RL Temp")
        self.plot_temp_rr = self.widget_tyre_temp.addPlot(title="RR Temp")
        self.dock_tyre_temp.setWidget(self.widget_tyre_temp)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_tyre_temp)
        
        # 7. Tyre Slip Ratio
        self.dock_slip = QDockWidget("Tyre Slip Ratio (Wheel vs Chassis)", self)
        self.dock_slip.setObjectName("dock_slip")
        self.widget_slip = pg.GraphicsLayoutWidget()
        self.plot_slip_fl = self.widget_slip.addPlot(title="FL Slip")
        self.plot_slip_fr = self.widget_slip.addPlot(title="FR Slip")
        self.widget_slip.nextRow()
        self.plot_slip_rl = self.widget_slip.addPlot(title="RL Slip")
        self.plot_slip_rr = self.widget_slip.addPlot(title="RR Slip")
        
        self.plot_slip_fl.setXLink(self.plot_speed)
        self.plot_slip_fr.setXLink(self.plot_speed)
        self.plot_slip_rl.setXLink(self.plot_speed)
        self.plot_slip_rr.setXLink(self.plot_speed)
        self.dock_slip.setWidget(self.widget_slip)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_slip)
        
        # 8. Formula Manager Toolbar / Data Grid
        self.dock_data = QDockWidget("Gestor de Datos y Fórmulas", self)
        self.dock_data.setObjectName("dock_data")
        data_container = QWidget()
        data_container.setStyleSheet(f"background-color: {Theme.BG_PANEL};")
        dl = QVBoxLayout(data_container)
        dl.setContentsMargins(15, 15, 15, 15)
        dl.setSpacing(10)
        
        sess_h = QHBoxLayout()
        self.combo_sessions = QComboBox()

        self.combo_sessions.currentIndexChanged.connect(self.on_session_selected)
        
        self.load_session_list()
        
        btn_load_sess = QPushButton("Load Selected Laps")
        btn_load_sess.setStyleSheet(Theme.btn_style(Theme.ACCENT_GREEN, '#FFFFFF', border_color='#229954', hover_bg='#2ECC71', pressed_bg='#1E8449'))
        btn_load_sess.clicked.connect(self.on_load_session_clicked)
        
        lbl_sess = QLabel("Session:")
        lbl_sess.setStyleSheet(f'font-weight: bold; color: {Theme.TEXT_PRIMARY};')
        sess_h.addWidget(lbl_sess)
        sess_h.addWidget(self.combo_sessions, stretch=1)
        sess_h.addWidget(btn_load_sess)
        dl.addLayout(sess_h)
        
        # Tabla de Laps
        from PyQt6.QtWidgets import QHeaderView, QAbstractItemView
        self.table_data = QTableWidget()
        self.table_data.setColumnCount(2)
        self.table_data.setHorizontalHeaderLabels(["[ ]", "Lap N°"])
        self.table_data.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_data.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_data.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_data.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_data.verticalHeader().setVisible(False)
        self.table_data.setAlternatingRowColors(True)
        self.table_data.setStyleSheet(Theme.table_style())
        self.table_data.setMinimumHeight(150)
        dl.addWidget(self.table_data)
        
        btn_h = QHBoxLayout()
        btn_h.setSpacing(15)
        
        btn_math = QPushButton("Formula Manager")
        btn_math.setStyleSheet(Theme.btn_style(Theme.ACCENT_DARK, '#FFFFFF', border_color='#1A252F', hover_bg='#34495E', padding='8px 12px'))
        btn_math.clicked.connect(self.open_formula_manager)
        btn_h.addWidget(btn_math)
        
        self.btn_export = QPushButton("Export to MoTeC")
        self.btn_export.setStyleSheet(Theme.btn_style('#D35400', '#FFFFFF', border_color='#BA4A00', hover_bg='#E67E22', padding='8px 12px'))
        self.btn_export.clicked.connect(self.on_export_motec_clicked)
        btn_h.addWidget(self.btn_export)
        
        btn_h.addStretch(1)
        
        btn_save_layout = QPushButton("Save Layout")
        btn_save_layout.setStyleSheet(Theme.btn_style(Theme.ACCENT_BLUE, '#FFFFFF', border_color='#2471A3', hover_bg='#3498DB', padding='8px 12px'))
        btn_save_layout.clicked.connect(self.save_layout)
        btn_h.addWidget(btn_save_layout)
        
        dl.addLayout(btn_h)
        
        self.dock_data.setWidget(data_container)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dock_data)
        
        # --- 3 columnas verticales: Izq (tabificada) | Centro (gráficas) | Der (análisis) ---
        # Tabificar los 3 docks en la columna izquierda
        self.tabifyDockWidget(self.dock_map, self.dock_gforce)
        self.tabifyDockWidget(self.dock_gforce, self.dock_data)
        self.dock_map.raise_()  # Track Map como pestaña activa
        
        # Pestañas en la parte inferior del dock
        self.setTabPosition(Qt.DockWidgetArea.LeftDockWidgetArea, QTabWidget.TabPosition.South)
        
        # Forzar 3 columnas de mismo ancho (33% cada una)
        self.resizeDocks(
            [self.dock_map, self.dock_scatter],
            [400, 400],
            Qt.Orientation.Horizontal
        )

    def load_session_list(self):
        if not self.db_path or not os.path.exists(self.db_path):
            return
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, car_name, start_time FROM sessions ORDER BY id DESC")
                for row in cursor.fetchall():
                    self.combo_sessions.addItem(f"#{row[0]} - {row[1]} ({row[2]})", row[0])
        except Exception as e:
            logging.error(f"Error loading sessions: {e}", exc_info=True)
            
    def on_session_selected(self, index):
        if not hasattr(self, 'table_data'): return
        sid = self.combo_sessions.itemData(index)
        if not sid or not self.db_path or not os.path.exists(self.db_path):
            return
            
        self.table_data.setRowCount(0)
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT lap_count FROM telemetry WHERE session_id = ? ORDER BY lap_count", (sid,))
                laps = cursor.fetchall()
                
                from PyQt6.QtWidgets import QTableWidgetItem
                from PyQt6.QtCore import Qt
                
                lap_nums = [row_data[0] for row_data in laps]
                
                # Filter out-lap (first) and in-lap (last)
                if len(lap_nums) > 2:
                    lap_nums = lap_nums[1:-1]
                elif len(lap_nums) == 2:
                    lap_nums = lap_nums[1:]
                    
                for row_idx, lap_num in enumerate(lap_nums):
                    self.table_data.insertRow(row_idx)
                    
                    chk_item = QTableWidgetItem()
                    chk_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                    # Check the first lap by default
                    chk_item.setCheckState(Qt.CheckState.Checked if row_idx == 0 else Qt.CheckState.Unchecked)
                    
                    self.table_data.setItem(row_idx, 0, chk_item)
                    self.table_data.setItem(row_idx, 1, QTableWidgetItem(f"Lap {lap_num}"))
        except Exception as e:
            logging.error(f"Error loading laps for session {sid}: {e}", exc_info=True)
            
    @safe_slot
    def on_load_session_clicked(self, *args):
        sid = self.combo_sessions.currentData()
        if not sid: return
        
        # Recopilar vueltas seleccionadas
        from PyQt6.QtCore import Qt
        selected_laps = []
        for row in range(self.table_data.rowCount()):
            item = self.table_data.item(row, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                # Extraer número de vuelta ("Lap X")
                lap_str = self.table_data.item(row, 1).text().replace("Lap ", "")
                selected_laps.append(int(lap_str))
                
        if not selected_laps:
            # Si no seleccionaron nada, cargar la vuelta 1 por defecto para evitar errores
            selected_laps = [1]
            
        self.session_id = sid
        self.selected_laps = selected_laps
        self.setWindowTitle(f"Pro Analysis Workspace - Loading Session #{sid} (Laps: {selected_laps})...")
        self.load_post_race_data()

    def load_post_race_data(self):
        # Deshabilitamos la interacción para evitar colisiones
        self.dock_data.setEnabled(False)
        if not hasattr(self, 'selected_laps'):
            self.selected_laps = [1]
            
        self.setWindowTitle(f"Pro Analysis Workspace - Loading Session #{self.session_id} (Processing BLOBs...)")
        
        # Lanzamos el hilo secundario
        self.loader_thread = DataLoaderThread(self.db_path, self.session_id, self.selected_laps)
        self.loader_thread.data_ready.connect(self.on_data_loaded)
        self.loader_thread.error_occurred.connect(self.on_data_load_error)
        self.loader_thread.start()

    def on_data_loaded(self, data):
        self.vectorized_data = data
        
        # Detectar nombre de la pista por distancia
        track_name = "Pista Desconocida"
        try:
            import json
            import os
            tracks_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "tracks.json"))
            if os.path.exists(tracks_file) and len(data['speed']) > 0:
                lap_counts = np.array(data['lap_count'])
                unique_laps = np.unique(lap_counts)
                
                # Descartar la vuelta de salida y entrada para la heurística si hay suficientes
                valid_laps = unique_laps
                if len(unique_laps) > 2:
                    valid_laps = unique_laps[1:-1]
                    
                dists = []
                elevs = []
                corns = []
                
                for lap in valid_laps:
                    idx = lap_counts == lap
                    if np.sum(idx) < 60: continue # Ignorar vueltas absurdamente cortas (menos de 1 seg)
                    
                    lap_speed = data['speed'][idx]
                    lap_time = data['timestamp'][idx]
                    
                    # Distancia con integración dt real (súper precisa)
                    dt = np.diff(lap_time)
                    dt = np.clip(dt, 0.0, 0.5) # Prevenir saltos de tiempo masivos
                    lap_dist = np.sum((lap_speed[:-1] / 3.6) * dt)
                    dists.append(lap_dist)
                    
                    lap_pos_y = data['position_y'][idx]
                    if len(lap_pos_y) > 0:
                        elevs.append(np.max(lap_pos_y) - np.min(lap_pos_y))
                    else:
                        elevs.append(0)
                        
                    # Detección de curvas
                    lap_brake = data['brake'][idx]
                    lap_throttle = data['throttle'][idx]
                    
                    corners_count = 0
                    in_corner = False
                    corner_start_speed = 0.0
                    corner_min_speed = 999.0
                    
                    for s, b, th in zip(lap_speed, lap_brake, lap_throttle):
                        if b > 0 and s > 50:
                            if not in_corner:
                                in_corner = True
                                corner_start_speed = s
                                corner_min_speed = s
                            else:
                                if s < corner_min_speed: corner_min_speed = s
                        elif th > 0 and in_corner:
                            if corner_start_speed - corner_min_speed > 10:
                                corners_count += 1
                            in_corner = False
                    corns.append(corners_count)
                    
                if dists:
                    med_dist = np.median(dists)
                    elev_diff = np.median(elevs)
                    num_corners = np.median(corns)
                    
                    with open(tracks_file, 'r') as f:
                        tracks = json.load(f)
                    
                    best_match = None
                    highest_score = 0
                    
                    for t in tracks:
                        track_len = t.get('length_m', 0)
                        length_diff = abs(track_len - med_dist)
                        
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
                        track_name = best_match['name']
        except Exception as e:
            logging.error(f"Error detecting track: {e}")
            
        self.setWindowTitle(f"Pro Analysis Workspace - {track_name} (Session #{self.session_id})")
        self.dock_data.setEnabled(True)
        self.refresh_combos()
        self.update_plots()
        
    def on_data_load_error(self, err_msg):
        self.setWindowTitle(f"Pro Analysis Workspace - Error: {err_msg}")
        self.dock_data.setEnabled(True)
        logging.error(f"Error loading Post-Race Data: {err_msg}")

    @safe_slot
    def add_custom_trace(self, *args):
        channel = self.combo_add_trace.currentText()
        if not channel: return
        
        self.widget_trace.nextRow()
        new_plot = self.widget_trace.addPlot(title=channel)
        new_plot.setXLink(self.plot_speed)
        
        if not hasattr(self, 'custom_plots'):
            self.custom_plots = []
        self.custom_plots.append(new_plot)
        
        # Agregar botón de cierre individual (X)
        from PyQt6.QtWidgets import QGraphicsProxyWidget
        from PyQt6.QtCore import Qt
        close_btn = QPushButton("X")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet(Theme.btn_style('#FFCDD2', '#1A1A1A', border_color='#E57373', padding='4px 8px'))
        
        proxy = QGraphicsProxyWidget()
        proxy.setWidget(close_btn)
        # La grilla del PlotItem tiene el título en la fila 0, col 1. Colocamos el botón en col 2
        new_plot.layout.addItem(proxy, 0, 2, alignment=Qt.AlignmentFlag.AlignRight)
        
        def remove_this_plot():
            self.widget_trace.removeItem(new_plot)
            if new_plot in getattr(self, 'custom_plots', []):
                self.custom_plots.remove(new_plot)
                
        close_btn.clicked.connect(remove_this_plot)
        
        if self.vectorized_data:
            data = self.get_channel_data(channel)
            dist = np.cumsum(self.vectorized_data['speed'] / 3.6 * 0.016)
            new_plot.plot(dist, data, pen=pg.mkPen('y', width=2))

    @safe_slot
    def clear_custom_traces(self, *args):
        if hasattr(self, 'custom_plots'):
            for plot in self.custom_plots:
                self.widget_trace.removeItem(plot)
            self.custom_plots.clear()

    @safe_slot
    def open_formula_manager(self, *args):
        fm = FormulaManagerWidget(self.math_engine, self, test_context=self.vectorized_data)
        fm.exec()
        self.refresh_combos()
        if self.vectorized_data:
            self.update_plots()

    @safe_slot
    def on_export_motec_clicked(self, *args):
        if not self.vectorized_data or len(self.vectorized_data['speed']) == 0:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Export Error", "No data loaded to export.")
            return

        from PyQt6.QtWidgets import QFileDialog
        default_name = f"GT7_Session_{self.session_id}_MoTeC"
        filepath, _ = QFileDialog.getSaveFileName(self, "Save MoTeC Telemetry", default_name, "ZIP Files (*.zip);;All Files (*)")
        if not filepath:
            return

        self.btn_export.setEnabled(False)
        self.btn_export.setText("Exporting...")

        # Extracción de info de pista del título si es posible
        title = self.windowTitle()
        track_name = "Unknown Track"
        if " - " in title:
            track_name = title.split(" - ")[-1].split(" (")[0]

        session_info = {
            "Driver": "GT7 Telemetry Pro Driver",
            "Vehicle": "GT7 Car",
            "Venue": track_name,
            "Date": ""
        }

        self.motec_thread = MotecExportThread(self.vectorized_data, session_info, filepath)
        self.motec_thread.export_finished.connect(self.on_motec_export_finished)
        self.motec_thread.export_error.connect(self.on_motec_export_error)
        self.motec_thread.start()

    @safe_slot
    def on_motec_export_finished(self, laps, filepath):
        self.btn_export.setEnabled(True)
        self.btn_export.setText("Export to MoTeC")
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, "MoTeC Export", f"Telemetry successfully exported! {laps} laps written to {filepath}")

    @safe_slot
    def on_motec_export_error(self, err_msg):
        self.btn_export.setEnabled(True)
        self.btn_export.setText("Export to MoTeC")
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(self, "MoTeC Export Error", f"Failed to export telemetry:\n{err_msg}")

    def refresh_combos(self):
        if not self.vectorized_data:
            return
        keys = list(self.vectorized_data.keys()) + list(self.math_engine.channels.keys())
        
        # Guardar selección actual para restaurarla
        cx = self.combo_x.currentText()
        cy = self.combo_y.currentText()
        
        self.combo_x.clear()
        self.combo_y.clear()
        self.combo_add_trace.clear()
        
        self.combo_x.addItems(keys)
        self.combo_y.addItems(keys)
        self.combo_add_trace.addItems(keys)
        
        if cx in keys: self.combo_x.setCurrentText(cx)
        else: self.combo_x.setCurrentText("speed")
        
        if cy in keys: self.combo_y.setCurrentText(cy)
        else: self.combo_y.setCurrentText("throttle")
        
        self.combo_x.currentTextChanged.connect(self.update_scatter)
        self.combo_y.currentTextChanged.connect(self.update_scatter)

    def get_channel_data(self, name: str) -> np.ndarray:
        if name in self.vectorized_data:
            return self.vectorized_data[name]
        elif name in self.math_engine.channels:
            try:
                return self.math_engine.evaluate(name, self.vectorized_data)
            except Exception as e:
                logging.error(f"Math Error ({name}): {e}", exc_info=True)
                return np.zeros_like(self.vectorized_data['timestamp'])
        return np.zeros_like(self.vectorized_data['timestamp'])

    def update_plots(self):
        if not self.vectorized_data or len(self.vectorized_data['timestamp']) == 0:
            return
            
        lap_counts = np.array(self.vectorized_data['lap_count'])
        unique_laps = np.unique(lap_counts)
        
        # Limpiar gráficas
        self.plot_speed.clear()
        self.plot_speed.addItem(self.cursor_line)
        self.plot_inputs.clear()
        self.plot_math.clear()
        
        self.plot_slip_fl.clear()
        self.plot_slip_fr.clear()
        self.plot_slip_rl.clear()
        self.plot_slip_rr.clear()
        
        self.plot_temp_fl.clear()
        self.plot_temp_fr.clear()
        self.plot_temp_rl.clear()
        self.plot_temp_rr.clear()
        
        # Paleta de colores alto contraste estilo MoTeC
        colors = ['#00FFFF', '#FF00FF', '#FFFF00', '#00FF00', '#FF8000', '#FFFFFF', '#FF0000', '#0000FF']
        
        for i, lap_num in enumerate(unique_laps):
            # Obtener índices de esta vuelta
            idx = lap_counts == lap_num
            if not np.any(idx):
                continue
                
            lap_speed = self.vectorized_data['speed'][idx]
            lap_throttle = self.vectorized_data['throttle'][idx]
            lap_brake = self.vectorized_data['brake'][idx]
            lap_time = self.vectorized_data['timestamp'][idx]
            
            # Distance starts at 0 for each lap for perfect overlay (using exact dt)
            dt = np.diff(lap_time)
            dt = np.clip(dt, 0.0, 0.5)
            # Pad the first distance to 0 so array length matches
            lap_dist = np.zeros(len(lap_speed))
            lap_dist[1:] = np.cumsum((lap_speed[:-1] / 3.6) * dt)
            
            color = colors[i % len(colors)]
            pen = pg.mkPen(color, width=2)
            
            self.plot_speed.plot(lap_dist, lap_speed, pen=pen, name=f"Lap {lap_num}")
            
            # Inputs
            self.plot_inputs.plot(lap_dist, lap_throttle * 100, pen=pg.mkPen(color, width=1))
            self.plot_inputs.plot(lap_dist, -lap_brake * 100, pen=pg.mkPen(color, width=2, style=Qt.PenStyle.DashLine))
            
            # Math
            try:
                math_channel = self.combo_y.currentText()
                if math_channel and math_channel in self.math_engine.channels:
                    # Filter context just for this lap to avoid array size mismatches
                    lap_context = {k: v[idx] for k, v in self.vectorized_data.items() if isinstance(v, np.ndarray)}
                    math_data = self.math_engine.evaluate(math_channel, lap_context)
                    self.plot_math.plot(lap_dist, math_data, pen=pen)
            except Exception as e:
                logging.error(f"Math overlay error: {e}")
                
            # Slip Ratio
            wheel_rps_fl = self.vectorized_data.get('wheelRPS_FL')
            if wheel_rps_fl is not None:
                wheel_rps_fl = wheel_rps_fl[idx]
                tyre_rad_fl = self.vectorized_data['tyreRadius_FL'][idx]
                slip_fl = (wheel_rps_fl * tyre_rad_fl * 2 * np.pi) - (lap_speed / 3.6)
                self.plot_slip_fl.plot(lap_dist, slip_fl, pen=pen)
                
                wheel_rps_fr = self.vectorized_data['wheelRPS_FR'][idx]
                tyre_rad_fr = self.vectorized_data['tyreRadius_FR'][idx]
                slip_fr = (wheel_rps_fr * tyre_rad_fr * 2 * np.pi) - (lap_speed / 3.6)
                self.plot_slip_fr.plot(lap_dist, slip_fr, pen=pen)
                
                wheel_rps_rl = self.vectorized_data['wheelRPS_RL'][idx]
                tyre_rad_rl = self.vectorized_data['tyreRadius_RL'][idx]
                slip_rl = (wheel_rps_rl * tyre_rad_rl * 2 * np.pi) - (lap_speed / 3.6)
                self.plot_slip_rl.plot(lap_dist, slip_rl, pen=pen)
                
                wheel_rps_rr = self.vectorized_data['wheelRPS_RR'][idx]
                tyre_rad_rr = self.vectorized_data['tyreRadius_RR'][idx]
                slip_rr = (wheel_rps_rr * tyre_rad_rr * 2 * np.pi) - (lap_speed / 3.6)
                self.plot_slip_rr.plot(lap_dist, slip_rr, pen=pen)

        # 2. Scatter
        self.update_scatter()
        
        # 3. Histogram (Suspension Velocity)
        for plt, wheel in [(self.plot_hist_fl, 'FL'), (self.plot_hist_fr, 'FR'), 
                           (self.plot_hist_rl, 'RL'), (self.plot_hist_rr, 'RR')]:
            plt.clear()
            susp = self.vectorized_data[f'suspHeight_{wheel}']
            vel = np.gradient(susp)
            y, x = np.histogram(vel, bins=40, range=(-0.05, 0.05))
            bar = pg.BarGraphItem(x=x[:-1], height=y, width=(x[1]-x[0])*0.8, brush='c')
            plt.addItem(bar)

        # 4. Track Map (Mantenemos todos los puntos de todas las vueltas para ver la trayectoria)
        x_pos = self.vectorized_data['position_x']
        z_pos = self.vectorized_data['position_z']
        speed = self.vectorized_data['speed']
        
        # Filtrar outliers
        valid = (np.abs(x_pos) < 500000) & (np.abs(z_pos) < 500000) & ((x_pos != 0.0) | (z_pos != 0.0))
        x_pos_f = x_pos[valid]
        z_pos_f = z_pos[valid]
        speed_f = speed[valid]
        
        if len(x_pos_f) > 0:
            try:
                cmap = pg.colormap.get('turbo')
            except Exception:
                cmap = pg.colormap.get('inferno')
                
            norm_speed = np.clip(speed_f / 300.0, 0, 1)
            cmap_colors = cmap.map(norm_speed)
            brushes = [pg.mkBrush(tuple(c)) for c in cmap_colors]
            
            self.map_scatter.setData(x=x_pos_f, y=-z_pos_f, brush=brushes, size=4)
            self.plot_map.autoRange()
            
        # 5. G-Force Traction Circle
        sway = self.vectorized_data.get('sway')
        surge = self.vectorized_data.get('surge')
        if sway is not None and surge is not None:
            self.gforce_scatter.setData(x=sway, y=surge)
            
        # 6. Tyre Temperatures
        temp_fl = self.vectorized_data.get('tyreTemp_FL')
        if temp_fl is not None:
            ts = self.vectorized_data['timestamp']
            self.plot_temp_fl.plot(ts, temp_fl, pen='c')
            self.plot_temp_fr.plot(ts, self.vectorized_data['tyreTemp_FR'], pen='m')
            self.plot_temp_rl.plot(ts, self.vectorized_data['tyreTemp_RL'], pen='y')
            self.plot_temp_rr.plot(ts, self.vectorized_data['tyreTemp_RR'], pen='g')

    def on_cursor_moved(self):
        if not self.vectorized_data or not hasattr(self, 'dist_array'):
            return
            
        pos_x = self.cursor_line.value()
        # Find index in arrays closest to the cursor distance
        idx = (np.abs(self.dist_array - pos_x)).argmin()
        
        # Move the dot on the track map
        px = self.vectorized_data['position_x'][idx]
        pz = self.vectorized_data['position_z'][idx]
        
        if np.abs(px) < 500000 and np.abs(pz) < 500000:
            self.map_cursor_dot.setData([{'pos': (px, -pz)}])

    def update_scatter(self):
        if not self.vectorized_data:
            return
        cx = self.combo_x.currentText()
        cy = self.combo_y.currentText()
        if cx and cy:
            x_data = self.get_channel_data(cx)
            y_data = self.get_channel_data(cy)
            if len(x_data) > 0 and len(x_data) == len(y_data):
                self.scatter_item.setData(x=x_data, y=y_data)

    def save_layout(self):
        settings = QSettings("RGDev", "GT7TelemetryPro_Workspace")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        logging.info("Workspace layout saved to disk.")

    @safe_slot
    def restore_default_layout(self, *args):
        from PyQt6.QtCore import Qt
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_scatter)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_hist)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_tyre_temp)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_slip)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dock_map)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dock_gforce)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dock_data)
        
        # Tabificar los 3 docks izquierdos
        self.tabifyDockWidget(self.dock_map, self.dock_gforce)
        self.tabifyDockWidget(self.dock_gforce, self.dock_data)
        self.dock_map.raise_()
        
        # Igualar anchos de columnas
        self.resizeDocks(
            [self.dock_map, self.dock_scatter],
            [400, 400],
            Qt.Orientation.Horizontal
        )
        
        self.dock_scatter.setFloating(False)
        self.dock_hist.setFloating(False)
        self.dock_map.setFloating(False)
        self.dock_data.setFloating(False)
        self.dock_gforce.setFloating(False)
        self.dock_tyre_temp.setFloating(False)
        self.dock_slip.setFloating(False)
        
        self.dock_scatter.show()
        self.dock_hist.show()
        self.dock_map.show()
        self.dock_data.show()
        self.dock_gforce.show()
        self.dock_tyre_temp.show()
        self.dock_slip.show()

    def restore_layout(self):
        settings = QSettings("RGDev", "GT7TelemetryPro_Workspace")
        # IGNORAR GEOMETRÍA VIEJA PARA FORZAR QUE SE VEA EL NUEVO CENTRAL WIDGET
        # if settings.contains("geometry"):
        #     self.restoreGeometry(settings.value("geometry"))
        # if settings.contains("windowState"):
        #     self.restoreState(settings.value("windowState"))
        pass

    def closeEvent(self, event):
        self.save_layout()
        super().closeEvent(event)
