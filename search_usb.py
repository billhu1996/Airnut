#!/usr/bin/env python3
import struct

with open('/Users/bill/dev/SmartHome/Airnut/SDCard/NO NAME/OTA_BackUp.bin', 'rb') as f:
    data = f.read()

print("=== Standalone 'USB' occurrences ===")
pos = 0
while True:
    idx = data.find(b'USB', pos)
    if idx == -1:
        break
    before = data[idx-1] if idx > 0 else 0
    after = data[idx+3] if idx+3 < len(data) else 0
    is_standalone = (before == 0 or before > 127) and (after == 0 or after > 127 or after < 0x20)
    if is_standalone:
        context_before = data[max(0,idx-8):idx]
        context_after = data[idx+3:idx+11]
        print(f"  0x{idx:06x}: before=0x{before:02x} after=0x{after:02x}")
        print(f"    hex context: {context_before.hex()} [USB] {context_after.hex()}")
    pos = idx + 1

print()
print("=== Screen/Display related strings ===")
# Look for show_screen, Screen Change, LED Screen, etc.
for keyword in [b'show_screen', b'Screen Change', b'LED Screen', b'Screen']:
    pos = 0
    while True:
        idx = data.find(keyword, pos)
        if idx == -1:
            break
        start = max(0, idx - 4)
        end = min(len(data), idx + len(keyword) + 4)
        print(f"  0x{idx:06x}: {data[start:end]}")
        pos = idx + 1

print()
print("=== Looking for short display strings (2-5 chars, null-terminated) near USB strings ===")
# The LED screen likely uses short strings
# Check around the USB-related string areas for short displayable strings
for area_start, area_end, label in [
    (0x323D0, 0x32420, "USB VERSION area"),
    (0x329D0, 0x32A20, "USB BACKUP LOG area"),
    (0x33700, 0x337B0, "USB LOG/Indication area"),
    (0x339A0, 0x339E0, "MSC Interface area"),
    (0x34370, 0x343C0, "MSC Config/gesture area"),
]:
    print(f"\n--- {label} ---")
    chunk = data[area_start:area_end]
    # Find null-terminated strings
    parts = chunk.split(b'\x00')
    for p in parts:
        p = p.strip()
        if len(p) >= 2 and len(p) <= 20:
            try:
                text = p.decode('ascii')
                if text.isprintable():
                    print(f"  '{text}' (len={len(text)})")
            except:
                try:
                    text = p.decode('gbk')
                    print(f"  '{text}' (GBK, len={len(text)})")
                except:
                    pass
