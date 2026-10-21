"""Tcl binding helpers shared by popups, menus and notifications."""
import tkinter as tk


def unbind(widget, sequence, funcid):
    """Remove one ``bind(..., add='+')`` handler and keep the others.

    Before Python 3.13, ``Misc.unbind(sequence, funcid)`` clears every script
    bound to ``sequence`` on that widget, silently breaking other components.
    """
    if not funcid:
        return
    try:
        script = str(widget.tk.call('bind', widget._w, sequence))
        prefix = 'if {"[' + funcid + ' '
        kept = [line for line in script.split('\n') if line.strip() and not line.startswith(prefix)]
        widget.tk.call('bind', widget._w, sequence, '\n'.join(kept))
    except tk.TclError:
        pass
    try:
        widget.deletecommand(funcid)
    except (tk.TclError, ValueError):
        pass
