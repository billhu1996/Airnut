#!/usr/bin/env python3
with open('/Users/bill/dev/SmartHome/Airnut/SDCard/NO NAME/OTA_BackUp.bin', 'rb') as f:
    data = f.read()

# 1. Look at Screen Change Flag context - what screens exist?
print("=== Screen Change Flag area (0x33040 - 0x330A0) ===")
chunk = data[0x33040:0x330A0]
parts = chunk.split(b'\x00')
for p in parts:
    p = p.strip()
    if len(p) >= 2:
        try:
            text = p.decode('gbk', errors='replace')
            if text.strip():
                print(f"  '{text}'")
        except:
            pass

# 2. Look at show_screen context
print("\n=== show_screen area (0x34310 - 0x34360) ===")
chunk = data[0x34310:0x34360]
parts = chunk.split(b'\x00')
for p in parts:
    p = p.strip()
    if len(p) >= 2:
        try:
            text = p.decode('gbk', errors='replace')
            if text.strip():
                print(f"  '{text}'")
        except:
            pass

# 3. Look at ALL screen-related strings in order
print("\n=== All screen/display related strings in firmware order ===")
for keyword in [b'screen', b'Screen', b'SCREEN', b'show_', b'LED', b'display', b'bitmap']:
    pos = 0x30000  # string table area only
    while True:
        idx = data.find(keyword, pos)
        if idx == -1 or idx > 0x35000:
            break
        # Get the null-terminated string containing this
        start = idx
        while start > 0 and data[start-1] != 0:
            start -= 1
        end = idx
        while end < len(data) and data[end] != 0:
            end += 1
        s = data[start:end]
        try:
            text = s.decode('ascii')
            if text.isprintable() and len(text) > 3:
                print(f"  0x{start:06x}: '{text}'")
        except:
            try:
                text = s.decode('gbk', errors='replace')
                print(f"  0x{start:06x}: '{text}' (GBK)")
            except:
                pass
        pos = idx + len(keyword)

# 4. Look for bitmap/font data - search for patterns that could be LED pixel data
# LED displays typically use 1-bit-per-pixel bitmaps
# "USB" on a small LED matrix (e.g., 16x16 or 32x8) would be small byte arrays
print("\n=== Looking for potential bitmap data near 'USB Indication' ===")
# USB Indication at 0x33790
# Check for structured data nearby
for off in range(0x33780, 0x33810, 16):
    hex_str = data[off:off+16].hex()
    ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[off:off+16])
    print(f"  0x{off:06x}: {hex_str}  {ascii_str}")

# 5. Check the Snake game - it has a display, so screen rendering code exists
print("\n=== Snake Task/Flag area ===")
chunk = data[0x34390:0x343C0]
parts = chunk.split(b'\x00')
for p in parts:
    p = p.strip()
    if len(p) >= 2:
        try:
            text = p.decode('gbk', errors='replace')
            if text.strip():
                print(f"  '{text}'")
        except:
            pass

# 6. Look for all wake-up sources
print("\n=== Wake up sources (near 唤醒信号来源) ===")
idx = data.find(b'\xba\xc0\xd0\xc5\xd0\xc5\xba\xc5\xc0\xb4\xd4\xb4')  # GBK for 唤醒信号来源
if idx == -1:
    # Search by ASCII pattern
    idx = data.find('唤醒信号来源'.encode('gbk'))
if idx >= 0:
    print(f"  Found at 0x{idx:06x}")
    # Show context around it
    chunk = data[max(0,idx-200):idx+100]
    parts = chunk.split(b'\x00')
    for p in parts:
        p = p.strip()
        if len(p) >= 3:
            try:
                text = p.decode('gbk', errors='replace')
                if text.strip():
                    print(f"  '{text}'")
            except:
                pass
