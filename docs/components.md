# 扩展组件：表单、通知、仪表、数据表、图片与外观

运行 `python demo.py` 后，可在以下页面看到这些组件：

- 第 9 页：日期输入、日历、表单校验、带数值输入的滑块、对话框与轻提示。
- 第 10 页：圆环/半圆仪表、带文字的进度条、状态标签和按钮变体。
- 第 11 页：搜索、按列筛选、分页、列管理和 CSV 导出。
- 第 12 页：图片预览、颜色选择、字体选择。

只需 Python 标准库和 Tkinter。图片框在已安装 Pillow 时可支持更多格式和平滑缩放，但不强制安装。组件外观与主题一致：蓝色主色、小圆角、轻量边框和统一浮层。

## 1. 日期选择

```python
from datetime import date
from tkwebui import DateEntry
picker = DateEntry(parent, value=date(2026,10,12), minimum=date(2026,1,1), maximum=date(2026,12,31))
picker.pack(fill='x')
value = picker.get_date()   # datetime.date；空输入返回 None；无效输入抛 ValueError
picker.set_date(date(2026,11,1))
picker.clear()
picker.state(['disabled'])
```

可直接键入 YYYY-MM-DD，或点击日历。日历支持年/月输入、上一月/下一月、今天、清空和范围限制。

打开按钮使用在内存生成的日历图标，按 DPI 缩放，不依赖字体中的符号或外部图片。

validate() 返回 bool，并更新输入框错误状态。日历选中触发 <<DateEntrySelected>>，也可传 command(date_or_none)。

日期弹层按 Escape、点击外部或失去焦点关闭；从已有模态弹窗打开时会恢复先前抓取。

## 2. 表单校验

```python
from tkwebui import ValidatedEntry
amount = ValidatedEntry(parent, label='数量', kind='integer', required=True, minimum=1, maximum=100)
amount.pack(fill='x')
amount.set(10)
if amount.validate():
    value = amount.get_value()    # 按 kind 返回 int / float / date / str
```

kind 支持 text、integer、float、date、email。email 是常用格式检查，不是完整 RFC 邮件地址解析器。

pattern 可指定 fullmatch 正则；validator(value) 可返回错误文字、False，或返回 None/True 表示通过。

失焦/Enter 校验，错误显示在字段下方。get() 返回原始字符串，get_value() 会验证并返回类型化结果。

entry 属性是内部 ttk.Entry，variable 是文本变量。不会修改业务数据或自动提交整个表单。

## 3. 带数值的滑块

```python
from tkwebui import ValueSlider
slider = ValueSlider(parent, from_=0, to=5, step=.1, unit='秒')
slider.set(1.5)
value = slider.get()
```

滑块和数字微调框双向同步；数字按 Enter 或失焦确认，统一按步长取值、按范围限制。

滑块左侧已选范围以主题色填充，右侧为浅灰轨道；禁用时显示灰色填充。

支持 variable=DoubleVar、command(value)、state(['disabled'])。

## 4. 通用对话框

```python
from tkwebui import Dialogs
if Dialogs.confirm(root, '确认删除所选记录吗？', danger=True):
    delete_selected()
name = Dialogs.ask_string(root, '请输入名称', initial='新项目', title='重命名')
count = Dialogs.ask_integer(root, '请输入数量', initial=10, minimum=0, maximum=100)
value = Dialogs.ask_float(root, '请输入系数', initial=1.0)
Dialogs.info(root, '任务完成')
Dialogs.warning(root, '请检查输入')
Dialogs.error(root, '任务执行失败')
```

confirm 返回 bool；输入对话框取消返回 None，合法的 0 或空字符串不会被当作取消。

对话框等待结果期间，Tk 事件循环继续运行。需要异步管理时可直接创建 MessageDialog / InputDialog，并访问 result、primary、secondary、field。

## 5. 轻提示

```python
from tkwebui import notify
toast = notify(root, '已保存', kind='success', duration=3000)
toast.hide()
```

kind 支持 primary/success/warning/danger/info/neutral。position 可选 bottom-right 或 top-right。

非阻塞，不抓取输入；悬停延缓消失。每个角落最多保留三条，并按窗口可用高度移除最旧提示，避免堆叠重叠。

duration<=0 时手动关闭；宿主隐藏或销毁时跟随关闭。ToastNotification(...).show_toast() 可显式创建。

## 6. 带文字进度条

```python
from tkwebui import TextProgress
progress = TextProgress(parent, maximum=100, mask='已完成 {value:.0f} / {maximum}')
progress.pack(fill='x')
progress.set(65)
loading = TextProgress(parent, mode='indeterminate', text='正在处理…')
loading.start()
loading.stop()
```

支持 variable、get/set/step、orient='vertical'、length、thickness 和 kind 状态色。

mask 可使用 value、maximum、percent。text 非空时显示固定文字。

工作任务仍应由应用安排，长时间计算不应直接阻塞 Tk 主线程。

## 7. 仪表

```python
from tkwebui import Meter
meter = Meter(parent, value=65, maximum=100, unit='%', subtext='完成率', interactive=True)
semi = Meter(parent, meter_type='semi', thresholds=[(60,'success'),(85,'warning'),(100,'danger')])
meter.set(75)
```

meter_type 为 full 或 semi；支持 minimum/maximum、variable、get/set、command(value)。

thresholds 按量程百分比设置颜色上界。interactive=True 时可以鼠标调整、方向键增减、Home/End 到端点。

set 或交互操作产生 <<MeterChanged>>；外部变量也会更新图形。

仪表环形边缘通过内存抗锯齿图层绘制，仍为 Tkinter 控件；Windows 使用自带 GDI+，不需要安装额外依赖。

## 8. 状态标签与按钮变体

```python
from tkwebui import Badge
Badge(parent, text='已完成', kind='success').pack()
ttk.Button(parent, text='删除', style='Danger.TButton').pack()
ttk.Button(parent, text='重试', style='Warning.Outline.TButton').pack()
ttk.Button(parent, text='查看详情', style='Info.Link.TButton').pack()
```

Primary / Success / Warning / Danger / Info / Neutral 均提供对应实心、Outline、Link 按钮；Badge 为对应状态标签。

apply_theme 自动安装样式，无需单独调用 configure_form_styles。

## 9. 数据管理表格

```python
from tkwebui import DataTable
table = DataTable(parent,
    columns=[{'key':'name','text':'名称','width':220}, {'key':'count','text':'数量','width':100}],
    rows=[['资料 A',10], ['资料 B',2]], page_size=10)
table.pack(fill='both', expand=True)
table.search('资料')
table.filter_column('count', 10)
table.clear_filters()
table.sort_by('count', reverse=False)
table.set_visible_columns(['name'])
table.reset_layout()
table.export_csv('result.csv', scope='filtered')
```

列 key 唯一；行长度必须与列数一致。列可用字符串列表简写，key 此时为 '0'、'1' 等。

搜索为全列、不区分大小写的子串匹配；按列筛选为精确匹配，可组合不同列。

排序在全部筛选结果上执行，然后分页，不只排序当前页。

goto_page(index) 从 0 开始；set_page_size(n)、set_rows(rows)、insert_row(values)、get_rows(scope) 可程序调用。

scope 支持 all / filtered / page / selected；选中行跨页保留，selected 也可能包含当前筛选未显示的行。

右键可排序、左右移动/隐藏列、恢复布局和导出。CSV 使用 UTF-8 BOM，保留全部数据列，包括隐藏列。

本控件用于管理记录；单元格编辑和 Ctrl+C/V 仍使用原来的 Spreadsheet。

## 10. 图片框

```python
from tkwebui import ImageViewer
viewer = ImageViewer(parent, height=300)
viewer.pack(fill='both', expand=True)
ok = viewer.load('example.png')
viewer.set_image(photo_image)  # tkinter.PhotoImage，内部保留副本
viewer.fit()
viewer.set_zoom(1)             # 原图 1:1，受预览尺寸上限限制
viewer.clear()
```

支持打开文件、适应窗口、1:1、放大缩小、滚轮锚点缩放、拖动平移和双击适应窗口。

棋盘格显示透明区域；状态栏显示尺寸和实际缩放比例。

无 Pillow 时使用 Tk 原生 PNG/GIF/PPM/PGM 解码和近邻缩放；可显示静态帧，不播放 GIF 动画。

已安装 Pillow 时，文件加载可支持 JPEG/BMP/WebP 等 Pillow 支持的格式，并采用平滑缩放及 EXIF 方向处理。

打开失败返回 False，保留原图，并在 error 与状态栏说明原因。load 的路径使用 pathlib.Path。

为控制小工具内存，默认预览最多约四百万显示像素、最长边 4096 像素；大图的 1:1/放大可能受限。max_render_pixels 可调整总显示像素上限。

图片内容不被修改；未提供绘画、裁剪保存或屏幕取色功能。

## 11. 颜色选择

```python
from tkwebui import ColorPicker, ColorDialog
picker = ColorPicker(parent, color='#087DFF', command=lambda color: print(color))
color = picker.get_color()    # '#RRGGBB'
picker.set_color('#ABC')
chosen = ColorDialog(root, color='#087DFF').show_result()  # 取消为 None
```

提供饱和度/亮度渐变面板、色相条、HEX/RGB 输入、预设色和复制 HEX。

get_color 验证当前 HEX 文本；apply_hex / apply_rgb 返回 bool。颜色变化产生 <<ColorChanged>>。

这是颜色选择器，没有跨屏幕吸管功能。

## 12. 字体选择

```python
from tkwebui import FontPicker, FontDialog
picker = FontPicker(parent)
selected_font = picker.get_font()
selected_font = FontDialog(root).show_result()   # tkinter.font.Font；取消为 None
```

可输入字体名筛选候选列表、设置字号、粗体和斜体，并预览中英文与数字。

候选列表最多显示 80 项，可通过输入缩小范围；提交时要求完整的已安装字体名称。

返回独立 Font，调用方应保留引用。只修改预览字体，不会自动覆盖整个应用的字体。
