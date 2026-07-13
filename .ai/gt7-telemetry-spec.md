# SYSTEM PROMPT / SOFTWARE SPECIFICATION
## Project: Real-Time Telemetry Client for Gran Turismo 7 (Windows & macOS)

You are a **Principal Software Engineer** specializing in embedded systems, low-latency networking, and real-time cryptography. Your task is to generate a complete, modular, and production-ready Python 3.10+ project that reads, decrypts, parses, and visualizes real-time telemetry from **Gran Turismo 7 (PS4/PS5)**.

The project must support both **Windows 10/11** and **macOS (Intel/Apple Silicon)**. Follow the technical specifications, memory offsets, and architectural guidelines below. **Do not use placeholders, truncated listings, or `# TODO` comments.** Write every module in its entirety.

---

### 1. PROTOCOL & NETWORK SPECIFICATION

The physics engine of Gran Turismo 7 (GT7) exposes a diagnostic and motion-rig network interface via UDP [1, 2]. To optimize console performance, the game does not broadcast telemetry automatically; it uses a strict **subscription and keep-alive (heartbeat)** model [2, 6].

1. **The Highlander Principle (Single Client Restriction):** The console permits exactly **one** active telemetry session at a time [11]. The first client to register its heartbeat locks the stream to its IP address and packet format [11]. To switch packet formats or clients, the active client must stop sending heartbeats for **at least 16 seconds**, allowing the console's session socket to time out and release the lock [11].
2. **Ports:**
   - **Console Listener (Destination Port):** UDP port `33739` [7, 8].
   - **Client Listener (Local Port):** UDP port `33740` [1, 5, 8].
3. **Session Handshake & Heartbeat:**
   - The client initiates the stream by sending a single-byte UDP datagram (an ASCII character) to the console's IP address on port `33739` [5, 8, 9].
   - The selected character determines the telemetry packet structure returned by the console [5, 9]:
     - `'A'`: Base telemetry packet (296 bytes) [5, 10].
     - `'B'`: Motion/Chassis-oriented packet (316 bytes) [5, 11].
     - `'~'`: Technical assistance/Torque packet (344 bytes) [5, 10].
     - `'C'`: Full racing/Surface-type telemetry packet (368 bytes) [5, 9].
     - `'+'`: Simplified diagnostic heartbeat packet (148 bytes) [12, 13].
4. **Keep-Alive Requirements:**
   - Upon receiving a valid heartbeat, the console transmits telemetry at a nominal frequency of **60 Hz** (~16.67 ms interval) [1, 5, 8].
   - If the console does not receive a heartbeat, it automatically stops sending telemetry after exactly **1000 packets** (~16.6 seconds) [5, 9].
   - **Recommendation:** Implement an asynchronous background worker to send a heartbeat datagram every 1.5 seconds (or every 100 received packets) [7].

---

### 2. CRYPTOGRAPHIC PIPELINE (Salsa20 Decryption)

All telemetry payloads sent from the console are encrypted using the **Salsa20** stream cipher [1, 5, 9]. To process 60 frames per second without packet loss, the decryption pipeline must be highly optimized [6, 10].

1. **Symmetric Key (32 bytes):**
   - The base ASCII key is: `"Simulator Interface Packet GT7 ver 0.0"` [4, 9].
   - Truncate this key to exactly the first **32 characters** (32 bytes) [8, 9]:
     `b"Simulator Interface Packet GT7 "`
2. **Dynamic Nonce Derivation (8 bytes / 64 bits):**
   Every UDP packet contains a plaintext seed used to construct a unique, dynamic 8-byte nonce [8, 9]:
   - **Step 1 (Seed Extraction):** Extract 4 bytes from offsets `0x40` to `0x44` (decimal offsets 64 to 68) of the raw UDP payload [8, 9].
   - **Step 2 (iv1 Value):** Read these 4 bytes as a 32-bit unsigned integer in **Little-Endian** format, denoted as `iv1` [8, 9].
   - **Step 3 (iv2 Value):** Perform a bitwise XOR operation between `iv1` and a version-specific magic constant to calculate a second 32-bit integer, `iv2` [8, 9]:
     $$iv_2 = iv_1 \oplus \text{XOR\_CONSTANT}$$
     The magic constants are [4, 8, 9, 11]:
     - Packet Type `'A'`: `0xDEADBEAF` (Note: `BEAF`, not `BEEF`) [8, 9].
     - Packet Type `'B'`: `0xDEADBEEF` [11].
     - Packet Type `'~'` / `'C'`: `0x55FABB4F` [4, 9, 11].
   - **Step 4 (Nonce Assembly):** Pack both integers as Little-Endian bytes, concatenating `iv2` (first 4 bytes) and `iv1` (last 4 bytes) to form the 8-byte nonce [8, 9]:
     $$\text{Nonce} = \text{Bytes}(iv_2) \parallel \text{Bytes}(iv_1)$$
3. **Structural Verification (Integrity Check):**
   - Decrypt the payload using Salsa20 with the 32-byte key and the derived 8-byte nonce [8, 9].
   - Read the first 4 bytes of the decrypted buffer as a 32-bit Little-Endian integer [10].
   - The packet is valid **only if** this value equals `0x47375330` (the ASCII magic string `"G7S0"`) [10]. If this check fails, discard the packet as corrupt or misaligned [10].

---

### 3. COMPREHENSIVE TELEMETRY MEMORY MAP

Once decrypted, the packet is parsed using standard binary structures (Little-Endian alignment). Below are the exact offsets, data types, and scaling rules.

#### Base Layout: Packet "A" (296 Bytes) [5]
| Offset (Hex) | Data Type | Variable Name | Description & Scaling |
|---|---|---|---|
| `0x00` | `int32` | `magic` | Static validation signature (must be `0x47375330` / `"G7S0"`) [5, 8] |
| `0x04` | `float[3]` | `position` | Absolute Cartesian coordinates `[X, Y, Z]` on track (meters) [5] |
| `0x10` | `float[3]` | `worldVelocity` | Linear velocity vector `[Vx, Vy, Vz]` in global space (m/s) [5] |
| `0x1C` | `float[3]` | `rotation` | Pitch, Yaw, and Roll attitudes (radians, range: `[-1.0, 1.0]`) [5] |
| `0x28` | `float` | `orientationNorth` | Orientation relative to North (range: `[0.0, 1.0]`, where `1.0 = North`, `0.0 = South`) [5] |
| `0x2C` | `float[3]` | `angularVelocity` | Angular velocity vector around the center of mass (rad/s) [5] |
| `0x38` | `float` | `bodyHeight` | Instantaneous chassis height relative to the ground (meters) [5] |
| `0x3C` | `float` | `engineRPM` | Internal combustion engine RPM [5] |
| `0x40` | `uint32` | `ivSeed` | Plaintext seed used to derive the Salsa20 nonce [8, 9] |
| `0x44` | `float` | `fuelLevel` | Instantaneous fuel remaining in the tank (liters) [5] |
| `0x48` | `float` | `fuelCapacity` | Maximum fuel tank capacity (liters, range: `[0.0, 100.0]`) [5] |
| `0x4C` | `float` | `speed` | Vehicle speed in global space (m/s). Multiply by `3.6` for km/h [5]. |
| `0x50` | `float` | `boost` | Turbo manifold pressure (kPa). Relative pressure is calculated by offset `+100.0` [5]. |
| `0x54` | `float` | `oilPressure` | Engine oil hydraulic pressure (bar) [5] |
| `0x58` | `float` | `waterTemp` | Engine coolant temperature (ºC, static at `85.0` in physics engine) [5] |
| `0x5C` | `float` | `oilTemp` | Engine oil temperature (ºC, static at `110.0` in physics engine) [5] |
| `0x60` | `float[4]` | `tyreTemp` | Tire tread surface temperatures: `[FL, FR, RL, RR]` (ºC) [5] |
| `0x70` | `int32` | `packetId` | Monotonically increasing frame identifier (tick counter) [5, 13] |
| `0x74` | `int16` | `lapCount` | Current lap number [5] |
| `0x76` | `int16` | `totalLaps` | Total scheduled laps in the session [5] |
| `0x78` | `int32` | `bestLaptime` | Fast lap record in the session (milliseconds, `-1` if unset) [5] |
| `0x7C` | `int32` | `lastLaptime` | Final lap time of the last completed lap (milliseconds, `-1` if unset) [5] |
| `0x80` | `int32` | `dayProgression` | Sim time progression (milliseconds from midnight) [5] |
| `0x84` | `int16` | `startPosition` | Assigned starting grid position of the player's car [5] |
| `0x86` | `int16` | `preRaceNumCars` | Total number of cars registered on the grid [5] |
| `0x88` | `int16` | `minAlertRPM` | Shift alert lower threshold RPM [5] |
| `0x8A` | `int16` | `maxAlertRPM` | Maximum RPM (engine rev-limiter threshold) [5] |
| `0x8C` | `int16` | `calcMaxSpeed` | Theoretical maximum speed under current gear ratios (km/h) [5] |
| `0x8E` | `uint32` | `flags` | Bitmask of active driver assists and game states [5] |
| `0x92` | `uint8` | `gears` | Bit-packed current gear and recommended gear [5] |
| `0x93` | `uint8` | `throttle` | Unfiltered accelerator pedal input (`0` to `255`) [5] |
| `0x94` | `uint8` | `brake` | Unfiltered brake pedal input (`0` to `255`) [5] |
| `0x95` | `uint8` | `padding1` | Memory structural alignment padding (always `0x00`) [5] |
| `0x96` | `float[3]` | `roadPlane` | Perpendicular normal vector unit of the road plane under the car [5] |
| `0xA2` | `float` | `roadDistance` | Orthogonal distance of the car center to the middle track plane (meters) [5] |
| `0xA6` | `float[4]` | `wheelRPS` | Rotational velocity of each wheel: `[FL, FR, RL, RR]` (rad/s) [5] |
| `0xB6` | `float[4]` | `tyreRadius` | Dynamic rolling radius calculated per tire: `[FL, FR, RL, RR]` (meters) [5] |
| `0xC6` | `float[4]` | `suspHeight` | Dynamic suspension travel deflection per wheel: `[FL, FR, RL, RR]` (meters) [5] |
| `0xD6` | `float[8]` | `unknownFloats` | Reserved chassis physical inputs and lateral force values [5] |
| `0xF6` | `float` | `clutch` | Physical clutch input depth (`0.0` to `1.0`) [5] |
| `0xFA` | `float` | `clutchEngagement` | Actual clutch disk coupling coefficient (`0.0` to `1.0`) [5] |
| `0xFE` | `float` | `clutchRpm` | Clutch plate exit rotation speed (RPM) [5] |
| `0x102` | `float` | `topGearRatio` | Transmission ratio of the highest configured gear [5] |
| `0x106` | `float[8]` | `gearRatios` | Individual gear ratios for cars with up to 8-speed gearboxes [5] |
| `0x126` | `int32` | `carCode` | Unique identifier key mapping to the active car model [5, 11] |

#### Motion Packet "B" Extensions (316 Bytes Total) [5]
Appended directly after the `carCode` field [4, 5]:
| Offset (Hex) | Data Type | Variable Name | Description & Unit |
|---|---|---|---|
| `0x124` | `float` | `wheelRotation` | Cabin steering wheel physical angle (radians) [4, 5] |
| `0x128` | `float` | `steeringAngularVel` | Angular speed of steering wheel rotation (rad/s) [5] |
| `0x12C` | `float` | `sway` | Transverse (X-axis) linear acceleration of the sprung mass (m/s²) [5] |
| `0x130` | `float` | `heave` | Vertical (Y-axis) linear acceleration of the sprung mass (m/s²) [5] |
| `0x134` | `float` | `surge` | Longitudinal (Z-axis) linear acceleration of the sprung mass (m/s²) [5] |

#### Assistance Packet "~" Extensions (344 Bytes Total) [5]
Appended after the Motion Packet structure [4, 5]:
| Offset (Hex) | Data Type | Variable Name | Description & Unit |
|---|---|---|---|
| `0x138` | `uint8` | `throttleFiltered` | Throttle input smoothed/filtered by the TCS system [5] |
| `0x139` | `uint8` | `brakeFiltered` | Brake pressure modulated/filtered by the active ABS loop [5] |
| `0x13A` | `uint8` | `unknownUint8_1` | Reserved controller logic flag [5] |
| `0x13B` | `uint8` | `unknownUint8_2` | Reserved controller logic flag [5] |
| `0x13C` | `float[4]` | `torqueVectors` | Active traction torque applied per wheel: `[FL, FR, RL, RR]` (Newtons) [4, 5] |
| `0x14C` | `float` | `energyRecovery` | Hybrid/EV kinetic energy regeneration rate (Watts or Joules) [4, 5] |
| `0x150` | `float` | `unknownFloat` | Reserved for future engine expansion [5] |

#### Full Packet "C" Extensions (368 Bytes Total) [5]
Overwrites structures from offset `0x138` onward in Packet "~" [4, 5]:
| Offset (Hex) | Data Type | Variable Name | Description & Scaling |
|---|---|---|---|
| `0x138` | `char[4]` | `surfaceType` | Physical ground surface texture code per tire `[FL, FR, RL, RR]` [4, 5]:<br>`'T'` (Tarmac), `'C'` (Curb/Kerb), `'D'` (Dirt), `'G'` (Grass), `'S'` (Sand), `'s'` (Snow) |
| `0x13C` | `int32` | `currentLap` | High-precision time elapsed in the current lap (milliseconds) [4, 5] |
| `0x140` | `float` | `wheelSteerAngle` | Physical alignment angle of front steering wheels relative to chassis (radians) [4, 5] |
| `0x148` | `float` | `wheelBase` | Geometric wheelbase distance of the active car (meters) [5] |
| `0x14C` | `char[4]` | `carCategory` | Null-terminated string indicating FIA homologation category (e.g., `GR3\0`, `GR4\0`) [5] |
| `0x150` | `char[24]` | `tailSignature` | Packet footer starting with class keys like `"TCTC"` or `"TTTT"`, ending in static string `"GR3."` (`0x47523300`) [12, 13] |

---

### 4. BITWISE & NIBBLE DECODING

#### Simulator State Flags (Offset `0x8E`)
Drivers assists, engine status, and UI states are packed into a single 32-bit unsigned integer `flags` [5]. Extract active flags using bitwise masking [9]:
```python
is_active = (flags & (1 << bit_id)) != 0
```
- **Bit 0:** `CarOnTrack` – Car is spawned on track, engine is on, and physics simulation is running [9].
- **Bit 1:** `Paused` – Game is paused [9].
- **Bit 2:** `LoadingOrProcessing` – UI/graphic load or transition is processing [9].
- **Bit 3:** `InGear` – Clutch is engaged, transmitting drivetrain power [9].
- **Bit 4:** `HasTurbo` – Engine is fitted with a turbocharger [9].
- **Bit 5:** `RevLimitAlertActive` – RPM has exceeded limits, triggering shift light indicators [9].
- **Bit 6:** `HandbrakeActive` – Handbrake is pulled [9].
- **Bit 7:** `LightsActive` – Standard headlights are switched on [9].
- **Bit 8:** `HighBeamsActive` – High beam headlights are switched on [9].
- **Bit 9:** `LowBeamsActive` – Low beam headlights are switched on [9].
- **Bit 10:** `ASMActive` – Active Stability Management is actively correcting car attitude [9].
- **Bit 11:** `TCSActive` – Traction Control System is actively limiting wheel slip [9].

#### Transmission Gears Byte (Offset `0x92`)
The transmission byte `gears` contains both the engaged gear and recommended gear packed as 4-bit nibbles [5, 9].
- **Engaged Gear (Bits 0-3):** Read the lower nibble [9].
  $$\text{CurrentGear} = \text{gears} \ \& \ \text{0x0F}$$
  - Values: `0` (Neutral/N), `1-8` (Forward gears), `15` (`0x0F` - Reverse/R) [9].
- **Recommended Gear (Bits 4-7):** Shift right by 4 bits and mask [9].
  $$\text{RecommendedGear} = (\text{gears} \gg 4) \ \& \ \text{0x0F}$$
  - Values: `15` (`0x0F`) indicates no recommended gear (assist inactive) [9].

---

### 5. PRODUCTION ARCHITECTURE (Concurreny Pattern)

To avoid losing frames (*packet drops*) over Wi-Fi, the program **must** implement a multi-threaded **Producer-Consumer** architecture with an decoupled I/O buffer [6, 10, 16].

```
┌─────────────────────────────────┐
│     GT7 PlayStation Console     │
└────────────────┬────────────────┘
                 │ 60Hz UDP Telemetry (Port 33740)
                 ▼
┌─────────────────────────────────┐
│     Network Capture Thread      │ (Decoupled I/O Thread)
│      (OS UDP Socket Buffer)     │
└────────────────┬────────────────┘
                 │ High-Priority queue.Queue
                 ▼
┌─────────────────────────────────┐
│   Decryption & Parser Thread    │ (Salsa20 Decryption Pipeline)
└────────────────┬────────────────┘
                 │ Decoded Dictionary/Object
                 ▼
┌─────────────────────────────────┐
│      Main UI/CLI Terminal       │ (60 FPS Non-blocking Loop)
└─────────────────────────────────┘
```

1. **Network Capture Thread (I/O Producer):**
   - Bind socket to `0.0.0.0` port `33740` [5, 8]. On Windows/macOS, set the socket buffer size explicitly to at least `4MB` (`socket.SO_RCVBUF`) to buffer network spikes [16, 18].
   - **Crucial Rule:** This thread must only listen to the socket (`socket.recvfrom`) and immediately push the raw datagrams into a thread-safe memory queue alongside a microsecond-precision timestamp [18, 20]. Doing anything else in this thread will result in immediate packet drops [6, 16].
2. **Decryption & Parsing Thread (Consumer Thread):**
   - Pop raw buffers from the memory queue. Extract the IV seed from offsets `0x40-0x44`, perform Salsa20 decryption, validate using magic number `"G7S0"`, and unpack binary buffers into strongly-typed objects [8, 9, 10].
3. **Heartbeat Worker Thread (Interval Dispatcher):**
   - Spawn an independent async task that writes a single ASCII character (such as `'C'`) to the console's port `33739` every 1.5 seconds to prevent stream suspension [5, 7, 9].

---

### 6. SOFTWARE IMPLEMENTATION

Generate a modular, production-ready, fully commented Python codebase. Organize the project into the following structural layout:

#### File: `requirements.txt`
```text
pycryptodome>=3.15.0
colorama>=0.4.6
```

#### File: `models.py`
Provide Python classes mapping the complete layouts using `struct.unpack` or `ctypes.Structure`. Use Little-Endian format specifiers (e.g., `<f`, `<i`, `<H`). Implement proper validation routines.

#### File: `crypto.py`
Implement high-performance Salsa20 decryption. Leverage `Crypto.Cipher.Salsa20` from `pycryptodome` for hardware-accelerated performance. Do not use unoptimized pure Python loops unless absolutely necessary as a fallback.

#### File: `client.py`
Implement the multi-threaded consumer-producer pattern. Maintain strict exception handling (e.g., handling dropped packets, timeout reconnections, network buffer resizing).

#### File: `main.py`
Create a CLI application. Use `colorama` for a beautiful, clean dashboard terminal interface that updates in place without flickering. Implement:
- Clear step-by-step setup guides (PlayStation IP config, firewall ports).
- Real-time terminal reporting of parameters (Vehicle velocity, Gear state, RPM, throttle/brake, high-resolution lap times, tire surface types).
- Automatic lap logging, saving telemetry outputs as clean CSV/JSON arrays on completed laps.

Make the generated system resilient and easy to start!

---

### 7. TRACK DETECTION HEURISTICS
To map raw telemetry to a physical track without explicit API support, the system correlates the final lap `distance` (meters) against a known database (`data/tracks.json`).
- **Hard Filter**: The system MUST reject any track match where the absolute difference between `total_dist` and `track.length_m` is strictly greater than `200` meters.
- **Scoring Weights**: Track detection relies primarily on minimizing physical length differences (heavy penalty for deviation), followed by elevation changes (medium penalty), and corner count differences (low penalty).
