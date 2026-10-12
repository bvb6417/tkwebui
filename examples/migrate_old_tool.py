"""旧工具接入示例：一个普通的 ttk 小工具，只加了标注 ★ 的几行就换上新主题。"""
import sys
from pathlib import Path
import tkinter as tk
from tkinter import ttk

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tkwebui import enable_dpi_awareness, apply_theme, ThemedCombobox, RoundedText  # ★

enable_dpi_awareness()                                  # ★ 原来创建 Tk() 之前
root = tk.Tk()
root.title('批量重命名（旧工具示例）')
apply_theme(root)                                       # ★ 原来创建控件之前

form = ttk.Frame(root, padding=16)
form.pack(fill='both', expand=True)
form.columnconfigure(1, weight=1)
ttk.Label(form, text='文件夹').grid(row=0, column=0, sticky='w', pady=6)
ttk.Entry(form).grid(row=0, column=1, sticky='ew', padx=8)
ttk.Button(form, text='浏览').grid(row=0, column=2)
ttk.Label(form, text='命名规则').grid(row=1, column=0, sticky='w', pady=6)
rule = ThemedCombobox(form, values=['序号_原名', '日期_序号', '自定义'], state='readonly')  # ★ 原来是 ttk.Combobox
rule.current(0)
rule.grid(row=1, column=1, columnspan=2, sticky='ew', padx=(8, 0))
ttk.Checkbutton(form, text='包含子文件夹').grid(row=2, column=1, sticky='w', pady=6)
log = RoundedText(form, height=8)                       # ★ 原来是 tk.Text
log.grid(row=3, column=0, columnspan=3, sticky='nsew', pady=8)
form.rowconfigure(3, weight=1)
log.insert('end', '旧代码的布局和业务逻辑保持不变。\n')
buttons = ttk.Frame(form)
buttons.grid(row=4, column=0, columnspan=3, sticky='e')
ttk.Button(buttons, text='预览').pack(side='left', padx=4)
ttk.Button(buttons, text='开始重命名', style='Primary.TButton').pack(side='left')
root.mainloop()
