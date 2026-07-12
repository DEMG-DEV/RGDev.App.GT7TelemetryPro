import socket
import time
import struct

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', 33739))
    print("Fake PS4 listening on 33739...")
    
    last_addr = None
    
    while True:
        try:
            sock.settimeout(1.0)
            data, addr = sock.recvfrom(1024)
            if data == b'C':
                print(f"Received heartbeat from {addr}")
                last_addr = (addr[0], 33740)
        except socket.timeout:
            pass
            
        if last_addr:
            # Send dummy packet
            # We don't have the key easily here, but we can just send gibberish or a valid encrypted packet.
            # Wait, if we send gibberish, `decrypt_telemetry` will fail or `parse_telemetry_packet` will return None.
            # But the network loop DOES NOT CARE!
            # It just does `raw_queue.put_nowait(data)` and updates `last_packet_time`!
            # So the UI should show "Connected to 127.0.0.1"!
            sock.sendto(b'DUMMY_DATA' * 30, last_addr)
            time.sleep(1/60.0)

if __name__ == '__main__':
    main()
