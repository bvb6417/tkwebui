# TkWebUI

Modern Web-style themes and widgets for Python's `tkinter` / `ttk`.
给 Python 自带的 Tkinter / ttk 换上现代 Web 应用风格的外观，并补齐常用控件。

## Installation / 安装

```bash
python -m pip install tkwebui
```

Requires Python 3.8+ with Tkinter available. Developed and tested on Windows 11
with Python 3.11. Other platforms use pure-Python fallbacks and have not been
fully tested. On Linux, install your distribution's Tkinter package (often
`python3-tk`) if needed; Tkinter is not installed by pip.

Core widgets use only the Python standard library. No external theme images
or browser engine are required. `ImageViewer` can optionally use Pillow for
JPEG, WebP and additional image formats.

## Quick start / 快速开始

```python
import tkinter as tk
from tkinter import ttk
import tkwebui as ui

ui.enable_dpi_awareness()
root = tk.Tk()
root.title("TkWebUI example")
ui.apply_theme(root)
ttk.Entry(root).pack(padx=24, pady=12)
ttk.Button(root, text="Save", style="Primary.TButton").pack(padx=24, pady=12)
root.mainloop()
```

Call `enable_dpi_awareness()` before creating the Tk root, and `apply_theme(root)`
before creating widgets.

The library provides menus, dropdowns, tooltips, dialogs, cards, navigation,
tables, an editable spreadsheet, charts, date pickers and form controls.
Version 0.3.2 fixes dropdown and tooltip positioning on secondary monitors,
including negative virtual-desktop coordinates.

## Demo and documentation

Download the [GitHub source](https://github.com/bvb6417/tkwebui) or source
distribution, then run `python demo.py` to open the 12-page widget gallery.
The wheel installs the library; the demo stays in the source distribution.

- [Full documentation](https://github.com/bvb6417/tkwebui#readme)
- [Examples](https://github.com/bvb6417/tkwebui/tree/main/examples)
- [Changelog](https://github.com/bvb6417/tkwebui/blob/main/CHANGELOG.md)
- [Issue tracker](https://github.com/bvb6417/tkwebui/issues)
- [TkWin11](https://github.com/bvb6417/tkwin11), a related Windows 11 Fluent-style library

Do not mix TkWebUI and TkWin11 in the same Tk interpreter. MIT license.
