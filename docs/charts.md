# TkWebUI 原生交互图表

运行依赖：Python 标准库 + tkinter。没有 NumPy、Matplotlib、浏览器、WebView 或图表运行时依赖。

运行 `python demo.py --page 8` 打开“原生交互图表”页。可以直接操作图例、悬停、点击、缩放和更新数据。

| 控件 | 说明 |
| --- | --- |
| LineChart | 折线图：多系列、缺失值断线、点提示、十字线、缩放、平移 |
| ColumnChart | 柱状图：分类标签、多系列分组、正负值、悬停、点击 |
| ScatterChart | 散点图：多系列、点定位、十字线、双轴缩放与平移 |
| DonutChart | 环形图：数值/比例提示、图例开关、可见项合计 |
| PieChart | 饼图：与 DonutChart 共用实现，默认没有中间空洞 |

## 基本用法

```python
import tkinter as tk
from tkwebui import enable_dpi_awareness, apply_theme, LineChart

enable_dpi_awareness()
root = tk.Tk()
apply_theme(root)
chart = LineChart(
    root,
    values=[12, 18, 14, 26, 23],
    labels=['一月', '二月', '三月', '四月', '五月'],
    on_click=lambda point: print(point),
)
chart.pack(fill='both', expand=True, padx=16, pady=16)
root.mainloop()
```

### 更新数据

```python
chart.set_data(values=[15, 20, 18, 30, 28])
```

## 多系列折线 / 分组柱状图

```python
chart = ColumnChart(parent, labels=['A', 'B', 'C'], series=[
    {'name':'计划', 'values':[10, 20, 30], 'color':'#087DFF'},
    {'name':'实际', 'values':[12, 18, 32], 'color':'#19A58B'},
])
```

## 散点图 / 数值横轴折线

```python
chart = ScatterChart(parent, series=[
    {'name':'观测', 'points':[(1, 2), (2.5, 4), (4, 3)]},
])
```

LineChart 也支持 points；顺序按照输入的顺序连接，不自动重排数据。

LineChart 的 values 中用 None 或 NaN 表示缺失，折线会在该处断开。非有限值不参与绘图。

ColumnChart 使用 values + labels；空值跳过。

## 饼图 / 环形图

```python
chart = DonutChart(parent, data=[('已完成',42), ('处理中',18), ('待处理',12)])
chart.set_hole(0)       # 切换饼图
chart.set_hole(.62)     # 切回环形
```

也可使用 {'name':'已完成','value':42,'color':'#087DFF'} 字典形式。

数值必须有限且非负；零值不绘制扇区，总值为 0 时显示空状态。

## 交互

- 点击图例：隐藏 / 显示系列；图例可通过 Tab 聚焦，再用空格或 Enter 操作。
- 悬停：显示数值；折线按最近横坐标定位，散点按邻近点定位。
- 点击数据：调用 on_click，并生成 <<ChartSelected>>。最近选择位于 chart.last_selection。
- 折线滚轮：默认缩放 x 轴，Shift+滚轮缩放 y 轴。
- 散点滚轮：默认同时缩放两轴，Shift+滚轮只缩放 y 轴。
- 折线 / 散点：缩放后拖动平移；双击、Escape 或“重置”恢复全图。
- 柱状图与饼图支持悬停、点击、图例筛选，不提供坐标缩放。
- 饼图比例和中间合计按当前可见项重新计算。

## 共同 API

```text
set_data(...)            更新数据；折线、柱状图、散点默认重置视图
get_data()               返回数据副本，可传回 set_data()
toggle_series(name)      切换图例对应项
reset_view()             折线 / 散点恢复全图
on_click                点击回调
last_selection          最后一次点击的数据字典
<<ChartSelected>>       点击事件
<<ChartSeriesChanged>>  图例变化事件
<<ChartViewChanged>>    折线 / 散点缩放或平移变化事件
```

## 常用构造参数

```text
height=230              画布逻辑高度，按 DPI 缩放
y_formatter=callable    折线 / 柱状 / 散点的纵轴及提示数值格式
x_formatter=callable    数值横轴及提示横坐标格式
value_formatter=callable 饼图 / 环形图的数值格式
tooltip_formatter=callable 自定义提示文本，接收数据字典
```

## 点击数据格式

折线 / 柱状 / 散点：{'series':名称, 'index':原数据序号, 'x':横坐标, 'y':数值, 'label':标签, 'kind':图类型}

饼图 / 环形图：{'name':名称, 'value':数值, 'percent':可见项占比, 'kind':'pie'或'donut'}

## 定位与性能

适用于小工具中几十、几百到少量几千数据点的常见图表，具体流畅度取决于点数、控件大小和机器。

没有加入公式计算、拟合、3D、海量数据分析、WebGL 或通用图像导出功能。

悬停只更新覆盖层，不重建图形。散点使用屏幕网格索引定位；折线使用横坐标二分定位。

数据变化、缩放和大小变化合并到短周期回调重绘；这不是固定帧率保证。

折线、圆点、饼图和环形图先在内存中抗锯齿绘制，再作为 PhotoImage 显示到 Canvas。Windows 使用系统 GDI+，其他平台使用标准库像素覆盖回退。

文字、坐标轴、提示和命中检测继续使用 Tk。无需 Pillow、NumPy 或浏览器；缩放后按当前分辨率重新绘制。

简易的 `BarChart`（tkwebui/core.py）仍然保留；需要交互柱状图时使用 `ColumnChart`。
