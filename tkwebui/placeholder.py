"""Grey hint text for empty inputs (PlaceholderText), GitHub issue #3.

The hint is a separate label laid over the field, never text inside it, so
get(), textvariable, show='●', validation and readonly behave exactly as
without a hint. Like Windows 11 it stays visible while the field has focus and
disappears as soon as there is content.

    set_placeholder(existing_entry, '请输入用户名')      # any entry-like widget
    PlaceholderEntry(parent, placeholder='搜索')          # convenience class
"""
import tkinter as tk
from tkinter import ttk
from .core import PALETTE

_ENTRIES=(ttk.Entry,tk.Entry,tk.Spinbox)          # ttk.Combobox/Spinbox derive from ttk.Entry
_ARROWS=(ttk.Combobox,ttk.Spinbox,tk.Spinbox)


def _field_color(widget):
    """Colour of the field face behind the hint (grey only when disabled)."""
    if not isinstance(widget,ttk.Widget):
        state=str(widget.cget('state'))
        key='disabledbackground' if state=='disabled' else 'readonlybackground' if state=='readonly' else 'background'
        try:return str(widget.cget(key))
        except tk.TclError:return str(widget.cget('background'))
    return PALETTE['sidebar'] if widget.instate(['disabled']) else PALETTE['bg']


def _disabled(widget):
    if isinstance(widget,ttk.Widget):return widget.instate(['disabled'])
    return str(widget.cget('state'))=='disabled'


class Placeholder:
    """Controller behind set_placeholder(); one per widget."""
    def __init__(self,widget,text=''):
        self.widget=widget;self.text=str(text or '')
        self.job=None;self.closed=False;self.variable=None;self._own=None;self._drawn=None;self._retries=0
        self.label=tk.Label(widget.master,anchor='w',borderwidth=0,highlightthickness=0,padx=0,pady=0,
                            cursor='xterm',takefocus=0)
        self.trace_command=widget.register(lambda *args:self.schedule())
        # Our own bindtag: user bindings stay untouched and nothing to unbind.
        self.tag=f'TkWebUIPlaceholder{id(self)}'
        tags=widget.bindtags();widget.bindtags((tags[0],self.tag,*tags[1:]))
        self.sequences=('<Map>','<Configure>','<FocusIn>','<FocusOut>','<KeyRelease>','<Enter>','<Leave>',
                        '<<Paste>>','<<Cut>>','<<Clear>>','<<ComboboxSelected>>')
        for sequence in self.sequences:widget.bind_class(self.tag,sequence,self.schedule)
        widget.bind_class(self.tag,'<Destroy>',self.destroyed)
        # Clicks and hover belong to the field underneath.
        self.label.bind('<ButtonPress-1>',lambda e:self.forward(e,'<ButtonPress-1>'))
        self.label.bind('<ButtonRelease-1>',lambda e:self.forward(e,'<ButtonRelease-1>'))
        self.label.bind('<Enter>',lambda e:widget.event_generate('<Enter>'))
        self.label.bind('<Leave>',self.label_left)
        # state()/configure() emit no event; follow them for the disabled look.
        for name in ('state','configure','config'):
            original=getattr(widget,name,None)
            if original is None:continue       # classic tk.Entry has no state()
            def follow(*args,_original=original,**kwargs):
                result=_original(*args,**kwargs)
                if args or kwargs:self.schedule()
                return result
            setattr(widget,name,follow)
        widget._tkwebui_placeholder=self
        self.schedule()

    def set_text(self,text):
        self.text=str(text or '');self.schedule()

    def forward(self,event,sequence):
        w=self.widget
        if not w.winfo_exists():return 'break'
        w.event_generate(sequence,x=event.x_root-w.winfo_rootx(),y=event.y_root-w.winfo_rooty())
        return 'break'

    def label_left(self,event):
        w=self.widget
        if not w.winfo_exists():return
        x,y=w.winfo_pointerxy()
        if not (w.winfo_rootx()<=x<w.winfo_rootx()+w.winfo_width() and w.winfo_rooty()<=y<w.winfo_rooty()+w.winfo_height()):
            w.event_generate('<Leave>')

    def schedule(self,event=None):
        # A frame later: after the widget's own handlers (hover/focus states are
        # current) and after Tk's idle redraw, which is when ttk lays out the
        # text area that bbox() reports.
        if not self.closed and self.job is None:self.job=self.widget.after(16,self.refresh)

    def hook_variable(self):
        """Content changes arrive through the textvariable (typing, insert,
        delete, set, current). Widgets without one get a private variable."""
        w=self.widget
        name=str(w.cget('textvariable'))
        if not name:
            self._own=tk.StringVar(w,value=w.get())
            w.configure(textvariable=self._own);name=str(self._own)
        if name==self.variable:return
        self.untrace()
        self.variable=name
        w.tk.call('trace','add','variable',name,('write','unset'),self.trace_command)

    def untrace(self):
        if self.variable:
            try:self.widget.tk.call('trace','remove','variable',self.variable,('write','unset'),self.trace_command)
            except tk.TclError:pass
        self.variable=None

    def refresh(self):
        self.job=None
        w=self.widget
        if self.closed or not w.winfo_exists():return
        self.hook_variable()
        if not self.text or w.get() or not w.winfo_ismapped():
            if self._drawn is not None:self.label.place_forget();self._drawn=None
            return
        box=w.bbox(0) if isinstance(w,ttk.Widget) else None
        if box and box[0]==0 and box[1]==0 and self._retries<10:
            # Not laid out yet (first map): bbox is still all zeros.
            self._retries+=1;self.job=w.after(30,self.refresh);return
        self._retries=0
        if box and box[3]>0:x,y,height=box[0],box[1],box[3]
        else:
            x=int(w.winfo_pixels(w.cget('borderwidth')))+int(w.winfo_pixels(w.cget('highlightthickness')))+1
            y=height=None
        right=x+(w.winfo_height() if isinstance(w,_ARROWS) else 0)
        font=str(w.cget('font')) or 'TkTextFont'
        options=dict(text=self.text,font=font,background=_field_color(w),
                     foreground=PALETTE['disabled'] if _disabled(w) else PALETTE['muted'])
        place=dict(in_=w,x=x,relwidth=1,width=-(x+right))
        place.update(dict(y=y,height=height) if y is not None else dict(rely=.5,anchor='w'))
        signature=(tuple(sorted(options.items())),tuple(sorted((k,str(v)) for k,v in place.items())))
        if signature!=self._drawn:
            self._drawn=signature
            self.label.configure(**options)
            self.label.place(**place)
        self.label.tk.call('raise',self.label._w,w._w)

    def destroyed(self,event):
        if event.widget is not self.widget or self.closed:return
        self.closed=True
        if self.job is not None:
            try:self.widget.after_cancel(self.job)
            except tk.TclError:pass
        self.untrace()
        try:self.widget.deletecommand(self.trace_command)
        except tk.TclError:pass
        for sequence in (*self.sequences,'<Destroy>'):self.widget.unbind_class(self.tag,sequence)
        if self.label.winfo_exists():self.label.destroy()


def set_placeholder(widget,text):
    """Show grey hint ``text`` while ``widget`` is empty; '' hides it.

    Works on ttk.Entry, ttk.Combobox (editable or readonly, e.g. '请选择…'),
    ttk.Spinbox, tk.Entry and tk.Spinbox. get() always returns the real
    content. Calling it again changes the text. Returns the controller.
    """
    if not isinstance(widget,_ENTRIES):raise TypeError('set_placeholder 只支持 Entry / Combobox / Spinbox')
    controller=getattr(widget,'_tkwebui_placeholder',None)
    if controller is not None and not controller.closed:
        controller.set_text(text);return controller
    return Placeholder(widget,text)


class PlaceholderEntry(ttk.Entry):
    """ttk.Entry with a grey hint; ``get()`` returns '' while it is empty."""
    def __init__(self,master=None,placeholder='',**kwargs):
        super().__init__(master,**kwargs)
        self._placeholder=set_placeholder(self,placeholder)

    @property
    def placeholder(self):return self._placeholder.text

    @placeholder.setter
    def placeholder(self,text):self._placeholder.set_text(text)
