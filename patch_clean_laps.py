import sys

with open('ui/widgets/advanced_analysis_dialog.py', 'r', encoding='utf-8') as f:
    code = f.read()

old_logic = """            for lap, data in list(self.laps_data.items()):
                if len(data.packets) < 100:
                    del self.laps_data[lap]
                    continue
                    
                data.lap_time = len(data.packets) * (1000.0 / 60.0)
                data.is_valid = True
                
                if data.lap_time < best_time and lap > 0:
                    best_time = data.lap_time
                    self.best_lap = lap"""

new_logic = """            for lap, data in list(self.laps_data.items()):
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
                # If only 2 laps (e.g. 0 and 1), delete 0
                for lap in list(self.laps_data.keys()):
                    if lap <= 0:
                        del self.laps_data[lap]

            for lap, data in self.laps_data.items():
                if data.lap_time < best_time:
                    best_time = data.lap_time
                    self.best_lap = lap"""

code = code.replace(old_logic, new_logic)

with open('ui/widgets/advanced_analysis_dialog.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Patch applied to clean out-laps and in-laps.")
