"""Small-radius Web controls. Uses only tkinter and the Python standard library."""
from __future__ import annotations
import math
import sys
import tkinter as tk
from tkinter import ttk, font as tkfont
from .core import PALETTE, Card, ScrollArea, Modal, icon, _patch, _raster, _rgb
from .tcl_bridge import unbind


def configure_extra_styles(root, style):
    c = PALETTE
    scale = root.winfo_fpixels('1i') / 96
    px = lambda n: max(1, round(n * scale))
    cache = {}
    def face(fill, border, radius=4):
        key = fill, border, radius
        if key not in cache:
            image = _patch(root, fill, border, c['bg'], px(radius))
            root._tkwebui_images.append(image)
            cache[key] = image
        return cache[key]
    def surface(name, normal, states=(), radius=4, **options):
        style.element_create(name, 'image', normal, *states, border=px(radius)+1,
                             width=px(radius)*2+2, height=px(radius)*2+2, sticky='nsew', **options)
    for name, plain in [('Toggle.TButton', False), ('Toolbutton', True)]:
        element = 'Web.'+name+'.surface'
        surface(element, face(c['bg'], c['bg'] if plain else c['border']), [
            ('disabled selected', face(c['sidebar'], c['border'])),
            ('disabled', face(c['bg'], c['bg'] if plain else c['border'])),
            ('pressed', face(c['selected'], c['blue'])),
            ('selected', face(c['selected'], c['blue'] if not plain else c['selected'])),
            ('focus', face(c['bg'], c['blue'])),
            ('active', face(c['hover'], c['hover'] if plain else c['border'])),
        # Same box as TButton: the style padding alone sets the content inset
        # (ttk would default an image element's padding to its border).
        ], padding=0)
        style.layout(name, [(element, {'sticky':'nsew', 'children':[
            ('Checkbutton.padding', {'sticky':'nsew', 'children':[
                ('Checkbutton.label', {'sticky':'nsew'})]})]})])
        style.configure(name, padding=(px(12),px(7)), anchor='center', foreground=c['fg'])
        style.map(name, foreground=[('disabled',c['disabled']),('selected',c['blue'])])
    # Compact rectangular switch; square thumb, with state handling kept in ttk.
    switch_images={}
    for on in (False,True):
        for state in ('normal','active','focus','disabled'):
            width,height=px(40),px(26)
            track_color=(c['disabled'] if on else '#D9DEE6') if state=='disabled' else (
                c['accent_hover'] if on and state=='active' else c['accent'] if on else
                '#858E9C' if state=='active' else '#9B9DA7')
            def sample(x,y,on=on,state=state,width=width,height=height,track_color=track_color):
                x=x*40/width;y=y*26/height
                if state=='focus' and 0.5<=x<=39.5 and 0.5<=y<=25.5:
                    if x<1.5 or x>38.5 or y<1.5 or y>24.5:return _rgb(c['blue'])
                if not (3<=x<=37 and 3<=y<=23):return _rgb(c['bg'])
                left=20 if on else 6
                if left<=x<=left+14 and 6<=y<=20:
                    return _rgb('#F7F8FA' if state=='disabled' else '#FFFFFF')
                return _rgb(track_color)
            image=_raster(root,width,height,sample)
            switch_images[on,state]=image;root._tkwebui_images.append(image)
    style.element_create('Web.SquareSwitch.indicator','image',switch_images[False,'normal'],
        ('disabled selected',switch_images[True,'disabled']),('disabled',switch_images[False,'disabled']),
        ('focus selected',switch_images[True,'focus']),('focus',switch_images[False,'focus']),
        ('active selected',switch_images[True,'active']),('active',switch_images[False,'active']),
        ('selected',switch_images[True,'normal']),width=px(40),height=px(26),sticky='')
    style.layout('Square.Switch.TCheckbutton',[('Checkbutton.padding',{'sticky':'nsew','children':[
        ('Web.SquareSwitch.indicator',{'side':'left'}),('Checkbutton.label',{'side':'left','sticky':'w'})]})])
    style.configure('Square.Switch.TCheckbutton',background=c['bg'],padding=(0,px(2)),foreground=c['fg'])
    style.map('Square.Switch.TCheckbutton',background=[('active',c['bg'])],foreground=[('disabled',c['disabled'])])
    for name in ('TMenubutton', 'TOptionMenu'):
        style.layout(name, [('TButton.surface', {'sticky':'nsew','children':[
            ('Menubutton.padding', {'sticky':'nsew','children':[
                ('Switch.Dropdown.arrow', {'side':'right','sticky':''}),
                ('Menubutton.label', {'side':'left','sticky':'nsew','expand':True})]})]})])
        style.configure(name, padding=(px(10),px(7)), anchor='w')
        style.map(name, foreground=[('disabled',c['disabled'])])
    surface('Web.Labelframe.border', face(c['bg'],c['border']))
    style.layout('TLabelframe', [('Web.Labelframe.border',{'sticky':'nsew'})])
    style.configure('TLabelframe', background=c['bg'], borderwidth=px(1), relief='flat')
    style.configure('TLabelframe.Label', background=c['bg'], foreground=c['muted'], font=('Microsoft YaHei UI',10))
    surface('Web.Notebook.client', face(c['bg'],c['border']))
    surface('Web.Notebook.tab', face(c['bg'],c['bg']), [
        ('disabled',face(c['bg'],c['bg'])),
        ('selected focus',face(c['selected'],c['blue'])),
        ('selected',face(c['selected'],c['selected'])),
        ('active',face(c['hover'],c['hover'])),
    ])
    style.layout('TNotebook', [('Web.Notebook.client',{'sticky':'nsew'})])
    style.layout('TNotebook.Tab', [('Web.Notebook.tab',{'sticky':'nsew','children':[
        ('Notebook.padding',{'sticky':'nsew','children':[('Notebook.label',{'sticky':'nsew'})]})]})])
    style.configure('TNotebook', background=c['bg'], padding=px(1), tabmargins=(0,0,0,px(7)))
    style.configure('TNotebook.Tab', padding=(px(16),px(8)), foreground=c['muted'])
    style.map('TNotebook.Tab', foreground=[('disabled',c['disabled']),('selected',c['blue'])])
    # Both sash orientations have a generous hit target and a small visible handle.
    for orientation in ('Horizontal','Vertical'):
        horizontal = orientation == 'Horizontal'
        w,h = (px(36),px(12)) if horizontal else (px(12),px(36))
        def sample(x,y,w=w,h=h,horizontal=horizontal):
            long,short = (x,y) if horizontal else (y,x)
            length,thickness = (w,h) if horizontal else (h,w)
            center=min(max(long,px(5)),length-px(5))
            return _rgb('#BFC4CD') if math.hypot(long-center,short-thickness/2)<=max(1,scale) else _rgb(c['bg'])
        grip=_raster(root,w,h,sample); root._tkwebui_images.append(grip)
        name='Web.'+orientation+'.Sash.grip'
        style.element_create(name,'image',grip,width=w,height=h,sticky='')
        style.layout(orientation+'.Sash',[(name,{'sticky':'ns' if not horizontal else 'ew'})])
    style.configure('Sash',sashthickness=px(12),gripcount=0)
    # Round and compact-bar slider variants share native ttk Scale behavior.
    for orient in ('Horizontal','Vertical'):
        horizontal=orient=='Horizontal'
        w,h=(px(128),px(24)) if horizontal else (px(24),px(128))
        def track(x,y,w=w,h=h,horizontal=horizontal):
            long,short=(x,y) if horizontal else (y,x)
            length,thickness=(w,h) if horizontal else (h,w)
            center=min(max(long,px(12)),length-px(12))
            return _rgb(c['hover']) if math.hypot(long-center,short-thickness/2)<=px(2) else _rgb(c['bg'])
        image=_raster(root,w,h,track); root._tkwebui_images.append(image)
        track_name='Web.'+orient+'.Scale.trough'
        style.element_create(track_name,'image',image,border=(px(12),0) if horizontal else (0,px(12)),
                             width=px(24),height=px(24),sticky='nsew')
        for variant in ('','Tick.'):
            images=[]
            size=px(24)
            for edge,fill in [(c['border'],c['bg']),(c['blue'],c['bg']),(c['disabled'],c['sidebar'])]:
                def thumb(x,y,edge=edge,fill=fill,variant=variant,size=size,horizontal=horizontal):
                    cx,cy=size/2,size/2
                    if variant:
                        a,b=(x,y) if horizontal else (y,x)
                        nearest=min(max(b,cy-px(5)),cy+px(5))
                        distance=math.hypot(a-cx,b-nearest)
                        return _rgb(edge if edge==c['disabled'] else c['blue']) if distance<=px(2) else _rgb(c['bg'])
                    d=math.hypot(x-cx,y-cy)
                    return _rgb(fill) if d<px(7)-1 else _rgb(edge) if d<=px(7) else _rgb(c['bg'])
                im=_raster(root,size,size,thumb,transparent=_rgb(c['bg']) if variant else None,
                           outside=None if variant else lambda xx,yy,size=size:math.hypot(xx+.5-size/2,yy+.5-size/2)>px(7)+1)
                root._tkwebui_images.append(im);images.append(im)
            slider_name='Web.'+orient+'.'+variant+'Scale.slider'
            style.element_create(slider_name,'image',images[0],('disabled',images[2]),('pressed',images[1]),('active',images[1]),('focus',images[1]),width=size,height=size,sticky='')
            name=orient+'.'+variant+'TScale'
            style.layout(name,[(track_name,{'sticky':'ew' if horizontal else 'ns','children':[
                (slider_name,{'side':'left' if horizontal else 'top','sticky':''})]})])
            style.configure(name,background=c['bg'],borderwidth=0)
        # Small-radius progress surfaces, horizontal and vertical.
        for part,color in [('trough',c['hover']),('pbar',c['accent'])]:
            width,height=(px(128),px(7)) if horizontal else (px(7),px(128))
            im=_patch(root,color,color,c['bg'],px(2),width=width,height=height)
            root._tkwebui_images.append(im)
            element='Web.'+orient+'.Progress.'+part
            style.element_create(element,'image',im,border=px(2),width=px(7),height=px(7),sticky='nsew')
        style.layout(orient+'.TProgressbar', [('Progressbar.padding',{'sticky':'nsew','children':[
            ('Web.'+orient+'.Progress.trough',{'sticky':'ew' if horizontal else 'ns','children':[
                ('Web.'+orient+'.Progress.pbar',{'side':'left' if horizontal else 'bottom','sticky':'ns' if horizontal else 'ew'})]})]})])
        style.configure(orient+'.TProgressbar',background=c['bg'],thickness=px(7),borderwidth=0,padding=(px(14),0) if horizontal else (0,px(14)))
    blank=tk.PhotoImage(master=root,width=px(16),height=px(16));root._tkwebui_images.append(blank)
    style.element_create('Web.Tree.indicator','image',icon(root,'chevronright',px(13)),('user2',blank),('user1',icon(root,'chevrondown',px(13))),width=px(24),sticky='')
    style.layout('Treeview.Item',[('Treeitem.padding',{'sticky':'nsew','children':[
        ('Web.Tree.indicator',{'side':'left'}),('Treeitem.image',{'side':'left'}),('Treeitem.text',{'sticky':'nsew'})]})])
    style.configure('Treeview.Item',padding=(px(3),0))
    size=px(15)
    grip=tk.PhotoImage(master=root,width=size,height=size)
    for a,b in [(10,10),(6,10),(10,6),(2,10),(6,6),(10,2)]:
        grip.put(c['disabled'],to=(px(a),px(b),px(a)+px(2),px(b)+px(2)))
    root._tkwebui_images.append(grip)
    style.element_create('Web.Sizegrip','image',grip,sticky='se',width=size,height=size)
    style.layout('TSizegrip',[('Web.Sizegrip',{'side':'bottom','sticky':'se'})])
    style.layout('Web.List.TFrame',style.layout('RoundedText.TFrame'))
    for name,fill in [('Web.MenuRow.TFrame',c['bg']),('Web.ActiveMenuRow.TFrame',c['hover'])]:
        element=name+'.surface';surface(element,face(fill,fill),radius=4)
        style.layout(name,[(element,{'sticky':'nsew'})])
        style.configure(name,background=fill)


class SquareSwitch(ttk.Checkbutton):
    """Rectangular sliding switch with a square thumb; standard Checkbutton API."""
    def __init__(self,master=None,**kwargs):
        if 'variable' not in kwargs:
            self.variable=tk.BooleanVar(master=master,value=False)
            kwargs['variable']=self.variable
        else:self.variable=kwargs['variable']
        kwargs.setdefault('style','Square.Switch.TCheckbutton')
        super().__init__(master,**kwargs)
        self.bind('<Return>',self._activate)
    def _activate(self,event=None):
        self.invoke()
        return 'break'


class ToggleButton(ttk.Checkbutton):
    def __init__(self, master=None, **kwargs):
        kwargs.setdefault('style','Toggle.TButton')
        super().__init__(master,**kwargs)


class ToolButton(ttk.Checkbutton):
    def __init__(self, master=None, **kwargs):
        kwargs.setdefault('style','Toolbutton')
        super().__init__(master,**kwargs)


class MenuButton(ttk.Menubutton):
    """A real ttk Menubutton that opens the unified Web menu instead of Tk's popup."""
    def __init__(self, master=None, **kwargs):
        super().__init__(master,**kwargs)
        self.bind('<ButtonPress-1>',self.post_menu)
        self.bind('<ButtonRelease-1>',lambda e:'break')
        for event in ('<space>','<Return>','<Down>','<Alt-Down>'):
            self.bind(event,self.post_menu)
        self.bind('<Destroy>',self._cleanup,add='+')
    def post_menu(self,event=None):
        if self.instate(['disabled']):return 'break'
        self.focus_set()
        name=str(self.cget('menu'))
        if not name:return 'break'
        menu=self.nametowidget(name)
        popup=getattr(menu,'popup',None) or getattr(menu,'_web_popup',None)
        if popup is not None and not popup._closed:
            menu.unpost();return 'break'
        if hasattr(menu,'popup'):
            menu.tk_popup(self.winfo_rootx(),self.winfo_rooty()+self.winfo_height()+4,owner=self,min_width=self.winfo_width())
        else:
            # A supplied plain tk.Menu also gets the Web renderer.
            menu._web_popup=MenuPopup(self,menu,self.winfo_rootx(),self.winfo_rooty()+self.winfo_height()+4,min_width=self.winfo_width())
        return 'break'
    def _cleanup(self,event):
        if event.widget is not self:return
        try:
            name=str(self.cget('menu'))
            if name:
                menu=self.nametowidget(name)
                popup=getattr(menu,'popup',None) or getattr(menu,'_web_popup',None)
                if popup is not None and not popup._closed:popup.close()
        except (tk.TclError,KeyError):pass


class OptionMenu(MenuButton):
    """ttk.OptionMenu-like API backed by the same rounded menu as MenuButton."""
    def __init__(self,master,variable,default=None,*values,command=None,**kwargs):
        from .popups import ThemedMenu
        self.variable=variable;self.on_change=command
        kwargs.setdefault('style','TOptionMenu')
        kwargs['textvariable']=variable
        super().__init__(master,**kwargs)
        self.menu=ThemedMenu(self,tearoff=False)
        self.configure(menu=self.menu)
        self.set_menu(default,*values)
    def set_menu(self,default=None,*values):
        self.menu.delete(0,'end')
        for value in values:
            self.menu.add_radiobutton(label=value,value=value,variable=self.variable,command=lambda v=value:self._selected(v))
        if default is not None:self.variable.set(default)
    def _selected(self,value):
        self.event_generate('<<OptionMenuSelected>>',when='tail')
        if self.on_change:self.on_change(value)


class RoundedListbox(tk.Listbox):
    """Native Listbox API, small-radius focus shell, hover rows and native selection."""
    def __init__(self,master,*,scrollbars=True,**kwargs):
        from .widgets import _TextContainer
        from .scrolling import _attach_scrollbars
        self.container=_TextContainer(master,style='Web.List.TFrame',padding=6)
        self.container.columnconfigure(0,weight=1);self.container.rowconfigure(0,weight=1)
        kwargs.update(borderwidth=0,highlightthickness=0,relief='flat')
        for key,value in dict(background=PALETTE['bg'],foreground=PALETTE['fg'],selectbackground=PALETTE['selected'],
                              selectforeground=PALETTE['blue'],activestyle='none',exportselection=False).items():
            kwargs.setdefault(key,value)
        super().__init__(self.container,**kwargs)
        tk.Listbox.grid(self,row=0,column=0,sticky='nsew')
        if scrollbars:_attach_scrollbars(self,self.container)
        self._hover=None
        self.bind('<FocusIn>',lambda e:self.container.state(['focus']),add='+')
        self.bind('<FocusOut>',lambda e:self.container.state(['!focus']),add='+')
        self.bind('<Motion>',self._motion,add='+');self.bind('<Leave>',lambda e:self._restore(),add='+')
        self._sync()
    def _sync(self):
        self.container.state(['disabled' if str(self.cget('state'))=='disabled' else '!disabled'])
    def _restore(self):
        if self._hover is not None:
            index,color=self._hover;self._hover=None
            if index<self.size():self.itemconfigure(index,background=color)
    def _motion(self,event):
        if str(self.cget('state'))=='disabled' or not self.size():return
        index=self.nearest(event.y)
        bounds=self.bbox(index)
        if bounds is None or not bounds[1]<=event.y<bounds[1]+bounds[3]:self._restore();return
        if self._hover is not None and self._hover[0]==index:return
        self._restore();self._hover=(index,self.itemcget(index,'background'))
        self.itemconfigure(index,background=PALETTE['hover'])
    def delete(self,first,last=None):
        self._restore();return super().delete(first,last)
    def configure(self,cnf=None,**kwargs):
        if isinstance(cnf,str):return super().configure(cnf,**kwargs)
        options=dict(cnf or {},**kwargs)
        if not options:return super().configure()
        options.update(borderwidth=0,highlightthickness=0,relief='flat')
        result=super().configure(**options)
        from .scrolling import _release_scrollbars
        _release_scrollbars(self,options)
        self._sync();return result
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


def _monitor_api():
    """Private user32 prototypes. Setting argtypes on the shared ctypes.windll
    object would break other code (including the host program) that calls the
    same functions with its own structures."""
    global _MONITOR_API
    if _MONITOR_API is None:
        import ctypes
        from types import SimpleNamespace
        from ctypes import wintypes as w
        class MonitorInfo(ctypes.Structure):
            _fields_=[('cbSize',w.DWORD),('rcMonitor',w.RECT),('rcWork',w.RECT),('dwFlags',w.DWORD)]
        user=ctypes.WinDLL('user32')
        user.MonitorFromPoint.argtypes=[w.POINT,w.DWORD];user.MonitorFromPoint.restype=w.HANDLE
        user.GetMonitorInfoW.argtypes=[w.HANDLE,ctypes.POINTER(MonitorInfo)];user.GetMonitorInfoW.restype=w.BOOL
        _MONITOR_API=SimpleNamespace(ctypes=ctypes,w=w,user=user,MonitorInfo=MonitorInfo)
    return _MONITOR_API


_MONITOR_API=None


class MenuPopup(tk.Toplevel):
    """Shared menu renderer with native Menu commands/variables and nested popups."""
    def __init__(self,owner,menu,x,y,*,min_width=190,parent_popup=None,parent_index=None,selected=None):
        self.owner=owner;self.menu=menu;self.host=owner.winfo_toplevel()
        self.parent_popup=parent_popup;self.parent_index=parent_index
        self.root_popup=parent_popup.root_popup if parent_popup else self
        self.child_popup=None;self.cursor=None;self.rows={};self._closed=False
        self._hover_job=None;self._focus_job=None;self._region_size=None
        self._host_binding=None;self._destroy_binding=None
        self.scale=owner.winfo_fpixels('1i')/96;self.px=lambda n:max(1,round(n*self.scale));self.corner_radius=5
        if parent_popup is None:
            existing=getattr(self.host,'_choice_popup',None)
            if existing is not None:existing.close()
            self.previous_focus=owner.focus_get();self.previous_grab=owner.grab_current()
        command=str(menu.cget('postcommand')).strip()
        if command:menu.tk.call('uplevel','#0',command)
        super().__init__(self.host)
        self.withdraw();self.overrideredirect(True);self.transient(self.host);self.configure(background=PALETTE['bg'])
        shell=Card(self,padding=5,border_color='#CCD1DC');shell.pack(fill='both',expand=True,padx=1,pady=1)
        self.area=ScrollArea(shell);self.area.pack(fill='both',expand=True)
        end=menu.index('end')
        for index in range(end+1 if end is not None else 0):
            kind=menu.type(index)
            if kind=='tearoff':continue
            if kind=='separator':
                ttk.Separator(self.area.body).pack(fill='x',padx=self.px(7),pady=self.px(5));continue
            disabled=str(menu.entrycget(index,'state'))=='disabled'
            checked=False
            if kind in ('checkbutton','radiobutton'):
                variable=menu.entrycget(index,'variable')
                expected=menu.entrycget(index,'onvalue' if kind=='checkbutton' else 'value')
                try:checked=str(menu.getvar(variable))==str(expected)
                except tk.TclError:pass
            row=ttk.Frame(self.area.body,style='Web.MenuRow.TFrame',padding=(self.px(8),self.px(6)))
            row.pack(fill='x',pady=1)
            foreground=PALETTE['disabled'] if disabled else PALETTE['blue'] if checked else PALETTE['fg']
            widgets=[]
            mark=tk.Label(row,text='✓' if checked else '',width=2,anchor='center',borderwidth=0,background=PALETTE['bg'],foreground=foreground)
            mark.pack(side='left');widgets.append(mark)
            image=str(menu.entrycget(index,'image'))
            if image:
                picture=tk.Label(row,image=image,borderwidth=0,background=PALETTE['bg'])
                picture.pack(side='left',padx=(0,self.px(7)));widgets.append(picture)
            suffix='›' if kind=='cascade' else str(menu.entrycget(index,'accelerator'))
            if suffix:
                shortcut=tk.Label(row,text=suffix,borderwidth=0,background=PALETTE['bg'],foreground=PALETTE['disabled'] if disabled else PALETTE['muted'])
                shortcut.pack(side='right',padx=(self.px(28),self.px(4)));widgets.append(shortcut)
            label=tk.Label(row,text=menu.entrycget(index,'label'),anchor='w',borderwidth=0,background=PALETTE['bg'],foreground=foreground)
            label.pack(side='left',fill='x',expand=True);widgets.append(label)
            self.rows[index]=(row,widgets,disabled,kind)
            for widget in [row,*widgets]:
                widget.bind('<Enter>',lambda e,i=index:self.hover(i))
                widget.bind('<ButtonRelease-1>',lambda e,i=index:self.choose(i))
        self.update_idletasks()
        left,top,right,bottom=self.work_area(x,y)
        width=min(max(self.px(190),min_width,self.area.body.winfo_reqwidth()+self.px(18)),right-left-self.px(16))
        height=min(self.area.body.winfo_reqheight()+self.px(18),self.px(430),bottom-top-self.px(24))
        if parent_popup and x+width>right-self.px(8):x=parent_popup.winfo_rootx()-width+self.px(4)
        elif parent_popup is None and y+height>bottom-self.px(8) and owner.winfo_viewable():
            y=min(y,owner.winfo_rooty()-height-self.px(4))
        x=max(left+self.px(8),min(x,right-width-self.px(8)))
        y=max(top+self.px(8),min(y,bottom-height-self.px(8)))
        self.geometry(f'{width}x{height}{int(x):+d}{int(y):+d}')
        self.bind('<Up>',lambda e:self.move(-1));self.bind('<Down>',lambda e:self.move(1))
        self.bind('<Home>',lambda e:self.highlight(next(iter(self.enabled()),None)))
        self.bind('<End>',lambda e:self.highlight(self.enabled()[-1] if self.enabled() else None))
        self.bind('<Return>',lambda e:self.choose(self.cursor));self.bind('<space>',lambda e:self.choose(self.cursor))
        self.bind('<Right>',lambda e:self.open_child(self.cursor))
        self.bind('<Left>',self.go_back);self.bind('<Escape>',self.go_back)
        self.bind('<Tab>',lambda e:self.root_popup.close())
        self.bind('<ButtonPress-1>',self.outside,add='+')
        self.bind('<FocusOut>',lambda e:self.root_popup.defer_focus_check(),add='+')
        if parent_popup is None:
            self.host._choice_popup=self
            self._host_binding=self.host.bind('<Configure>',self.host_configured,add='+')
            self._destroy_binding=self.host.bind('<Destroy>',self.host_destroyed,add='+')
        self.attributes('-topmost',True);self.deiconify();self.update_idletasks()
        Modal.round_corners(self);self.lift();self.focus_force()
        if parent_popup is None:self.grab_set()
        if selected not in self.enabled():selected=next(iter(self.enabled()),None)
        self.highlight(selected)
    @staticmethod
    def work_area(x,y):
        if sys.platform=='win32':
            api=_monitor_api()
            info=api.MonitorInfo();info.cbSize=api.ctypes.sizeof(info)
            if api.user.GetMonitorInfoW(api.user.MonitorFromPoint(api.w.POINT(int(x),int(y)),2),api.ctypes.byref(info)):
                r=info.rcWork;return r.left,r.top,r.right,r.bottom
        root=tk._default_root
        return 0,0,root.winfo_screenwidth(),root.winfo_screenheight()
    def enabled(self):return [i for i,(_,_,disabled,_) in self.rows.items() if not disabled]
    def highlight(self,index):
        if index not in self.enabled():return 'break'
        if self.cursor is not None and self.cursor in self.rows:
            row,widgets,_,_=self.rows[self.cursor];row.configure(style='Web.MenuRow.TFrame')
            for widget in widgets:widget.configure(background=PALETTE['bg'])
        self.cursor=index
        row,widgets,_,_=self.rows[index];row.configure(style='Web.ActiveMenuRow.TFrame')
        for widget in widgets:widget.configure(background=PALETTE['hover'])
        self.update_idletasks()
        total=max(1,self.area.body.winfo_reqheight());first,last=self.area.canvas.yview()
        y=row.winfo_y();end=y+row.winfo_height()
        if y<first*total:self.area.canvas.yview_moveto(y/total)
        elif end>last*total:self.area.canvas.yview_moveto((end-self.area.canvas.winfo_height())/total)
        return 'break'
    def hover(self,index):
        if self._hover_job is not None:self.after_cancel(self._hover_job);self._hover_job=None
        if index not in self.enabled():return
        if index!=self.cursor and self.child_popup is not None:self.child_popup.close()
        self.highlight(index)
        if self.rows[index][3]=='cascade':self._hover_job=self.after(180,lambda:self.open_child(index))
    def move(self,delta):
        if self.child_popup is not None:self.child_popup.close()
        indices=self.enabled()
        if indices:self.highlight(indices[(indices.index(self.cursor)+delta)%len(indices)] if self.cursor in indices else indices[0])
        return 'break'
    def choose(self,index):
        if index not in self.enabled():return 'break'
        if self.rows[index][3]=='cascade':return self.open_child(index)
        menu=self.menu;self.root_popup.close()
        if menu.winfo_exists():menu.invoke(index)
        return 'break'
    def open_child(self,index):
        if self._hover_job is not None:self.after_cancel(self._hover_job)
        self._hover_job=None
        if self._closed or index not in self.enabled() or self.rows[index][3]!='cascade':return 'break'
        self.highlight(index)
        if self.child_popup is not None and not self.child_popup._closed and self.child_popup.parent_index==index:
            self.child_popup.focus_force();return 'break'
        if self.child_popup is not None:self.child_popup.close()
        submenu=self.menu.nametowidget(self.menu.entrycget(index,'menu'))
        ancestor=self
        while ancestor is not None:
            if ancestor.menu is submenu:return 'break'
            ancestor=ancestor.parent_popup
        row=self.rows[index][0]
        self.child_popup=MenuPopup(self.owner,submenu,self.winfo_rootx()+self.winfo_width()-self.px(4),row.winfo_rooty()-self.px(6),
                                   parent_popup=self,parent_index=index)
        return 'break'
    def go_back(self,event=None):
        if self.parent_popup is not None:
            parent=self.parent_popup;self.close();parent.focus_force()
        else:self.close()
        return 'break'
    def chain(self):
        current=self.root_popup
        while current is not None and not current._closed:
            yield current;current=current.child_popup
    def outside(self,event):
        if not any(p.winfo_rootx()<=event.x_root<p.winfo_rootx()+p.winfo_width() and p.winfo_rooty()<=event.y_root<p.winfo_rooty()+p.winfo_height() for p in self.chain()):
            self.root_popup.close()
    def defer_focus_check(self):
        if not self._closed and self._focus_job is None:self._focus_job=self.after(100,self.check_focus)
    def check_focus(self):
        self._focus_job=None
        if self._closed:return
        focus=self.focus_get()
        if focus is None or focus.winfo_toplevel() not in list(self.chain()):self.close(restore_focus=False)
    def host_configured(self,event):
        if event.widget is self.host:self.close()
    def host_destroyed(self,event):
        if event.widget is self.host:self.close(restore_focus=False)
    def close(self,*,restore_focus=True):
        if self._closed:return 'break'
        self._closed=True
        for job in (self._hover_job,self._focus_job):
            if job is not None:self.after_cancel(job)
        if self.child_popup is not None:self.child_popup.close(restore_focus=False)
        if self.parent_popup is not None:
            self.parent_popup.child_popup=None
            super().destroy()
            return 'break'
        if self._host_binding:unbind(self.host,'<Configure>',self._host_binding)
        if self._destroy_binding:unbind(self.host,'<Destroy>',self._destroy_binding)
        if getattr(self.host,'_choice_popup',None) is self:self.host._choice_popup=None
        self.grab_release();super().destroy()
        try:
            if self.previous_grab is not None and self.previous_grab.winfo_exists():self.previous_grab.grab_set()
            if restore_focus:
                target=self.previous_focus
                if target is None or not target.winfo_exists() or not target.winfo_viewable():target=self.host
                if target.winfo_exists():target.focus_force()
        except tk.TclError:pass
        return 'break'
    def destroy(self):self.close()
