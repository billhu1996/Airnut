# 空气果1S DFU 整片 Flash Dump 分析报告

## 读取信息

| 属性 | 值 |
|---|---|
| 读取日期 | 2026-08-09 |
| 读取方式 | STM32 内置 DFU bootloader（DfuSe 协议，只读 UPLOAD） |
| DFU 枚举 | STMicroelectronics "DFU in FS Mode"，USB ID `0483:df11`，序列号 `00000000010C`，Full-Speed |
| 目标芯片 | **STM32F407VG**（Cortex-M4，**1MB Flash**） |
| Dump 文件 | `firmware/airnut_full_flash_1MB.bin`（1,048,576 字节，整片） |
| SHA256 | `486b2562da1198ca43af4b253b3661b37bafb268b175e773cabc124f07163cbe` |
| 读取工具 | `firmware/dfu_read.py`（pyusb 实现，纯只读） |

> **重要修正**：此前 `OTA_BackUp_Analysis.md` 中记录芯片为 STM32F407VET6（512KB），
> 与事实不符。DFU 接口描述符报告 Flash 布局
> `@Internal Flash /0x08000000/03*016Ka,01*016Kg,01*064Kg,07*128Kg`
> （3×16K + 16K + 64K + 7×128K = **1024KB**），实际为 **F407VG**。
> 该描述符由 ST 出厂 bootloader 依据芯片容量寄存器生成，可信。

## 读保护（RDP）状态

**未开启**。判据：

1. DFU bootloader 正常枚举（RDP 等级 2 会彻底禁用 DFU，设备根本不会出现）；
2. 用户 Flash 可通过 DFU UPLOAD 正常读出（RDP 等级 1 会拒绝用户 Flash 读取）；
3. 读出的内容是合法向量表和固件代码，而非全 0 或错误响应。

注：该 bootloader 不开放系统存储区（`0x1FFFxxxx`）的 DFU 读取，Option Bytes /
Unique ID / Flash 容量寄存器均无法直接读（返回"命令回显"，首字节 `0x21` + 请求地址），
因此 RDP 状态只能如上间接确认。OTP 区（`0x1FFF7800`）读出全 `0xFF`，为空白未写入。

## Flash 布局

| 区域 | 地址范围 | 内容 |
|---|---|---|
| 固件镜像 | `0x08000000` – `0x08044FB5` | 单一应用镜像，282,550 字节（约 276KB） |
| 空白区 | `0x08044FB6` – `0x080FFFFF` | 全 `0xFF`（擦除态） |

- 向量表 @`0x08000000`：初始 SP `0x20001148`，Reset Handler `0x0800865D`（Thumb，实际 `0x0800865C`）
- 镜像**链接基址为 `0x08000000`**，自包含全部功能（uC/OS-III、WiFi 协议、语音、OTA 逻辑），未见独立 bootloader 分区
- 镜像内有 1 处对 `0x08040000` 的字面引用（`0x08007A78`），疑似 OTA/旧布局残留逻辑

## 与 TF 卡备份 OTA_BackUp.bin 的关系

**结论：设备上当前的固件与 TF 卡备份不是同一个构建**（同一产品的不同版本）。

| 对比项 | TF 卡备份 `OTA_BackUp.bin` | 本次 Dump 中的固件 |
|---|---|---|
| 大小 | 216,600 字节 | 282,550 字节 |
| 链接基址 | `0x08040000`（Reset `0x08044479`） | `0x08000000`（Reset `0x0800865D`） |
| 初始 SP | `0x20000400` | `0x20001148` |
| 版本标记 | `WuBo    microSD Flash   1.00` | `WuBo    microSD Flash   1.00`（相同） |
| 逐字节重合 | — | 仅 2–3%（抽样 1KB 块命中 5/53，均为公共库代码） |
| 字符串重合 | — | 766 条共有（同一产品家族特征字符串齐全） |

推断：旧版固件采用 "bootloader @`0x08000000` + 应用 @`0x08040000`" 的分区布局
（这解释了 `OTA_BackUp_Analysis.md` 中"向量表指向 Sector 6 但文件只覆盖到
`0x08034E18`"的疑问——备份文件就是位于 `0x08040000` 的应用镜像）；
而设备当前烧录的新版固件改为了 `0x08000000` 单镜像布局。

**警告**：不能把 `OTA_BackUp.bin` 直接当作整片固件写回 `0x08000000`
（链接基址不对，且缺少旧布局中的 bootloader 部分）。

## Dump 中发现的关键字符串

| 地址 | 字符串 | 说明 |
|---|---|---|
| `0x080083B0` | `The Airnut_1s is designed by the moji hardware team!` | 墨迹硬件团队署名 |
| `0x08011021` | 同上（第二处） | |
| `0x08041C1C` | `WuBo    microSD Flash   1.00` | 开发者 + 版本标记 |
| `0x080439B8` | `apn.airnut.com` | 云服务器域名 |
| `0x08044480` | `airnut_p` | 产品密钥 |
| `0x08043A78` | `MJBW15080800888` | 设备标识 |
| `0x08042534` | `USB AIRNUT1S VERSION` | USB 版本查询命令 |
| `0x08008640` 附近 | `DFU Interface` / `DFU Config` / `00000000010C` | 固件内置 DFU USB 描述符（与 DFU 模式枚举信息吻合） |

其余字符串（任务名、传感器、协议命令等）与 `OTA_BackUp_Analysis.md` 所述一致，
两份固件功能集合基本相同。

## DfuSe 读取协议实测要点（踩坑记录）

1. **SET_ADDRESS 后必须 ABORT**：下发 `0x21` 设置地址命令并轮询至 `dfuDNLOAD_IDLE`
   后，必须再发一次 `DFU_ABORT` 让设备回到 `dfuIDLE`，否则后续所有
   `DFU_UPLOAD` 都会被 STALL 拒绝。数据块编号从 **2** 开始（0/1 保留给命令）。
2. **系统区不可读**：`0x1FFFxxxx`（Option Bytes / Unique ID / 容量寄存器）
   的 UPLOAD 返回命令回显而非数据；用户 Flash 与 OTP 区可读。
3. 读取速度：1KB/块，整片 1MB 约 1–2 秒。
4. 复现命令：
   ```
   # 让设备进入 DFU 模式后
   python3 firmware/dfu_read.py flash 0x08000000 0x100000 dump.bin
   # 抽查校验（重读比对，见 dfu_read.py 注释）
   ```
5. 依赖：`brew install libusb && pip3 install pyusb`。
   （dfu-util 亦可：`dfu-util -d 0483:df11 -a 0 -s 0x08000000 -U dump.bin`）

## 下一步建议

1. 用 Ghidra/IDA 反编译 `0x08000000` 镜像（链接基址 `0x08000000`，入口 `0x0800865C`），
   重点看 `0x08007A78` 附近的 `0x08040000` 引用，确认新固件的 OTA 写入布局；
2. 确认新固件 OTA 流程后，才能安全地进行固件改造/自制 OTA；
3. 如需进一步分析运行期行为，可在正常模式下通过 USB 与设备交互
   （固件含 "USB AIRNUT1S VERSION" 等 USB 命令字）。
