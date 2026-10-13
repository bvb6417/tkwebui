"""Scrollbars that occupy layout space only while their viewport overflows."""
import tkinter as tk
from tkinter import ttk


class AutoScrollbar(ttk.Scrollbar):
    """Use with grid() and a widget's x/yscrollcommand, just like ttk.Scrollbar.

    Starts hidden. Tk's viewport fractions determine visibility after content
    changes, scrolling and resizing. grid_remove preserves the layout options.
    """
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self._needed = False
        self._laid_out = False
        self._visibility_job = None
        self.bind('<Destroy>', self._cleanup, add='+')

    def grid(self, *args, **kwargs):
        super().grid(*args, **kwargs)
        self._laid_out = True
        if not self._needed:
            super().grid_remove()
    grid_configure = grid

    def set(self, first, last):
        super().set(first, last)
        self._needed = float(first) > 1e-7 or float(last) < 1-1e-7
        if self._visibility_job is None:
            self._visibility_job = self.after_idle(self._sync)

    def _sync(self):
        self._visibility_job = None
        if self._laid_out:
            if self._needed and not self.winfo_manager():
                super().grid()
            elif not self._needed and self.winfo_manager():
                super().grid_remove()

    def pack(self, *args, **kwargs):
        raise tk.TclError('AutoScrollbar uses grid(); place it in a Frame if the outer layout uses pack().')
    pack_configure = pack
    place = pack
    place_configure = pack

    def _cleanup(self, event):
        if event.widget is self and self._visibility_job is not None:
            self.after_cancel(self._visibility_job)
            self._visibility_job = None


def _attach_scrollbars(widget, container):
    """Add internal bars without taking over caller-supplied scroll commands."""
    widget._auto_scrollbars = {}
    for axis, options in [('y', dict(row=0, column=1, sticky='ns')),
                          ('x', dict(row=1, column=0, sticky='ew'))]:
        option = axis+'scrollcommand'
        if widget.cget(option):
            continue
        bar = AutoScrollbar(container, orient='vertical' if axis=='y' else 'horizontal',
                            command=getattr(widget, axis+'view'))
        bar.grid(**options)
        # Bypass subclass configure: this installs, rather than replaces, bars.
        tk.Widget.configure(widget, **{option: bar.set})
        widget._auto_scrollbars[option] = bar


def _release_scrollbars(widget, options):
    # Existing applications can still connect their own external scrollbar.
    for option in options:
        bar = getattr(widget, '_auto_scrollbars', {}).pop(option, None)
        if bar is not None:
            bar.destroy()
