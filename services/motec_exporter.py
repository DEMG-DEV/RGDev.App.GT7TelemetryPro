import struct
import numpy as np
import os
import xml.etree.ElementTree as ET
import logging
import zipfile

class MotecLdWriter:
    def __init__(self, filename, session_info):
        self.filename = filename
        self.session_info = session_info
        self.channels = []
        self.num_channels = 0
        self.sample_rate = 60  # Fixed 60Hz

    def add_channel(self, name, units, data, data_type=3):
        # data_type: 1 = int16, 2 = int32, 3 = float32
        self.channels.append({
            'name': name[:31].encode('ascii', 'ignore').ljust(32, b'\0'),
            'units': units[:15].encode('ascii', 'ignore').ljust(16, b'\0'),
            'data': data,
            'data_type': data_type,
            'num_samples': len(data)
        })
        self.num_channels += 1

    def write(self):
        with open(self.filename, 'wb') as f:
            # A. File Header (offset 0x00 - 0x40)
            magic = b"LDData\0\0"
            f.write(magic)  # 0x00
            
            f.write(struct.pack('<I', 0x00010003))  # 0x08 Format version
            
            ch_meta_ptr = 0x40  # Offset to first channel header
            lap_ptr = 0  # 0x10, Lap blocks will be defined in LDX instead
            
            f.write(struct.pack('<I', ch_meta_ptr))  # 0x0C
            f.write(struct.pack('<I', lap_ptr))  # 0x10
            
            # Padding
            f.write(b'\0' * 16)
            
            f.write(struct.pack('<I', self.num_channels))  # 0x24 Total channels
            
            # Pad to 0x40
            f.write(b'\0' * (0x40 - f.tell()))
            
            # B. Channel Headers
            channel_header_size = 124  # Size for MoTeC channel headers
            
            data_start_offset = ch_meta_ptr + (self.num_channels * channel_header_size)
            current_data_offset = data_start_offset
            
            for i, ch in enumerate(self.channels):
                next_ch_ptr = ch_meta_ptr + (i + 1) * channel_header_size if i < self.num_channels - 1 else 0
                
                f.write(struct.pack('<I', next_ch_ptr))          # 0x00 Next channel
                f.write(struct.pack('<I', current_data_offset))  # 0x04 Data offset
                f.write(struct.pack('<I', ch['num_samples']))    # 0x08 Num samples
                f.write(struct.pack('<H', ch['data_type']))      # 0x0C Data type
                f.write(struct.pack('<H', self.sample_rate))     # 0x0E Sample rate
                
                f.write(ch['name'])   # 0x10 (32 bytes)
                f.write(ch['units'])  # 0x30 (16 bytes)
                
                bytes_written = 4 + 4 + 4 + 2 + 2 + 32 + 16
                f.write(b'\0' * (channel_header_size - bytes_written))
                
                if ch['data_type'] == 1:
                    size_per_sample = 2
                elif ch['data_type'] == 2:
                    size_per_sample = 4
                elif ch['data_type'] == 3:
                    size_per_sample = 4
                else:
                    size_per_sample = 4
                    
                current_data_offset += ch['num_samples'] * size_per_sample
                
            # C. Data Blocks
            for ch in self.channels:
                if ch['data_type'] == 1:
                    data = np.asarray(ch['data'], dtype=np.int16)
                    f.write(data.tobytes())
                elif ch['data_type'] == 2:
                    data = np.asarray(ch['data'], dtype=np.int32)
                    f.write(data.tobytes())
                elif ch['data_type'] == 3:
                    data = np.asarray(ch['data'], dtype=np.float32)
                    f.write(data.tobytes())

class MotecLdxWriter:
    def __init__(self, filename, session_info, laps_info):
        self.filename = filename
        self.session_info = session_info
        self.laps_info = laps_info

    def write(self):
        root = ET.Element("MoTeC_File")
        
        session = ET.SubElement(root, "Session")
        ET.SubElement(session, "Driver").text = self.session_info.get("Driver", "GT7 Driver")
        ET.SubElement(session, "Vehicle").text = self.session_info.get("Vehicle", "Unknown Car")
        ET.SubElement(session, "Venue").text = self.session_info.get("Venue", "Unknown Track")
        ET.SubElement(session, "Date").text = self.session_info.get("Date", "")
        
        laps = ET.SubElement(root, "Laps")
        for lap in self.laps_info:
            ET.SubElement(laps, "Lap", {
                "LapNumber": str(lap.get('LapNumber', 0)),
                "StartTime": f"{lap.get('StartTime', 0.0):.4f}",
                "Duration": f"{lap.get('Duration', 0.0):.4f}",
                "IsFastest": "true" if lap.get('IsFastest', False) else "false"
            })
            
        ET.SubElement(root, "Beacons")
            
        tree = ET.ElementTree(root)
        ET.indent(tree, space="\t", level=0)
        tree.write(self.filename, encoding="utf-8", xml_declaration=True)


class MotecExporter:
    def __init__(self, vectorized_data, session_info, export_path, zip_output=False):
        self.vectorized_data = vectorized_data
        self.session_info = session_info
        self.export_path = export_path
        self.zip_output = zip_output
        self.sample_rate = 60

    def export(self) -> int:
        base_name = os.path.splitext(self.export_path)[0]
        ld_path = base_name + ".ld"
        ldx_path = base_name + ".ldx"

        ld_writer = MotecLdWriter(ld_path, self.session_info)
        
        num_samples = len(self.vectorized_data['speed'])
        if num_samples == 0:
            return 0
            
        # Time
        time_data = np.arange(num_samples, dtype=np.float32) / self.sample_rate
        ld_writer.add_channel("Time", "s", time_data, data_type=3)

        # Speed (km/h)
        speed_kmh = np.asarray(self.vectorized_data['speed'], dtype=np.float32)
        ld_writer.add_channel("Speed", "km/h", speed_kmh, data_type=3)

        # RPM
        rpm = np.asarray(self.vectorized_data.get('engineRPM', np.zeros(num_samples)), dtype=np.float32)
        ld_writer.add_channel("Engine RPM", "rpm", rpm, data_type=3)

        # Throttle (DB might be 0-100 or 0-255 based on interpretation, force to 0-100)
        throttle_raw = np.asarray(self.vectorized_data.get('throttle', np.zeros(num_samples)), dtype=np.float32)
        if np.max(throttle_raw) > 1.0:
            throttle = (throttle_raw / 255.0) * 100.0
        else:
            throttle = throttle_raw * 100.0
        ld_writer.add_channel("Throttle Pos", "%", throttle, data_type=3)

        # Brake
        brake_raw = np.asarray(self.vectorized_data.get('brake', np.zeros(num_samples)), dtype=np.float32)
        if np.max(brake_raw) > 1.0:
            brake = (brake_raw / 255.0) * 100.0
        else:
            brake = brake_raw * 100.0
        ld_writer.add_channel("Brake Pos", "%", brake, data_type=3)

        # Gear
        gear = np.asarray(self.vectorized_data.get('gear', np.zeros(num_samples)), dtype=np.int16)
        ld_writer.add_channel("Gear", "", gear, data_type=1)

        # Suggested Gear
        s_gear = np.asarray(self.vectorized_data.get('suggested_gear', np.zeros(num_samples)), dtype=np.int16)
        ld_writer.add_channel("Suggested Gear", "", s_gear, data_type=1)

        # Steering
        steering_rad = np.asarray(self.vectorized_data.get('steering', np.zeros(num_samples)), dtype=np.float32)
        steering_deg = steering_rad * (180.0 / np.pi)
        ld_writer.add_channel("Steering Angle", "deg", steering_deg, data_type=3)

        # G-Forces (convert m/s^2 to G)
        g_surge = np.asarray(self.vectorized_data.get('g_force_surge', np.zeros(num_samples)), dtype=np.float32)
        ld_writer.add_channel("G Force Long", "G", g_surge / 9.80665, data_type=3)

        g_sway = np.asarray(self.vectorized_data.get('g_force_sway', np.zeros(num_samples)), dtype=np.float32)
        ld_writer.add_channel("G Force Lat", "G", g_sway / 9.80665, data_type=3)

        g_heave = np.asarray(self.vectorized_data.get('g_force_heave', np.zeros(num_samples)), dtype=np.float32)
        ld_writer.add_channel("G Force Vert", "G", g_heave / 9.80665, data_type=3)

        # Suspension Deflection (m to mm)
        for wheel in ['FL', 'FR', 'RL', 'RR']:
            key = f"suspHeight_{wheel}"
            susp_mm = np.asarray(self.vectorized_data.get(key, np.zeros(num_samples)), dtype=np.float32) * 1000.0
            ld_writer.add_channel(f"Susp Pos {wheel}", "mm", susp_mm, data_type=3)

        # Tire Temperatures
        for wheel in ['FL', 'FR', 'RL', 'RR']:
            key = f"tireTemp_{wheel}"
            temp = np.asarray(self.vectorized_data.get(key, np.zeros(num_samples)), dtype=np.float32)
            ld_writer.add_channel(f"Tyre Temp {wheel}", "C", temp, data_type=3)

        # Ground Surface
        surface = np.asarray(self.vectorized_data.get('ground_surface', np.zeros(num_samples)), dtype=np.int16)
        ld_writer.add_channel("Ground Surface", "", surface, data_type=1)

        ld_writer.write()

        # Build Laps Info
        lap_counts = np.asarray(self.vectorized_data.get('lap_count', np.zeros(num_samples)))
        timestamps = np.asarray(self.vectorized_data.get('timestamp', time_data))
        unique_laps = np.unique(lap_counts)
        
        laps_info = []
        fastest_lap_num = None
        fastest_duration = 999999.0
        
        for lap_num in unique_laps:
            idx = (lap_counts == lap_num)
            lap_times = timestamps[idx]
            if len(lap_times) > 0:
                duration = lap_times[-1] - lap_times[0]
                start_time = lap_times[0] - timestamps[0]
                
                if 10.0 < duration < fastest_duration:
                    fastest_duration = duration
                    fastest_lap_num = lap_num
                    
                laps_info.append({
                    'LapNumber': int(lap_num),
                    'StartTime': float(start_time),
                    'Duration': float(duration),
                    'IsFastest': False
                })
        
        for lap in laps_info:
            if lap['LapNumber'] == fastest_lap_num:
                lap['IsFastest'] = True

        ldx_writer = MotecLdxWriter(ldx_path, self.session_info, laps_info)
        ldx_writer.write()

        # Zip it
        if self.zip_output:
            zip_path = base_name + ".zip"
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.write(ld_path, os.path.basename(ld_path))
                zf.write(ldx_path, os.path.basename(ldx_path))

        return len(unique_laps)
