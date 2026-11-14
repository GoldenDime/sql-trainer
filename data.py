"""Учебные базы данных тренажёра.

shop   - маленький магазин из лекций (Анна, Борис, Вера, Глеб).
market - маркетплейс за 2025 год: пользователи, события приложения, заказы,
         A/B-тест, подписки, маркетинг. Генерируется детерминированно.
"""
import math
import random
import sqlite3
from datetime import date, datetime, timedelta

SHOP_SQL = """
CREATE TABLE category (
    category_id INTEGER PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE
);
CREATE TABLE product (
    product_id  INTEGER PRIMARY KEY,
    category_id INTEGER NOT NULL REFERENCES category(category_id),
    name        TEXT NOT NULL,
    price       NUMERIC NOT NULL CHECK (price >= 0),
    stock       INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
    active      INTEGER NOT NULL DEFAULT 1,
    description TEXT,
    attributes  TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE customer (
    customer_id INTEGER PRIMARY KEY,
    full_name   TEXT NOT NULL,
    email       TEXT NOT NULL UNIQUE,
    city        TEXT
);
CREATE TABLE orders (
    order_id    INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customer(customer_id),
    status      TEXT NOT NULL DEFAULT 'NEW'
                CHECK (status IN ('NEW','PAID','DONE','CANCELLED')),
    created_at  TEXT NOT NULL,
    courier_id  INTEGER REFERENCES courier(courier_id)
);
CREATE TABLE order_item (
    order_id   INTEGER NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES product(product_id),
    quantity   INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC NOT NULL CHECK (unit_price >= 0),
    PRIMARY KEY (order_id, product_id)
);
CREATE TABLE newsletter_subscriber (
    email TEXT PRIMARY KEY
);
CREATE TABLE courier (
    courier_id   INTEGER PRIMARY KEY,
    courier_name TEXT NOT NULL
);
CREATE TABLE blocked_list (
    customer_id INTEGER
);
CREATE TABLE category_tree (
    id        INTEGER PRIMARY KEY,
    name      TEXT NOT NULL,
    parent_id INTEGER REFERENCES category_tree(id)
);
CREATE TABLE employee (
    employee_id INTEGER PRIMARY KEY,
    full_name   TEXT NOT NULL,
    position    TEXT NOT NULL,
    manager_id  INTEGER REFERENCES employee(employee_id),
    salary      INTEGER NOT NULL
);
CREATE TABLE seller_monthly (
    name  TEXT PRIMARY KEY,
    sales INTEGER NOT NULL
);
CREATE TABLE price_audit (
    audit_id   INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL,
    old_price  NUMERIC NOT NULL,
    new_price  NUMERIC NOT NULL,
    changed_at TEXT NOT NULL DEFAULT (datetime('now'))
);

INSERT INTO category VALUES (1,'Ноутбуки'),(2,'Аксессуары'),(3,'Мониторы'),(4,'Клавиатуры');
INSERT INTO product VALUES
 (1,1,'Ноутбук',80000,5,1,'15 дюймов','{"ram_gb":16,"color":"серый","ports":["USB-C","HDMI"]}'),
 (2,2,'Мышь',1500,12,1,NULL,'{"wireless":true,"color":"чёрный"}'),
 (3,3,'Монитор',22000,0,1,'IPS','{"diagonal":27,"ports":["HDMI"]}'),
 (4,2,'Коврик',600,20,1,NULL,'{}'),
 (5,2,'Кабель',900,8,1,NULL,'{"length_m":1.5}');
INSERT INTO customer VALUES
 (1,'Анна','anna@shop.ru','Москва'),
 (2,'Борис','boris@shop.ru','Казань'),
 (3,'Вера','vera@shop.ru','Москва'),
 (4,'Глеб','gleb@shop.ru',NULL);
INSERT INTO courier VALUES (1,'Алексей'),(2,'Мария');
INSERT INTO orders VALUES
 (101,1,'PAID','2026-10-01 10:15:00',1),
 (102,1,'NEW','2026-10-02 12:40:00',NULL),
 (103,2,'PAID','2026-10-02 18:05:00',2),
 (104,3,'CANCELLED','2026-10-03 09:30:00',NULL);
INSERT INTO order_item VALUES
 (101,1,1,80000),(101,2,2,1500),(102,3,1,22000),
 (103,2,1,1500),(103,4,3,600),(104,2,1,1500);
INSERT INTO newsletter_subscriber VALUES ('anna@shop.ru'),('irina@shop.ru'),('vera@shop.ru');
INSERT INTO blocked_list VALUES (2),(NULL);
INSERT INTO category_tree VALUES
 (1,'Каталог',NULL),(2,'Электроника',1),(3,'Аксессуары',2),
 (4,'Мыши',3),(5,'Клавиатуры',3),(6,'Книги',1);
INSERT INTO employee VALUES
 (1,'Ольга Смирнова','CEO',NULL,400000),
 (2,'Игорь Петров','CTO',1,320000),
 (3,'Нина Козлова','CFO',1,300000),
 (4,'Павел Орлов','Тимлид',2,220000),
 (5,'Дарья Соколова','Разработчик',4,180000),
 (6,'Артём Волков','Разработчик',4,170000),
 (7,'Евгения Лебедева','Аналитик',2,160000),
 (8,'Сергей Морозов','Бухгалтер',3,120000),
 (9,'Кирилл Новиков','Стажёр',5,60000);
INSERT INTO seller_monthly VALUES ('Анна',100),('Борис',80),('Вера',80),('Глеб',50);
"""

CATEGORIES = [
    (1, 'Электроника', None), (2, 'Смартфоны', 1), (3, 'Ноутбуки', 1),
    (4, 'Аксессуары', 1), (5, 'Чехлы', 4), (6, 'Наушники', 4), (7, 'Зарядки', 4),
    (8, 'Одежда', None), (9, 'Мужская', 8), (10, 'Женская', 8), (11, 'Обувь', 8),
    (12, 'Дом', None), (13, 'Кухня', 12), (14, 'Текстиль', 12),
    (15, 'Книги', None),
]

PRODUCT_TEMPLATES = {
    2: (['Смартфон Nova', 'Смартфон Pix', 'Смартфон Orbit', 'Смартфон Lumo'], ['Nova', 'Pix', 'Orbit', 'Lumo'], (14000, 90000)),
    3: (['Ноутбук Aero', 'Ноутбук Core', 'Ноутбук Flex'], ['Aero', 'Core', 'Flex'], (45000, 160000)),
    5: (['Чехол силиконовый', 'Чехол-книжка', 'Чехол противоударный'], ['Case+', 'Shield'], (400, 2500)),
    6: (['Наушники Bass', 'Наушники Air', 'Наушники Studio'], ['Sonix', 'Air', 'Studio'], (1500, 25000)),
    7: (['Зарядка 20W', 'Зарядка 65W', 'Пауэрбанк 10000'], ['Volt', 'Ampere'], (800, 4500)),
    9: (['Футболка мужская', 'Джинсы мужские', 'Куртка мужская', 'Худи мужское'], ['Urban', 'North'], (900, 12000)),
    10: (['Платье', 'Блузка', 'Джинсы женские', 'Пальто'], ['Mila', 'Urban'], (1200, 15000)),
    11: (['Кроссовки', 'Ботинки', 'Кеды'], ['Stride', 'North'], (2500, 14000)),
    13: (['Сковорода', 'Набор ножей', 'Кофеварка', 'Чайник'], ['Kitchy', 'Home+'], (900, 18000)),
    14: (['Плед', 'Комплект белья', 'Полотенце'], ['Softy', 'Home+'], (600, 6000)),
    15: (['Книга «SQL для аналитиков»', 'Книга «Статистика»', 'Роман «Север»', 'Книга «Продукт»'], ['Изд-во А', 'Изд-во Б'], (450, 2200)),
}

START = date(2025, 1, 1)
END = date(2025, 12, 31)
AB_START = date(2025, 9, 1)
AB_END = date(2025, 10, 31)

MARKET_DDL = """
CREATE TABLE categories (
    category_id INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    parent_id   INTEGER REFERENCES categories(category_id)
);
CREATE TABLE products (
    product_id  INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    category_id INTEGER NOT NULL REFERENCES categories(category_id),
    brand       TEXT NOT NULL,
    price       NUMERIC NOT NULL,
    cost        NUMERIC NOT NULL
);
CREATE TABLE users (
    user_id     INTEGER PRIMARY KEY,
    signup_date TEXT NOT NULL,
    channel     TEXT NOT NULL,
    device      TEXT NOT NULL,
    city        TEXT NOT NULL,
    birth_year  INTEGER
);
CREATE TABLE events (
    event_id    INTEGER PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(user_id),
    event_time  TEXT NOT NULL,
    event_name  TEXT NOT NULL,
    product_id  INTEGER REFERENCES products(product_id)
);
CREATE TABLE orders (
    order_id      INTEGER PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES users(user_id),
    created_at    TEXT NOT NULL,
    status        TEXT NOT NULL,
    promo_code    TEXT,
    delivery_cost NUMERIC NOT NULL
);
CREATE TABLE order_items (
    order_id   INTEGER NOT NULL REFERENCES orders(order_id),
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    quantity   INTEGER NOT NULL,
    price      NUMERIC NOT NULL,
    PRIMARY KEY (order_id, product_id)
);
CREATE TABLE ab_test (
    user_id     INTEGER PRIMARY KEY REFERENCES users(user_id),
    test_name   TEXT NOT NULL,
    group_name  TEXT NOT NULL,
    assigned_at TEXT NOT NULL
);
CREATE TABLE subscriptions (
    subscription_id INTEGER PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(user_id),
    plan            TEXT NOT NULL,
    price_per_month NUMERIC NOT NULL,
    started_at      TEXT NOT NULL,
    ended_at        TEXT
);
CREATE TABLE marketing_spend (
    spend_date TEXT NOT NULL,
    channel    TEXT NOT NULL,
    spend      NUMERIC NOT NULL,
    PRIMARY KEY (spend_date, channel)
);
CREATE TABLE raw_signups (
    row_id     INTEGER PRIMARY KEY,
    email      TEXT NOT NULL,
    full_name  TEXT,
    created_at TEXT NOT NULL,
    source     TEXT
);
"""

MARKET_INDEXES = """
CREATE INDEX idx_events_user_time ON events(user_id, event_time);
CREATE INDEX idx_events_name_time ON events(event_name, event_time);
CREATE INDEX idx_orders_user ON orders(user_id, created_at);
CREATE INDEX idx_order_items_product ON order_items(product_id);
"""


def _pick(rng, weighted):
    r = rng.random() * sum(w for _, w in weighted)
    for v, w in weighted:
        r -= w
        if r <= 0:
            return v
    return weighted[-1][0]


def _ts(d, seconds):
    return (datetime(d.year, d.month, d.day) + timedelta(seconds=seconds)).strftime('%Y-%m-%d %H:%M:%S')


def build_market(conn):
    rng = random.Random(2025)
    conn.executescript(MARKET_DDL)
    conn.executemany('INSERT INTO categories VALUES (?,?,?)', CATEGORIES)

    products = []
    pid = 0
    for cat, (names, brands, (lo, hi)) in PRODUCT_TEMPLATES.items():
        for name in names:
            pid += 1
            price = round(rng.uniform(lo, hi) / 10) * 10
            cost = round(price * rng.uniform(0.45, 0.75) / 10) * 10
            products.append((pid, name, cat, rng.choice(brands), price, cost))
    conn.executemany('INSERT INTO products VALUES (?,?,?,?,?,?)', products)
    # популярность: дешёвые товары покупают чаще
    weights = [1.0 / math.sqrt(p[4]) for p in products]

    channels = [('organic', 40), ('ads', 30), ('referral', 15), ('social', 15)]
    devices = [('android', 45), ('ios', 35), ('web', 20)]
    cities = [('Москва', 30), ('Санкт-Петербург', 18), ('Казань', 9), ('Новосибирск', 8),
              ('Екатеринбург', 9), ('Нижний Новгород', 6), ('Краснодар', 7), ('Самара', 5), ('Другой', 8)]
    engage = {'organic': 1.0, 'ads': 0.65, 'referral': 1.35, 'social': 0.8}

    days_total = (END - START).days + 1
    users, events, orders, items, ab, subs = [], [], [], [], [], []
    uid = 0
    eid = 0
    oid = 0
    sid = 0
    for day_idx in range(days_total):
        d = START + timedelta(days=day_idx)
        base = 4 + 6 * day_idx / days_total
        if d.month in (11, 12):
            base *= 1.35
        if d.weekday() >= 5:
            base *= 1.15
        n_new = max(0, int(rng.gauss(base, 2.5)))
        for _ in range(n_new):
            uid += 1
            ch = _pick(rng, channels)
            dev = _pick(rng, devices)
            by = None if rng.random() < 0.06 else rng.randint(1962, 2007)
            users.append((uid, d.isoformat(), ch, dev, _pick(rng, cities), by))
            e = engage[ch] * rng.lognormvariate(0, 0.6)
            group = None
            if d <= AB_END:
                group = 'A' if rng.random() < 0.5 else 'B'
                ab.append((uid, 'new_checkout', group, max(d, AB_START).isoformat()))
            # подписка
            if rng.random() < 0.10 * min(e, 2):
                start_off = rng.randint(0, 60)
                st = d + timedelta(days=start_off)
                if st <= END:
                    plan = 'year' if rng.random() < 0.25 else 'month'
                    ppm = 249 if plan == 'year' else 299
                    dur = rng.randint(20, 400) if plan == 'month' else rng.choice([365, 365, 730])
                    en = st + timedelta(days=dur)
                    sid += 1
                    subs.append((sid, uid, plan, ppm, st.isoformat(), en.isoformat() if en <= END else None))
            tau = 25 * e
            for t in range(0, (END - d).days + 1):
                cur = d + timedelta(days=t)
                if t == 0:
                    p = 1.0
                else:
                    p = min(0.9, 0.30 * e * (0.12 + 0.88 * math.exp(-t / tau)))
                    if cur.month in (11, 12):
                        p *= 1.15
                if rng.random() > p:
                    continue
                n_sessions = 1 if rng.random() < 0.8 else 2
                sec = rng.randint(7 * 3600, 20 * 3600)
                for s in range(n_sessions):
                    if s == 1:
                        sec = min(sec + rng.randint(3600, 4 * 3600), 86000)
                    eid += 1
                    events.append((eid, uid, _ts(cur, sec), 'app_open', None))
                    n_views = rng.choice([0, 1, 1, 2, 2, 3, 4])
                    viewed = []
                    for _v in range(n_views):
                        sec = min(sec + rng.randint(20, 240), 86390)
                        prod = rng.choices(products, weights)[0][0]
                        viewed.append(prod)
                        eid += 1
                        events.append((eid, uid, _ts(cur, sec), 'view_item', prod))
                    if not viewed or rng.random() > 0.33:
                        continue
                    cart = viewed[-1]
                    sec = min(sec + rng.randint(15, 180), 86390)
                    eid += 1
                    events.append((eid, uid, _ts(cur, sec), 'add_to_cart', cart))
                    if rng.random() > 0.55:
                        continue
                    sec = min(sec + rng.randint(30, 300), 86390)
                    eid += 1
                    events.append((eid, uid, _ts(cur, sec), 'begin_checkout', None))
                    pp = 0.55
                    if group == 'B' and AB_START <= cur <= AB_END:
                        pp = 0.63
                    if cur.month == 11 and 24 <= cur.day <= 30:
                        pp += 0.1
                    if rng.random() > pp:
                        continue
                    sec = min(sec + rng.randint(30, 240), 86399)
                    ts = _ts(cur, sec)
                    eid += 1
                    events.append((eid, uid, ts, 'purchase', None))
                    oid += 1
                    st = _pick(rng, [('delivered', 85), ('cancelled', 8), ('returned', 7)])
                    if cur.month == 11 and 24 <= cur.day <= 30 and rng.random() < 0.6:
                        promo = 'BLACKFRIDAY'
                    elif t == 0 and rng.random() < 0.5:
                        promo = 'WELCOME10'
                    elif rng.random() < 0.07:
                        promo = 'SALE20'
                    else:
                        promo = None
                    basket = {cart}
                    while rng.random() < 0.35 and len(basket) < 4:
                        basket.add(rng.choices(products, weights)[0][0])
                    total = 0
                    for prod in sorted(basket):
                        q = 1 if rng.random() < 0.8 else rng.randint(2, 3)
                        price = products[prod - 1][4]
                        if promo == 'BLACKFRIDAY':
                            price = round(price * 0.8)
                        items.append((oid, prod, q, price))
                        total += q * price
                    delivery = 0 if total >= 3000 else 199
                    orders.append((oid, uid, ts, st, promo, delivery))

    conn.executemany('INSERT INTO users VALUES (?,?,?,?,?,?)', users)
    conn.executemany('INSERT INTO events VALUES (?,?,?,?,?)', events)
    conn.executemany('INSERT INTO orders VALUES (?,?,?,?,?,?)', orders)
    conn.executemany('INSERT INTO order_items VALUES (?,?,?,?)', items)
    conn.executemany('INSERT INTO ab_test VALUES (?,?,?,?)', ab)
    conn.executemany('INSERT INTO subscriptions VALUES (?,?,?,?,?,?)', subs)

    spend = []
    for day_idx in range(days_total):
        d = START + timedelta(days=day_idx)
        k = 1.4 if d.month in (11, 12) else 1.0
        spend.append((d.isoformat(), 'ads', round(rng.uniform(9000, 16000) * k * (1 + day_idx / 500))))
        spend.append((d.isoformat(), 'social', round(rng.uniform(3000, 7000) * k)))
        spend.append((d.isoformat(), 'referral', round(rng.uniform(1000, 2500))))
    conn.executemany('INSERT INTO marketing_spend VALUES (?,?,?)', spend)

    raw = [
        ('anna.ivanova@mail.ru', 'Анна Иванова', '2025-03-01 10:00:00', 'web'),
        ('Anna.Ivanova@mail.ru ', 'Анна Иванова', '2025-03-01 10:02:10', 'android'),
        ('boris@yandex.ru', 'Борис', '2025-03-02 08:15:00', 'ios'),
        ('vera@gmail.com', 'Вера П.', '2025-03-02 09:00:00', 'web'),
        ('VERA@gmail.com', 'Вера Петрова', '2025-03-05 19:40:00', 'web'),
        ('vera@gmail.com', 'Вера Петрова', '2025-03-07 11:11:11', 'ios'),
        ('gleb@mail.ru', None, '2025-03-03 12:00:00', 'android'),
        ('dina@mail.ru', 'Дина', '2025-03-04 15:30:00', 'web'),
        (' dina@mail.ru', 'Дина К.', '2025-03-04 15:31:00', 'web'),
        ('egor@yandex.ru', 'Егор', '2025-03-06 07:45:00', 'ios'),
        ('zhanna@gmail.com', 'Жанна', '2025-03-06 21:05:00', 'android'),
        ('ZHANNA@GMAIL.COM', 'Жанна', '2025-03-08 10:00:00', 'web'),
        ('ilya@mail.ru', 'Илья', '2025-03-09 13:20:00', None),
        ('kira@yandex.ru', 'Кира', '2025-03-10 16:00:00', 'web'),
    ]
    conn.executemany('INSERT INTO raw_signups(email, full_name, created_at, source) VALUES (?,?,?,?)', raw)
    conn.executescript(MARKET_INDEXES)
    conn.commit()


def build_shop(conn):
    conn.executescript(SHOP_SQL)
    conn.commit()


BUILDERS = {'shop': build_shop, 'market': build_market}
DATA_VERSION = 3


def build_file(name, path):
    conn = sqlite3.connect(path)
    try:
        BUILDERS[name](conn)
        conn.execute(f'PRAGMA user_version = {DATA_VERSION}')
        conn.commit()
    finally:
        conn.close()
