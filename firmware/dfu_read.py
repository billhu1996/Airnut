#!/usr/bin/env python3
"""STM32 DfuSe 只读读取工具（基于 ST AN3156 协议）

只执行 UPLOAD（读取）操作，绝不执行擦除/下载/解锁，安全无损。

用法:
  python3 dfu_read.py ob                     # 读 Option Bytes（检查读保护 RDP）
  python3 dfu_read.py info                   # 读 Unique ID + Flash 容量
  python3 dfu_read.py flash <addr> <size> <outfile>   # 读指定 Flash 区域
  例: python3 dfu_read.py flash 0x08000000 0x100000 full_dump.bin   # 整片 1MB

实测要点（空气果1S / STM32F407VG 内置 bootloader）:
  1. SET_ADDRESS 命令完成后必须先发 DFU_ABORT 回到 dfuIDLE，
     否则后续 DFU_UPLOAD 全部被 STALL 拒绝；
  2. 该 bootloader 不开放系统存储区（0x1FFFxxxx，含 Option Bytes /
     Unique ID / Flash 容量寄存器）的 DFU 读取，ob/info 模式会返回
     "命令回显"（首字节 0x21 + 请求地址），不是真实数据；
     判断 RDP 只能靠"用户 Flash 能否读出"间接确认（RDP L1 拒绝读，
     L2 连 DFU 都不会枚举）；
  3. 用户 Flash（0x08000000 起）读取正常，1KB 块约 1ms，整片 1MB 约 2 秒。

依赖: python3 + pyusb + libusb (brew install libusb; pip3 install pyusb)
"""
import struct
import sys
import time

import usb.core
import usb.util

VID, PID = 0x0483, 0xDF11

# DFU 类请求 (bRequest)
DFU_DETACH, DFU_DNLOAD, DFU_UPLOAD = 0, 1, 2
DFU_GETSTATUS, DFU_CLRSTATUS, DFU_GETSTATE, DFU_ABORT = 3, 4, 5, 6

# DfuSe 命令（通过 DNLOAD wValue=0 下发）
DFUSE_SET_ADDRESS = 0x21

STATE_NAMES = {
    0: "appIDLE", 1: "appDETACH", 2: "dfuIDLE", 3: "dfuDNLOAD_SYNC",
    4: "dfuDNBUSY", 5: "dfuDNLOAD_IDLE", 6: "dfuMANIFEST_SYNC",
    7: "dfuMANIFEST", 8: "dfuMANIFEST_WAIT_RESET", 9: "dfuUPLOAD_IDLE",
    10: "dfuERROR",
}


def find_device():
    dev = usb.core.find(idVendor=VID, idProduct=PID)
    if dev is None:
        sys.exit("未找到 STM32 DFU 设备 (0483:df11)，请确认已进入 DFU 模式")
    try:
        dev.set_configuration()
    except Exception:
        pass  # macOS 下通常已配置，忽略
    return dev


def get_status(dev):
    """GETSTATUS -> (status, poll_timeout_ms, state)"""
    r = dev.ctrl_transfer(0xA1, DFU_GETSTATUS, 0, 0, 6, timeout=2000)
    status = r[0]
    poll = r[1] | (r[2] << 8) | (r[3] << 16)
    state = r[4]
    return status, poll, state


def ensure_idle(dev):
    """确保设备处于 dfuIDLE；若在 ERROR 态则 CLRSTATUS"""
    try:
        _, _, state = get_status(dev)
    except Exception:
        dev.ctrl_transfer(0x21, DFU_CLRSTATUS, 0, 0, None, timeout=2000)
        _, _, state = get_status(dev)
    if state == 10:  # dfuERROR
        dev.ctrl_transfer(0x21, DFU_CLRSTATUS, 0, 0, None, timeout=2000)
        _, _, state = get_status(dev)
    if state != 2:
        # 发 ABORT 尝试回到 idle
        dev.ctrl_transfer(0x21, DFU_ABORT, 0, 0, None, timeout=2000)
        _, _, state = get_status(dev)
    if state != 2:
        sys.exit(f"设备状态异常: {STATE_NAMES.get(state, state)}，无法继续")


def set_address(dev, addr):
    """DfuSe SET_ADDRESS 命令，随后轮询至 dfuDNLOAD_IDLE，
    再 ABORT 回 dfuIDLE（否则后续 UPLOAD 会被 STALL）。"""
    cmd = bytes([DFUSE_SET_ADDRESS]) + struct.pack("<I", addr)
    dev.ctrl_transfer(0x21, DFU_DNLOAD, 0, 0, cmd, timeout=2000)
    for _ in range(50):
        status, poll, state = get_status(dev)
        if status != 0:
            sys.exit(f"SET_ADDRESS 失败: status={status} state={STATE_NAMES.get(state)}")
        if state == 5:  # dfuDNLOAD_IDLE
            break
        time.sleep(max(poll, 1) / 1000.0)
    else:
        sys.exit("SET_ADDRESS 后等待 dfuDNLOAD_IDLE 超时")
    # 关键：ABORT 回 dfuIDLE，upload 才会被接受
    dev.ctrl_transfer(0x21, DFU_ABORT, 0, 0, None, timeout=2000)
    get_status(dev)


def upload(dev, addr, size, block_size=1024):
    """从 addr 读取 size 字节"""
    ensure_idle(dev)
    set_address(dev, addr)
    data = bytearray()
    block = 2  # DfuSe 数据块编号从 2 开始（0=命令，1=保留）
    while len(data) < size:
        want = min(block_size, size - len(data))
        chunk = dev.ctrl_transfer(0xA1, DFU_UPLOAD, block, 0, want, timeout=5000)
        if len(chunk) == 0:
            break  # 短包：设备认为区域结束
        data.extend(chunk)
        block += 1
        if len(chunk) < want:
            print(f"注意: 在 {len(data)} 字节处收到短包（区域结束）")
            break
    # 回到空闲态
    try:
        dev.ctrl_transfer(0x21, DFU_ABORT, 0, 0, None, timeout=2000)
        get_status(dev)
    except Exception:
        pass
    return bytes(data)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    mode = sys.argv[1]
    dev = find_device()

    if mode == "ob":
        d = upload(dev, 0x1FFFC000, 16)
        print(f"Option Bytes (0x1FFFC000): {d.hex()}")
        rdp = d[0]
        lvl = {0xAA: "0 (无保护)", 0x55: "1 (调试/读保护)"}.get(rdp, "2 (永久保护)")
        print(f"RDP 字节 = 0x{rdp:02X} -> 读保护等级 {lvl}")
    elif mode == "info":
        uid = upload(dev, 0x1FFF7A10, 12)
        print(f"Unique ID (0x1FFF7A10): {uid.hex()}")
        flash = upload(dev, 0x1FFF7A22, 2)
        print(f"Flash 容量 (0x1FFF7A22): {struct.unpack('<H', flash)[0]} KB")
    elif mode == "flash":
        addr = int(sys.argv[2], 16)
        size = int(sys.argv[3], 16)
        out = sys.argv[4]
        print(f"读取 0x{addr:08X} .. +0x{size:X} ...")
        t0 = time.time()
        d = upload(dev, addr, size)
        with open(out, "wb") as f:
            f.write(d)
        print(f"完成: {len(d)} 字节 -> {out} ({time.time()-t0:.1f}s)")
        if len(d) < size:
            print(f"警告: 只读到 {len(d)}/{size} 字节")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
