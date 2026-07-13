from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QListWidget, 
                             QPushButton, QLabel, QTextEdit, QLineEdit, QComboBox, 
                             QMessageBox, QDialog, QSplitter)
from PyQt6.QtCore import Qt
import numpy as np
from core.dynamic_math import DynamicMathEngine

class FormulaManagerWidget(QDialog):
    def __init__(self, math_engine: DynamicMathEngine, parent=None, test_context=None):
        super().__init__(parent)
        self.engine = math_engine
        self.test_context = test_context # Dict[str, np.ndarray] para pruebas dry-run
        self.setWindowTitle("Formula Manager")
        self.resize(800, 600)
        self.init_ui()
        self.load_formulas()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        
        # Left Panel (List)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0,0,0,0)
        
        self.list_formulas = QListWidget()
        self.list_formulas.itemSelectionChanged.connect(self.on_select_formula)
        left_layout.addWidget(QLabel("Saved Channels:"))
        left_layout.addWidget(self.list_formulas)
        
        btn_add = QPushButton("New Channel")
        btn_add.clicked.connect(self.on_new)
        left_layout.addWidget(btn_add)
        
        btn_del = QPushButton("Delete")
        btn_del.clicked.connect(self.on_delete)
        left_layout.addWidget(btn_del)
        
        # Right Panel (Editor)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0,0,0,0)
        
        form_h1 = QHBoxLayout()
        form_h1.addWidget(QLabel("Name:"))
        self.in_name = QLineEdit()
        form_h1.addWidget(self.in_name)
        
        form_h1.addWidget(QLabel("Group:"))
        self.in_group = QComboBox()
        self.in_group.addItems(["Engine", "Suspension", "Tyres", "Driver", "Chassis", "Custom"])
        self.in_group.setEditable(True)
        form_h1.addWidget(self.in_group)
        
        form_h1.addWidget(QLabel("Color:"))
        self.in_color = QLineEdit("#FFFFFF")
        self.in_color.setFixedWidth(80)
        form_h1.addWidget(self.in_color)
        right_layout.addLayout(form_h1)
        
        right_layout.addWidget(QLabel("Description:"))
        self.in_desc = QLineEdit()
        right_layout.addWidget(self.in_desc)
        
        right_layout.addWidget(QLabel("Math Expression (NumPy allowed via 'np.'):"))
        self.in_expr = QTextEdit()
        self.in_expr.setStyleSheet("font-family: monospace; font-size: 14px; background-color: #FAFAFA; color: #1A1A1A;")
        right_layout.addWidget(self.in_expr)
        
        # Action Buttons
        btn_h = QHBoxLayout()
        btn_test = QPushButton("Dry Run (Test)")
        btn_test.clicked.connect(self.on_test)
        btn_save = QPushButton("Save Channel")
        btn_save.clicked.connect(self.on_save)
        
        btn_h.addWidget(btn_test)
        btn_h.addWidget(btn_save)
        right_layout.addLayout(btn_h)
        
        self.lbl_status = QLabel("Ready")
        self.lbl_status.setStyleSheet("color: #666;")
        right_layout.addWidget(self.lbl_status)
        
        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([250, 550])
        
        main_layout.addWidget(splitter)
        
    def load_formulas(self):
        self.list_formulas.clear()
        for name in sorted(self.engine.channels.keys()):
            self.list_formulas.addItem(name)
            
    def on_select_formula(self):
        items = self.list_formulas.selectedItems()
        if not items:
            return
        name = items[0].text()
        ch = self.engine.channels.get(name)
        if not ch:
            return
            
        self.in_name.setText(name)
        self.in_name.setReadOnly(True) # Cannot rename directly, must create new to rename
        self.in_group.setCurrentText(ch.get("group", "Custom"))
        self.in_color.setText(ch.get("color", "#FFFFFF"))
        self.in_desc.setText(ch.get("description", ""))
        self.in_expr.setPlainText(ch.get("expression", ""))
        self.lbl_status.setText("Loaded.")
        
    def on_new(self):
        self.list_formulas.clearSelection()
        self.in_name.setReadOnly(False)
        self.in_name.clear()
        self.in_group.setCurrentText("Custom")
        self.in_color.setText("#FFFFFF")
        self.in_desc.clear()
        self.in_expr.clear()
        self.lbl_status.setText("New channel mode.")
        self.in_name.setFocus()
        
    def on_delete(self):
        items = self.list_formulas.selectedItems()
        if not items:
            return
        name = items[0].text()
        reply = QMessageBox.question(self, "Confirm Delete", f"Delete channel '{name}'?", 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.engine.delete_channel(name)
            self.load_formulas()
            self.on_new()
            
    def on_save(self):
        name = self.in_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Name cannot be empty.")
            return
            
        expr = self.in_expr.toPlainText()
        
        # Validate syntax
        # We need a context set to validate. If test_context is provided, use it. Otherwise use dummy.
        dummy_vars = set(self.test_context.keys()) if self.test_context else {"speed", "throttle", "brake", "sway", "surge", "heave"}
        is_valid, msg = self.engine.validate_expression(expr, dummy_vars)
        if not is_valid:
            QMessageBox.critical(self, "Syntax/Security Error", msg)
            return
            
        self.engine.add_channel(
            name, expr, 
            group=self.in_group.currentText(),
            color=self.in_color.text(),
            description=self.in_desc.text()
        )
        self.lbl_status.setText("Saved successfully.")
        
        # Reload and select
        self.load_formulas()
        items = self.list_formulas.findItems(name, Qt.MatchFlag.MatchExactly)
        if items:
            items[0].setSelected(True)
            
    def on_test(self):
        if not self.test_context:
            self.lbl_status.setText("No test context provided (live session needed).")
            return
            
        expr = self.in_expr.toPlainText()
        name = self.in_name.text().strip() or "test_channel"
        
        # Temporarily inject into engine to test evaluate
        old_val = None
        existed = name in self.engine.channels
        if existed:
            old_val = self.engine.channels[name]
            
        self.engine.channels[name] = {"expression": expr}
        try:
            res = self.engine.evaluate(name, self.test_context)
            self.lbl_status.setText(f"Success! Result Shape: {res.shape}, Min: {np.min(res):.2f}, Max: {np.max(res):.2f}")
            self.lbl_status.setStyleSheet("color: #00AA00;")
        except Exception as e:
            self.lbl_status.setText(f"Error: {e}")
            self.lbl_status.setStyleSheet("color: #AA0000;")
        finally:
            if existed:
                self.engine.channels[name] = old_val
            else:
                del self.engine.channels[name]
