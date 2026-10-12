"""Interactive Canvas charts for small Tkinter tools. No third-party dependencies.

LineChart, ColumnChart, ScatterChart, DonutChart and PieChart accept Python lists.
Hover changes only overlay items. Data, view and resize redraws are coalesced.
"""
from __future__ import annotations
import bisect
import copy
import math
import tkinter as tk
from tkinter import ttk, font as tkfont
from .core import PALETTE
from .render import SmoothImage

COLORS = ('#087DFF', '#19A58B', '#E9A13B', '#8B68D9', '#DC708E', '#269DB2')


def _number(value):
    if value is None:return None
    try:value=float(value)
    except (TypeError,ValueError) as error:raise ValueError(f'图表需要数值，收到 {value!r}') from error
    return value if math.isfinite(value) else None


def _format(value):
    if value==0:return '0'
    if abs(value)>=1e6 or abs(value)<.001:return f'{value:.3g}'
    return f'{value:,.3f}'.rstrip('0').rstrip('.') if value!=int(value) else f'{value:,.0f}'


def _ticks(low,high,count=5):
    raw=(high-low)/max(1,count-1)
    if not math.isfinite(raw) or raw<=0:return [low]
    power=10**math.floor(math.log10(raw))
    step=next((n*power for n in (1,2,2.5,5,10) if n*power>=raw),10*power)
    first=math.ceil(low/step)*step
    return [0.0 if abs(first+i*step)<step*1e-9 else first+i*step
            for i in range(min(20,max(0,int((high-first)/step)+1)))]


def _clip_segment(x1,y1,x2,y2,rect):
    left,top,right,bottom=rect;dx=x2-x1;dy=y2-y1;start,end=0.,1.
    for p,q in ((-dx,x1-left),(dx,right-x1),(-dy,y1-top),(dy,bottom-y1)):
        if p==0:
            if q<0:return None
        else:
            value=q/p
            if p<0:start=max(start,value)
            else:end=min(end,value)
            if start>end:return None
    return x1+start*dx,y1+start*dy,x1+end*dx,y1+end*dy


class _Chart(ttk.Frame):
    def __init__(self,master,*,height=230,on_click=None,tooltip_formatter=None,**kwargs):
        super().__init__(master,**kwargs)
        self.scale=self.winfo_fpixels('1i')/96;self.px=lambda value:max(1,round(value*self.scale))
        self.on_click=on_click;self.tooltip_formatter=tooltip_formatter
        self.last_selection=None;self.hidden=set();self._closed=False
        self._draw_job=None;self._hover_job=None;self._pointer=None;self._hover=None
        self._highlighted=None;self._drag_start=None;self._previous_grab=None
        self._aa_photo=None;self._marker_images={}
        self.font=tkfont.Font(self,font='TkDefaultFont');self.font.configure(size=max(8,int(self.font.cget('size'))-1))
        self.toolbar=ttk.Frame(self);self.toolbar.pack(fill='x',pady=(0,self.px(4)))
        self.legend=ttk.Frame(self.toolbar);self.legend.pack(side='left',fill='x',expand=True)
        self.legend.bind('<Configure>',self._layout_legend)
        self._legend_labels=[]
        self.canvas=tk.Canvas(self,height=self.px(height),width=self.px(240),background=PALETTE['bg'],
                              highlightthickness=0,borderwidth=0,takefocus=True)
        self.canvas.pack(fill='both',expand=True)
        self.canvas.bind('<Configure>',lambda e:self.schedule())
        self.canvas.bind('<Motion>',self._motion)
        self.canvas.bind('<Leave>',lambda e:self._clear_hover())
        self.canvas.bind('<ButtonPress-1>',self._press)
        self.canvas.bind('<ButtonRelease-1>',self._release)
        self.canvas.bind('<B1-Motion>',self._drag)
        self.bind('<Destroy>',self._cleanup,add='+')

    def _set_legend(self,items):
        for label in self._legend_labels:label.destroy()
        self._legend_labels=[]
        for name,color in items:
            label=tk.Label(self.legend,text='●  '+name,font=self.font,padx=self.px(5),pady=self.px(3),
                           background=PALETTE['bg'],foreground=PALETTE['muted'] if name in self.hidden else color,
                           cursor='hand2',takefocus=True,highlightthickness=1,
                           highlightbackground=PALETTE['bg'],highlightcolor=PALETTE['blue'])
            label._series_name=name;label._series_color=color
            label.bind('<Button-1>',lambda e,n=name:self.toggle_series(n))
            label.bind('<space>',lambda e,n=name:self.toggle_series(n))
            label.bind('<Return>',lambda e,n=name:self.toggle_series(n))
            self._legend_labels.append(label)
        self._layout_legend()
    def _layout_legend(self,event=None):
        available=max(self.px(120),self.legend.winfo_width());row=col=used=0
        for label in self._legend_labels:
            width=label.winfo_reqwidth()+self.px(4)
            if used and used+width>available:row+=1;col=used=0
            label.grid(row=row,column=col,sticky='w',padx=(0,self.px(4)))
            col+=1;used+=width
    def toggle_series(self,name):
        if name not in {label._series_name for label in self._legend_labels}:raise KeyError(name)
        if name in self.hidden:self.hidden.remove(name)
        else:self.hidden.add(name)
        for label in self._legend_labels:
            label.configure(foreground=PALETTE['disabled'] if label._series_name in self.hidden else label._series_color)
        self.schedule();self.event_generate('<<ChartSeriesChanged>>',when='tail')
        return 'break'
    def schedule(self):
        if not self._closed and self._draw_job is None:self._draw_job=self.after(16,self._redraw)
    def redraw(self):
        if self._draw_job is not None:self.after_cancel(self._draw_job);self._draw_job=None
        self._redraw()
    def _redraw(self):
        self._draw_job=None
        if self._closed:return
        self._clear_hover();self.canvas.delete('plot')
        self._draw()
    def _motion(self,event):
        self._pointer=(event.x,event.y)
        if self._hover_job is None:self._hover_job=self.after(16,self._update_hover)
    def _update_hover(self):
        self._hover_job=None
        if self._closed or self._pointer is None:return
        x,y=self._pointer;hit=self._hit(x,y)
        if hit is None:self._clear_hover();return
        self._clear_hover(cancel_job=False)
        self._hover=hit
        self._draw_highlight(hit)
        if self.tooltip_formatter:text=str(self.tooltip_formatter(dict(hit['data'])))
        else:text=self._tooltip_text(hit['data'])
        # Keep the tooltip in this canvas; no Toplevel, images or global grab.
        text_item=self.canvas.create_text(0,0,text=text,font=self.font,anchor='nw',fill=PALETTE['fg'],
                                           width=max(self.px(60),self.canvas.winfo_width()-self.px(36)),tags='overlay')
        bounds=self.canvas.bbox(text_item)
        pad=self.px(8);width=bounds[2]-bounds[0]+2*pad;height=bounds[3]-bounds[1]+2*pad
        left=max(2,min(x+self.px(14),self.canvas.winfo_width()-width-2))
        top=max(2,min(y+self.px(16),self.canvas.winfo_height()-height-2))
        box=self.canvas.create_rectangle(left,top,left+width,top+height,fill=PALETTE['bg'],outline='#CCD1DC',tags='overlay')
        self.canvas.coords(text_item,left+pad,top+pad);self.canvas.tag_raise(text_item,box)
    def _clear_hover(self,cancel_job=True):
        if cancel_job and self._hover_job is not None:self.after_cancel(self._hover_job);self._hover_job=None
        if self._highlighted is not None:
            item,color=self._highlighted;self.canvas.itemconfigure(item,fill=color);self._highlighted=None
        self.canvas.delete('overlay');self._hover=None
    def _draw_highlight(self,hit):
        if 'item' in hit:
            item=hit['item'];self._highlighted=(item,hit['color'])
            channels=self.winfo_rgb(hit['color'])
            color='#'+''.join(f'{round(v/257*.84):02x}' for v in channels)
            self.canvas.itemconfigure(item,fill=color)
    def _tooltip_text(self,data):return str(data)
    def _press(self,event):
        self.canvas.focus_set();self._press_position=(event.x,event.y)
    def _drag(self,event):pass
    def _release(self,event):
        hit=self._hit(event.x,event.y)
        if hit is not None:self._select_hit(hit)
    def _select_hit(self,hit):
        self.last_selection=dict(hit['data'])
        if self.on_click:self.on_click(dict(self.last_selection))
        self.event_generate('<<ChartSelected>>',when='tail')
    def _empty(self,text='暂无数据'):
        self.canvas.create_text(self.canvas.winfo_width()/2,self.canvas.winfo_height()/2,
                                text=text,font=self.font,fill=PALETTE['muted'],tags='plot')
    def _cleanup(self,event):
        if event.widget is not self:return
        self._closed=True
        for job in (self._draw_job,self._hover_job):
            if job is not None:self.after_cancel(job)
        try:
            if self._previous_grab is not None and self._previous_grab.winfo_exists():self._previous_grab.grab_set()
        except tk.TclError:pass


class _CartesianChart(_Chart):
    kind='line'
    def __init__(self,master,*,series=None,values=None,labels=None,height=230,y_formatter=None,x_formatter=None,**kwargs):
        super().__init__(master,height=height,**kwargs)
        self.y_formatter=y_formatter or _format;self.x_formatter=x_formatter or _format
        self.series=[];self.labels=[];self._view=None;self._plot=None
        self._hits=[];self._line_index=[];self._buckets={};self._full_bounds=(0.,1.,0.,1.)
        if self.kind!='bar':
            ttk.Button(self.toolbar,text='重置',style='Quiet.TButton',command=self.reset_view).pack(side='right')
            self.canvas.bind('<MouseWheel>',self._wheel)
            self.canvas.bind('<Double-Button-1>',lambda e:self.reset_view())
            self.canvas.bind('<Escape>',lambda e:self.reset_view())
        self.set_data(series=series,values=values,labels=labels)

    def set_data(self,series=None,*,values=None,labels=None,reset_view=True):
        if series is not None and values is not None:raise ValueError('请只传 series 或 values 其中之一')
        if series is None:series=[{'name':'数据','values':list(values or [])}]
        parsed=[];names=set()
        for index,item in enumerate(series):
            name=str(item.get('name',f'系列 {index+1}'))
            if name in names:raise ValueError('系列名称不能重复：'+name)
            names.add(name)
            color=item.get('color',PALETTE['accent'] if index==0 else COLORS[index%len(COLORS)])
            self.winfo_rgb(color)
            if 'points' in item:
                if self.kind=='bar':raise ValueError('柱状图使用 values 和 labels，而不是 points')
                points=[]
                for point in item['points']:
                    if point is None:points.append(None);continue
                    if len(point)!=2:raise ValueError('points 中每个点都应是 (x, y)')
                    x,y=map(_number,point);points.append(None if x is None or y is None else (x,y))
            else:points=[None if (y:=_number(value)) is None else (float(i),y) for i,value in enumerate(item.get('values',[]))]
            parsed.append({'name':name,'color':color,'points':points})
        self.series=parsed
        if labels is not None:self.labels=[str(value) for value in labels]
        self.hidden.intersection_update(names)
        if reset_view:self._view=None
        self._set_legend([(item['name'],item['color']) for item in self.series])
        self.schedule()
    def get_data(self):
        if self.kind=='bar':
            return [{'name':series['name'],'color':series['color'],
                     'values':[point[1] if point is not None else None for point in series['points']]} for series in self.series]
        return copy.deepcopy(self.series)
    def _bounds(self):
        points=[point for series in self.series if series['name'] not in self.hidden for point in series['points'] if point is not None]
        if not points:return None
        xs,ys=zip(*points);xmin,xmax=min(xs),max(xs);ymin,ymax=min(ys),max(ys)
        if self.kind=='bar':
            xmin=-.5;xmax=max(len(series['points']) for series in self.series)-.5
            ymin=min(0,ymin);ymax=max(0,ymax)
        else:
            xpad=(xmax-xmin)*.03 if xmax>xmin else max(1,abs(xmin)*.1)
            xmin-=xpad;xmax+=xpad
        ypad=(ymax-ymin)*.08 if ymax>ymin else max(1,abs(ymin)*.1)
        return xmin,xmax,ymin-ypad,ymax+ypad
    def _draw(self):
        self._hits=[];self._line_index=[];self._buckets={}
        bounds=self._bounds()
        if bounds is None:
            self._plot=None;self._empty('点击图例显示数据' if self.hidden else '暂无数据');return
        self._full_bounds=bounds
        if self._view is None:view=bounds
        else:view=self._clamp_view(self._view);self._view=view
        self._draw_bounds=view
        xmin,xmax,ymin,ymax=view
        yticks=_ticks(ymin,ymax)
        left=max(self.px(42),max((self.font.measure(str(self.y_formatter(y))) for y in yticks),default=0)+self.px(10))
        right=self.canvas.winfo_width()-self.px(12);top=self.px(12);bottom=self.canvas.winfo_height()-self.px(32)
        if right-left<self.px(35) or bottom-top<self.px(35):self._plot=None;return
        self._plot=(left,top,right,bottom)
        for y in yticks:
            sy=self._xy(xmin,y)[1]
            self.canvas.create_line(left,sy,right,sy,fill=PALETTE['border'],dash=(2,4),tags='plot')
            self.canvas.create_text(left-self.px(8),sy,text=self.y_formatter(y),anchor='e',font=self.font,fill=PALETTE['muted'],tags='plot')
        if self.labels:
            first=max(0,math.ceil(xmin));last=min(len(self.labels)-1,math.floor(xmax))
            capacity=max(1,int((right-left)/self.px(64)));step=max(1,math.ceil((last-first+1)/capacity))
            xticks=list(range(first,last+1,step))
        else:xticks=_ticks(xmin,xmax,max(2,int((right-left)/self.px(80))))
        for x in xticks:
            sx=self._xy(x,ymin)[0]
            label=self.labels[int(x)] if self.labels and int(x)==x and 0<=int(x)<len(self.labels) else str(self.x_formatter(x))
            while self.font.measure(label)>self.px(85) and len(label)>3:label=label[:-2]+'…'
            self.canvas.create_text(sx,bottom+self.px(16),text=label,font=self.font,fill=PALETTE['muted'],tags='plot')
        self.canvas.create_line(left,bottom,right,bottom,fill=PALETTE['border'],tags='plot')
        if ymin<0<ymax:
            sy=self._xy(xmin,0)[1];self.canvas.create_line(left,sy,right,sy,fill='#BFC7D3',tags='plot')
        visible=[item for item in self.series if item['name'] not in self.hidden]
        if self.kind=='bar':
            for series_index,series in enumerate(visible):self._draw_bars(series,series_index,len(visible))
        else:
            with SmoothImage(self,self.canvas.winfo_width(),self.canvas.winfo_height()) as surface:
                self._smooth=surface
                for series in visible:self._draw_points(series)
                self._aa_photo=surface.photo()
            self._smooth=None
            self.canvas.create_image(0,0,image=self._aa_photo,anchor='nw',tags='plot')
    def _xy(self,x,y):
        left,top,right,bottom=self._plot;xmin,xmax,ymin,ymax=self._draw_bounds
        return left+(x-xmin)/(xmax-xmin)*(right-left),bottom-(y-ymin)/(ymax-ymin)*(bottom-top)
    def _data_at(self,x,y):
        left,top,right,bottom=self._plot;xmin,xmax,ymin,ymax=self._draw_bounds
        return xmin+(x-left)/(right-left)*(xmax-xmin),ymax-(y-top)/(bottom-top)*(ymax-ymin)
    def _payload(self,series,index,point):
        x,y=point
        label=self.labels[int(x)] if int(x)==x and 0<=int(x)<len(self.labels) else str(self.x_formatter(x))
        return {'series':series['name'],'index':index,'x':x,'y':y,'label':label,'kind':self.kind}
    def _draw_points(self,series):
        color=series['color'];last=None;path=[];lookup=[]
        left,top,right,bottom=self._plot
        show_markers=self.kind=='scatter' or len(series['points'])<=60
        def flush():
            if len(path)>=4:self._smooth.line(path,color,width=self.px(2))
            path.clear()
        for index,point in enumerate(series['points']):
            if point is None:flush();last=None;continue
            x,y=self._xy(*point)
            if self.kind=='line' and last is not None:
                clipped=_clip_segment(*last,x,y,self._plot)
                if clipped:
                    if path and (abs(path[-2]-clipped[0])>1e-6 or abs(path[-1]-clipped[1])>1e-6):flush()
                    if not path:path.extend(clipped[:2])
                    path.extend(clipped[2:])
                else:flush()
            last=(x,y)
            if not (left<=x<=right and top<=y<=bottom):continue
            hit={'x':x,'y':y,'color':color,'data':self._payload(series,index,point)}
            lookup.append(hit)
            if show_markers:
                radius=self.px(3 if self.kind=='line' else 3.5)
                self._smooth.ellipse((x-radius,y-radius,x+radius,y+radius),fill=color,outline=PALETTE['bg'],width=1)
            if self.kind=='scatter':
                key=(int(x//self.px(24)),int(y//self.px(24)))
                self._buckets.setdefault(key,[]).append(hit)
        flush()
        lookup.sort(key=lambda hit:hit['x'])
        self._line_index.append(([hit['x'] for hit in lookup],lookup))
    def _draw_bars(self,series,index,count):
        left,top,right,bottom=self._plot
        zero=self._xy(0,0)[1];slot=(right-left)/(self._draw_bounds[1]-self._draw_bounds[0])
        group_width=slot*.72;bar_width=max(1,group_width/count-self.px(2))
        for i,point in enumerate(series['points']):
            if point is None:continue
            x,y=self._xy(*point);x=x-group_width/2+index*group_width/count
            y1=max(top,min(y,zero));y2=min(bottom,max(y,zero))
            if y2-y1<1:y2=y1+1
            item=self.canvas.create_rectangle(x,y1,x+bar_width,y2,fill=series['color'],outline='',tags='plot')
            self._hits.append({'bbox':(x,y1,x+bar_width,y2),'x':x+bar_width/2,'y':y,
                               'item':item,'color':series['color'],'data':self._payload(series,i,point)})
    def _inside(self,x,y):
        return self._plot is not None and self._plot[0]<=x<=self._plot[2] and self._plot[1]<=y<=self._plot[3]
    def _hit(self,x,y):
        if not self._inside(x,y):return None
        if self.kind=='bar':
            return next((hit for hit in self._hits if hit['bbox'][0]<=x<=hit['bbox'][2] and hit['bbox'][1]-2<=y<=hit['bbox'][3]+2),None)
        if self.kind=='scatter':
            col,row=int(x//self.px(24)),int(y//self.px(24))
            hits=[hit for dx in (-1,0,1) for dy in (-1,0,1) for hit in self._buckets.get((col+dx,row+dy),[])]
            hit=min(hits,key=lambda h:(h['x']-x)**2+(h['y']-y)**2,default=None)
            return hit if hit and math.hypot(hit['x']-x,hit['y']-y)<=self.px(14) else None
        candidates=[]
        for xs,hits in self._line_index:
            index=bisect.bisect_left(xs,x)
            candidates.extend(hits[i] for i in (index-1,index) if 0<=i<len(hits))
        return min(candidates,key=lambda h:(abs(h['x']-x),abs(h['y']-y)),default=None)
    def _draw_highlight(self,hit):
        if self.kind=='bar':super()._draw_highlight(hit);return
        left,top,right,bottom=self._plot;x,y=hit['x'],hit['y'];radius=self.px(5)
        self.canvas.create_line(x,top,x,bottom,fill='#A9B4C4',dash=(3,3),tags='overlay')
        self.canvas.create_line(left,y,right,y,fill='#CDD3DE',dash=(3,3),tags='overlay')
        key=(hit['color'],radius)
        if key not in self._marker_images:
            size=2*radius+self.px(6);center=size/2
            with SmoothImage(self,size,size) as surface:
                surface.ellipse((center-radius,center-radius,center+radius,center+radius),fill=PALETTE['bg'],outline=hit['color'],width=self.px(2))
                self._marker_images[key]=surface.photo()
        self.canvas.create_image(x,y,image=self._marker_images[key],tags='overlay')
    def _tooltip_text(self,data):
        return f"{data['series']}\n{data['label']}  ·  {self.y_formatter(data['y'])}"
    def reset_view(self):
        self._view=None;self.schedule();self.event_generate('<<ChartViewChanged>>',when='tail');return 'break'
    def _clamp_view(self,view):
        full=self._full_bounds;result=[]
        for low,high,base_low,base_high in ((view[0],view[1],full[0],full[1]),(view[2],view[3],full[2],full[3])):
            span=min(high-low,base_high-base_low)
            low=max(base_low,min(low,base_high-span));result.extend((low,low+span))
        return tuple(result)
    def _wheel(self,event):
        if not self._inside(event.x,event.y) or not event.delta:return
        old=self._view or self._full_bounds;center=self._data_at(event.x,event.y)
        factor=.82 if event.delta>0 else 1/.82
        # Lines zoom horizontally by default; Shift zooms y. Scatter zooms both.
        axes=(False,True) if event.state&1 else ((True,True) if self.kind=='scatter' else (True,False))
        new=[]
        for axis,(low,high) in enumerate(((old[0],old[1]),(old[2],old[3]))):
            if axes[axis]:
                span=(high-low)*factor;fullspan=self._full_bounds[axis*2+1]-self._full_bounds[axis*2]
                span=max(fullspan/10000,min(span,fullspan));ratio=(center[axis]-low)/(high-low)
                low=center[axis]-span*ratio;high=low+span
            new.extend((low,high))
        self._view=self._clamp_view(tuple(new));self.schedule();self.event_generate('<<ChartViewChanged>>',when='tail')
        return 'break'
    def _press(self,event):
        super()._press(event)
        if self.kind!='bar' and self._inside(event.x,event.y):
            self._drag_start=(event.x,event.y,self._view or self._full_bounds)
            self._previous_grab=self.canvas.grab_current();self.canvas.grab_set()
    def _drag(self,event):
        if self._drag_start is None:return
        x,y,view=self._drag_start;left,top,right,bottom=self._plot
        dx=(event.x-x)/(right-left)*(view[1]-view[0]);dy=(event.y-y)/(bottom-top)*(view[3]-view[2])
        self._view=self._clamp_view((view[0]-dx,view[1]-dx,view[2]+dy,view[3]+dy))
        self.schedule();return 'break'
    def _release(self,event):
        origin=getattr(self,'_press_position',(event.x,event.y));moved=math.hypot(event.x-origin[0],event.y-origin[1])>self.px(4)
        self._drag_start=None
        if self.canvas.grab_current() is self.canvas:
            self.canvas.grab_release()
            if self._previous_grab is not None and self._previous_grab.winfo_exists():self._previous_grab.grab_set()
        self._previous_grab=None
        if not moved:super()._release(event)
        else:self.event_generate('<<ChartViewChanged>>',when='tail')


class LineChart(_CartesianChart):
    """Line chart with gaps, multiple series, crosshair, zoom and pan."""
    kind='line'


class ColumnChart(_CartesianChart):
    """Grouped vertical bars, including negative values and multiple series."""
    kind='bar'


class ScatterChart(_CartesianChart):
    """Scatter plot with bucket-indexed hit testing, zoom and pan."""
    kind='scatter'


class DonutChart(_Chart):
    def __init__(self,master,*,data=None,hole=.62,height=230,value_formatter=None,**kwargs):
        super().__init__(master,height=height,**kwargs)
        if not 0<=hole<=.85:raise ValueError('hole 应在 0 到 0.85 之间')
        self.hole=hole;self.value_formatter=value_formatter or _format
        self.data=[];self._slices=[];self._center=None;self._aa_item=None;self._lit_slice=None
        self.set_data(data or [])
    def set_hole(self,hole):
        if not 0<=hole<=.85:raise ValueError('hole 应在 0 到 0.85 之间')
        self.hole=hole;self.schedule()
    def set_data(self,data):
        parsed=[];names=set()
        for index,item in enumerate(data):
            if isinstance(item,dict):name=item['name'];value=item['value'];color=item.get('color',COLORS[index%len(COLORS)])
            else:name,value=item;color=COLORS[index%len(COLORS)]
            name=str(name);value=_number(value)
            if value is None or value<0:raise ValueError('饼图 / 环形图需要有限的非负数值')
            if name in names:raise ValueError('名称不能重复：'+name)
            names.add(name);self.winfo_rgb(color)
            parsed.append({'name':name,'value':value,'color':color})
        self.data=parsed;self.hidden.intersection_update(names)
        self._set_legend([(item['name'],item['color']) for item in parsed]);self.schedule()
    def get_data(self):return copy.deepcopy(self.data)
    def _draw(self):
        self._slices=[];self._center=None
        items=[item for item in self.data if item['name'] not in self.hidden and item['value']>0]
        total=sum(item['value'] for item in items)
        if not total:self._empty('点击图例显示数据' if self.hidden else '暂无数据');return
        width,height=self.canvas.winfo_width(),self.canvas.winfo_height()
        radius=max(1,min(width,height)/2-self.px(12));cx=width/2;cy=height/2
        self._center=(cx,cy,radius);bounds=(cx-radius,cy-radius,cx+radius,cy+radius)
        angle=0.
        for item in items:
            extent=item['value']/total*360
            self._slices.append({'start':angle,'end':angle+extent,'color':item['color'],
                                 'data':{'name':item['name'],'value':item['value'],'percent':item['value']/total*100,'kind':'donut' if self.hole else 'pie'}})
            angle+=extent
        self._paint_slices()
        if self.hole:
            inner=radius*self.hole
            text=str(self.value_formatter(total))
            self.canvas.create_text(cx,cy-self.px(7),text=text,font=(self.font.actual('family'),self.font.actual('size')+4,'bold'),fill=PALETTE['fg'],tags='plot')
            self.canvas.create_text(cx,cy+self.px(17),text='合计',font=self.font,fill=PALETTE['muted'],tags='plot')
    def _paint_slices(self,highlight=None):
        if not self._slices or self._center is None:return
        cx,cy,radius=self._center;pad=self.px(3);size=math.ceil(2*(radius+pad));center=size/2
        bounds=(center-radius,center-radius,center+radius,center+radius)
        with SmoothImage(self,size,size) as surface:
            for item in self._slices:
                color=item['color']
                if item['data']['name']==highlight:color='#'+''.join(f'{round(v/257*.84):02x}' for v in self.winfo_rgb(color))
                surface.pie(bounds,item['start']-90,item['end']-item['start'],color)
            if len(self._slices)>1:
                for item in self._slices:
                    angle=math.radians(item['start']-90)
                    surface.line([center,center,center+radius*math.cos(angle),center+radius*math.sin(angle)],PALETTE['bg'],self.px(2))
            if self.hole:
                inner=radius*self.hole;surface.ellipse((center-inner,center-inner,center+inner,center+inner),fill=PALETTE['bg'])
            self._aa_photo=surface.photo()
        if self._aa_item is not None and self.canvas.type(self._aa_item)=='image':
            self.canvas.itemconfigure(self._aa_item,image=self._aa_photo);self.canvas.coords(self._aa_item,cx,cy)
        else:self._aa_item=self.canvas.create_image(cx,cy,image=self._aa_photo,tags='plot')
        self.canvas.tag_lower(self._aa_item)
    def _draw_highlight(self,hit):
        self._lit_slice=hit['data']['name'];self._paint_slices(self._lit_slice)
    def _clear_hover(self,cancel_job=True):
        if getattr(self,'_lit_slice',None) is not None:
            self._lit_slice=None;self._paint_slices()
        super()._clear_hover(cancel_job)
    def _hit(self,x,y):
        if self._center is None:return None
        cx,cy,radius=self._center;distance=math.hypot(x-cx,y-cy)
        if not radius*self.hole<=distance<=radius:return None
        angle=(90-math.degrees(math.atan2(cy-y,x-cx)))%360
        return next((item for item in self._slices if item['start']<=angle<item['end']),None)
    def _tooltip_text(self,data):return f"{data['name']}\n{self.value_formatter(data['value'])}  ·  {data['percent']:.1f}%"


class PieChart(DonutChart):
    def __init__(self,master,**kwargs):
        kwargs.setdefault('hole',0)
        super().__init__(master,**kwargs)
