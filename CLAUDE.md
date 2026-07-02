# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a monorepo containing two independently pip-installable Python distributions for the mjbots moteus brushless controller:

- **`moteus`** (`moteus/`, its own `pyproject.toml`) — the core async Python API for communicating with moteus controllers over CAN-FD, plus headless helpers (`ControlManager`, `simulator`) that have no GUI dependencies. The importable package lives at `moteus/moteus/`.
- **`moteus_gui`** (`moteus_gui/`, its own `pyproject.toml`) — GUI tools that depend on `moteus`: the official Qt-based `tview` diagnostic tool and a custom high-frequency Tkinter GUI (`fastgui`). The importable package lives at `moteus_gui/moteus_gui/`.

Both sub-projects follow the same layout: `<name>/pyproject.toml` (project root) + `<name>/<name>/` (importable package). Neither the repo root itself nor `moteus/` alone can be `pip install`-ed directly with a bare `.` — always point pip at the sub-project directory (`./moteus` or `./moteus_gui`).

`moteus_gui` is not published to public PyPI (that name is owned by the upstream mjbots project); it's installed from this repo directly, e.g. `pip install -e ./moteus_gui`, following the same "install moteus from git" convention used for the `moteus` fork itself.

## Setup

```bash
pip3 install -e ./moteus
# or with dev dependencies
pip3 install pyserial python-can pyelftools scipy importlib_metadata packaging
```

## Architecture

### Layer model

```
User code
    ↓
Controller (moteus/moteus/moteus.py)     ← high-level per-servo API
    ↓
Transport (moteus/moteus/transport.py)   ← multi-device dispatch, routing, discovery
    ↓
TransportDevice (moteus/moteus/transport_device.py)  ← ABC for hardware devices
    ↓
FdcanusbDevice / PythonCanDevice  ← concrete hardware backends
```

### Key classes

- **`Controller`** (`moteus/moteus/moteus.py`) — The primary user-facing class. Each instance represents one physical servo. All commands are built with `make_*()` methods and executed with `execute()` or `set_*()` methods. The `transport=None` default triggers singleton auto-discovery.

- **`Transport`** (`moteus/moteus/transport.py`) — Dispatches CAN-FD frames to one or more `TransportDevice` instances. Handles multi-bus routing: builds a `_routing_table` by broadcasting UUID queries on first use. The `cycle()` method is the primary bus-efficient API for commanding multiple controllers in one round-trip.

- **`TransportDevice`** (`moteus/moteus/transport_device.py`) — ABC that defines `send_frame()`, `receive_frame()`, `transaction()`. Maintains a subscription/waiter queue for async frame delivery.

- **`FdcanusbDevice`** (`moteus/moteus/fdcanusb_device.py`) — Serial-port transport for the mjbots fdcanusb USB-CAN adapter.

- **`PythonCanDevice`** (`moteus/moteus/pythoncan_device.py`) — Transport backed by python-can (socketcan, PCAN, kvaser, vector). Handles fdcanusb deduplication via USB serial numbers to avoid double-counting the same physical device.

- **`CandleDevice`** (`moteus/moteus/candle_device.py`) — `TransportDevice` for candle CAN-FD USB adapters (Windows/Mac). Overrides `_frame_to_can_message` to honour `bitrate_switch` from the frame (necessary for CAN-FD BRS). `enumerate_devices()` calls `can.detect_available_configs("candle")`, parses `"serial:index"` channel strings, and creates one instance per channel.

- **`Candle`** (`moteus/moteus/candle.py`) — Convenience `TransportWrapper` around `CandleDevice`, mirroring the `Fdcanusb`/`PythonCan` pattern.

- **`transport_factory.py`** — Singleton transport construction via `get_singleton_transport()`. Tries `FdcanusbFactory` (priority 10), `PythonCanFactory` (priority 11), `CandleFactory` (priority 12) then any `moteus.transports2` entry points. `CandleFactory` only auto-enumerates devices on non-Linux; on Linux candle hardware appears as socketcan and is handled by `PythonCanFactory`. Additional transports (e.g., pi3hat) register via setuptools entry points in the `moteus.transports2` group.

- **`ControlManager`** (`moteus/moteus/control_manager.py`) — Thread-safe, high-frequency control wrapper: runs an asyncio event loop in a background thread and exposes a synchronous, thread-safe command API (`command_position`, `command_velocity`, `command_stop`, etc.) plus `CsvLogger`, a pluggable listener for recording controller status to CSV. Re-exported at the top level (`moteus.ControlManager`, `moteus.CsvLogger`) via `moteus/moteus/export.py`. No GUI dependencies — this lives in the `moteus` core package, not `moteus_gui`, because it's useful outside of any GUI context.

- **`moteus.simulator`** (`moteus/moteus/simulator.py`) — Offline PD-physics simulator. `SimulatedTransport` / `patch_singleton` let you exercise `Controller` code without hardware; `CanEmulator` drives a real CAN adapter with simulated telemetry for hardware-in-the-loop testing.

- **`moteus_gui`** (`moteus_gui/`, separate distribution) — Two console entry points:
  - `tview` (`moteus_gui/moteus_gui/tview.py`) — official mjbots Qt/PySide6 diagnostic tool.
  - `moteus_fastgui` (`moteus_gui/moteus_gui/fastgui/gui_app.py`) — custom Tkinter GUI built on `moteus.control_manager.ControlManager`, for real-time motion commands, status monitoring, and CSV logging.

### Resolution system

Commands and queries use typed resolution constants (`mp.INT8`, `mp.INT16`, `mp.INT32`, `mp.F32`, `mp.IGNORE`) defined in `moteus/moteus/multiplex.py`. `QueryResolution` and `PositionResolution` classes in `moteus/moteus/moteus.py` control the wire encoding per field. `mp.WriteCombiner` consolidates adjacent non-`IGNORE` fields into compact register-write opcodes.

### Wire protocol

`moteus/moteus/protocol.py` — CAN arbitration ID encoding: `dest_id | (reply_required << 15) | (source_id << 8) | (can_prefix << 16)`. Register read/write opcodes follow the moteus multiplex protocol documented at `https://github.com/mjbots/moteus/blob/main/docs/reference.md`.

### DeviceAddress and UUID routing

Controllers can be addressed by integer CAN ID or by `DeviceAddress` (containing optional UUID bytes). `Transport.discover()` broadcasts a UUID query and builds a map. UUID-based addressing is used when multiple controllers share the same CAN ID across different buses.

### CLI tool

`moteus_tool` entry point → `moteus/moteus/moteus_tool.py`. Uses `make_transport_args()` + `get_singleton_transport()` for CLI-driven transport selection.

## Common patterns

Single controller (transport auto-discovered):
```python
import asyncio, moteus

async def main():
    c = moteus.Controller(id=1)
    await c.set_stop()
    result = await c.set_position(position=0.5, query=True)

asyncio.run(main())
```

Bus-optimized multi-controller (one CAN cycle):
```python
transport = moteus.Fdcanusb()
c1, c2 = moteus.Controller(id=1), moteus.Controller(id=2)
results = await transport.cycle([
    c1.make_position(position=0.0, query=True),
    c2.make_position(position=0.0, query=True),
])
```

## Type checking

```bash
cd moteus && mypy moteus/
```

Config is in `moteus/pyproject.toml` (`[tool.mypy]`). Currently lenient — `disallow_untyped_defs` and strict checking are disabled to allow gradual adoption. Test files are excluded from mypy checks.
