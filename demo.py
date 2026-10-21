"""TkWebUI widget gallery. Double-click or run: python demo.py [--page N]

Standard library only; demo data stays in memory and is not saved.
"""
from __future__ import annotations
import argparse
from datetime import date
from pathlib import Path
import random
import sys
import tkinter as tk
from tkinter import ttk
import traceback

sys.dont_write_bytecode = True
BASE = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

import tkwebui as ui
from tkwebui import (RoundedText, SectionCard, configure_table, ThemedCombobox, ThemedMenu,
                     MenuButton, OptionMenu, RoundedListbox, SquareSwitch, SortableTreeview, Spreadsheet)

PAGES = ['01  输入与按钮', '02  选择与进度', '03  容器与布局', '04  单列、多列与树形列表', '05  菜单与弹窗', '06  组合组件',
         '07  可编辑表格', '08  原生交互图表', '09  表单与通知', '10  仪表与状态', '11  数据管理', '12  图片与外观']


class ScrollPage(ui.ScrollArea):
    def __init__(self, parent):
        super().__init__(parent)
        self.body.configure(padding=12)


class Gallery(tk.Tk):
    def __init__(self, page=0):
        super().__init__()
        self.withdraw()
        self.errors = []
        self.title('TkWebUI · 现代 Web 风格 Tkinter 控件')
        self.scale = self.winfo_fpixels('1i') / 96
        self.px = lambda v: max(1, round(v * self.scale))
        ui.apply_theme(self)
        self.style = ttk.Style(self)
        self.style.configure('Demo.Note.TLabel', foreground='#697180', font=('Microsoft YaHei UI', 9))
        self.style.configure('Demo.Strong.TLabel', font=('Microsoft YaHei UI', 10, 'bold'))
        self._window_icon = ui.icon(self, 'controls', 32)
        self.iconphoto(True, self._window_icon)
        self.status = tk.StringVar(value='可直接操作控件。')
        self.page_var = tk.StringVar(value=PAGES[page])
        self.pages = {}
        self.refs = {}
        self.variables = []
        self.active_page = -1
        self.dialog = None
        self.build()
        self.position()
        self.reveal(page)
        self.protocol('WM_DELETE_WINDOW', self.close)

    def reveal(self, page):
        """Show the window only after Tk has applied its size and laid it out.

        Once the native window exists, Tk applies wm geometry at the first map,
        so a withdrawn window is still 1x1 and the first page would be laid out
        while visible. On Windows the window is mapped DWM-cloaked (laid out,
        not composed) until the page has settled.
        """
        cloak = None
        if sys.platform == 'win32':
            import ctypes
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            def cloak(on):
                value = ctypes.c_int(on)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 13, ctypes.byref(value), 4)  # DWMWA_CLOAK
            cloak(1)
        self.deiconify()
        self.update()       # real window size
        self.show_page(page)
        self.update()       # page layout, scroll region and wrapping
        if cloak is not None:
            cloak(0)

    def report_callback_exception(self, exc, value, tb):
        detail = ''.join(traceback.format_exception(exc, value, tb))
        self.errors.append(detail)
        sys.stderr.write(detail)
        if hasattr(self, 'status'):
            self.status.set('出现错误：' + str(value))

    def position(self):
        left, top, right, bottom = 0, 0, self.winfo_screenwidth(), self.winfo_screenheight()
        if sys.platform == 'win32':
            import ctypes
            from ctypes import wintypes
            rect = wintypes.RECT()
            if ctypes.windll.user32.SystemParametersInfoW(48, 0, ctypes.byref(rect), 0):
                left, top, right, bottom = rect.left, rect.top, rect.right, rect.bottom
        gap = self.px(10)
        width = min(right-left-2*gap, self.px(1120))
        height = min(bottom-top-self.px(70), self.px(925))
        x = left+(right-left-width)//2
        y = top+self.px(16)
        self.geometry(f'{width}x{height}{x:+d}{y:+d}')
        self.minsize(self.px(660), self.px(500))

    def var(self, cls, value):
        variable = cls(self, value=value)
        self.variables.append(variable)
        return variable

    def build(self):
        toolbar = ttk.Frame(self, padding=(self.px(16), self.px(10)))
        toolbar.pack(fill='x')
        ttk.Button(toolbar, text='‹', width=3, command=lambda: self.navigate(-1)).pack(side='left')
        selector = ThemedCombobox(toolbar, textvariable=self.page_var, values=PAGES, state='readonly', width=27)
        self.refs['page_selector'] = selector
        selector.pack(side='left', padx=self.px(8))
        selector.bind('<<ComboboxSelected>>', lambda e: self.show_page(PAGES.index(self.page_var.get())))
        ttk.Button(toolbar, text='›', width=3, command=lambda: self.navigate(1)).pack(side='left')
        ttk.Separator(self).pack(fill='x')
        footer = ttk.Frame(self, padding=(self.px(16), self.px(9)))
        footer.pack(side='bottom', fill='x')
        ttk.Label(footer, textvariable=self.status, style='Demo.Note.TLabel').pack(side='left', fill='x', expand=True)
        ttk.Sizegrip(footer).pack(side='right')
        self.host = ttk.Frame(self)
        self.host.pack(fill='both', expand=True)
        note = 'TkWebUI · 小圆角、统一浮层、可编辑单元格表格与原生图表，仅依赖标准库'
        ttk.Label(self.host, text=note, style='Demo.Note.TLabel', padding=(self.px(18), self.px(8))).pack(fill='x')
        self.deck = ttk.Frame(self.host)
        self.deck.pack(fill='both', expand=True)
        self.bind('<Control-Prior>', lambda e: self.navigate(-1))
        self.bind('<Control-Next>', lambda e: self.navigate(1))

    def navigate(self, delta):
        self.show_page((self.active_page+delta) % len(PAGES))

    def show_page(self, index):
        if self.active_page == index:
            return
        if index not in self.pages:
            page = ScrollPage(self.deck)
            self.pages[index] = page
            page.body.columnconfigure((0, 1), weight=1, uniform='half')
            [self.inputs, self.choices, self.containers, self.tables, self.popups, self.composites, self.spreadsheet_page,
             self.charts_page, self.forms_page, self.feedback_page, self.dataview_page, self.media_page][index](page.body)
            # Lay the new page out at its final width while the current one is
            # still shown; otherwise its cards appear narrow and then widen.
            page.prepare(max(1, self.deck.winfo_width()), max(1, self.deck.winfo_height()))
        if self.active_page in self.pages:
            self.pages[self.active_page].pack_forget()
        self.pages[index].pack(fill='both', expand=True)
        self.active_page = index
        self.page_var.set(PAGES[index])
        hint = {3: '单列 / 多列 / 树形列表；多列列表支持表头排序', 6: '按单元格选择；双击编辑；支持与 Excel 复制粘贴'}.get(index, '可直接操作控件')
        self.status.set(f'{PAGES[index]}  ·  {hint}')

    def card(self, parent, title, row, col=0, span=1):
        box = ui.Card(parent, padding=self.px(16))
        box.grid(row=row, column=col, columnspan=span, sticky='nsew', padx=self.px(5), pady=self.px(6))
        ttk.Label(box, text=title, style='Demo.Strong.TLabel').pack(anchor='w', pady=(0, self.px(12)))
        return box

    def note(self, parent, text):
        label = ttk.Label(parent, text=text, style='Demo.Note.TLabel', wraplength=self.px(360), justify='left')
        label.pack(anchor='w', fill='x', pady=(self.px(8), self.px(5)))
        label.bind('<Configure>', lambda e: label.configure(wraplength=max(50, e.width)))
        return label

    def field(self, parent, label, widget):
        ttk.Label(parent, text=label).pack(anchor='w', pady=(self.px(8), self.px(5)))
        widget.pack(fill='x', pady=(0, self.px(3)))
        return widget

    def button(self, parent, text, command=None, primary=False, **kwargs):
        button = ttk.Button(parent, text=text, command=command or (lambda: self.status.set('已点击：'+text)),
                            style='Primary.TButton' if primary else 'TButton', **kwargs)
        button.pack(side='left', padx=(0, self.px(8)), pady=self.px(4))
        return button

    def inputs(self, page):
        box = self.card(page, '单行输入与数字框', 0)
        entry = self.field(box, '普通输入', ttk.Entry(box))
        entry.insert(0, '项目资料 / Project notes')
        self.refs['entry'] = entry
        hint = self.field(box, '输入提示（框内灰字，输入后消失）', ui.PlaceholderEntry(box, placeholder='请输入用户名'))
        self.refs['placeholder'] = hint
        pw = self.field(box, '密码输入', ttk.Entry(box, show='●'))
        pw.insert(0, 'tkwebui')
        invalid = self.field(box, '错误状态', ttk.Entry(box))
        invalid.insert(0, 'name@'); invalid.state(['invalid'])
        disabled = self.field(box, '禁用状态', ttk.Entry(box))
        disabled.insert(0, '暂不可编辑'); disabled.state(['disabled'])
        self.field(box, '数量  1—100', ttk.Spinbox(box, from_=1, to=100, textvariable=self.var(tk.IntVar, 12)))
        box = self.card(page, '下拉框与文本编辑', 0, 1)
        editable = self.field(box, '可编辑下拉框', ThemedCombobox(box, values=['工作资料', '个人笔记', '归档文件']))
        editable.set('工作资料'); self.refs['combo'] = editable
        readonly = self.field(box, '只读下拉框', ThemedCombobox(box, values=['普通', '重要', '稍后处理'], state='readonly'))
        readonly.current(1)
        choose = self.field(box, '未选择时的提示', ThemedCombobox(box, values=['普通', '重要', '稍后处理'], state='readonly'))
        ui.set_placeholder(choose, '请选择优先级…')
        ttk.Label(box, text='多行文本  ·  可编辑 / 撤销').pack(anchor='w', pady=(self.px(12), self.px(6)))
        area = ttk.Frame(box); area.pack(fill='both', expand=True)
        area.columnconfigure(0, weight=1); area.rowconfigure(0, weight=1)
        editor = RoundedText(area, height=8, width=20, wrap='word', undo=True)
        editor.grid(row=0, column=0, sticky='nsew')
        editor.insert('1.0', '这是一段可编辑的多行文本。\n\n观察边框圆角、内边距、焦点以及文字选择。\n\n可直接输入，按 Ctrl+Z 撤销。')
        self.refs['text'] = editor
        self.note(box, 'RoundedText 保留原生 Text 接口；ThemedCombobox 使用统一的下拉浮层。')
        box = self.card(page, '按钮层级', 1, span=2)
        row = ttk.Frame(box); row.pack(fill='x')
        self.button(row, '保存更改', primary=True)
        self.button(row, '普通按钮')
        quiet = ttk.Button(row, text='轻量操作', style='Quiet.TButton', command=lambda: self.status.set('轻量操作已执行'))
        quiet.pack(side='left', padx=self.px(5))
        self.button(row, '禁用按钮', state='disabled')
        row = ttk.Frame(box); row.pack(fill='x', pady=(self.px(8), 0))
        for name, label in [('search', '搜索'), ('edit', '编辑'), ('more', '更多')]:
            img = ui.icon(self, name, self.px(16))
            button = ttk.Button(row, image=img, style='Quiet.TButton', command=lambda text=label: self.status.set(text))
            button.image = img; button.pack(side='left', padx=self.px(4))
            ui.Tooltip(button, label)
        self.note(box, '图标在内存生成；悬停可以查看提示。')

    def choices(self, page):
        box = self.card(page, '复选、单选与开关', 0)
        for label, value in [('自动保存', True), ('显示详细信息', False)]:
            ttk.Checkbutton(box, text=label, variable=self.var(tk.BooleanVar, value)).pack(anchor='w', pady=self.px(7))
        ttk.Checkbutton(box, text='禁用的复选项', variable=self.var(tk.BooleanVar, False), state='disabled').pack(anchor='w', pady=self.px(7))
        ttk.Separator(box).pack(fill='x', pady=self.px(12))
        radio = self.var(tk.StringVar, '标准')
        row = ttk.Frame(box); row.pack(fill='x')
        for value in ['紧凑', '标准', '宽松']:
            ttk.Radiobutton(row, text=value, value=value, variable=radio).pack(side='left', padx=(0, self.px(12)))
        for label, value in [('开启通知', True), ('后台同步', False)]:
            ttk.Checkbutton(box, text=label, style='Switch.TCheckbutton', variable=self.var(tk.BooleanVar, value)).pack(anchor='w', pady=self.px(12))
        ttk.Separator(box).pack(fill='x', pady=self.px(8))
        ttk.Label(box, text='方角滑动开关', style='Demo.Note.TLabel').pack(anchor='w')
        self.refs['square_switches'] = []
        for disabled in (False, True):
            row = ttk.Frame(box); row.pack(fill='x', pady=self.px(5))
            for label, value in [('开启', True), ('关闭', False)]:
                switch = SquareSwitch(row, text=('禁用 · ' if disabled else '')+label,
                                      variable=self.var(tk.BooleanVar, value),
                                      state='disabled' if disabled else 'normal')
                switch.pack(side='left', padx=(0, self.px(24)))
                self.refs['square_switches'].append(switch)
        box = self.card(page, 'Toggle / Toolbutton', 0, 1)
        self.note(box, 'Toggle 是保持选中状态的按钮；多个按钮可分别开关。')
        row = ttk.Frame(box); row.pack(fill='x', pady=self.px(12))
        for name in ['收藏', '置顶', '标记']:
            ttk.Checkbutton(row, text=name, style='Toggle.TButton', variable=self.var(tk.BooleanVar, name == '收藏')).pack(side='left', padx=self.px(5))
        row = ttk.Frame(box); row.pack(fill='x', pady=self.px(10))
        for name in ['B', 'I', 'U']:
            ttk.Checkbutton(row, text=name, style='Toolbutton', variable=self.var(tk.BooleanVar, name == 'B')).pack(side='left', padx=self.px(5))
        self.note(box, '支持选中、悬停、焦点和禁用状态。')
        box = self.card(page, '进度条与进度选择器', 1)
        progress = self.var(tk.DoubleVar, 62)
        ttk.Progressbar(box, variable=progress, maximum=100).pack(fill='x', pady=self.px(12))
        slider = ui.ProgressSlider(box, variable=progress)
        slider.pack(fill='x', pady=self.px(10)); self.refs['slider'] = slider
        label = ttk.Label(box, text='62%'); label.pack(anchor='e')
        progress.trace_add('write', lambda *_: label.configure(text=f'{progress.get():.0f}%'))
        self.refs['progress_variable'] = progress
        loading = ttk.Progressbar(box, mode='indeterminate'); loading.pack(fill='x', pady=self.px(12))
        self.refs['loading'] = loading
        row = ttk.Frame(box); row.pack(fill='x')
        self.button(row, '开始加载', loading.start)
        self.button(row, '停止', loading.stop)
        self.note(box, '进度条与进度选择器采用一致轨道边距；可点击开始测试加载。')
        box = self.card(page, '垂直进度与滑块', 1, 1)
        row = ttk.Frame(box); row.pack(fill='x')
        ttk.Progressbar(row, orient='vertical', length=self.px(115), value=62).pack(side='left', padx=self.px(20))
        ttk.Scale(row, orient='vertical', from_=100, to=0, variable=self.var(tk.DoubleVar, 62), length=self.px(115)).pack(side='left', padx=self.px(20))
        right = ttk.Frame(row); right.pack(side='left', fill='x', expand=True)
        ttk.Scale(right, from_=0, to=100, variable=self.var(tk.DoubleVar, 40)).pack(fill='x', pady=self.px(12))
        ttk.Scale(right, from_=0, to=100, variable=self.var(tk.DoubleVar, 70), style='Horizontal.Tick.TScale').pack(fill='x', pady=self.px(12))
        self.note(box, '下方为紧凑条形滑块；支持水平和垂直方向。')

    def containers(self, page):
        box = self.card(page, '分组卡片 / SectionCard', 0)
        group = SectionCard(box, text='连接设置')
        group.pack(fill='x')
        self.field(group, '服务地址', ttk.Entry(group, textvariable=self.var(tk.StringVar, 'https://example.org')))
        ttk.Checkbutton(group, text='启动时自动连接', variable=self.var(tk.BooleanVar, True)).pack(anchor='w', pady=self.px(10))
        self.note(box, 'SectionCard 与原生 LabelFrame 均已统一为小圆角分组。')
        box = self.card(page, 'Notebook 标签页', 0, 1)
        notebook = ttk.Notebook(box); notebook.pack(fill='both', expand=True)
        for text in ['基本', '高级', '禁用']:
            body = ttk.Frame(notebook, padding=self.px(14))
            notebook.add(body, text=text, state='disabled' if text == '禁用' else 'normal')
            ttk.Label(body, text=f'{text}设置').pack(anchor='w', pady=self.px(10))
            ttk.Entry(body).pack(fill='x', pady=self.px(8))
            ttk.Checkbutton(body, text='启用当前选项', variable=self.var(tk.BooleanVar, False)).pack(anchor='w', pady=self.px(8))
        self.refs['notebook'] = notebook
        self.note(box, '小圆角标签，包含选中、悬停、焦点与禁用状态。')
        box = self.card(page, 'Panedwindow 分割面板', 1, span=2)
        paned = ttk.Panedwindow(box, orient='horizontal', height=self.px(160)); paned.pack(fill='both', expand=True)
        for text in ['资源区域', '内容工作区']:
            frame = ttk.Frame(paned, padding=self.px(14)); paned.add(frame, weight=1)
            ttk.Label(frame, text=text).pack(anchor='w', pady=self.px(10))
            ttk.Entry(frame).pack(fill='x', pady=self.px(8))
            ttk.Label(frame, text='拖动中间分隔条调整宽度', style='Demo.Note.TLabel').pack(anchor='w', pady=self.px(8))
        self.refs['paned'] = paned
        vertical = ttk.Panedwindow(box, orient='vertical', height=self.px(130))
        vertical.pack(fill='x', pady=(self.px(12), 0))
        for title in ['上方区域', '下方区域']:
            pane = ttk.Frame(vertical, padding=self.px(8))
            vertical.add(pane, weight=1)
            ttk.Label(pane, text=title).pack(anchor='w')
        self.refs['vertical_paned'] = vertical
        self.note(box, '横向与纵向分割条均已统一，保留较大的拖动命中区域。')
        box = self.card(page, '原生 LabelFrame / Sizegrip / Separator', 2, span=2)
        native = ttk.LabelFrame(box, text='原生 LabelFrame', padding=self.px(12)); native.pack(fill='x')
        ttk.Label(native, text='旧代码里的 ttk.LabelFrame 无需修改即可获得主题样式。').pack(anchor='w')
        row = ttk.Frame(box); row.pack(fill='x', pady=self.px(12))
        ttk.Label(row, text='水平与竖直分隔线').pack(side='left')
        ttk.Separator(row, orient='vertical').pack(side='left', fill='y', padx=self.px(16))
        ttk.Label(row, text='右下角手柄可缩放窗口').pack(side='left')
        ttk.Sizegrip(row).pack(side='right')
        ttk.Separator(box).pack(fill='x')

    def tables(self, page):
        box = self.card(page, '多列列表 · 整行选择 / 表头排序', 0, span=2)
        area = ttk.Frame(box); area.pack(fill='both', expand=True)
        area.rowconfigure(0, weight=1); area.columnconfigure(0, weight=1)
        tree = SortableTreeview(area, columns=('name', 'type', 'state', 'date'), show='headings', height=6, selectmode='extended')
        for key, title, width, anchor in [('name', '名称', 310, 'w'), ('type', '数量', 110, 'e'), ('state', '状态', 110, 'center'), ('date', '更新日期', 150, 'center')]:
            tree.heading(key, text=title, anchor=anchor)
            tree.column(key, width=self.px(width), minwidth=self.px(80), anchor=anchor)
        for i in range(18):
            tree.insert('', 'end', iid=f'r{i}', values=(f'{i+1:02d}  项目资料 / 示例条目', [2, 10, 3][i%3], ['已完成', '待处理'][i%2], '2026-10-12'))
        tree.selection_set('r1')
        tree.grid(row=0, column=0, sticky='nsew')
        vertical = ttk.Scrollbar(area, command=tree.yview); vertical.grid(row=0, column=1, sticky='ns')
        horizontal = ttk.Scrollbar(area, orient='horizontal', command=tree.xview); horizontal.grid(row=1, column=0, sticky='ew')
        tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        configure_table(tree)
        self.refs['table'] = tree
        self.note(box, '名称左对齐、数量右对齐、状态和日期居中；column(anchor=...) 设置表项，heading(anchor=...) 设置表头。点击表头排序；Ctrl / Shift 多选。')
        box = self.card(page, '树形列表 · 层级节点 / 展开折叠', 1)
        area = ttk.Frame(box); area.pack(fill='both', expand=True)
        area.columnconfigure(0, weight=1); area.rowconfigure(0, weight=1)
        tree = ttk.Treeview(area, height=7, show='tree', selectmode='browse'); tree.grid(row=0, column=0, sticky='nsew')
        vertical = ui.AutoScrollbar(area, command=tree.yview); vertical.grid(row=0, column=1, sticky='ns')
        horizontal = ui.AutoScrollbar(area, orient='horizontal', command=tree.xview); horizontal.grid(row=1, column=0, sticky='ew')
        tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.refs['tree_list'] = tree
        for title in ['工作空间', '个人收藏']:
            item = tree.insert('', 'end', text=title, open=True)
            for name in ['文档', '图片', '归档']:
                child = tree.insert(item, 'end', text=name)
                tree.insert(child, 'end', text='示例文件')
        self.note(box, '树形展开箭头、节点间距与选中状态均已统一。')
        box = self.card(page, '单列列表 · 单列选项 / 多选', 1, 1)
        listbox = RoundedListbox(box, height=7, selectmode='extended', exportselection=False)
        listbox.pack(fill='both', expand=True)
        for label in ['全部项目', '最近使用', '已收藏', '待处理', '已完成', '已归档', '回收站']:
            listbox.insert('end', label)
        listbox.selection_set(2)
        self.refs['single_list'] = listbox
        self.note(box, 'RoundedListbox 使用小圆角外框，支持悬停、多选与原生 Listbox 接口。')

    def make_menu(self, parent):
        menu = ThemedMenu(parent, tearoff=False)
        menu.add_command(label='新建项目', image=ui.icon(self, 'edit', self.px(15)), compound='left', accelerator='Ctrl+N', command=lambda: self.status.set('已新建示例项目'))
        menu.add_command(label='复制名称', command=lambda: self.status.set('已执行示例复制操作'))
        menu.add_separator()
        menu.add_checkbutton(label='显示已完成', variable=self.var(tk.BooleanVar, True))
        choice = self.var(tk.StringVar, '名称')
        for value in ['名称', '日期']:
            menu.add_radiobutton(label='按'+value+'排序', variable=choice, value=value)
        menu.add_separator()
        submenu = ThemedMenu(menu, tearoff=False)
        submenu.add_command(label='导出 CSV', command=lambda: self.status.set('已选择 CSV（演示）'))
        submenu.add_command(label='导出 JSON', command=lambda: self.status.set('已选择 JSON（演示）'))
        menu.add_cascade(label='导出为', menu=submenu)
        menu.add_command(label='暂不可用', state='disabled')
        return menu

    def popups(self, page):
        box = self.card(page, '统一菜单浮层', 0)
        menu = self.make_menu(self); self.refs['menu'] = menu
        button = ttk.Button(box, text='打开菜单', command=lambda: menu.tk_popup(button.winfo_rootx(), button.winfo_rooty()+button.winfo_height()+4))
        button.pack(anchor='w', pady=self.px(10))
        area = ttk.Label(box, text='也可以在这里点击鼠标右键', padding=self.px(20), relief='solid', borderwidth=1)
        area.pack(fill='x', pady=self.px(10)); area.bind('<Button-3>', lambda e: menu.tk_popup(e.x_root, e.y_root))
        self.note(box, '支持图标、快捷键文字、勾选项、单选项、分隔线、禁用项和级联子菜单；←/→ 展开返回，Esc 关闭。')
        box = self.card(page, 'Menubutton / OptionMenu', 0, 1)
        menubutton = MenuButton(box, text='更多操作')
        menubutton['menu'] = self.make_menu(menubutton)
        menubutton.pack(fill='x', pady=self.px(10))
        option = OptionMenu(box, self.var(tk.StringVar, '普通'), '普通', '普通', '重要', '紧急')
        option.pack(fill='x', pady=self.px(10))
        self.note(box, 'MenuButton 与 OptionMenu 共用统一浮层，支持只读选择和键盘操作。')
        box = self.card(page, 'Modal 弹窗与 Tooltip', 1)
        row = ttk.Frame(box); row.pack(fill='x')
        self.button(row, '打开表单弹窗', self.open_modal, primary=True)
        tip = self.button(row, '悬停查看提示')
        ui.Tooltip(tip, '这是工具提示，可以说明按钮的作用。')
        self.note(box, '弹窗包含输入、下拉和确认操作；Escape 关闭。')
        box = self.card(page, 'Dropdown 按钮式选择', 1, 1)
        value = self.var(tk.StringVar, '最近一周')
        dropdown = ui.Dropdown(box, ['最近一天', '最近一周', '最近一月'], variable=value)
        dropdown.pack(fill='x', pady=self.px(12))
        self.note(box, 'Dropdown 与 ThemedCombobox 共用 ChoicePopup。')

    def open_modal(self):
        if self.dialog is not None and self.dialog.winfo_exists():
            self.dialog.lift(); return self.dialog
        dialog = ui.Modal(self, '编辑项目', width=480, height=385)
        dialog.secondary.pack(side='right', padx=self.px(8))
        body = dialog.body
        self.dialog = dialog
        self.field(body, '项目名称', ttk.Entry(body, textvariable=self.var(tk.StringVar, '示例项目')))
        combo = ThemedCombobox(body, values=['普通', '重要', '紧急'], state='readonly'); combo.current(1)
        self.field(body, '优先级', combo)
        ttk.Checkbutton(body, text='保存后保留当前窗口设置', variable=self.var(tk.BooleanVar, True)).pack(anchor='w', pady=self.px(18))
        dialog.primary.configure(text='保存', command=lambda: (self.status.set('表单已保存（演示）'), dialog.close()))
        return dialog

    def composites(self, page):
        box = self.card(page, 'Sidebar 与分段选择', 0)
        row = ttk.Frame(box); row.pack(fill='x')
        sidebar = ui.Sidebar(row, [('all', '全部项目', 'library'), ('star', '我的收藏', 'star'), ('settings', '设置', 'settings')], lambda value: self.status.set('导航：'+value), width=self.px(165))
        sidebar.pack(side='left', fill='y'); sidebar.configure(height=self.px(175)); sidebar.select('all', notify=False)
        right = ttk.Frame(row, padding=(self.px(12), 0)); right.pack(side='left', fill='both', expand=True)
        ttk.Label(right, text='内容工作区').pack(anchor='w', pady=self.px(12))
        self.note(right, '切换导航观察选中状态。')
        value = self.var(tk.StringVar, 'week')
        ui.SegmentedControl(box, [('day', '日'), ('week', '周'), ('month', '月')], value).pack(anchor='w', pady=self.px(12))
        box = self.card(page, 'Accordion 与 SettingRow', 0, 1)
        accordion = ui.Accordion(box, '高级选项', opened=True, padding=self.px(12)); accordion.pack(fill='x')
        body = accordion.body
        setting = ui.SettingRow(body, '自动保存', help_text='每次编辑后自动保存。'); setting.pack(fill='x')
        ttk.Checkbutton(setting.action, style='Switch.TCheckbutton', variable=self.var(tk.BooleanVar, True)).pack()
        ttk.Checkbutton(body, text='保留历史记录', variable=self.var(tk.BooleanVar, True)).pack(anchor='w', pady=self.px(10))
        self.note(box, '折叠区和设置行可独立复用。')
        box = self.card(page, '卡片列表', 1, span=2)
        data = [dict(id=str(i), name=name, detail='本地演示数据 · 可点击右侧操作', tag='示例', mark=str(i+1), color='#087DFF')
                for i, name in enumerate(['项目资料', '个人收藏'])]
        cards = ui.CardList(box, lambda key, action, x, y: self.status.set(f'卡片 {key}：{action}'), height=self.px(158))
        cards.pack(fill='x'); cards.pack_propagate(False); cards.set_rows(data, '0')
        box = self.card(page, '简易柱状图 BarChart', 2)
        chart = ui.BarChart(box, [12, 20, 16, 28, 22], ['周一', '周二', '周三', '周四', '周五'])
        chart.canvas.configure(height=self.px(125)); chart.pack(fill='x')
        self.note(box, '悬停柱形可查看对应数值。')
        box = self.card(page, '窗口操作栏', 2, 1)
        ttk.Button(box, text='打开窗口操作示例', command=self.open_chrome).pack(anchor='w', pady=self.px(10))
        self.note(box, '此按钮打开 WindowChrome 操作示例，可测试拖动、缩放与置顶（仅 Windows）。')

    def open_chrome(self):
        window = tk.Toplevel(self); window.title('窗口操作示例')
        window.geometry(f'{self.px(500)}x{self.px(300)}+{self.winfo_rootx()+self.px(60)}+{self.winfo_rooty()+self.px(80)}')
        toolbar = ttk.Frame(window, padding=self.px(10)); toolbar.pack(fill='x')
        label = ttk.Label(toolbar, text='窗口操作'); label.pack(side='left')
        chrome = ui.WindowChrome(window, toolbar, drag_widgets=(toolbar, label))
        window._chrome = chrome
        def close():
            chrome.detach(); window.destroy()
        chrome.on_close = close
        window.protocol('WM_DELETE_WINDOW', close)
        area = ttk.Frame(window, padding=self.px(20)); area.pack(fill='both', expand=True)
        ttk.Entry(area).pack(fill='x', pady=self.px(12))
        ttk.Label(area, text='可测试拖动、缩放、最小化与最大化。').pack(anchor='w')
        return window

    def spreadsheet_page(self, page):
        box = self.card(page, '可编辑表格 · 单元格选择 / 编辑 / 复制粘贴', 0, span=2)
        actions = ttk.Frame(box); actions.pack(fill='x', pady=(0, self.px(10)))
        data = [['项目', '数量', '单价', '备注'], ['资料整理', '12', '25.50', '双击编辑'],
                ['图片归档', '8', '10.00', 'Ctrl+C / Ctrl+V'], ['数据校对', '20', '8.50', 'Shift 选择矩形区域'],
                ['文献检索', '6', '18.00', 'Ctrl+单击追加不连续单元格']]
        sheet = Spreadsheet(box, data=data, rows=24, columns=8, height=self.px(450))
        sheet.pack(fill='both', expand=True); sheet.pack_propagate(False)
        self.refs['sheet'] = sheet
        self.button(actions, '复制', lambda: sheet._shortcut(sheet.copy))
        self.button(actions, '粘贴', lambda: sheet._shortcut(sheet.paste), primary=True)
        self.button(actions, '撤销', sheet.undo)
        self.button(actions, '重做', sheet.redo)
        self.button(actions, '清空选区', sheet.clear_selection)
        self.note(box, '单击设置活动单元格；拖动或 Shift 多选；Ctrl+单击追加选区。粘贴以活动单元格为左上角，超出范围时自动扩展。')
        self.note(box, '双击 / F2 编辑，Enter 保存，Esc 取消。非连续选区复制时保留行列位置，间隙为空。可与 Excel 互相复制表格值。')

    def charts_page(self, page):
        controls = ttk.Frame(page, padding=(self.px(5), self.px(4)))
        controls.grid(row=0, column=0, columnspan=2, sticky='ew')
        chart_refs = {}
        def clicked(data):
            name = data.get('series', data.get('name', ''))
            value = data.get('y', data.get('value', ''))
            self.status.set(f'图表点击：{name}  ·  {data.get("label", "")}  ·  {value:g}')
        self.refs['charts'] = chart_refs
        box = self.card(page, '折线图 · 多系列与缩放', 1)
        line = ui.LineChart(box, series=[{'name': '本周', 'values': [12, 18, 14, 26, 23, 34, 29]},
                                         {'name': '上周', 'values': [8, 11, 15, 17, 19, 20, 24]}],
                            labels=['周一', '周二', '周三', '周四', '周五', '周六', '周日'], height=200, on_click=clicked)
        line.pack(fill='both', expand=True); chart_refs['line'] = line
        self.note(box, '悬停查看数值；滚轮缩放，拖动平移；双击或点击重置恢复。')
        box = self.card(page, '柱状图 · 分组与正负值', 1, 1)
        bars = ui.ColumnChart(box, series=[{'name': '流入', 'values': [12, 18, 15, 21, 24]},
                                           {'name': '流出', 'values': [-6, -9, -5, -8, -10]}],
                              labels=['一月', '二月', '三月', '四月', '五月'], height=200, on_click=clicked)
        bars.pack(fill='both', expand=True); chart_refs['bar'] = bars
        self.note(box, '点击柱形触发回调；点击图例可隐藏或显示对应系列。')
        box = self.card(page, '散点图 · 定位与探索', 2)
        rng = random.Random(7)
        scatter = ui.ScatterChart(box, series=[{'name': '观测 A', 'points': [(round(rng.uniform(8, 80), 1), round(rng.gauss(45, 12), 1)) for _ in range(45)]},
                                               {'name': '观测 B', 'points': [(round(rng.uniform(25, 95), 1), round(rng.gauss(65, 10), 1)) for _ in range(45)]}],
                                  height=200, on_click=clicked)
        scatter.pack(fill='both', expand=True); chart_refs['scatter'] = scatter
        self.note(box, '悬停定位数据点；滚轮同时缩放两轴，拖动探索局部。')
        box = self.card(page, '饼图 / 环形图 · 占比', 2, 1)
        donut = ui.DonutChart(box, data=[('已完成', 42), ('处理中', 18), ('待处理', 12)], height=200, on_click=clicked)
        donut.pack(fill='both', expand=True); chart_refs['donut'] = donut
        self.note(box, '悬停显示数值与占比；点击图例后按可见项重新计算占比。')
        counter = [0]
        def refresh():
            counter[0] += 1; rng = random.Random(counter[0]+20)
            line.set_data([{'name': '本周', 'values': [rng.randint(10, 36) for _ in range(7)]},
                           {'name': '上周', 'values': [8, 11, 15, 17, 19, 20, 24]}])
            bars.set_data([{'name': '流入', 'values': [rng.randint(10, 28) for _ in range(5)]},
                           {'name': '流出', 'values': [-rng.randint(4, 12) for _ in range(5)]}])
            self.status.set('图表数据已更新；仅使用 Python 列表与标准库。')
        self.button(controls, '更新演示数据', refresh, primary=True)
        self.button(controls, '切换饼图 / 环形', lambda: donut.set_hole(0 if donut.hole else .62))
        self.button(controls, '重置缩放', lambda: (line.reset_view(), scatter.reset_view()))
        ttk.Label(controls, text='纯 Tkinter Canvas · 无第三方运行依赖', style='Demo.Note.TLabel').pack(side='right')

    def forms_page(self, page):
        box = self.card(page, '日期输入与日历', 0)
        ttk.Label(box, text='计划日期').pack(anchor='w', pady=(0, 6))
        date_entry = ui.DateEntry(box, value=date(2026, 10, 12), command=lambda value: self.status.set(f'日期：{value}'))
        date_entry.pack(fill='x'); self.refs['date_entry'] = date_entry
        self.note(box, '可输入日期，或点击日历选择；支持今天、清空和日期范围。')
        optional = ui.DateEntry(box, minimum=date(2026, 1, 1), maximum=date(2026, 12, 31)); optional.pack(fill='x', pady=10)
        self.note(box, '下方日期限制为 2026 年，可留空。')
        box = self.card(page, '带数值输入的滑块', 0, 1)
        slider = ui.ValueSlider(box, variable=self.var(tk.DoubleVar, 35), from_=0, to=100, step=1, unit='%')
        slider.pack(fill='x', pady=12); self.refs['value_slider'] = slider
        fine = ui.ValueSlider(box, variable=self.var(tk.DoubleVar, 1.5), from_=0, to=5, step=.1, unit='秒'); fine.pack(fill='x', pady=12)
        self.note(box, '拖动滑块或直接输入数值；按 Enter 确认，步长与范围统一处理。')
        box = self.card(page, '表单校验', 1)
        fields = []
        for label, kind, initial, options in [('任务名称', 'text', '', {'required': True}),
                                              ('处理数量', 'integer', '10', {'minimum': 1, 'maximum': 100}),
                                              ('联系邮箱', 'email', 'demo@example.com', {})]:
            field = ui.ValidatedEntry(box, label=label, kind=kind, **options); field.set(initial); field.pack(fill='x', pady=8); fields.append(field)
        self.refs['validated_fields'] = fields
        def validate():
            results = [field.validate() for field in fields]
            ui.notify(self, '表单验证通过' if all(results) else '请检查标红的输入项', kind='success' if all(results) else 'warning')
        ttk.Button(box, text='校验表单', style='Primary.TButton', command=validate).pack(anchor='w', pady=8)
        box = self.card(page, '通用对话框与轻提示', 1, 1)
        Dialogs = ui.Dialogs
        for text, command in [('确认操作', lambda: self.status.set('确认结果：'+str(Dialogs.confirm(self, '确认执行这项演示操作吗？')))),
                              ('重命名', lambda: self.status.set('输入结果：'+str(Dialogs.ask_string(self, '请输入名称', initial='我的项目', title='重命名')))),
                              ('输入数量', lambda: self.status.set('数量：'+str(Dialogs.ask_integer(self, '输入 1–100 的整数', initial=10, minimum=1, maximum=100)))),
                              ('错误提示', lambda: Dialogs.error(self, '这是一个演示错误提示。'))]:
            ttk.Button(box, text=text, command=command).pack(fill='x', pady=5)
        row = ttk.Frame(box); row.pack(fill='x', pady=12)
        for kind, text in [('success', '成功'), ('warning', '警告'), ('danger', '失败')]:
            ttk.Button(row, text=text, style=kind.title()+'.Outline.TButton',
                       command=lambda k=kind, t=text: ui.notify(self, t+'：这是自动消失的通知。', kind=k)).pack(side='left', padx=(0, 6))
        self.note(box, '轻提示不阻塞操作，多条按角落排列；悬停可延缓消失。')

    def feedback_page(self, page):
        variable = self.var(tk.DoubleVar, 65)
        thresholds = [(60, 'success'), (85, 'warning'), (100, 'danger')]
        box = self.card(page, '圆环仪表 · 可拖动', 0)
        meter = ui.Meter(box, variable=variable, interactive=True, subtext='完成率', size=170, thresholds=thresholds)
        meter.pack(fill='both', expand=True); self.refs['meter'] = meter
        box = self.card(page, '半圆仪表 · 阈值颜色', 0, 1)
        semi = ui.Meter(box, variable=variable, meter_type='semi', subtext='资源使用', size=170, thresholds=thresholds)
        semi.pack(fill='both', expand=True)
        ui.ValueSlider(box, variable=variable, unit='%').pack(fill='x', pady=8)
        box = self.card(page, '带文字的进度条', 1, span=2)
        gauge = ui.TextProgress(box, variable=variable, mask='已完成 {value:.0f} / {maximum}', maximum=100)
        gauge.pack(fill='x', pady=8); self.refs['text_progress'] = gauge
        loading = ui.TextProgress(box, mode='indeterminate', text='正在处理…', kind='info'); loading.pack(fill='x', pady=8)
        self.refs['text_loading'] = loading
        row = ttk.Frame(box); row.pack(fill='x')
        self.button(row, '开始加载', loading.start); self.button(row, '停止', loading.stop)
        box = self.card(page, '状态标签与按钮变体', 2, span=2)
        for kind, text in [('success', '成功'), ('warning', '警告'), ('danger', '危险'), ('info', '信息'), ('neutral', '次要')]:
            row = ttk.Frame(box); row.pack(fill='x', pady=4)
            ui.Badge(row, text=text, kind=kind).pack(side='left', padx=(0, 12))
            for variant, label in [('', '实心'), ('Outline.', '描边'), ('Link.', '链接')]:
                ttk.Button(row, text=text+' · '+label, style=kind.title()+'.'+variant+'TButton',
                           command=lambda t=text: self.status.set(t+'按钮已点击')).pack(side='left', padx=(0, 10))

    def dataview_page(self, page):
        box = self.card(page, '多列列表 · 搜索 / 筛选 / 分页', 0, span=2)
        table = ui.DataTable(box, columns=[{'key': 'name', 'text': '文件名称', 'width': 260}, {'key': 'count', 'text': '数量', 'width': 90},
                                           {'key': 'state', 'text': '状态', 'width': 120}, {'key': 'group', 'text': '分组', 'width': 140}],
                             rows=[[f'资料_{i+1:03d}.csv', [2, 10, 30, 5][i%4], ['待处理', '已完成', '处理中'][i%3], ['工作', '个人'][i%2]] for i in range(53)],
                             page_size=10, height=9)
        table.pack(fill='both', expand=True); self.refs['data_table'] = table
        row = ttk.Frame(box); row.pack(fill='x', pady=10)
        self.button(row, '导出筛选结果', lambda: table.export_csv(scope='filtered'), primary=True)
        self.button(row, '导出当前页', lambda: table.export_csv(scope='page'))
        self.button(row, '恢复列布局', table.reset_layout)
        self.note(box, '排序作用于全部筛选结果，再分页显示。右键可排序、移动/隐藏列或导出；Ctrl / Shift 多选，翻页保留选择。')

    def media_page(self, page):
        box = self.card(page, '图片预览框', 0, span=2)
        viewer = ui.ImageViewer(box, height=175); viewer.pack(fill='both', expand=True); self.refs['image_viewer'] = viewer
        image = tk.PhotoImage(master=self, width=640, height=220)
        image.put('#EAF3FF', to=(0, 0, 640, 220)); image.put('#087DFF', to=(30, 35, 185, 185))
        image.put('#19A58B', to=(215, 70, 400, 185)); image.put('#E9A13B', to=(430, 105, 610, 185))
        viewer.set_image(image)
        self.note(box, '滚轮缩放，拖动平移，双击适应窗口。演示图片由 Tk 在内存中生成。')
        box = self.card(page, '颜色选择工具', 1)
        picker = ui.ColorPicker(box); picker.pack(fill='both', expand=True); self.refs['color_picker'] = picker
        def choose_color():
            value = ui.ColorDialog(self, color=picker.get_color()).show_result()
            if value:
                picker.set_color(value)
        ttk.Button(box, text='以弹窗选择颜色', command=choose_color).pack(anchor='w', pady=6)
        box = self.card(page, '字体选择与实时预览', 1, 1)
        font = ui.FontPicker(box); font.pack(fill='both', expand=True); self.refs['font_picker'] = font
        def choose_font():
            result = ui.FontDialog(self).show_result()
            if result:
                self._picked_font = result; self.status.set('已选择字体：'+str(result.actual()))
        ttk.Button(box, text='以弹窗选择字体', command=choose_font).pack(anchor='w', pady=6)

    def close(self):
        loading = self.refs.get('loading')
        if loading:
            loading.stop()
        if self.dialog is not None and self.dialog.winfo_exists():
            self.dialog.close()
        for child in self.winfo_children():
            if hasattr(child, '_chrome'):
                child._chrome.detach()
        self.destroy()


def main():
    parser = argparse.ArgumentParser(description='TkWebUI widget gallery')
    parser.add_argument('--page', type=int, choices=range(1, len(PAGES)+1), default=1, help='page to open, 1-12')
    args = parser.parse_args()
    ui.enable_dpi_awareness()
    Gallery(page=args.page-1).mainloop()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        (BASE/'startup_error.log').write_text(traceback.format_exc(), encoding='utf-8')
        raise
