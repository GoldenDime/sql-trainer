"""SQL-тренажёр: десктопное приложение (Tkinter + встроенный SQLite).

Запуск: python trainer.py  (или двойной щелчок по run.bat)
"""
import os
import queue
import re
import sys
import textwrap
import threading
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox, ttk

if sys.platform == 'win32':
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

import course
import engine
import theory
from progress import Progress

APP_TITLE = 'SQL-тренажёр'
LEVEL_STARS = {1: '★☆☆', 2: '★★☆', 3: '★★★'}
SQL_KEYWORDS = sorted(set('''
select from where and or not in is null as on join left right full inner outer cross using group by order having
limit offset distinct union all intersect except case when then else end with recursive insert into values update set
delete create table view index unique primary key foreign references default check constraint alter add column drop
rename to begin commit rollback transaction savepoint release trigger after before for each row instead of exists
between like glob asc desc over partition rows range unbounded preceding following current filter conflict do nothing
returning cascade restrict if replace explain query plan materialized lateral true false cast integer text real numeric
'''.split()))
SQL_FUNCS = sorted(set('''
count sum avg min max round coalesce nullif lower upper trim ltrim rtrim length substr substring replace instr
row_number rank dense_rank ntile lag lead first_value last_value nth_value cume_dist percent_rank date datetime julianday
strftime date_trunc date_part greatest least split_part median percentile_cont stddev variance corr string_agg group_concat
abs sqrt power ln exp floor ceil json_extract json_each json_set json_object json_array printf concat iif typeof
'''.split()))

def split_md_row(line):
    """Делит строку markdown-таблицы на ячейки; | внутри `кода` не считается разделителем."""
    cells, cur, in_code = [], [], False
    body = line.strip()
    if body.startswith('|'):
        body = body[1:]
    if body.endswith('|') and not body.endswith('\\|'):
        body = body[:-1]
    for ch in body:
        if ch == '`':
            in_code = not in_code
        if ch == '|' and not in_code:
            cells.append(''.join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    cells.append(''.join(cur).strip())
    return cells


SANDBOX_DEFAULT = {'shop': 'SELECT * FROM product;', 'market': 'SELECT * FROM users LIMIT 20;',
                   'uni': 'SELECT * FROM students;'}

C = {
    'bg': '#f6f7f9', 'panel': '#ffffff', 'accent': '#2f6fde', 'ok': '#1e8e3e', 'bad': '#c5221f', 'warn': '#b06000',
    'muted': '#6b7280', 'code_bg': '#f1f3f5', 'kw': '#1a4fbf', 'fn': '#7a3ea8', 'str': '#a3500b', 'num': '#0b7a6b',
    'comment': '#8a8f98', 'h1': '#111827', 'sel': '#dbe7ff',
}


def task_num(tid):
    num = tid[1:].lstrip('0')
    return '0' + num if num.startswith('.') else num


def fmt_value(v):
    if v is None:
        return 'NULL'
    if isinstance(v, float):
        if v == int(v) and abs(v) < 1e15:
            return str(int(v))
        return ('%.6f' % v).rstrip('0').rstrip('.')
    return str(v)


def pick_font(*names):
    fams = set(tkfont.families())
    for n in names:
        if n in fams:
            return n
    return names[-1]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry('1360x860')
        self.minsize(1000, 640)
        try:
            if sys.platform == 'win32':
                self.state('zoomed')
        except tk.TclError:
            pass
        self.configure(bg=C['bg'])

        self.progress = Progress()
        self.checker = engine.TaskChecker()
        self.mode = None          # 'theory' | 'task' | 'sandbox'
        self.current = None       # id задачи или модуля
        self.sandbox_db = 'shop'
        self.sandbox_conns = {}
        self.busy = False
        self.worker_conn = None
        self.results = queue.Queue()
        self.hint_shown = 0
        self.pending = []
        self._exp_loaded = None

        ui = pick_font('Segoe UI', 'Helvetica Neue', 'DejaVu Sans', 'Arial')
        mono = pick_font('Consolas', 'Cascadia Mono', 'JetBrains Mono', 'Menlo', 'DejaVu Sans Mono', 'Courier New')
        size = self.progress.data.get('font_size', 12)
        self.f_ui = tkfont.Font(family=ui, size=10)
        self.f_ui_b = tkfont.Font(family=ui, size=10, weight='bold')
        self.f_text = tkfont.Font(family=ui, size=11)
        self.f_text_b = tkfont.Font(family=ui, size=11, weight='bold')
        self.f_h1 = tkfont.Font(family=ui, size=16, weight='bold')
        self.f_h2 = tkfont.Font(family=ui, size=13, weight='bold')
        self.f_mono = tkfont.Font(family=mono, size=size)
        self.f_mono_s = tkfont.Font(family=mono, size=10)
        self.f_mono_b = tkfont.Font(family=mono, size=size, weight='bold')

        self._style()
        self._build()
        self._bind_keys()
        self.refresh_tree()
        self.update_header()
        self.after(50, self._warmup)
        self.after(200, lambda: self.main_pane.sashpos(0, max(330, int(self.winfo_width() * 0.24))))
        self.after(100, self._poll)
        self.protocol('WM_DELETE_WINDOW', self.on_close)

        cur = self.progress.data.get('current')
        if cur in course.TASKS:
            self.open_task(cur)
        else:
            self.open_theory(course.MODULES[0]['id'])

    # ------------------------------------------------------------ UI
    def _style(self):
        st = ttk.Style(self)
        if sys.platform != 'win32':
            st.theme_use('clam')
        st.configure('.', font=self.f_ui)
        st.configure('Treeview', rowheight=int(self.f_ui.metrics('linespace') * 1.6), font=self.f_ui)
        st.configure('Nav.Treeview', rowheight=int(self.f_ui.metrics('linespace') * 1.75), font=self.f_ui)
        st.configure('Treeview.Heading', font=self.f_ui_b)
        st.configure('Accent.TButton', font=self.f_ui_b)
        st.configure('Header.TLabel', font=self.f_ui_b, background=C['bg'])
        st.configure('Muted.TLabel', foreground=C['muted'], background=C['bg'])
        st.configure('TFrame', background=C['bg'])
        st.configure('TLabel', background=C['bg'])

    def _build(self):
        top = ttk.Frame(self, padding=(10, 6))
        top.pack(fill='x')
        for text, cmd in (('?', self.show_help), ('В PostgreSQL', self.export_pg), ('Прогресс', self.show_progress),
                          ('Схема БД', self.show_schema), ('Песочница', self.open_sandbox)):
            ttk.Button(top, text=text, command=cmd, width=len(text) + 2 if text != '?' else 3).pack(side='right', padx=2)
        self.btn_review = ttk.Button(top, text='Повторение', command=self.next_review)
        self.btn_review.pack(side='right', padx=2)
        ttk.Button(top, text='Продолжить ▶', style='Accent.TButton', command=self.continue_course).pack(side='right', padx=6)
        ttk.Label(top, text=APP_TITLE, font=self.f_h2).pack(side='left')
        self.lbl_rank = ttk.Label(top, text='', style='Header.TLabel')
        self.lbl_rank.pack(side='left', padx=(18, 0))
        self.pb = ttk.Progressbar(top, length=140, mode='determinate')
        self.pb.pack(side='left', padx=10)
        self.lbl_stat = ttk.Label(top, text='', style='Muted.TLabel')
        self.lbl_stat.pack(side='left')

        main = ttk.PanedWindow(self, orient='horizontal')
        main.pack(fill='both', expand=True, padx=8, pady=(0, 4))

        left = ttk.Frame(main)
        self.nav = ttk.Treeview(left, show='tree', style='Nav.Treeview', selectmode='browse')
        sb = ttk.Scrollbar(left, orient='vertical', command=self.nav.yview)
        self.nav.configure(yscrollcommand=sb.set)
        self.nav.pack(side='left', fill='both', expand=True)
        sb.pack(side='right', fill='y')
        self.nav.tag_configure('solved', foreground=C['ok'])
        self.nav.tag_configure('tried', foreground=C['warn'])
        self.nav.tag_configure('due', foreground=C['accent'])
        self.nav.tag_configure('module', font=self.f_ui_b)
        self.nav.tag_configure('theory', foreground=C['muted'])
        self.nav.bind('<<TreeviewSelect>>', self.on_nav)
        main.add(left, weight=1)
        self.main_pane = main

        right = ttk.PanedWindow(main, orient='vertical')
        main.add(right, weight=4)
        self.right = right

        # описание
        dframe = ttk.Frame(right)
        self.desc = tk.Text(dframe, wrap='word', font=self.f_text, bg=C['panel'], relief='flat', padx=16, pady=10,
                            highlightthickness=1, highlightbackground='#e2e5ea', cursor='arrow', spacing1=2, spacing3=2)
        dsb = ttk.Scrollbar(dframe, orient='vertical', command=self.desc.yview)
        self.desc.configure(yscrollcommand=dsb.set)
        self.desc.pack(side='left', fill='both', expand=True)
        dsb.pack(side='right', fill='y')
        self._desc_tags(self.desc)
        self.desc.bind('<1>', lambda e: self.desc.focus_set())
        self.desc.bind('<Configure>', self._on_desc_resize)
        self.desc.configure(state='disabled')
        right.add(dframe, weight=2)

        # редактор
        eframe = ttk.Frame(right)
        bar = ttk.Frame(eframe, padding=(0, 4))
        bar.pack(fill='x')
        self.btn_run = ttk.Button(bar, text='▶ Выполнить  F5', command=self.run_current)
        self.btn_run.pack(side='left')
        self.btn_check = ttk.Button(bar, text='✔ Проверить  F9', style='Accent.TButton', command=self.check_current)
        self.btn_check.pack(side='left', padx=4)
        self.btn_hint = ttk.Button(bar, text='Подсказка', command=self.show_hint)
        self.btn_hint.pack(side='left', padx=4)
        self.btn_sol = ttk.Button(bar, text='Решение', command=self.reveal_solution)
        self.btn_sol.pack(side='left')
        self.btn_next = ttk.Button(bar, text='Следующее →', command=self.next_task)
        self.btn_next.pack(side='left', padx=4)
        self.btn_stop = ttk.Button(bar, text='■ Стоп', command=self.stop_query, state='disabled')
        self.btn_stop.pack(side='left', padx=4)
        self.db_var = tk.StringVar(value='shop')
        self.db_box = ttk.Combobox(bar, textvariable=self.db_var, values=list(engine.DB_TITLES), width=9, state='readonly')
        self.db_box.bind('<<ComboboxSelected>>', self.on_sandbox_db)
        self.btn_reset = ttk.Button(bar, text='Сбросить базу', command=self.reset_sandbox)
        self.lbl_db = ttk.Label(bar, text='', style='Muted.TLabel')
        self.lbl_db.pack(side='right')

        edit_wrap = ttk.Frame(eframe)
        edit_wrap.pack(fill='both', expand=True)
        self.lines = tk.Text(edit_wrap, width=4, font=self.f_mono, bg='#eef0f3', fg=C['muted'], relief='flat',
                             state='disabled', padx=4, takefocus=0, cursor='arrow')
        self.lines.pack(side='left', fill='y')
        self.editor = tk.Text(edit_wrap, wrap='none', font=self.f_mono, undo=True, maxundo=-1, relief='flat',
                              bg='#ffffff', insertbackground='#111', selectbackground=C['sel'], padx=8, pady=6,
                              highlightthickness=1, highlightbackground='#d0d5dd', highlightcolor=C['accent'], tabs=('4c',))
        esb = ttk.Scrollbar(edit_wrap, orient='vertical', command=self._editor_scroll)
        self.editor.configure(yscrollcommand=lambda *a: (esb.set(*a), self._sync_lines()))
        self.editor.pack(side='left', fill='both', expand=True)
        esb.pack(side='right', fill='y')
        for tag, color in (('kw', C['kw']), ('fn', C['fn']), ('str', C['str']), ('num', C['num']), ('comment', C['comment'])):
            self.editor.tag_configure(tag, foreground=color)
        self.editor.tag_configure('kw', font=self.f_mono_b)
        self.editor.tag_raise('str')
        self.editor.tag_raise('comment')
        right.add(eframe, weight=2)

        # результаты
        self.nb = ttk.Notebook(right)
        self.res_grid = self._make_grid(self.nb)
        self.exp_grid = self._make_grid(self.nb)
        mframe = ttk.Frame(self.nb)
        self.msg = tk.Text(mframe, wrap='word', font=self.f_mono_s, bg=C['panel'], relief='flat', padx=10, pady=8)
        msb = ttk.Scrollbar(mframe, orient='vertical', command=self.msg.yview)
        self.msg.configure(yscrollcommand=msb.set)
        self.msg.pack(side='left', fill='both', expand=True)
        msb.pack(side='right', fill='y')
        self.msg.tag_configure('ok', foreground=C['ok'], font=self.f_text_b)
        self.msg.tag_configure('bad', foreground=C['bad'], font=self.f_text_b)
        self.msg.tag_configure('muted', foreground=C['muted'])
        self.msg.tag_configure('code', background=C['code_bg'])
        self.nb.add(self.res_grid['frame'], text='Результат')
        self.nb.add(self.exp_grid['frame'], text='Ожидаемый результат')
        self.nb.add(mframe, text='Сообщения')
        self.nb.bind('<<NotebookTabChanged>>', self.on_tab)
        right.add(self.nb, weight=2)

        self.status = ttk.Label(self, text='', style='Muted.TLabel', padding=(10, 2))
        self.status.pack(fill='x')

        self.editor.bind('<<Modified>>', self._on_modified)
        self._hl_job = None

    def _desc_tags(self, t):
        t.tag_configure('h1', font=self.f_h1, foreground=C['h1'], spacing1=6, spacing3=8)
        t.tag_configure('h2', font=self.f_h2, foreground=C['h1'], spacing1=10, spacing3=4)
        t.tag_configure('b', font=self.f_text_b)
        t.tag_configure('code', font=self.f_mono_s, background=C['code_bg'])
        t.tag_configure('block', font=self.f_mono_s, background=C['code_bg'], lmargin1=14, lmargin2=14, spacing1=0, spacing3=0)
        t.tag_configure('table', font=self.f_mono_s, lmargin1=8, lmargin2=8, spacing1=0, spacing3=0)
        t.tag_configure('table_b', font=tkfont.Font(family=self.f_mono_s.cget('family'), size=10, weight='bold'),
                        lmargin1=8, lmargin2=8, spacing1=0, spacing3=0)
        t.tag_configure('table_rule', font=self.f_mono_s, foreground='#c9ced6', lmargin1=8, spacing1=0, spacing3=0)
        t.tag_configure('bullet', lmargin1=12, lmargin2=28)
        t.tag_configure('muted', foreground=C['muted'])
        t.tag_configure('ok', foreground=C['ok'], font=self.f_text_b)
        t.tag_configure('warn', foreground=C['warn'])
        t.tag_configure('hint', background='#fff7e0', lmargin1=10, lmargin2=10)
        t.tag_configure('block_pg', font=self.f_mono_s, background='#eef4ff', lmargin1=14, lmargin2=14, spacing1=0, spacing3=0)
        t.tag_configure('block_bad', font=self.f_mono_s, background='#fdeeee', lmargin1=14, lmargin2=14, spacing1=0, spacing3=0)
        t.tag_configure('lbl', font=self.f_ui, foreground=C['muted'], lmargin1=14, spacing1=8, spacing3=1)
        t.tag_configure('lbl_pg', font=self.f_ui, foreground='#3559a8', lmargin1=14, spacing1=8, spacing3=1)
        t.tag_configure('lbl_bad', font=self.f_ui_b, foreground=C['bad'], lmargin1=14, spacing1=8, spacing3=1)
        t.tag_configure('link', font=self.f_ui_b, foreground=C['accent'], underline=True)
        t.tag_configure('footer', spacing1=18)

    def _make_grid(self, parent):
        frame = ttk.Frame(parent)
        info = ttk.Label(frame, text='', style='Muted.TLabel', padding=(6, 3))
        info.pack(fill='x')
        inner = ttk.Frame(frame)
        inner.pack(fill='both', expand=True)
        tree = ttk.Treeview(inner, show='headings')
        ys = ttk.Scrollbar(inner, orient='vertical', command=tree.yview)
        xs = ttk.Scrollbar(inner, orient='horizontal', command=tree.xview)
        tree.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        tree.grid(row=0, column=0, sticky='nsew')
        ys.grid(row=0, column=1, sticky='ns')
        xs.grid(row=1, column=0, sticky='ew')
        inner.rowconfigure(0, weight=1)
        inner.columnconfigure(0, weight=1)
        tree.tag_configure('odd', background='#f8f9fb')
        return {'frame': frame, 'tree': tree, 'info': info}

    def _bind_keys(self):
        for seq in ('<F5>', '<Control-Return>'):
            self.bind_all(seq, lambda e: (self.run_current(), 'break')[1])
        for seq in ('<F9>', '<Control-Shift-Return>'):
            self.bind_all(seq, lambda e: (self.check_current(), 'break')[1])
        self.editor.bind('<Control-Return>', lambda e: (self.run_current(), 'break')[1])
        self.editor.bind('<Control-Shift-Return>', lambda e: (self.check_current(), 'break')[1])
        self.editor.bind('<Tab>', self._tab)
        self.editor.bind('<Shift-Tab>', self._untab)
        self.editor.bind('<ISO_Left_Tab>', self._untab)
        self.editor.bind('<Return>', self._newline)
        self.editor.bind('<Control-slash>', self._toggle_comment)
        self.editor.bind('<Control-a>', lambda e: (self.editor.tag_add('sel', '1.0', 'end-1c'), 'break')[1])
        self.bind_all('<Control-equal>', lambda e: self._zoom(1))
        self.bind_all('<Control-plus>', lambda e: self._zoom(1))
        self.bind_all('<Control-minus>', lambda e: self._zoom(-1))

    # ------------------------------------------------------------ редактор
    def _editor_scroll(self, *args):
        self.editor.yview(*args)
        self._sync_lines()

    def _sync_lines(self):
        n = int(self.editor.index('end-1c').split('.')[0])
        cur = int(self.lines.index('end-1c').split('.')[0]) if self.lines.get('1.0', 'end-1c') else 0
        if cur != n:
            self.lines.configure(state='normal', width=max(3, len(str(n)) + 1))
            self.lines.delete('1.0', 'end')
            self.lines.insert('1.0', '\n'.join(str(i) for i in range(1, n + 1)))
            self.lines.configure(state='disabled')
        self.lines.yview_moveto(self.editor.yview()[0])

    def _on_modified(self, _e=None):
        if self.editor.edit_modified():
            self.editor.edit_modified(False)
            if self._hl_job:
                self.after_cancel(self._hl_job)
            self._hl_job = self.after(120, self.highlight)
            self._sync_lines()

    def highlight(self):
        self._hl_job = None
        text = self.editor.get('1.0', 'end-1c')
        for tag in ('kw', 'fn', 'str', 'num', 'comment'):
            self.editor.tag_remove(tag, '1.0', 'end')
        if len(text) > 60000:
            return

        def add(tag, m):
            self.editor.tag_add(tag, f'1.0+{m.start()}c', f'1.0+{m.end()}c')

        for m in re.finditer(r'\b[A-Za-z_]+\b', text):
            w = m.group(0).lower()
            if w in SQL_KEYWORDS:
                add('kw', m)
            elif w in SQL_FUNCS and text[m.end():m.end() + 1] == '(':
                add('fn', m)
        for m in re.finditer(r'\b\d+(\.\d+)?\b', text):
            add('num', m)
        for m in re.finditer(r"'(?:[^']|'')*'?", text):
            add('str', m)
        for m in re.finditer(r'--[^\n]*|/\*.*?(\*/|$)', text, flags=re.S):
            add('comment', m)

    def _tab(self, _e):
        try:
            first = int(self.editor.index('sel.first').split('.')[0])
            last = int(self.editor.index('sel.last').split('.')[0])
            for ln in range(first, last + 1):
                self.editor.insert(f'{ln}.0', '    ')
        except tk.TclError:
            self.editor.insert('insert', '    ')
        return 'break'

    def _untab(self, _e):
        try:
            first = int(self.editor.index('sel.first').split('.')[0])
            last = int(self.editor.index('sel.last').split('.')[0])
        except tk.TclError:
            first = last = int(self.editor.index('insert').split('.')[0])
        for ln in range(first, last + 1):
            line = self.editor.get(f'{ln}.0', f'{ln}.end')
            k = len(line) - len(line.lstrip(' '))
            if k:
                self.editor.delete(f'{ln}.0', f'{ln}.{min(4, k)}')
        return 'break'

    def _newline(self, _e):
        line = self.editor.get('insert linestart', 'insert')
        indent = re.match(r'[ \t]*', line).group(0)
        self.editor.insert('insert', '\n' + indent)
        self.editor.see('insert')
        return 'break'

    def _toggle_comment(self, _e):
        try:
            first = int(self.editor.index('sel.first').split('.')[0])
            last = int(self.editor.index('sel.last').split('.')[0])
        except tk.TclError:
            first = last = int(self.editor.index('insert').split('.')[0])
        lines = [self.editor.get(f'{ln}.0', f'{ln}.end') for ln in range(first, last + 1)]
        uncomment = all(l.lstrip().startswith('--') or not l.strip() for l in lines)
        for ln, l in zip(range(first, last + 1), lines):
            if uncomment:
                i = l.find('--')
                if i >= 0:
                    cut = 3 if l[i + 2:i + 3] == ' ' else 2
                    self.editor.delete(f'{ln}.{i}', f'{ln}.{i + cut}')
            elif l.strip():
                self.editor.insert(f'{ln}.0', '-- ')
        return 'break'

    def _zoom(self, d):
        size = max(8, min(28, self.f_mono.cget('size') + d))
        for f in (self.f_mono, self.f_mono_b):
            f.configure(size=size)
        self.progress.data['font_size'] = size
        self.progress.save()

    def set_editor(self, text):
        self.editor.delete('1.0', 'end')
        self.editor.insert('1.0', text)
        self.editor.edit_reset()
        self.editor.edit_modified(True)
        self._on_modified()
        self.editor.mark_set('insert', 'end')

    def editor_text(self):
        return self.editor.get('1.0', 'end-1c')

    # ------------------------------------------------------------ навигация
    def task_label(self, t):
        st = self.progress.status(t['id'])
        due = t['id'] in self._due
        icon = '↻' if due else {'solved': '✔', 'tried': '•'}.get(st, '○')
        return f'{icon} {task_num(t["id"])}  {t["title"]}', ('due' if due else st if st in ('solved', 'tried') else '')

    def refresh_tree(self):
        self._due = set(self.progress.due_reviews(course.ORDER))
        opened = {iid for iid in self.nav.get_children('') if self.nav.item(iid, 'open')}
        opened_th = {iid + ':theory' for iid in self.nav.get_children('')
                     if self.nav.exists(iid + ':theory') and self.nav.item(iid + ':theory', 'open')}
        sel = self.nav.selection()
        self.nav.delete(*self.nav.get_children(''))
        for m in course.MODULES:
            ids = [t['id'] for t in m['tasks']]
            done = self.progress.solved_count(ids)
            self.nav.insert('', 'end', iid=m['id'], text=f'{m["title"]}   {done}/{len(ids)}', open=m['id'] in opened,
                            tags=('module', 'solved') if done == len(ids) else ('module',))
            pages = theory.pages(m['id'])
            th = m['id'] + ':theory'
            self.nav.insert(m['id'], 'end', iid=th, text=f'§  Теория · {len(pages)} стр.', tags=('theory',),
                            open=th in opened_th)
            for k, (ptitle, _md) in enumerate(pages):
                self.nav.insert(th, 'end', iid=f'{th}:{k}', text=f'{k + 1}. {ptitle}', tags=('theory',))
            for t in m['tasks']:
                label, tag = self.task_label(t)
                self.nav.insert(m['id'], 'end', iid=t['id'], text=label, tags=(tag,) if tag else ())
        if sel and self.nav.exists(sel[0]):
            self._select_silently(sel[0])

    def update_tree_item(self, tid):
        self._due = set(self.progress.due_reviews(course.ORDER))
        t = course.TASKS[tid]
        label, tag = self.task_label(t)
        self.nav.item(tid, text=label, tags=(tag,) if tag else ())
        m = next(m for m in course.MODULES if any(x['id'] == tid for x in m['tasks']))
        ids = [x['id'] for x in m['tasks']]
        done = self.progress.solved_count(ids)
        self.nav.item(m['id'], text=f'{m["title"]}   {done}/{len(ids)}',
                      tags=('module', 'solved') if done == len(ids) else ('module',))

    def _select_silently(self, iid):
        self._suppress_nav = True
        parent = self.nav.parent(iid)
        while parent:
            self.nav.item(parent, open=True)
            parent = self.nav.parent(parent)
        self.nav.selection_set(iid)
        self.nav.see(iid)
        self.after(10, lambda: setattr(self, '_suppress_nav', False))

    def on_nav(self, _e=None):
        if getattr(self, '_suppress_nav', False):
            return
        sel = self.nav.selection()
        if not sel:
            return
        iid = sel[0]
        if iid in course.TASKS:
            self.open_task(iid, select=False)
        elif ':theory' in iid:
            parts = iid.split(':')
            if len(parts) == 2:
                self.nav.item(iid, open=True)
            self.open_theory(parts[0], int(parts[2]) if len(parts) > 2 else 0, select=False)
        else:
            self.nav.item(iid, open=True)
            self.open_theory(iid, select=False)

    def update_header(self):
        total = len(course.ORDER)
        solved = self.progress.solved_count(course.ORDER)
        rank, nxt = self.progress.rank()
        xp = self.progress.data['xp']
        self.lbl_rank.configure(text=f'{rank} · {xp} XP')
        self.pb.configure(maximum=total, value=solved)
        streak = self.progress.streak()
        self.lbl_stat.configure(text=f'{solved}/{total} · серия {streak} дн.' + (f' · до звания {nxt - xp} XP' if nxt else ''))
        due = len(self.progress.due_reviews(course.ORDER))
        self.btn_review.configure(text=f'Повторение ({due})')

    # ------------------------------------------------------------ режимы
    def _save_current_sql(self):
        if self.mode == 'task' and self.current:
            self.progress.save_sql(self.current, self.editor_text())
        elif self.mode in ('sandbox', 'theory'):
            self.progress.data['sandbox'][self.sandbox_db] = self.editor_text()

    def _set_task_buttons(self, task_mode):
        state = 'normal' if task_mode else 'disabled'
        for b in (self.btn_check, self.btn_hint, self.btn_sol, self.btn_next):
            b.configure(state=state)
        if task_mode:
            self.db_box.pack_forget()
            self.btn_reset.pack_forget()
        else:
            self.db_box.pack(side='left', padx=(12, 4))
            self.btn_reset.pack(side='left')

    def _sash(self, desc_share):
        self.update_idletasks()
        h = self.right.winfo_height()
        if h > 100:
            self.right.sashpos(0, int(h * desc_share))
            self.right.sashpos(1, int(h * (desc_share + (1 - desc_share) * 0.45)))

    def open_theory(self, mid, page=0, select=True):
        self._save_current_sql()
        m = next(x for x in course.MODULES if x['id'] == mid)
        pages = theory.pages(mid)
        page = max(0, min(page, len(pages) - 1))
        was_theory = self.mode == 'theory'
        self.mode, self.current = 'theory', mid
        self.progress.mark_theory(mid)
        title, md = pages[page]
        head = f'_{m["title"]}  ·  теория, страница {page + 1} из {len(pages)}_'

        def show():
            self.render_desc(head + '\n' + md.strip('\n'), runnable=True)
            self._theory_footer(m, pages, page)
        show()
        self._rerender = show
        self._set_task_buttons(False)
        if not was_theory or self.sandbox_db != 'uni':
            self.switch_sandbox_db('uni', load_text=True)
        self.lbl_db.configure(text='примеры: база uni')
        if select:
            self._select_silently(f'{mid}:theory:{page}')
        if not was_theory:
            self.after(30, lambda: self._sash(0.58))

    def _theory_footer(self, m, pages, page):
        t = self.desc
        t.configure(state='normal')
        t.insert('end', '\n', 'footer')
        if page > 0:
            self._link(t, f'← {pages[page - 1][0]}', lambda: self.open_theory(m['id'], page - 1))
            t.insert('end', '      ')
        if page + 1 < len(pages):
            self._link(t, f'{pages[page + 1][0]} →', lambda: self.open_theory(m['id'], page + 1))
        elif m['tasks']:
            first = next((x['id'] for x in m['tasks'] if self.progress.status(x['id']) != 'solved'), m['tasks'][0]['id'])
            self._link(t, 'К заданиям модуля →', lambda: self.open_task(first))
        t.insert('end', '\n')
        t.configure(state='disabled')

    def _link(self, t, text, callback):
        self._link_no = getattr(self, '_link_no', 0) + 1
        tag = f'lnk{self._link_no}'
        t.insert('end', text, ('link', tag))
        t.tag_bind(tag, '<Button-1>', lambda _e: (callback(), 'break')[1])
        t.tag_bind(tag, '<Enter>', lambda _e: t.configure(cursor='hand2'))
        t.tag_bind(tag, '<Leave>', lambda _e: t.configure(cursor='arrow'))

    def run_example(self, code):
        if self.busy:
            self.set_status('Дождитесь окончания предыдущего запроса.')
            return
        if self.sandbox_db != 'uni':
            self.progress.data['sandbox'][self.sandbox_db] = self.editor_text()
            self.sandbox_db = 'uni'
            self.db_var.set('uni')
        self.set_editor(code.strip('\n') + '\n')
        self.nb.select(0)
        self.run_current()

    def open_sandbox(self):
        self._save_current_sql()
        self.mode, self.current = 'sandbox', None
        self._rerender = None
        self.render_desc("""# Песочница
Свободный режим. Выберите базу справа от кнопок. Здесь можно делать что угодно: INSERT, UPDATE, CREATE TABLE —
изменения живут, пока открыта программа, кнопка «Сбросить базу» возвращает исходные данные.

Полезное: `SELECT name FROM sqlite_master WHERE type = 'table';` — список таблиц, `PRAGMA table_info(orders);` — столбцы,
`EXPLAIN QUERY PLAN SELECT ...` — план запроса.""")
        self._set_task_buttons(False)
        self.switch_sandbox_db(self.sandbox_db, load_text=True)
        self.lbl_db.configure(text='')
        self.nav.selection_remove(self.nav.selection())
        self.after(30, lambda: self._sash(0.22))

    def switch_sandbox_db(self, db, load_text=False):
        if self.mode in ('sandbox', 'theory') and not load_text:
            self.progress.data['sandbox'][self.sandbox_db] = self.editor_text()
        self.sandbox_db = db
        self.db_var.set(db)
        if load_text:
            default = SANDBOX_DEFAULT[db]
            self.set_editor(self.progress.data['sandbox'].get(db) or default)

    def on_sandbox_db(self, _e=None):
        self.progress.data['sandbox'][self.sandbox_db] = self.editor_text()
        self.sandbox_db = self.db_var.get()
        default = SANDBOX_DEFAULT[self.sandbox_db]
        self.set_editor(self.progress.data['sandbox'].get(self.sandbox_db) or default)

    def reset_sandbox(self):
        conn = self.sandbox_conns.pop(self.sandbox_db, None)
        if conn:
            conn.close()
        self.set_status(f'База {self.sandbox_db} в песочнице сброшена к исходным данным.')

    def open_task(self, tid, select=True):
        self._save_current_sql()
        t = course.TASKS[tid]
        self.mode, self.current = 'task', tid
        self.hint_shown = 0
        self.progress.data['current'] = tid
        self.progress.save()
        self._set_task_buttons(True)
        self.render_task(t)
        self.set_editor(self.progress.task(tid)['sql'] or '-- ' + t['title'] + '\n')
        self.lbl_db.configure(text=f'база: {engine.DB_TITLES[t["db"]]}')
        self.clear_grid(self.res_grid, '')
        self.clear_grid(self.exp_grid, 'Откройте вкладку — покажу, какая таблица должна получиться.')
        self._exp_loaded = None
        self.msg_clear()
        if select:
            self._select_silently(tid)
        self.after(30, lambda: self._sash(0.30))
        self.editor.focus_set()
        if self.nb.index('current') == 1:
            self.load_expected()

    def render_task(self, t):
        rec = self.progress.task(t['id'])
        kind = {'select': 'запрос', 'dml': 'изменение данных', 'ddl': 'структура БД'}[t.get('kind', 'select')]
        st = {'solved': 'решено', 'tried': f'попыток: {rec["attempts"]}', 'new': 'не начато'}[rec['status']]
        lines = [f'# {task_num(t["id"])}  {t["title"]}',
                 f'_{LEVEL_STARS[t["level"]]}  ·  {kind}  ·  база {t["db"]}'
                 + (f'  ·  лекция {t["lecture"]}' if t.get('lecture') else '') + f'  ·  {st}_', '', t['text']]
        if t.get('ordered'):
            lines += ['', '_Порядок строк проверяется._']
        if t.get('kind') in ('dml', 'ddl'):
            lines += ['', '_Каждый запуск идёт на свежей копии базы. Проверка: ваш скрипт → проверочные вставки/запрос._']
        self.render_desc('\n'.join(lines))
        self._rerender = lambda: self.render_task(t)

    # ------------------------------------------------------------ разметка
    def render_desc(self, md, runnable=False):
        t = self.desc
        t.configure(state='normal')
        t.delete('1.0', 'end')
        for tag in t.tag_names():
            if tag.startswith('lnk'):
                t.tag_delete(tag)
        lines = md.strip('\n').split('\n')
        i, in_code, lang, buf = 0, False, '', []
        while i < len(lines):
            line = lines[i]
            if line.strip().startswith('```'):
                if not in_code:
                    in_code, lang, buf = True, line.strip()[3:].strip().lower(), []
                else:
                    in_code = False
                    self._code_block(t, lang, buf, runnable)
                i += 1
                continue
            if in_code:
                buf.append(line)
            elif line.startswith('|'):
                rows = []
                while i < len(lines) and lines[i].startswith('|'):
                    cells = split_md_row(lines[i])
                    if not all(re.fullmatch(r':?-{2,}:?', c) for c in cells if c):
                        rows.append([c.replace('`', '').replace('**', '') for c in cells])
                    i += 1
                self._table(t, rows)
                continue
            elif line.startswith('# '):
                t.insert('end', line[2:] + '\n', 'h1')
            elif line.startswith('## '):
                t.insert('end', line[3:] + '\n', 'h2')
            elif line.startswith('- '):
                t.insert('end', '•  ', 'bullet')
                self._inline(t, line[2:], 'bullet')
                t.insert('end', '\n', 'bullet')
            elif line.startswith('_') and line.endswith('_') and len(line) > 1:
                t.insert('end', line[1:-1] + '\n', 'muted')
            else:
                self._inline(t, line)
                t.insert('end', '\n')
            i += 1
        if in_code:
            self._code_block(t, lang, buf, runnable)
        t.configure(state='disabled')
        t.yview_moveto(0)

    def _table(self, t, rows):
        ncol = max(len(r) for r in rows)
        rows = [r + [''] * (ncol - len(r)) for r in rows]
        cw = max(1, self.f_mono_s.measure('0'))
        width = t.winfo_width()
        if width < 200:
            width = 900
        avail = max(40, int((width - 2 * 16 - 40) / cw))
        gap = 2
        natural = [max(len(r[k]) for r in rows) for k in range(ncol)]
        widths = list(natural)
        if sum(natural) + gap * (ncol - 1) > avail:
            room = avail - gap * (ncol - 1)
            mins = [min(natural[k], max(8, min(18, max((len(w) for r in rows for w in r[k].split()), default=1))))
                    for k in range(ncol)]
            extra = max(0, room - sum(mins))
            want = [natural[k] - mins[k] for k in range(ncol)]
            total_want = sum(want) or 1
            widths = [mins[k] + int(extra * want[k] / total_want) for k in range(ncol)]
        wrapped = [[textwrap.wrap(r[k], widths[k], break_long_words=True, break_on_hyphens=False) or [''] for k in range(ncol)]
                   for r in rows]
        multi = any(len(c) > 1 for r in wrapped for c in r)
        line_w = sum(widths) + gap * (ncol - 1)
        for n, r in enumerate(wrapped):
            height = max(len(c) for c in r)
            for h in range(height):
                text = (' ' * gap).join((r[k][h] if h < len(r[k]) else '').ljust(widths[k]) for k in range(ncol))
                t.insert('end', text.rstrip() + '\n', 'table_b' if n == 0 else 'table')
            if n == 0 or (multi and n + 1 < len(wrapped)):
                t.insert('end', '─' * line_w + '\n', 'table_rule')
        t.insert('end', '\n')

    def _on_desc_resize(self, e):
        w = e.width
        if abs(w - getattr(self, '_desc_w', 0)) < 40:
            return
        self._desc_w = w
        if getattr(self, '_resize_job', None):
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(250, self._rerender_desc)

    def _rerender_desc(self):
        self._resize_job = None
        fn = getattr(self, '_rerender', None)
        if fn:
            pos = self.desc.yview()[0]
            fn()
            self.desc.yview_moveto(pos)

    def _code_block(self, t, lang, buf, runnable):
        code = '\n'.join(buf)
        tag = 'block'
        if lang in ('sql', 'sql-error') and runnable:
            t.insert('end', '', 'lbl')
            self._link(t, '▶ Выполнить пример', lambda c=code: self.run_example(c))
            t.insert('end', '   на базе uni' + ('  ·  в конце будет ошибка — так задумано' if lang == 'sql-error' else '') + '\n',
                     'lbl')
        elif lang == 'pg':
            t.insert('end', 'PostgreSQL  ·  во встроенном SQLite не выполнится\n', 'lbl_pg')
            tag = 'block_pg'
        elif lang == 'bad':
            t.insert('end', '✗ Так не надо\n', 'lbl_bad')
            tag = 'block_bad'
        for ln in buf:
            t.insert('end', ln + '\n', tag)

    def _inline(self, t, s, base=None):
        parts = re.split(r'(\*\*[^*]+\*\*|`[^`]+`)', s)
        for p in parts:
            if not p:
                continue
            if p.startswith('**'):
                t.insert('end', p[2:-2], ('b', base) if base else 'b')
            elif p.startswith('`'):
                t.insert('end', p[1:-1], ('code', base) if base else 'code')
            else:
                t.insert('end', p, base or ())

    # ------------------------------------------------------------ сетки
    def clear_grid(self, g, info):
        tree = g['tree']
        tree.delete(*tree.get_children())
        tree['columns'] = ()
        g['info'].configure(text=info)

    def fill_grid(self, g, cols, rows, info):
        tree = g['tree']
        tree.delete(*tree.get_children())
        ids = [f'c{i}' for i in range(len(cols))]
        tree['columns'] = ids
        cw = self.f_ui.measure('0')
        for i, c in enumerate(cols):
            sample = [len(str(r[i])) if r[i] is not None else 4 for r in rows[:200]]
            width = max([len(str(c))] + sample) * cw + 24
            tree.heading(ids[i], text=str(c), anchor='w')
            tree.column(ids[i], width=min(max(width, 60), 420), stretch=False, anchor='w')
        for n, r in enumerate(rows):
            vals = [fmt_value(v) for v in r]
            tree.insert('', 'end', values=vals, tags=('odd',) if n % 2 else ())
        g['info'].configure(text=info)

    def msg_clear(self):
        self.msg.delete('1.0', 'end')

    def msg_add(self, text, tag=None):
        self.msg.insert('end', text + '\n', tag or ())
        self.msg.see('end')

    def set_status(self, text):
        self.status.configure(text=text)

    # ------------------------------------------------------------ выполнение
    def _start(self, label, fn):
        if self.busy:
            self.pending.append((label, fn))
            self.set_status('В очереди: дождитесь окончания предыдущего запроса (или нажмите «Стоп»).')
            return
        self.busy = True
        self.btn_stop.configure(state='normal')
        self.btn_run.configure(state='disabled')
        self.set_status(label)
        self.config(cursor='watch')

        def work():
            try:
                out = fn()
            except Exception as e:  # noqa: BLE001
                out = ('exception', e)
            self.results.put(out)

        threading.Thread(target=work, daemon=True).start()

    def _poll(self):
        try:
            while True:
                out = self.results.get_nowait()
                self.busy = False
                self.worker_conn = None
                self.btn_stop.configure(state='disabled')
                self.btn_run.configure(state='normal')
                self.config(cursor='')
                kind = out[0]
                if kind == 'exception':
                    self.msg_clear()
                    self.msg_add('Внутренняя ошибка: ' + str(out[1]), 'bad')
                    self.nb.select(2)
                    self.set_status('Ошибка.')
                elif kind == 'run':
                    self.show_run(out[1])
                elif kind == 'check':
                    self.show_check(*out[1:])
                elif kind == 'expected':
                    self.show_expected(*out[1:])
                elif kind == 'warm':
                    self.set_status('Готово. F5 — выполнить, F9 — проверить.')
                if self.pending and not self.busy:
                    label, fn = self.pending.pop(0)
                    self._start(label, fn)
        except queue.Empty:
            pass
        self.after(80, self._poll)

    def _warmup(self):
        self.set_status('Готовлю учебные базы (первый запуск может занять несколько секунд)…')

        def work():
            for name in engine.DB_TITLES:
                engine.db_path(name)
            self.results.put(('warm',))
        threading.Thread(target=work, daemon=True).start()

    def stop_query(self):
        conn = self.worker_conn
        if conn is not None:
            try:
                conn.interrupt()
            except Exception:  # noqa: BLE001
                pass
        self.set_status('Останавливаю…')

    def sandbox_conn(self, db):
        if db not in self.sandbox_conns:
            self.sandbox_conns[db] = engine.open_fresh(db)
        return self.sandbox_conns[db]

    def run_current(self):
        sql = self.editor_text()
        if not sql.strip():
            return
        self._save_current_sql()
        if self.mode == 'task':
            task = course.TASKS[self.current]

            def fn():
                conn = self.checker.connection_for(task)
                self.worker_conn = conn
                try:
                    return ('run', engine.run_script(conn, sql))
                finally:
                    conn.close()
        else:
            db = self.sandbox_db

            def fn():
                conn = self.sandbox_conn(db)
                self.worker_conn = conn
                res = engine.run_script(conn, sql)
                if res.error and conn.in_transaction:
                    try:
                        conn.execute('ROLLBACK')
                        res.messages.append('Транзакция не завершилась из-за ошибки — тренажёр откатил её (ROLLBACK).')
                    except Exception:  # noqa: BLE001
                        pass
                return ('run', res)
        self._start('Выполняю…', fn)

    def show_run(self, res):
        self.msg_clear()
        if res.error:
            if res.has_result:
                self.fill_grid(self.res_grid, res.columns, res.rows, 'Результат последнего успешного оператора')
            self.msg_add('Ошибка', 'bad')
            self.msg_add(res.error)
            for m in res.messages:
                self.msg_add(m, 'muted')
            self.nb.select(2)
            self.set_status('Ошибка в запросе.')
            return
        for m in res.messages:
            self.msg_add(m, 'muted')
        if res.has_result:
            info = f'строк: {len(res.rows)}' + (' (обрезано)' if res.truncated else '') + f' · {res.elapsed * 1000:.0f} мс'
            self.fill_grid(self.res_grid, res.columns, res.rows, info)
            self.nb.select(0)
            self.set_status(info)
        else:
            self.clear_grid(self.res_grid, 'Оператор не вернул таблицу.')
            self.nb.select(2)
            self.set_status(f'Выполнено за {res.elapsed * 1000:.0f} мс')

    def check_current(self):
        if self.mode != 'task':
            self.set_status('Проверка доступна в заданиях. Здесь — просто «Выполнить».')
            return
        sql = self.editor_text()
        if not sql.strip():
            return
        self._save_current_sql()
        task = course.TASKS[self.current]

        def fn():
            ok, msg, got = self.checker.check(task, sql)
            return ('check', task['id'], ok, msg, got)
        self._start('Проверяю…', fn)

    def show_check(self, tid, ok, msg, got):
        if tid != self.current:
            return
        task = course.TASKS[tid]
        was_solved = self.progress.status(tid) == 'solved'
        gained = self.progress.record_attempt(tid, ok, task['level'])
        run = got.get('run')
        self.msg_clear()
        if run is not None and run.has_result and task.get('kind', 'select') == 'select':
            self.fill_grid(self.res_grid, run.columns, run.rows, f'строк: {len(run.rows)}')
        elif got.get('cols') is not None and task.get('kind') != 'select':
            self.fill_grid(self.res_grid, got['cols'], got['rows'], 'Проверочный запрос после вашего скрипта')
        if ok:
            self.msg_add('✔ ' + msg + (f'  +{gained} XP' if gained else ''), 'ok')
            if was_solved and not gained:
                self.msg_add('Задание уже было решено раньше.', 'muted')
            nxt = self._next_unsolved(tid)
            if nxt:
                self.msg_add(f'Дальше: {course.TASKS[nxt]["title"]} — кнопка «Следующее →».', 'muted')
            self.set_status('Верно!' + (f' +{gained} XP' if gained else ''))
        else:
            self.msg_add('✘ Пока не то', 'bad')
            self.msg_add(msg)
            self.set_status('Есть расхождения — смотрите «Сообщения» и «Ожидаемый результат».')
        self.nb.select(2)
        self.update_tree_item(tid)
        self.update_header()
        self.render_task(task)

    def on_tab(self, _e=None):
        if self.mode == 'task' and self.nb.index('current') == 1:
            self.load_expected()

    def load_expected(self):
        if self._exp_loaded == self.current:
            return
        task = course.TASKS[self.current]

        def fn():
            exp = self.checker.expected(task)
            return ('expected', task['id'], exp)
        self._start('Готовлю ожидаемый результат…', fn)

    def show_expected(self, tid, exp):
        if tid != self.current:
            return
        self._exp_loaded = tid
        task = course.TASKS[tid]
        if exp.get('cols') is None:
            self.clear_grid(self.exp_grid, 'В этом задании проверяются ограничения: правильные вставки проходят, неправильные — отклоняются.')
        else:
            note = 'Проверочный запрос после правильного скрипта: ' + task['check'] if task.get('kind') != 'select' else \
                f'строк: {len(exp["rows"])}' + (' · порядок важен' if task.get('ordered') else ' · порядок не важен') + \
                ' · имена столбцов могут быть любыми'
            self.fill_grid(self.exp_grid, exp['cols'], exp['rows'], note)
        self.set_status('')

    def show_hint(self):
        if self.mode != 'task':
            return
        task = course.TASKS[self.current]
        hints = task['hints'] or ['Разбейте задачу на шаги: какая таблица, какие строки, какая группировка, что вывести.']
        if self.hint_shown >= len(hints):
            self.msg_add('Подсказки закончились. Можно открыть решение.', 'muted')
            self.nb.select(2)
            return
        h = hints[self.hint_shown]
        self.hint_shown += 1
        if self.progress.status(task['id']) != 'solved':
            self.progress.use_hint(task['id'])
        self.msg_add(f'Подсказка {self.hint_shown}/{len(hints)}: {h}', 'muted')
        self.nb.select(2)

    def reveal_solution(self):
        if self.mode != 'task':
            return
        task = course.TASKS[self.current]
        if self.progress.status(task['id']) != 'solved':
            if not messagebox.askyesno(APP_TITLE, 'Показать эталонное решение?\nЗадание можно будет засчитать, но без опыта.'):
                return
            self.progress.reveal(task['id'])
        self.msg_clear()
        self.msg_add('Эталонное решение (возможны и другие правильные варианты):', 'muted')
        self.msg_add(task['solution'], 'code')
        self.msg_add('\nПерепишите его своими руками в редакторе и нажмите «Проверить».', 'muted')
        self.nb.select(2)

    # ------------------------------------------------------------ переходы
    def _next_unsolved(self, after=None):
        order = course.ORDER
        start = order.index(after) + 1 if after in order else 0
        for tid in order[start:] + order[:start]:
            if self.progress.status(tid) != 'solved':
                return tid
        return None

    def next_task(self):
        if self.mode == 'task':
            order = course.ORDER
            i = order.index(self.current)
            if i + 1 < len(order):
                self.open_task(order[i + 1])

    def continue_course(self):
        nxt = self._next_unsolved(self.current if self.mode == 'task' else None)
        if nxt:
            m = next(m for m in course.MODULES if any(t['id'] == nxt for t in m['tasks']))
            if m['id'] not in self.progress.data['theory']:
                self.open_theory(m['id'])
                self.set_status('Сначала теория модуля. Затем «Продолжить» откроет задание.')
                return
            self.open_task(nxt)
        else:
            messagebox.showinfo(APP_TITLE, 'Все задания решены! Остаётся повторение и песочница.')

    def next_review(self):
        due = self.progress.due_reviews(course.ORDER)
        if not due:
            messagebox.showinfo(APP_TITLE, 'На сегодня повторять нечего. Решённые задания вернутся сюда через 2, 6, 15, 35 дней.')
            return
        tid = due[0]
        self.open_task(tid)
        self.set_editor('-- Повторение: решите заново, не подглядывая в прошлое решение\n')
        self.set_status(f'Повторение: осталось {len(due)}')

    # ------------------------------------------------------------ окна
    def show_schema(self):
        db = course.TASKS[self.current]['db'] if self.mode == 'task' else self.sandbox_db
        win = tk.Toplevel(self)
        win.title(f'Схема: {engine.DB_TITLES[db]}')
        win.geometry('560x640')
        tree = ttk.Treeview(win, columns=('type', 'info'), show='tree headings')
        tree.heading('#0', text='таблица / столбец')
        tree.heading('type', text='тип')
        tree.heading('info', text='ключи')
        tree.column('#0', width=240)
        tree.column('type', width=90)
        tree.column('info', width=200)
        sb = ttk.Scrollbar(win, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side='left', fill='both', expand=True)
        sb.pack(side='right', fill='y')
        for t, n, cols in engine.table_overview(db):
            node = tree.insert('', 'end', text=f'{t}  ({n} строк)', open=n < 50 or len(cols) < 8)
            for name, typ, notnull, pk, fk in cols:
                info = ', '.join(x for x in ('PK' if pk else '', 'NOT NULL' if notnull and not pk else '', f'→ {fk}' if fk else '') if x)
                tree.insert(node, 'end', text=name, values=(typ, info))

        def insert_name(_e):
            iid = tree.focus()
            if iid:
                name = tree.item(iid, 'text').split()[0]
                self.editor.insert('insert', name)
                self.editor.focus_set()
        tree.bind('<Double-1>', insert_name)
        ttk.Label(win, text='Двойной щелчок — вставить имя в редактор', style='Muted.TLabel').pack(side='bottom')

    def show_progress(self):
        win = tk.Toplevel(self)
        win.title('Прогресс')
        win.geometry('620x620')
        rank, _ = self.progress.rank()
        d = self.progress.data
        head = (f'{rank} · {d["xp"]} XP · решено {self.progress.solved_count(course.ORDER)} из {len(course.ORDER)} · '
                f'дней занятий: {len(d["days"])} · серия: {self.progress.streak()}')
        ttk.Label(win, text=head, font=self.f_ui_b, padding=10).pack(fill='x')
        tree = ttk.Treeview(win, columns=('done', 'tried', 'bar'), show='tree headings')
        tree.heading('#0', text='модуль')
        tree.heading('done', text='решено')
        tree.heading('tried', text='в работе')
        tree.heading('bar', text='')
        tree.column('#0', width=300)
        tree.column('done', width=70, anchor='center')
        tree.column('tried', width=70, anchor='center')
        tree.column('bar', width=140)
        tree.pack(fill='both', expand=True, padx=10)
        for m in course.MODULES:
            ids = [t['id'] for t in m['tasks']]
            done = self.progress.solved_count(ids)
            tried = sum(1 for i in ids if self.progress.status(i) == 'tried')
            bar = '█' * round(10 * done / len(ids)) + '░' * (10 - round(10 * done / len(ids)))
            tree.insert('', 'end', text=m['title'], values=(f'{done}/{len(ids)}', tried, bar))
        bottom = ttk.Frame(win, padding=10)
        bottom.pack(fill='x')
        ttk.Label(bottom, text=f'Файл прогресса: {self.progress.path}', style='Muted.TLabel').pack(side='left')

        def reset():
            if messagebox.askyesno(APP_TITLE, 'Сбросить весь прогресс? Старый файл сохранится как progress.json.bak', parent=win):
                try:
                    os.replace(self.progress.path, self.progress.path + '.bak')
                except OSError:
                    pass
                self.progress = Progress()
                self.refresh_tree()
                self.update_header()
                win.destroy()
        ttk.Button(bottom, text='Сбросить прогресс', command=reset).pack(side='right')

    def export_pg(self):
        db = course.TASKS[self.current]['db'] if self.mode == 'task' else self.sandbox_db
        path = filedialog.asksaveasfilename(title='Экспорт в PostgreSQL', defaultextension='.sql',
                                            initialfile=f'trainer_{db}.sql', filetypes=[('SQL', '*.sql')])
        if not path:
            return
        engine.export_postgres(db, path)
        messagebox.showinfo(APP_TITLE, f'Сохранено: {path}\n\nЗагрузка в PostgreSQL:\n'
                                       f'  createdb -U postgres trainer\n  psql -U postgres -d trainer -f "{os.path.basename(path)}"\n\n'
                                       f'Таблицы лежат в схеме {db}. Перед запросами выполните:\n  SET search_path TO {db};')

    def show_help(self):
        messagebox.showinfo(APP_TITLE, 'Горячие клавиши\n\n'
                            'F5 / Ctrl+Enter — выполнить\nF9 / Ctrl+Shift+Enter — проверить\n'
                            'Ctrl+/ — закомментировать строки\nTab / Shift+Tab — отступ\nCtrl+= / Ctrl+- — размер шрифта\n\n'
                            'В теории «▶ Выполнить пример» переносит пример в редактор и выполняет на базе uni.\n'
                            'Если выполняются несколько операторов, показывается результат последнего SELECT.\n'
                            'Прогресс сохраняется автоматически в progress.json.')

    def on_close(self):
        try:
            self._save_current_sql()
            self.progress.save()
        finally:
            self.destroy()


def main():
    try:
        app = App()
        import sqlite3
        if sqlite3.sqlite_version_info < (3, 39):
            messagebox.showwarning(APP_TITLE, f'Встроенный SQLite {sqlite3.sqlite_version} старый: RIGHT/FULL JOIN и часть '
                                              'JSON-операторов не заработают. Поставьте Python 3.12+ с python.org.')
        app.mainloop()
    except Exception:  # noqa: BLE001
        import traceback
        log = os.path.join(engine.APP_DIR, 'error.log')
        with open(log, 'w', encoding='utf-8') as f:
            traceback.print_exc(file=f)
        try:
            messagebox.showerror(APP_TITLE, f'Программа упала. Подробности в {log}')
        except Exception:  # noqa: BLE001
            pass
        raise


if __name__ == '__main__':
    main()
