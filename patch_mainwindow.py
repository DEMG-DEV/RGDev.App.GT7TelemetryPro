import sys

with open('ui/main_window.py', 'r', encoding='utf-8') as f:
    code = f.read()

old_load_session = """    def load_session(self):
        sessions_dir = os.path.join(os.getcwd(), 'Sessions')
        master_db = os.path.join(sessions_dir, 'telemetry_master.sqlite')
        
        if not os.path.exists(master_db):
            self.lbl_status.setText("Status: No Master DB found")
            return
            
        import sqlite3
        from PyQt6.QtWidgets import QInputDialog, QMessageBox
        
        try:
            with sqlite3.connect(master_db) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, start_time, car_name, total_laps, best_laptime FROM sessions ORDER BY id DESC")
                sessions = cursor.fetchall()
                
            if not sessions:
                self.lbl_status.setText("Status: No sessions found")
                return
                
            session_items = []
            session_ids = []
            for s in sessions:
                s_id, s_time, c_name, t_laps, b_lap = s
                # Format b_lap from ms to MM:SS.ms
                if b_lap and b_lap > 0:
                    minutes = b_lap // 60000
                    seconds = (b_lap % 60000) / 1000
                    lap_str = f"{minutes:02d}:{seconds:06.3f}"
                else:
                    lap_str = "N/A"
                    
                display_text = f"#{s_id} - {s_time[:16]} | {c_name} | Laps: {t_laps} | Best: {lap_str}"
                session_items.append(display_text)
                session_ids.append(s_id)
                
            item, ok = QInputDialog.getItem(
                self, 
                "Select Session", 
                "Choose a historical session to replay:", 
                session_items, 
                0, 
                False
            )
            
            if ok and item:
                index = session_items.index(item)
                selected_id = session_ids[index]
                
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Acción sobre Sesión")
                msg_box.setText(f"Has seleccionado la sesión #{selected_id}.\\n¿Qué deseas hacer?")
                btn_analysis = msg_box.addButton("Análisis Rápido", QMessageBox.ButtonRole.ActionRole)
                btn_play = msg_box.addButton("Reproducir Sesión", QMessageBox.ButtonRole.ActionRole)
                btn_cancel = msg_box.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
                
                msg_box.exec()
                
                if msg_box.clickedButton() == btn_analysis:
                    self.show_quick_analysis(master_db, selected_id)
                elif msg_box.clickedButton() == btn_play:
                    self.player.load(master_db, selected_id)
                    self.player.play()
                    self.btn_play.setEnabled(True)
                    self.lbl_status.setText(f"Status: Playing Session #{selected_id}")
                    self.lbl_status.setStyleSheet("color: #00ff7f; font-weight: bold; font-size: 14px;")
                    self.btn_connect.setEnabled(False)
        except Exception as e:
            self.lbl_status.setText(f"Status: Error loading sessions ({e})")
            import logging
            logging.error(f"Failed to load sessions: {e}")"""

new_load_session = """    def load_session(self):
        sessions_dir = os.path.join(os.getcwd(), 'Sessions')
        master_db = os.path.join(sessions_dir, 'telemetry_master.sqlite')
        
        if not os.path.exists(master_db):
            self.lbl_status.setText("Status: No Master DB found")
            return
            
        import sqlite3
        from ui.widgets.session_browser import SessionBrowserDialog
        from PyQt6.QtWidgets import QDialog
        
        try:
            with sqlite3.connect(master_db) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, start_time, car_name, total_laps, best_laptime FROM sessions ORDER BY id DESC")
                sessions = cursor.fetchall()
                
            if not sessions:
                self.lbl_status.setText("Status: No sessions found")
                return
                
            dialog = SessionBrowserDialog(sessions, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                selected_id = dialog.selected_id
                action = dialog.action_type
                
                if action == "ANALYSIS":
                    self.show_quick_analysis(master_db, selected_id)
                elif action == "PLAY":
                    self.player.load(master_db, selected_id)
                    self.player.play()
                    self.btn_play.setEnabled(True)
                    self.lbl_status.setText(f"Status: Playing Session #{selected_id}")
                    self.lbl_status.setStyleSheet("color: #00ff7f; font-weight: bold; font-size: 14px;")
                    self.btn_connect.setEnabled(False)
        except Exception as e:
            self.lbl_status.setText(f"Status: Error loading sessions ({e})")
            import logging
            logging.error(f"Failed to load sessions: {e}")"""

code = code.replace(old_load_session, new_load_session)

with open('ui/main_window.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Patch applied to main_window.py")
