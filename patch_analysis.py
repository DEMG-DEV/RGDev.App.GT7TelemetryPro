import sys

with open('ui/widgets/advanced_analysis_dialog.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. LapAnalysisData init
code = code.replace(
    'self.pos_x = []\n        self.pos_z = []',
    'self.pos_x = []\n        self.pos_y = []\n        self.pos_z = []'
)

# 2. Append pos_y (initial)
code = code.replace(
    'data.pos_x.append(data.packets[0].position[0])\n                data.pos_z.append(data.packets[0].position[2])',
    'data.pos_x.append(data.packets[0].position[0])\n                data.pos_y.append(data.packets[0].position[1])\n                data.pos_z.append(data.packets[0].position[2])'
)

# 3. Append pos_y (loop)
code = code.replace(
    'data.pos_x.append(p.position[0])\n                    data.pos_z.append(p.position[2])',
    'data.pos_x.append(p.position[0])\n                    data.pos_y.append(p.position[1])\n                    data.pos_z.append(p.position[2])'
)

# 4. np.array pos_y
code = code.replace(
    'data.pos_x = np.array(data.pos_x)\n                data.pos_z = np.array(data.pos_z)',
    'data.pos_x = np.array(data.pos_x)\n                data.pos_y = np.array(data.pos_y)\n                data.pos_z = np.array(data.pos_z)'
)

# 5. Extract _detect_corners
detect_corners_func = """    def _detect_corners(self, data):
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

    def _update_corners_table(self, data):
        corners = self._detect_corners(data)
"""
code = code.replace(
    "    def _update_corners_table(self, data):\n        corners = []\n        in_corner = False\n        corner_start_speed = 0.0\n        corner_min_speed = 999.0\n        corner_max_brake = 0\n        \n        for speed, brake, throttle in zip(data.speed, data.brake, data.throttle):\n            if brake > 0 and speed > 50:\n                if not in_corner:\n                    in_corner = True\n                    corner_start_speed = speed\n                    corner_min_speed = speed\n                    corner_max_brake = brake\n                else:\n                    if speed < corner_min_speed: corner_min_speed = speed\n                    if brake > corner_max_brake: corner_max_brake = brake\n            elif throttle > 0 and in_corner:\n                if corner_start_speed - corner_min_speed > 10:\n                    corners.append({\n                        'entry_speed': corner_start_speed,\n                        'apex_speed': corner_min_speed,\n                        'max_brake': corner_max_brake\n                    })\n                in_corner = False",
    detect_corners_func.strip('\n')
)

# 6. Re-write track scoring
track_detection_old = """            # Track detection
            if self.best_lap and self.best_lap in self.laps_data:
                total_dist = self.laps_data[self.best_lap].distance[-1]
                
                tracks_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "tracks.json"))
                if os.path.exists(tracks_file):
                    with open(tracks_file, 'r') as f:
                        tracks = json.load(f)
                    
                    closest = None
                    min_diff = 999999
                    for t in tracks:
                        diff = abs(t['length_m'] - total_dist)
                        if diff < min_diff:
                            min_diff = diff
                            closest = t
                            
                    import logging
                    logging.info(f"Track Detection: Lap distance {total_dist:.1f}m. Closest track: {closest['name'] if closest else 'None'} (diff: {min_diff:.1f}m)")
                    
                    if closest and min_diff < 500:
                        self.track_name = closest['name']
                    elif closest and min_diff < 1500:
                        self.track_name = f"Probable: {closest['name']}?"
"""
track_detection_new = """            # Track detection
            if self.best_lap and self.best_lap in self.laps_data:
                best_data = self.laps_data[self.best_lap]
                total_dist = best_data.distance[-1]
                elev_diff = np.max(best_data.pos_y) - np.min(best_data.pos_y)
                num_corners = len(self._detect_corners(best_data))
                
                tracks_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "tracks.json"))
                if os.path.exists(tracks_file):
                    with open(tracks_file, 'r') as f:
                        tracks = json.load(f)
                    
                    best_match = None
                    highest_score = 0
                    
                    for t in tracks:
                        score = 0
                        # Distancia
                        diff_dist = abs(t['length_m'] - total_dist)
                        if diff_dist < 200: score += 50
                        elif diff_dist < 500: score += 20
                        
                        # Elevación
                        diff_elev = abs(t['elevation_diff_m'] - elev_diff)
                        if diff_elev < 15: score += 20
                        elif diff_elev < 30: score += 10
                        
                        # Curvas
                        diff_corners = abs(t['num_corners'] - num_corners)
                        if diff_corners <= 2: score += 20
                        elif diff_corners <= 4: score += 10
                        
                        if score > highest_score:
                            highest_score = score
                            best_match = t
                            
                    import logging
                    logging.info(f"Track Detection: dist={total_dist:.1f} elev={elev_diff:.1f} corners={num_corners}. Best Match: {best_match['name'] if best_match else 'None'} (score: {highest_score})")
                    
                    if best_match and highest_score >= 40:
                        self.track_name = best_match['name']
                    elif best_match and highest_score > 0:
                        self.track_name = f"Probable: {best_match['name']}?"
"""
code = code.replace(track_detection_old, track_detection_new)

# 7. Rediseño de UI: remover tabs y colocar en splitter
ui_old = """        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("QTabWidget::pane { border: 1px solid #45a29e; } QTabBar::tab { background: #1f2833; color: white; padding: 10px; } QTabBar::tab:selected { background: #66fcf1; color: black; font-weight: bold; }")
        
        self.graph_widget = pg.GraphicsLayoutWidget()
        self.graph_widget.setBackground('#0b0c10')"""

ui_new = """        self.graph_widget = pg.GraphicsLayoutWidget()
        self.graph_widget.setBackground('#0b0c10')"""
code = code.replace(ui_old, ui_new)

ui_old2 = """        self.tabs.addTab(self.graph_widget, "Telemetría Pro")
        
        self.table_corners = QTableWidget()
        self.table_corners.setColumnCount(4)
        self.table_corners.setHorizontalHeaderLabels(["Curva", "Vel. Entrada", "Vel. Ápice", "Freno Max"])
        header = self.table_corners.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_corners.setStyleSheet("QTableWidget { color: white; background-color: #1f2833; border: 1px solid #45a29e; } QHeaderView::section { background-color: #0b0c10; color: #66fcf1; }")
        
        self.tabs.addTab(self.table_corners, "Análisis de Curvas")
        
        right_layout.addWidget(self.tabs)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(self.map_widget)
        splitter.addWidget(right_panel)
        
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setStretchFactor(2, 4)
        
        layout.addWidget(splitter)"""

ui_new2 = """        self.table_corners = QTableWidget()
        self.table_corners.setColumnCount(4)
        self.table_corners.setHorizontalHeaderLabels(["Curva", "Vel. Entrada", "Vel. Ápice", "Freno Max"])
        header = self.table_corners.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_corners.setStyleSheet("QTableWidget { color: white; background-color: #1f2833; border: 1px solid #45a29e; } QHeaderView::section { background-color: #0b0c10; color: #66fcf1; }")
        
        # Panel derecho es ahora un splitter vertical (mapa arriba, tabla abajo)
        right_sub_splitter = QSplitter(Qt.Orientation.Vertical)
        right_sub_splitter.addWidget(self.map_widget)
        right_sub_splitter.addWidget(self.table_corners)
        right_sub_splitter.setStretchFactor(0, 3)
        right_sub_splitter.setStretchFactor(1, 2)
        
        right_layout.addWidget(right_sub_splitter)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(self.graph_widget)
        splitter.addWidget(right_panel)
        
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 5)
        splitter.setStretchFactor(2, 3)
        
        layout.addWidget(splitter)"""
code = code.replace(ui_old2, ui_new2)

with open('ui/widgets/advanced_analysis_dialog.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Patch applied.")
