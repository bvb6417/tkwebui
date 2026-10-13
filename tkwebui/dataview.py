"""Searchable, filterable and paginated native Treeview with CSV export."""
import csv
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog
from .popups import ThemedCombobox, ThemedMenu
from .extras import MenuButton
from .table import _sort_key
from .scrolling import AutoScrollbar

class DataTable(ttk.Frame):
    def __init__(self,master,*,columns,rows=(),page_size=10,height=8,**kwargs):
        super().__init__(master,**kwargs)
        self.columns=[dict(key=str(item['key']),text=str(item.get('text',item['key'])),width=int(item.get('width',140))) if isinstance(item,dict)
                      else dict(key=str(i),text=str(item),width=140) for i,item in enumerate(columns)]
        self.keys=[item['key'] for item in self.columns]
        if not self.keys or len(set(self.keys))!=len(self.keys):raise ValueError('表格列不能为空，且 key 必须唯一')
        self.page_size=max(1,int(page_size));self.page=0;self.filters={};self.sort_column=None;self.reverse=False
        self.records=[];self.filtered=[];self.selected=set();self._rendering=False;self._search_job=None;self._next_id=0
        self.dpi=self.winfo_fpixels('1i')/96
        self.query=tk.StringVar(self);self.column_choice=tk.StringVar(self,value=self.columns[0]['text']);self.filter_text=tk.StringVar(self)
        self.page_info=tk.StringVar(self);self.status=tk.StringVar(self)
        tools=ttk.Frame(self);tools.pack(fill='x',pady=(0,8))
        ttk.Label(tools,text='搜索').pack(side='left',padx=(0,6))
        self.search_entry=ttk.Entry(tools,textvariable=self.query,width=22);self.search_entry.pack(side='left',fill='x',expand=True)
        self.search_entry.bind('<Return>',lambda e:self.refresh(reset_page=True))
        ttk.Button(tools,text='清除筛选',command=self.clear_filters).pack(side='left',padx=6)
        columns_button=MenuButton(tools,text='列');columns_button.pack(side='right')
        self.column_menu=ThemedMenu(columns_button,tearoff=False);columns_button.configure(menu=self.column_menu)
        self.visible_vars={}
        for column in self.columns:
            var=tk.BooleanVar(self,value=True);self.visible_vars[column['key']]=var
            self.column_menu.add_checkbutton(label=column['text'],variable=var,command=self._columns_changed)
        self.column_menu.add_separator();self.column_menu.add_command(label='恢复列布局',command=self.reset_layout)
        filters=ttk.Frame(self);filters.pack(fill='x',pady=(0,8))
        ThemedCombobox(filters,textvariable=self.column_choice,values=[column['text'] for column in self.columns],state='readonly',width=12).pack(side='left')
        ttk.Entry(filters,textvariable=self.filter_text,width=18).pack(side='left',padx=6,fill='x',expand=True)
        ttk.Button(filters,text='按列精确筛选',command=self._apply_filter).pack(side='left')
        area=ttk.Frame(self);area.pack(fill='both',expand=True);area.rowconfigure(0,weight=1);area.columnconfigure(0,weight=1)
        self.tree=ttk.Treeview(area,columns=self.keys,show='headings',selectmode='extended',height=height)
        self.tree.grid(row=0,column=0,sticky='nsew')
        for column in self.columns:
            key=column['key'];self.tree.heading(key,text=column['text'],command=lambda k=key:self.sort_by(k))
            self.tree.column(key,width=round(column['width']*self.dpi),minwidth=60,stretch=key==self.keys[-1])
        vbar=AutoScrollbar(area,command=self.tree.yview);vbar.grid(row=0,column=1,sticky='ns')
        hbar=AutoScrollbar(area,orient='horizontal',command=self.tree.xview);hbar.grid(row=1,column=0,sticky='ew')
        self.tree.configure(yscrollcommand=vbar.set,xscrollcommand=hbar.set)
        self.tree.bind('<<TreeviewSelect>>',self._capture_selection)
        self.tree.bind('<Button-3>',self._context)
        foot=ttk.Frame(self);foot.pack(fill='x',pady=(8,0))
        self.first=ttk.Button(foot,text='|‹',width=3,command=lambda:self.goto_page(0));self.first.pack(side='left')
        self.prev=ttk.Button(foot,text='‹',width=3,command=lambda:self.goto_page(self.page-1));self.prev.pack(side='left',padx=4)
        ttk.Label(foot,textvariable=self.page_info,style='Muted.TLabel').pack(side='left',padx=6)
        self.next=ttk.Button(foot,text='›',width=3,command=lambda:self.goto_page(self.page+1));self.next.pack(side='left',padx=4)
        self.last=ttk.Button(foot,text='›|',width=3,command=lambda:self.goto_page(self.page_count-1));self.last.pack(side='left')
        self.page_size_var=tk.StringVar(self,value=str(self.page_size))
        sizes=ThemedCombobox(foot,textvariable=self.page_size_var,values=['10','20','50','100'],state='readonly',width=5)
        sizes.pack(side='right');sizes.bind('<<ComboboxSelected>>',lambda e:self.set_page_size(int(self.page_size_var.get())))
        ttk.Label(foot,text='每页',style='Muted.TLabel').pack(side='right',padx=5)
        ttk.Label(self,textvariable=self.status,style='Muted.TLabel',padding=(0,6)).pack(fill='x')
        self._query_trace=self.query.trace_add('write',self._search_changed)
        self.bind('<Destroy>',self._cleanup,add='+');self.set_rows(rows)
    @property
    def page_count(self):return max(1,(len(self.filtered)+self.page_size-1)//self.page_size)
    def set_rows(self,rows):
        converted=[]
        for index,row in enumerate(rows):
            values=list(row)
            if len(values)!=len(self.keys):raise ValueError('每行的单元格数必须与列数一致')
            converted.append({'id':str(index),'values':values})
        self.records=converted;self._next_id=len(converted);self.selected.clear();self.page=0;self.refresh()
    def insert_row(self,values):
        if len(values)!=len(self.keys):raise ValueError('列数不匹配')
        key=str(self._next_id);self._next_id+=1;self.records.append({'id':key,'values':list(values)});self.refresh();return key
    def _search_changed(self,*_):
        if self._search_job is not None:self.after_cancel(self._search_job)
        self._search_job=self.after(150,lambda:self.refresh(reset_page=True))
    def search(self,text):self.query.set(text);self.refresh(reset_page=True)
    def filter_column(self,key,value):
        if key not in self.keys:raise KeyError(key)
        self.filters[key]=str(value).casefold();self.refresh(reset_page=True)
    def _apply_filter(self):
        column=next(c for c in self.columns if c['text']==self.column_choice.get())
        self.filter_column(column['key'],self.filter_text.get())
    def clear_filters(self):
        self.filters.clear();self.query.set('');self.filter_text.set('');self.refresh(reset_page=True)
    def sort_by(self,key,reverse=None):
        if key not in self.keys:raise KeyError(key)
        self.reverse=(not self.reverse if key==self.sort_column else False) if reverse is None else bool(reverse)
        self.sort_column=key;self.refresh(reset_page=True)
        self.event_generate('<<DataTableSorted>>',when='tail')
    def refresh(self,reset_page=False):
        if self._search_job is not None:self.after_cancel(self._search_job);self._search_job=None
        self._capture_selection()
        query=self.query.get().casefold().strip();filtered=[]
        for row in self.records:
            values=row['values']
            if query and not any(query in str(value).casefold() for value in values):continue
            if any(str(values[self.keys.index(key)]).casefold()!=value for key,value in self.filters.items()):continue
            filtered.append(row)
        if self.sort_column is not None:
            index=self.keys.index(self.sort_column)
            filled=[r for r in filtered if str(r['values'][index]).strip()];empty=[r for r in filtered if not str(r['values'][index]).strip()]
            filtered=sorted(filled,key=lambda r:_sort_key(r['values'][index]),reverse=self.reverse)+empty
        self.filtered=filtered
        self.page=0 if reset_page else min(self.page,self.page_count-1)
        self._render()
    def _render(self):
        self._rendering=True
        try:
            self.tree.delete(*self.tree.get_children())
            rows=self.filtered[self.page*self.page_size:(self.page+1)*self.page_size]
            for row in rows:self.tree.insert('','end',iid=row['id'],values=row['values'])
            chosen=[row['id'] for row in rows if row['id'] in self.selected]
            if chosen:self.tree.selection_set(chosen)
            for column in self.columns:
                text=column['text']+(' ▼' if self.reverse else ' ▲') if column['key']==self.sort_column else column['text']
                self.tree.heading(column['key'],text=text)
            self.page_info.set(f'{self.page+1} / {self.page_count} 页 · {len(self.filtered)} 条')
            for button,disabled in [(self.first,self.page==0),(self.prev,self.page==0),(self.next,self.page==self.page_count-1),(self.last,self.page==self.page_count-1)]:
                button.state(['disabled'] if disabled else ['!disabled'])
            self.status.set(f'总计 {len(self.records)} 条 · 已选 {len(self.selected)} 条'+(' · 已应用筛选' if self.filters or self.query.get() else ''))
        finally:self._rendering=False
    def _capture_selection(self,event=None):
        if self._rendering:return
        visible=set(self.tree.get_children());self.selected.difference_update(visible);self.selected.update(self.tree.selection())
        self.selected.intersection_update(row['id'] for row in self.records)
        if event is not None:self.status.set(f'总计 {len(self.records)} 条 · 已选 {len(self.selected)} 条')
    def goto_page(self,page):
        self._capture_selection();self.page=max(0,min(self.page_count-1,int(page)));self._render()
    def set_page_size(self,value):
        self._capture_selection();self.page_size=max(1,int(value));self.page_size_var.set(str(self.page_size));self.page=0;self._render()
    def get_rows(self,scope='all'):
        self._capture_selection()
        if scope=='all':rows=self.records
        elif scope=='filtered':rows=self.filtered
        elif scope=='page':rows=self.filtered[self.page*self.page_size:(self.page+1)*self.page_size]
        elif scope=='selected':rows=[row for row in self.records if row['id'] in self.selected]
        else:raise ValueError('scope 应为 all / filtered / page / selected')
        return [row['values'][:] for row in rows]
    def set_visible_columns(self,keys):
        keys=list(keys)
        if not keys or len(set(keys))!=len(keys) or any(key not in self.keys for key in keys):raise ValueError('至少保留一个有效列，且不能重复')
        self.tree.configure(displaycolumns=keys)
        for key,var in self.visible_vars.items():var.set(key in keys)
    def _columns_changed(self):
        keys=[key for key,var in self.visible_vars.items() if var.get()]
        if not keys:
            keys=list(self.tree['displaycolumns']);self.status.set('至少保留一列')
            if keys==['#all']:keys=self.keys[:]
        self.set_visible_columns(keys)
    def reset_layout(self):
        self.set_visible_columns(self.keys)
        for column in self.columns:self.tree.column(column['key'],width=round(column['width']*self.dpi),stretch=column['key']==self.keys[-1])
    def export_csv(self,path=None,scope='filtered'):
        if path is None:path=filedialog.asksaveasfilename(parent=self,defaultextension='.csv',filetypes=[('CSV 文件','*.csv')])
        if not path:return None
        path=Path(path).expanduser().resolve()
        with path.open('w',encoding='utf-8-sig',newline='') as file:
            writer=csv.writer(file);writer.writerow([c['text'] for c in self.columns]);writer.writerows(self.get_rows(scope))
        self.status.set('已导出：'+path.name);return path
    def _move_column(self,key,delta):
        keys=list(self.tree['displaycolumns'])
        if keys==['#all']:keys=self.keys[:]
        index=keys.index(key);new=max(0,min(len(keys)-1,index+delta));keys.insert(new,keys.pop(index));self.set_visible_columns(keys)
    def _context(self,event):
        menu=ThemedMenu(self,tearoff=False)
        old=getattr(self,'_context_menu',None)
        if old is not None:old.destroy()
        self._context_menu=menu
        display=list(self.tree['displaycolumns']);display=self.keys if display==['#all'] else display
        identified=self.tree.identify_column(event.x)
        key=display[int(identified[1:])-1] if identified and identified!='#0' else None
        if key:
            menu.add_command(label='升序排列',command=lambda:self.sort_by(key,False));menu.add_command(label='降序排列',command=lambda:self.sort_by(key,True))
            menu.add_command(label='左移此列',command=lambda:self._move_column(key,-1));menu.add_command(label='右移此列',command=lambda:self._move_column(key,1))
            if len(display)>1:menu.add_command(label='隐藏此列',command=lambda:self.set_visible_columns([k for k in display if k!=key]))
        menu.add_separator();menu.add_command(label='恢复列布局',command=self.reset_layout)
        for scope,label in [('filtered','导出筛选结果'),('page','导出当前页'),('selected','导出选中行')]:
            menu.add_command(label=label,command=lambda s=scope:self.export_csv(scope=s))
        menu.tk_popup(event.x_root,event.y_root)
    def _cleanup(self,event):
        if event.widget is self:
            if self._search_job is not None:self.after_cancel(self._search_job)
            self.query.trace_remove('write',self._query_trace)
