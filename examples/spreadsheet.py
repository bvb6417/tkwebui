"""单元格表格示例：和 Excel 互相复制粘贴，并在 Python 里读取数据。"""
import sys
from pathlib import Path
import tkinter as tk
from tkinter import ttk

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tkwebui import enable_dpi_awareness, apply_theme, Spreadsheet, notify

enable_dpi_awareness()
root = tk.Tk()
root.title('Spreadsheet 示例')
root.geometry('900x560')
apply_theme(root)

bar = ttk.Frame(root, padding=(16, 12))
bar.pack(fill='x')
ttk.Label(bar, text='在 Excel 中复制一块区域，单击活动单元格后按 Ctrl+V 粘贴；Ctrl+C 可复制回 Excel。').pack(side='left')
sheet = Spreadsheet(root, data=[['站点', '流量', '压力'], ['A', '12.5', '0.32'], ['B', '9.8', '0.29']], rows=30, columns=10)
sheet.pack(fill='both', expand=True, padx=16, pady=(0, 16))

def summary():
    rows = [row for row in sheet.get_data() if any(cell.strip() for cell in row)]
    notify(root, f'共 {len(rows)} 行非空数据', kind='success')

ttk.Button(bar, text='统计非空行', style='Primary.TButton', command=summary).pack(side='right')
sheet.bind('<<SheetChanged>>', lambda e: root.title('Spreadsheet 示例 *'))
root.mainloop()
