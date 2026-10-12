"""Native color/font pickers and an image viewport; Pillow is optional."""
import colorsys
import struct
import zlib
import math
from pathlib import Path
import tkinter as tk
from tkinter import ttk, font as tkfont, filedialog
from .core import PALETTE, Card
from .popups import ThemedCombobox
from .forms import ResultDialog

def _photo_rows(photo):
    """Decode the known 8-bit RGB/RGBA PNG emitted by Tk, preserving alpha."""
    png=bytes(photo.tk.call(str(photo),'data','-format','png'))
    offset=8;compressed=[];header=None
    while offset<len(png):
        size=struct.unpack_from('>I',png,offset)[0];kind=png[offset+4:offset+8];data=png[offset+8:offset+8+size]
        if kind==b'IHDR':header=struct.unpack('>IIBBBBB',data)
        elif kind==b'IDAT':compressed.append(data)
        offset+=size+12
    width,height,depth,color_type,_,_,interlace=header
    channels={2:3,6:4}.get(color_type)
    if depth!=8 or channels is None or interlace:raise ValueError('当前 Tk 的图片导出格式不支持原生缩放')
    raw=zlib.decompress(b''.join(compressed));stride=width*channels;previous=bytearray(stride);rows=[]
    for y in range(height):
        start=y*(stride+1);mode=raw[start];row=bytearray(raw[start+1:start+1+stride])
        if mode:
            for i in range(stride):
                a=row[i-channels] if i>=channels else 0;b=previous[i];c=previous[i-channels] if i>=channels else 0
                if mode==1:predictor=a
                elif mode==2:predictor=b
                elif mode==3:predictor=(a+b)//2
                elif mode==4:
                    p=a+b-c;pa,pb,pc=abs(p-a),abs(p-b),abs(p-c)
                    predictor=a if pa<=pb and pa<=pc else b if pb<=pc else c
                else:raise ValueError('无法解码 Tk 图片行')
                row[i]=(row[i]+predictor)&255
        rows.append(bytes(row));previous=row
    return width,height,channels,color_type,rows

def _resize_photo(master,decoded,width,height):
    source_width,source_height,channels,color_type,rows=decoded
    offsets=[min(source_width-1,x*source_width//width)*channels for x in range(width)]
    output=[];previous_y=None;scaled=None
    for y in range(height):
        source_y=min(source_height-1,y*source_height//height)
        if source_y!=previous_y:
            row=rows[source_y];scaled=b'\0'+b''.join(row[x:x+channels] for x in offsets);previous_y=source_y
        output.append(scaled)
    def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,color_type,0,0,0))
    png+=chunk(b'IDAT',zlib.compress(b''.join(output),3))+chunk(b'IEND',b'')
    return tk.PhotoImage(master=master,data=png,format='png')

class ColorPicker(ttk.Frame):
    def __init__(self,master,*,color='#087DFF',command=None,**kwargs):
        super().__init__(master,**kwargs)
        self.command=command;self._busy=False;self._job=None;self._closed=False
        self.dpi=self.winfo_fpixels('1i')/96;self.px=lambda n:max(1,round(n*self.dpi))
        self._h,self._s,self._v=0,0,1;self._gradient=None
        self.hex=tk.StringVar(self);self.rgb=[tk.StringVar(self) for _ in range(3)];self.hue=tk.DoubleVar(self)
        self.canvas=tk.Canvas(self,height=self.px(145),width=self.px(280),highlightthickness=0,background=PALETTE['bg'],cursor='crosshair')
        self.canvas.pack(fill='x');self.canvas.bind('<Configure>',lambda e:self._schedule_gradient())
        self.canvas.bind('<Button-1>',self._pick);self.canvas.bind('<B1-Motion>',self._pick)
        self.hue_canvas=tk.Canvas(self,height=self.px(20),background=PALETTE['bg'],highlightthickness=0,cursor='hand2')
        self.hue_canvas.pack(fill='x',pady=8)
        self.hue_canvas.bind('<Configure>',lambda e:self._draw_hue())
        self.hue_canvas.bind('<Button-1>',self._pick_hue);self.hue_canvas.bind('<B1-Motion>',self._pick_hue)
        self._hue_image=None
        row=ttk.Frame(self);row.pack(fill='x')
        self.swatch=tk.Label(row,width=5,background=color,relief='flat');self.swatch.pack(side='left',fill='y',padx=(0,8))
        ttk.Label(row,text='HEX').pack(side='left',padx=(0,5))
        self.hex_entry=ttk.Entry(row,textvariable=self.hex,width=10);self.hex_entry.pack(side='left',fill='x',expand=True)
        self.hex_entry.bind('<Return>',lambda e:self.apply_hex());self.hex_entry.bind('<FocusOut>',lambda e:self.apply_hex())
        ttk.Button(row,text='复制',command=self.copy_color).pack(side='left',padx=(6,0))
        row=ttk.Frame(self);row.pack(fill='x',pady=8)
        for name,var in zip('RGB',self.rgb):
            ttk.Label(row,text=name).pack(side='left',padx=(0,4))
            spin=ttk.Spinbox(row,from_=0,to=255,width=4,textvariable=var,command=self.apply_rgb)
            spin.pack(side='left',padx=(0,9));spin.bind('<Return>',lambda e:self.apply_rgb());spin.bind('<FocusOut>',lambda e:self.apply_rgb())
        palette=ttk.Frame(self);palette.pack(fill='x',pady=(3,0));self._swatches=[]
        for color_value in ['#087DFF','#159576','#E8A138','#D54B58','#8B68D9','#197FA8','#16181D','#FFFFFF']:
            image=tk.PhotoImage(master=self,width=self.px(24),height=self.px(18));image.put(color_value,to=(0,0,image.width(),image.height()))
            for box in [(0,0,image.width(),1),(0,image.height()-1,image.width(),image.height()),(0,0,1,image.height()),(image.width()-1,0,image.width(),image.height())]:image.put('#CCD1DC',to=box)
            self._swatches.append(image)
            ttk.Button(palette,image=image,style='Quiet.TButton',command=lambda v=color_value:self.set_color(v)).pack(side='left',padx=1)
        self.status=tk.StringVar(self);ttk.Label(self,textvariable=self.status,style='Danger.TLabel').pack(anchor='w',pady=(5,0))
        self.bind('<Destroy>',self._cleanup,add='+');self.set_color(color,notify=False)
    def _normalize(self,color):
        text=str(color).strip()
        if len(text)==4 and text.startswith('#'):text='#'+''.join(c*2 for c in text[1:])
        try:rgb=self.winfo_rgb(text)
        except tk.TclError as exc:raise ValueError('请输入有效颜色，例如 #087DFF') from exc
        return '#'+''.join(f'{round(channel/257):02X}' for channel in rgb)
    def get_color(self):return self._normalize(self.hex.get())
    def set_color(self,color,*,notify=True):
        color=self._normalize(color);rgb=[int(color[i:i+2],16) for i in (1,3,5)]
        self._h,self._s,self._v=colorsys.rgb_to_hsv(*(c/255 for c in rgb))
        self._busy=True
        try:
            self.hex.set(color)
            for var,value in zip(self.rgb,rgb):var.set(str(value))
            self.hue.set(self._h);self.swatch.configure(background=color);self.hex_entry.state(['!invalid']);self.status.set('')
        finally:self._busy=False
        self._schedule_gradient()
        if notify:
            self.event_generate('<<ColorChanged>>',when='tail')
            if self.command:self.command(color)
    def apply_hex(self):
        try:self.set_color(self.hex.get());return True
        except ValueError as exc:self.status.set(str(exc));self.hex_entry.state(['invalid']);return False
    def apply_rgb(self):
        if self._busy:return
        try:
            rgb=[int(var.get()) for var in self.rgb]
            if any(not 0<=value<=255 for value in rgb):raise ValueError()
            self.set_color('#'+''.join(f'{value:02X}' for value in rgb));return True
        except ValueError:self.status.set('RGB 必须为 0–255 的整数');return False
    def _hue_changed(self,value):
        if self._busy:return
        self._h=float(value);self.hue.set(self._h);self._apply_hsv(rebuild=True)
    def _pick_hue(self,event):
        self._hue_changed(max(0,min(1,event.x/max(1,self.hue_canvas.winfo_width()-1))))
    def _draw_hue(self):
        width=max(2,self.hue_canvas.winfo_width());source=tk.PhotoImage(master=self,width=width,height=1)
        colors=['#'+''.join(f'{round(v*255):02x}' for v in colorsys.hsv_to_rgb(x/(width-1),1,1)) for x in range(width)]
        source.put('{'+' '.join(colors)+'}');self._hue_image=source.zoom(1,self.px(12))
        self.hue_canvas.delete('all');self.hue_canvas.create_image(0,self.px(4),image=self._hue_image,anchor='nw');self._hue_marker()
    def _hue_marker(self):
        self.hue_canvas.delete('marker');x=self._h*(self.hue_canvas.winfo_width()-1)
        self.hue_canvas.create_rectangle(x-self.px(2),1,x+self.px(2),self.px(20)-1,outline='#FFFFFF',width=2,tags='marker')
    def _pick(self,event):
        self._s=max(0,min(1,event.x/max(1,self.canvas.winfo_width()-1)))
        self._v=1-max(0,min(1,event.y/max(1,self.canvas.winfo_height()-1)))
        self._apply_hsv(rebuild=False)
    def _apply_hsv(self,rebuild):
        rgb=[round(c*255) for c in colorsys.hsv_to_rgb(self._h,self._s,self._v)];color='#'+''.join(f'{c:02X}' for c in rgb)
        self._busy=True
        try:
            self.hex.set(color)
            for var,value in zip(self.rgb,rgb):var.set(str(value))
            self.swatch.configure(background=color);self.status.set('');self.hex_entry.state(['!invalid'])
        finally:self._busy=False
        if rebuild:self._schedule_gradient()
        else:self._marker()
        if self.command:self.command(color)
        self.event_generate('<<ColorChanged>>',when='tail')
    def _schedule_gradient(self):
        if not self._closed and self._job is None:self._job=self.after(35,self._draw_gradient)
    def _draw_gradient(self):
        self._job=None
        if self._closed:return
        w,h=self.canvas.winfo_width(),self.canvas.winfo_height()
        if w<2 or h<2:return
        cell=self.px(1);cols=math.ceil(w/cell);rows=math.ceil(h/cell)
        source=tk.PhotoImage(master=self,width=cols,height=rows)
        pixels=[]
        pure=colorsys.hsv_to_rgb(self._h,1,1)
        columns=[tuple(1+(channel-1)*x/max(1,cols-1) for channel in pure) for x in range(cols)]
        for y in range(rows):
            value=1-y/max(1,rows-1)
            row=['#'+''.join(f'{round(channel*value*255):02x}' for channel in column) for column in columns]
            pixels.append('{'+ ' '.join(row)+'}')
        source.put(' '.join(pixels));self._gradient=source.zoom(cell)
        self.canvas.delete('gradient');self.canvas.create_image(0,0,image=self._gradient,anchor='nw',tags='gradient');self.canvas.tag_lower('gradient');self._marker();self._hue_marker()
    def _marker(self):
        self.canvas.delete('marker');x=self._s*(self.canvas.winfo_width()-1);y=(1-self._v)*(self.canvas.winfo_height()-1);r=self.px(5)
        self.canvas.create_oval(x-r,y-r,x+r,y+r,outline='#FFFFFF',width=2,tags='marker')
        self.canvas.create_oval(x-r-1,y-r-1,x+r+1,y+r+1,outline='#333333',width=1,tags='marker')
    def copy_color(self):
        if self.apply_hex():self.clipboard_clear();self.clipboard_append(self.get_color())
    def _cleanup(self,event):
        if event.widget is self:
            self._closed=True
            if self._job is not None:self.after_cancel(self._job)

class ColorDialog(ResultDialog):
    def __init__(self,master,*,color='#087DFF',title='选择颜色'):
        super().__init__(master,title,width=480,height=470)
        self.picker=ColorPicker(self.body,color=color);self.picker.pack(fill='both',expand=True)
        self.primary.configure(text='使用颜色',command=self.submit);self.secondary.pack(side='right',padx=8)
    def submit(self):
        if self.picker.apply_hex():self.accept(self.picker.get_color())

class FontPicker(ttk.Frame):
    def __init__(self,master,*,font='TkDefaultFont',**kwargs):
        super().__init__(master,**kwargs)
        self.preview_font=tkfont.Font(root=self._root(),font=font)
        settings=self.preview_font.actual();self.families=sorted(set(tkfont.families(self)),key=str.casefold)
        self.family=tk.StringVar(self,value=settings['family']);self.size=tk.StringVar(self,value=str(settings['size']))
        self.bold=tk.BooleanVar(self,value=settings['weight']=='bold');self.italic=tk.BooleanVar(self,value=settings['slant']=='italic')
        ttk.Label(self,text='字体（可输入名称搜索）').pack(anchor='w',pady=(0,6))
        self.combo=ThemedCombobox(self,textvariable=self.family,values=self.families[:80]);self.combo.pack(fill='x')
        row=ttk.Frame(self);row.pack(fill='x',pady=12)
        ttk.Label(row,text='字号').pack(side='left',padx=(0,8))
        ttk.Spinbox(row,from_=6,to=96,textvariable=self.size,width=5,command=self.refresh).pack(side='left')
        ttk.Checkbutton(row,text='粗体',variable=self.bold,command=self.refresh).pack(side='left',padx=12)
        ttk.Checkbutton(row,text='斜体',variable=self.italic,command=self.refresh).pack(side='left')
        area=Card(self,padding=14);area.pack(fill='both',expand=True)
        self.sample=ttk.Label(area,text='中文字体预览\nThe quick brown fox\n0123456789',font=self.preview_font,justify='left',wraplength=360)
        self.sample.pack(fill='both',expand=True,pady=8)
        self.status=tk.StringVar(self);ttk.Label(self,textvariable=self.status,style='Danger.TLabel').pack(anchor='w',pady=4)
        self._family_trace=self.family.trace_add('write',self._filter);self._size_trace=self.size.trace_add('write',lambda *_:self.refresh())
        self.bind('<Destroy>',self._cleanup,add='+')
    def _filter(self,*_):
        text=self.family.get().casefold();matches=[family for family in self.families if text in family.casefold()]
        self.combo.configure(values=(matches or self.families)[:80]);self.refresh()
    def refresh(self):
        try:
            size=int(self.size.get())
            if not 6<=size<=96:raise ValueError()
        except ValueError:self.status.set('字号应为 6–96 的整数');return False
        self.preview_font.configure(family=self.family.get(),size=size,weight='bold' if self.bold.get() else 'normal',slant='italic' if self.italic.get() else 'roman')
        self.status.set('');return True
    def get_font(self):
        if not self.refresh():raise ValueError(self.status.get())
        if self.family.get() not in self.families:raise ValueError('请从字体列表中选择完整字体名称')
        return self.preview_font.copy()
    def _cleanup(self,event):
        if event.widget is self:
            self.family.trace_remove('write',self._family_trace);self.size.trace_remove('write',self._size_trace)

class FontDialog(ResultDialog):
    def __init__(self,master,*,font='TkDefaultFont',title='选择字体'):
        super().__init__(master,title,width=480,height=430)
        self.picker=FontPicker(self.body,font=font);self.picker.pack(fill='both',expand=True)
        self.primary.configure(text='使用字体',command=self.submit);self.secondary.pack(side='right',padx=8)
    def submit(self):
        try:font=self.picker.get_font()
        except ValueError as exc:self.picker.status.set(str(exc));return
        self.accept(font)

class ImageViewer(ttk.Frame):
    def __init__(self,master,*,height=300,max_render_pixels=4_000_000,**kwargs):
        super().__init__(master,**kwargs)
        self._source=None;self._pil=None;self._display=None;self._native_rows=None;self.path=None;self.error=''
        self._fit=True;self.zoom_ratio=1.;self.cx=self.cy=0.;self._job=None;self._closed=False;self.max_render_pixels=max_render_pixels
        self.dpi=self.winfo_fpixels('1i')/96
        tools=ttk.Frame(self);tools.pack(fill='x',pady=(0,6))
        for text,command in [('打开',self.choose_file),('适应窗口',self.fit),('1:1',lambda:self.set_zoom(1)),('−',lambda:self.set_zoom(self.zoom_ratio/1.25)),('+',lambda:self.set_zoom(self.zoom_ratio*1.25)),('清空',self.clear)]:
            ttk.Button(tools,text=text,command=command,width=3 if text in ('−','+') else None).pack(side='left',padx=(0,5))
        self.canvas=tk.Canvas(self,height=round(height*self.dpi),background='#F5F6F9',highlightthickness=1,highlightbackground=PALETTE['border'])
        self.canvas.pack(fill='both',expand=True)
        self._item=self.canvas.create_image(0,0,anchor='center');self._empty=self.canvas.create_text(0,0,text='打开图片，或由程序传入 PhotoImage',fill=PALETTE['muted'],font='TkDefaultFont')
        self.status=tk.StringVar(self,value='PNG / GIF / PPM / PGM 原生支持；其他格式可选 Pillow')
        ttk.Label(self,textvariable=self.status,style='Muted.TLabel',wraplength=700).pack(fill='x',pady=(6,0))
        self.canvas.bind('<Configure>',self._resized);self.canvas.bind('<MouseWheel>',self._wheel)
        self.canvas.bind('<ButtonPress-1>',self._press);self.canvas.bind('<B1-Motion>',self._drag)
        self.canvas.bind('<Double-Button-1>',lambda e:self.fit());self._drag_start=None
        self.bind('<Destroy>',self._cleanup,add='+')
    def choose_file(self):
        path=filedialog.askopenfilename(parent=self,title='打开图片',filetypes=[('图片','*.png *.gif *.ppm *.pgm *.jpg *.jpeg *.bmp *.webp'),('所有文件','*.*')])
        if path:self.load(path)
    def load(self,path):
        path=Path(path).expanduser().resolve()
        Image=None
        try:
            try:
                from PIL import Image, ImageOps
            except ImportError:Image=None
            if Image is not None:
                with Image.open(path) as source:pil=ImageOps.exif_transpose(source).convert('RGBA').copy()
                native=None
            else:
                pil=None;native=tk.PhotoImage(master=self,file=str(path))
        except (OSError,ValueError,tk.TclError) as exc:
            self.error='无法打开图片：'+str(exc)
            if Image is None:self.error+='；JPEG / WebP 等格式可安装 Pillow 后使用'
            self.status.set(self.error);return False
        self._pil=pil;self._source=native;self._native_rows=None;self.path=path;self.error='';self.fit();return True
    def set_image(self,image):
        if not isinstance(image,tk.PhotoImage):raise TypeError('set_image 接收 tkinter.PhotoImage')
        self._source=image.copy();self._pil=None;self._native_rows=None;self.path=None;self.error='';self.fit()
    def _size(self):
        if self._pil is not None:return self._pil.size
        if self._source is not None:return self._source.width(),self._source.height()
        return 0,0
    def clear(self):
        self._source=self._pil=self._display=self._native_rows=None;self.path=None;self.error='';self.canvas.itemconfigure(self._item,image='')
        self.canvas.itemconfigure(self._empty,state='normal');self.status.set('未加载图片')
    def fit(self):
        self._fit=True;self._schedule()
    def set_zoom(self,value,anchor=None):
        w,h=self._size()
        if not w or not h:return
        old=self.zoom_ratio
        upper=min(8,math.sqrt(self.max_render_pixels/(w*h)),4096/max(w,h))
        value=max(1/max(w,h),min(float(value),upper))
        if anchor and old:
            self.cx=anchor[0]-(anchor[0]-self.cx)*value/old;self.cy=anchor[1]-(anchor[1]-self.cy)*value/old
        self.zoom_ratio=value;self._fit=False;self._schedule()
    def _resized(self,event):
        self.canvas.coords(self._empty,event.width/2,event.height/2)
        self.canvas.delete('checker');cell=round(18*self.dpi)
        for y in range(0,event.height,cell):
            for x in range(0,event.width,cell):
                if (x//cell+y//cell)%2:self.canvas.create_rectangle(x,y,x+cell,y+cell,fill='#E9ECF1',outline='',tags='checker')
        self.canvas.tag_lower('checker');self._schedule()
    def _schedule(self):
        if not self._closed and self._job is None:self._job=self.after(25,self._render)
    def _render(self):
        self._job=None
        if self._closed:return
        w,h=self._size()
        if not w or not h:return
        cw,ch=self.canvas.winfo_width(),self.canvas.winfo_height()
        if cw<2 or ch<2:return
        if self._fit:
            self.zoom_ratio=min((cw-16)/w,(ch-16)/h,math.sqrt(self.max_render_pixels/(w*h)),4096/max(w,h))
            self.zoom_ratio=max(self.zoom_ratio,1/max(w,h));self.cx=cw/2;self.cy=ch/2
        if self._pil is not None:
            from PIL import Image, ImageTk
            size=(max(1,round(w*self.zoom_ratio)),max(1,round(h*self.zoom_ratio)))
            self._display=ImageTk.PhotoImage(self._pil.resize(size,Image.Resampling.LANCZOS),master=self)
            backend='Pillow'
        else:
            if self._native_rows is None:self._native_rows=_photo_rows(self._source)
            self._display=_resize_photo(self,self._native_rows,max(1,round(w*self.zoom_ratio)),max(1,round(h*self.zoom_ratio)))
            backend='Tk 原生'
        self.canvas.itemconfigure(self._empty,state='hidden');self.canvas.itemconfigure(self._item,image=self._display)
        self.canvas.coords(self._item,self.cx,self.cy);self.canvas.tag_raise(self._item)
        actual=self._display.width()/w
        self.status.set(f'{self.path.name if self.path else "内存图片"} · {w} × {h} · {actual*100:.0f}% · {backend}')
    def _wheel(self,event):
        if self._size()[0]:self.set_zoom(self.zoom_ratio*(1.2 if event.delta>0 else 1/1.2),(event.x,event.y))
        return 'break'
    def _press(self,event):self._drag_start=(event.x,event.y,self.cx,self.cy)
    def _drag(self,event):
        if self._drag_start is None:return
        x,y,cx,cy=self._drag_start;self.cx=cx+event.x-x;self.cy=cy+event.y-y;self._fit=False
        self.canvas.coords(self._item,self.cx,self.cy)
    def _cleanup(self,event):
        if event.widget is self:
            self._closed=True
            if self._job is not None:self.after_cancel(self._job)
