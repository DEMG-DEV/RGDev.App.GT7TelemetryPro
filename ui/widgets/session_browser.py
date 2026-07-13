import sqlite3
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QPushButton, QHeaderView, QLabel,
                             QAbstractItemView, QMessageBox)
from PyQt6.QtCore import Qt

class SessionBrowserDialog(QDialog):
    def __init__(self, sessions, parent=None):
        super().__init__(parent)
        self.sessions = sessions
        self.selected_id = None
        self.action_type = None  # 'ANALYSIS' or 'PLAY'
        
        self.setWindowTitle("Explorador de Sesiones (Session Browser)")
        self.setMinimumSize(800, 400)
        self.setStyleSheet("background-color: #0b0c10; color: #c5c6c7;")
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        title = QLabel("Historial de Sesiones")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #66fcf1;")
        layout.addWidget(title)
        
        main_layout = QHBoxLayout()
        
        # Tabla de Sesiones
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Fecha / Hora", "Auto", "Vueltas", "Mejor Vuelta"])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setStyleSheet("""
            QTableWidget { background-color: #1f2833; color: white; border: 1px solid #45a29e; }
            QHeaderView::section { background-color: #0b0c10; color: #66fcf1; font-weight: bold; }
            QTableWidget::item:selected { background-color: #66fcf1; color: black; }
        """)
        
        self.table.cellDoubleClicked.connect(self.on_double_click)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        
        self.populate_table()
        main_layout.addWidget(self.table, stretch=4)
        
        # Panel de botones laterales
        btn_layout = QVBoxLayout()
        
        self.btn_analysis = QPushButton("📊 Análisis Avanzado\n(Doble Clic)")
        self.btn_analysis.setStyleSheet("background-color: #45a29e; color: white; font-weight: bold; padding: 15px;")
        self.btn_analysis.clicked.connect(self.on_analysis_clicked)
        self.btn_analysis.setEnabled(False)
        
        self.btn_play = QPushButton("▶️ Reproducir Telemetría")
        self.btn_play.setStyleSheet("background-color: #1f2833; color: white; padding: 15px; border: 1px solid #45a29e;")
        self.btn_play.clicked.connect(self.on_play_clicked)
        self.btn_play.setEnabled(False)
        
        btn_layout.addWidget(self.btn_analysis)
        btn_layout.addWidget(self.btn_play)
        btn_layout.addStretch()
        
        main_layout.addLayout(btn_layout, stretch=1)
        
        layout.addLayout(main_layout)
        
    def populate_table(self):
        self.table.setRowCount(len(self.sessions))
        for row, s in enumerate(self.sessions):
            s_id, s_time, c_name, t_laps, b_lap = s
            
            # Formatear el mejor tiempo
            if b_lap and b_lap > 0:
                minutes = int(b_lap // 60000)
                seconds = (b_lap % 60000) / 1000.0
                lap_str = f"{minutes:02d}:{seconds:06.3f}"
            else:
                lap_str = "N/A"
                
            item_id = QTableWidgetItem(f"#{s_id}")
            item_id.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            item_date = QTableWidgetItem(str(s_time)[:16])
            item_date.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            item_car = QTableWidgetItem(str(c_name))
            
            item_laps = QTableWidgetItem(str(t_laps))
            item_laps.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            item_best = QTableWidgetItem(lap_str)
            item_best.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if lap_str != "N/A":
                item_best.setForeground(Qt.GlobalColor.green)
                
            self.table.setItem(row, 0, item_id)
            self.table.setItem(row, 1, item_date)
            self.table.setItem(row, 2, item_car)
            self.table.setItem(row, 3, item_laps)
            self.table.setItem(row, 4, item_best)
            
            # Guardar el ID de la sesión en el Data de la fila
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, s_id)

    def on_selection_changed(self):
        selected = self.table.selectedItems()
        has_selection = len(selected) > 0
        self.btn_analysis.setEnabled(has_selection)
        self.btn_play.setEnabled(has_selection)
        
        if has_selection:
            # Obtener el ID de la fila seleccionada (desde la columna 0)
            row = selected[0].row()
            self.selected_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            
    def on_double_click(self, row, column):
        self.selected_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        self.action_type = "ANALYSIS"
        self.accept()
        
    def on_analysis_clicked(self):
        if self.selected_id is not None:
            self.action_type = "ANALYSIS"
            self.accept()
            
    def on_play_clicked(self):
        if self.selected_id is not None:
            self.action_type = "PLAY"
            self.accept()
