"""Выполнение SQL, PostgreSQL-подобные функции для SQLite и проверка ответов."""
import math
import os
import re
import sqlite3
import statistics
import threading
import time
from datetime import date, datetime, timedelta

import data

APP_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(APP_DIR, 'cache')
MAX_ROWS = 5000


# ---------- функции в стиле PostgreSQL ----------

def _parse_dt(v):
    if v is None:
        return None
    s = str(v).strip()
    for fmt, n in (('%Y-%m-%d %H:%M:%S', 19), ('%Y-%m-%dT%H:%M:%S', 19), ('%Y-%m-%d %H:%M', 16), ('%Y-%m-%d', 10)):
        try:
            return datetime.strptime(s[:n], fmt)
        except ValueError:
            continue
    return None


def f_date_trunc(unit, v):
    dt = _parse_dt(v)
    if dt is None or unit is None:
        return None
    u = str(unit).lower()
    if u == 'year':
        d = date(dt.year, 1, 1)
    elif u == 'quarter':
        d = date(dt.year, (dt.month - 1) // 3 * 3 + 1, 1)
    elif u == 'month':
        d = date(dt.year, dt.month, 1)
    elif u == 'week':
        d = dt.date() - timedelta(days=dt.weekday())
    elif u == 'day':
        d = dt.date()
    elif u == 'hour':
        return dt.strftime('%Y-%m-%d %H:00:00')
    else:
        raise ValueError(f"date_trunc: неизвестная единица '{unit}'")
    return d.isoformat()


def f_date_part(unit, v):
    dt = _parse_dt(v)
    if dt is None or unit is None:
        return None
    u = str(unit).lower()
    if u == 'year':
        return dt.year
    if u == 'quarter':
        return (dt.month - 1) // 3 + 1
    if u == 'month':
        return dt.month
    if u == 'day':
        return dt.day
    if u == 'hour':
        return dt.hour
    if u == 'minute':
        return dt.minute
    if u == 'dow':
        return (dt.weekday() + 1) % 7  # как в PostgreSQL: 0 = воскресенье
    if u == 'isodow':
        return dt.weekday() + 1
    if u == 'week':
        return dt.isocalendar()[1]
    if u == 'doy':
        return dt.timetuple().tm_yday
    if u == 'epoch':
        return int((dt - datetime(1970, 1, 1)).total_seconds())
    raise ValueError(f"date_part: неизвестная единица '{unit}'")


def f_greatest(*args):
    vals = [a for a in args if a is not None]
    return max(vals) if vals else None


def f_least(*args):
    vals = [a for a in args if a is not None]
    return min(vals) if vals else None


def f_split_part(s, delim, n):
    if s is None:
        return None
    parts = str(s).split(delim)
    return parts[n - 1] if 0 < n <= len(parts) else ''


def f_lower(s):
    return None if s is None else str(s).lower()


def f_upper(s):
    return None if s is None else str(s).upper()


def f_initcap(s):
    return None if s is None else str(s).title()


def f_concat(*args):
    return ''.join('' if a is None else str(a) for a in args)


def f_regexp_like(s, pattern):
    if s is None or pattern is None:
        return None
    return 1 if re.search(pattern, str(s)) else 0


def f_regexp(pattern, s):  # для оператора s REGEXP pattern
    if s is None or pattern is None:
        return None
    return 1 if re.search(pattern, str(s)) else 0


def f_regexp_replace(s, pattern, repl):
    if s is None:
        return None
    return re.sub(pattern, repl, str(s))


class _Collect:
    def __init__(self):
        self.vals = []

    def step(self, v, *rest):
        if v is not None:
            try:
                self.vals.append(float(v))
            except (TypeError, ValueError):
                pass


class Median(_Collect):
    def finalize(self):
        return statistics.median(self.vals) if self.vals else None


class PercentileCont(_Collect):
    p = None

    def step(self, v, p=0.5):
        self.p = p
        super().step(v)

    def finalize(self):
        if not self.vals:
            return None
        xs = sorted(self.vals)
        p = float(self.p if self.p is not None else 0.5)
        k = (len(xs) - 1) * p
        lo, hi = math.floor(k), math.ceil(k)
        return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


class Stddev(_Collect):
    def finalize(self):
        return statistics.stdev(self.vals) if len(self.vals) > 1 else None


class Variance(_Collect):
    def finalize(self):
        return statistics.variance(self.vals) if len(self.vals) > 1 else None


class Corr:
    def __init__(self):
        self.xs, self.ys = [], []

    def step(self, y, x):
        if x is not None and y is not None:
            self.xs.append(float(x))
            self.ys.append(float(y))

    def finalize(self):
        if len(self.xs) < 2:
            return None
        try:
            return statistics.correlation(self.xs, self.ys)
        except statistics.StatisticsError:
            return None


class BoolAnd:
    def __init__(self):
        self.v = None

    def step(self, x):
        if x is not None:
            self.v = bool(x) if self.v is None else (self.v and bool(x))

    def finalize(self):
        return None if self.v is None else int(self.v)


class BoolOr(BoolAnd):
    def step(self, x):
        if x is not None:
            self.v = bool(x) if self.v is None else (self.v or bool(x))


class StringAgg:
    def __init__(self):
        self.parts = []
        self.sep = ','

    def step(self, v, sep=','):
        self.sep = sep
        if v is not None:
            self.parts.append(str(v))

    def finalize(self):
        return self.sep.join(self.parts) if self.parts else None


def _has_function(conn, name):
    try:
        return conn.execute('SELECT 1 FROM pragma_function_list WHERE name = ?', (name,)).fetchone() is not None
    except sqlite3.Error:
        return False


def install_functions(conn):
    conn.create_function('date_trunc', 2, f_date_trunc, deterministic=True)
    conn.create_function('date_part', 2, f_date_part, deterministic=True)
    conn.create_function('greatest', -1, f_greatest, deterministic=True)
    conn.create_function('least', -1, f_least, deterministic=True)
    conn.create_function('split_part', 3, f_split_part, deterministic=True)
    conn.create_function('lower', 1, f_lower, deterministic=True)
    conn.create_function('upper', 1, f_upper, deterministic=True)
    conn.create_function('initcap', 1, f_initcap, deterministic=True)
    conn.create_function('regexp_like', 2, f_regexp_like, deterministic=True)
    conn.create_function('regexp', 2, f_regexp, deterministic=True)
    conn.create_function('regexp_replace', 3, f_regexp_replace, deterministic=True)
    conn.create_aggregate('median', 1, Median)
    conn.create_aggregate('percentile_cont', 2, PercentileCont)
    conn.create_aggregate('stddev', 1, Stddev)
    conn.create_aggregate('stddev_samp', 1, Stddev)
    conn.create_aggregate('variance', 1, Variance)
    conn.create_aggregate('corr', 2, Corr)
    conn.create_aggregate('bool_and', 1, BoolAnd)
    conn.create_aggregate('bool_or', 1, BoolOr)
    for name, n, fn in (('sqrt', 1, lambda x: None if x is None else math.sqrt(x)),
                        ('power', 2, lambda x, y: None if x is None or y is None else math.pow(x, y)),
                        ('ln', 1, lambda x: None if x is None else math.log(x)),
                        ('exp', 1, lambda x: None if x is None else math.exp(x)),
                        ('floor', 1, lambda x: None if x is None else math.floor(x)),
                        ('ceil', 1, lambda x: None if x is None else math.ceil(x)),
                        ('log10', 1, lambda x: None if x is None else math.log10(x))):
        if not _has_function(conn, name):
            conn.create_function(name, n, fn, deterministic=True)
    if not _has_function(conn, 'concat'):
        conn.create_function('concat', -1, f_concat, deterministic=True)
    if not _has_function(conn, 'string_agg'):
        conn.create_aggregate('string_agg', 2, StringAgg)


# ---------- базы ----------

DB_TITLES = {'shop': 'shop — магазин из лекций', 'market': 'market — маркетплейс 2025',
             'uni': 'uni — университет и онлайн-школа (примеры теории)'}


_DB_LOCK = threading.Lock()


def db_path(name):
    with _DB_LOCK:
        return _db_path(name)


def _db_path(name):
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, f'{name}.sqlite')
    ok = False
    if os.path.exists(path):
        try:
            c = sqlite3.connect(path)
            ok = c.execute('PRAGMA user_version').fetchone()[0] == data.DATA_VERSION
            c.close()
        except sqlite3.Error:
            ok = False
    if not ok:
        tmp = path + '.tmp'
        if os.path.exists(tmp):
            os.remove(tmp)
        data.build_file(name, tmp)
        os.replace(tmp, path)
    return path


def _prepare(conn):
    conn.isolation_level = None
    conn.execute('PRAGMA foreign_keys = ON')
    install_functions(conn)
    return conn


def open_fresh(name):
    """Изолированная копия базы в памяти: можно менять что угодно."""
    src = sqlite3.connect(db_path(name))
    mem = sqlite3.connect(':memory:', check_same_thread=False)
    src.backup(mem)
    src.close()
    return _prepare(mem)


def open_readonly(name):
    path = db_path(name).replace('\\', '/')
    conn = sqlite3.connect(f'file:{path}?mode=ro', uri=True, check_same_thread=False)
    return _prepare(conn)


# ---------- выполнение ----------

def split_statements(script):
    """Делит скрипт на операторы с учётом строк, комментариев и тел триггеров."""
    stmts, buf, i, n = [], [], 0, len(script)
    quote = None
    while i < n:
        ch = script[i]
        nxt = script[i + 1] if i + 1 < n else ''
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
        elif ch in ("'", '"', '`'):
            quote = ch
            buf.append(ch)
        elif ch == '-' and nxt == '-':
            j = script.find('\n', i)
            j = n if j == -1 else j
            buf.append(script[i:j])
            i = j
            continue
        elif ch == '/' and nxt == '*':
            j = script.find('*/', i + 2)
            j = n if j == -1 else j + 2
            buf.append(script[i:j])
            i = j
            continue
        else:
            buf.append(ch)
            if ch == ';' and sqlite3.complete_statement(''.join(buf)):
                text = ''.join(buf).strip()
                if _strip_comments(text).strip().strip(';').strip():
                    stmts.append(text)
                buf = []
        i += 1
    text = ''.join(buf).strip()
    if _strip_comments(text).strip().strip(';').strip():
        stmts.append(text)
    return stmts


def _strip_comments(s):
    s = re.sub(r'/\*.*?\*/', ' ', s, flags=re.S)
    return re.sub(r'--[^\n]*', ' ', s)


class RunResult:
    def __init__(self):
        self.columns = []
        self.rows = []
        self.truncated = False
        self.messages = []
        self.error = None
        self.elapsed = 0.0
        self.has_result = False


PG_HINTS = [
    (r'::', 'Приведение типов через :: — синтаксис PostgreSQL. В тренажёре (SQLite) пишите CAST(x AS INTEGER) / CAST(x AS REAL).'),
    (r'\bilike\b', 'ILIKE есть в PostgreSQL. Здесь используйте lower(col) LIKE lower(\'...\').'),
    (r'\bextract\s*\(', "EXTRACT(... FROM ...) здесь заменяет date_part('month', col)."),
    (r'\binterval\b', "INTERVAL — PostgreSQL. В SQLite: date(col, '+7 day'), datetime(col, '-1 month')."),
    (r'\bgenerate_series\b', 'generate_series в тренажёре нет — постройте ряд дат рекурсивным CTE (модуль «CTE и рекурсия»).'),
    (r'\bfilter\s*\(\s*where\b', None),
]


def friendly_error(sql, err):
    msg = str(err)
    low = sql.lower()
    tips = []
    for pat, tip in PG_HINTS:
        if tip and re.search(pat, low):
            tips.append(tip)
    if 'no such column' in msg:
        tips.append('Проверьте имя столбца и алиас таблицы (кнопка «Схема»).')
    if 'no such table' in msg:
        tips.append('Проверьте имя таблицы: задание идёт на базе, указанной в условии.')
    if 'readonly' in msg:
        tips.append('В этом задании база только для чтения — нужен SELECT. Изменять данные можно в песочнице и DML-заданиях.')
    if 'misuse of aggregate' in msg or 'aggregate functions are not allowed' in msg:
        tips.append('Агрегат нельзя ставить в WHERE — используйте HAVING или подзапрос.')
    if 'misuse of window function' in msg:
        tips.append('Оконную функцию нельзя фильтровать в WHERE того же SELECT — оберните запрос в CTE.')
    return msg + ('\n\nПодсказка: ' + '\n'.join(tips) if tips else '')


def run_script(conn, script, max_rows=MAX_ROWS):
    """Выполняет все операторы; результат — последнего, вернувшего строки."""
    res = RunResult()
    stmts = split_statements(script)
    if not stmts:
        res.error = 'Пустой запрос.'
        return res
    t0 = time.perf_counter()
    for st in stmts:
        try:
            cur = conn.execute(st)
            if cur.description:
                cols = [d[0] for d in cur.description]
                rows = cur.fetchmany(max_rows + 1)
                res.columns, res.has_result = cols, True
                res.truncated = len(rows) > max_rows
                res.rows = rows[:max_rows]
                if res.truncated:
                    rest = len(cur.fetchall())
                    res.messages.append(f'Показаны первые {max_rows} строк из {max_rows + 1 + rest - 1}.')
            else:
                word = st.split(None, 1)[0].upper() if st.split() else ''
                if word in ('INSERT', 'UPDATE', 'DELETE', 'REPLACE'):
                    res.messages.append(f'{word}: затронуто строк — {cur.rowcount}')
                else:
                    res.messages.append(f'{word}: выполнено')
        except (sqlite3.Error, ValueError, OverflowError) as e:
            res.error = friendly_error(st, e)
            res.messages.append('Ошибка в операторе:\n' + st[:500])
            break
    res.elapsed = time.perf_counter() - t0
    return res


# ---------- проверка ----------

def _norm(v):
    if isinstance(v, bool):
        return ('n', float(v))
    if isinstance(v, (int, float)):
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return ('s', str(v))
        return ('n', round(float(v) + 0.0, 2))
    if v is None:
        return ('0', '')
    if isinstance(v, bytes):
        return ('s', v.hex())
    s = str(v)
    try:
        if re.fullmatch(r'-?\d+(\.\d+)?', s.strip()):
            return ('n', round(float(s), 2))
    except ValueError:
        pass
    return ('s', s)


def _close(a, b):
    if a[0] == 'n' and b[0] == 'n':
        return abs(a[1] - b[1]) <= max(0.011, abs(b[1]) * 1e-6)
    return a == b


def _rows_equal(r1, r2):
    return len(r1) == len(r2) and all(_close(x, y) for x, y in zip(r1, r2))


def fmt_row(row):
    return '(' + ', '.join('NULL' if v is None else repr(v) if isinstance(v, str) else str(v) for v in row) + ')'


def compare(user_cols, user_rows, exp_cols, exp_rows, ordered):
    """Возвращает (ok, сообщение)."""
    if len(user_cols) != len(exp_cols):
        return False, (f'Ожидается столбцов: {len(exp_cols)}, у вас: {len(user_cols)}.\n'
                       f'Нужные столбцы по смыслу: {", ".join(exp_cols)}')
    u = [tuple(_norm(v) for v in r) for r in user_rows]
    e = [tuple(_norm(v) for v in r) for r in exp_rows]
    if len(u) != len(e):
        return False, f'Ожидается строк: {len(e)}, у вас: {len(u)}.'
    if not ordered:
        u_sorted, e_sorted = sorted(u), sorted(e)
        for i, (a, b) in enumerate(zip(u_sorted, e_sorted)):
            if not _rows_equal(a, b):
                return False, _diff_message(user_rows, exp_rows, u, e, ordered)
        return True, 'Верно!'
    for i, (a, b) in enumerate(zip(u, e)):
        if not _rows_equal(a, b):
            if sorted(u) == sorted(e) or all(_rows_equal(x, y) for x, y in zip(sorted(u), sorted(e))):
                return False, ('Строки правильные, но порядок не тот. Проверьте ORDER BY '
                               f'(первое расхождение в строке {i + 1}).')
            return False, _diff_message(user_rows, exp_rows, u, e, ordered, i)
    return True, 'Верно!'


def _diff_message(user_rows, exp_rows, u, e, ordered, idx=None):
    if idx is None:
        e_set = list(e)
        for i, row in enumerate(u):
            match = next((j for j, x in enumerate(e_set) if _rows_equal(row, x)), None)
            if match is None:
                return (f'Количество строк совпало, но значения отличаются.\n'
                        f'Например, такой строки в правильном ответе нет: {fmt_row(user_rows[i])}\n'
                        'Сравните с вкладкой «Ожидаемый результат».')
            e_set.pop(match)
        return 'Значения отличаются. Сравните с вкладкой «Ожидаемый результат».'
    return (f'Расхождение в строке {idx + 1}:\n  у вас:     {fmt_row(user_rows[idx])}\n'
            f'  ожидалось: {fmt_row(exp_rows[idx])}')


class TaskChecker:
    """Кеширует эталонные ответы и проверяет решения."""

    def __init__(self):
        self._expected = {}

    def needs_copy(self, task):
        return task.get('kind', 'select') != 'select'

    def connection_for(self, task):
        return open_fresh(task['db']) if self.needs_copy(task) else open_readonly(task['db'])

    def expected(self, task):
        if task['id'] in self._expected:
            return self._expected[task['id']]
        conn = self.connection_for(task)
        try:
            out = self._evaluate(conn, task, task['solution'])
        finally:
            conn.close()
        if out.get('error'):
            raise RuntimeError(f"Эталон задачи {task['id']} упал: {out['error']}")
        self._expected[task['id']] = out
        return out

    def _evaluate(self, conn, task, script):
        kind = task.get('kind', 'select')
        res = run_script(conn, script)
        out = {'run': res, 'error': res.error}
        if res.error:
            return out
        if kind == 'select':
            if not res.has_result:
                out['error'] = 'Запрос не вернул таблицу. Нужен SELECT.'
                return out
            out['cols'], out['rows'] = res.columns, res.rows
            return out
        probes = []
        for sql, _should in task.get('probes', []):
            try:
                conn.execute('SAVEPOINT probe')
                conn.execute(sql)
                probes.append(True)
            except sqlite3.Error:
                probes.append(False)
            finally:
                try:
                    conn.execute('ROLLBACK TO probe')
                    conn.execute('RELEASE probe')
                except sqlite3.Error:
                    pass
        out['probes'] = probes
        if task.get('after'):
            try:
                for st in split_statements(task['after']):
                    conn.execute(st)
            except sqlite3.Error as e:
                out['error'] = friendly_error(task['after'], e) + '\n(ошибка при проверочных действиях после вашего скрипта)'
                return out
        check = task.get('check')
        if check:
            try:
                cur = conn.execute(check)
                out['cols'] = [d[0] for d in cur.description]
                out['rows'] = cur.fetchall()
            except sqlite3.Error as e:
                out['error'] = friendly_error(check, e) + '\n(ошибка при проверочном запросе — возможно, нет нужной таблицы/столбца)'
        return out

    def check(self, task, script):
        exp = self.expected(task)
        conn = self.connection_for(task)
        try:
            got = self._evaluate(conn, task, script)
        finally:
            conn.close()
        if got.get('error'):
            return False, got['error'], got
        kind = task.get('kind', 'select')
        if kind != 'select':
            for (sql, should), passed in zip(task.get('probes', []), got.get('probes', [])):
                if passed != should:
                    verb = 'должен проходить' if should else 'должен падать с ошибкой (ограничение)'
                    return False, f'Проверка не пройдена: оператор\n  {sql}\n{verb}.', got
            if 'rows' not in exp:
                return True, 'Верно!', got
            ok, msg = compare(got['cols'], got['rows'], exp['cols'], exp['rows'], True)
            if not ok:
                msg = 'После вашего скрипта данные не такие, как нужно.\nПроверочный запрос:\n  ' + task['check'] + '\n' + msg
            return ok, msg, got
        ok, msg = compare(got['cols'], got['rows'], exp['cols'], exp['rows'], task.get('ordered', False))
        return ok, msg, got


def table_overview(name):
    conn = open_readonly(name)
    try:
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        out = []
        for t in tables:
            cols = conn.execute(f'PRAGMA table_info("{t}")').fetchall()
            n = conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
            fks = {r[3]: f'{r[2]}.{r[4]}' for r in conn.execute(f'PRAGMA foreign_key_list("{t}")')}
            out.append((t, n, [(c[1], c[2], bool(c[3]), bool(c[5]), fks.get(c[1])) for c in cols]))
        return out
    finally:
        conn.close()


PG_TYPES = {'INTEGER': 'bigint', 'TEXT': 'text', 'NUMERIC': 'numeric(12,2)', 'REAL': 'double precision'}


def export_postgres(name, path):
    """Выгружает базу в .sql для PostgreSQL (psql -f файл)."""
    conn = open_readonly(name)
    try:
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY rowid")]
        with open(path, 'w', encoding='utf-8') as f:
            f.write(f'-- Учебная база {name} для PostgreSQL (схема {name}).\n'
                    f'-- Загрузка: psql -U postgres -d trainer -f {os.path.basename(path)}\n'
                    f'-- Работа:   SET search_path TO {name};\n')
            f.write('BEGIN;\n')
            f.write(f'DROP SCHEMA IF EXISTS {name} CASCADE;\nCREATE SCHEMA {name};\nSET search_path TO {name};\n')
            for t in tables:
                cols = conn.execute(f'PRAGMA table_info("{t}")').fetchall()
                pk = [c[1] for c in sorted(cols, key=lambda c: c[5]) if c[5]]
                defs = []
                for c in cols:
                    typ = PG_TYPES.get(c[2].upper(), 'text')
                    if t in ('product', 'products') and c[1] == 'attributes':
                        typ = 'jsonb'
                    if t == 'courses' and c[1] == 'meta':
                        typ = 'jsonb'
                    if c[1].endswith('_on') or (t == 'library_visits' and c[1] == 'day'):
                        typ = 'date'
                    if c[1].endswith('_at') or c[1] in ('event_time',):
                        typ = 'timestamp'
                    if c[1].endswith('_date') and t != 'raw_signups':
                        typ = 'date'
                    if t in ('product', 'customer') and c[1] == 'active':
                        typ = 'boolean'
                    defs.append(f'  {c[1]} {typ}' + (' NOT NULL' if c[3] else ''))
                if pk:
                    defs.append(f'  PRIMARY KEY ({", ".join(pk)})')
                f.write(f'CREATE TABLE {t} (\n' + ',\n'.join(defs) + '\n);\n')
                names = [c[1] for c in cols]
                bools = {i for i, c in enumerate(cols) if t in ('product', 'customer') and c[1] == 'active'}
                batch = []
                for row in conn.execute(f'SELECT * FROM "{t}"'):
                    vals = []
                    for i, v in enumerate(row):
                        if v is None:
                            vals.append('NULL')
                        elif i in bools:
                            vals.append('true' if v else 'false')
                        elif isinstance(v, (int, float)):
                            vals.append(str(v))
                        else:
                            vals.append("'" + str(v).replace("'", "''") + "'")
                    batch.append('(' + ','.join(vals) + ')')
                    if len(batch) == 500:
                        f.write(f'INSERT INTO {t} ({", ".join(names)}) VALUES\n' + ',\n'.join(batch) + ';\n')
                        batch = []
                if batch:
                    f.write(f'INSERT INTO {t} ({", ".join(names)}) VALUES\n' + ',\n'.join(batch) + ';\n')
            for t in tables:
                for fk in conn.execute(f'PRAGMA foreign_key_list("{t}")'):
                    f.write(f'ALTER TABLE {t} ADD FOREIGN KEY ({fk[3]}) REFERENCES {fk[2]}({fk[4]});\n')
            for (sql,) in conn.execute("SELECT sql FROM sqlite_master WHERE type = 'index' AND sql IS NOT NULL"):
                f.write(sql + ';\n')
            f.write('COMMIT;\n')
    finally:
        conn.close()
