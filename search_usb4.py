#!/usr/bin/env python3
import struct

with open('/Users/bill/dev/SmartHome/Airnut/SDCard/NO NAME/OTA_BackUp.bin', 'rb') as f:
    data = f.read()

# 1. Analyze USB OTG FS code area (around 0x16820)
print("=== USB OTG FS code area (0x16800 - 0x16900) ===")
# Look for strings near USB OTG FS references
for off in [0x16800, 0x16880, 0x168D0]:
    chunk = data[off:off+64]
    strings = chunk.split(b'\x00')
    for s in strings:
        s = s.strip()
        if len(s) >= 3:
            try:
                text = s.decode('ascii')
                if text.isprintable():
                    print(f"  0x{off:05x}: '{text}'")
            except:
                pass

# 2. Look at USB OTG HS code area (around 0x2a6a8)
print("\n=== USB OTG HS code area (0x2A680 - 0x2A720) ===")
for off in range(0x2A680, 0x2A720, 16):
    hex_str = data[off:off+16].hex()
    ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[off:off+16])
    print(f"  0x{off:05x}: {hex_str}  {ascii_str}")

# 3. Search for VBUS-related patterns
# On STM32F4, VBUS sensing is done through GPIO
# Look for any VBUS strings
print("\n=== Search for VBUS, vbus, D+, D- strings ===")
for keyword in [b'VBUS', b'vbus', b'Vbus', b'D+', b'D-', b'USBD', b'CDC', b'HID']:
    pos = 0
    while True:
        idx = data.find(keyword, pos)
        if idx == -1:
            break
        start = max(0, idx - 10)
        end = min(len(data), idx + 30)
        context = data[start:end]
        ascii_ctx = ''.join(chr(b) if 32 <= b < 127 else '.' for b in context)
        print(f"  0x{idx:06x}: '{keyword.decode()}' context: {ascii_ctx}")
        pos = idx + 1

# 4. Look for the USB OTG FS global interrupt handler
# USB OTG FS IRQ = 67 (0x43)
# Check vector table at offset 0x00
print("\n=== Vector table entries for USB interrupts ===")
# IRQ 67 (USB_OTG_FS) at offset 4*67 = 268 = 0x10C
usb_fs_irq = struct.unpack('<I', data[0x10C:0x110])[0]
print(f"  USB_OTG_FS IRQ handler: 0x{usb_fs_irq:08X}")
# IRQ 77 (USB_OTG_HS) at offset 4*77 = 308 = 0x134  
usb_hs_irq = struct.unpack('<I', data[0x134:0x138])[0]
print(f"  USB_OTG_HS IRQ handler: 0x{usb_hs_irq:08X}")

# 5. Look for USB initialization strings
print("\n=== USB init/config strings near code area ===")
for keyword in [b'USB AIRNUT', b'Mass Storage', b'USB BACKUP', b'USB LOG', b'USB Indication', b'MSC']:
    idx = data.find(keyword)
    if idx >= 0:
        # Find flash address
        flash_addr = 0x08000000 + idx
        print(f"  '{keyword.decode()}' at file 0x{idx:06x} (flash 0x{flash_addr:08X})")

# 6. Search for the USB version print function context
# "USB AIRNUT1S VERSION" is likely printed via debug UART or USB CDC
print("\n=== Context around USB VERSION string ===")
idx = data.find(b'USB AIRNUT1S VERSION')
if idx >= 0:
    # Look at 256 bytes before the string for code that references it
    code_before = data[max(0,idx-256):idx]
    # Find the last null byte to identify the previous string boundary
    last_null = code_before.rfind(b'\x00')
    if last_null >= 0:
        code_start = max(0, idx-256) + last_null + 1
        code_chunk = data[code_start:idx]
        print(f"  Code/data before USB VERSION (0x{code_start:06x} - 0x{idx:06x}):")
        hex_str = code_chunk[:64].hex()
        print(f"    {hex_str}")
