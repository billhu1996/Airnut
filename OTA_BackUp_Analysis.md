# OTA_BackUp.bin 固件分析报告

> **更新（2026-08-09）**：已通过 DFU 读取整片 Flash，见 [`DFU_Dump_Analysis.md`](DFU_Dump_Analysis.md)。
> 实测确认芯片实为 **STM32F407VG（1MB Flash）**，本文"VET6/512KB"的记载有误；
> 且设备当前运行的固件与本备份**不是同一构建**（备份是链接在 `0x08040000` 的旧版应用镜像，
> 这解释了本文"向量表指向 Sector 6 但文件只覆盖到 `0x08034E18`"的疑问）。

## 基本信息

| 属性 | 值 |
|---|---|
| 文件名 | OTA_BackUp.bin |
| 来源 | 空气果1S (Airnut_1s) TF 卡备份 |
| 目标芯片 | STM32F407VET6 (Cortex-M4, 512KB Flash, 192KB RAM) |
| 文件大小 | 216,600 字节 (211.5 KB) |
| 文件格式 | 原始二进制固件镜像 (raw bin) |
| 初始 SP | `0x20000400` (RAM 起始 `0x20000000` + 1KB) |
| Reset Handler | `0x08044479` |
| 开发者 | moji hardware team（墨迹硬件团队），署名 WuBo |

## 固件结构

### 向量表

向量表位于文件偏移 `0x00`（对应 Flash `0x08000000`），包含标准 ARM Cortex-M 中断向量：

- 偏移 `0x00`: 初始栈指针 `0x20000400`
- 偏移 `0x04`: Reset 处理函数 `0x08044479`
- 偏移 `0x08`: NMI 处理函数 `0x08040779`
- 偏移 `0x0C`: HardFault 处理函数 `0x08040783`
- 大部分未使用的中断指向默认处理函数 `0x080407A3`

### 代码区域分布

| 文件偏移 | Flash 地址 | 大小 | 内容 |
|---|---|---|---|
| `0x000000-0x000200` | `0x08000000-0x080001FF` | 512 B | 中断向量表 |
| `0x001000-0x001100` | `0x08001000-0x080010FF` | 256 B | 签名区：`The Airnut_1s is designed by the moji hardware team!` |
| `0x001600-0x001700` | `0x08001600-0x080016FF` | 256 B | 数据区：`8888888888` |
| `0x002000-0x034E18` | `0x08002000-0x08034E17` | ~203 KB | **主代码段**（ARM Thumb-2 指令） |

### STM32F407 Flash 扇区使用情况

| 扇区 | 地址范围 | 大小 | 使用率 | 说明 |
|---|---|---|---|---|
| Sector 0 | `0x08000000-0x08003FFF` | 16 KB | 47.1% | 向量表 + 初始化代码 |
| Sector 1 | `0x08004000-0x08007FFF` | 16 KB | 86.4% | 代码段 |
| Sector 2 | `0x08008000-0x0800BFFF` | 16 KB | 88.4% | 代码段 |
| Sector 3 | `0x0800C000-0x0800FFFF` | 16 KB | 89.8% | 代码段 |
| Sector 4 | `0x08010000-0x0801FFFF` | 64 KB | 87.8% | 代码段 |
| Sector 5 | `0x08020000-0x0803FFFF` | 128 KB | 84.2% | 代码段（文件末尾） |
| Sector 6 | `0x08040000-0x0805FFFF` | 128 KB | — | 超出文件范围（向量表指向此区域） |
| Sector 7 | `0x08060000-0x0807FFFF` | 128 KB | — | 超出文件范围 |

> **注意**：向量表中的中断处理函数地址指向 `0x0804xxxx`（Sector 6），但文件内容仅覆盖到 `0x08034E18`。这可能意味着：
> - 此文件是 OTA 应用镜像，运行时由 Bootloader 搬运到 `0x08040000` 区域执行
> - 或 TF 卡上的备份不完整（只复制了部分数据）

## 软件架构

### RTOS：uC/OS-III

固件基于 **uC/OS-III** 实时操作系统运行，从任务名称字符串可以确认。

### 任务列表

| 任务名称 | 功能 |
|---|---|
| Main Task | 主任务 |
| OTA Task | OTA 固件升级任务 |
| PM2_5 Receive Task | PM2.5 传感器数据接收 |
| Sensor Measure Task | 传感器测量调度 |
| Proxi Sensor Left Task | 左侧接近传感器 |
| Proxi Sensor Right Task | 右侧接近传感器 |
| Proxi Sensor Task | 接近传感器总控 |
| BatteryFuelGaugeTask | 电池电量计（BQ274XX） |
| Breath LED Task | 呼吸灯效果 |
| Wifi Receive Task | WiFi 模块数据接收 |
| WiFi Server Task | WiFi 服务端逻辑 |
| Debug Receive Task | 调试串口接收 |
| Audio Mix Play Task | 音频混合播放 |
| Key Task | 按键处理 |
| uC/OS-III Timer Task | RTOS 定时器任务 |
| uC/OS-III Idle Task | RTOS 空闲任务 |
| uC/OS-III Stat Task | RTOS 统计任务 |
| uC/OS-III Tick Task | RTOS 时钟节拍 |
| uC/OS-III ISR Queue Task | RTOS 中断服务队列 |

### 互斥锁 / 信号量

- Proxi LEFT/Right Sensor Hold Mutex
- Temp Humi Hold Mutex
- LED Screen Hold Mutex
- Battert Hold Mutex
- Malloc Hold Mutex
- Debug UART Tx/Rx Sem
- WiFi UART Tx/Rx Flag
- PM2.5 UART Tx/Rx Flag
- CO2 UART Tx/Rx Flag

## 外设与传感器

### 传感器

| 传感器 | 接口 | 说明 |
|---|---|---|
| SHT20 | I2C | 温湿度传感器，配置为 8bit 湿度 + 12bit 温度模式 |
| PM2.5 | UART | 粉尘传感器（独立接收任务） |
| CO2 | UART | 二氧化碳传感器（独立收发标志） |
| BQ274XX | I2C | 电池电量计芯片（I2C 寄存器读写） |
| 接近传感器 (左/右) | GPIO/ADC | 人体接近检测，带阈值任务 |

### 通信

| 模块 | 接口 | 说明 |
|---|---|---|
| WiFi 模块 | UART | 支持 EasyLink 配网，服务端域名 `apn.airnut.com` |
| USB | USB | 调试/数据导出/日志读取 |
| microSD | SPI/FatFs | TF 卡存储，用于 OTA、语音文件、日志、配置 |

### 存储 (TF 卡文件系统)

使用 FatFs 文件系统，路径格式 `0:/xxx`，已知文件：

| 文件路径 | 用途 |
|---|---|
| `0:/OTA.bin` | OTA 固件文件 |
| `0:/OTA_Check.bin` | OTA 校验文件 |
| `0:/Sys_Cfg_Factory.bin` | 出厂系统配置 |
| `0:/Sys_Verify_Cfg.bin` | 系统校验配置 |
| `0:/voice/%s.mp3` | 语音播报文件 |
| `0:/music.wav` ~ `0:/music_11.wav` | 音乐/提示音 |
| `0:/Log/Log.txt` | 系统日志 |
| `0:/Log/Log_Backup.txt` | 日志备份 |

## OTA 升级机制

### OTA 流程

```
OTA_Start
    ↓
OTA_Get_File (从 WiFi 模块接收固件数据)
    ↓
写入 Flash (FLASH_ProgramByte)
    ↓
Wifi OTA Download Completed!!!
    ↓
OTA_Stop (校验并重启)
```

### OTA 状态

- `OTA_RCV_SUCCESS` — 接收成功
- `OTA_RCV_FAILED` — 接收失败
- `OTA_Start--------S` — 开始（服务端）
- `OTA_Stop---------S` — 停止（服务端）
- `OTA_Get_File-----A` — 获取文件（ACK）
- `Wifi_OTA_OK------S` — WiFi OTA 完成
- `MCU_Code_Version-S` — MCU 固件版本校验

### WiFi 状态机

```
WIFI_STATUS_WAIT_AP          ← 等待连接 AP
    ↓
WIFI_STATUS_EASY_LINK        ← EasyLink 配网中
    ↓
WIFI_STATUS_LOGIN_OK         ← 登录成功
    ↓
正常工作（数据上报/接收 OTA）
```

异常状态：
- `WIFI_STATUS_WLAN_FATAL_ERR` — WLAN 致命错误
- `WIFI_STATUS_STACK_OVERFLOW` — 协议栈溢出
- `ConnectAP_Failed` — 连接 AP 失败
- `Easylink_Err` — EasyLink 配网错误
- `Connection_Closed` — 连接关闭

配网方式：EasyLink（乐鑫 WiFi 模块一键配网）

## 语音播报系统

固件内置完整的语音播报功能，支持：

- **天气播报**：`weather/cloud_0` ~ `weather/cloud_2` 等
- **时间段问候**：`time/wee_hours`、`time/morning`、`time/forenoon`、`time/afternoon`、`time/evening`、`time/night2day`、`time/day2night`
- **PM2.5 播报**：独立的 PM2.5 语音文件
- **CO2 播报**：独立的 CO2 语音文件
- **数字播报**：`count/0.mp3` ~ `count/9999.mp3`
- **提示音**：`tips/` 目录下多种提示音
- **风力播报**：`wind/rotational` 等
- **灾害预警**：`disaster/` 目录下多种预警音
- **车载模式**：`car/` 目录下限行/不限行提示

## 关键字符串汇总

```
The Airnut_1s is designed by the moji hardware team!
WuBo    microSD Flash   1.00
USB AIRNUT1S VERSION
apn.airnut.com
airnut_p
Config SHT20  8bit Humidity 12bit Temperature mode
BQ274XX_I2C_WriteRegister
```

## 服务器交互协议

### 通信架构

```
STM32 (MCU) <--UART--> WiFi模块 <--TCP/UDP--> apn.airnut.com:10511
```

- **传输层**: TCP Socket，端口 **10511**
- **数据格式**: JSON，以 `\n\r` 分隔
- **协议前缀**: `#MJ-`（固件偏移 `0x034784`）
- **服务器域名**: `apn.airnut.com`（固件偏移 `0x033850`）
- **设备标识**: `MJBW15080800888`（固件偏移 `0x033900`）
- **产品密钥**: `airnut_p`（固件偏移 `0x0342EC`）

### 协议消息格式

日志中的消息格式：
```
#MJ-<命令名>-<方向>[<数据长度>]<JSON数据>
```

- **方向**: `S` = Send（MCU→服务器），`A` = Ack（服务器→MCU），`E` = Error

### MCU → 服务器命令 (Send/-S)

| 命令 | 说明 | 固件偏移 |
|---|---|---|
| `Login_OK` | 登录成功，携带 `{"type":"client","socket_id":14306,"result":0,"p":"log_in"}` | `0x032BAC` |
| `ConnectAP_OK` | WiFi AP 连接成功 | `0x032BE8` |
| `ConnectAP_Failed` | WiFi AP 连接失败 | `0x032BFC` |
| `ConnectionClosed` | 连接关闭 | `0x032BC0` |
| `ConnectFailed` | 连接失败 | `0x032B70` |
| `OTA_Start` | 开始 OTA 升级 | `0x032C10` |
| `OTA_Stop` | 停止 OTA | `0x032C24` |
| `Wifi_OTA_OK` | OTA 下载完成 | `0x032C4C` |
| `MCU_Code_Version` | 上报 MCU 固件版本 | `0x032C38` |
| `Get_Weather` | 请求天气数据 | `0x032D3C` |
| `UDP_Message` | UDP 消息 | `0x032DC8` |
| `Start_Detect` | 启动检测 | `0x032D50` |
| `Set_Volume` | 设置音量 | `0x032D64` |
| `Set_Check_Time` | 设置校时 | `0x032D78` |
| `Start_Broadcast` | 开始语音播报 | `0x032D8C` |
| `Test_Voice` | 语音测试 | `0x032DA0` |
| `Set_PM25kValue` | 设置 PM2.5 校准值 | `0x032DB4` |
| `Alarm` | 告警 | `0x032C60` |
| `EasyLinkRecv` | EasyLink 配网接收 | `0x032B48` |
| `EasyLinkComplete` | EasyLink 配网完成 | `0x032B5C` |
| `WlanFatalErr` | WLAN 致命错误 | `0x032B84` |
| `StackOverflow` | 协议栈溢出 | `0x032B98` |
| `EasyLinkErr` | EasyLink 配网错误 | `0x032BD4` |

### 服务器 → MCU命令 (Ack/-A)

| 命令 | 说明 | 固件偏移 |
|---|---|---|
| `Restore_Defaults` | 恢复出厂设置 | `0x032C74` |
| `Start_Easylink` | 启动配网 | `0x032C88` |
| `Stop_Easylink` | 停止配网 | `0x032C9C` |
| `Active` | 激活设备 | `0x032CB0` |
| `OTA_Get_File` | 获取 OTA 文件 | `0x032CC4` |
| `SelfCheck_Result` | 自检结果 | `0x032CD8` |
| `Power_Off_Reason` | 关机原因 | `0x032CEC` |
| `Wifi_Is_Aliving` | 心跳保活 | `0x032D00` |
| `OTA_Stop` | 停止 OTA | `0x032D14` |
| `UDP_DATA` | UDP 数据下发 | `0x032D28` |

### JSON 协议字段

**设备上报数据 (`p: "post"`)：**
```json
{
  "p": "post",
  "param": {
    "indoor": {
      "pm25": 35,
      "t": 25.6,
      "h": 60.2,
      "co2": 486
    },
    "charge": 1,
    "signal": 80
  }
}
```

**登录 (`p: "log_in"`)：**
```json
{"type": "client", "socket_id": 14306, "result": 0, "p": "log_in"}
```

**服务器控制命令类型：**

| `p` 字段值 | 说明 |
|---|---|
| `get` | 拉取传感器数据 |
| `post` | 设备上报数据 |
| `log_in` | 登录认证 |
| `active` / `reactive` | 设备激活 |
| `set_volume` | 设置音量 |
| `set_bgm` | 设置背景音 |
| `set_k` | 设置校准参数 |
| `checkTime` | 时间校准 |
| `voice_broadcast` | 语音播报 |
| `car_limit` | 车辆限行 |
| `heartbeat` | 心跳 |

**天气数据字段：**

| 字段 | 说明 |
|---|---|
| `city` | 城市 |
| `weather` | 天气 |
| `d_w_l` | 白天天气等级 |
| `d_w_d` | 白天天气描述 |
| `n_w_l` | 夜间天气等级 |
| `n_w_d` | 夜间天气描述 |
| `lunar` | 农历 |
| `is_day` | 是否白天 |

**校准参数字段：**

| 字段 | 说明 |
|---|---|
| `co2_offset` | CO2 偏移量 |
| `pm2.5_k1` / `pm2.5_k2` / `pm2.5_k3` | PM2.5 校准系数 |
| `pm2.5_noise` | PM2.5 噪声值 |
| `temp_offset` | 温度偏移量 |
| `humi_offset` | 湿度偏移量 |

**其他协议字段：**

| 字段 | 说明 |
|---|---|
| `volume` | 音量 |
| `time` | 时间 |
| `value` | 数值 |
| `pm25` | PM2.5 值 |
| `noise` | 噪声 |
| `reason` | 原因 |
| `info` | 信息 |
| `http` | HTTP 地址 |
| `port` | 端口 |
| `charge` | 充电状态 |
| `signal` | 信号强度 |
| `indoor` | 室内数据 |
| `manual` | 手动模式 |
| `reset` | 重置 |
| `enable` | 启用 |
| `voice` | 语音 |
| `online` | 在线状态 |
| `param` | 参数 |
| `result` | 结果 |
| `play` | 播放 |
| `night_time` | 夜间时间 |
| `night_start` | 夜间开始 |
| `check_key` | 校验密钥 |
| `weather_d` / `weather_n` | 白天/夜间天气 |
| `show_screen` | 屏幕显示 |
| `pressure` | 气压 |

### 日志中观察到的通信行为

从运行日志中观察到设备处于**反复断连循环**：
```
ConnectionClosed → Login_OK → Get_Weather(Error) → ConnectionClosed → ...
```
每约 47 秒一个周期，说明 WiFi 模块能连上服务器并登录，但获取天气后就断开了。

## 总结

这是一个 **STM32F407VET6 的完整应用固件镜像**，运行 **uC/OS-III RTOS**，实现了空气果1S 空气质量检测仪的全部功能，包括：

1. **多传感器采集**：PM2.5、CO2、温湿度、接近传感器、电池电量
2. **WiFi 联网**：通过 UART 连接 WiFi 模块，支持 EasyLink 配网，连接 `apn.airnut.com` 云服务
3. **OTA 远程升级**：通过 WiFi 接收新固件，写入 Flash，支持校验和回滚
4. **语音播报**：完整的语音系统，支持天气、空气质量、时间段问候等
5. **TF 卡存储**：用于 OTA 固件暂存、语音文件、日志记录、系统配置

固件有效数据约 **209 KB**，占 STM32F407 512KB Flash 的约 **40%**。
