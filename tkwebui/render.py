"""Antialiased in-memory shapes for Tk PhotoImage. No third-party dependencies.

Windows uses the OS GDI+ renderer. Other platforms use a pixel-coverage fallback.
Text, events, axes and hit testing stay in Tk; no browser or external image files.
"""
import atexit
import ctypes
import math
import struct
import sys
import tkinter as tk
import zlib

_gdip=None
_token=None

class _Point(ctypes.Structure):
    _fields_=[('x',ctypes.c_float),('y',ctypes.c_float)]

def _windows_api():
    global _gdip,_token
    if _gdip is not None:return _gdip
    dll=ctypes.WinDLL('gdiplus')
    pointer=ctypes.c_void_p;integer=ctypes.c_int;real=ctypes.c_float
    class Startup(ctypes.Structure):
        _fields_=[('version',ctypes.c_uint32),('callback',pointer),('background',integer),('codecs',integer)]
    signatures={
        'GdiplusStartup':([ctypes.POINTER(ctypes.c_size_t),ctypes.POINTER(Startup),pointer],integer),
        'GdiplusShutdown':([ctypes.c_size_t],None),
        'GdipCreateBitmapFromScan0':([integer,integer,integer,integer,pointer,ctypes.POINTER(pointer)],integer),
        'GdipGetImageGraphicsContext':([pointer,ctypes.POINTER(pointer)],integer),
        'GdipSetSmoothingMode':([pointer,integer],integer),
        'GdipSetPixelOffsetMode':([pointer,integer],integer),
        'GdipCreateSolidFill':([ctypes.c_uint32,ctypes.POINTER(pointer)],integer),
        'GdipCreatePen1':([ctypes.c_uint32,real,integer,ctypes.POINTER(pointer)],integer),
        'GdipSetPenStartCap':([pointer,integer],integer),
        'GdipSetPenEndCap':([pointer,integer],integer),
        'GdipSetPenLineJoin':([pointer,integer],integer),
        'GdipDrawLines':([pointer,pointer,ctypes.POINTER(_Point),integer],integer),
        'GdipDrawEllipse':([pointer,pointer,real,real,real,real],integer),
        'GdipFillEllipse':([pointer,pointer,real,real,real,real],integer),
        'GdipDrawArc':([pointer,pointer,real,real,real,real,real,real],integer),
        'GdipFillPie':([pointer,pointer,real,real,real,real,real,real],integer),
        'GdipFillRectangle':([pointer,pointer,real,real,real,real],integer),
        'GdipFlush':([pointer,integer],integer),
        'GdipDeleteBrush':([pointer],integer),'GdipDeletePen':([pointer],integer),
        'GdipDeleteGraphics':([pointer],integer),'GdipDisposeImage':([pointer],integer),
    }
    for name,(args,result) in signatures.items():
        fn=getattr(dll,name);fn.argtypes=args;fn.restype=result
    token=ctypes.c_size_t()
    if dll.GdiplusStartup(ctypes.byref(token),ctypes.byref(Startup(1,None,0,0)),None):raise OSError('GDI+ startup failed')
    _token=token;_gdip=dll;atexit.register(dll.GdiplusShutdown,token)
    return dll

def _png(width,height,rgba):
    def chunk(name,data):return struct.pack('>I',len(data))+name+data+struct.pack('>I',zlib.crc32(name+data)&0xffffffff)
    stride=width*4
    raw=b''.join(b'\0'+rgba[y*stride:(y+1)*stride] for y in range(height))
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(raw,2))+chunk(b'IEND',b'')

class SmoothImage:
    """A short-lived drawing surface. Keep the returned PhotoImage alive in Tk."""
    def __init__(self,master,width,height,*,software=False):
        self.master=master;self.width=max(1,int(math.ceil(width)));self.height=max(1,int(math.ceil(height)))
        self.api=None;self.bitmap=ctypes.c_void_p();self.graphics=ctypes.c_void_p()
        self.pens={};self.brushes={};self.colors={};self.closed=False
        if sys.platform=='win32' and not software:
            try:
                self.api=_windows_api()
                self.buffer=(ctypes.c_ubyte*(self.width*self.height*4))()
                self._check(self.api.GdipCreateBitmapFromScan0(self.width,self.height,self.width*4,0x26200A,self.buffer,ctypes.byref(self.bitmap)))
                self._check(self.api.GdipGetImageGraphicsContext(self.bitmap,ctypes.byref(self.graphics)))
                self._check(self.api.GdipSetSmoothingMode(self.graphics,5)) # 8 x 8 edge coverage
                self._check(self.api.GdipSetPixelOffsetMode(self.graphics,4))
            except (OSError,AttributeError):
                if self.graphics:self.api.GdipDeleteGraphics(self.graphics)
                if self.bitmap:self.api.GdipDisposeImage(self.bitmap)
                self.api=None
        if self.api is None:self.buffer=bytearray(self.width*self.height*4)
        self.backend='gdi+' if self.api else 'coverage'
    @staticmethod
    def _check(status):
        if status:raise OSError(f'GDI+ status {status}')
    def _color(self,color):
        if color not in self.colors:
            self.colors[color]=tuple(round(c/257) for c in self.master.winfo_rgb(color))
        return self.colors[color]
    def _argb(self,color):
        r,g,b=self._color(color);return 0xff000000|(r<<16)|(g<<8)|b
    def _pen(self,color,width):
        key=(color,width)
        if key not in self.pens:
            pen=ctypes.c_void_p();self._check(self.api.GdipCreatePen1(self._argb(color),width,2,ctypes.byref(pen)))
            self.api.GdipSetPenStartCap(pen,2);self.api.GdipSetPenEndCap(pen,2);self.api.GdipSetPenLineJoin(pen,2)
            self.pens[key]=pen
        return self.pens[key]
    def _brush(self,color):
        if color not in self.brushes:
            brush=ctypes.c_void_p();self._check(self.api.GdipCreateSolidFill(self._argb(color),ctypes.byref(brush)));self.brushes[color]=brush
        return self.brushes[color]
    def _blend(self,x,y,rgb,coverage):
        if coverage<=0:return
        coverage=min(1,coverage);i=(y*self.width+x)*4;buf=self.buffer
        if coverage>=1:buf[i:i+4]=bytes((*rgb,255));return
        old=buf[i+3]/255;alpha=coverage+old*(1-coverage)
        if not alpha:return
        for c in range(3):buf[i+c]=round((rgb[c]*coverage+buf[i+c]*old*(1-coverage))/alpha)
        buf[i+3]=round(alpha*255)
    def _paint(self,bounds,color,coverage):
        x1,y1,x2,y2=bounds;rgb=self._color(color)
        for y in range(max(0,math.floor(y1)),min(self.height,math.ceil(y2))):
            for x in range(max(0,math.floor(x1)),min(self.width,math.ceil(x2))):
                self._blend(x,y,rgb,coverage(x+.5,y+.5))
    def line(self,points,color,width=1):
        if len(points)<4:return
        if self.api:
            values=(_Point*(len(points)//2))(*[_Point(points[i],points[i+1]) for i in range(0,len(points),2)])
            self._check(self.api.GdipDrawLines(self.graphics,self._pen(color,width),values,len(values)));return
        radius=width/2
        for i in range(0,len(points)-2,2):
            x1,y1,x2,y2=points[i:i+4];dx=x2-x1;dy=y2-y1;square=dx*dx+dy*dy
            def coverage(x,y):
                t=max(0,min(1,((x-x1)*dx+(y-y1)*dy)/square)) if square else 0
                return max(0,min(1,radius+.5-math.hypot(x-x1-t*dx,y-y1-t*dy)))
            self._paint((min(x1,x2)-radius-1,min(y1,y2)-radius-1,max(x1,x2)+radius+1,max(y1,y2)+radius+1),color,coverage)
    def ellipse(self,bounds,*,fill=None,outline=None,width=1):
        x1,y1,x2,y2=bounds
        if self.api:
            if fill:self._check(self.api.GdipFillEllipse(self.graphics,self._brush(fill),x1,y1,x2-x1,y2-y1))
            if outline:self._check(self.api.GdipDrawEllipse(self.graphics,self._pen(outline,width),x1,y1,x2-x1,y2-y1))
            return
        cx=(x1+x2)/2;cy=(y1+y2)/2;rx=max(.001,(x2-x1)/2);ry=max(.001,(y2-y1)/2);r=min(rx,ry)
        def distance(x,y):return (math.hypot((x-cx)/rx,(y-cy)/ry)-1)*r
        if fill:self._paint((x1-1,y1-1,x2+1,y2+1),fill,lambda x,y:max(0,min(1,.5-distance(x,y))))
        if outline:self._paint((x1-width,y1-width,x2+width,y2+width),outline,lambda x,y:max(0,min(1,width/2+.5-abs(distance(x,y)))))
    def arc(self,bounds,start,sweep,color,width=1):
        if sweep<=0:return
        if sweep>=359.999:self.ellipse(bounds,outline=color,width=width);return
        x1,y1,x2,y2=bounds
        if self.api:
            self._check(self.api.GdipDrawArc(self.graphics,self._pen(color,width),x1,y1,x2-x1,y2-y1,start,sweep));return
        cx=(x1+x2)/2;cy=(y1+y2)/2;radius=(x2-x1)/2
        a=math.radians(start);b=math.radians(start+sweep)
        ends=[(cx+radius*math.cos(angle),cy+radius*math.sin(angle)) for angle in (a,b)]
        def coverage(x,y):
            angle=(math.degrees(math.atan2(y-cy,x-cx))-start)%360
            distance=abs(math.hypot(x-cx,y-cy)-radius) if angle<=sweep else min(math.hypot(x-ex,y-ey) for ex,ey in ends)
            return max(0,min(1,width/2+.5-distance))
        self._paint((x1-width,y1-width,x2+width,y2+width),color,coverage)
    def pie(self,bounds,start,sweep,color):
        if sweep<=0:return
        if sweep>=359.999:self.ellipse(bounds,fill=color);return
        x1,y1,x2,y2=bounds
        if self.api:
            self._check(self.api.GdipFillPie(self.graphics,self._brush(color),x1,y1,x2-x1,y2-y1,start,sweep));return
        cx=(x1+x2)/2;cy=(y1+y2)/2;radius=(x2-x1)/2
        def coverage(x,y):
            hits=0
            for dx,dy in ((-.25,-.25),(.25,-.25),(-.25,.25),(.25,.25)):
                angle=(math.degrees(math.atan2(y+dy-cy,x+dx-cx))-start)%360
                hits+=math.hypot(x+dx-cx,y+dy-cy)<=radius and angle<=sweep
            return hits/4
        self._paint((x1-1,y1-1,x2+1,y2+1),color,coverage)
    def rectangle(self,bounds,color):
        x1,y1,x2,y2=bounds
        if self.api:self._check(self.api.GdipFillRectangle(self.graphics,self._brush(color),x1,y1,x2-x1,y2-y1));return
        self._paint(bounds,color,lambda x,y:1)
    def rgba(self):
        if not self.api:return bytes(self.buffer)
        self._check(self.api.GdipFlush(self.graphics,1))
        bgra=bytes(self.buffer);rgba=bytearray(len(bgra))
        rgba[0::4]=bgra[2::4];rgba[1::4]=bgra[1::4];rgba[2::4]=bgra[0::4];rgba[3::4]=bgra[3::4]
        return bytes(rgba)
    def photo(self):return tk.PhotoImage(master=self.master,data=_png(self.width,self.height,self.rgba()),format='png')
    def close(self):
        if self.closed:return
        self.closed=True
        if self.api:
            for pen in self.pens.values():self.api.GdipDeletePen(pen)
            for brush in self.brushes.values():self.api.GdipDeleteBrush(brush)
            self.api.GdipDeleteGraphics(self.graphics);self.api.GdipDisposeImage(self.bitmap)
    def __enter__(self):return self
    def __exit__(self,*_):self.close()

def calendar_icon(master,size,color='#697180'):
    root=master._root();cache=getattr(root,'_web_calendar_icons',None)
    if cache is None:cache=root._web_calendar_icons={}
    key=(size,color)
    if key not in cache:
        scale=size/24
        with SmoothImage(root,size,size) as image:
            def line(coords):image.line([v*scale for v in coords],color,max(1,1.5*scale))
            line([4,6,20,6,20,21,4,21,4,6]);line([4,10,20,10]);line([8,3,8,8]);line([16,3,16,8])
            for y in (13,17):
                for x in (7,11,15):image.rectangle((x*scale,y*scale,(x+2)*scale,(y+2)*scale),color)
            cache[key]=image.photo()
    return cache[key]
