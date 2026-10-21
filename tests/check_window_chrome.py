"""Windows GUI regression for issue #5. Run: python tests/check_window_chrome.py."""
import sys
import time
import traceback
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tkinter as tk
from tkinter import ttk
import tkwebui as ui

ui.enable_dpi_awareness()
def check(cls, mode):
    root = tk.Tk()
    errors = []
    root.report_callback_exception = lambda *args: errors.append(''.join(traceback.format_exception(*args)))
    root.title(f'{cls.__name__}: {mode}')
    root.geometry('640x420+100+100')
    ui.apply_theme(root)
    toolbar = ttk.Frame(root, height=48)
    toolbar.pack(fill='x')
    toolbar.pack_propagate(False)
    label = ttk.Label(toolbar, text='Window controls')
    label.pack(side='left', padx=20)
    entry = ttk.Entry(root)
    entry.insert(0, 'Custom title bar regression check')
    entry.pack(fill='x', padx=20, pady=20)
    chrome = cls(root, toolbar, drag_widgets=(toolbar, label))
    def pump():
        end=time.monotonic()+0.15
        while time.monotonic()<end:
            root.update()
            time.sleep(0.01)
    try:
        if mode=='before_attach':chrome.controls.destroy()
        pump()
        assert chrome.attached
        if mode=='destroy':chrome.controls.destroy()
        elif mode=='single':chrome.max_button.destroy()
        elif mode=='override':
            chrome.paint_control=lambda *a,**k:None
            chrome.controls.destroy()
        custom=ttk.Button(toolbar,text='Close',command=root.destroy)
        custom.pack(side='right')
        for axes in [(False,False),(True,False),(False,True),(True,True)]:
            root.resizable(*axes)
            pump()
            chrome.refresh_cache()
            assert chrome._resize_axes==axes
            assert bool(chrome.get_long(chrome.hwnd,-16)&0x00010000)==all(axes)
            if mode=='normal':assert chrome.max_button.instate(['disabled']) == (not all(axes))
        before=chrome._drag_rects[:]
        for x in (140,190,240):
            root.geometry(f'+{x}+120')
            pump()
        assert chrome._drag_rects != before
        assert chrome._excluded
        for key in chrome.buttons:chrome.paint_control(key,True)
        chrome.minimize()
        pump()
        root.deiconify()
        pump()
        assert not errors, '\n'.join(errors)
        print(f'PASS {cls.__name__} {mode}',flush=True)
    finally:
        root.destroy()

if __name__ == '__main__':
    if sys.platform != 'win32':
        print('SKIP: WindowChrome regression requires Windows')
    else:
        for mode in ('normal','destroy','single','override','before_attach'):
            check(ui.WindowChrome,mode)
