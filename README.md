# moteus 无刷电机控制器 Python 绑定

本库提供与 mjbots moteus 无刷电机控制器通信和控制的 Python 接口，包含：

- 基础异步控制 API（`moteus.Controller`）
- 面向 GUI 的高频同步控制层（`ControlManager`）
- CSV 数据记录能力（`CsvLogger`）
- 离线模拟器（`moteus.app.simulator`）
- 自定义高频 GUI（`moteus.app.gui_app`）

## 目录

- [安装](#安装)
- [CAN 适配器支持](#can-适配器支持)
- [快速开始](#快速开始)
- [图形界面](#图形界面)
- [CSV 数据记录](#csv-数据记录)
- [离线模拟器](#离线模拟器)
- [基础 API](#基础-api)
- [ControlManager（高频控制接口）](#controlmanager高频控制接口)

## 安装

### 方式一：克隆后本地安装

```bash
git clone git@github.com:Turing-zero/moteus-python-packages.git
cd moteus-python-packages
pip install .
```

### 方式二：直接从 Git 安装

```bash
# ssh
pip install "git+ssh://git@github.com/Turing-zero/moteus-python-packages.git@v0.3.102-tz"

# https
pip install "git+https://github.com/Turing-zero/moteus-python-packages.git@v0.3.102-tz"
```

## CAN 适配器支持

| 适配器 | 平台 | 参数示例 |
|--------|------|----------|
| `fdcanusb` | Linux / Windows / macOS | `--fdcanusb /dev/ttyUSB0` |
| `socketcan` | Linux | `--can-iface socketcan --can-chan can0` |
| `candle` / CANable FD | Windows / macOS | `--can-iface candle --can-chan 0` |

说明：

- Candle 在 Windows/macOS 上自动枚举。
- 在 Linux 上，Candle 通常以 `socketcan` 接口呈现，由 `socketcan` 传输层处理。

## 快速开始

### 单控制器示例

```python
import asyncio
import moteus

async def main():
    c = moteus.Controller(id=1)  # transport=None 时自动发现
    await c.set_stop()
    result = await c.set_position(position=0.5, query=True)
    print(result)

asyncio.run(main())
```

### 多控制器总线优化示例

`transport.cycle()` 可以在一次 CAN 轮询中发送多个指令，提高总线利用率：

```python
import asyncio
import math
import moteus

async def main():
    transport = moteus.Fdcanusb()
    c1 = moteus.Controller(id=1)
    c2 = moteus.Controller(id=2)

    while True:
        print(await transport.cycle([
            c1.make_position(position=math.nan, query=True),
            c2.make_position(position=math.nan, query=True),
        ]))

asyncio.run(main())
```

补充：

- 所有 `set_` 方法均有对应 `make_` 版本，可直接传入 `cycle()`。
- 该优化在 `pi3hat` 等非 `fdcanusb` 链路上通常更明显。

## 图形界面

### 1) `moteus_gui.tview`（Diagnostic Protocol）

文档：[Diagnostic Protocol](https://mjbots.github.io/moteus/protocol/diagnostic/)

安装依赖：

```bash
pip install moteus_gui
```

运行示例：

```bash
# Windows
python -m moteus_gui.tview --can-iface candle --can-chan 0 --can-disable-brs

# Ubuntu
python -m moteus_gui.tview --can-iface socketcan --can-chan can0 --can-disable-brs
```

### 2) 自定义高频 CANFD GUI（`moteus.app.gui_app`）

用于实时连接、发送指令、监控状态。

```bash
python -m moteus.app.gui_app
python -m moteus.app.gui_app --can-type candle --can-chan 0 --ids 1,2
python -m moteus.app.gui_app --can-type socketcan --can-chan can0 --ids 1
python -m moteus.app.gui_app --can-type fdcanusb --can-chan /dev/ttyUSB0 --ids 1
```

关键页面：

- **Motion**：Stop / Brake / Zero Vel / Rezero、位置控制、速度控制。
- **CSV Log**：设置输出路径和字段，`Start Logging` 后持续记录状态。

提示：勾选 `Persistent` 后，指令会在每个控制周期重复发送，避免看门狗超时停机。

## CSV 数据记录

`CsvLogger` 是可插拔监听器，可将状态更新实时写入 CSV。

```python
from moteus.app.control_manager import ControlManager, CsvLogger
import time

manager = ControlManager(cycle_hz=500)

with CsvLogger('/data/run.csv', controller_ids=[1, 2]) as logger:
    manager.add_listener(logger.on_status_update)
    manager.connect([1, 2], can_type='socketcan', can_chan='can0')
    time.sleep(10)
    manager.disconnect()

print(f'共写入 {logger.row_count} 行')
```

### 指定字段

默认不包含 `trajectory_complete`。可通过 `fields` 指定：

```python
CsvLogger(
    '/data/run.csv',
    fields=['timestamp', 'id', 'position', 'velocity', 'torque'],
)
```

可用字段：

```text
timestamp  id  mode  position  velocity  torque  voltage  temperature  fault  trajectory_complete
```

### 在 GUI 中记录

切换到 `CSV Log` 标签页后：

1. 填写输出路径（或点击 `Browse`）。
2. 勾选需要记录的字段。
3. 点击 `Start Logging` 开始记录。
4. 点击 `Stop Logging` 刷新并关闭文件。

## 离线模拟器

`moteus.app.simulator` 使用 PD 物理模型模拟控制器响应，可用于无硬件调试 GUI 或验证 CAN 报文解析。

```bash
# 纯软件演示（无需硬件）
python -m moteus.app.simulator --ids 1 2 3

# 硬件在环仿真：连接真实 CAN 适配器并主动发送模拟遥测
python -m moteus.app.simulator --can-iface candle --can-chan 0 --ids 1 --rate 200
```

作为库使用：

```python
from moteus.app.simulator import SimulatedTransport, patch_singleton
import moteus

# 方式一：显式传入 transport
transport = SimulatedTransport([1, 2])
c = moteus.Controller(id=1, transport=transport)

# 方式二：替换全局单例（context manager）
with patch_singleton([1, 2]):
    c = moteus.Controller(id=1)  # transport=None 也可自动发现
    await c.set_position(position=0.5)
```

## 基础 API

### 位置模式参数

`Controller.set_position` / `Controller.make_position` 支持以下参数（传 `None` 表示省略该字段）：

| 参数 | 说明 |
|------|------|
| `position` | 目标位置（转数）；`math.nan` 表示纯速度模式 |
| `velocity` | 前馈速度（rev/s） |
| `feedforward_torque` | 前馈力矩（N·m） |
| `kp_scale` | 位置增益缩放（0-1） |
| `kd_scale` | 速度增益缩放（0-1） |
| `maximum_torque` | 最大力矩限制（N·m） |
| `stop_position` | 到达后停止的位置（转数） |
| `watchdog_timeout` | 看门狗超时（s），`0` 表示禁用 |
| `query` | 是否同时查询状态 |

### 编码精度控制

可通过 `Controller` 构造参数分别配置命令与查询的编码精度：

```python
import moteus

pr = moteus.PositionResolution()
pr.position = moteus.INT16
pr.velocity = moteus.INT16
pr.kp_scale = moteus.F32
pr.kd_scale = moteus.F32

qr = moteus.QueryResolution()
qr.mode = moteus.INT8
qr.position = moteus.F32
qr.velocity = moteus.F32
qr.torque = moteus.F32

c = moteus.Controller(position_resolution=pr, query_resolution=qr)
```

## ControlManager（高频控制接口）

`ControlManager` 在后台线程运行 asyncio 事件循环，对外提供同步、线程安全 API，适合 GUI 或其他非异步程序。

```python
from moteus.app.control_manager import ControlManager

manager = ControlManager(cycle_hz=500)
manager.connect([1, 2], can_type='candle', can_chan='0')

manager.command_position([1], position=0.5, persistent=True)
manager.command_velocity([2], velocity=2.0, persistent=True)  # rev/s
manager.command_stop()
manager.disconnect()
```

### 支持的指令

| 方法 | 电机模式 | 说明 |
|------|----------|------|
| `command_stop(ids)` | `STOPPED` | 停机并清除所有持久指令 |
| `command_brake(ids)` | `BRAKE` | 再生制动保持 |
| `command_zero_velocity(ids)` | `ZERO_VELOCITY` | `kd` 阻尼保持零速 |
| `command_position(ids, position, ...)` | `POSITION` | 完整位置控制参数集 |
| `command_velocity(ids, velocity, ...)` | `POSITION (pos=NaN)` | 纯速度跟踪 |
| `command_vfoc(ids, theta, voltage)` | `VOLTAGE_FOC` | 开环电压 FOC |
| `command_current(ids, d_A, q_A)` | `CURRENT` | `dq` 轴电流直接控制 |
| `command_stay_within(ids, lower, upper)` | `STAY_WITHIN` | 软限位（仅在边界施力） |
| `command_rezero(ids, rezero)` | `-` | 重新标定输出位置零点 |

补充：

- `ids=None` 时作用于所有已管理控制器。
- `persistent=True`（位置/速度默认值）表示每个控制周期都会重复发送该指令。

### 状态回调

```python
def on_update(status):  # 在后台 asyncio 线程调用，需保持轻量
    for cid, s in status.items():
        print(cid, s.position, s.velocity, s.mode)

manager.add_listener(on_update)
manager.remove_listener(on_update)
snapshot = manager.get_status()  # 线程安全状态字典副本
```

`ControllerStatus` 字段：
`controller_id`、`mode`、`position`、`velocity`、`torque`、`voltage`、`temperature`、`fault`、`trajectory_complete`、`last_update`。
