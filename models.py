import struct
from dataclasses import dataclass
from typing import Tuple, Optional

@dataclass
class GT7TelemetryPacket:
    # Magic Number
    magic: int
    
    # Position and Velocity
    position: Tuple[float, float, float]
    world_velocity: Tuple[float, float, float]
    rotation: Tuple[float, float, float]
    orientation_north: float
    angular_velocity: Tuple[float, float, float]
    
    # Engine and Chassis
    body_height: float
    engine_rpm: float
    iv_seed: int
    fuel_level: float
    fuel_capacity: float
    speed: float  # In m/s
    boost: float
    oil_pressure: float
    water_temp: float
    oil_temp: float
    tyre_temp: Tuple[float, float, float, float] # FL, FR, RL, RR
    
    # Session Information
    packet_id: int
    lap_count: int
    total_laps: int
    best_laptime: int
    last_laptime: int
    day_progression: int
    start_position: int
    pre_race_num_cars: int
    min_alert_rpm: int
    max_alert_rpm: int
    calc_max_speed: int
    
    # Controls and States
    flags: int
    gears: int
    throttle: int
    brake: int
    
    # Suspension and Wheels
    road_plane: Tuple[float, float, float]
    road_distance: float
    wheel_rps: Tuple[float, float, float, float]
    tyre_radius: Tuple[float, float, float, float]
    susp_height: Tuple[float, float, float, float]
    
    # Transmission
    clutch: float
    clutch_engagement: float
    clutch_rpm: float
    top_gear_ratio: float
    gear_ratios: Tuple[float, float, float, float, float, float, float, float]
    car_code: int
    
    # --- Extensions ---
    
    # Motion Packet (B)
    wheel_rotation: Optional[float] = None
    steering_angular_vel: Optional[float] = None
    sway: Optional[float] = None
    heave: Optional[float] = None
    surge: Optional[float] = None
    
    # Assistance Packet (~)
    throttle_filtered: Optional[int] = None
    brake_filtered: Optional[int] = None
    torque_vectors: Optional[Tuple[float, float, float, float]] = None
    energy_recovery: Optional[float] = None
    
    # Full Packet (C)
    surface_type: Optional[Tuple[str, str, str, str]] = None
    current_lap_time: Optional[int] = None
    wheel_steer_angle: Optional[float] = None
    wheel_base: Optional[float] = None
    car_category: Optional[str] = None
    
    @property
    def speed_kmh(self) -> float:
        return self.speed * 3.6
        
    @property
    def current_gear(self) -> int:
        return self.gears & 0x0F
        
    @property
    def recommended_gear(self) -> int:
        return (self.gears >> 4) & 0x0F
        
    @property
    def is_paused(self) -> bool:
        return (self.flags & (1 << 1)) != 0
        
    @property
    def in_gear(self) -> bool:
        return (self.flags & (1 << 3)) != 0
        
    @property
    def rev_limit_alert_active(self) -> bool:
        return (self.flags & (1 << 5)) != 0
        
    @property
    def tcs_active(self) -> bool:
        return (self.flags & (1 << 11)) != 0


def parse_telemetry_packet(data: bytes, packet_type: str) -> Optional[GT7TelemetryPacket]:
    """
    Parses a decrypted bytearray into a GT7TelemetryPacket object based on the packet_type.
    """
    if len(data) < 296:
        return None
        
    # Unpack Base Packet 'A' (296 bytes)
    # Update struct to use H (uint16) for flags, because total size before flags is 142.
    # Flags takes 2 bytes (142, 143), so gears is at 144 (0x90).
    format_A = '<i9ff3f2fI7f4fi2h3i5hH4B4f12f8f4f8fi'
    format_B = format_A + '4f'
    format_C = format_B + '4Bif4s24s'
    
    size = struct.calcsize(format_A)
    # Pad the data buffer to avoid unpack errors if the console sends 296 instead of 298.
    if len(data) < size:
        data = data.ljust(size, b'\x00')
        
    try:
        unpacked = struct.unpack(format_A, data[:size])
    except struct.error as e:
        print(f"Struct unpack error: {e}")
        return None
        
    packet = GT7TelemetryPacket(
        magic=unpacked[0],
        position=unpacked[1:4],
        world_velocity=unpacked[4:7],
        rotation=unpacked[7:10],
        orientation_north=unpacked[10],
        angular_velocity=unpacked[11:14],
        body_height=unpacked[14],
        engine_rpm=unpacked[15],
        iv_seed=unpacked[16],
        fuel_level=unpacked[17],
        fuel_capacity=unpacked[18],
        speed=unpacked[19],
        boost=unpacked[20],
        oil_pressure=unpacked[21],
        water_temp=unpacked[22],
        oil_temp=unpacked[23],
        tyre_temp=unpacked[24:28],
        packet_id=unpacked[28],
        lap_count=unpacked[29],
        total_laps=unpacked[30],
        best_laptime=unpacked[31],
        last_laptime=unpacked[32],
        day_progression=unpacked[33],
        start_position=unpacked[34],
        pre_race_num_cars=unpacked[35],
        min_alert_rpm=unpacked[36],
        max_alert_rpm=unpacked[37],
        calc_max_speed=unpacked[38],
        flags=unpacked[39],
        gears=unpacked[40],
        throttle=unpacked[41],
        brake=unpacked[42],
        road_plane=unpacked[44:47],
        road_distance=unpacked[47],
        wheel_rps=unpacked[48:52],
        tyre_radius=unpacked[52:56],
        susp_height=unpacked[56:60],
        clutch=unpacked[68],
        clutch_engagement=unpacked[69],
        clutch_rpm=unpacked[70],
        top_gear_ratio=unpacked[71],
        gear_ratios=unpacked[72:80],
        car_code=unpacked[80]
    )

    if packet_type in ['B', '~', 'C'] and len(data) >= 312:
        # Motion Extensions start at 0x124 (292)
        motion_format = '<fffff'
        motion_unpacked = struct.unpack(motion_format, data[292:312])
        packet.wheel_rotation = motion_unpacked[0]
        packet.steering_angular_vel = motion_unpacked[1]
        packet.sway = motion_unpacked[2]
        packet.heave = motion_unpacked[3]
        packet.surge = motion_unpacked[4]

    if packet_type in ['~', 'C'] and len(data) >= 344:
        if packet_type == '~':
            # Assist starts at 0x138 (312)
            assist_format = '<BBBB4fff'
            assist_unpacked = struct.unpack(assist_format, data[312:344])
            packet.throttle_filtered = assist_unpacked[0]
            packet.brake_filtered = assist_unpacked[1]
            packet.torque_vectors = assist_unpacked[4:8]
            packet.energy_recovery = assist_unpacked[8]

    if packet_type == 'C' and len(data) >= 352:
        # Full starts at 0x138 (312)
        full_format = '<4sif f24s'
        full_unpacked = struct.unpack(full_format, data[312:352])
        
        surface_bytes = full_unpacked[0]
        packet.surface_type = (chr(surface_bytes[0]), chr(surface_bytes[1]), chr(surface_bytes[2]), chr(surface_bytes[3]))
        
        packet.current_lap_time = full_unpacked[1]
        packet.wheel_steer_angle = full_unpacked[2]
        packet.wheel_base = full_unpacked[3]
        
        category_bytes = full_unpacked[4]
        packet.car_category = category_bytes.split(b'\x00')[0].decode('ascii', errors='ignore')

    return packet
