"""Модули 0–10: база курса по лекциям 1–8."""


def T(id, title, text, solution, db='shop', ordered=False, hints=(), level=1, kind='select',
      check=None, probes=(), after=None, lecture=None):
    return dict(id=id, title=title, text=text.strip(), solution=solution.strip(), db=db, ordered=ordered,
                hints=list(hints), level=level, kind=kind, check=check, probes=list(probes), after=after,
                lecture=lecture)


M0 = dict(id='m00', title='0. Как устроен тренажёр', theory=r"""
# Как устроен тренажёр

Слева — модули. В каждом есть **теория** и **задания**. Решение пишется в редакторе, затем:

- **F5 / Ctrl+Enter** — выполнить и посмотреть результат;
- **F9 / Ctrl+Shift+Enter** — проверить решение;
- «Подсказка» открывает подсказки по одной, «Решение» показывает эталон (задание тогда засчитывается без опыта);
- вкладка «Ожидаемый результат» показывает, какая таблица должна получиться.

Проверяется **результат**, а не текст запроса: совпадение строк и значений, имена столбцов не важны. Порядок строк проверяется, только если в условии сказано «отсортируйте». Числа сравниваются с точностью до 0.01.

Прогресс, последние решения и опыт хранятся в файле `progress.json` рядом с программой. Решённые задания возвращаются в раздел «Повторение» через 2, 6, 15, 35 дней (интервальное повторение).

## Две учебные базы

- **shop** — магазин из лекций: category, product, customer, orders, order_item, newsletter_subscriber, courier, blocked_list, category_tree, employee, seller_monthly, price_audit.
- **market** — маркетплейс за 2025 год: users (~2.6 тыс.), events (~180 тыс. событий приложения), orders, order_items, products, categories (дерево), ab_test, subscriptions, marketing_spend, raw_signups.

Кнопка «Схема» показывает таблицы и столбцы текущей базы. «Песочница» — свободный режим, там можно менять данные (кнопка «Сбросить» вернёт исходное состояние).

## Диалект: SQLite с добавками PostgreSQL

Внутри работает встроенный SQLite (ничего ставить не надо). Синтаксис запросов почти совпадает с PostgreSQL: JOIN всех видов, CTE, WITH RECURSIVE, оконные функции, FILTER, RETURNING, ON CONFLICT. Добавлены функции как в PostgreSQL: `date_trunc`, `date_part`, `greatest`, `least`, `split_part`, `median`, `percentile_cont(x, p)`, `stddev`, `corr`, `string_agg`, `bool_and`, `bool_or`, а `lower/upper` понимают кириллицу.

Отличия, которые надо помнить:

- `x::int` → `CAST(x AS INTEGER)`; `5/2 = 2` (целочисленное деление, как в PostgreSQL) — пишите `5.0/2` или `CAST(x AS REAL)`;
- даты хранятся текстом `'2025-12-31 18:00:00'`; интервалы: `date(d, '+7 day')`, `datetime(t, '-1 month')`; разница в днях — `julianday(b) - julianday(a)` (в PostgreSQL: `b::date - a::date`);
- `ILIKE` нет — `lower(col) LIKE '%...%'`; `EXTRACT(dow FROM t)` → `date_part('dow', t)`;
- логические значения — 1/0; JSON-оператор `->>` есть, но вместо `@>` и `?` — `json_extract`, `json_each`;
- нет `generate_series` — ряд строим рекурсивным CTE.

Кнопка «Экспорт в PostgreSQL» сохранит любую базу в .sql — её можно загрузить в твой локальный PostgreSQL 17 и решать те же задачи там.
""", tasks=[
    T('m00.1', 'Первый запрос', """
База **shop**. Выведите всех клиентов — все столбцы таблицы `customer`.
""", "SELECT * FROM customer;", hints=['SELECT * FROM имя_таблицы;']),
])

M1 = dict(id='m01', title='1. SELECT: выборка и сортировка', theory=r"""
# SELECT: читаем строки и столбцы

```
SELECT столбцы / выражения AS алиас
FROM таблица
WHERE условие для каждой строки
ORDER BY столбец [ASC|DESC], ...
LIMIT n [OFFSET k];
```

**Логический порядок выполнения**: FROM → WHERE → SELECT → DISTINCT → ORDER BY → LIMIT. Поэтому алиас из SELECT нельзя использовать в WHERE, но можно в ORDER BY.

- `SELECT *` удобно для разведки, в отчётах перечисляйте нужные столбцы.
- Без ORDER BY порядок строк **не гарантирован**. Для стабильного TOP-N добавляйте второй ключ: `ORDER BY price DESC, product_id`.
- `DISTINCT` убирает повторы сочетаний выбранных столбцов.
- `BETWEEN a AND b` включает обе границы; `IN (1, 2, 3)` — проверка на вхождение в список.
- Выражения в SELECT: `price * stock AS stock_value`, конкатенация строк `||`.

## NULL

NULL — «значение неизвестно», а не 0 и не пустая строка. `col = NULL` никогда не истинно; пишем `col IS NULL` / `IS NOT NULL`. Любая арифметика с NULL даёт NULL.
""", tasks=[
    T('m01.1', 'Названия и цены', "Выведите название и цену всех товаров (`product`).",
      "SELECT name, price FROM product;", lecture=4),
    T('m01.2', 'Дороже тысячи', "Товары дороже 1000: название и цену. Отсортируйте по возрастанию цены.",
      "SELECT name, price FROM product WHERE price > 1000 ORDER BY price;", ordered=True, lecture=4),
    T('m01.3', 'Несколько условий', """
Товары категории 2 с ценой от 500 до 1600 включительно, которые есть в наличии (stock > 0).
Выведите name, price, stock, отсортируйте по цене.
""", "SELECT name, price, stock FROM product WHERE category_id = 2 AND price BETWEEN 500 AND 1600 AND stock > 0 ORDER BY price;",
      ordered=True, hints=['BETWEEN включает границы', 'Условия соединяются через AND'], lecture=4),
    T('m01.4', 'TOP-3', "Три самых дорогих товара: name, price. При равной цене — по product_id.",
      "SELECT name, price FROM product ORDER BY price DESC, product_id LIMIT 3;", ordered=True,
      hints=['ORDER BY ... DESC', 'LIMIT 3']),
    T('m01.5', 'DISTINCT', "Номера клиентов (customer_id), у которых есть заказы, без повторов, по возрастанию.",
      "SELECT DISTINCT customer_id FROM orders ORDER BY customer_id;", ordered=True),
    T('m01.6', 'Вычисляемый столбец', """
Стоимость остатков по каждому товару: name и price * stock под именем stock_value.
Отсортируйте по stock_value по убыванию.
""", "SELECT name, price * stock AS stock_value FROM product ORDER BY stock_value DESC;", ordered=True,
      hints=['Алиас из SELECT можно использовать в ORDER BY']),
    T('m01.7', 'IS NULL', "Товары без описания: product_id, name.",
      "SELECT product_id, name FROM product WHERE description IS NULL;",
      hints=['= NULL не работает, нужен IS NULL']),
    T('m01.8', 'OR и NULL', "Клиенты из Москвы или с неизвестным городом: full_name, city.",
      "SELECT full_name, city FROM customer WHERE city = 'Москва' OR city IS NULL;"),
    T('m01.9', 'OFFSET', "Товары, отсортированные по цене по возрастанию: пропустите первые 2 и выведите следующие 2 (name, price).",
      "SELECT name, price FROM product ORDER BY price LIMIT 2 OFFSET 2;", ordered=True),
])

M2 = dict(id='m02', title='2. Выражения: CASE, COALESCE, строки', theory=r"""
# Выражения, которые нужны каждый день

## CASE — условная логика

```sql
SELECT name,
       CASE WHEN stock = 0 THEN 'нет'
            WHEN stock < 10 THEN 'мало'
            ELSE 'много' END AS availability
FROM product;
```
Ветки проверяются сверху вниз, срабатывает первая истинная. Без ELSE результат — NULL.

## Работа с NULL

- `COALESCE(a, b, c)` — первое не-NULL значение: `COALESCE(city, 'не указан')`.
- `NULLIF(a, b)` — NULL, если a = b. Классика безопасного деления: `x / NULLIF(y, 0)`.

## Строки

- `||` — конкатенация (в PostgreSQL ещё `concat()`, она игнорирует NULL);
- `lower`, `upper`, `trim`, `length`, `substr(s, start, len)`, `replace`, `instr(s, sub)` (в PostgreSQL — `strpos`), `split_part(s, '@', 2)`;
- `LIKE 'Смартфон%'`: `%` — любая строка, `_` — один символ. В PostgreSQL для регистра есть `ILIKE`, здесь — `lower(col) LIKE ...`.

## Числа и деление

`7 / 2 = 3` — деление целых целочисленное (и в PostgreSQL тоже!). Для доли умножайте на `100.0` или приводите тип: `100.0 * part / total`. Округление — `round(x, 2)`.
""", tasks=[
    T('m02.1', 'CASE: наличие', """
Для каждого товара выведите name и статус: 'нет', если stock = 0; 'мало', если stock < 10; иначе 'много'.
""", "SELECT name, CASE WHEN stock = 0 THEN 'нет' WHEN stock < 10 THEN 'мало' ELSE 'много' END AS availability FROM product;"),
    T('m02.2', 'COALESCE', "Клиенты: full_name и город, где вместо NULL написано 'не указан'.",
      "SELECT full_name, COALESCE(city, 'не указан') AS city FROM customer;"),
    T('m02.3', 'LIKE', "База **market**. Товары, в названии которых есть «Наушники» или «Зарядка»: product_id, name.",
      "SELECT product_id, name FROM products WHERE name LIKE '%Наушники%' OR name LIKE '%Зарядка%';", db='market'),
    T('m02.4', 'IN и диапазон дат', """
База **market**. Пользователи из Москвы или Казани, зарегистрированные в декабре 2025 с устройства ios:
user_id, signup_date, city.
""", "SELECT user_id, signup_date, city FROM users WHERE city IN ('Москва','Казань') AND signup_date BETWEEN '2025-12-01' AND '2025-12-31' AND device = 'ios';",
      db='market', hints=["Даты — строки вида '2025-12-01', их можно сравнивать BETWEEN"]),
    T('m02.5', 'Возрастные группы', """
База **market**. Для пользователей с user_id от 1 до 15 выведите user_id и возрастную группу на 2025 год
(возраст = 2025 − birth_year): 'до 25' (< 25), '25-34', '35-44', '45+', а если год рождения неизвестен — 'неизвестно'.
""", """SELECT user_id,
       CASE WHEN birth_year IS NULL THEN 'неизвестно'
            WHEN 2025 - birth_year < 25 THEN 'до 25'
            WHEN 2025 - birth_year < 35 THEN '25-34'
            WHEN 2025 - birth_year < 45 THEN '35-44'
            ELSE '45+' END AS age_group
FROM users WHERE user_id BETWEEN 1 AND 15;""", db='market', hints=['Проверку на NULL ставьте первой веткой']),
    T('m02.6', 'Маржа в процентах', """
База **market**. Пять товаров с наибольшей маржинальностью: name, price, cost, margin = price − cost,
margin_pct = (price − cost) / price × 100, округлённая до 1 знака. Сортировка по margin_pct по убыванию, затем по product_id.
""", "SELECT name, price, cost, price - cost AS margin, round(100.0 * (price - cost) / price, 1) AS margin_pct FROM products ORDER BY margin_pct DESC, product_id LIMIT 5;",
      db='market', ordered=True, level=2, hints=['Осторожно с целочисленным делением: 100.0 * ...']),
    T('m02.7', 'Чистим email', "База **market**, таблица `raw_signups`. Выведите row_id и email, приведённый к нижнему регистру и без пробелов по краям. Сортировка по row_id.",
      "SELECT row_id, lower(trim(email)) AS email_norm FROM raw_signups ORDER BY row_id;", db='market', ordered=True),
    T('m02.8', 'Склейка строк', "Для каждого товара выведите строку вида `Ноутбук — 80000 руб.` в порядке product_id.",
      "SELECT name || ' — ' || price || ' руб.' AS card FROM product ORDER BY product_id;", ordered=True),
    T('m02.9', 'Домен почты', "База **market**. Из `raw_signups` выведите row_id и домен почты (часть после @, в нижнем регистре, без пробелов). Сортировка по row_id.",
      "SELECT row_id, lower(trim(split_part(email, '@', 2))) AS domain FROM raw_signups ORDER BY row_id;", db='market', ordered=True,
      hints=["split_part(email, '@', 2) или substr(email, instr(email, '@') + 1)"]),
])

M3 = dict(id='m03', title='3. Агрегаты, GROUP BY, HAVING', theory=r"""
# Агрегаты: одна цифра вместо многих строк

`COUNT`, `SUM`, `AVG`, `MIN`, `MAX` берут набор строк и возвращают одно значение.

- `COUNT(*)` — число строк; `COUNT(col)` — непустых значений; `COUNT(DISTINCT col)` — уникальных непустых.
- Агрегаты игнорируют NULL (кроме `COUNT(*)`). `AVG` от пустого набора — NULL.

## GROUP BY

Строки с одинаковыми значениями ключа собираются в группу, агрегаты считаются внутри группы, каждая группа даёт одну строку. В SELECT можно писать только ключи группировки и агрегаты.

## WHERE vs HAVING

```
FROM → WHERE (отдельные строки) → GROUP BY → агрегаты → HAVING (группы) → SELECT → ORDER BY
```
```sql
SELECT category_id, COUNT(*) AS products, SUM(stock) AS units
FROM product
WHERE stock > 0               -- до группировки
GROUP BY category_id
HAVING COUNT(*) >= 2          -- после группировки
ORDER BY units DESC;
```

## Условная агрегация

```sql
SELECT COUNT(*) FILTER (WHERE status = 'PAID')       AS paid,      -- PostgreSQL и SQLite
       SUM(CASE WHEN status = 'NEW' THEN 1 ELSE 0 END) AS new_orders -- работает везде
FROM orders;
```
Это главный инструмент аналитика для сводных таблиц.
""", tasks=[
    T('m03.1', 'Пять агрегатов', "Для таблицы product посчитайте: число товаров, сумму остатков, среднюю цену, минимальную и максимальную цену.",
      "SELECT COUNT(*), SUM(stock), AVG(price), MIN(price), MAX(price) FROM product;", lecture=4),
    T('m03.2', 'Три COUNT', "По таблице orders: всего заказов, заказов с назначенным курьером (courier_id не NULL), число разных покупателей.",
      "SELECT COUNT(*), COUNT(courier_id), COUNT(DISTINCT customer_id) FROM orders;",
      hints=['COUNT(col) не считает NULL']),
    T('m03.3', 'GROUP BY', "По каждой категории: category_id, число товаров, сумма остатков.",
      "SELECT category_id, COUNT(*) AS products, SUM(stock) AS units FROM product GROUP BY category_id;", lecture=4),
    T('m03.4', 'HAVING', "Категории, где не меньше двух товаров в наличии (stock > 0): category_id, число таких товаров, сумма их остатков.",
      "SELECT category_id, COUNT(*) AS products, SUM(stock) AS units FROM product WHERE stock > 0 GROUP BY category_id HAVING COUNT(*) >= 2;",
      lecture=4, hints=['stock > 0 — фильтр строк (WHERE), «не меньше двух» — фильтр групп (HAVING)']),
    T('m03.5', 'Сумма заказа', "Стоимость каждого заказа: order_id и сумма quantity × unit_price из order_item.",
      "SELECT order_id, SUM(quantity * unit_price) AS total FROM order_item GROUP BY order_id;"),
    T('m03.6', 'Пользователи по каналам', "База **market**. Число пользователей по каналам привлечения (channel), по убыванию числа.",
      "SELECT channel, COUNT(*) AS users FROM users GROUP BY channel ORDER BY users DESC;", db='market', ordered=True),
    T('m03.7', 'Выручка по месяцам', """
База **market**. Выручка по месяцам 2025 года — только заказы со статусом 'delivered'.
Выручка = сумма quantity × price из order_items. Столбцы: месяц в формате '2025-01' и выручка, по возрастанию месяца.
""", """SELECT substr(o.created_at, 1, 7) AS month, SUM(oi.quantity * oi.price) AS revenue
FROM orders o JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.status = 'delivered'
GROUP BY month ORDER BY month;""", db='market', ordered=True, level=2,
      hints=["substr(created_at, 1, 7) даст '2025-01'", 'Понадобится JOIN orders и order_items']),
    T('m03.8', 'Крупные города', "База **market**. Города, где больше 200 пользователей: city, users. По убыванию users.",
      "SELECT city, COUNT(*) AS users FROM users GROUP BY city HAVING COUNT(*) > 200 ORDER BY users DESC;", db='market', ordered=True),
    T('m03.9', 'Группировка по двум полям', """
База **market**. Число заказов в разрезе статуса и признака «был промокод» (1 — promo_code заполнен, 0 — нет).
Столбцы: status, has_promo, orders.
""", "SELECT status, CASE WHEN promo_code IS NULL THEN 0 ELSE 1 END AS has_promo, COUNT(*) AS orders FROM orders GROUP BY status, has_promo;",
      db='market'),
    T('m03.10', 'Условная агрегация', """
База **market**. Одной строкой: число заказов со статусом delivered, cancelled и returned, а также процент отмен
(cancelled от всех заказов, округлить до 2 знаков).
""", """SELECT COUNT(*) FILTER (WHERE status = 'delivered') AS delivered,
       COUNT(*) FILTER (WHERE status = 'cancelled') AS cancelled,
       COUNT(*) FILTER (WHERE status = 'returned') AS returned,
       round(100.0 * COUNT(*) FILTER (WHERE status = 'cancelled') / COUNT(*), 2) AS cancel_pct
FROM orders;""", db='market', level=2, hints=["COUNT(*) FILTER (WHERE ...) или SUM(CASE WHEN ... THEN 1 ELSE 0 END)"]),
])

M4 = dict(id='m04', title='4. JOIN: соединяем таблицы', theory=r"""
# JOIN

`JOIN ... ON условие` соединяет пары строк, для которых условие истинно.

| Тип | Что остаётся |
|---|---|
| INNER JOIN | только совпавшие пары |
| LEFT JOIN | все строки слева; справа NULL, если пары нет |
| RIGHT JOIN | все строки справа (переписывается в LEFT, поменяв таблицы) |
| FULL JOIN | все строки с обеих сторон |
| CROSS JOIN | все сочетания (декартово произведение) |

## Ловушки

1. **Условие на правую таблицу в WHERE убивает LEFT JOIN**: строки с NULL справа отфильтруются. Хотите «всех клиентов и только оплаченные заказы» — условие в `ON ... AND o.status = 'PAID'`.
2. **COUNT после LEFT JOIN**: `COUNT(*)` даст 1 клиенту без заказов, нужен `COUNT(o.order_id)`.
3. **Размножение строк**: JOIN «один-ко-многим» повторяет строку родителя. SUM по полю родителя после такого JOIN раздувается — агрегируйте детей до JOIN.
4. **Anti-join** — «у кого нет»: `LEFT JOIN ... WHERE right.id IS NULL` или `NOT EXISTS`.

## Self-join

Таблица соединяется сама с собой под разными алиасами: сотрудник и его руководитель.
```sql
SELECT e.full_name AS employee, m.full_name AS manager
FROM employee e LEFT JOIN employee m ON m.employee_id = e.manager_id;
```
""", tasks=[
    T('m04.1', 'Заказы и имена', "full_name клиента, order_id, status для всех заказов; по order_id.",
      "SELECT c.full_name, o.order_id, o.status FROM customer c JOIN orders o ON o.customer_id = c.customer_id ORDER BY o.order_id;",
      ordered=True, lecture=4),
    T('m04.2', 'Состав заказа', "Состав заказа 101: order_id, имя клиента, название товара, quantity. По product_id.",
      """SELECT o.order_id, c.full_name, p.name AS product, oi.quantity
FROM orders o JOIN customer c ON c.customer_id = o.customer_id
JOIN order_item oi ON oi.order_id = o.order_id
JOIN product p ON p.product_id = oi.product_id
WHERE o.order_id = 101 ORDER BY p.product_id;""", ordered=True, lecture=4, hints=['Нужны 4 таблицы: orders, customer, order_item, product']),
    T('m04.3', 'LEFT JOIN', "Все клиенты и номера их заказов (у кого нет — NULL): full_name, order_id. Сортировка по customer_id, order_id.",
      "SELECT c.full_name, o.order_id FROM customer c LEFT JOIN orders o ON o.customer_id = c.customer_id ORDER BY c.customer_id, o.order_id;",
      ordered=True, lecture=4),
    T('m04.4', 'Считаем с нулями', "Число заказов у каждого клиента, включая тех, у кого их нет: full_name, orders_count.",
      "SELECT c.full_name, COUNT(o.order_id) AS orders_count FROM customer c LEFT JOIN orders o ON o.customer_id = c.customer_id GROUP BY c.customer_id, c.full_name;",
      hints=['COUNT(*) даст Глебу 1 — считайте COUNT(o.order_id)'], lecture=4),
    T('m04.5', 'Условие в ON', """
Оплаченная сумма по каждому клиенту (статус PAID), все клиенты, у кого нет оплат — 0.
Столбцы: full_name, paid_total.
""", """SELECT c.full_name, COALESCE(SUM(oi.quantity * oi.unit_price), 0) AS paid_total
FROM customer c
LEFT JOIN orders o ON o.customer_id = c.customer_id AND o.status = 'PAID'
LEFT JOIN order_item oi ON oi.order_id = o.order_id
GROUP BY c.customer_id, c.full_name;""", level=2, lecture=4,
      hints=["Условие status = 'PAID' — в ON, иначе Вера и Глеб пропадут", 'COALESCE(SUM(...), 0)']),
    T('m04.6', 'FULL JOIN', "Сопоставьте клиентов и подписчиков рассылки по email: full_name, email клиента, email подписчика — все строки с обеих сторон.",
      "SELECT c.full_name, c.email AS customer_email, n.email AS subscriber_email FROM customer c FULL JOIN newsletter_subscriber n ON c.email = n.email;",
      lecture=4),
    T('m04.7', 'Self-join', "Каждый сотрудник (employee) и его руководитель: employee, manager (у CEO — NULL). По employee_id.",
      "SELECT e.full_name AS employee, m.full_name AS manager FROM employee e LEFT JOIN employee m ON m.employee_id = e.manager_id ORDER BY e.employee_id;",
      ordered=True),
    T('m04.8', 'Число подчинённых', "Руководители и число их прямых подчинённых: full_name, reports (только те, у кого подчинённые есть).",
      "SELECT m.full_name, COUNT(*) AS reports FROM employee e JOIN employee m ON m.employee_id = e.manager_id GROUP BY m.employee_id, m.full_name;"),
    T('m04.9', 'Anti-join', "База **market**. Сколько пользователей ни разу не сделали заказ? Одно число.",
      "SELECT COUNT(*) FROM users u LEFT JOIN orders o ON o.user_id = u.user_id WHERE o.order_id IS NULL;", db='market',
      hints=['LEFT JOIN + WHERE o.order_id IS NULL']),
    T('m04.10', 'Выручка по корневым категориям', """
База **market**. Категории образуют дерево (до 3 уровней): товар лежит в листовой категории, у неё может быть родитель,
у родителя — свой родитель. Посчитайте выручку (delivered, quantity × price) по **корневым** категориям:
root_category, revenue. По убыванию выручки.
""", """SELECT COALESCE(c3.name, c2.name, c1.name) AS root_category, SUM(oi.quantity * oi.price) AS revenue
FROM order_items oi
JOIN orders o ON o.order_id = oi.order_id AND o.status = 'delivered'
JOIN products p ON p.product_id = oi.product_id
JOIN categories c1 ON c1.category_id = p.category_id
LEFT JOIN categories c2 ON c2.category_id = c1.parent_id
LEFT JOIN categories c3 ON c3.category_id = c2.parent_id
GROUP BY root_category ORDER BY revenue DESC;""", db='market', ordered=True, level=3,
      hints=['Присоедините categories трижды: категория, родитель, дед', 'Корень = COALESCE(дед, родитель, сама категория)']),
    T('m04.11', 'CROSS JOIN', "Сколько строк даст декартово произведение customer × orders? Выведите одно число запросом.",
      "SELECT COUNT(*) FROM customer CROSS JOIN orders;", lecture=4),
])

M5 = dict(id='m05', title='5. Подзапросы, IN, EXISTS', theory=r"""
# Подзапросы

- **Скалярный** — одно значение: `WHERE price > (SELECT AVG(price) FROM product)`. Вернул 0 строк → NULL, больше одной → ошибка.
- **Набор** — для `IN (SELECT ...)`.
- **EXISTS (SELECT 1 ...)** — есть ли хотя бы одна подходящая строка; что выбрано внутри, не важно.
- **Коррелированный** — ссылается на внешний запрос (`WHERE o.customer_id = c.customer_id`) и логически выполняется для каждой внешней строки.
- **В FROM** — промежуточная таблица с алиасом: `FROM (SELECT ...) AS x`.

## Ловушка NOT IN

```sql
WHERE customer_id NOT IN (SELECT customer_id FROM blocked_list) -- список: 2, NULL
```
`1 <> NULL` → UNKNOWN, поэтому `NOT IN` не вернёт ни одной строки. Для «нет в списке» используйте **NOT EXISTS** или anti-join.

## Что выбрать

| Вопрос | Инструмент |
|---|---|
| дороже среднего | скалярный подзапрос |
| есть оплаченный заказ | EXISTS / IN |
| нет заказов | NOT EXISTS / LEFT JOIN … IS NULL |
| многошаговый отчёт | подзапрос в FROM или CTE |
""", tasks=[
    T('m05.1', 'Дороже среднего', "Товары дороже средней цены: name, price, по убыванию цены.",
      "SELECT name, price FROM product WHERE price > (SELECT AVG(price) FROM product) ORDER BY price DESC;", ordered=True, lecture=5),
    T('m05.2', 'Отклонение от средней', "Для каждого товара: name и разница между ценой и средней ценой (delta). По product_id.",
      "SELECT name, price - (SELECT AVG(price) FROM product) AS delta FROM product ORDER BY product_id;", ordered=True, lecture=5),
    T('m05.3', 'EXISTS', "Клиенты, у которых есть хотя бы один оплаченный (PAID) заказ: full_name. Решите через EXISTS.",
      "SELECT c.full_name FROM customer c WHERE EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.customer_id AND o.status = 'PAID');", lecture=5),
    T('m05.4', 'Ловушка NOT IN', """
Клиенты, которых нет в `blocked_list`: full_name. Сначала попробуйте NOT IN и посмотрите, что получится,
затем решите правильно.
""", "SELECT c.full_name FROM customer c WHERE NOT EXISTS (SELECT 1 FROM blocked_list b WHERE b.customer_id = c.customer_id);",
      lecture=5, level=2, hints=['В blocked_list есть NULL', 'NOT EXISTS не боится NULL']),
    T('m05.5', 'Коррелированный подзапрос', "Для каждого клиента — full_name и число его заказов через подзапрос в SELECT.",
      "SELECT c.full_name, (SELECT COUNT(*) FROM orders o WHERE o.customer_id = c.customer_id) AS orders_count FROM customer c;", lecture=5),
    T('m05.6', 'Подзапрос в FROM', "Заказы с суммой больше 10000: order_id, total.",
      "SELECT x.order_id, x.total FROM (SELECT order_id, SUM(quantity * unit_price) AS total FROM order_item GROUP BY order_id) AS x WHERE x.total > 10000;",
      lecture=5),
    T('m05.7', 'Дороже среднего в своей категории', "База **market**. Товары, цена которых выше средней цены в их категории: name, category_id, price. По product_id.",
      "SELECT p.name, p.category_id, p.price FROM products p WHERE p.price > (SELECT AVG(p2.price) FROM products p2 WHERE p2.category_id = p.category_id) ORDER BY p.product_id;",
      db='market', ordered=True, level=2),
    T('m05.8', 'Активные покупатели', "База **market**. Пользователи с более чем 5 доставленными заказами: user_id, orders. По убыванию orders, затем user_id.",
      "SELECT user_id, COUNT(*) AS orders FROM orders WHERE status = 'delivered' GROUP BY user_id HAVING COUNT(*) > 5 ORDER BY orders DESC, user_id;",
      db='market', ordered=True),
    T('m05.9', 'IN с подзапросом', "База **market**. Сколько пользователей, пришедших из канала 'referral', сделали хотя бы один заказ с промокодом? Одно число.",
      "SELECT COUNT(*) FROM users WHERE channel = 'referral' AND user_id IN (SELECT user_id FROM orders WHERE promo_code IS NOT NULL);",
      db='market'),
])

M6 = dict(id='m06', title='6. CTE и рекурсия', theory=r"""
# CTE: WITH ... AS (...)

CTE — именованный промежуточный результат внутри одного запроса. Запрос читается сверху вниз: «сначала посчитаем totals, потом используем».

```sql
WITH paid AS (
    SELECT order_id, customer_id FROM orders WHERE status = 'PAID'
), totals AS (
    SELECT order_id, SUM(quantity * unit_price) AS total FROM order_item GROUP BY order_id
)
SELECT c.full_name, t.total
FROM paid p JOIN totals t USING (order_id) JOIN customer c USING (customer_id);
```

CTE — про читаемость, а не про скорость: PostgreSQL может встроить CTE в общий план или материализовать его. Проверяем через `EXPLAIN (ANALYZE, BUFFERS)`.

# WITH RECURSIVE

Стартовая часть + `UNION ALL` + рекурсивный шаг, который соединяется с уже найденными строками. Остановка — когда шаг ничего не нашёл.

```sql
WITH RECURSIVE tree AS (
    SELECT id, name, parent_id, 0 AS depth FROM category_tree WHERE id = 2
    UNION ALL
    SELECT c.id, c.name, c.parent_id, t.depth + 1
    FROM category_tree c JOIN tree t ON c.parent_id = t.id
)
SELECT id, name, depth FROM tree;
```

Применения: деревья категорий, оргструктура, **генерация рядов** (дни, числа) — в PostgreSQL для рядов есть `generate_series`, здесь рекурсия:
```sql
WITH RECURSIVE d(day) AS (
    SELECT '2025-12-01'
    UNION ALL
    SELECT date(day, '+1 day') FROM d WHERE day < '2025-12-31'
)
SELECT day FROM d;
```
Защита от циклов: хранить путь посещённых id или ограничивать глубину (`WHERE depth < 20`), в PostgreSQL 14+ — `CYCLE`.
""", tasks=[
    T('m06.1', 'Несколько CTE', "Через CTE: имена клиентов и суммы их оплаченных (PAID) заказов — full_name, total по каждому заказу.",
      """WITH paid AS (SELECT order_id, customer_id FROM orders WHERE status = 'PAID'),
totals AS (SELECT order_id, SUM(quantity * unit_price) AS total FROM order_item GROUP BY order_id)
SELECT c.full_name, t.total FROM paid p JOIN totals t USING (order_id) JOIN customer c USING (customer_id);""", lecture=5),
    T('m06.2', 'Потомки категории', "Все категории внутри «Электроника» (id = 2), включая её саму: id, name, depth (у самой — 0). Сортировка по depth, id.",
      """WITH RECURSIVE tree AS (
  SELECT id, name, parent_id, 0 AS depth FROM category_tree WHERE id = 2
  UNION ALL
  SELECT c.id, c.name, c.parent_id, t.depth + 1 FROM category_tree c JOIN tree t ON c.parent_id = t.id)
SELECT id, name, depth FROM tree ORDER BY depth, id;""", ordered=True, lecture=5, level=2),
    T('m06.3', 'Путь до корня', "Для каждого узла category_tree выведите id и путь от корня: 'Каталог > Электроника > Аксессуары'. По id.",
      """WITH RECURSIVE t AS (
  SELECT id, name AS path FROM category_tree WHERE parent_id IS NULL
  UNION ALL
  SELECT c.id, t.path || ' > ' || c.name FROM category_tree c JOIN t ON c.parent_id = t.id)
SELECT id, path FROM t ORDER BY id;""", ordered=True, level=2, hints=['Стартуйте с корня (parent_id IS NULL) и наращивайте строку пути']),
    T('m06.4', 'Оргструктура', "Все прямые и косвенные подчинённые Игоря Петрова (employee_id = 2): full_name и level (прямые — 1). Сортировка по level, employee_id.",
      """WITH RECURSIVE sub AS (
  SELECT employee_id, full_name, 1 AS level FROM employee WHERE manager_id = 2
  UNION ALL
  SELECT e.employee_id, e.full_name, s.level + 1 FROM employee e JOIN sub s ON e.manager_id = s.employee_id)
SELECT full_name, level FROM sub ORDER BY level, employee_id;""", ordered=True, level=2),
    T('m06.5', 'Ряд чисел', "Рекурсивным CTE выведите числа от 1 до 10 и их квадраты: n, sq.",
      """WITH RECURSIVE s(n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM s WHERE n < 10)
SELECT n, n * n AS sq FROM s;""", db='market'),
    T('m06.6', 'Календарь с нулями', """
База **market**. Для каждого дня декабря 2025 выведите число заказов (любой статус), включая дни без заказов (0).
Столбцы: day ('2025-12-01'), orders. По дню.
""", """WITH RECURSIVE d(day) AS (
  SELECT '2025-12-01' UNION ALL SELECT date(day, '+1 day') FROM d WHERE day < '2025-12-31')
SELECT d.day, COUNT(o.order_id) AS orders
FROM d LEFT JOIN orders o ON date(o.created_at) = d.day
GROUP BY d.day ORDER BY d.day;""", db='market', ordered=True, level=2,
      hints=['Сначала календарь рекурсией, потом LEFT JOIN заказов', 'date(created_at) отрежет время']),
    T('m06.7', 'Средний чек по каналам', """
База **market**. Средний чек доставленных заказов по каналу привлечения пользователя.
Чек заказа = сумма quantity × price его позиций. Столбцы: channel, avg_check (округлить до 2). По убыванию avg_check.
""", """WITH order_totals AS (
  SELECT o.order_id, o.user_id, SUM(oi.quantity * oi.price) AS total
  FROM orders o JOIN order_items oi ON oi.order_id = o.order_id
  WHERE o.status = 'delivered' GROUP BY o.order_id, o.user_id)
SELECT u.channel, round(AVG(t.total), 2) AS avg_check
FROM order_totals t JOIN users u ON u.user_id = t.user_id
GROUP BY u.channel ORDER BY avg_check DESC;""", db='market', ordered=True, level=2,
      hints=['Сначала посчитайте сумму каждого заказа в CTE, потом усредняйте — иначе среднее будет по позициям']),
])

M7 = dict(id='m07', title='7. Оконные функции', theory=r"""
# Оконные функции

GROUP BY сворачивает строки, окно — **добавляет** расчёт к каждой строке.

```sql
функция(...) OVER (
    PARTITION BY ...      -- на какие группы делить (необязательно)
    ORDER BY ...          -- порядок внутри окна
    ROWS BETWEEN ... AND ...  -- рамка (для накопительных и скользящих)
)
```

| Задача | Функция |
|---|---|
| нумерация | `ROW_NUMBER()` |
| рейтинг с пропусками / без | `RANK()` (1,2,2,4) / `DENSE_RANK()` (1,2,2,3) |
| предыдущее / следующее значение | `LAG(x, k, default)` / `LEAD(x)` |
| первое / последнее в окне | `FIRST_VALUE(x)` / `LAST_VALUE(x)` (осторожно с рамкой) |
| накопительный итог | `SUM(x) OVER (ORDER BY d ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)` |
| скользящее среднее 7 дней | `AVG(x) OVER (ORDER BY d ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)` |
| доля от итога | `x * 100.0 / SUM(x) OVER ()` |
| квантили | `NTILE(4) OVER (ORDER BY x)` |

## Важно

- Окна вычисляются **после** WHERE/GROUP BY/HAVING. Поэтому фильтровать по `rn` можно только уровнем выше (CTE). Зато окно можно навесить на агрегат: `SUM(SUM(x)) OVER ()`.
- `ORDER BY` внутри OVER определяет нумерацию/накопление, внешний `ORDER BY` — порядок показа.
- Если в OVER есть ORDER BY без рамки, рамка по умолчанию — `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW` (одинаковые значения ORDER BY попадут вместе). Для накопительных итогов надёжнее явно писать `ROWS`.
- TOP-N в группе: ROW_NUMBER в CTE → `WHERE rn <= N`.
""", tasks=[
    T('m07.1', 'Средняя по категории', "Для каждого товара: name, category_id, price и средняя цена его категории (avg_in_category).",
      "SELECT name, category_id, price, AVG(price) OVER (PARTITION BY category_id) AS avg_in_category FROM product;", lecture=5),
    T('m07.2', 'ROW_NUMBER', "Пронумеруйте товары внутри категории от дорогих к дешёвым (при равенстве — по product_id): category_id, name, price, rn. Сортировка по category_id, rn.",
      "SELECT category_id, name, price, ROW_NUMBER() OVER (PARTITION BY category_id ORDER BY price DESC, product_id) AS rn FROM product ORDER BY category_id, rn;",
      ordered=True, lecture=5),
    T('m07.3', 'RANK и DENSE_RANK', "По seller_monthly: name, sales, RANK и DENSE_RANK по убыванию продаж. Сортировка по sales убыв., name.",
      "SELECT name, sales, RANK() OVER (ORDER BY sales DESC) AS r, DENSE_RANK() OVER (ORDER BY sales DESC) AS dr FROM seller_monthly ORDER BY sales DESC, name;",
      ordered=True, lecture=5),
    T('m07.4', 'Накопительный итог', "Суммы заказов (из order_item) и накопительная сумма в порядке order_id: order_id, total, running_total.",
      """WITH totals AS (SELECT order_id, SUM(quantity * unit_price) AS total FROM order_item GROUP BY order_id)
SELECT order_id, total, SUM(total) OVER (ORDER BY order_id ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_total
FROM totals ORDER BY order_id;""", ordered=True, lecture=5),
    T('m07.5', 'LAG', "Суммы заказов и сумма предыдущего заказа по order_id: order_id, total, prev_total.",
      """WITH totals AS (SELECT order_id, SUM(quantity * unit_price) AS total FROM order_item GROUP BY order_id)
SELECT order_id, total, LAG(total) OVER (ORDER BY order_id) AS prev_total FROM totals ORDER BY order_id;""", ordered=True, lecture=5),
    T('m07.6', 'TOP-2 в категории', "Два самых дорогих товара в каждой категории: name, category_id, price. Сортировка по category_id, price убыв.",
      """WITH ranked AS (SELECT name, category_id, price, ROW_NUMBER() OVER (PARTITION BY category_id ORDER BY price DESC, product_id) AS rn FROM product)
SELECT name, category_id, price FROM ranked WHERE rn <= 2 ORDER BY category_id, price DESC;""", ordered=True, lecture=5,
      hints=['Окно нельзя фильтровать в WHERE того же уровня — оберните в CTE']),
    T('m07.7', 'Доля от итога', "База **market**. Доля каждого канала в пользователях: channel, users, share_pct (округлить до 1). По убыванию users.",
      "SELECT channel, COUNT(*) AS users, round(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS share_pct FROM users GROUP BY channel ORDER BY users DESC;",
      db='market', ordered=True, level=2, hints=['SUM(COUNT(*)) OVER () — окно поверх агрегата']),
    T('m07.8', 'Рост месяц к месяцу', """
База **market**. Выручка доставленных заказов по месяцам, выручка прошлого месяца и рост в % (округлить до 1):
month, revenue, prev_revenue, growth_pct. По месяцу.
""", """WITH m AS (
  SELECT substr(o.created_at, 1, 7) AS month, SUM(oi.quantity * oi.price) AS revenue
  FROM orders o JOIN order_items oi ON oi.order_id = o.order_id
  WHERE o.status = 'delivered' GROUP BY month)
SELECT month, revenue, LAG(revenue) OVER (ORDER BY month) AS prev_revenue,
       round(100.0 * (revenue - LAG(revenue) OVER (ORDER BY month)) / LAG(revenue) OVER (ORDER BY month), 1) AS growth_pct
FROM m ORDER BY month;""", db='market', ordered=True, level=2),
    T('m07.9', 'Скользящее среднее', """
База **market**. Число заказов по дням (любой статус) и скользящее среднее за 7 дней (текущий + 6 предыдущих дней, в которых были заказы),
округлённое до 2. Окно считается по всему году, а вывести нужно только декабрь. Столбцы: day, orders, ma7. По дню.
""", """WITH d AS (SELECT date(created_at) AS day, COUNT(*) AS orders FROM orders GROUP BY day),
w AS (SELECT day, orders, round(AVG(orders) OVER (ORDER BY day ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 2) AS ma7 FROM d)
SELECT day, orders, ma7 FROM w WHERE day >= '2025-12-01' ORDER BY day;""", db='market', ordered=True, level=3,
      hints=['Если отфильтровать декабрь до окна, первые дни декабря потеряют ноябрьскую историю', 'Окно в CTE, фильтр снаружи']),
    T('m07.10', 'Интервалы между заказами', """
База **market**. Для пользователя с user_id = 1010 — все его заказы: order_id, created_at, номер заказа по порядку (order_num)
и сколько дней прошло с предыдущего заказа (days_since_prev, округлить до 1; у первого — NULL). По created_at.
""", """SELECT order_id, created_at,
       ROW_NUMBER() OVER (ORDER BY created_at) AS order_num,
       round(julianday(created_at) - julianday(LAG(created_at) OVER (ORDER BY created_at)), 1) AS days_since_prev
FROM orders WHERE user_id = 1010 ORDER BY created_at;""", db='market', ordered=True, level=2,
      hints=['julianday(a) - julianday(b) — разница в днях']),
    T('m07.11', 'Квартили покупателей', """
База **market**. Разбейте пользователей с доставленными заказами на 4 группы по сумме покупок (NTILE(4), порядок: сумма, затем user_id).
Для каждой группы: quartile, users, min_spent, max_spent. По quartile.
""", """WITH s AS (
  SELECT o.user_id, SUM(oi.quantity * oi.price) AS spent
  FROM orders o JOIN order_items oi ON oi.order_id = o.order_id
  WHERE o.status = 'delivered' GROUP BY o.user_id),
q AS (SELECT user_id, spent, NTILE(4) OVER (ORDER BY spent, user_id) AS quartile FROM s)
SELECT quartile, COUNT(*) AS users, MIN(spent) AS min_spent, MAX(spent) AS max_spent FROM q GROUP BY quartile ORDER BY quartile;""",
      db='market', ordered=True, level=2),
    T('m07.12', 'Первый товар пользователя', """
База **market**. Для пользователей с user_id от 1000 до 1010, у которых есть заказы: user_id и название товара из самой первой
позиции их самого первого заказа (при нескольких позициях — с наименьшим product_id). По user_id.
""", """WITH x AS (
  SELECT o.user_id, p.name,
         ROW_NUMBER() OVER (PARTITION BY o.user_id ORDER BY o.created_at, o.order_id, oi.product_id) AS rn
  FROM orders o JOIN order_items oi ON oi.order_id = o.order_id JOIN products p ON p.product_id = oi.product_id
  WHERE o.user_id BETWEEN 1000 AND 1010)
SELECT user_id, name FROM x WHERE rn = 1 ORDER BY user_id;""", db='market', ordered=True, level=2),
])

M8 = dict(id='m08', title='8. DML и транзакции', theory=r"""
# DML: меняем данные

```sql
INSERT INTO customer (full_name, email) VALUES ('Ирина', 'irina@shop.ru') RETURNING customer_id;
INSERT INTO newsletter_subscriber (email) SELECT email FROM customer WHERE ...;   -- INSERT ... SELECT
UPDATE product SET price = price * 1.1 WHERE category_id = 2;                   -- без WHERE — вся таблица!
DELETE FROM orders WHERE status = 'CANCELLED';                                    -- позиции уйдут по ON DELETE CASCADE
```

**UPSERT** (PostgreSQL и SQLite):
```sql
INSERT INTO customer (full_name, email, city) VALUES ('Анна', 'anna@shop.ru', 'Самара')
ON CONFLICT (email) DO UPDATE SET city = excluded.city;
```

## Транзакции

`BEGIN; ... COMMIT;` — всё или ничего. `ROLLBACK` отменяет. Оформление заказа — классическая транзакция: заказ + позиции + списание остатка. Если одна часть упала, не должно остаться «половины заказа».

Хорошая привычка: сначала `SELECT` с тем же WHERE, потом `UPDATE`/`DELETE`.

**В заданиях этого модуля** каждое выполнение идёт на свежей копии базы, так что ломать не страшно. Проверка запускает ваш скрипт, а затем проверочный SELECT.
""", tasks=[
    T('m08.1', 'INSERT', "Добавьте клиента: id 5, 'Ирина', 'irina@shop.ru', город 'Самара'.",
      "INSERT INTO customer (customer_id, full_name, email, city) VALUES (5, 'Ирина', 'irina@shop.ru', 'Самара');",
      kind='dml', check='SELECT customer_id, full_name, email, city FROM customer ORDER BY customer_id', lecture=4),
    T('m08.2', 'UPDATE', "Поднимите цены всех товаров категории 2 (аксессуары) на 10%.",
      "UPDATE product SET price = price * 1.1 WHERE category_id = 2;",
      kind='dml', check='SELECT product_id, price FROM product ORDER BY product_id', lecture=4),
    T('m08.3', 'DELETE + CASCADE', "Удалите все отменённые заказы (позиции должны удалиться каскадом).",
      "DELETE FROM orders WHERE status = 'CANCELLED';",
      kind='dml', check='SELECT (SELECT COUNT(*) FROM orders), (SELECT COUNT(*) FROM order_item)', lecture=4),
    T('m08.4', 'INSERT ... SELECT', "Подпишите на рассылку всех клиентов, которых в ней ещё нет (email из customer).",
      "INSERT INTO newsletter_subscriber (email) SELECT email FROM customer c WHERE NOT EXISTS (SELECT 1 FROM newsletter_subscriber n WHERE n.email = c.email);",
      kind='dml', check='SELECT email FROM newsletter_subscriber ORDER BY email', level=2),
    T('m08.5', 'UPDATE с подзапросом', "Переведите в статус DONE оплаченные (PAID) заказы на сумму больше 10000.",
      "UPDATE orders SET status = 'DONE' WHERE status = 'PAID' AND (SELECT SUM(quantity * unit_price) FROM order_item oi WHERE oi.order_id = orders.order_id) > 10000;",
      kind='dml', check='SELECT order_id, status FROM orders ORDER BY order_id', level=2),
    T('m08.6', 'Оформить заказ транзакцией', """
Оформите в одной транзакции заказ 105 для Глеба (customer_id 4), статус NEW, created_at '2026-10-05 12:00:00':
мышь (product_id 2) — 1 шт. и коврик (product_id 4) — 2 шт. по текущим ценам из product, и уменьшите их остатки.
""", """BEGIN;
INSERT INTO orders (order_id, customer_id, status, created_at) VALUES (105, 4, 'NEW', '2026-10-05 12:00:00');
INSERT INTO order_item (order_id, product_id, quantity, unit_price)
  SELECT 105, product_id, CASE product_id WHEN 2 THEN 1 ELSE 2 END, price FROM product WHERE product_id IN (2, 4);
UPDATE product SET stock = stock - CASE product_id WHEN 2 THEN 1 ELSE 2 END WHERE product_id IN (2, 4);
COMMIT;""", kind='dml', level=3,
      check="SELECT (SELECT status FROM orders WHERE order_id = 105), (SELECT COUNT(*) FROM order_item WHERE order_id = 105), (SELECT SUM(quantity * unit_price) FROM order_item WHERE order_id = 105), (SELECT stock FROM product WHERE product_id = 2), (SELECT stock FROM product WHERE product_id = 4)"),
    T('m08.7', 'UPSERT', "Анна (anna@shop.ru) переехала в Санкт-Петербург. Одним INSERT ... ON CONFLICT обновите её город (если бы её не было — добавили бы).",
      "INSERT INTO customer (full_name, email, city) VALUES ('Анна', 'anna@shop.ru', 'Санкт-Петербург') ON CONFLICT (email) DO UPDATE SET city = excluded.city;",
      kind='dml', check='SELECT customer_id, full_name, email, city FROM customer ORDER BY customer_id', level=2),
])

M9 = dict(id='m09', title='9. DDL, ограничения, миграции', theory=r"""
# DDL и ограничения

Порядок проектирования: требования → сущности → атрибуты → ключи → связи → обязательность → типы. Таблицы создаются от родителей к детям.

| Ограничение | Смысл |
|---|---|
| PRIMARY KEY | «кто это?» — уникально и не NULL |
| UNIQUE | не повторяется (email, sku) |
| NOT NULL | обязательно |
| CHECK | значение проходит бизнес-правило |
| FOREIGN KEY | ссылка существует; ON DELETE RESTRICT / CASCADE / SET NULL |
| DEFAULT | значение, если столбец не указан |

Ограничения работают при INSERT **и** UPDATE, для сайта, импорта и ручного SQL одинаково.

## PostgreSQL vs SQLite в DDL

| PostgreSQL | В тренажёре (SQLite) |
|---|---|
| `bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY` | `INTEGER PRIMARY KEY` (автонумерация) |
| `numeric(10,2)`, `timestamptz`, `boolean` | `NUMERIC`, `TEXT`, `INTEGER` 0/1 |
| `ALTER TABLE t ALTER COLUMN c SET NOT NULL` | нет — пересоздание таблицы |
| `ALTER TABLE t ADD CONSTRAINT uq UNIQUE (c)` | `CREATE UNIQUE INDEX uq ON t(c)` |
| `ALTER TABLE ... DROP CONSTRAINT` | нет |
| `ADD COLUMN`, `RENAME COLUMN`, `DROP COLUMN` | есть |

## Миграция add → fill → constrain (PostgreSQL)

```sql
BEGIN;
ALTER TABLE product ADD COLUMN sku text;                       -- 1. nullable столбец
UPDATE product SET sku = 'SKU-' || product_id WHERE sku IS NULL; -- 2. заполнить старые строки
ALTER TABLE product ALTER COLUMN sku SET NOT NULL;               -- 3. ужесточить
ALTER TABLE product ADD CONSTRAINT uq_product_sku UNIQUE (sku);
COMMIT;
```

Перенос столбца в другую таблицу: создать новое место → скопировать → проверить → только потом удалить старое.

**Проверка в этом модуле**: после вашего скрипта тренажёр пробует вставлять правильные и неправильные строки — неправильные должны отклоняться ограничениями.
""", tasks=[
    T('m09.1', 'Таблица promo_code', """
Создайте таблицу `promo_code`: promo_code_id — первичный ключ (автонумерация), code — текст, обязательный и уникальный,
discount_percent — целое, обязательное, от 1 до 90, active — целое, обязательное, по умолчанию 1.
""", """CREATE TABLE promo_code (
  promo_code_id INTEGER PRIMARY KEY,
  code TEXT NOT NULL UNIQUE,
  discount_percent INTEGER NOT NULL CHECK (discount_percent BETWEEN 1 AND 90),
  active INTEGER NOT NULL DEFAULT 1
);""", kind='ddl', lecture=3,
      probes=[("INSERT INTO promo_code (code, discount_percent) VALUES ('WELCOME', 10)", True),
              ("INSERT INTO promo_code (code, discount_percent) VALUES ('A', 10), ('A', 20)", False),
              ("INSERT INTO promo_code (code, discount_percent) VALUES ('B', 0)", False),
              ("INSERT INTO promo_code (code, discount_percent) VALUES ('C', 95)", False),
              ("INSERT INTO promo_code (code, discount_percent) VALUES (NULL, 10)", False),
              ("INSERT INTO promo_code (code) VALUES ('D')", False)],
      check="SELECT COUNT(*) FROM pragma_table_info('promo_code') WHERE name = 'active' AND dflt_value IS NOT NULL AND \"notnull\" = 1"),
    T('m09.2', 'Миграция: артикул', """
Добавьте товарам артикул: столбец sku, заполните старые строки значениями 'SKU-' || product_id,
и сделайте sku уникальным (в SQLite — уникальным индексом).
""", """ALTER TABLE product ADD COLUMN sku TEXT;
UPDATE product SET sku = 'SKU-' || product_id WHERE sku IS NULL;
CREATE UNIQUE INDEX uq_product_sku ON product (sku);""", kind='ddl', level=2, lecture=3,
      probes=[("UPDATE product SET sku = 'SKU-1' WHERE product_id = 2", False),
              ("UPDATE product SET sku = 'SKU-NEW' WHERE product_id = 2", True)],
      check='SELECT product_id, sku FROM product ORDER BY product_id'),
    T('m09.3', 'Связь 1:1', """
Создайте таблицу `shipment`: shipment_id — первичный ключ, order_id — обязательный, уникальный, внешний ключ на orders
с удалением каскадом, shipped_at — текст (может быть NULL).
""", """CREATE TABLE shipment (
  shipment_id INTEGER PRIMARY KEY,
  order_id INTEGER NOT NULL UNIQUE REFERENCES orders(order_id) ON DELETE CASCADE,
  shipped_at TEXT
);""", kind='ddl', lecture=3,
      probes=[("INSERT INTO shipment (order_id) VALUES (101)", True),
              ("INSERT INTO shipment (order_id) VALUES (101), (101)", False),
              ("INSERT INTO shipment (order_id) VALUES (999)", False),
              ("INSERT INTO shipment (order_id) VALUES (NULL)", False)],
      after="INSERT INTO shipment (order_id) VALUES (101), (103); DELETE FROM orders WHERE order_id = 101;",
      check='SELECT order_id FROM shipment ORDER BY order_id'),
    T('m09.4', 'M:N: теги товаров', """
Создайте таблицу `product_tag` (product_id, tag): оба обязательны, product_id ссылается на product,
пара (product_id, tag) — составной первичный ключ.
""", """CREATE TABLE product_tag (
  product_id INTEGER NOT NULL REFERENCES product(product_id),
  tag TEXT NOT NULL,
  PRIMARY KEY (product_id, tag)
);""", kind='ddl', lecture=2,
      probes=[("INSERT INTO product_tag VALUES (1, 'игровой'), (1, 'работа'), (2, 'игровой')", True),
              ("INSERT INTO product_tag VALUES (1, 'игровой'), (1, 'игровой')", False),
              ("INSERT INTO product_tag VALUES (99, 'x')", False),
              ("INSERT INTO product_tag VALUES (1, NULL)", False)]),
    T('m09.5', 'RENAME и DROP COLUMN', "В customer переименуйте full_name в name и удалите столбец city.",
      "ALTER TABLE customer RENAME COLUMN full_name TO name;\nALTER TABLE customer DROP COLUMN city;", kind='ddl', lecture=3,
      check="SELECT name FROM pragma_table_info('customer') ORDER BY cid"),
    T('m09.6', 'Отзывы: ON DELETE SET NULL', """
Создайте таблицу `review`: review_id — PK; product_id — обязательный FK на product с ON DELETE CASCADE;
customer_id — необязательный FK на customer с ON DELETE SET NULL; rating — обязательное целое от 1 до 5;
created_at — обязательный текст, по умолчанию CURRENT_TIMESTAMP.
""", """CREATE TABLE review (
  review_id INTEGER PRIMARY KEY,
  product_id INTEGER NOT NULL REFERENCES product(product_id) ON DELETE CASCADE,
  customer_id INTEGER REFERENCES customer(customer_id) ON DELETE SET NULL,
  rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);""", kind='ddl', level=2,
      probes=[("INSERT INTO review (product_id, customer_id, rating) VALUES (1, 1, 5)", True),
              ("INSERT INTO review (product_id, customer_id, rating) VALUES (1, NULL, 4)", True),
              ("INSERT INTO review (product_id, rating) VALUES (1, 6)", False),
              ("INSERT INTO review (product_id, rating) VALUES (99, 3)", False),
              ("INSERT INTO review (product_id, customer_id, rating) VALUES (1, 99, 3)", False)],
      after="INSERT INTO review (product_id, customer_id, rating) VALUES (1, 4, 5), (2, 4, 3); DELETE FROM customer WHERE customer_id = 4;",
      check='SELECT product_id, customer_id, rating FROM review ORDER BY review_id'),
])

M10 = dict(id='m10', title='10. VIEW, триггеры, JSON, индексы', theory=r"""
# Представления

- **VIEW** — сохранённый SELECT. Всегда свежие данные, само по себе не ускоряет. `CREATE OR REPLACE VIEW` (PostgreSQL), в SQLite — `DROP VIEW` + `CREATE VIEW`.
- **MATERIALIZED VIEW** (PostgreSQL) — сохранённый результат, нужен `REFRESH MATERIALIZED VIEW` (CONCURRENTLY — с UNIQUE-индексом). В SQLite нет: аналог — таблица `CREATE TABLE ... AS SELECT`.

# Триггеры

PostgreSQL: триггерная функция (`RETURNS trigger`, `OLD`/`NEW`, `RETURN NEW`) + `CREATE TRIGGER ... AFTER UPDATE OF price ON product FOR EACH ROW WHEN (OLD.price IS DISTINCT FROM NEW.price) EXECUTE FUNCTION f();`

SQLite пишет тело прямо в триггере:
```sql
CREATE TRIGGER trg_price_audit
AFTER UPDATE OF price ON product
FOR EACH ROW WHEN OLD.price IS NOT NEW.price          -- аналог IS DISTINCT FROM
BEGIN
    INSERT INTO price_audit (product_id, old_price, new_price)
    VALUES (OLD.product_id, OLD.price, NEW.price);
END;
```
Аналог `RAISE EXCEPTION` — `SELECT RAISE(ABORT, 'текст')` внутри BEFORE-триггера. BEFORE в SQLite не может менять NEW (в PostgreSQL может — так делают `updated_at`).

# JSON

| PostgreSQL (jsonb) | SQLite |
|---|---|
| `attributes ->> 'color'` | `attributes ->> 'color'` или `json_extract(attributes, '$.color')` |
| `attributes @> '{"wireless":true}'` | `json_extract(attributes, '$.wireless') = 1` |
| `attributes ? 'ports'` | `json_type(attributes, '$.ports') IS NOT NULL` |
| `jsonb_array_elements_text(attributes -> 'ports')` | `json_each(attributes, '$.ports')` |
| `jsonb_set(...)` | `json_set(attributes, '$.ram_gb', 32)` |

# Индексы

B-tree — `=`, диапазоны, ORDER BY; составной `(a, b)` хорошо работает для фильтра по `a` и `a + b`. Частичный — `WHERE status = 'NEW'`. По выражению — `ON product (lower(name))`. GIN (PostgreSQL) — JSONB, массивы, полнотекст; GiST — диапазоны и геометрия; BRIN — огромные журналы по времени. Каждый индекс замедляет запись.

План запроса: в PostgreSQL `EXPLAIN (ANALYZE, BUFFERS) SELECT ...`, здесь — `EXPLAIN QUERY PLAN SELECT ...` (ищите `USING INDEX` vs `SCAN`).
""", tasks=[
    T('m10.1', 'VIEW', """
Создайте представление `v_order_details` со столбцами: order_id, full_name, product_name, quantity,
amount (quantity × unit_price) — по всем позициям всех заказов.
""", """CREATE VIEW v_order_details AS
SELECT o.order_id, c.full_name, p.name AS product_name, oi.quantity, oi.quantity * oi.unit_price AS amount
FROM orders o JOIN customer c ON c.customer_id = o.customer_id
JOIN order_item oi ON oi.order_id = o.order_id JOIN product p ON p.product_id = oi.product_id;""",
      kind='ddl', lecture=6, check='SELECT order_id, full_name, product_name, quantity, amount FROM v_order_details ORDER BY order_id, product_name'),
    T('m10.2', 'Триггер аудита цен', """
Создайте триггер, который при изменении цены товара пишет строку в `price_audit` (product_id, old_price, new_price).
Если цена не изменилась (UPDATE на то же значение) — запись не нужна.
""", """CREATE TRIGGER trg_price_audit AFTER UPDATE OF price ON product
FOR EACH ROW WHEN OLD.price IS NOT NEW.price
BEGIN
  INSERT INTO price_audit (product_id, old_price, new_price) VALUES (OLD.product_id, OLD.price, NEW.price);
END;""", kind='ddl', level=2, lecture=7,
      after="UPDATE product SET price = 85000 WHERE product_id = 1; UPDATE product SET price = 85000 WHERE product_id = 1; UPDATE product SET price = price + 100 WHERE product_id IN (2, 3);",
      check='SELECT product_id, old_price, new_price FROM price_audit ORDER BY audit_id'),
    T('m10.3', 'Триггер-проверка', """
Создайте BEFORE INSERT триггер на order_item, который запрещает (RAISE(ABORT, ...)) добавлять позицию,
если quantity больше текущего остатка товара в product.
""", """CREATE TRIGGER trg_check_stock BEFORE INSERT ON order_item
FOR EACH ROW WHEN NEW.quantity > (SELECT stock FROM product WHERE product_id = NEW.product_id)
BEGIN
  SELECT RAISE(ABORT, 'Недостаточно товара на складе');
END;""", kind='ddl', level=2, lecture=8,
      probes=[("INSERT INTO order_item VALUES (102, 1, 10, 80000)", False),
              ("INSERT INTO order_item VALUES (102, 4, 2, 600)", True),
              ("INSERT INTO order_item VALUES (102, 5, 8, 900)", True),
              ("INSERT INTO order_item VALUES (102, 5, 9, 900)", False)]),
    T('m10.4', 'JSON: значение ключа', "Товары, у которых в attributes есть цвет: name, color. По product_id.",
      "SELECT name, attributes ->> 'color' AS color FROM product WHERE attributes ->> 'color' IS NOT NULL ORDER BY product_id;",
      ordered=True, lecture=6),
    T('m10.5', 'JSON: фильтр по признаку', "Беспроводные товары (в attributes wireless = true): name.",
      "SELECT name FROM product WHERE json_extract(attributes, '$.wireless') = 1;", lecture=6,
      hints=["json_extract(attributes, '$.wireless') вернёт 1 для true"]),
    T('m10.6', 'JSON: разворачиваем массив', "Разверните массив ports: по строке на каждый порт — name, port. Сортировка по name, port.",
      "SELECT p.name, j.value AS port FROM product p, json_each(p.attributes, '$.ports') j ORDER BY p.name, j.value;",
      ordered=True, level=2, lecture=6, hints=['json_each(json, путь) возвращает строки с колонкой value — как LATERAL']),
    T('m10.7', 'Индекс под запрос', """
База **market**. Аналитики часто фильтруют заказы так: `WHERE status = 'returned' AND created_at >= '2025-12-01'`.
Создайте составной индекс, который подойдёт этому запросу (первый столбец — status). Проверьте план через EXPLAIN QUERY PLAN.
""", "CREATE INDEX idx_orders_status_created ON orders (status, created_at);", db='market', kind='ddl', level=2, lecture=8,
      check="SELECT EXISTS (SELECT 1 FROM pragma_index_list('orders') il, pragma_index_info(il.name) ii WHERE ii.seqno = 0 AND ii.name = 'status' AND EXISTS (SELECT 1 FROM pragma_index_info(il.name) i2 WHERE i2.seqno = 1 AND i2.name = 'created_at'))"),
    T('m10.8', 'Soft delete + VIEW', """
Реализуйте мягкое удаление: добавьте в product столбец deleted_at (TEXT), пометьте мышь (id 2) удалённой
значением '2026-10-09 12:00:00' и создайте представление `active_product` (product_id, name, price) только с неудалёнными товарами.
""", """ALTER TABLE product ADD COLUMN deleted_at TEXT;
UPDATE product SET deleted_at = '2026-10-09 12:00:00' WHERE product_id = 2;
CREATE VIEW active_product AS SELECT product_id, name, price FROM product WHERE deleted_at IS NULL;""",
      kind='ddl', level=2, lecture=8, check='SELECT product_id, name, price FROM active_product ORDER BY product_id'),
])

MODULES = [M0, M1, M2, M3, M4, M5, M6, M7, M8, M9, M10]
