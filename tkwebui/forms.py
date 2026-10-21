"""Standard-library Web form controls and result-returning dialogs."""
import calendar
from datetime import date, datetime
import math
import re
import tkinter as tk
from tkinter import ttk
from .core import PALETTE, Modal, Card, ProgressSlider, _patch
from .render import calendar_icon
from .tcl_bridge import unbind

SEMANTIC={'primary':'#087DFF','success':'#159576','warning':'#B77717','danger':'#D54B58','info':'#197FA8','neutral':'#657080'}

def tint(color,white=.91):
    return '#'+''.join(f'{round(int(color[i:i+2],16)*(1-white)+255*white):02x}' for i in (1,3,5))

def configure_form_styles(root,style):
    px=lambda n:max(1,round(n*root.winfo_fpixels('1i')/96))
    for key,base in SEMANTIC.items():
        color=PALETTE['accent'] if key=='primary' else base;prefix=key.title()
        style.configure(prefix+'.TLabel',background=PALETTE['bg'],foreground=color)
        style.configure(prefix+'.Badge.TLabel',background=tint(color),foreground=color,padding=(px(8),px(4)))
        for variant in ('','Outline.','Link.'):
            name=prefix+'.'+variant+'TButton'
            if name=='Primary.TButton':continue
            fill=color if not variant else PALETTE['bg'];border=color if variant!='Link.' else PALETTE['bg']
            normal=_patch(root,fill,border,PALETTE['bg'],px(4))
            hover=_patch(root,tint(color,.84) if variant else color,color if variant!='Link.' else tint(color,.84),PALETTE['bg'],px(4))
            disabled=_patch(root,PALETTE['sidebar'],PALETTE['border'] if variant!='Link.' else PALETTE['sidebar'],PALETTE['bg'],px(4))
            focus=_patch(root,fill,PALETTE['fg'],PALETTE['bg'],px(4))
            root._tkwebui_images.extend((normal,hover,disabled,focus))
            element='Web.'+name+'.surface'
            style.element_create(element,'image',normal,('disabled',disabled),('pressed',hover),('active',hover),('focus',focus),border=px(4)+1,padding=0,width=px(10),height=px(10),sticky='nsew')
            style.layout(name,[(element,{'sticky':'nsew','children':[('Button.padding',{'sticky':'nsew','children':[('Button.label',{'sticky':'nsew'})]})]})])
            style.configure(name,padding=(px(12),px(7)),anchor='center',foreground=color if variant else '#FFFFFF')
            style.map(name,foreground=[('disabled',PALETTE['disabled'])])

class Badge(ttk.Label):
    def __init__(self,master,*,kind='info',**kwargs):
        kwargs.setdefault('style',kind.title()+'.Badge.TLabel');super().__init__(master,**kwargs)

class ValidatedEntry(ttk.Frame):
    def __init__(self,master,*,variable=None,kind='text',required=False,minimum=None,maximum=None,pattern=None,validator=None,label='',**kwargs):
        super().__init__(master)
        self.variable=variable if variable is not None else tk.StringVar(self)
        self.kind,self.required,self.minimum,self.maximum=kind,required,minimum,maximum
        self.pattern,self.validator=pattern,validator
        self.columnconfigure(0,weight=1)
        row=0
        if label:ttk.Label(self,text=label).grid(row=0,column=0,sticky='w',pady=(0,5));row=1
        self.entry=ttk.Entry(self,textvariable=self.variable,**kwargs);self.entry.grid(row=row,column=0,sticky='ew')
        self.error=tk.StringVar(self)
        self.error_label=ttk.Label(self,textvariable=self.error,style='Danger.TLabel',wraplength=320)
        self.error_label.grid(row=row+1,column=0,sticky='w',pady=(4,0));self.error_label.grid_remove()
        self.entry.bind('<FocusOut>',lambda e:self.validate(),add='+')
        self.entry.bind('<Return>',lambda e:self.validate(),add='+')
        self._trace=self.variable.trace_add('write',self._edited)
        self.bind('<Destroy>',self._cleanup,add='+')
    def get(self):return str(self.variable.get())
    def set(self,value):self.variable.set('' if value is None else str(value))
    def get_value(self):
        text=self.get().strip()
        if not text:
            if self.required:raise ValueError('此项不能为空')
            return '' if self.kind=='text' else None
        try:
            if self.kind=='integer':value=int(text)
            elif self.kind=='float':
                value=float(text)
                if not math.isfinite(value):raise ValueError()
            elif self.kind=='date':value=date.fromisoformat(text)
            else:value=text
        except (ValueError,OverflowError) as exc:
            raise ValueError({'integer':'请输入整数','float':'请输入有限数值','date':'请输入有效日期，格式 YYYY-MM-DD'}.get(self.kind,'输入无效')) from exc
        if self.kind=='email' and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',text):raise ValueError('请输入有效的邮箱地址')
        if self.minimum is not None and value<self.minimum:raise ValueError(f'不能小于 {self.minimum}')
        if self.maximum is not None and value>self.maximum:raise ValueError(f'不能大于 {self.maximum}')
        if self.pattern and not re.fullmatch(self.pattern,text):raise ValueError('输入格式不符合要求')
        if self.validator:
            result=self.validator(value)
            if result is False:raise ValueError('输入未通过校验')
            if isinstance(result,str) and result:raise ValueError(result)
        return value
    def validate(self):
        try:self.get_value()
        except (ValueError,TypeError) as exc:
            self.error.set(str(exc));self.entry.state(['invalid']);self.error_label.grid();return False
        self.error.set('');self.entry.state(['!invalid']);self.error_label.grid_remove();return True
    def _edited(self,*_):
        if self.error.get():self.validate()
    def _cleanup(self,event):
        if event.widget is self:self.variable.trace_remove('write',self._trace)

class ResultDialog(Modal):
    def __init__(self,master,title,**kwargs):
        self.result=None;super().__init__(master,title,**kwargs)
    def accept(self,value):self.result=value;self.close()
    def show_result(self):self.wait_window();return self.result

class MessageDialog(ResultDialog):
    def __init__(self,master,message,*,title='提示',kind='info',question=False):
        super().__init__(master,title,width=440,height=260)
        Badge(self.body,text={'info':'提示','success':'完成','warning':'注意','danger':'错误'}.get(kind,'提示'),kind=kind).pack(anchor='w',pady=(0,12))
        ttk.Label(self.body,text=message,wraplength=round(380*self.scale),justify='left').pack(fill='x')
        self.primary.configure(text='确认' if question else '知道了',style=kind.title()+'.TButton',command=lambda:self.accept(True))
        if question:
            self.secondary.configure(command=lambda:self.accept(False));self.secondary.pack(side='right',padx=8)

class InputDialog(ResultDialog):
    def __init__(self,master,prompt,*,title='输入',initial='',kind='text',minimum=None,maximum=None,required=False):
        super().__init__(master,title,width=450,height=285)
        self.field=ValidatedEntry(self.body,label=prompt,kind=kind,minimum=minimum,maximum=maximum,required=required)
        self.field.pack(fill='x');self.field.set(initial)
        self.initial_focus=self.field.entry
        self.primary.configure(text='确定',command=self.submit)
        self.secondary.pack(side='right',padx=8)
        self.field.entry.bind('<Return>',lambda e:self.submit())
    def submit(self):
        if self.field.validate():self.accept(self.field.get_value())

class Dialogs:
    @staticmethod
    def info(master,message,title='提示'):return MessageDialog(master,message,title=title).show_result()
    @staticmethod
    def error(master,message,title='错误'):return MessageDialog(master,message,title=title,kind='danger').show_result()
    @staticmethod
    def warning(master,message,title='注意'):return MessageDialog(master,message,title=title,kind='warning').show_result()
    @staticmethod
    def confirm(master,message,title='确认操作',danger=False):
        return MessageDialog(master,message,title=title,kind='danger' if danger else 'info',question=True).show_result() is True
    @staticmethod
    def ask_string(master,prompt,**kwargs):return InputDialog(master,prompt,kind='text',**kwargs).show_result()
    @staticmethod
    def ask_integer(master,prompt,**kwargs):return InputDialog(master,prompt,kind='integer',**kwargs).show_result()
    @staticmethod
    def ask_float(master,prompt,**kwargs):return InputDialog(master,prompt,kind='float',**kwargs).show_result()

def _as_date(value):
    if value is None or value=='':return None
    if isinstance(value,datetime):return value.date()
    if isinstance(value,date):return value
    return date.fromisoformat(str(value))

class DateEntry(ttk.Frame):
    def __init__(self,master,*,value=None,minimum=None,maximum=None,command=None,**kwargs):
        super().__init__(master,**kwargs)
        self.minimum=_as_date(minimum);self.maximum=_as_date(maximum)
        if self.minimum and self.maximum and self.minimum>self.maximum:raise ValueError('最小日期不能大于最大日期')
        self.command=command;self.popup=None;self.variable=tk.StringVar(self)
        self.columnconfigure(0,weight=1)
        self.entry=ttk.Entry(self,textvariable=self.variable)
        self.entry.grid(row=0,column=0,sticky='ew')
        size=max(18,round(20*self.winfo_fpixels('1i')/96))
        self._calendar_icon=calendar_icon(self,size,PALETTE['muted'])
        self._calendar_disabled=calendar_icon(self,size,PALETTE['disabled'])
        self.button=ttk.Button(self,image=self._calendar_icon,command=self.open_calendar,padding=(8,5))
        self.button.grid(row=0,column=1,padx=(5,0))
        self.entry.bind('<Alt-Down>',lambda e:self.open_calendar())
        self.entry.bind('<FocusOut>',lambda e:self.validate(),add='+')
        self.entry.bind('<Return>',lambda e:self.validate(),add='+')
        self.bind('<Destroy>',self._cleanup,add='+')
        self.set_date(value)
    def get_date(self):
        value=_as_date(self.variable.get().strip())
        if value and self.minimum and value<self.minimum:raise ValueError('日期早于允许范围')
        if value and self.maximum and value>self.maximum:raise ValueError('日期晚于允许范围')
        return value
    def set_date(self,value):
        value=_as_date(value)
        if value and ((self.minimum and value<self.minimum) or (self.maximum and value>self.maximum)):raise ValueError('日期超出允许范围')
        self.variable.set(value.isoformat() if value else '');self.entry.state(['!invalid'])
    def clear(self):self.set_date(None)
    def validate(self):
        try:self.get_date()
        except ValueError:self.entry.state(['invalid']);return False
        self.entry.state(['!invalid']);return True
    def state(self,statespec=None):
        result=self.entry.state(statespec)
        if statespec is not None:
            disabled=self.entry.instate(['disabled'])
            self.button.state(['disabled'] if disabled else ['!disabled'])
            self.button.configure(image=self._calendar_disabled if disabled else self._calendar_icon)
        return result
    def open_calendar(self):
        if self.entry.instate(['disabled']):return 'break'
        if self.popup is not None and not self.popup._closed:self.popup.close();return 'break'
        self.popup=CalendarPopup(self)
        return 'break'
    def _chosen(self,value):
        self.set_date(value);self.event_generate('<<DateEntrySelected>>',when='tail')
        if self.command:self.command(value)
    def _cleanup(self,event):
        if event.widget is self and self.popup is not None and not self.popup._closed:self.popup.close(False)

class CalendarPopup(tk.Toplevel):
    def __init__(self,owner):
        self.owner=owner;self.host=owner.winfo_toplevel();self._closed=False
        existing=getattr(self.host,'_choice_popup',None)
        if existing is not None:existing.close()
        self.previous_focus=owner.focus_get();self.previous_grab=owner.grab_current()
        super().__init__(self.host);self.withdraw();self.overrideredirect(True);self.transient(self.host)
        self.scale=owner.winfo_fpixels('1i')/96;self.corner_radius=5;self._region_size=None;self._focus_job=None
        try:selected=owner.get_date()
        except ValueError:selected=None
        focused=selected or date.today()
        if owner.minimum:focused=max(focused,owner.minimum)
        if owner.maximum:focused=min(focused,owner.maximum)
        self.selected=selected;self.year=tk.IntVar(self,value=focused.year);self.month=tk.IntVar(self,value=focused.month)
        card=Card(self,padding=10);card.pack(fill='both',expand=True,padx=1,pady=1)
        head=ttk.Frame(card);head.pack(fill='x',pady=(0,10))
        ttk.Button(head,text='‹',width=2,command=lambda:self.move_month(-1)).pack(side='left')
        ttk.Spinbox(head,from_=1,to=9999,textvariable=self.year,width=5,command=self.draw).pack(side='left',padx=4)
        ttk.Label(head,text='年').pack(side='left')
        ttk.Spinbox(head,from_=1,to=12,textvariable=self.month,width=3,command=self.draw).pack(side='left',padx=4)
        ttk.Label(head,text='月').pack(side='left')
        ttk.Button(head,text='›',width=2,command=lambda:self.move_month(1)).pack(side='right')
        self.days=ttk.Frame(card);self.days.pack(fill='both',expand=True)
        foot=ttk.Frame(card);foot.pack(fill='x',pady=(10,0))
        ttk.Button(foot,text='今天',command=lambda:self.choose(date.today())).pack(side='left')
        ttk.Button(foot,text='清空',command=lambda:self.choose(None)).pack(side='right')
        self.bind('<Return>',lambda e:self.draw(),add='+');self.bind('<Escape>',lambda e:self.close())
        self.bind('<ButtonPress-1>',self.outside,add='+');self.bind('<FocusOut>',self.focus_out,add='+')
        self._host_bind=self.host.bind('<Configure>',lambda e:self.close() if e.widget is self.host else None,add='+')
        self.host._choice_popup=self
        self.draw();self.update_idletasks()
        from .extras import MenuPopup
        x=owner.winfo_rootx();y=owner.winfo_rooty()+owner.winfo_height()+4
        left,top,right,bottom=MenuPopup.work_area(x,y);w=self.winfo_reqwidth();h=self.winfo_reqheight()
        if y+h>bottom:y=owner.winfo_rooty()-h-4
        x=max(left+4,min(x,right-w-4));y=max(top+4,min(y,bottom-h-4))
        self.geometry(f'{w}x{h}{x:+d}{y:+d}')
        self.attributes('-topmost',True);self.deiconify();self.update_idletasks();Modal.round_corners(self)
        self.focus_force();self.grab_set()
    def draw(self):
        try:y=int(self.year.get());m=int(self.month.get());date(y,m,1)
        except (ValueError,tk.TclError):return
        for child in self.days.winfo_children():child.destroy()
        for col,text in enumerate('一二三四五六日'):
            ttk.Label(self.days,text=text,style='Muted.TLabel',anchor='center').grid(row=0,column=col,sticky='ew',pady=5)
            self.days.columnconfigure(col,weight=1)
        self.day_buttons={}
        weeks=calendar.Calendar().monthdayscalendar(y,m)
        for r in range(6):
            week=weeks[r] if r<len(weeks) else [0]*7
            for col,day in enumerate(week):
                if not day:
                    ttk.Label(self.days,text='',width=3).grid(row=r+1,column=col,pady=2);continue
                value=date(y,m,day);style='Primary.TButton' if value==self.selected else 'Quiet.TButton'
                button=ttk.Button(self.days,text=str(day),width=3,style=style,command=lambda d=value:self.choose(d))
                if (self.owner.minimum and value<self.owner.minimum) or (self.owner.maximum and value>self.owner.maximum):button.state(['disabled'])
                button.grid(row=r+1,column=col,padx=1,pady=2);self.day_buttons[value]=button
    def move_month(self,delta):
        try:index=(int(self.year.get())-1)*12+int(self.month.get())-1+delta
        except (ValueError,tk.TclError):return
        index=max(0,min(9999*12-1,index));self.year.set(index//12+1);self.month.set(index%12+1);self.draw()
    def choose(self,value):
        if value and ((self.owner.minimum and value<self.owner.minimum) or (self.owner.maximum and value>self.owner.maximum)):return
        self.close();self.owner._chosen(value)
    def outside(self,event):
        if not(self.winfo_rootx()<=event.x_root<self.winfo_rootx()+self.winfo_width() and self.winfo_rooty()<=event.y_root<self.winfo_rooty()+self.winfo_height()):self.close()
    def focus_out(self,event):
        if self._focus_job is None and not self._closed:self._focus_job=self.after(100,self.check_focus)
    def check_focus(self):
        self._focus_job=None
        if self._closed:return
        focus=self.focus_get()
        if focus is None or focus.winfo_toplevel() is not self:self.close(False)
    def close(self,restore_focus=True):
        if self._closed:return
        self._closed=True
        if self._focus_job is not None:self.after_cancel(self._focus_job)
        unbind(self.host,'<Configure>',self._host_bind)
        if getattr(self.host,'_choice_popup',None) is self:self.host._choice_popup=None
        self.grab_release();super().destroy()
        if self.previous_grab is not None and self.previous_grab.winfo_exists():self.previous_grab.grab_set()
        if restore_focus:
            focus=self.previous_focus
            if focus is not None and focus.winfo_exists() and focus.winfo_viewable():focus.focus_force()
    def destroy(self):self.close(False)

class ValueSlider(ttk.Frame):
    def __init__(self,master,*,variable=None,from_=0,to=100,step=1,unit='',command=None,**kwargs):
        super().__init__(master,**kwargs)
        if to<=from_ or step<=0:raise ValueError('需要 to > from_ 且 step > 0')
        self.minimum,self.maximum,self.step=from_,to,step;self.unit=unit;self.command=command;self._busy=False
        self.variable=variable if variable is not None else tk.DoubleVar(self,value=from_)
        self.number=tk.StringVar(self)
        self.columnconfigure(0,weight=1)
        self.slider=ProgressSlider(self,from_=from_,to=to,step=step,variable=self.variable);self.slider.grid(row=0,column=0,sticky='ew',padx=(0,8))
        self.spin=ttk.Spinbox(self,from_=from_,to=to,increment=step,textvariable=self.number,width=7,command=self.commit)
        self.spin.grid(row=0,column=1)
        ttk.Label(self,text=unit,style='Muted.TLabel').grid(row=0,column=2,padx=(5,0))
        self.spin.bind('<Return>',lambda e:self.commit());self.spin.bind('<FocusOut>',lambda e:self.commit())
        self._trace=self.variable.trace_add('write',self._sync);self._sync()
        self.bind('<Destroy>',self._cleanup,add='+')
    def get(self):return float(self.variable.get())
    def set(self,value):
        value=float(value)
        if not math.isfinite(value):raise ValueError('数值必须有限')
        value=max(self.minimum,min(self.maximum,self.minimum+round((value-self.minimum)/self.step)*self.step))
        self.variable.set(round(value,10))
    def commit(self):
        try:self.set(float(self.number.get()));self.spin.state(['!invalid'])
        except ValueError:self.spin.state(['invalid'])
    def _sync(self,*_):
        if self._busy:return
        self._busy=True
        try:
            try:value=self.get()
            except (ValueError,tk.TclError):value=self.minimum
            if not math.isfinite(value):value=self.minimum
            value=max(self.minimum,min(self.maximum,self.minimum+round((value-self.minimum)/self.step)*self.step))
            self.variable.set(round(value,10));self.number.set(f'{value:g}');self.spin.state(['!invalid'])
        finally:self._busy=False
        if self.command:self.command(self.get())
    def state(self,statespec=None):
        result=self.spin.state(statespec)
        if statespec is not None:
            disabled=self.spin.instate(['disabled'])
            self.slider.configure(state='disabled' if disabled else 'normal')
            self.slider.itemconfigure(self.slider.fill,fill=PALETTE['disabled'] if disabled else PALETTE['accent'])
        return result
    def _cleanup(self,event):
        if event.widget is self:self.variable.trace_remove('write',self._trace)
