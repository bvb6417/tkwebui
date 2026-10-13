"""Sortable native Treeview and an editable, cell-selectable TSV spreadsheet."""
from __future__ import annotations
import csv
from decimal import Decimal, InvalidOperation
import io
import math
import re
import tkinter as tk
from tkinter import ttk, font as tkfont
from .core import PALETTE
from .scrolling import AutoScrollbar


def _sort_key(value):
    text=str(value).strip()
    try:
        number=Decimal(text.replace(',','').rstrip('%'))
        if number.is_finite():return 0,number
    except InvalidOperation:pass
    return 1,tuple((0,int(part)) if part.isdigit() else (1,part) for part in re.split(r'(\d+)',text.casefold()))


class TableSorter:
    def __init__(self,tree):
        self.tree=tree;self.labels={};self.column=None;self.reverse=False
        self.refresh()
    def refresh(self):
        for column in self.tree['columns']:
            current=self.tree.heading(column)
            if column not in self.labels and not current.get('command'):
                self.labels[column]=current['text']
                self.tree.heading(column,command=lambda c=column:self.sort_by(c))
    def sort_by(self,column,reverse=None):
        if column not in self.tree['columns']:raise ValueError('Unknown column: '+str(column))
        reverse=(not self.reverse if column==self.column else False) if reverse is None else bool(reverse)
        def sort_children(parent):
            children=self.tree.get_children(parent)
            values=[(self.tree.set(item,column),item) for item in children]
            filled=[pair for pair in values if str(pair[0]).strip()]
            empty=[pair for pair in values if not str(pair[0]).strip()]
            ordered=sorted(filled,key=lambda pair:_sort_key(pair[0]),reverse=reverse)+empty
            for position,(_,item) in enumerate(ordered):
                self.tree.move(item,parent,position)
                if self.tree.get_children(item):sort_children(item)
        sort_children('')
        for key in self.labels:
            current=self.tree.heading(key,'text')
            self.labels[key]=re.sub(r' [▲▼]$','',current)
            self.tree.heading(key,text=self.labels[key]+((' ▼' if reverse else ' ▲') if key==column else ''))
        self.column=column;self.reverse=reverse
        self.tree.event_generate('<<TreeviewSorted>>',when='tail')


def enable_sorting(tree):
    """Install native heading commands. Existing custom heading commands are retained."""
    if not hasattr(tree,'_web_sorter'):tree._web_sorter=TableSorter(tree)
    else:tree._web_sorter.refresh()
    return tree._web_sorter


class SortableTreeview(ttk.Treeview):
    def __init__(self,master=None,**kwargs):
        super().__init__(master,**kwargs)
        enable_sorting(self)
    def sort_by(self,column,reverse=None):
        self._web_sorter.sort_by(column,reverse)


def column_name(index):
    result='';index+=1
    while index:
        index,remainder=divmod(index-1,26);result=chr(65+remainder)+result
    return result


class Spreadsheet(ttk.Frame):
    """Editable cells; Shift range, Ctrl disjoint selection, TSV copy/paste and undo.

    Coordinates in the API are zero-based (row, column). Paste starts at `active`,
    not the selection's bounding box. Disjoint copying leaves blank TSV cells in
    the gaps. Values are plain text; formulas are never evaluated.
    """
    def __init__(self,master,*,data=None,rows=30,columns=8,headers=None,column_width=122,row_height=30,max_cells=1_000_000,**kwargs):
        super().__init__(master,**kwargs)
        self.scale=self.winfo_fpixels('1i')/96;self.px=lambda n:max(1,round(n*self.scale))
        self.cw=self.px(column_width);self.rh=self.px(row_height);self.max_cells=max_cells
        self.headers=list(headers or []);self.active=(0,0);self.anchor=(0,0)
        self.selection={(0,0)};self._drag_base=set();self._drag_anchor=(0,0)
        self._draw_job=None;self.editor=None;self.editing_cell=None;self._closing=False
        self._undo=[];self._redo=[];self._previous_grab=None
        self.font=tkfont.Font(self,family='Microsoft YaHei UI',size=10)
        self.columnconfigure(1,weight=1);self.rowconfigure(1,weight=1)
        canvas_options=dict(background=PALETTE['bg'],highlightthickness=0,borderwidth=0)
        self.corner=tk.Canvas(self,width=self.px(45),height=self.rh,**canvas_options)
        self.top=tk.Canvas(self,height=self.rh,**canvas_options)
        self.left=tk.Canvas(self,width=self.px(45),**canvas_options)
        self.canvas=tk.Canvas(self,takefocus=True,**canvas_options)
        self.corner.grid(row=0,column=0,sticky='nsew');self.top.grid(row=0,column=1,sticky='ew')
        self.left.grid(row=1,column=0,sticky='ns');self.canvas.grid(row=1,column=1,sticky='nsew')
        self.vbar=AutoScrollbar(self,command=self.yview);self.vbar.grid(row=1,column=2,sticky='ns')
        self.hbar=AutoScrollbar(self,orient='horizontal',command=self.xview);self.hbar.grid(row=2,column=1,sticky='ew')
        self.canvas.configure(xscrollcommand=self._xscroll,yscrollcommand=self._yscroll)
        self.status=tk.StringVar(self,value='A1')
        ttk.Label(self,textvariable=self.status,style='Muted.TLabel',padding=(6,5)).grid(row=3,column=0,columnspan=3,sticky='ew')
        self.canvas.bind('<Configure>',lambda e:self.schedule())
        self.canvas.bind('<ButtonPress-1>',self._press)
        self.canvas.bind('<B1-Motion>',self._drag)
        self.canvas.bind('<ButtonRelease-1>',self._release)
        self.canvas.bind('<Double-Button-1>',lambda e:self.start_edit())
        self.canvas.bind('<MouseWheel>',self._wheel)
        self.canvas.bind('<Shift-MouseWheel>',lambda e:self._wheel(e,horizontal=True))
        self.canvas.bind('<KeyPress>',self._type)
        for key,delta in [('Left',(0,-1)),('Right',(0,1)),('Up',(-1,0)),('Down',(1,0))]:
            self.canvas.bind('<'+key+'>',lambda e,d=delta:self._navigate(d,bool(e.state&1)))
        self.canvas.bind('<Home>',lambda e:self.select(self.active[0],0))
        self.canvas.bind('<End>',lambda e:self.select(self.active[0],self.column_count-1))
        self.canvas.bind('<Control-Home>',lambda e:self.select(0,0))
        self.canvas.bind('<Control-End>',lambda e:self.select(self.row_count-1,self.column_count-1))
        for key in ('Return','F2'):
            self.canvas.bind('<'+key+'>',lambda e:self.start_edit())
        self.canvas.bind('<Tab>',lambda e:self._navigate((0,-1 if e.state&1 else 1),False))
        self.canvas.bind('<Delete>',lambda e:self.clear_selection())
        for key,action in [('c',self.copy),('v',self.paste),('a',self.select_all),('z',self.undo),('y',self.redo)]:
            self.canvas.bind('<Control-'+key+'>',lambda e,fn=action:self._shortcut(fn))
        self.top.bind('<Button-1>',self._select_column)
        self.left.bind('<Button-1>',self._select_row)
        self.corner.bind('<Button-1>',lambda e:self.select_all())
        self.bind('<Destroy>',self._destroyed,add='+')
        self.set_data(data or [],rows=rows,columns=columns)

    @property
    def row_count(self):return len(self.data)
    @property
    def column_count(self):return len(self.data[0]) if self.data else 0
    def set_data(self,data,*,rows=None,columns=None):
        self.finish_edit(False)
        values=[[str(value) if value is not None else '' for value in row] for row in data]
        nr=max(1,rows or 0,len(values));nc=max(1,columns or 0,max(map(len,values),default=0),len(self.headers))
        self._check_size(nr,nc)
        self.data=[(values[r] if r<len(values) else [])+['']*(nc-(len(values[r]) if r<len(values) else 0)) for r in range(nr)]
        self.active=self.anchor=(0,0);self.selection={(0,0)};self._undo.clear();self._redo.clear()
        self._regions();self.schedule();self._status()
    def get_data(self):return [row[:] for row in self.data]
    def get_cell(self,row,column):return self.data[row][column]
    def set_cell(self,row,column,value):
        if row<0 or column<0:raise IndexError('Cell coordinates must be nonnegative')
        self._ensure_size(row+1,column+1)
        self._apply([(row,column,str(value))])
    def get_selection(self):return sorted(self.selection)
    def _check_size(self,rows,columns):
        if rows*columns>self.max_cells:raise ValueError(f'表格最多支持 {self.max_cells:,} 个单元格')
    def _ensure_size(self,rows,columns):
        rows=max(rows,self.row_count);columns=max(columns,self.column_count);self._check_size(rows,columns)
        for row in self.data:row.extend(['']*(columns-len(row)))
        self.data.extend([['']*columns for _ in range(rows-self.row_count)])
        self._regions()
    def _regions(self):
        width=self.column_count*self.cw;height=self.row_count*self.rh
        self.canvas.configure(scrollregion=(0,0,width,height))
        self.top.configure(scrollregion=(0,0,width,self.rh))
        self.left.configure(scrollregion=(0,0,self.px(45),height))
    def schedule(self):
        if not self._closing and self._draw_job is None:self._draw_job=self.after_idle(self._draw)
    def _xscroll(self,first,last):
        self.hbar.set(first,last);self.top.xview_moveto(first);self.schedule()
    def _yscroll(self,first,last):
        self.vbar.set(first,last);self.left.yview_moveto(first);self.schedule()
    def xview(self,*args):
        if args:self.finish_edit()
        return self.canvas.xview(*args)
    def yview(self,*args):
        if args:self.finish_edit()
        return self.canvas.yview(*args)
    def _wheel(self,event,horizontal=False):
        self.finish_edit()
        if horizontal:self.canvas.xview_scroll(-int(event.delta/120)*2,'units')
        else:self.canvas.yview_scroll(-int(event.delta/120)*2,'units')
        return 'break'
    def _fit_text(self,value):
        value=value.replace('\r\n',' ↵ ').replace('\n',' ↵ ').replace('\t','    ')
        available=self.cw-self.px(16)
        if self.font.measure(value)<=available:return value
        lo,hi=0,len(value)
        while lo<hi:
            middle=(lo+hi+1)//2
            if self.font.measure(value[:middle]+'…')<=available:lo=middle
            else:hi=middle-1
        return value[:lo]+'…'
    def _draw(self):
        self._draw_job=None
        if self._closing:return
        c=PALETTE
        for canvas in (self.canvas,self.top,self.left,self.corner):canvas.delete('all')
        x0=self.canvas.canvasx(0);y0=self.canvas.canvasy(0)
        first_col=max(0,int(x0//self.cw));first_row=max(0,int(y0//self.rh))
        last_col=min(self.column_count,math.ceil((x0+self.canvas.winfo_width())/self.cw)+1)
        last_row=min(self.row_count,math.ceil((y0+self.canvas.winfo_height())/self.rh)+1)
        for r in range(first_row,last_row):
            y=r*self.rh
            self.left.create_rectangle(0,y,self.px(45),y+self.rh,fill=c['selected'] if r==self.active[0] else c['sidebar'],outline=c['border'])
            self.left.create_text(self.px(22),y+self.rh/2,text=str(r+1),font=self.font,fill=c['blue'] if r==self.active[0] else c['muted'])
            for col in range(first_col,last_col):
                x=col*self.cw;selected=(r,col) in self.selection
                self.canvas.create_rectangle(x,y,x+self.cw,y+self.rh,fill=c['selected'] if selected else c['bg'],outline=c['border'])
                self.canvas.create_text(x+self.px(8),y+self.rh/2,text=self._fit_text(self.data[r][col]),anchor='w',font=self.font,fill=c['fg'])
        for col in range(first_col,last_col):
            x=col*self.cw
            self.top.create_rectangle(x,0,x+self.cw,self.rh,fill=c['selected'] if col==self.active[1] else c['sidebar'],outline=c['border'])
            title=self.headers[col] if col<len(self.headers) else column_name(col)
            self.top.create_text(x+self.cw/2,self.rh/2,text=self._fit_text(title),font=self.font,fill=c['blue'] if col==self.active[1] else c['muted'])
        self.corner.create_rectangle(0,0,self.px(45),self.rh,fill=c['sidebar'],outline=c['border'])
        self.corner.create_text(self.px(23),self.rh/2,text='▦',font=self.font,fill=c['muted'])
        r,col=self.active;x=col*self.cw;y=r*self.rh
        self.canvas.create_rectangle(x+1,y+1,x+self.cw-1,y+self.rh-1,outline=c['blue'],width=self.px(2))
        if self.editor is not None:
            self.editor.place(x=round(x-x0),y=round(y-y0),width=self.cw,height=self.rh)
    def _cell_at(self,x,y):
        col=min(self.column_count-1,max(0,int(self.canvas.canvasx(x)//self.cw)))
        row=min(self.row_count-1,max(0,int(self.canvas.canvasy(y)//self.rh)))
        return row,col
    @staticmethod
    def _rectangle(a,b):
        return {(r,c) for r in range(min(a[0],b[0]),max(a[0],b[0])+1) for c in range(min(a[1],b[1]),max(a[1],b[1])+1)}
    def select(self,row,column,*,extend=False,add=False):
        self.finish_edit()
        row=min(self.row_count-1,max(0,row));column=min(self.column_count-1,max(0,column));cell=(row,column)
        if extend:
            self.selection=(self.selection if add else set())|self._rectangle(self.anchor,cell)
        elif add:
            if cell in self.selection and len(self.selection)>1:self.selection.remove(cell)
            else:self.selection.add(cell)
            self.anchor=cell
        else:self.selection={cell};self.anchor=cell
        self.active=cell;self.see(row,column);self.canvas.focus_set();self._changed_selection()
        return 'break'
    def _changed_selection(self):
        self._status();self.schedule();self.event_generate('<<SheetSelect>>',when='tail')
    def _status(self,message=''):
        row,col=self.active
        self.status.set(f'{column_name(col)}{row+1}  ·  已选 {len(self.selection)} 格'+('  ·  '+message if message else ''))
    def see(self,row,column):
        x=column*self.cw;y=row*self.rh;x0=self.canvas.canvasx(0);y0=self.canvas.canvasy(0)
        width=self.canvas.winfo_width();height=self.canvas.winfo_height()
        if x<x0:self.canvas.xview_moveto(x/(self.column_count*self.cw))
        elif x+self.cw>x0+width:self.canvas.xview_moveto((x+self.cw-width)/(self.column_count*self.cw))
        if y<y0:self.canvas.yview_moveto(y/(self.row_count*self.rh))
        elif y+self.rh>y0+height:self.canvas.yview_moveto((y+self.rh-height)/(self.row_count*self.rh))
    def _press(self,event):
        self.finish_edit();self.canvas.focus_set()
        cell=self._cell_at(event.x,event.y)
        shift=bool(event.state&1);control=bool(event.state&4)
        before=self.selection.copy()
        self.select(*cell,extend=shift,add=control)
        self._drag_anchor=self.anchor if shift else cell
        self._drag_base=before if control else set()
        self._previous_grab=self.canvas.grab_current();self.canvas.grab_set()
        return 'break'
    def _drag(self,event):
        if event.y<0:self.canvas.yview_scroll(-1,'units')
        elif event.y>self.canvas.winfo_height():self.canvas.yview_scroll(1,'units')
        if event.x<0:self.canvas.xview_scroll(-1,'units')
        elif event.x>self.canvas.winfo_width():self.canvas.xview_scroll(1,'units')
        cell=self._cell_at(event.x,event.y)
        self.selection=self._drag_base|self._rectangle(self._drag_anchor,cell)
        self.active=cell;self._changed_selection()
        return 'break'
    def _release(self,event=None):
        if self.canvas.grab_current() is self.canvas:
            self.canvas.grab_release()
            if self._previous_grab is not None and self._previous_grab.winfo_exists():self._previous_grab.grab_set()
        self._previous_grab=None
        return 'break'
    def _navigate(self,delta,extend=False):
        return self.select(self.active[0]+delta[0],self.active[1]+delta[1],extend=extend)
    def _select_column(self,event):
        self.finish_edit();col=min(self.column_count-1,max(0,int(self.top.canvasx(event.x)//self.cw)))
        self.selection={(r,col) for r in range(self.row_count)};self.active=self.anchor=(0,col)
        self.canvas.focus_set();self._changed_selection();return 'break'
    def _select_row(self,event):
        self.finish_edit();row=min(self.row_count-1,max(0,int(self.left.canvasy(event.y)//self.rh)))
        self.selection={(row,c) for c in range(self.column_count)};self.active=self.anchor=(row,0)
        self.canvas.focus_set();self._changed_selection();return 'break'
    def select_all(self):
        self.finish_edit();self.selection=self._rectangle((0,0),(self.row_count-1,self.column_count-1))
        self.canvas.focus_set();self._changed_selection();return 'break'
    def _type(self,event):
        if event.state&4 or not event.char or not event.char.isprintable():return
        return self.start_edit(event.char)
    def start_edit(self,initial=None):
        self.finish_edit();row,col=self.active;self.see(row,col)
        self.editing_cell=self.active
        self.editor=ttk.Entry(self.canvas)
        self.editor.insert(0,self.data[row][col] if initial is None else initial)
        if initial is None:self.editor.selection_range(0,'end')
        self.editor.icursor('end')
        self.editor.bind('<Return>',lambda e:self._end_edit((1,0)))
        self.editor.bind('<Tab>',lambda e:self._end_edit((0,-1 if e.state&1 else 1)))
        self.editor.bind('<Escape>',lambda e:self._end_edit(None,False))
        self.editor.bind('<FocusOut>',lambda e:self.finish_edit())
        self.schedule();self.update_idletasks();self.editor.focus_set()
        return 'break'
    def _end_edit(self,delta=None,commit=True):
        self.finish_edit(commit)
        if delta:self._navigate(delta)
        else:self.canvas.focus_set()
        return 'break'
    def finish_edit(self,commit=True):
        if self.editor is None:return
        editor=self.editor;cell=self.editing_cell;self.editor=None;self.editing_cell=None
        value=editor.get();editor.destroy()
        if commit and cell is not None:self._apply([(*cell,value)])
    def _apply(self,values,record=True):
        changes=[]
        for row,column,value in values:
            previous=self.data[row][column]
            if previous!=value:
                changes.append((row,column,previous,value));self.data[row][column]=value
        if changes:
            if record:self._undo.append(changes);self._undo=self._undo[-100:];self._redo.clear()
            self.schedule();self.event_generate('<<SheetChanged>>',when='tail')
        return changes
    def copy(self):
        self.finish_edit()
        if not self.selection:return ''
        rows=[r for r,_ in self.selection];columns=[c for _,c in self.selection]
        # Tk's Windows clipboard renderer converts LF to CRLF. Passing CRLF
        # here produces CR CR LF in CF_UNICODETEXT and blank rows in Excel.
        output=io.StringIO(newline='');writer=csv.writer(output,delimiter='\t',lineterminator='\n')
        for r in range(min(rows),max(rows)+1):
            writer.writerow([self.data[r][c].replace('\r\n','\n').replace('\r','\n') if (r,c) in self.selection else '' for c in range(min(columns),max(columns)+1)])
        text=output.getvalue();self.clipboard_clear();self.clipboard_append(text)
        self._status('已复制；非连续选区的间隙保留为空格位')
        return text
    def paste(self,text=None):
        self.finish_edit()
        if text is None:text=self.clipboard_get()
        values=list(csv.reader(io.StringIO(text,newline=''),delimiter='\t'))
        if not values:return []
        width=max(map(len,values),default=0)
        if not width:return []
        row,column=self.active
        self._ensure_size(row+len(values),column+width)
        changes=[(row+i,column+j,value) for i,line in enumerate(values) for j,value in enumerate(line)]
        self._apply(changes)
        self.selection={(r,c) for r,c,_ in changes};self.anchor=self.active
        self._changed_selection();self._status(f'已粘贴 {len(values)} 行 × {width} 列')
        return changes
    def clear_selection(self):
        self.finish_edit();self._apply([(r,c,'') for r,c in self.selection]);self._status('已清空选区');return 'break'
    def undo(self):
        self.finish_edit()
        if self._undo:
            changes=self._undo.pop();self._apply([(r,c,old) for r,c,old,new in changes],record=False);self._redo.append(changes)
            self._status('已撤销')
        return 'break'
    def redo(self):
        self.finish_edit()
        if self._redo:
            changes=self._redo.pop();self._apply([(r,c,new) for r,c,old,new in changes],record=False);self._undo.append(changes)
            self._status('已重做')
        return 'break'
    def _shortcut(self,action):
        try:action()
        except (tk.TclError,ValueError,csv.Error) as error:self._status('操作未完成：'+str(error))
        return 'break'
    def _destroyed(self,event):
        if event.widget is not self:return
        self._closing=True
        if self._draw_job is not None:self.after_cancel(self._draw_job)
