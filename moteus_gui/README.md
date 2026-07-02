# moteus GUI tools

本包提供两个面向 moteus 控制器的图形界面工具，依赖同仓库的 [`moteus`](../README.md) 核心库。

## 安装

先确保 `moteus` 已经以可编辑模式安装（在仓库根目录）：

```bash
pip install -e .
```

再安装本包：

```bash
pip install -e ./moteus_gui
```

## 1) `tview`（官方 Diagnostic Protocol 工具）

基于 PySide6/Qt 的诊断工具，文档见 [Diagnostic Protocol](https://mjbots.github.io/moteus/protocol/diagnostic/)。

```bash
tview --can-iface candle --can-chan 0 --can-disable-brs
# 或
python -m moteus_gui.tview --can-iface socketcan --can-chan can0 --can-disable-brs
```

## 2) `fastgui`（自建高频 Tkinter GUI）

基于 `moteus.control_manager.ControlManager` 的高频实时控制界面，用于连接、发送指令、监控状态、CSV 记录。

```bash
moteus_fastgui --can-type candle --can-chan 0 --ids 1 --can-disable-brs
# 或
python -m moteus_gui.fastgui.gui_app --can-type socketcan --can-chan can0 --ids 1,2 --can-disable-brs
```

详细用法见仓库根目录 [README.md](../README.md) 的"图形界面"章节。
