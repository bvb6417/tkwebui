"""最小示例：主题 + 按钮 + 单元格表格 + 折线图。运行：python examples/minimal.py"""
import sys
from pathlib import Path
import tkinter as tk
from tkinter import ttk

# 让示例找到上一级目录里的 tkwebui；把 tkwebui 文件夹复制到你的项目后不需要这一行。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tkwebui import enable_dpi_awareness, apply_theme, Spreadsheet, LineChart

enable_dpi_awareness()      # 在创建 Tk() 之前调用，高分屏下不发虚
root = tk.Tk()
root.title('TkWebUI 最小示例')
apply_theme(root)           # 在创建控件之前调用

ttk.Button(root, text='保存', style='Primary.TButton').pack(padx=16, pady=8)
Spreadsheet(root, data=[['项目', '数量'], ['资料整理', '12']], rows=12, columns=6).pack(fill='both', expand=True)
LineChart(root, values=[12, 18, 14, 26, 23], labels=['一', '二', '三', '四', '五']).pack(fill='both', expand=True)
root.mainloop()
