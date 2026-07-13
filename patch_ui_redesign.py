import sys
import re

with open('ui/widgets/advanced_analysis_dialog.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Update Track Detection
old_track_logic = """                    score = 0
                    score += abs(t.get('length_m', 0) - total_dist) / 100.0
                    score += abs(t.get('elevation_diff_m', 0) - elev_diff) / 10.0
                    score += abs(t.get('num_corners', 0) - num_corners) * 5.0"""
                    
new_track_logic = """                    length_diff = abs(t.get('length_m', 0) - total_dist)
                    if length_diff > 300:  # Hard filter: if off by more than 300m, skip
                        continue
                    score = 0
                    score += length_diff / 10.0
                    score += abs(t.get('elevation_diff_m', 0) - elev_diff) / 5.0
                    score += abs(t.get('num_corners', 0) - num_corners) * 1.0"""
code = code.replace(old_track_logic, new_track_logic)

# 2. Update init_ui to remove plots and add table
# Find where the plots are initialized
old_ui_block = """        # Gráficas
        graphs_widget = QWidget()
        graphs_layout = QVBoxLayout(graphs_widget)
        graphs_layout.setContentsMargins(0, 0, 0, 0)
        
        self.plot_delta = pg.PlotWidget(title="Delta Time (s)")
        self.plot_speed = pg.PlotWidget(title="Velocidad (km/h)")
        self.plot_rpm = pg.PlotWidget(title="R.P.M. y Dirección")
        self.plot_throttle_brake = pg.PlotWidget(title="Acelerador / Freno (%)")
        
        # Ocultar ejes X excepto en el último
        self.plot_delta.getAxis('bottom').setStyle(showValues=False)
        self.plot_speed.getAxis('bottom').setStyle(showValues=False)
        self.plot_rpm.getAxis('bottom').setStyle(showValues=False)
        
        # Link X axis
        self.plot_speed.setXLink(self.plot_delta)
        self.plot_rpm.setXLink(self.plot_delta)
        self.plot_throttle_brake.setXLink(self.plot_delta)
        
        graphs_layout.addWidget(self.plot_delta)
        graphs_layout.addWidget(self.plot_speed)
        graphs_layout.addWidget(self.plot_rpm)
        graphs_layout.addWidget(self.plot_throttle_brake)
        
        # Líneas verticales
        self.vlines = []
        for p in [self.plot_delta, self.plot_speed, self.plot_rpm, self.plot_throttle_brake]:
            p.showGrid(x=True, y=True, alpha=0.3)
            p.setBackground('#0b0c10')
            vline = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen(color='w', style=Qt.PenStyle.DashLine))
            p.addItem(vline)
            self.vlines.append(vline)
            
        proxy = pg.SignalProxy(self.plot_throttle_brake.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)
        self.proxy = proxy"""

new_ui_block = """        # Gráficas y Resumen
        graphs_widget = QWidget()
        graphs_layout = QVBoxLayout(graphs_widget)
        graphs_layout.setContentsMargins(0, 0, 0, 0)
        
        # Única Gráfica
        self.plot_speed = pg.PlotWidget(title="Velocidad (km/h)")
        self.plot_speed.showGrid(x=True, y=True, alpha=0.3)
        self.plot_speed.setBackground('#0b0c10')
        self.vline = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen(color='w', style=Qt.PenStyle.DashLine))
        self.plot_speed.addItem(self.vline)
        
        # Tabla de Resumen
        self.table_summary = QTableWidget()
        self.table_summary.setColumnCount(2)
        self.table_summary.setRowCount(4)
        self.table_summary.horizontalHeader().setVisible(False)
        self.table_summary.verticalHeader().setVisible(False)
        self.table_summary.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_summary.setStyleSheet("background-color: #1f2833; color: white; font-size: 14px;")
        
        graphs_layout.addWidget(self.plot_speed, stretch=2)
        
        lbl_res = QLabel("📋 Resumen de la Vuelta")
        lbl_res.setStyleSheet("font-size: 16px; font-weight: bold; color: #66fcf1; padding-top: 10px;")
        graphs_layout.addWidget(lbl_res)
        graphs_layout.addWidget(self.table_summary, stretch=1)
        
        proxy = pg.SignalProxy(self.plot_speed.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)
        self.proxy = proxy"""

code = code.replace(old_ui_block, new_ui_block)

# 3. Update on_lap_selected
old_plot_logic = """        self.plot_delta.clear()
        self.plot_speed.clear()
        self.plot_rpm.clear()
        self.plot_throttle_brake.clear()
        
        self.plot_delta.addItem(self.vlines[0])
        self.plot_speed.addItem(self.vlines[1])
        self.plot_rpm.addItem(self.vlines[2])
        self.plot_throttle_brake.addItem(self.vlines[3])
        
        # Graficar Velocidad
        self.plot_speed.plot(data.distance, data.speed, pen=pg.mkPen('c', width=2))
        
        # Graficar RPM y Dirección
        self.plot_rpm.plot(data.distance, data.rpm, pen=pg.mkPen('y', width=1.5))
        
        # Graficar Acelerador y Freno
        self.plot_throttle_brake.plot(data.distance, data.throttle, pen=pg.mkPen('g', width=2), fillLevel=0, brush=(0,255,0,50))
        self.plot_throttle_brake.plot(data.distance, data.brake, pen=pg.mkPen('r', width=2), fillLevel=0, brush=(255,0,0,50))"""

new_plot_logic = """        self.plot_speed.clear()
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
                item1.setTextAlignment(Qt.AlignmentFlag.AlignCenter)"""

code = code.replace(old_plot_logic, new_plot_logic)

# 4. Update mouseMoved
old_mouse_logic = """            x_dist = p.x()
            if self.active_lap_data and len(self.active_lap_data.distance) > 0:
                # Find closest index
                idx = (np.abs(self.active_lap_data.distance - x_dist)).argmin()
                
                for vline in self.vlines:
                    vline.setPos(x_dist)"""

new_mouse_logic = """            x_dist = p.x()
            if self.active_lap_data and len(self.active_lap_data.distance) > 0:
                # Find closest index
                idx = (np.abs(self.active_lap_data.distance - x_dist)).argmin()
                self.vline.setPos(x_dist)"""

code = code.replace(old_mouse_logic, new_mouse_logic)

with open('ui/widgets/advanced_analysis_dialog.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("UI Redesign patched.")
