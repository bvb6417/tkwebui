# 旧工具接入 TkWebUI

**能否只在开头调用一次就完成整个 UI 替换？**

如果界面主要由 tkinter.ttk 标准控件构成，一次 `apply_theme` 就能统一大部分基础样式。它不会自动转换传统 tk 控件、改写布局、替换自绘界面或添加新的交互功能。

## 推荐插入位置

```python
import tkinter as tk
from tkinter import ttk
from tkwebui import enable_dpi_awareness, apply_theme

enable_dpi_awareness()     # 原来创建 Tk 之前
root = tk.Tk()             # 使用旧工具现有的根窗口，不要额外创建一个
apply_theme(root)          # 创建业务控件之前
# 原来的业务界面创建代码
root.mainloop()
```

把整个 `tkwebui` 文件夹复制到旧工具可导入的目录即可（各模块之间互相依赖，不要只挑其中几个文件）。`demo.py` 仅为演示入口，不要拿它覆盖旧工具的业务入口。

## 自动生效的范围

- ttk.Button、Entry、Spinbox、Checkbutton、Radiobutton、Frame、Label、LabelFrame。
- ttk.Notebook、Panedwindow、Treeview、Scale、Progressbar、Scrollbar、Separator、Sizegrip。
- ttk.Combobox 的输入区与箭头样式；默认的原生弹出列表仍需替换为 ThemedCombobox。
- 默认字体、主题色与部分 tk 控件的默认配色。显式指定颜色的代码优先级可能更高。

## 需要少量适配的部分

| 旧用法 | 统一现代 Web 外观的用法 |
| --- | --- |
| tk.Button / Entry / Frame 等 | 对应 ttk 控件；同步调整 bg/fg/relief 等不兼容参数 |
| ttk.Combobox | ThemedCombobox，保留 values/get/set/current 等接口 |
| tk.Text | RoundedText，保留文本编辑和滚动接口 |
| tk.Listbox | RoundedListbox，保留选择和列表接口 |
| tk.Menu | ThemedMenu；菜单按钮用 MenuButton / OptionMenu |
| 原生对话框 | Modal 或 Dialogs，由应用填入内容和按钮行为 |
| 需要表头排序的 Treeview | SortableTreeview，或对已有 tree 调用 enable_sorting(tree) |
| 需要单元格编辑/多选粘贴的区域 | Spreadsheet，需要由业务代码读写其数据 |
| 自绘 Canvas、第三方控件 | 需分别适配，不受 ttk 样式统一控制 |

## 常用导入

```python
from tkwebui import (RoundedText, configure_table, ThemedCombobox, ThemedMenu,
                     MenuButton, OptionMenu, RoundedListbox,
                     SortableTreeview, enable_sorting, Spreadsheet)
```

## 接入时注意

- 旧代码后面若再次调用 theme_use('vista') 或其他主题切换，会覆盖当前主题。
- 旧代码自己设置的 ttk 自定义样式、硬编码颜色、图片、Canvas 绘图不会自动改写。
- 布局位置、固定宽高、表单结构与业务逻辑保持原样；应检查高 DPI 下是否需要调整固定尺寸。
- 顶层系统标题栏不会被 apply_theme 替换；如需一体化操作栏，单独接入 WindowChrome。
- 不应全局强行把 tkinter 类替换成 ttk 类，二者有部分选项和行为差异。

具体到某个旧工具，需要查看其实际控件组成才能判断适配量。
