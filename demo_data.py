"""Демо-база uni: университет + онлайн-школа. Только для примеров в теории.

Задания курса её не используют, поэтому примеры теории никогда не совпадают с решениями.
"""
import random
from datetime import date, datetime, timedelta

UNI_SQL = r"""
CREATE TABLE departments (
    dept_id    INTEGER PRIMARY KEY,
    name       TEXT NOT NULL,
    parent_id  INTEGER REFERENCES departments(dept_id)
);
INSERT INTO departments VALUES
 (1, 'Институт ИТ', NULL),
 (2, 'Кафедра программирования', 1),
 (3, 'Кафедра баз данных', 1),
 (4, 'Институт экономики', NULL),
 (5, 'Кафедра финансов', 4),
 (6, 'Кафедра маркетинга', 4),
 (7, 'Лаборатория ИИ', 2);

CREATE TABLE teachers (
    teacher_id INTEGER PRIMARY KEY,
    full_name  TEXT NOT NULL,
    dept_id    INTEGER REFERENCES departments(dept_id),
    hired_on   TEXT NOT NULL,
    salary     INTEGER NOT NULL CHECK (salary > 0),
    mentor_id  INTEGER REFERENCES teachers(teacher_id)
);
INSERT INTO teachers VALUES
 (1, 'Орлов Андрей',    2, '2010-09-01', 180000, NULL),
 (2, 'Белова Ирина',    3, '2012-02-01', 165000, 1),
 (3, 'Ким Сергей',      2, '2018-09-01', 120000, 1),
 (4, 'Лебедева Анна',   5, '2015-09-01', 150000, NULL),
 (5, 'Захаров Пётр',    5, '2021-09-01',  95000, 4),
 (6, 'Тихонова Ольга',  3, '2023-02-01',  90000, 2),
 (7, 'Гусев Максим', NULL, '2024-09-01',  70000, NULL),
 (8, 'Фомина Елена',    7, '2019-09-01', 140000, 3);

CREATE TABLE study_groups (
    group_id   INTEGER PRIMARY KEY,
    code       TEXT NOT NULL UNIQUE,
    year       INTEGER NOT NULL,
    curator_id INTEGER REFERENCES teachers(teacher_id)
);
INSERT INTO study_groups VALUES
 (1, 'ИТ-21', 2021, 1),
 (2, 'ИТ-22', 2022, 3),
 (3, 'ЭК-22', 2022, 4),
 (4, 'ЭК-23', 2023, NULL);

CREATE TABLE students (
    student_id  INTEGER PRIMARY KEY,
    full_name   TEXT NOT NULL,
    group_id    INTEGER REFERENCES study_groups(group_id),
    city        TEXT NOT NULL,
    birth_date  TEXT NOT NULL,
    email       TEXT UNIQUE,
    scholarship INTEGER
);
INSERT INTO students VALUES
 (1,  'Алексеев Иван',    1,    'Москва', '2003-04-12', 'ivan@uni.ru',   3000),
 (2,  'Борисова Мария',   1,    'Тула',   '2003-11-02', 'maria@uni.ru',  5000),
 (3,  'Волков Дмитрий',   1,    'Москва', '2002-07-23', NULL,            NULL),
 (4,  'Григорьева Софья', 2,    'Казань', '2004-01-30', 'sofia@uni.ru',  3000),
 (5,  'Данилов Артём',    2,    'Москва', '2004-05-17', 'artem@uni.ru',  NULL),
 (6,  'Егорова Полина',   2,    'Тверь',  '2003-09-09', 'polina@uni.ru', 7000),
 (7,  'Жуков Никита',     3,    'Казань', '2004-02-14', 'nikita@uni.ru', NULL),
 (8,  'Зайцева Ева',      3,    'Москва', '2004-12-01', 'eva@uni.ru',    5000),
 (9,  'Иванов Олег',      3,    'Тула',   '2003-06-06', 'oleg@uni.ru',   3000),
 (10, 'Ковалёва Дарья',   4,    'Москва', '2005-03-21', 'daria@uni.ru',  NULL),
 (11, 'Лосев Роман',      4,    'Самара', '2005-08-08', NULL,            NULL),
 (12, 'Миронова Алиса',   NULL, 'Москва', '2004-10-10', 'alisa@uni.ru',  NULL),
 (13, 'Новиков Глеб',     4,    'Тверь',  '2005-01-15', 'gleb@uni.ru',   3000),
 (14, 'Орлова Вера',      2,    'Самара', '2004-07-07', 'vera@uni.ru',   5000);

CREATE TABLE courses (
    course_id  INTEGER PRIMARY KEY,
    title      TEXT NOT NULL,
    credits    INTEGER NOT NULL,
    teacher_id INTEGER REFERENCES teachers(teacher_id),
    meta       TEXT
);
INSERT INTO courses VALUES
 (1, 'Базы данных',       5, 2, '{"format": "offline", "room": "А-301", "tags": ["sql", "postgres"]}'),
 (2, 'Алгоритмы',         6, 1, '{"format": "offline", "room": "А-105", "tags": ["python", "graphs"]}'),
 (3, 'Python',            4, 3, '{"format": "online", "tags": ["python"]}'),
 (4, 'Финансовый анализ', 4, 4, '{"format": "offline", "room": "Б-210", "tags": ["excel", "sql"]}'),
 (5, 'Микроэкономика',    3, 5, '{"format": "online", "tags": []}'),
 (6, 'Машинное обучение', 5, 8, '{"format": "hybrid", "room": "А-301", "tags": ["python", "ml"]}'),
 (7, 'Философия',         2, NULL, NULL);

CREATE TABLE enrollments (
    student_id INTEGER NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    course_id  INTEGER NOT NULL REFERENCES courses(course_id),
    grade      INTEGER CHECK (grade BETWEEN 2 AND 5),
    exam_date  TEXT,
    PRIMARY KEY (student_id, course_id)
);
INSERT INTO enrollments VALUES
 (1, 1, 5, '2025-01-20'), (1, 2, 4, '2025-01-25'), (1, 3, 5, '2024-06-15'),
 (2, 1, 4, '2025-01-20'), (2, 2, 5, '2025-01-25'), (2, 6, 3, '2025-06-10'),
 (3, 1, 3, '2025-01-20'), (3, 2, NULL, NULL),      (3, 3, 2, '2024-06-15'),
 (4, 1, 5, '2025-01-21'), (4, 3, 4, '2025-06-16'),
 (5, 3, NULL, NULL),
 (6, 1, 5, '2025-01-21'), (6, 2, 5, '2025-01-26'), (6, 6, 4, '2025-06-10'),
 (7, 4, 4, '2025-01-22'), (7, 5, 3, '2025-06-12'),
 (8, 4, 5, '2025-01-22'), (8, 5, 5, '2025-06-12'),
 (9, 4, 3, '2025-01-22'), (9, 5, NULL, NULL),
 (10, 5, 4, '2025-06-12'),
 (13, 4, 4, '2025-06-11'),
 (14, 1, 4, '2025-06-09'), (14, 3, 5, '2025-06-16');

CREATE TABLE club_members (
    email TEXT
);
INSERT INTO club_members VALUES ('ivan@uni.ru'), ('sofia@uni.ru'), ('guest@mail.ru'), (NULL), ('eva@uni.ru');

CREATE TABLE dorm_payments (
    payment_id INTEGER PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(student_id),
    paid_on    TEXT NOT NULL,
    amount     INTEGER NOT NULL
);
INSERT INTO dorm_payments(student_id, paid_on, amount) VALUES
 (1, '2025-09-03', 2500), (1, '2025-10-02', 2500), (1, '2025-11-05', 2500), (1, '2025-12-01', 2500),
 (3, '2025-09-10', 2500), (3, '2025-11-12', 5000),
 (4, '2025-09-01', 3000), (4, '2025-10-01', 3000), (4, '2025-11-01', 3000), (4, '2025-12-02', 3000),
 (7, '2025-09-15', 2500), (7, '2025-10-20', 2500),
 (11, '2025-10-01', 2500), (11, '2025-11-01', 2500), (11, '2025-12-01', 2500);

CREATE TABLE library_visits (
    day    TEXT PRIMARY KEY,
    visits INTEGER NOT NULL
);
INSERT INTO library_visits VALUES
 ('2025-11-03', 120), ('2025-11-04', 135), ('2025-11-05', 98),  ('2025-11-06', 143),
 ('2025-11-07', 160), ('2025-11-08', 75),  ('2025-11-10', 110), ('2025-11-11', 150),
 ('2025-11-12', 150), ('2025-11-13', 128), ('2025-11-14', 171), ('2025-11-15', 64),
 ('2025-11-17', 140);

CREATE INDEX idx_students_group ON students(group_id);
CREATE INDEX idx_enrollments_course ON enrollments(course_id);
"""

LMS_SQL = r"""
CREATE TABLE lms_users (
    user_id     INTEGER PRIMARY KEY,
    signup_date TEXT NOT NULL,
    channel     TEXT NOT NULL,
    variant     TEXT NOT NULL
);
CREATE TABLE lms_events (
    user_id    INTEGER NOT NULL REFERENCES lms_users(user_id),
    event_time TEXT NOT NULL,
    event      TEXT NOT NULL
);
CREATE TABLE lms_payments (
    payment_id INTEGER PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES lms_users(user_id),
    paid_at    TEXT NOT NULL,
    amount     INTEGER NOT NULL,
    plan       TEXT NOT NULL
);
"""


def build_lms(conn):
    """Онлайн-школа: 600 учеников, январь–июнь 2025. Детерминированно."""
    rnd = random.Random(7)
    conn.executescript(LMS_SQL)
    users, events, payments = [], [], []
    start = date(2025, 1, 1)
    end = date(2025, 6, 30)
    for uid in range(1, 601):
        signup = start + timedelta(days=rnd.randrange(0, 151))
        channel = rnd.choices(['ads', 'blog', 'friend'], weights=[5, 3, 2])[0]
        variant = 'A' if rnd.random() < 0.5 else 'B'
        users.append((uid, signup.isoformat(), channel, variant))
        engage = {'ads': 0.55, 'blog': 0.7, 'friend': 0.8}[channel]
        day = signup
        alive = True
        paid = False
        while alive and day <= end:
            if rnd.random() < engage:
                t = datetime(day.year, day.month, day.day, rnd.randrange(7, 24), rnd.randrange(60))
                events.append((uid, t.isoformat(sep=' '), 'visit'))
                if rnd.random() < 0.7:
                    events.append((uid, (t + timedelta(minutes=2)).isoformat(sep=' '), 'lesson'))
                    if rnd.random() < 0.45:
                        events.append((uid, (t + timedelta(minutes=40)).isoformat(sep=' '), 'homework'))
                        p_buy = 0.06 if variant == 'A' else 0.09
                        if not paid and rnd.random() < p_buy:
                            paid = True
                            plan = 'year' if rnd.random() < 0.25 else 'month'
                            events.append((uid, (t + timedelta(minutes=45)).isoformat(sep=' '), 'purchase'))
                            payments.append((uid, (t + timedelta(minutes=45)).isoformat(sep=' '),
                                             9900 if plan == 'year' else 1490, plan))
            day += timedelta(days=rnd.choice([1, 1, 1, 2, 3, 7]))
            if rnd.random() < (0.05 if paid else 0.12):
                alive = False
        if paid and payments[-1][3] == 'month':
            pay_day = datetime.fromisoformat(payments[-1][1])
            while rnd.random() < 0.75:
                pay_day += timedelta(days=30)
                if pay_day.date() > end:
                    break
                payments.append((uid, pay_day.isoformat(sep=' '), 1490, 'month'))
    conn.executemany('INSERT INTO lms_users VALUES (?,?,?,?)', users)
    conn.executemany('INSERT INTO lms_events VALUES (?,?,?)', events)
    conn.executemany('INSERT INTO lms_payments(user_id, paid_at, amount, plan) VALUES (?,?,?,?)', payments)
    conn.execute('CREATE INDEX idx_lms_events_user ON lms_events(user_id, event_time)')


def build_uni(conn):
    conn.executescript(UNI_SQL)
    build_lms(conn)
    conn.commit()
