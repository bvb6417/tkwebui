"""Reusable standard-library widgets, layout helpers and input focus handling."""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from .core import Card, PALETTE, icon, _raster, _rgb
from .scrolling import _attach_scrollbars, _release_scrollbars

def focus_when_mapped(widget,*,when=None):
    """Hand off focus after a page is mapped; optional predicate cancels stale navigation."""
    root=widget._root()
    pending=getattr(root,'_switch_focus_job',None)
    if pending is not None:root.after_cancel(pending)
    def restore(attempt=0):
        root._switch_focus_job=None
        if not widget.winfo_exists() or (when is not None and not when()):return
        grab=widget.grab_current()
        if grab is not None and grab.winfo_toplevel() is not widget.winfo_toplevel():return
        if not widget.winfo_viewable():
            if attempt<5:root._switch_focus_job=root.after(20,lambda:restore(attempt+1))
            return
        if 'state' not in widget.keys() or str(widget.cget('state'))!='disabled':widget.focus_force()
    root._switch_focus_job=root.after(20,restore)

def install_input_focus(scope):
    """Fix input activation locally, including inputs added to modal windows later."""
    tag='TkWebUIInputFocus'
    def clicked(event):
        widget=event.widget
        if not widget.winfo_viewable() or str(widget.cget('state'))=='disabled':return
        grab=widget.grab_current()
        if grab is None or grab.winfo_toplevel() is widget.winfo_toplevel():widget.focus_force()
    def attach(widget):
        if isinstance(widget,(tk.Text,tk.Entry,ttk.Entry,ttk.Combobox,ttk.Spinbox)):
            tags=widget.bindtags()
            if tag not in tags:widget.bindtags((tags[0],tag,*tags[1:]))
        for child in widget.winfo_children():attach(child)
    if not getattr(scope,'_switch_focus_installed',False):
        scope.bind_class(tag,'<ButtonPress-1>',clicked)
        scope.bind('<Map>',lambda event:attach(event.widget),add='+')
        scope._switch_focus_installed=True
    attach(scope)

class _TextContainer(ttk.Frame):
    def destroy(self):
        if getattr(self,'_destroying',False):return
        self._destroying=True
        super().destroy()

class RoundedText(tk.Text):
    """A real tk.Text inside a small-radius field; pack/grid/place operate on its shell.

    Text methods, bindings, tags, undo, selection and scroll commands are native.
    `container` exposes the surrounding ttk.Frame when layout inspection is needed.
    """
    def __init__(self,master,*,padding=None,scrollbars=True,**kwargs):
        scale=master.winfo_fpixels('1i')/96
        self.container=_TextContainer(master,style='RoundedText.TFrame',
                                      padding=padding if padding is not None else (round(6*scale),round(4*scale)))
        self.container.columnconfigure(0,weight=1);self.container.rowconfigure(0,weight=1)
        kwargs.update(borderwidth=0,highlightthickness=0,relief='flat')
        kwargs.setdefault('padx',0);kwargs.setdefault('pady',0)
        kwargs.setdefault('background',PALETTE['bg']);kwargs.setdefault('foreground',PALETTE['fg'])
        kwargs.setdefault('insertbackground',PALETTE['fg'])
        kwargs.setdefault('selectbackground',PALETTE['selected']);kwargs.setdefault('selectforeground',PALETTE['fg'])
        super().__init__(self.container,**kwargs)
        tk.Text.grid(self,row=0,column=0,sticky='nsew')
        if scrollbars:_attach_scrollbars(self,self.container)
        self.bind('<FocusIn>',lambda _:self.container.state(['focus']),add='+')
        self.bind('<FocusOut>',lambda _:self.container.state(['!focus']),add='+')
        self._sync_shell()
        install_input_focus(self.winfo_toplevel())

    def _sync_shell(self):
        disabled=str(self.cget('state'))=='disabled'
        self.container.state(['disabled' if disabled else '!disabled'])
        # Read-only text remains a white reading surface, not a grey block.
        if disabled:self.container.state(['!disabled'])

    def configure(self,cnf=None,**kwargs):
        if isinstance(cnf,str):return super().configure(cnf,**kwargs)
        options=dict(cnf or {},**kwargs)
        if options:
            options.update(borderwidth=0,highlightthickness=0,relief='flat')
            result=super().configure(**options)
            _release_scrollbars(self,options)
            self._sync_shell();return result
        return super().configure()
    config=configure

    def destroy(self):
        if getattr(self.container,'_destroying',False):super().destroy()
        else:self.container.destroy()

    def pack(self,*args,**kw):return self.container.pack(*args,**kw)
    pack_configure=pack
    def grid(self,*args,**kw):return self.container.grid(*args,**kw)
    grid_configure=grid
    def place(self,*args,**kw):return self.container.place(*args,**kw)
    place_configure=place
    def pack_forget(self):return self.container.pack_forget()
    def grid_forget(self):return self.container.grid_forget()
    def grid_remove(self):return self.container.grid_remove()
    def place_forget(self):return self.container.place_forget()
    def pack_info(self):return self.container.pack_info()
    def grid_info(self):return self.container.grid_info()
    def place_info(self):return self.container.place_info()

def initial_window_bounds(root,width,height):
    """Center the larger default window, leaving room for taskbar and borders."""
    left,top,right,bottom=0,0,root.winfo_screenwidth(),root.winfo_screenheight()
    import sys
    if sys.platform=='win32':
        import ctypes
        from ctypes import wintypes as w
        user=ctypes.WinDLL('user32',use_last_error=True)
        class MonitorInfo(ctypes.Structure):
            _fields_=[('cbSize',w.DWORD),('rcMonitor',w.RECT),('rcWork',w.RECT),('dwFlags',w.DWORD)]
        user.MonitorFromWindow.argtypes=[w.HWND,w.DWORD];user.MonitorFromWindow.restype=w.HANDLE
        user.GetMonitorInfoW.argtypes=[w.HANDLE,ctypes.POINTER(MonitorInfo)]
        monitor=user.MonitorFromWindow(root.winfo_id(),2)
        info=MonitorInfo();info.cbSize=ctypes.sizeof(info)
        if user.GetMonitorInfoW(monitor,ctypes.byref(info)):
            left,top,right,bottom=info.rcWork.left,info.rcWork.top,info.rcWork.right,info.rcWork.bottom
    width=min(width,max(1,right-left-80));height=min(height,max(1,bottom-top-80))
    return width,height,left+(right-left-width)//2,top+(bottom-top-height)//2

def align_tree_scrollbar(tree):
    """Fit the final visible column and show only genuinely needed scrollbars."""
    if not hasattr(tree,'_responsive_table'):tree._responsive_table=ResponsiveTable(tree)
    return tree._responsive_table

def configure_table(tree, *, sortable=True):
    layout=align_tree_scrollbar(tree)
    if sortable:
        from .table import enable_sorting
        enable_sorting(tree)
    return layout

class ResponsiveTable:
    def __init__(self,tree):
        self.tree=tree;self.job=None;self.offset=None;self.visible=()
        self.preferred={column:tree.column(column,'width') for column in tree['columns']}
        self.bars={str(child.cget('orient')):child for child in tree.master.winfo_children()
                   if isinstance(child,ttk.Scrollbar)}
        for orientation,option in [('vertical','yscrollcommand'),('horizontal','xscrollcommand')]:
            if orientation in self.bars:
                bar=self.bars[orientation]
                def changed(first,last,bar=bar):
                    bar.set(first,last);self.schedule()
                tree.configure(**{option:changed})
                bar.grid_remove()
        tree.bind('<Map>',self.schedule,add='+')
        tree.bind('<Configure>',self.schedule,add='+')
        tree.bind('<<ThemeChanged>>',self.theme_changed,add='+')
        tree.bind('<Destroy>',self.cleanup,add='+')
        # Mark the stretching column now. Treeview columns stretch by default,
        # so a table laid out before it is shown (ScrollArea.prepare) would
        # otherwise spread its final width over every column for good.
        self.refresh()

    def schedule(self,event=None):
        if self.job is None:self.job=self.tree.after_idle(self.refresh)

    def theme_changed(self,event):
        self.offset=None;self.schedule()

    def remember_columns(self):
        # The stretched width is a layout result, not a new user preference.
        last=self.visible[-1] if self.visible else None
        for column in self.preferred:
            if column!=last:self.preferred[column]=self.tree.column(column,'width')
        return self.preferred.copy()

    def refresh(self):
        self.job=None
        tree=self.tree
        display=tree['displaycolumns']
        count=len(tree['columns']) if '#all' in display else len(display)
        visible=tuple(tree.column(f'#{i+1}','id') for i in range(count))
        if visible!=self.visible:
            for column in self.visible:
                if column!=self.visible[-1]:self.preferred[column]=tree.column(column,'width')
            if self.visible:
                old=self.visible[-1]
                tree.column(old,stretch=False,width=self.preferred[old])
            self.visible=visible
            for column in tree['columns']:tree.column(column,stretch=bool(visible and column==visible[-1]))
            # Let Tk finish allocating the newly stretchable column before
            # measuring overflow; no reset of the user's other column widths.
            self.schedule();return
        if not tree.winfo_ismapped():return
        for orientation,view in [('horizontal',tree.xview),('vertical',tree.yview)]:
            bar=self.bars.get(orientation)
            if bar is None:continue
            first,last=view()
            needed=float(first)>1e-7 or float(last)<1-1e-7
            showing=bar.winfo_manager()=='grid'
            if needed!=showing:
                if needed:bar.grid()
                else:bar.grid_remove()
            if orientation=='vertical' and needed:
                if self.offset is None:
                    limit=min(tree.winfo_height(),round(tree.winfo_fpixels('1i')/96*120))
                    header=[y for y in range(limit) if tree.identify_region(8,y) in ('heading','separator')]
                    if header:self.offset=max(header)+1
                if self.offset is not None and getattr(bar,'_header_offset',None)!=self.offset:
                    bar.grid_configure(pady=(self.offset,0));bar._header_offset=self.offset

    def cleanup(self,event):
        if event.widget is self.tree and self.job is not None:
            self.tree.after_cancel(self.job);self.job=None

def auto_hide_text_scrollbar(widget):
    """Use the actual Text viewport, including wrapping, to hide its scrollbar."""
    if getattr(widget,'_auto_bar_installed',False) or not widget.cget('yscrollcommand'):return
    outer=getattr(widget,'container',widget)
    bars=[child for child in outer.master.winfo_children()
          if isinstance(child,ttk.Scrollbar) and str(child.cget('orient'))=='vertical']
    if len(bars)!=1:return
    bar=bars[0];manager=bar.winfo_manager()
    if manager not in ('grid','pack'):return
    options=bar.pack_info() if manager=='pack' else None
    state={'job':None}
    def refresh():
        state['job']=None
        if not widget.winfo_ismapped():return
        first,last=widget.yview();needed=first>1e-7 or last<1-1e-7
        showing=bool(bar.winfo_manager())
        if needed==showing:return
        if manager=='grid':bar.grid() if needed else bar.grid_remove()
        elif needed:bar.pack(**options)
        else:bar.pack_forget()
    def changed(first,last):
        bar.set(first,last)
        if state['job'] is None:state['job']=widget.after_idle(refresh)
    def cleanup(event):
        if event.widget is widget and state['job'] is not None:widget.after_cancel(state['job'])
    widget.configure(yscrollcommand=changed)
    widget.bind('<Destroy>',cleanup,add='+')
    widget.bind('<Map>',lambda _:changed(*widget.yview()),add='+')
    widget._auto_bar_installed=True
    if manager=='grid':bar.grid_remove()
    else:bar.pack_forget()

class SectionCard(Card):
    """LabelFrame-compatible container with the reusable rounded card surface."""
    def __init__(self, master, *, text='', padding=14, **kwargs):
        super().__init__(master, padding=padding, **kwargs)
        scale=self.winfo_fpixels('1i')/96
        gap=round(14*scale)
        self.configure(padding=(gap,round(38*scale),gap,gap))
        self.caption=ttk.Label(self,text=text,style='Strong.TLabel')
        # ttk.Frame's place cavity begins after its padding, unlike Canvas.
        self.caption.place(x=0,y=-round(28*scale))

def configure_widget_styles(root,style):
    style.layout('RoundedText.TFrame',[('Switch.Entry.field',{'sticky':'nsew'})])
    style.configure('RoundedText.TFrame',background=PALETTE['bg'])
    scale=root.winfo_fpixels('1i')/96
    # Keep a generous invisible drag target with one short centered grip.
    style.configure('TPanedwindow',background=PALETTE['bg'])
    style.configure('Sash',sashthickness=round(12*scale),gripcount=0)
    width,height=round(12*scale),round(36*scale)
    def grip_sample(x,y):
        import math
        cx=width/2;cy=min(max(y,6*scale),height-6*scale)
        return _rgb('#BFC4CD') if math.hypot(x-cx,y-cy)<=1.5*scale else _rgb(PALETTE['bg'])
    grip=_raster(root,width,height,grip_sample)
    root._tkwebui_images.append(grip)
    style.element_create('TkWebUI.Sash.grip','image',grip,width=width,height=height,sticky='')
    style.layout('Vertical.Sash',[('TkWebUI.Sash.grip',{'sticky':'ns'})])
    style.configure('Popup.Quiet.TButton',foreground=PALETTE['fg'])
    style.configure('Checked.Popup.Quiet.TButton',foreground=PALETTE['blue'])
    # The containing Card owns the outer border, including both scrollbars.
    style.layout('Treeview',[('Treeview.padding',{'sticky':'nsew','children':[
        ('Treeview.treearea',{'sticky':'nsew'})]})])
    # Keep the real editable Combobox API, native popup and selection events.
    style.element_create('TkWebUI.Combobox.downarrow','image',icon(root,'chevrondown',round(12*scale)),
                         width=round(30*scale),sticky='')
    style.layout('TCombobox',[('Switch.Entry.field',{'sticky':'nsew','children':[
        ('TkWebUI.Combobox.downarrow',{'side':'right','sticky':'ns'}),
        ('Combobox.padding',{'sticky':'nsew','children':[('Combobox.textarea',{'sticky':'nsew'})]})]})])
    style.configure('TCombobox',padding=(round(9*scale),round(6*scale)))
    root.option_add('*TCombobox*Listbox.background',PALETTE['bg'])
    root.option_add('*TCombobox*Listbox.selectBackground',PALETTE['selected'])
    root.option_add('*TCombobox*Listbox.selectForeground',PALETTE['fg'])
    # Small cached pill images for progress, preserving ttk .start/.stop semantics.
    h=max(6,round(6*scale))
    for part,color in [('trough',PALETTE['hover']),('pbar',PALETTE['accent'])]:
        rgb=_rgb(color);bg=_rgb(PALETTE['bg'])
        def sample(x,y,fg=rgb,h=h,bg=bg):
            import math
            cx=min(max(x,h/2),128-h/2)
            return fg if math.hypot(x-cx,y-h/2)<=h/2 else bg
        img=_raster(root,128,h,sample)
        root._tkwebui_images.append(img)
        style.element_create('TkWebUI.Progress.'+part,'image',img,border=h//2,width=h,height=h,sticky='nsew')
    style.layout('Horizontal.TProgressbar',[('TkWebUI.Progress.trough',{'sticky':'ew','children':[
        ('TkWebUI.Progress.pbar',{'side':'left','sticky':'ns'})]})])
    style.configure('Horizontal.TProgressbar',thickness=h,borderwidth=0)

