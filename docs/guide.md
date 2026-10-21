# TkWebUI 使用指南

## 运行演示

在项目根目录运行 `python demo.py`（或直接双击），使用已安装的系统 Python 即可，无需第三方运行依赖。

演示共十二页：第 1–6 页是基础控件、菜单弹窗和组合组件，第 7 页是 Excel 式单元格表格，第 8 页是原生交互图表，第 9–12 页是表单、通知、仪表、数据管理、图片与外观工具。`python demo.py --page 7` 可直接打开指定页。

演示数据只在内存中，关闭窗口后不保存。

## 放进自己的项目

把仓库里的 `tkwebui` 文件夹整个复制到你的脚本旁边（或任意可导入目录），然后：

```python
from tkwebui import enable_dpi_awareness, apply_theme
```

所有常用组件都可以直接从 `tkwebui` 导入，也可以从各自模块导入（如 `from tkwebui.charts import LineChart`）。各模块分工：

| 模块 | 内容 |
| --- | --- |
| `tkwebui/core.py` | 基础主题 `apply_theme`、Card、Sidebar、SegmentedControl、Dropdown、Accordion、SettingRow、ScrollArea、Tooltip、Modal、CardList、BarChart、ProgressSlider |
| `tkwebui/widgets.py` | RoundedText、SectionCard、输入焦点与按需滚动条、configure_table |
| `tkwebui/popups.py` | ThemedCombobox、ThemedMenu、ChoicePopup |
| `tkwebui/extras.py` | SquareSwitch、ToggleButton、ToolButton、MenuButton、OptionMenu、RoundedListbox 及扩展样式 |
| `tkwebui/table.py` | SortableTreeview、enable_sorting、Spreadsheet |
| `tkwebui/charts.py` | LineChart、ColumnChart、ScatterChart、DonutChart、PieChart |
| `tkwebui/render.py` | 内存抗锯齿绘制；Windows 使用系统 GDI+，无需第三方包 |
| `tkwebui/forms.py` | DateEntry、ValidatedEntry、ValueSlider、Dialogs 与语义样式 |
| `tkwebui/feedback.py` | ToastNotification、TextProgress、Meter |
| `tkwebui/dataview.py` | DataTable 搜索/筛选/分页/导出 |
| `tkwebui/media.py` | ImageViewer、ColorPicker/ColorDialog、FontPicker/FontDialog |
| `tkwebui/window_chrome.py` | 可选的一体化窗口操作栏（Windows） |

`demo.py` 只是演示程序，不是主题运行必需的文件。

本主题使用标准 tkinter/ttk 和内存生成的 PhotoImage，不需要外部图片或浏览器。原生图表使用 Canvas，直接接收 Python 列表，不依赖 NumPy，详见 [charts.md](charts.md)。第 9–12 页组件的参数与用法见 [components.md](components.md)；图片框可选用 Pillow，其余组件只需标准库。

## 最小接入

```python
import tkinter as tk
from tkwebui import enable_dpi_awareness, apply_theme, ToggleButton, OptionMenu

enable_dpi_awareness()
root = tk.Tk()
apply_theme(root)
ToggleButton(root, text='收藏', variable=tk.BooleanVar(value=True)).pack()
value = tk.StringVar(value='普通')
OptionMenu(root, value, '普通', '普通', '重要', '紧急').pack(fill='x')
root.mainloop()
```

`apply_theme` 必须在创建主题控件之前调用；扩展样式会自动加载。默认蓝色主色，可在首次调用时传 `accent` / `accent_hover`。

ttk.Button、Entry、Spinbox、LabelFrame、Notebook、Panedwindow、Treeview、Progressbar、Scale、Sizegrip 等直接获得主题样式。

- 切换按钮可直接写 `ttk.Checkbutton(..., style='Toggle.TButton')`；工具按钮使用 `style='Toolbutton'`。
- 紧凑滑块使用 `style='Horizontal.Tick.TScale'` 或 `'Vertical.Tick.TScale'`。
- 圆形滑动开关使用 `ttk.Checkbutton(..., style='Switch.TCheckbutton')`。
- 方角滑动开关使用 `SquareSwitch`，或 `ttk.Checkbutton(..., style='Square.Switch.TCheckbutton')`。

```python
from tkwebui import SquareSwitch
enabled = tk.BooleanVar(value=True)
SquareSwitch(parent, text='自动同步', variable=enabled).pack()
```

方角开关支持鼠标、空格和 Enter，包含开启/关闭、悬停、焦点和禁用状态。省略 `variable` 时 SquareSwitch 自带一个默认关闭的 BooleanVar，可通过控件的 `variable` 属性读取。

普通 ttk.Combobox 的下拉浮层不由 ttk 样式完整控制；需要统一浮层时请使用 `ThemedCombobox`。

## 菜单

```python
from tkwebui import MenuButton, ThemedMenu, icon

button = MenuButton(root, text='更多操作')
menu = ThemedMenu(button, tearoff=False)
menu.add_command(label='新建', image=icon(root, 'edit', 16), compound='left', accelerator='Ctrl+N', command=create)
submenu = ThemedMenu(menu, tearoff=False)
submenu.add_command(label='CSV', command=export_csv)
menu.add_cascade(label='导出为', menu=submenu)
button.configure(menu=menu)
button.pack()
```

右键菜单调用 `menu.tk_popup(event.x_root, event.y_root)`。MenuButton 和 OptionMenu 的默认浮层也使用同一实现。

↑/↓ 选择，→ 展开子菜单，←/Escape 返回上一层，最外层 Escape 关闭；点击外部或窗口失去焦点时关闭并恢复抓取。快捷键文字仅作展示，实际快捷键由应用自己绑定。菜单栏未封装为单独组件，可以用 MenuButton 按工具栏布局组合。

## 多列列表（可排序）

```python
from tkwebui import SortableTreeview
tree = SortableTreeview(parent, columns=('name', 'count'), show='headings')
tree.heading('name', text='名称')
tree.heading('count', text='数量')
tree.insert('', 'end', values=('资料 2', 10))
tree.insert('', 'end', values=('资料 10', 2))
```

点击原生表头即可排序，表头显示方向箭头：数字按数值，文本按自然顺序（“资料 2”排在“资料 10”前面）；再次点击反向，空值放末尾，保留选中行。

- 已有 ttk.Treeview 可调用 `enable_sorting(tree)`；`configure_table(tree)` 也默认启用排序。
- 已有自定义 heading command 会保留，不会被覆盖。`configure_table(tree, sortable=False)` 可关闭自动排序。
- 更改 columns 后再次调用 `enable_sorting(tree)` 安装新列；`SortableTreeview.sort_by(column, reverse=None)` 支持程序调用。
- `configure_table` 的自动列宽和按需滚动条针对带表头的平面列表；树节点直接用 ttk.Treeview。
- RoundedListbox 是无表头的原生 Listbox 子类，适用于单列选项，不负责列排序。

### 多列列表框的对齐方式

`ttk.Treeview` 和 `SortableTreeview` 使用相同的原生接口。`anchor='w'` 为左对齐，`'center'` 为居中，`'e'` 为右对齐；表项和表头分别设置，互不影响：

```python
tree.column('name', anchor='w')       # 名称列的表项左对齐
tree.column('count', anchor='e')      # 数量列的表项右对齐
tree.heading('name', anchor='w')      # 名称列的表头左对齐
tree.heading('count', anchor='e')     # 数量列的表头右对齐

# 所有列的表项和表头都居中
for key in tree['columns']:
    tree.column(key, anchor='center')
    tree.heading(key, anchor='center')
```

可在创建列后或运行期间设置；排序、`configure_table(tree)` 和窗口缩放不会改变对齐设置。`DataTable` 的底层列表为 `table.tree`，例如 `table.tree.column('count', anchor='e')`。这是整列设置，不能给同一列的不同行分别指定对齐方式。树形列表的树节点列使用 `tree.column('#0', anchor='w')`。

## 可编辑表格（单元格）

```python
from tkwebui import Spreadsheet
sheet = Spreadsheet(parent, data=[['项目', '数量'], ['资料整理', '12']], rows=24, columns=8)
sheet.pack(fill='both', expand=True)
```

操作：

- 单击定位活动单元格；拖动或 Shift+点击/方向键选择矩形；Ctrl+点击追加/切换非连续单元格。
- 点击列头/行号选择整列/整行；Ctrl+A 全选。
- Ctrl+C：复制所选单元格为 TSV，可直接粘贴到 Excel。非连续选区按最小外接矩形输出，未选中的间隙是空单元格。
- 复制时统一使用 LF 交给 Tk，由 Windows 剪贴板转换为 CRLF，避免 Excel 将重复回车解释为空行。
- Ctrl+V：以当前蓝色边框的活动单元格作为左上角粘贴，按剪贴板的原行列展开；空间不足时自动扩展表格。
- 粘贴不重复填充整个选区；非连续复制留下的空单元格，粘贴时会按空值覆盖对应位置。
- 双击/F2/Enter 编辑，直接输入字符也可开始编辑；Enter 保存并下移，Tab 保存并右移，Escape 取消。
- Delete 清空所选值；Ctrl+Z / Ctrl+Y 撤销与重做最近 100 次修改，扩展后的表格尺寸不会随撤销收缩。
- 编辑单元格期间 Ctrl+C/V 操作编辑框文字，退出编辑后操作单元格选区。

API（坐标均从 0 开始）：

```text
sheet.get_data() / set_data(data, rows=..., columns=...)
sheet.get_cell(row, column) / set_cell(row, column, value)
sheet.select(row, column, extend=False, add=False)
sheet.get_selection()  -> [(row, column), ...]
sheet.active           -> (row, column)
sheet.copy()           -> 写入剪贴板并返回 TSV
sheet.paste(text=None) -> 从传入 TSV 或剪贴板粘贴
sheet.undo() / redo()
<<SheetChanged>> / <<SheetSelect>> 事件
```

表格只编辑和复制单元格值，不提供 Excel 文件读写、公式计算、合并单元格或格式复制。默认最多 1,000,000 个单元格，可通过 `max_cells` 调整。画面只绘制可见区域，数据保存在内存。

## 文本框、列表框与窗口操作栏

RoundedText 保留 Text 的编辑、撤销、tags 与滚动接口；RoundedListbox 保留 Listbox 的选择和列表 API。二者的 pack/grid/place 作用于圆角外壳，文本/列表方法和 `winfo_*` 作用于内部原生控件。

Demo 第 04 页分别展示「单列列表」（RoundedListbox）、「多列列表」（SortableTreeview）和「树形列表」（ttk.Treeview）；第 07 页的「可编辑表格」（Spreadsheet）按单元格选择、编辑和复制粘贴。多列列表按整行选择，不等同于可编辑表格。

### 按需滚动条

滚动条默认不占空间，仅在内容超出当前可视区域时出现；删除内容、清除筛选或扩大窗口后，内容能完整显示时自动隐藏。横向和纵向分别判断，不按固定条目数判断。

- RoundedText、RoundedListbox 内置按需滚动条；文本自动换行时不显示无用的横向滚动条。传入 `scrollbars=False` 可关闭内置滚动条。设置自己的 `xscrollcommand` / `yscrollcommand` 时，对应方向交由调用方管理，避免重复滚动条。
- Spreadsheet 根据实际行列区域显示滚动条；空白单元格也是可编辑区域的一部分。
- DataTable 根据当前页及筛选后的可见条目显示滚动条。
- ScrollArea、卡片列表，以及使用 ScrollArea 的下拉选项和菜单浮层按内容高度显示滚动条。
- 原生 ttk.Treeview 不自带滚动条。多列列表可配合 `configure_table(tree)` 管理已有滚动条并启用表头排序；树形列表或普通滚动控件可使用 `AutoScrollbar`。

```python
from tkwebui import AutoScrollbar
area = ttk.Frame(parent)
area.pack(fill='both', expand=True)
area.columnconfigure(0, weight=1)
area.rowconfigure(0, weight=1)
tree = ttk.Treeview(area)
tree.grid(row=0, column=0, sticky='nsew')
bar = AutoScrollbar(area, command=tree.yview)
bar.grid(row=0, column=1, sticky='ns')
tree.configure(yscrollcommand=bar.set)
```

AutoScrollbar 使用 `grid` 布局，以便隐藏和恢复时保留布局位置。外层容器仍可以使用 `pack` 或 `place`。`apply_theme()` 只负责样式；普通 `ttk.Treeview` 的表头排序需要显式调用 `enable_sorting(tree)` / `configure_table(tree)`，或改用 `SortableTreeview`。

### 窗口显示后再构建的页面

ScrollArea 的内容宽度、滚动条以及按 `<Configure>` 调整换行的文字，都依赖控件显示到屏幕上之后才到达的窗口事件。窗口显示后再构建并直接 `pack` 的页面，会先按控件的自然宽度画出来，再拉伸到实际宽度。先用 `prepare(width, height)` 在可视区域外按最终尺寸完成布局，再显示：

```python
page = ui.ScrollArea(deck)
build(page.body)
page.prepare(deck.winfo_width(), deck.winfo_height())
current.pack_forget()          # 构建期间旧页面保持可见
page.pack(fill='both', expand=True)
```

`prepare()` 不处理用户输入，只向尺寸变化的控件补发 `<Configure>`。Demo 的 `show_page()` 即按此方式切换页面。

WindowChrome 提供置顶、最小化、最大化、移动和边缘缩放；关闭窗口前调用 `detach()`。非 Windows 平台保留系统标题栏。尚未提供 Windows 11 最大化按钮的悬停布局面板。

普通窗口无需传入 `sidebar`，四周缩放区域与主背景同色；只有左侧确实存在侧栏时才传入 `sidebar=sidebar_widget`，以保持左边缘与侧栏底色一致。

## 打包后的路径

源码运行时用 `Path(__file__).resolve().parent` 定位程序目录；打包成 EXE 后用 `Path(sys.executable).resolve().parent`；包内资源单独使用 `sys._MEIPASS`。`demo.py` 从其他工作目录启动时也能找到 `tkwebui`，启动异常会写入同目录的 `startup_error.log`。
