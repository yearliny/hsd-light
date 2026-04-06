# HSD Love Light CLI & SDK

通过命令行控制 HSD Love Light BLE 蓝牙音箱灯 — 支持灯光、音乐、闹钟等全部功能。

本项目包含两层：

- **SDK**（`hsd_light.protocol` + `hsd_light.device`）— 可直接在 Python 项目中集成
- **CLI**（`hsd` 命令）— 终端一行命令即可操控设备

## 环境要求

- Python >= 3.10
- 系统蓝牙适配器（支持 BLE）
- Windows / macOS / Linux

## 安装

```bash
cd cli
pip install -e .
```

安装后即可使用 `hsd` 命令。

## CLI 用法

### 全局选项

```
hsd [OPTIONS] COMMAND
```

| 选项 | 说明 |
|------|------|
| `-a, --address TEXT` | 指定设备 MAC 地址（跳过扫描） |
| `-t, --timeout FLOAT` | 扫描/连接超时秒数（默认 10） |
| `-v, --verbose` | 输出调试日志 |

### 扫描设备

```bash
hsd scan
# Found: HSD Love Light  [AA:BB:CC:DD:EE:FF]
```

### 灯光控制

```bash
# 预设颜色
hsd light color red          # red / green / blue / white

# 自定义 RGB
hsd light rgb 255 0 128
hsd light rgb 255 100 0 --white 50 --brightness 80

# 亮度 (0-100)
hsd light brightness 60

# 灯效
hsd light effect gradient    # gradient / flow / dither
```

### 音乐控制

```bash
hsd music send play          # play / pause (同一键切换)
hsd music send next          # 下一曲
hsd music send prev          # 上一曲
hsd music send volume-up     # 音量+
hsd music send volume-down   # 音量-
hsd music send eq            # 循环切换 EQ
hsd music send source        # 切换 BT / TF 音源
hsd music send mute          # 静音
```

### 闹钟

```bash
hsd alarm set 07:30              # 设置并启用闹钟
hsd alarm set 22:00 --disable    # 设置但不启用
```

### 时间同步 & 设备查询

```bash
hsd sync     # 将系统时间同步到设备
hsd query    # 查询设备当前状态
```

### 指定设备地址

已知 MAC 地址时可跳过扫描，加快连接速度：

```bash
hsd -a AA:BB:CC:DD:EE:FF light color blue
```

## SDK 用法

### 快速上手

```python
import asyncio
from hsd_light import HSDDevice, Command
from hsd_light.protocol import MusicAction, ColorPreset, Effect

async def main():
    async with HSDDevice() as dev:
        # 设置红色、亮度 80%
        await dev.send(Command.color_preset(ColorPreset.RED))
        await dev.send(Command.brightness(80))

        # 自定义颜色
        await dev.send(Command.custom_color(r=255, g=0, b=128, w=0, brightness=100))

        # 渐变灯效
        await dev.send(Command.effect(Effect.GRADIENT))

        # 音乐：播放、下一曲
        await dev.send(Command.music(MusicAction.PLAY_PAUSE))
        await dev.send(Command.music(MusicAction.NEXT_TRACK))

        # 设置闹钟 07:30
        await dev.send(Command.timer(7, 30, enabled=True))

asyncio.run(main())
```

### 指定设备地址

```python
async with HSDDevice(address="AA:BB:CC:DD:EE:FF") as dev:
    await dev.send(Command.brightness(50))
```

### 监听设备通知

```python
async with HSDDevice() as dev:
    dev.on_notify = lambda data: print("Received:", data.hex())
    await dev.send(Command.query_params())
    await asyncio.sleep(2)  # 等待响应
```

### 手动管理连接

```python
dev = HSDDevice()
await dev.connect()          # 扫描 + 连接 + 自动时间同步
await dev.send(Command.brightness(100))
await dev.disconnect()
```

## BLE 协议概要

所有命令均为二进制包，格式如下：

```
[0x69, 0x96, <length>, <cmd_type>, <payload...>]
 ──────────  ────────  ──────────  ───────────
   固定头部    载荷长度   命令类型     命令数据
```

| 命令类型 | 值 | 载荷 | 说明 |
|---------|----|----|------|
| COLOR_MODE | 1 | `[preset]` | 预设颜色/灯效 (1-7) |
| TIME_SYNC | 2 | `[year_hi, year_lo, month, day, hour, min, sec]` | 时间同步 |
| CUSTOM_RGB | 3 | `[R, G, B, W, brightness]` | 自定义颜色 |
| TIMER | 4 | `[hour, min, mode]` | 闹钟设置 |
| MUSIC | 8 | `[action]` | 音乐控制 (2-10) |
| QUERY | 15 | — | 查询状态 |
| BRIGHTNESS | 17 | `[value]` | 亮度 (0-100) |

## 项目结构

```
cli/
├── pyproject.toml
├── README.md
└── hsd_light/
    ├── __init__.py        # 导出 Command, HSDDevice
    ├── __main__.py        # python -m hsd_light
    ├── protocol.py        # 协议层 — 纯字节命令构建，无外部依赖
    ├── device.py          # 设备层 — 基于 bleak 的 BLE 连接管理
    └── cli.py             # CLI 层 — 基于 click 的命令行工具
```

## License

MIT
