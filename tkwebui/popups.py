"""Rounded context menus and ComboBox popups, retaining original widget APIs."""
import tkinter as tk
from tkinter import ttk, font as tkfont
from .core import Card, ScrollArea, Modal, PALETTE
from .tcl_bridge import unbind

class ChoicePopup(tk.Toplevel):
    def __init__(self,owner,items,x,y,*,width=180,selected=0,above=None):
        self.owner=owner
        self.host=owner.winfo_toplevel()
        existing=getattr(self.host,'_choice_popup',None)
        if existing is not None:existing.close()
        self.previous_focus=owner.focus_get()
        self.previous_grab=owner.grab_current()
        super().__init__(self.host)
        self.withdraw();self.overrideredirect(True);self.transient(self.host)
        self.configure(background=PALETTE['bg'])
        self.scale=owner.winfo_fpixels('1i')/96
        self.corner_radius=5
        self._closed=False;self._region_size=None;self._focus_job=None
        self.host._choice_popup=self
        self.items=items;self.rows=[];self.cursor=None
        shell=Card(self,padding=6,border_color='#CCD1DC')
        # Keep the one-pixel outline inside the native rounded window region.
        shell.pack(fill='both',expand=True,padx=1,pady=1)
        self.area=ScrollArea(shell);self.area.pack(fill='both',expand=True)
        font=tkfont.nametofont('TkDefaultFont')
        width=max(width,max((font.measure(str(item.get('label','')))+round(68*self.scale) for item in items),default=width))
        height=round(22*self.scale)
        for index,item in enumerate(items):
            if item.get('separator'):
                ttk.Separator(self.area.body).pack(fill='x',pady=round(5*self.scale))
                self.rows.append(None);height+=round(11*self.scale);continue
            text=('✓  ' if item.get('checked') else '    ')+str(item['label'])
            button=ttk.Button(self.area.body,text=text,style='Popup.Quiet.TButton',command=lambda i=index:self.choose(i),takefocus=False)
            if item.get('disabled'):button.state(['disabled'])
            if item.get('checked'):button.configure(style='Checked.Popup.Quiet.TButton')
            button.pack(fill='x',pady=1)
            button.bind('<Enter>',lambda _,i=index:self.highlight(i))
            self.rows.append(button);height+=button.winfo_reqheight()+2
        left,top,right,bottom=0,0,self.winfo_screenwidth(),self.winfo_screenheight()
        chrome=getattr(owner._root(),'_window_chrome',None)
        if chrome is not None and chrome.attached:
            info=chrome.work_area()
            if info:left,top,right,bottom=info.rcWork.left,info.rcWork.top,info.rcWork.right,info.rcWork.bottom
        width=min(width,right-left-16)
        height=min(height,round(430*self.scale),bottom-top-24)
        if above is not None and y+height>bottom-8:y=above-height-4
        x=max(left+8,min(x,right-width-8));y=max(top+8,min(y,bottom-height-8))
        self.geometry(f'{int(width)}x{int(height)}{int(x):+d}{int(y):+d}')
        self.bind('<Escape>',lambda _:self.close())
        self.bind('<Up>',lambda _:self.move(-1));self.bind('<Down>',lambda _:self.move(1))
        self.bind('<Home>',lambda _:self.highlight(self.enabled()[0]) if self.enabled() else 'break')
        self.bind('<End>',lambda _:self.highlight(self.enabled()[-1]) if self.enabled() else 'break')
        self.bind('<Return>',lambda _:self.choose(self.cursor))
        self.bind('<Tab>',lambda _:self.close())
        self.bind('<ButtonPress-1>',self.outside,add='+')
        self.bind('<FocusOut>',self.defer_focus_check,add='+')
        self._host_binding=self.host.bind('<Configure>',self.host_configured,add='+')
        self.attributes('-topmost',True)
        self.deiconify();self.update_idletasks()
        Modal.round_corners(self)
        self.lift();self.focus_force();self.grab_set()
        self.highlight(selected if selected in self.enabled() else next(iter(self.enabled()),None))

    def enabled(self):return [i for i,row in enumerate(self.rows) if row is not None and not row.instate(['disabled'])]
    def highlight(self,index):
        if index not in self.enabled():return 'break'
        if self.cursor is not None:self.rows[self.cursor].state(['!active'])
        self.cursor=index;row=self.rows[index];row.state(['active'])
        self.update_idletasks()
        canvas=self.area.canvas;total=max(1,self.area.body.winfo_reqheight())
        first,last=canvas.yview()
        y=row.winfo_y();end=y+row.winfo_height()
        if y<first*total:canvas.yview_moveto(y/total)
        elif end>last*total:canvas.yview_moveto((end-canvas.winfo_height())/total)
        return 'break'
    def move(self,delta):
        enabled=self.enabled()
        if enabled:self.highlight(enabled[(enabled.index(self.cursor)+delta)%len(enabled)] if self.cursor in enabled else enabled[0])
        return 'break'
    def choose(self,index):
        if index not in self.enabled():return 'break'
        action=self.items[index].get('command')
        self.close()
        if action:action()
        return 'break'
    def outside(self,event):
        if not (self.winfo_rootx()<=event.x_root<self.winfo_rootx()+self.winfo_width() and self.winfo_rooty()<=event.y_root<self.winfo_rooty()+self.winfo_height()):self.close()
    def host_configured(self,event):
        if event.widget is self.host:self.close()
    def defer_focus_check(self,event):
        if not self._closed and self._focus_job is None:self._focus_job=self.after(100,self.check_focus)
    def check_focus(self):
        self._focus_job=None
        if self._closed:return
        focus=self.focus_get()
        if focus is None or focus.winfo_toplevel() is not self:self.close(restore_focus=False)
    def close(self,*,restore_focus=True):
        if self._closed:return 'break'
        self._closed=True
        if self._focus_job is not None:self.after_cancel(self._focus_job)
        unbind(self.host,'<Configure>',self._host_binding)
        if getattr(self.host,'_choice_popup',None) is self:self.host._choice_popup=None
        self.grab_release();super().destroy()
        if self.previous_grab is not None and self.previous_grab.winfo_exists():self.previous_grab.grab_set()
        if restore_focus:
            target=self.previous_focus
            if target is None or not target.winfo_exists() or not target.winfo_viewable():target=self.host
            if target.winfo_exists():target.focus_force()
        return 'break'
    def destroy(self):self.close()

class ThemedCombobox(ttk.Combobox):
    """The native entry/current/values API with a replacement choice window."""
    def __init__(self,master=None,**kw):
        super().__init__(master,**kw)
        self.popup=None
        self.bind('<ButtonPress-1>',self.click,add='+')
        self.bind('<Down>',self.post_from_event)
        self.bind('<Alt-Down>',self.post_from_event)
        self.bind('<F4>',self.post_from_event)
        self.bind('<Destroy>',self.cleanup,add='+')
    def click(self,event):
        if self.instate(['disabled']):return 'break'
        if self.instate(['readonly']) or 'downarrow' in self.identify(event.x,event.y):return self.post_from_event()
    def post_from_event(self,event=None):
        try:self.open_popup()
        except Exception:
            import sys
            self._root().report_callback_exception(*sys.exc_info())
        # Never run the native TCombobox post binding, even on a failed custom
        # callback. Otherwise a second, unthemed popup opens underneath it.
        return 'break'
    def open_popup(self,event=None):
        if self.instate(['disabled']):return 'break'
        if self.popup is not None and not self.popup._closed:self.popup.close();return 'break'
        # cget may return a truthy Tcl_Obj whose string value is empty after
        # the first selection. Normalize before testing/evaluating the script.
        command=str(self.cget('postcommand')).strip()
        if command:self.tk.call('uplevel','#0',command)
        values=self.cget('values')
        if not values:return 'break'
        current=self.current()
        items=[dict(label=value,checked=index==current,command=lambda i=index:self.choose(i)) for index,value in enumerate(values)]
        self.popup=ChoicePopup(self,items,self.winfo_rootx(),self.winfo_rooty()+self.winfo_height()+4,
                               width=self.winfo_width(),selected=max(0,current),above=self.winfo_rooty())
        return 'break'
    def choose(self,index):
        self.current(index)
        self.event_generate('<<ComboboxSelected>>',when='tail')
    def cleanup(self,event):
        if event.widget is self and self.popup is not None and not self.popup._closed:self.popup.close()

class ThemedMenu(tk.Menu):
    """Keep Tcl's menu model/invoke/checkbutton semantics; replace its popup."""
    def __init__(self,*args,**kw):
        super().__init__(*args,**kw);self.popup=None
    def tk_popup(self,x,y,entry='',*,owner=None,min_width=190):
        from .extras import MenuPopup
        if self.index('end') is None and not str(self.cget('postcommand')).strip():return
        if self.popup is not None and not self.popup._closed:self.popup.close()
        selected=None if entry=='' else self.index(entry)
        self.popup=MenuPopup(owner or self.master,self,x,y,min_width=min_width,selected=selected)
    post=tk_popup
    def unpost(self):
        if self.popup is not None:self.popup.close()
    def grab_release(self):
        # Legacy callers use finally: menu.grab_release(). The custom popup
        # owns its own grab until selection/dismissal, and restores it itself.
        pass
    def destroy(self):
        self.unpost();super().destroy()
