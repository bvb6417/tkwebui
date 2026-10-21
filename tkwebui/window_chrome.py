"""Windows client-side title region, using ctypes only.

Keeps a real taskbar window, system menu, resize borders and Windows maximize.
No overrideredirect(), fake minimize window, WebView, or third-party package.
On non-Windows systems the ordinary OS title bar is retained.
"""
from __future__ import annotations
import re
import sys
import tkinter as tk
from tkinter import ttk
from .core import icon, Tooltip, PALETTE


class WindowChrome:
    def __init__(self,root,toolbar,drag_widgets=(),on_close=None,sidebar=None):
        self.root=root
        root._window_chrome=self
        self.close_action=on_close or getattr(root,'close',root.destroy)
        self.attached=False
        self._old_proc=None
        self._cache_job=None
        self._drag_rects=[]
        self._excluded=[]
        self.extra_exclusions=[]
        self._drag_anchor=None
        self._drag_job=None
        self._drag_target=None
        self._drag_widget=None
        self._batch_depth=0
        self._native_moving=False
        self._system_move_pending=False
        self.system_move_count=0
        self.resize_handles={}
        self.toolbar=toolbar
        self.sidebar=sidebar
        self.drag_widgets=list(drag_widgets)
        # resizable() per axis, and the client size a fixed axis must keep.
        self._resize_axes=(True,True)
        self._fixed_size=None
        self._size_job=None
        self._geometry_originals={}
        if sys.platform!='win32':return
        import ctypes
        from ctypes import wintypes as w
        self.c,self.w=ctypes,w
        self.u=ctypes.WinDLL('user32',use_last_error=True)
        self.dwm=ctypes.WinDLL('dwmapi',use_last_error=True)
        self.PROC=ctypes.WINFUNCTYPE(ctypes.c_ssize_t,w.HWND,w.UINT,w.WPARAM,w.LPARAM)
        self.get_long=self.u.GetWindowLongPtrW
        self.get_long.argtypes=[w.HWND,ctypes.c_int];self.get_long.restype=ctypes.c_ssize_t
        self.set_long=self.u.SetWindowLongPtrW
        self.set_long.argtypes=[w.HWND,ctypes.c_int,ctypes.c_void_p];self.set_long.restype=ctypes.c_void_p
        self.u.CallWindowProcW.argtypes=[ctypes.c_void_p,w.HWND,w.UINT,w.WPARAM,w.LPARAM]
        self.u.CallWindowProcW.restype=ctypes.c_ssize_t
        self.u.GetParent.argtypes=[w.HWND];self.u.GetParent.restype=w.HWND
        self.u.SetWindowPos.argtypes=[w.HWND,w.HWND,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,w.UINT]
        self.u.RedrawWindow.argtypes=[w.HWND,ctypes.c_void_p,w.HANDLE,w.UINT]
        self.u.GetWindowRect.argtypes=[w.HWND,ctypes.POINTER(w.RECT)]
        self.u.IsZoomed.argtypes=[w.HWND]
        self.u.IsIconic.argtypes=[w.HWND];self.u.IsIconic.restype=w.BOOL
        self.u.IsWindow.argtypes=[w.HWND];self.u.IsWindow.restype=w.BOOL
        self.u.GetMenu.argtypes=[w.HWND];self.u.GetMenu.restype=w.HMENU
        self.u.AdjustWindowRectEx.argtypes=[ctypes.POINTER(w.RECT),w.DWORD,w.BOOL,w.DWORD]
        try:self.u.AdjustWindowRectExForDpi.argtypes=[ctypes.POINTER(w.RECT),w.DWORD,w.BOOL,w.DWORD,w.UINT]
        except AttributeError:pass  # Windows before 10 1607
        self.u.SendMessageW.argtypes=[w.HWND,w.UINT,w.WPARAM,w.LPARAM];self.u.SendMessageW.restype=ctypes.c_ssize_t
        self.u.PostMessageW.argtypes=[w.HWND,w.UINT,w.WPARAM,w.LPARAM];self.u.PostMessageW.restype=w.BOOL
        self.u.DefWindowProcW.argtypes=[w.HWND,w.UINT,w.WPARAM,w.LPARAM];self.u.DefWindowProcW.restype=ctypes.c_ssize_t
        self.u.MonitorFromWindow.argtypes=[w.HWND,w.DWORD];self.u.MonitorFromWindow.restype=w.HANDLE
        self.u.GetMonitorInfoW.argtypes=[w.HANDLE,ctypes.c_void_p]
        self.dwm.DwmSetWindowAttribute.argtypes=[w.HWND,w.DWORD,ctypes.c_void_p,w.DWORD]
        self.dwm.DwmExtendFrameIntoClientArea.argtypes=[w.HWND,ctypes.c_void_p]
        class MonitorInfo(ctypes.Structure):
            _fields_=[('cbSize',w.DWORD),('rcMonitor',w.RECT),('rcWork',w.RECT),('dwFlags',w.DWORD)]
        class MinMaxInfo(ctypes.Structure):
            _fields_=[('ptReserved',w.POINT),('ptMaxSize',w.POINT),('ptMaxPosition',w.POINT),('ptMinTrackSize',w.POINT),('ptMaxTrackSize',w.POINT)]
        self.MonitorInfo,self.MinMaxInfo=MonitorInfo,MinMaxInfo
        self.controls=ttk.Frame(toolbar)
        self.controls.pack(side='right',padx=(18,0))
        self.pinned=False
        self.buttons={}
        self._drawn_controls={}
        self.icon_size=round(root.winfo_fpixels('1i')/96*14)
        for key,command,label in [('pin',self.toggle_pin,'窗口置顶'),('minimize',self.minimize,'最小化'),
                                  ('maximize',self.toggle_maximize,'最大化 / 还原'),('close',self.close,'关闭')]:
            button=ttk.Button(self.controls,image=icon(root,key,self.icon_size),
                              style='Close.TButton' if key=='close' else 'Quiet.TButton',
                              command=command,takefocus=False,padding=(12,9))
            button.pack(side='left',padx=1)
            self.buttons[key]=button
            button.bind('<Enter>',lambda event,k=key:self.paint_control(k,True),add='+')
            button.bind('<Leave>',lambda event,k=key:self.paint_control(k,False),add='+')
            Tooltip(button,(lambda:'取消置顶' if self.pinned else '窗口置顶') if key=='pin' else label)
        self.max_button=self.buttons['maximize']
        for widget in self.drag_widgets:
            widget.bind('<ButtonPress-1>',self.drag,add='+')
            widget.bind('<B1-Motion>',self.drag_motion,add='+')
            widget.bind('<ButtonRelease-1>',self.end_drag,add='+')
            widget.bind('<Double-Button-1>',self.double_click,add='+')
        root.bind('<Escape>',self.cancel_drag,add='+')
        root.bind('<Configure>',self.schedule_cache,add='+')
        root.bind('<Map>',self.schedule_cache,add='+')
        self._attach_job=root.after_idle(self.attach)

    def attach(self):
        if self.attached:return
        self._attach_job=None
        self.root.update_idletasks()
        # Tk creates its native wrapper after the first map. Subclassing the
        # client HWND before then would leave the real OS caption untouched.
        wrapper=self.u.GetParent(self.root.winfo_id())
        if not wrapper:
            self._attach_job=self.root.after(20,self.attach)
            return
        self.hwnd=wrapper
        self.original_style=self.get_long(self.hwnd,-16)
        self.original_exstyle=self.get_long(self.hwnd,-20)
        self._resize_axes=tuple(bool(value) for value in self.root.resizable())
        # Tk sized the wrapper as client + OS frame. Once WM_NCCALCSIZE hands
        # the whole wrapper to the client, that frame becomes extra content
        # (640x420 opened as 662x476). Remember what the program asked for.
        # Also runs when Tk replaced its wrapper; that one is client + frame again.
        self._fixed_size=self._requested_size()
        self._install_geometry_bridge()
        self._callback=self.PROC(self.window_proc)  # Must stay alive for the window lifetime.
        self._old_proc=self.set_long(self.hwnd,-4,self.c.cast(self._callback,self.c.c_void_p))
        if not self._old_proc:return
        self.attached=True
        # Keep standard window capabilities for native Snap/animations. The
        # caption is hidden by WM_NCCALCSIZE, not by stripping capability flags.
        # Resize border / maximize box only where Tk's resizable() allows it.
        style=self._capability_style(self.original_style|0x00C00000|0x00080000|0x00020000)
        self.set_long(self.hwnd,-16,self.c.c_void_p(style))
        self.set_long(self.hwnd,-20,self.c.c_void_p((self.original_exstyle|0x00040000)&~0x00000080))
        margins=(self.c.c_int*4)(1,1,1,1)
        self.dwm.DwmExtendFrameIntoClientArea(self.hwnd,self.c.byref(margins))
        corner=self.c.c_int(2)
        self.dwm.DwmSetWindowAttribute(self.hwnd,33,self.c.byref(corner),self.c.sizeof(corner))
        self.u.SetWindowPos(self.hwnd,None,0,0,0,0,0x0001|0x0002|0x0004|0x0010|0x0020)
        if not self.u.IsZoomed(self.hwnd) and not self.u.IsIconic(self.hwnd):
            width,height=self._fixed_size
            self.u.SetWindowPos(self.hwnd,None,0,0,width,height,0x0002|0x0004|0x0010)
        if not self.resize_handles:self.install_resize_handles()
        self.sync_capabilities()
        self.schedule_cache()

    def _requested_size(self):
        """Client size the program requested, read before the frame is removed.

        Derived from the native outer rectangle minus the frame Tk added. On a
        monitor whose DPI differs from Tk's startup DPI, winfo_width() already
        contains the frame-size mismatch, so it is only a fallback.
        """
        outer=self.w.RECT()
        self.u.GetWindowRect(self.hwnd,self.c.byref(outer))
        frame=self.w.RECT(0,0,0,0)
        menu=bool(self.u.GetMenu(self.hwnd))
        dpi=round(self.root.winfo_fpixels('1i'))
        try:ok=self.u.AdjustWindowRectExForDpi(self.c.byref(frame),self.original_style,menu,self.original_exstyle,dpi)
        except AttributeError:ok=self.u.AdjustWindowRectEx(self.c.byref(frame),self.original_style,menu,self.original_exstyle)
        if ok and outer.right>outer.left:
            return (max(1,outer.right-outer.left-(frame.right-frame.left)),max(1,outer.bottom-outer.top-(frame.bottom-frame.top)))
        return (max(1,self.root.winfo_width()),max(1,self.root.winfo_height()))

    def _capability_style(self,style):
        style=style|0x00040000 if any(self._resize_axes) else style&~0x00040000     # WS_THICKFRAME
        return style|0x00010000 if all(self._resize_axes) else style&~0x00010000    # WS_MAXIMIZEBOX

    def sync_capabilities(self):
        """Follow root.resizable(), including changes made after attach()."""
        if not self.attached:return
        previous=self._resize_axes
        self._resize_axes=tuple(bool(value) for value in self.root.resizable())
        if previous!=self._resize_axes and not self.u.IsIconic(self.hwnd):
            # An axis that just became fixed keeps its current size.
            size=list(self._fixed_size or (self.root.winfo_width(),self.root.winfo_height()))
            for axis in (0,1):
                if previous[axis] and not self._resize_axes[axis]:
                    size[axis]=self.root.winfo_width() if axis==0 else self.root.winfo_height()
            self._fixed_size=tuple(size)
        style=self.get_long(self.hwnd,-16);updated=self._capability_style(style)
        if updated!=style:
            self.set_long(self.hwnd,-16,self.c.c_void_p(updated))
            self.u.SetWindowPos(self.hwnd,None,0,0,0,0,0x0001|0x0002|0x0004|0x0010|0x0020)
        allowed=all(self._resize_axes) or bool(self.u.IsZoomed(self.hwnd))
        # Custom title bars may destroy the built-in controls. Keep syncing
        # native capabilities and resize handles even when no button remains.
        if self.max_button.winfo_exists():
            self.max_button.state(['!disabled'] if allowed else ['disabled'])
            self.paint_control('maximize')
        if previous!=self._resize_axes:self.layout_resize_handles()

    def _install_geometry_bridge(self):
        """Keep the stable size in step with root.geometry('WxH') at runtime."""
        if self._geometry_originals:return
        original=self.root.wm_geometry
        for name in ('geometry','wm_geometry'):
            self._geometry_originals[name]=(name in self.root.__dict__,getattr(self.root,name))
        def geometry(value=None):
            match=re.match(r'^\s*(\d+)x(\d+)',str(value)) if value is not None else None
            if match and self.attached:
                lower=self.root.minsize();upper=self.root.maxsize()
                self._fixed_size=tuple(max(lower[i],min(upper[i],int(match.group(i+1)))) for i in (0,1))
            result=original(value)
            if match and self.attached:
                # Tk re-adds its frame size; restore the exact requested size.
                if self._size_job is not None:self.root.after_cancel(self._size_job)
                self._size_job=self.root.after_idle(lambda:self._apply_fixed_size(all_axes=True))
            return result
        self._geometry_bridge=geometry
        self.root.geometry=self.root.wm_geometry=geometry

    def _apply_fixed_size(self,all_axes=False):
        self._size_job=None
        if not self.attached or self._fixed_size is None or self.u.IsIconic(self.hwnd) or self.u.IsZoomed(self.hwnd):return
        rect=self.w.RECT();self.u.GetWindowRect(self.hwnd,self.c.byref(rect))
        width=rect.right-rect.left if self._resize_axes[0] and not all_axes else self._fixed_size[0]
        height=rect.bottom-rect.top if self._resize_axes[1] and not all_axes else self._fixed_size[1]
        self.u.SetWindowPos(self.hwnd,None,0,0,width,height,0x0002|0x0004|0x0010)

    def install_resize_handles(self):
        # Tk child HWNDs cover the client edges after WM_NCCALCSIZE removes
        # the frame. Wrapper-only WM_NCHITTEST therefore misses real mouse
        # input there. Narrow client hit targets forward to Windows SC_SIZE.
        for name,direction,cursor in [('left',1,'size_we'),('right',2,'size_we'),
                ('top',3,'size_ns'),('topleft',4,'size_nw_se'),('topright',5,'size_ne_sw'),
                ('bottom',6,'size_ns'),('bottomleft',7,'size_ne_sw'),('bottomright',8,'size_nw_se')]:
            # Only sidebar layouts have a grey left edge. Plain windows must
            # blend all resize targets, including both left corners, into bg.
            color=PALETTE['sidebar'] if self.sidebar is not None and 'left' in name else PALETTE['bg']
            handle=tk.Frame(self.root,bg=color,borderwidth=0,highlightthickness=0,cursor=cursor,takefocus=False)
            handle.bind('<ButtonPress-1>',lambda event,d=direction:self.start_resize(d,event))
            if name in ('top','bottom'):
                handle.sidebar_fill=tk.Frame(handle,bg=PALETTE['sidebar'],borderwidth=0,highlightthickness=0,cursor=cursor)
                handle.sidebar_fill.bind('<ButtonPress-1>',lambda event,d=direction:self.start_resize(d,event))
            self.resize_handles[name]=handle
        self.layout_resize_handles()

    def layout_resize_handles(self):
        if not self.resize_handles:return
        if self.u.IsZoomed(self.hwnd):
            for handle in self.resize_handles.values():handle.place_forget()
            return
        edge=getattr(self,'resize_margin',7);corner=edge*2
        horizontal_ok,vertical_ok=self._resize_axes
        positions={
            'left':dict(x=0,y=corner,width=edge,relheight=1,height=-2*corner),
            'right':dict(relx=1,x=-edge,y=corner,width=edge,relheight=1,height=-2*corner),
            'top':dict(x=corner,y=0,relwidth=1,width=-2*corner,height=edge),
            'bottom':dict(x=corner,rely=1,y=-edge,relwidth=1,width=-2*corner,height=edge),
            'topleft':dict(x=0,y=0,width=corner,height=corner),
            'topright':dict(relx=1,x=-corner,y=0,width=corner,height=corner),
            'bottomleft':dict(x=0,rely=1,y=-corner,width=corner,height=corner),
            'bottomright':dict(relx=1,x=-corner,rely=1,y=-corner,width=corner,height=corner)}
        for name,handle in self.resize_handles.items():
            # No resize targets on an axis the program fixed with resizable().
            if ('left' in name or 'right' in name) and not horizontal_ok or ('top' in name or 'bottom' in name) and not vertical_ok:
                handle.place_forget();continue
            handle.place(**positions[name]);handle.lift()
            if hasattr(handle,'sidebar_fill'):
                sidebar=self.sidebar
                width=max(0,sidebar.winfo_width()-corner) if sidebar is not None else 0
                if width:handle.sidebar_fill.place(x=0,y=0,width=width,relheight=1)
                else:handle.sidebar_fill.place_forget()

    def start_resize(self,direction,event=None):
        if not self.attached or self.u.IsZoomed(self.hwnd):return 'break'
        if direction in (1,2,4,5,7,8) and not self._resize_axes[0]:return 'break'
        if direction in (3,4,5,6,7,8) and not self._resize_axes[1]:return 'break'
        if self.root.grab_current() is not None:return 'break'
        self.u.ReleaseCapture()
        self._system_move_pending=True
        packed=0 if event is None else (event.x_root&0xffff)|((event.y_root&0xffff)<<16)
        self.u.PostMessageW(self.hwnd,0x0112,0xf000|direction,packed)
        return 'break'

    def work_area(self):
        info=self.MonitorInfo();info.cbSize=self.c.sizeof(info)
        monitor=self.u.MonitorFromWindow(self.hwnd,2)
        return info if self.u.GetMonitorInfoW(monitor,self.c.byref(info)) else None

    def window_proc(self,hwnd,message,wparam,lparam):
        try:
            if message==0x0231:  # WM_ENTERSIZEMOVE
                self._native_moving=True;self._system_move_pending=False
                self.system_move_count+=1
            elif message==0x0232:  # WM_EXITSIZEMOVE
                self._native_moving=False;self._system_move_pending=False
            if (message in (0x00A1,0x00A3) and (wparam==2 or 10<=wparam<=17)) or (message==0x0112 and wparam&0xfff0 in (0xf000,0xf010)):
                # Use Windows' caption/move handler, not Tk's translated mouse
                # bindings. This enables native Snap without synchronous Tcl
                # callback -> SendMessage -> Tcl callback recursion.
                result=self.u.DefWindowProcW(hwnd,message,wparam,lparam)
                self._system_move_pending=False
                return result
            if message==0x0085:  # WM_NCPAINT: no OS caption to paint, including inactive popups.
                return 0
            if message==0x0086:  # WM_NCACTIVATE: retain client chrome when focus leaves the window.
                return 1
            if message==0x0083 and wparam:  # WM_NCCALCSIZE: the toolbar owns the top client area.
                if self.u.IsZoomed(hwnd):
                    info=self.work_area()
                    if info:
                        rect=self.c.cast(lparam,self.c.POINTER(self.w.RECT)).contents
                        rect.left,rect.top,rect.right,rect.bottom=info.rcWork.left,info.rcWork.top,info.rcWork.right,info.rcWork.bottom
                return 0
            if message==0x0112 and wparam&0xfff0==0xF030 and not all(self._resize_axes):
                return 0  # SC_MAXIMIZE: a resizable(False) window never maximizes
            if message==0x0024:  # WM_GETMINMAXINFO, including multi-monitor taskbar bounds.
                result=self.u.CallWindowProcW(self._old_proc,hwnd,message,wparam,lparam)
                limits=self.c.cast(lparam,self.c.POINTER(self.MinMaxInfo)).contents
                # Tk locks a fixed axis to client + 2 x frame, but the frame is
                # now part of the client. Windows enforced that on every move
                # (+22 px per drag) and from transient minimize/restore sizes.
                # Lock fixed axes to the stable requested size instead.
                if self._fixed_size is not None:
                    if not self._resize_axes[0]:
                        limits.ptMinTrackSize.x=limits.ptMaxTrackSize.x=limits.ptMaxSize.x=self._fixed_size[0]
                    if not self._resize_axes[1]:
                        limits.ptMinTrackSize.y=limits.ptMaxTrackSize.y=limits.ptMaxSize.y=self._fixed_size[1]
                info=self.work_area()
                if info and all(self._resize_axes):
                    limits.ptMaxPosition.x=info.rcWork.left-info.rcMonitor.left
                    limits.ptMaxPosition.y=info.rcWork.top-info.rcMonitor.top
                    limits.ptMaxSize.x=info.rcWork.right-info.rcWork.left
                    limits.ptMaxSize.y=info.rcWork.bottom-info.rcWork.top
                return result
            if message==0x0084:  # WM_NCHITTEST, all pixel calculations; no Tk re-entry.
                x=self.c.c_short(lparam&0xffff).value;y=self.c.c_short((lparam>>16)&0xffff).value
                rect=self.w.RECT();self.u.GetWindowRect(hwnd,self.c.byref(rect))
                edge=getattr(self,'resize_margin',7)
                left=x<rect.left+edge and self._resize_axes[0];right=x>=rect.right-edge and self._resize_axes[0]
                top=y<rect.top+edge and self._resize_axes[1];bottom=y>=rect.bottom-edge and self._resize_axes[1]
                if not self.u.IsZoomed(hwnd):
                    if top and left:return 13
                    if top and right:return 14
                    if bottom and left:return 16
                    if bottom and right:return 17
                    if left:return 10
                    if right:return 11
                    if top:return 12
                    if bottom:return 15
                contains=lambda r:r[0]<=x<r[2] and r[1]<=y<r[3]
                if any(contains(r) for r in self._excluded):return 1
                if any(contains(r) for r in self._drag_rects):return 2
        except Exception:
            # A platform-specific edge case must not crash the window procedure.
            pass
        return self.u.CallWindowProcW(self._old_proc,hwnd,message,wparam,lparam)

    def schedule_cache(self,event=None):
        if event is not None and event.widget is not self.root:return
        if self._cache_job is None:self._cache_job=self.root.after_idle(self.refresh_cache)

    def refresh_cache(self):
        self._cache_job=None
        if not self.attached:return
        # Tk destroys and recreates its wrapper HWND after wm resizable /
        # transient / attributes changes. Follow it, or the new wrapper shows
        # the native caption again and every Win32 call targets a dead handle.
        wrapper=self.u.GetParent(self.root.winfo_id())
        if wrapper and wrapper!=self.hwnd:
            if self.u.IsWindow(self.hwnd):self.set_long(self.hwnd,-4,self.c.c_void_p(self._old_proc))
            self.attached=False
            self.attach()
            return
        self.sync_capabilities()
        self.resize_margin=max(5,round(self.root.winfo_fpixels('1i')/96*5))
        self.layout_resize_handles()
        def rect(widget):
            x,y=widget.winfo_rootx(),widget.winfo_rooty()
            return x,y,x+widget.winfo_width(),y+widget.winfo_height()
        self._drag_rects=[rect(widget) for widget in self.drag_widgets if widget.winfo_exists()]
        self._excluded=[rect(widget) for widget in self.toolbar.winfo_children()
                        if widget not in self.drag_widgets and widget.winfo_ismapped()]
        self._excluded.extend(rect(widget) for widget in self.extra_exclusions if widget.winfo_exists() and widget.winfo_ismapped())
        self.paint_control('maximize',False)

    def paint_control(self,key,hover=False):
        button=self.buttons.get(key)
        if button is None or not button.winfo_exists():return
        pinned=key=='pin' and self.pinned
        disabled=self.buttons[key].instate(['disabled'])
        hover=hover and not disabled
        background=('#FFE8E8' if key=='close' else PALETTE['hover']) if hover else PALETTE['selected'] if pinned else PALETTE['bg']
        color=PALETTE['disabled'] if disabled else '#DD3333' if key=='close' and hover else PALETTE['blue'] if pinned else PALETTE['muted']
        symbol='restore' if key=='maximize' and self.attached and self.u.IsZoomed(self.hwnd) else key
        signature=(symbol,color,background,pinned)
        if self._drawn_controls.get(key)==signature:return
        self._drawn_controls[key]=signature
        self.buttons[key].configure(image=icon(self.root,symbol,self.icon_size,color=color,background=background),
                                   style='Close.TButton' if key=='close' else 'CardIcon.TButton' if pinned else 'Quiet.TButton')

    def toggle_pin(self):
        self.pinned=not self.pinned
        self.root.attributes('-topmost',self.pinned)
        self.paint_control('pin')

    def drag(self,event):
        if not self.attached:return
        if self._native_moving or self._system_move_pending:return 'break'
        self._system_move_pending=True
        self.u.ReleaseCapture()
        point=((int(event.y_root)&0xffff)<<16)|(int(event.x_root)&0xffff)
        # Child HWND fallback: post a system command and return to Tk first.
        # Never synchronously send WM_NCLBUTTONDOWN from a Tk mouse callback.
        if not self.u.PostMessageW(self.hwnd,0x0112,0xF012,point):self._system_move_pending=False
        return 'break'

    def drag_motion(self,event):
        if self._drag_anchor is None:return
        x,y,left,top=self._drag_anchor
        self._drag_target=(left+event.x_root-x,top+event.y_root-y)
        if self._drag_job is None:self._drag_job=self.root.after(12,self.flush_drag)
        return 'break'

    def flush_drag(self):
        self._drag_job=None
        if self._drag_target is not None and self.attached:
            x,y=self._drag_target;self._drag_target=None
            self.u.SetWindowPos(self.hwnd,None,round(x),round(y),0,0,0x0001|0x0004|0x0010)

    def end_drag(self,event=None):
        if self._drag_job is not None:
            self.root.after_cancel(self._drag_job);self._drag_job=None
        self.flush_drag()
        self._drag_anchor=None
        if self._drag_widget is not None:
            try:self._drag_widget.grab_release()
            except tk.TclError:pass
            self._drag_widget=None
        return 'break'

    def cancel_drag(self,event=None):
        if self._native_moving or self._system_move_pending:
            self.u.PostMessageW(self.hwnd,0x001F,0,0)
            self._system_move_pending=False
            return 'break'
        if self._drag_anchor is None and self._drag_job is None:return None
        self._drag_target=None
        return self.end_drag(event)

    def double_click(self,event):
        self.end_drag()
        self.toggle_maximize();return 'break'

    def toggle_maximize(self):
        # Double-click and the maximize button do nothing for a fixed window.
        if not all(self.root.resizable()) and self.root.state()!='zoomed':return
        self.begin_update()
        try:
            self.root.state('normal' if self.root.state()=='zoomed' else 'zoomed')
            self.root.update_idletasks()
        finally:self.end_update()
        self.schedule_cache()

    def begin_update(self):
        if self.attached:
            if self._batch_depth==0:self.u.SendMessageW(self.hwnd,0x000B,0,0)
            self._batch_depth+=1

    def end_update(self):
        if self.attached and self._batch_depth:
            self._batch_depth-=1
            if self._batch_depth==0:
                self.u.SendMessageW(self.hwnd,0x000B,1,0)
                self.u.RedrawWindow(self.hwnd,None,None,0x0001|0x0080|0x0100|0x0400)

    def minimize(self):self.root.iconify()

    def close(self):
        self.detach()
        self.close_action()

    def detach(self):
        if sys.platform!='win32':return
        self.cancel_drag()
        for handle in self.resize_handles.values():
            if handle.winfo_exists():handle.destroy()
        self.resize_handles.clear()
        while self._batch_depth:self.end_update()
        for job in (self._cache_job,getattr(self,'_attach_job',None),self._size_job):
            if job is not None:
                try:self.root.after_cancel(job)
                except tk.TclError:pass
        if self.attached and self._old_proc:
            self.set_long(self.hwnd,-4,self.c.c_void_p(self._old_proc))
            self.attached=False
        for name,(owned,original) in self._geometry_originals.items():
            if getattr(self.root,name,None) is self._geometry_bridge:
                if owned:setattr(self.root,name,original)
                else:self.root.__dict__.pop(name,None)
        self._geometry_originals.clear()
