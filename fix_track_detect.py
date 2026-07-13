import sys

with open('ui/widgets/advanced_analysis_dialog.py', 'r', encoding='utf-8') as f:
    code = f.read()

old_logic = """            # Track detection
            valid_laps_for_detection = [lap for lap in self.laps_data.keys() if 0 < lap < max(self.laps_data.keys())]
            if not valid_laps_for_detection and self.best_lap in self.laps_data:
                valid_laps_for_detection = [self.best_lap]"""

new_logic = """            # Track detection
            # Ya limpiamos las vueltas basura arriba, así que usamos todas las que quedaron.
            valid_laps_for_detection = list(self.laps_data.keys())
            if not valid_laps_for_detection and self.best_lap in self.laps_data:
                valid_laps_for_detection = [self.best_lap]"""

code = code.replace(old_logic, new_logic)

with open('ui/widgets/advanced_analysis_dialog.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Track detection logic updated.")
