#!/usr/bin/env python3
with open('/Users/bill/dev/SmartHome/Airnut/SDCard/NO NAME/OTA_BackUp.bin', 'rb') as f:
    data = f.read()

# 1. Look at the code section for USB-related instruction patterns
# The code section is 0x2000 - 0x34E18
# Search for USB OTG peripheral register addresses
# STM32F407 USB OTG FS base: 0x50000000
# STM32F407 USB OTG HS base: 0x40040000
# STM32F407 GPIO for USB VBUS detection: typically PA12 (USB_FS_VBUS) or PB13 (USB_HS_VBUS)

import struct

print("=== Search for STM32 USB peripheral addresses in code ===")
for name, addr in [("USB_OTG_FS", 0x50000000), ("USB_OTG_HS", 0x40040000), 
                    ("USB_OTG_FS_DEV", 0x50000800), ("USB_OTG_HS_DEV", 0x40040800)]:
    target = struct.pack('<I', addr)
    pos = 0x2000
    count = 0
    while pos < 0x34E18:
        idx = data.find(target, pos)
        if idx == -1 or idx > 0x34E18:
            break
        count += 1
        if count <= 3:
            print(f"  {name} (0x{addr:08X}) referenced at code offset 0x{idx:x}")
        pos = idx + 1
    if count > 3:
        print(f"  ... and {count-3} more references")
    if count == 0:
        print(f"  {name}: no references found")

# 2. Search for USB-related GPIO pins
# PA11/PA12 = USB FS D-/D+
# PB12/PB13/PB14/PB15 = USB HS
print("\n=== Search for USB pin configurations ===")
# GPIOA = 0x40020000, GPIOB = 0x40020400
for name, addr in [("GPIOA", 0x40020000), ("GPIOB", 0x40020400), ("GPIOC", 0x40020800)]:
    target = struct.pack('<I', addr)
    pos = 0x2000
    count = 0
    while pos < 0x34E18:
        idx = data.find(target, pos)
        if idx == -1 or idx > 0x34E18:
            break
        count += 1
        pos = idx + 1
    print(f"  {name} (0x{addr:08X}): {count} references in code")

# 3. Look for the complete list of task names in order (they're likely in a task table)
print("\n=== All Task names in firmware order ===")
pos = 0x30000
task_list = []
while pos < 0x35000:
    idx = data.find(b'Task', pos)
    if idx == -1:
        break
    # Find the start of this null-terminated string
    start = idx
    while start > 0 and data[start-1] != 0:
        start -= 1
    end = idx + 4
    s = data[start:end]
    try:
        text = s.decode('ascii')
        if text.isprintable() and 'Task' in text and len(text) < 30:
            if text not in task_list:
                task_list.append(text)
                print(f"  0x{start:06x}: '{text}'")
    except:
        pass
    pos = idx + 4

# 4. Search for "USB" as a 3-byte display string with null terminator
# It could be in a bitmap font table
print("\n=== Search for 'USB\\x00' as display string ===")
pos = 0
while True:
    idx = data.find(b'USB\x00', pos)
    if idx == -1:
        break
    # Check context
    before = data[idx-1] if idx > 0 else 0xFF
    print(f"  0x{idx:06x}: before=0x{before:02x}, context={data[max(0,idx-4):idx+8].hex()}")
    pos = idx + 1

# 5. Look at the complete Key Task area for button handling logic
print("\n=== Key Task full context (0x34340 - 0x34400) ===")
chunk = data[0x34340:0x34400]
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
