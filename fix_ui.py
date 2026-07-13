import sys

with open('ui/widgets/advanced_analysis_dialog.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Fix data.is_valid logic and best_lap logic
old_logic = """            for lap, data in list(self.laps_data.items()):
                if len(data.packets) < 100:
                    del self.laps_data[lap]
                    continue
                    
                # Fix lap_time using 60Hz packet count instead of corrupt current_lap_time
                data.lap_time = len(data.packets) * (1000.0 / 60.0)
                
                if data.lap_time > 10000:
                    data.is_valid = True
                    if data.lap_time < best_time:
                        best_time = data.lap_time
                        self.best_lap = lap"""

new_logic = """            for lap, data in list(self.laps_data.items()):
                if len(data.packets) < 100:
                    del self.laps_data[lap]
                    continue
                    
                data.lap_time = len(data.packets) * (1000.0 / 60.0)
                data.is_valid = True
                
                if data.lap_time < best_time and lap > 0:
                    best_time = data.lap_time
                    self.best_lap = lap"""

code = code.replace(old_logic, new_logic)

# 2. Fix the 'Invalida' string in list
old_list = """        for lap in sorted(self.laps_data.keys()):
            data = self.laps_data[lap]
            t_str = f"{int(data.lap_time // 60000):02d}:{((data.lap_time % 60000) / 1000):06.3f}" if data.is_valid else "Invalida"
            marker = "★ " if lap == self.best_lap else ""
            self.list_laps.addItem(f"{marker}Vuelta {lap} ({t_str})")"""

new_list = """        for lap in sorted(self.laps_data.keys()):
            data = self.laps_data[lap]
            t_str = f"{int(data.lap_time // 60000):02d}:{((data.lap_time % 60000) / 1000):06.3f}"
            marker = "★ " if lap == self.best_lap else ""
            self.list_laps.addItem(f"{marker}Vuelta {lap} ({t_str})")"""

code = code.replace(old_list, new_list)

# 3. Auto-select first lap in init_ui
old_ui_end = """        layout.addWidget(splitter)"""
new_ui_end = """        layout.addWidget(splitter)
        
        # Auto select best lap
        if self.list_laps.count() > 0:
            items = self.list_laps.findItems("★", Qt.MatchFlag.MatchContains)
            if items:
                items[0].setSelected(True)
                self.on_lap_selected(items[0])
            else:
                self.list_laps.item(0).setSelected(True)
                self.on_lap_selected(self.list_laps.item(0))"""

code = code.replace(old_ui_end, new_ui_end)

with open('ui/widgets/advanced_analysis_dialog.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("UI Fixed.")
