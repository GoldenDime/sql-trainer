"""Прогресс ученика: progress.json рядом с программой."""
import json
import os
from datetime import date, datetime, timedelta

from engine import APP_DIR

PATH = os.path.join(APP_DIR, 'progress.json')
INTERVALS = [2, 6, 15, 35, 80]
XP_BY_LEVEL = {1: 10, 2: 20, 3: 35}
RANKS = [(0, 'Новичок'), (150, 'Знает SELECT'), (400, 'Уверенный JOIN'), (800, 'Оконщик'),
         (1300, 'Junior-аналитик'), (2000, 'Аналитик'), (2800, 'Продуктовый аналитик'), (3600, 'SQL-мастер')]


def today():
    return date.today().isoformat()


class Progress:
    def __init__(self, path=PATH):
        self.path = path
        self.data = {'version': 1, 'xp': 0, 'tasks': {}, 'theory': [], 'days': [], 'current': None, 'sandbox': {}}
        if os.path.exists(path):
            try:
                with open(path, encoding='utf-8') as f:
                    loaded = json.load(f)
                self.data.update(loaded)
            except (OSError, ValueError):
                backup = path + '.broken'
                try:
                    os.replace(path, backup)
                except OSError:
                    pass

    # --- сохранение ---
    def save(self):
        tmp = self.path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.path)

    def touch_day(self):
        d = today()
        if d not in self.data['days']:
            self.data['days'].append(d)

    # --- задания ---
    def task(self, tid):
        return self.data['tasks'].setdefault(tid, {'status': 'new', 'attempts': 0, 'hints': 0, 'revealed': False,
                                                   'sql': '', 'solved_at': None, 'review_step': 0, 'due': None})

    def status(self, tid):
        t = self.data['tasks'].get(tid)
        return t['status'] if t else 'new'

    def save_sql(self, tid, sql):
        self.task(tid)['sql'] = sql

    def record_attempt(self, tid, ok, level):
        t = self.task(tid)
        self.touch_day()
        t['attempts'] += 1
        gained = 0
        if ok:
            if t['status'] != 'solved':
                gained = XP_BY_LEVEL.get(level, 10)
                if t['revealed']:
                    gained = 0
                else:
                    gained = max(2, gained - 3 * t['hints'])
                t['status'] = 'solved'
                t['solved_at'] = datetime.now().isoformat(timespec='seconds')
                t['review_step'] = 0
                t['due'] = (date.today() + timedelta(days=INTERVALS[0])).isoformat()
            elif t.get('due') and t['due'] <= today():
                step = min(t.get('review_step', 0) + 1, len(INTERVALS) - 1)
                t['review_step'] = step
                t['due'] = (date.today() + timedelta(days=INTERVALS[step])).isoformat()
                gained = 3
        else:
            if t['status'] == 'new':
                t['status'] = 'tried'
            elif t['status'] == 'solved' and t.get('due') and t['due'] <= today():
                t['review_step'] = 0
                t['due'] = (date.today() + timedelta(days=1)).isoformat()
        self.data['xp'] += gained
        self.save()
        return gained

    def use_hint(self, tid):
        t = self.task(tid)
        t['hints'] += 1
        self.save()
        return t['hints']

    def reveal(self, tid):
        t = self.task(tid)
        t['revealed'] = True
        self.save()

    def due_reviews(self, ids):
        d = today()
        return [tid for tid in ids if self.data['tasks'].get(tid, {}).get('status') == 'solved'
                and (self.data['tasks'][tid].get('due') or '9999') <= d]

    # --- статистика ---
    def solved_count(self, ids):
        return sum(1 for tid in ids if self.status(tid) == 'solved')

    def streak(self):
        days = set(self.data['days'])
        d = date.today()
        if d.isoformat() not in days:
            d -= timedelta(days=1)
        n = 0
        while d.isoformat() in days:
            n += 1
            d -= timedelta(days=1)
        return n

    def rank(self):
        xp = self.data['xp']
        name, nxt = RANKS[0][1], None
        for i, (need, title) in enumerate(RANKS):
            if xp >= need:
                name = title
                nxt = RANKS[i + 1][0] if i + 1 < len(RANKS) else None
        return name, nxt

    def mark_theory(self, mid):
        if mid not in self.data['theory']:
            self.data['theory'].append(mid)
            self.save()
