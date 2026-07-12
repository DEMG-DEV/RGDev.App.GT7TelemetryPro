import struct
from typing import Optional, Tuple
from Crypto.Cipher import Salsa20

# 32-byte key derived from "Simulator Interface Packet GT7 ver 0.0"
SALSA20_KEY = b"Simulator Interface Packet GT7 "

# XOR Magic Constants based on packet type
XOR_CONSTANTS = {
    'A': 0xDEADBEAF,
    'B': 0xDEADBEEF,
    '~': 0x55FABB4F,
    'C': 0x55FABB4F
}

# The validation magic number "G7S0"
MAGIC_VALIDATION = 0x47375330

def derive_nonce(iv_seed: int, packet_type: str) -> bytes:
    """
    Derives the 8-byte Salsa20 nonce using the iv_seed and packet type magic constant.
    """
    xor_const = XOR_CONSTANTS.get(packet_type, XOR_CONSTANTS['A'])
    
    iv1 = iv_seed
    iv2 = iv1 ^ xor_const
    
    # Pack as Little-Endian: iv2 (4 bytes) followed by iv1 (4 bytes)
    nonce = struct.pack('<II', iv2, iv1)
    return nonce

def decrypt_telemetry(raw_data: bytes, packet_type: str) -> Optional[bytes]:
    """
    Decrypts the raw UDP packet using Salsa20 and validates the payload.
    Returns the decrypted bytes if valid, or None if invalid.
    """
    # Packets are at least 0x44 (68) bytes long to contain the seed
    if len(raw_data) < 68:
        return None
        
    # Step 1: Extract 4-byte seed from offset 0x40 (64)
    seed_bytes = raw_data[64:68]
    try:
        iv_seed = struct.unpack('<I', seed_bytes)[0]
    except struct.error:
        return None
        
    # Step 2 & 3: Derive nonce
    nonce = derive_nonce(iv_seed, packet_type)
    
    # Step 4: Decrypt payload
    try:
        cipher = Salsa20.new(key=SALSA20_KEY, nonce=nonce)
        decrypted_data = cipher.decrypt(raw_data)
    except ValueError:
        return None
        
    # Step 5: Structural Validation
    if len(decrypted_data) >= 4:
        magic_val = struct.unpack('<I', decrypted_data[:4])[0]
        if magic_val == MAGIC_VALIDATION:
            return decrypted_data
            
    return None
