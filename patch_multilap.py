import sys

with open('ui/widgets/advanced_analysis_dialog.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Modify List setup
old_list_setup = """        self.list_laps = QListWidget()
        self.list_laps.setFixedWidth(200)
        self.list_laps.setStyleSheet("background-color: #1f2833; color: white;")
        self.list_laps.itemClicked.connect(self.on_lap_selected)
        
        # Populate laps
        for lap in sorted(self.laps_data.keys()):
            data = self.laps_data[lap]
            t_str = f"{int(data.lap_time // 60000):02d}:{((data.lap_time % 60000) / 1000):06.3f}"
            marker = "★ " if lap == self.best_lap else ""
            self.list_laps.addItem(f"{marker}Vuelta {lap} ({t_str})")"""

new_list_setup = """        self.list_laps = QListWidget()
        self.list_laps.setFixedWidth(200)
        self.list_laps.setStyleSheet("background-color: #1f2833; color: white;")
        self.list_laps.itemSelectionChanged.connect(self.on_lap_selected)
        self.list_laps.itemChanged.connect(self.refresh_plot)
        
        self.colors = ['#00ffff', '#ff00ff', '#ffff00', '#00ff00', '#ff0000', '#ffffff']
        
        # Populate laps
        for lap in sorted(self.laps_data.keys()):
            data = self.laps_data[lap]
            t_str = f"{int(data.lap_time // 60000):02d}:{((data.lap_time % 60000) / 1000):06.3f}"
            marker = "★ " if lap == self.best_lap else ""
            item = QListWidgetItem(f"{marker}Vuelta {lap} ({t_str})")
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if lap == self.best_lap else Qt.CheckState.Unchecked)
            self.list_laps.addItem(item)"""

code = code.replace(old_list_setup, new_list_setup)

# 2. Add Legend
old_legend = """        self.plot_speed = pg.PlotWidget(title="Velocidad (km/h)")
        self.plot_speed.showGrid(x=True, y=True, alpha=0.3)"""

new_legend = """        self.plot_speed = pg.PlotWidget(title="Velocidad (km/h)")
        self.plot_speed.addLegend()
        self.plot_speed.showGrid(x=True, y=True, alpha=0.3)"""
code = code.replace(old_legend, new_legend)

# 3. Modify auto-select
old_auto_select = """        if self.list_laps.count() > 0:
            items = self.list_laps.findItems("★", Qt.MatchFlag.MatchContains)
            if items:
                items[0].setSelected(True)
                self.on_lap_selected(items[0])
            else:
                self.list_laps.item(0).setSelected(True)
                self.on_lap_selected(self.list_laps.item(0))"""

new_auto_select = """        if self.list_laps.count() > 0:
            items = self.list_laps.findItems("★", Qt.MatchFlag.MatchContains)
            if items:
                items[0].setSelected(True)
            else:
                self.list_laps.item(0).setSelected(True)
            self.refresh_plot()"""
code = code.replace(old_auto_select, new_auto_select)

# 4. Rewrite on_lap_selected to only handle table/map (no plotting)
old_on_lap_selected = """    def on_lap_selected(self, item):
        txt = item.text().replace("★ ", "")
        lap_str = txt.split(" ")[1]
        lap = int(lap_str)
        
        data = self.laps_data[lap]
        self.active_lap_data = data
        
        self.plot_speed.clear()
        self.plot_speed.addItem(self.vline)
        self.plot_speed.plot(data.distance, data.speed, pen=pg.mkPen('c', width=2))
        
        # Calcular Resumen
        import numpy as np
        max_speed = np.max(data.speed)
        min_speed = np.min(data.speed)
        full_throttle_pts = np.sum(data.throttle > 95)
        brake_pts = np.sum(data.brake > 5)
        total_pts = len(data.packets)
        
        ft_pct = (full_throttle_pts / total_pts) * 100 if total_pts > 0 else 0
        brk_pct = (brake_pts / total_pts) * 100 if total_pts > 0 else 0
        
        self.table_summary.setItem(0, 0, QTableWidgetItem("Velocidad Máxima"))
        self.table_summary.setItem(0, 1, QTableWidgetItem(f"{max_speed:.1f} km/h"))
        
        self.table_summary.setItem(1, 0, QTableWidgetItem("Velocidad Mínima en Curva"))
        self.table_summary.setItem(1, 1, QTableWidgetItem(f"{min_speed:.1f} km/h"))
        
        self.table_summary.setItem(2, 0, QTableWidgetItem("Tiempo a fondo (Acelerador > 95%)"))
        self.table_summary.setItem(2, 1, QTableWidgetItem(f"{ft_pct:.1f}% de la vuelta"))
        
        self.table_summary.setItem(3, 0, QTableWidgetItem("Tiempo Frenando"))
        self.table_summary.setItem(3, 1, QTableWidgetItem(f"{brk_pct:.1f}% de la vuelta"))
        
        # Dar formato
        for row in range(4):
            item0 = self.table_summary.item(row, 0)
            item1 = self.table_summary.item(row, 1)
            if item0 and item1:
                item0.setFont(QFont("Arial", 12, QFont.Weight.Bold))
                item1.setFont(QFont("Arial", 12))
                item1.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                
        # Fill Map
        self.map_widget.clear()
        for p in data.packets:
            self.map_widget.add_point(p.position[0], p.position[2], p.throttle, p.brake)
        self.map_widget.update_plot()
        
        # Fill Corner table
        self.table_corners.setRowCount(0)
        if self.track_data and 'corners' in self.track_data:
            corners = self.track_data['corners']
            self.table_corners.setRowCount(len(corners))
            for i, c in enumerate(corners):
                entry_vel = c['entry_speed']
                apex_vel = c['apex_speed']
                max_brake = c['max_brake']
                
                self.table_corners.setItem(i, 0, QTableWidgetItem(f"Curva {c['id']}"))
                self.table_corners.setItem(i, 1, QTableWidgetItem(f"{entry_vel:.1f} km/h"))
                self.table_corners.setItem(i, 2, QTableWidgetItem(f"{apex_vel:.1f} km/h"))
                
                brk_item = QTableWidgetItem(f"{max_brake:.0f}%")
                if max_brake > 90:
                    brk_item.setForeground(Qt.GlobalColor.red)
                self.table_corners.setItem(i, 3, brk_item)"""

new_on_lap_selected = """    def on_lap_selected(self):
        items = self.list_laps.selectedItems()
        if not items:
            return
        item = items[0]
        
        txt = item.text().replace("★ ", "")
        lap_str = txt.split(" ")[1]
        lap = int(lap_str)
        
        data = self.laps_data[lap]
        self.active_lap_data = data
        
        # Calcular Resumen para la vuelta seleccionada
        import numpy as np
        if len(data.speed) == 0:
            return
            
        max_speed = np.max(data.speed)
        min_speed = np.min(data.speed)
        full_throttle_pts = np.sum(data.throttle > 95)
        brake_pts = np.sum(data.brake > 5)
        total_pts = len(data.packets)
        
        ft_pct = (full_throttle_pts / total_pts) * 100 if total_pts > 0 else 0
        brk_pct = (brake_pts / total_pts) * 100 if total_pts > 0 else 0
        
        self.table_summary.setItem(0, 0, QTableWidgetItem("Velocidad Máxima"))
        self.table_summary.setItem(0, 1, QTableWidgetItem(f"{max_speed:.1f} km/h"))
        
        self.table_summary.setItem(1, 0, QTableWidgetItem("Velocidad Mínima en Curva"))
        self.table_summary.setItem(1, 1, QTableWidgetItem(f"{min_speed:.1f} km/h"))
        
        self.table_summary.setItem(2, 0, QTableWidgetItem("Tiempo a fondo (Acelerador > 95%)"))
        self.table_summary.setItem(2, 1, QTableWidgetItem(f"{ft_pct:.1f}% de la vuelta"))
        
        self.table_summary.setItem(3, 0, QTableWidgetItem("Tiempo Frenando"))
        self.table_summary.setItem(3, 1, QTableWidgetItem(f"{brk_pct:.1f}% de la vuelta"))
        
        # Dar formato
        for row in range(4):
            item0 = self.table_summary.item(row, 0)
            item1 = self.table_summary.item(row, 1)
            if item0 and item1:
                item0.setFont(QFont("Arial", 12, QFont.Weight.Bold))
                item1.setFont(QFont("Arial", 12))
                item1.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                
        # Fill Map
        self.map_widget.clear()
        for p in data.packets:
            self.map_widget.add_point(p.position[0], p.position[2], p.throttle, p.brake)
        self.map_widget.update_plot()
        
        # Fill Corner table
        self.table_corners.setRowCount(0)
        if self.track_data and 'corners' in self.track_data:
            corners = self.track_data['corners']
            self.table_corners.setRowCount(len(corners))
            for i, c in enumerate(corners):
                entry_vel = c['entry_speed']
                apex_vel = c['apex_speed']
                max_brake = c['max_brake']
                
                self.table_corners.setItem(i, 0, QTableWidgetItem(f"Curva {c['id']}"))
                self.table_corners.setItem(i, 1, QTableWidgetItem(f"{entry_vel:.1f} km/h"))
                self.table_corners.setItem(i, 2, QTableWidgetItem(f"{apex_vel:.1f} km/h"))
                
                brk_item = QTableWidgetItem(f"{max_brake:.0f}%")
                if max_brake > 90:
                    brk_item.setForeground(Qt.GlobalColor.red)
                self.table_corners.setItem(i, 3, brk_item)

    def refresh_plot(self, changed_item=None):
        self.plot_speed.clear()
        self.plot_speed.addItem(self.vline)
        
        color_idx = 0
        for i in range(self.list_laps.count()):
            item = self.list_laps.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                txt = item.text().replace("★ ", "")
                lap_str = txt.split(" ")[1]
                lap = int(lap_str)
                
                data = self.laps_data[lap]
                if len(data.distance) > 0:
                    color = self.colors[color_idx % len(self.colors)]
                    self.plot_speed.plot(
                        data.distance, 
                        data.speed, 
                        pen=pg.mkPen(color, width=2), 
                        name=f"Vuelta {lap}"
                    )
                    color_idx += 1"""

code = code.replace(old_on_lap_selected, new_on_lap_selected)

with open('ui/widgets/advanced_analysis_dialog.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Patch applied for multi-lap overlay.")
