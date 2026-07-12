import struct
from typing import Optional, Tuple
from Crypto.Cipher import Salsa20

# 32-byte key derived from "Simulator Interface Packet GT7 ver 0.0"
SALSA20_KEY = b"Simulator Interface Packet GT7 v"

# XOR Magic Constants based on packet type
XOR_CONSTANTS = {
    'A': 0xDEADBEAF,
    'B': 0xDEADBEEF,
    '~': 0x55FABB4F,
    'C': 0x55FABB4F
}

# The validation magic number "G7S0"
MAGIC_VALIDATION = 0x47375330
MAGIC_VALIDATION_LE = 0x30533747 # "G7S0" interpreted as Little-Endian uint32

def derive_nonce(iv_seed: int, xor_const: int) -> bytes:
    """
    Derives the 8-byte Salsa20 nonce using the iv_seed and a magic constant.
    """
    iv1 = iv_seed
    iv2 = iv1 ^ xor_const
    return struct.pack('<II', iv2, iv1)

def decrypt_telemetry(raw_data: bytes, packet_type: str) -> Optional[bytes]:
    """
    Decrypts the raw UDP packet using Salsa20 and validates the payload.
    Returns the decrypted bytes if valid, or None if invalid.
    """
    if len(raw_data) < 68:
        return None
        
    seed_bytes = raw_data[64:68]
    try:
        iv_seed = struct.unpack('<I', seed_bytes)[0]
    except struct.error:
        return None
        
    # Standard constants + PS4 Fallbacks
    XOR_CONSTS_TO_TRY = [
        XOR_CONSTANTS.get(packet_type, XOR_CONSTANTS['A']),
        0xDEADBEEF, # Common PS4 / GT Sport fallback
        0x55FABB4F,
        0xDEADBEAF
    ]
    
    for xor_const in XOR_CONSTS_TO_TRY:
        nonce = derive_nonce(iv_seed, xor_const)
        try:
            cipher = Salsa20.new(key=SALSA20_KEY, nonce=nonce)
            decrypted_data = cipher.decrypt(raw_data)
            
            if len(decrypted_data) >= 4:
                magic_val = struct.unpack('<I', decrypted_data[:4])[0]
                if magic_val in (MAGIC_VALIDATION, MAGIC_VALIDATION_LE):
                    return decrypted_data
        except ValueError:
            continue
            
    return None
