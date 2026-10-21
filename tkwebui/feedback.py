"""Nonblocking toasts, text progress and radial meters, all native Tk."""
import math
import tkinter as tk
from tkinter import ttk
from .core import PALETTE, Card, Modal
from .forms import SEMANTIC, Badge
from .render import SmoothImage
from .tcl_bridge import unbind

class ToastNotification(tk.Toplevel):
    def __init__(self,master,message,*,title='',kind='info',duration=3000,position='bottom-right'):
        self.host=master.winfo_toplevel();self.kind=kind;self.duration=duration;self.position=position
        self._closed=False;self._timer=None;self._shown=False;self._region_size=None
        self.scale=master.winfo_fpixels('1i')/96;self.corner_radius=5
        super().__init__(self.host);self.withdraw();self.overrideredirect(True);self.transient(self.host)
        self.configure(background=PALETTE['bg'])
        body=Card(self,padding=14,border_color=SEMANTIC.get(kind,SEMANTIC['info']));body.pack(fill='both',expand=True,padx=1,pady=1)
        head=ttk.Frame(body);head.pack(fill='x')
        Badge(head,text=title or {'success':'已完成','danger':'操作失败','warning':'请注意','info':'提示'}.get(kind,'提示'),kind=kind).pack(side='left')
        ttk.Button(head,text='×',width=2,style='Quiet.TButton',command=self.hide).pack(side='right')
        ttk.Label(body,text=message,wraplength=round(280*self.scale),justify='left').pack(fill='x',pady=(10,0))
        self.bind('<Enter>',self._pause,add='+');self.bind('<Leave>',self._resume,add='+')
        self._configure_bind=self.host.bind('<Configure>',self._host_configure,add='+')
        self._unmap_bind=self.host.bind('<Unmap>',lambda e:self.hide() if e.widget is self.host else None,add='+')
        self._destroy_bind=self.host.bind('<Destroy>',lambda e:self.hide() if e.widget is self.host else None,add='+')
    def show_toast(self):
        if self._closed:return self
        self.update_idletasks()
        if not self._shown:
            stack=getattr(self.host,'_web_toasts',None)
            if stack is None:stack=self.host._web_toasts=[]
            same=[toast for toast in stack if toast.position==self.position]
            gap=round(10*self.scale)
            while same and (len(same)>=3 or sum(toast.winfo_reqheight()+gap for toast in same)+self.winfo_reqheight()+2*gap>self.host.winfo_height()):
                same.pop(0).hide()
            stack.append(self);self._shown=True
        self.update_idletasks();self.deiconify();self.reflow();self.update_idletasks();Modal.round_corners(self)
        self._resume();return self
    def _host_configure(self,event):
        if event.widget is self.host:self.reflow()
    def reflow(self):
        if self._closed:return
        gap=round(10*self.scale);offset=gap
        for toast in list(getattr(self.host,'_web_toasts',[])):
            if toast._closed or toast.position!=self.position:continue
            w=toast.winfo_reqwidth();h=toast.winfo_reqheight()
            x=self.host.winfo_rootx()+max(gap,self.host.winfo_width()-w-gap)
            if self.position=='top-right':y=self.host.winfo_rooty()+offset
            else:y=self.host.winfo_rooty()+max(gap,self.host.winfo_height()-offset-h)
            toast.geometry(f'{w}x{h}{x:+d}{y:+d}');offset+=h+gap
    def _pause(self,event=None):
        if self._timer is not None:self.after_cancel(self._timer);self._timer=None
    def _resume(self,event=None):
        if self._closed:return
        self._pause()
        if self.duration>0:self._timer=self.after(self.duration,self.hide)
    def hide(self):
        if self._closed:return
        self._closed=True;self._pause()
        stack=getattr(self.host,'_web_toasts',[])
        if self in stack:stack.remove(self)
        for event,binding in [('<Configure>',self._configure_bind),('<Unmap>',self._unmap_bind),('<Destroy>',self._destroy_bind)]:
            try:unbind(self.host,event,binding)
            except tk.TclError:pass
        super().destroy()
        for toast in list(stack):toast.reflow()
    def destroy(self):self.hide()

def notify(master,message,**kwargs):return ToastNotification(master,message,**kwargs).show_toast()

class TextProgress(ttk.Frame):
    def __init__(self,master,*,variable=None,value=0,maximum=100,mask='{value:.0f}%',text='',orient='horizontal',mode='determinate',kind='primary',length=240,thickness=28,**kwargs):
        super().__init__(master,**kwargs)
        if maximum<=0 or orient not in ('horizontal','vertical'):raise ValueError('进度范围或方向无效')
        self.variable=variable if variable is not None else tk.DoubleVar(self,value=value)
        self.maximum,self.mask,self.text,self.orient,self.mode,self.kind=maximum,mask,text,orient,mode,kind
        self._timer=None;self._phase=0;self._closed=False
        self.dpi=self.winfo_fpixels('1i')/96;self.px=lambda n:max(1,round(n*self.dpi))
        w,h=(self.px(length),self.px(thickness)) if orient=='horizontal' else (self.px(thickness),self.px(length))
        self.canvas=tk.Canvas(self,width=w,height=h,background=PALETTE['bg'],highlightthickness=0)
        self.canvas.pack(fill='both',expand=True)
        self.canvas.bind('<Configure>',lambda e:self.draw())
        self._trace=self.variable.trace_add('write',lambda *_:self.draw());self.bind('<Destroy>',self._cleanup,add='+')
        self.draw()
    def get(self):return float(self.variable.get())
    def set(self,value):
        value=float(value)
        if not math.isfinite(value):raise ValueError('进度必须是有限数值')
        self.variable.set(max(0,min(self.maximum,value)))
    def step(self,amount=1):self.set(self.get()+amount)
    def draw(self):
        if self._closed:return
        c=self.canvas;c.delete('all');w=c.winfo_width();h=c.winfo_height()
        if w<2 or h<2:return
        color=PALETTE['accent'] if self.kind=='primary' else SEMANTIC.get(self.kind,PALETTE['accent'])
        ratio=max(0,min(1,self.get()/self.maximum))
        c.create_rectangle(0,0,w,h,fill=PALETTE['hover'],outline='')
        horizontal=self.orient=='horizontal'
        if self.mode=='indeterminate':a=self._phase*.75;b=a+.25
        else:a=0;b=ratio
        if horizontal:c.create_rectangle(w*a,0,w*b,h,fill=color,outline='')
        else:c.create_rectangle(0,h*(1-b),w,h*(1-a),fill=color,outline='')
        caption=self.text or self.mask.format(value=self.get(),maximum=self.maximum,percent=ratio*100)
        foreground='#FFFFFF' if a<=.5<=b else PALETTE['fg']
        c.create_text(w/2,h/2,text=caption,fill=foreground,font='TkDefaultFont',angle=0 if horizontal else 90)
    def start(self,interval=35):
        if self._timer is not None:return
        self._interval=max(15,interval);self._tick()
    def _tick(self):
        if self._closed:return
        if self.mode=='indeterminate':self._phase=(self._phase+.035)%1;self.draw()
        else:self.set((self.get()+1)%(self.maximum+1))
        self._timer=self.after(self._interval,self._tick)
    def stop(self):
        if self._timer is not None:self.after_cancel(self._timer);self._timer=None
    def _cleanup(self,event):
        if event.widget is self:
            self._closed=True;self.stop();self.variable.trace_remove('write',self._trace)

class Meter(ttk.Frame):
    def __init__(self,master,*,variable=None,value=0,minimum=0,maximum=100,meter_type='full',unit='%',subtext='',interactive=False,thresholds=None,command=None,size=190,**kwargs):
        super().__init__(master,**kwargs)
        if maximum<=minimum or meter_type not in ('full','semi'):raise ValueError('仪表量程或类型无效')
        self.minimum,self.maximum,self.meter_type=minimum,maximum,meter_type
        self.unit,self.subtext,self.interactive,self.thresholds,self.command=unit,subtext,interactive,thresholds or [],command
        self.variable=variable if variable is not None else tk.DoubleVar(self,value=value)
        self.dpi=self.winfo_fpixels('1i')/96;self.px=lambda n:max(1,round(n*self.dpi))
        self._closed=False;self._geometry=None;self._meter_image=None;self._draw_job=None
        self.canvas=tk.Canvas(self,width=self.px(size),height=self.px(size if meter_type=='full' else size*.72),background=PALETTE['bg'],highlightthickness=0,takefocus=interactive)
        self.canvas.pack(fill='both',expand=True)
        self.canvas.bind('<Configure>',lambda e:self.schedule())
        if interactive:
            self.canvas.configure(cursor='hand2');self.canvas.bind('<Button-1>',self._pointer);self.canvas.bind('<B1-Motion>',self._pointer)
            for event,delta in [('<Left>',-1),('<Down>',-1),('<Right>',1),('<Up>',1)]:self.canvas.bind(event,lambda e,d=delta:self.set(self.get()+d))
            self.canvas.bind('<Home>',lambda e:self.set(self.minimum));self.canvas.bind('<End>',lambda e:self.set(self.maximum))
        self._trace=self.variable.trace_add('write',lambda *_:self.schedule());self.bind('<Destroy>',self._cleanup,add='+')
        self.draw()
    def schedule(self):
        if not self._closed and self._draw_job is None:self._draw_job=self.after(16,self.draw)
    def get(self):return float(self.variable.get())
    def set(self,value):
        value=float(value)
        if not math.isfinite(value):raise ValueError('仪表数值必须有限')
        self.variable.set(max(self.minimum,min(self.maximum,value)))
        self.event_generate('<<MeterChanged>>',when='tail')
        if self.command:self.command(self.get())
        return 'break'
    def draw(self):
        if self._draw_job is not None:self.after_cancel(self._draw_job);self._draw_job=None
        if self._closed:return
        c=self.canvas;c.delete('all');w=c.winfo_width();h=c.winfo_height()
        if w<5 or h<5:return
        full=self.meter_type=='full';width=self.px(12)
        radius=max(1,min(w/2-self.px(14),h/2-self.px(12) if full else h-self.px(42)))
        cx=w/2;cy=h/2 if full else radius+self.px(10)
        self._geometry=(cx,cy,radius)
        bounds=(cx-radius,cy-radius,cx+radius,cy+radius)
        ratio=max(0,min(1,(self.get()-self.minimum)/(self.maximum-self.minimum)))
        color=PALETTE['accent']
        for limit,kind in sorted(self.thresholds):
            if ratio*100<=limit:color=SEMANTIC.get(kind,kind);break
        with SmoothImage(self,w,h) as surface:
            surface.arc(bounds,270 if full else 180,360 if full else 180,PALETTE['hover'],width)
            surface.arc(bounds,270 if full else 180,ratio*(360 if full else 180),color,width)
            self._meter_image=surface.photo()
        c.create_image(0,0,image=self._meter_image,anchor='nw')
        c.create_text(cx,cy-self.px(9),text=f'{self.get():g}{self.unit}',fill=PALETTE['fg'],font=('Microsoft YaHei UI',17,'bold'))
        c.create_text(cx,cy+self.px(19),text=self.subtext,fill=PALETTE['muted'],font='TkDefaultFont')
    def _pointer(self,event):
        if self._geometry is None:return
        self.canvas.focus_set();cx,cy,r=self._geometry
        angle=math.degrees(math.atan2(cy-event.y,event.x-cx))
        if self.meter_type=='full':ratio=((90-angle)%360)/360
        else:ratio=max(0,min(1,(180-angle)/180)) if angle>=0 else (1 if event.x>=cx else 0)
        return self.set(round(self.minimum+ratio*(self.maximum-self.minimum),1))
    def _cleanup(self,event):
        if event.widget is self:
            self._closed=True;self.variable.trace_remove('write',self._trace)
            if self._draw_job is not None:self.after_cancel(self._draw_job);self._draw_job=None
