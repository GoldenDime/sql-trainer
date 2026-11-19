"""Теория модулей 11–16 (аналитика). Примеры — на онлайн-школе из базы uni (lms_*)."""
from course_analytics import DEFS

LMS = r"""
_Примеры этого модуля — на онлайн-школе из базы uni: lms_users (signup_date, channel, variant), lms_events (event_time, event: visit → lesson → homework → purchase), lms_payments (paid_at, amount, plan). Данные за январь–июнь 2025, «сегодня» = 2025-07-01. Задания модуля — на базе market._
"""

MARKET_PAGE = ('Договорённости базы market', r"""
# Договорённости базы market

Задания аналитических модулей решаются на базе **market**. Чтобы ответы были однозначными, в ней приняты определения:
""" + DEFS.replace('## Договорённости в базе market', '') + r"""
Если условие задания определяет метрику иначе, побеждает условие задания.
""")

M11 = [
('Типы дат и времени', r"""
# Дата, время, часовые пояса
""" + LMS + r"""
## Типы в PostgreSQL

| Тип | Пример | Что хранит |
|---|---|---|
| `date` | `2025-03-01` | день без времени |
| `timestamp` | `2025-03-01 14:30:00` | «настенные часы», без пояса |
| `timestamptz` | `2025-03-01 11:30:00+00` | **момент времени**; хранится в UTC, выводится в поясе сессии |
| `interval` | `3 days 04:00:00` | длительность |
| `time` | `14:30:00` | время суток |

`timestamp` против `timestamptz` — главное различие. «14:30» в timestamp не говорит, где это было. Событие в приложении из Москвы и из Владивостока в timestamp без пояса склеится в неправильный порядок. Для событий храните `timestamptz`, для отчёта переводите в нужный пояс:

```pg
SELECT event_time AT TIME ZONE 'Europe/Moscow' AS msk_time FROM events;
SET timezone = 'Europe/Moscow';   -- пояс вывода для всей сессии
```

Отчёт «по дням» зависит от пояса: день по UTC и день по Москве различаются на 3 часа событий. Договоритесь о поясе отчётности заранее.

## Даты в SQLite

Отдельных типов нет. Даты хранят текстом в формате ISO `YYYY-MM-DD HH:MM:SS`: такие строки сортируются и сравниваются правильно, как даты. Функции:

| Функция | Результат |
|---|---|
| `date(t)` | `'2025-03-01'` |
| `datetime(t)` | `'2025-03-01 14:30:00'` |
| `strftime('%Y-%m', t)` | `'2025-03'`; коды: `%Y %m %d %H %M %W %w %j` |
| `julianday(t)` | дробное число дней — для разниц |
| `unixepoch(t)` | секунды с 1970 (SQLite 3.38+) |

```sql
SELECT event_time,
       date(event_time)                AS day,
       strftime('%Y-%m', event_time)   AS month,
       strftime('%H', event_time)      AS hour,
       date_part('isodow', event_time) AS iso_weekday
FROM lms_events LIMIT 5;
```
"""),
('date_trunc, date_part, to_char', r"""
# Округление и части даты

Три похожие операции, которые часто путают:

| Функция | Возвращает | `2025-03-19 14:30` → | Для чего |
|---|---|---|---|
| `date_trunc('month', t)` | **дату-время**, округлённую вниз | `2025-03-01 00:00:00` | группировка по периоду с сохранением года |
| `date_part('month', t)` / `EXTRACT(month FROM t)` | **число** | `3` | сезонность: «все марты вместе» |
| `to_char(t, 'YYYY-MM')` | **строку** | `'2025-03'` | подпись на графике, ключ отчёта |

```sql
SELECT date_trunc('month', event_time) AS month_start,
       date_part('month', event_time)  AS month_num,
       strftime('%Y-%m', event_time)   AS month_label,
       COUNT(*) AS events
FROM lms_events
GROUP BY 1, 2, 3
ORDER BY 1;
```

Ловушка: `GROUP BY date_part('month', t)` на данных за несколько лет сложит январь 2024 и январь 2025 в одну группу. Для динамики — date_trunc, для сезонности — date_part.

## Недели

- `date_trunc('week', t)` — понедельник недели (ISO-неделя).
- `date_part('dow', t)`: 0 — воскресенье … 6 — суббота. `date_part('isodow', t)`: 1 — понедельник … 7 — воскресенье.
- Номер недели `date_part('week', t)` — ISO: первые дни января могут принадлежать 52-й неделе прошлого года. Для ключа недели берите `date_trunc('week', t)`, а не номер.

```sql
SELECT date_trunc('week', signup_date) AS week_start, COUNT(*) AS signups
FROM lms_users
GROUP BY week_start
ORDER BY week_start
LIMIT 6;
```

## Другие единицы

`date_trunc` принимает `'year'`, `'quarter'`, `'month'`, `'week'`, `'day'`, `'hour'`, `'minute'`. `date_part` дополнительно: `'dow'`, `'isodow'`, `'doy'` (день года), `'epoch'` (секунды).
"""),
('Арифметика дат и интервалы', r"""
# Арифметика дат

| Задача | PostgreSQL | SQLite |
|---|---|---|
| прибавить | `d + interval '7 days'`, `d + 7` (для date) | `date(d, '+7 day')`, `datetime(t, '+3 hour')` |
| начало следующего месяца | `date_trunc('month', d) + interval '1 month'` | `date(d, 'start of month', '+1 month')` |
| последний день месяца | `(date_trunc('month', d) + interval '1 month - 1 day')::date` | `date(d, 'start of month', '+1 month', '-1 day')` |
| разница в днях | `d2 - d1` (date) или `extract(epoch FROM t2 - t1) / 86400` | `julianday(d2) - julianday(d1)` |
| разница «годы-месяцы-дни» | `age(d2, d1)` | вычислять вручную |
| возраст в годах | `date_part('year', age(birth))` | `(strftime('%Y', 'now') - strftime('%Y', birth)) - (strftime('%m-%d', 'now') < strftime('%m-%d', birth))` |

```sql
-- через сколько дней после регистрации ученик впервые сделал домашку
SELECT u.user_id, u.signup_date, MIN(e.event_time) AS first_homework,
       CAST(julianday(date(MIN(e.event_time))) - julianday(u.signup_date) AS INTEGER) AS days_to_hw
FROM lms_users u
JOIN lms_events e ON e.user_id = u.user_id AND e.event = 'homework'
GROUP BY u.user_id, u.signup_date
ORDER BY u.user_id
LIMIT 8;
```

`julianday` от даты со временем даёт дробь: 0.5 — полдня. Решите, что вам нужно: «полных суток прошло» (`CAST(... AS INTEGER)` от разницы моментов) или «календарных дней» (разница `date(...)`). Это разные числа: событие в 23:59 и в 00:01 следующего дня — 0 полных суток и 1 календарный день.

## Полуинтервалы

Для фильтра «за март» с временем внутри:

```
t >= '2025-03-01' AND t < '2025-04-01'      -- правильно для date и timestamp
t BETWEEN '2025-03-01' AND '2025-03-31'      -- потеряет 31 марта после 00:00
date(t) BETWEEN ...                          -- правильно, но функция над столбцом мешает индексу
```

## Скользящие периоды

«Активные за последние 30 дней» относительно даты отчёта:

```sql
SELECT COUNT(DISTINCT user_id) AS active_30d
FROM lms_events
WHERE event_time >= date('2025-07-01', '-30 day') AND event_time < '2025-07-01';
```

Граница периода — частый источник расхождений в метриках: 30 дней включая сегодня или нет, «с первого числа» или «скользящий». Записывайте определение рядом с запросом.
"""),
('Календарь и пропуски в рядах', r"""
# Ряды без пропусков

GROUP BY по событиям не покажет дни, когда событий не было. На графике это выглядит как плавная линия там, где на самом деле был провал до нуля, а скользящие средние и LAG считаются неправильно.

Решение — **календарь-каркас** + LEFT JOIN (подробно о генерации рядов в модуле 6):

```sql
WITH RECURSIVE days(day) AS (
  SELECT '2025-06-01'
  UNION ALL SELECT date(day, '+1 day') FROM days WHERE day < '2025-06-30'
),
purchases AS (
  SELECT date(event_time) AS day, COUNT(*) AS n
  FROM lms_events WHERE event = 'purchase'
  GROUP BY date(event_time)
)
SELECT d.day, COALESCE(p.n, 0) AS purchases
FROM days d LEFT JOIN purchases p ON p.day = d.day
ORDER BY d.day;
```

Обратите внимание: агрегация идёт **до** соединения с календарём (в CTE). Если сначала соединить календарь с событиями, а потом считать `COUNT(*)`, у пустых дней получится 1 — уже знакомая ловушка LEFT JOIN.

## Каркас «период × сегмент»

Для отчёта по каналам на каждый месяц нужен CROSS JOIN календаря и списка каналов, иначе канал без регистраций в каком-то месяце просто исчезнет из этого месяца:

```sql
WITH RECURSIVE months(m) AS (
  SELECT '2025-01' UNION ALL
  SELECT strftime('%Y-%m', date(m || '-01', '+1 month')) FROM months WHERE m < '2025-06'
),
channels AS (SELECT DISTINCT channel FROM lms_users)
SELECT mo.m, ch.channel, COUNT(u.user_id) AS signups
FROM months mo CROSS JOIN channels ch
LEFT JOIN lms_users u ON strftime('%Y-%m', u.signup_date) = mo.m AND u.channel = ch.channel
GROUP BY mo.m, ch.channel
ORDER BY mo.m, ch.channel;
```

## Шпаргалка дат

| Похожие | Разница |
|---|---|
| `timestamp` и `timestamptz` | настенные часы и момент времени |
| `date_trunc` и `date_part` | дата начала периода и число |
| `date_part('month')` и `date_trunc('month')` в GROUP BY | сезонность (годы склеиваются) и динамика |
| `dow` и `isodow` | 0 = воскресенье и 1 = понедельник |
| номер недели и `date_trunc('week')` | номер повторяется каждый год, дата — нет |
| `BETWEEN` и полуинтервал | BETWEEN теряет последний день при наличии времени |
| разница моментов и разница дат | полные сутки и календарные дни |
| GROUP BY по событиям и календарь + LEFT JOIN | пропуски исчезают и пропуски становятся нулями |
"""),
MARKET_PAGE,
]

M12 = [
('Как определить метрику', r"""
# Как устроена метрика
""" + LMS + r"""
Любая метрика — это **числитель / знаменатель** за **период** по **единице анализа**. Половина споров «почему у нас разные цифры» — из-за того, что одна из четырёх частей определена по-разному.

| Вопрос | Варианты | Пример расхождения |
|---|---|---|
| что считаем | события, пользователи, сессии, деньги | 7 тысяч событий против 564 активных пользователей |
| кого считаем | все, только активные, только платящие | ARPU против ARPPU |
| за какой период | календарный месяц, скользящие 30 дней, с начала года | MAU за июнь против MAU за 30 дней до 1 июля |
| что исключаем | тестовые аккаунты, возвраты, ботов | выручка gross против net |

```sql
SELECT COUNT(*)                AS events,
       COUNT(DISTINCT user_id) AS users,
       COUNT(DISTINCT user_id || '|' || date(event_time)) AS user_days
FROM lms_events;
```

Три числа про «активность», и все правильные — для своих вопросов: сколько действий, сколько людей, сколько человеко-дней.

## Активность: DAU, WAU, MAU, stickiness

| Метрика | Определение |
|---|---|
| DAU | число уникальных пользователей с активностью за день |
| WAU / MAU | за неделю / месяц (календарный или скользящий — договоритесь) |
| средний DAU за месяц | среднее дневных значений; ≠ MAU / 30 |
| stickiness | средний DAU / MAU: какую долю месяца типичный пользователь возвращается |

```sql
WITH daily AS (
  SELECT date(event_time) AS day, COUNT(DISTINCT user_id) AS dau
  FROM lms_events WHERE event_time >= '2025-06-01' AND event_time < '2025-07-01'
  GROUP BY date(event_time)
),
monthly AS (
  SELECT COUNT(DISTINCT user_id) AS mau
  FROM lms_events WHERE event_time >= '2025-06-01' AND event_time < '2025-07-01'
)
SELECT ROUND(AVG(d.dau), 1) AS avg_dau, m.mau,
       ROUND(AVG(d.dau) * 1.0 / m.mau, 3) AS stickiness
FROM daily d CROSS JOIN monthly m;
```

Почему MAU нельзя получить суммой DAU: один и тот же человек в разные дни посчитается многократно. **Уникальные пользователи не складываются** между периодами и сегментами — их всегда надо пересчитывать от сырых событий.
"""),
('Денежные метрики', r"""
# Деньги

| Метрика | Формула | Знаменатель |
|---|---|---|
| Revenue | сумма оплат | — |
| AOV, средний чек | revenue / число **заказов** (оплат) | заказы |
| ARPU | revenue / **все** пользователи (или активные) | пользователи |
| ARPPU | revenue / **платящие** пользователи | платящие |
| конверсия в оплату | платящие / все | пользователи |
| ARPU = конверсия × ARPPU | | |

```sql
WITH base AS (
  SELECT (SELECT COUNT(*) FROM lms_users)                 AS users,
         COUNT(DISTINCT user_id)                           AS payers,
         COUNT(*)                                          AS payments,
         SUM(amount)                                       AS revenue
  FROM lms_payments
)
SELECT revenue,
       ROUND(1.0 * revenue / payments, 1) AS aov,
       ROUND(1.0 * revenue / users, 1)    AS arpu,
       ROUND(1.0 * revenue / payers, 1)   AS arppu,
       ROUND(1.0 * payers / users, 3)     AS paying_share
FROM base;
```

Проверка: `arpu ≈ paying_share × arppu`. Если тождество не сходится, значит, знаменатели определены по-разному.

## Среднее и медиана

У денежных распределений длинный хвост: несколько годовых подписок по 9900 тянут средний чек вверх. Смотрите и на медиану, и на перцентили:

```sql
SELECT plan, COUNT(*) AS payments, AVG(amount) AS avg_amount, median(amount) AS median_amount
FROM lms_payments GROUP BY plan
UNION ALL
SELECT 'все', COUNT(*), AVG(amount), median(amount) FROM lms_payments;
```

## Gross и net, признание выручки

- **Gross** — всё, что оплачено. **Net** — за вычетом возвратов, отмен, скидок, иногда комиссий и НДС.
- Годовая подписка за 9900 — это 9900 в день оплаты (cash) или 825 в каждом месяце (признанная выручка, MRR). Для динамики бизнеса подписок важна вторая.
- Валюта, налоги, курс на дату — тоже часть определения.

## Маркетинговые метрики

| Метрика | Формула |
|---|---|
| CAC | расходы на привлечение / число привлечённых клиентов (платящих!) |
| CPA, CPL | расходы / действия (регистрации, заявки) |
| ROMI | (доход от канала − расходы) / расходы |
| LTV | доход (или маржа) с клиента за всё время / за N дней |
| LTV / CAC | окупаемость: > 3 — комфортно |
| payback period | через сколько месяцев доход с клиента покрывает CAC |

Чтобы посчитать CAC и ROMI по каналу, расходы и доход должны быть **на одном уровне**: сначала свернуть траты по каналу, отдельно доход по каналу, потом соединить. Соединение «траты по дням × пользователи» размножит строки (модуль 4).
"""),
('Ошибки в метриках', r"""
# Типичные ошибки при подсчёте метрик

## 1. Среднее средних

Конверсия по сегментам и общая конверсия связаны **взвешенно**, а не простым средним:

```sql
WITH seg AS (
  SELECT channel,
         COUNT(*) AS users,
         SUM(EXISTS (SELECT 1 FROM lms_payments p WHERE p.user_id = u.user_id)) AS payers
  FROM lms_users u GROUP BY channel
)
SELECT ROUND(AVG(1.0 * payers / users), 4)     AS "среднее конверсий каналов — неверно",
       ROUND(1.0 * SUM(payers) / SUM(users), 4) AS "общая конверсия — верно"
FROM seg;
```

Простое среднее даёт маленькому каналу такой же вес, как большому.

## 2. Целочисленное деление

`payers / users` при целых даст 0. Всегда `1.0 * a / b` или `CAST`.

## 3. Знаменатель без нулей

«Средний доход на пользователя» через `AVG(amount)` из таблицы оплат — это ARPPU, не ARPU: неплатящих в таблице оплат нет. Нужен LEFT JOIN от всех пользователей и `COALESCE(..., 0)`:

```sql
SELECT ROUND(AVG(COALESCE(rev, 0)), 1) AS arpu,
       ROUND(AVG(rev), 1)              AS arppu
FROM lms_users u
LEFT JOIN (SELECT user_id, SUM(amount) AS rev FROM lms_payments GROUP BY user_id) p
  ON p.user_id = u.user_id;
```

## 4. Сумма уникальных

DAU за 30 дней не складываются в MAU, MAU каналов не складываются в общий MAU, если пользователь бывает в нескольких каналах.

## 5. Парадокс Симпсона

Вариант B может выигрывать в каждом канале и проигрывать в целом (или наоборот), если доли каналов в вариантах разные. Всегда смотрите и разрез, и итог, и **состав** групп.

## 6. Незрелые периоды

Конверсия за последний месяц всегда ниже: пользователи июня ещё не успели заплатить. Сравнивайте когорты на одинаковом «возрасте» (модуль 14).

## 7. Разные часовые пояса и границы периодов

Отчёт, построенный по UTC, и отчёт по Москве разойдутся в каждом дне.

## Шпаргалка

| Похожие | Разница |
|---|---|
| события и уникальные пользователи | `COUNT(*)` и `COUNT(DISTINCT user_id)` |
| средний DAU и MAU / 30 | разные величины |
| AOV, ARPU, ARPPU | на заказ, на всех, на платящих |
| среднее и медиана | медиана устойчива к хвосту |
| gross и net | до и после возвратов и скидок |
| cash и признанная выручка | день оплаты и распределение по периоду |
| CAC и CPA | на клиента и на действие |
| ROI и ROMI | вся прибыль и маркетинговые расходы |
| простое и взвешенное среднее | AVG(долей) и SUM(числ.) / SUM(знам.) |
"""),
MARKET_PAGE,
]

M13 = [
('Виды воронок', r"""
# Воронки
""" + LMS + r"""
Воронка — последовательность шагов и доля пользователей, дошедших до каждого. В онлайн-школе: визит → урок → домашка → оплата.

## Чем воронки отличаются друг от друга

| Вид | Кто считается на шаге N | Особенность |
|---|---|---|
| **открытая** (нестрогая) | у кого есть событие шага N, в любом порядке | проще всего; шаги могут «не сужаться» |
| **закрытая** (по порядку) | у кого шаг N случился **после** шага N−1 | честнее отражает путь пользователя |
| **в окне времени** | шаги по порядку и все в пределах X часов/дней от первого | конверсия «в рамках одного визита/недели» |
| **по сессиям** | единица — сессия, а не пользователь | для UX внутри визита |

И отдельно — **единица**: пользователи (дошёл ли человек хоть когда-нибудь) или события (сколько раз).

## Открытая воронка

```sql
SELECT COUNT(DISTINCT user_id) FILTER (WHERE event = 'visit')    AS visit,
       COUNT(DISTINCT user_id) FILTER (WHERE event = 'lesson')   AS lesson,
       COUNT(DISTINCT user_id) FILTER (WHERE event = 'homework') AS homework,
       COUNT(DISTINCT user_id) FILTER (WHERE event = 'purchase') AS purchase
FROM lms_events;
```

Один проход по таблице, условная агрегация с `COUNT(DISTINCT ...)`.

## Длинная форма и конверсии

Для графика и для конверсий удобнее строка на шаг:

```sql
WITH steps(step_no, event) AS (VALUES (1, 'visit'), (2, 'lesson'), (3, 'homework'), (4, 'purchase')),
counts AS (
  SELECT s.step_no, s.event, COUNT(DISTINCT e.user_id) AS users
  FROM steps s LEFT JOIN lms_events e ON e.event = s.event
  GROUP BY s.step_no, s.event
)
SELECT step_no, event, users,
       ROUND(1.0 * users / LAG(users) OVER (ORDER BY step_no), 3)          AS conv_from_prev,
       ROUND(1.0 * users / FIRST_VALUE(users) OVER (ORDER BY step_no), 3)  AS conv_from_start
FROM counts ORDER BY step_no;
```

| Конверсия | Формула | Что показывает |
|---|---|---|
| шаговая | шаг N / шаг N−1 | где именно теряем людей |
| от начала | шаг N / шаг 1 | итоговую эффективность |
| итоговая | последний / первый | одно число для сравнения вариантов |
"""),
('Закрытая воронка и окно времени', r"""
# Порядок шагов и окно времени

Открытая воронка посчитает пользователя, который сначала купил, а потом посмотрел урок, как прошедшего все шаги. Закрытая требует порядка.

## Через время первого события каждого шага

```sql
WITH firsts AS (
  SELECT user_id,
         MIN(CASE WHEN event = 'visit'    THEN event_time END) AS t_visit,
         MIN(CASE WHEN event = 'lesson'   THEN event_time END) AS t_lesson,
         MIN(CASE WHEN event = 'homework' THEN event_time END) AS t_homework,
         MIN(CASE WHEN event = 'purchase' THEN event_time END) AS t_purchase
  FROM lms_events GROUP BY user_id
)
SELECT COUNT(t_visit) AS visit,
       COUNT(CASE WHEN t_lesson   >= t_visit    THEN 1 END) AS lesson,
       COUNT(CASE WHEN t_homework >= t_lesson   AND t_lesson >= t_visit THEN 1 END) AS homework,
       COUNT(CASE WHEN t_purchase >= t_homework AND t_homework >= t_lesson AND t_lesson >= t_visit THEN 1 END) AS purchase
FROM firsts;
```

В учебных данных все пользователи проходят шаги по порядку, поэтому здесь закрытая воронка совпадает с открытой. В реальных логах (покупка по прямой ссылке без урока, события из разных устройств) они расходятся.

Ограничение подхода: берётся **первое** событие каждого шага. Если первый урок был до первого визита (так не бывает в нашей школе, но бывает в жизни), пользователь выпадет, хотя позже прошёл путь правильно. Строже — искать для каждого шага первое событие **после** найденного предыдущего (коррелированный подзапрос или LEAD).

## Окно времени

«Купил в течение 7 дней после первого визита»:

```sql
WITH firsts AS (
  SELECT user_id,
         MIN(CASE WHEN event = 'visit' THEN event_time END)    AS t_visit,
         MIN(CASE WHEN event = 'purchase' THEN event_time END) AS t_purchase
  FROM lms_events GROUP BY user_id
)
SELECT COUNT(*) AS visitors,
       COUNT(CASE WHEN t_purchase <= datetime(t_visit, '+7 day') THEN 1 END) AS bought_7d,
       COUNT(t_purchase) AS bought_ever
FROM firsts WHERE t_visit IS NOT NULL;
```

Окно — часть определения метрики. «Конверсия в покупку» без окна растёт со временем, и сравнивать её между когортами разного возраста нельзя.

## Через LEAD: следующий шаг сразу за текущим

```sql
WITH seq AS (
  SELECT user_id, event, event_time,
         LEAD(event) OVER (PARTITION BY user_id ORDER BY event_time) AS next_event
  FROM lms_events
)
SELECT event, next_event, COUNT(*) AS transitions
FROM seq
GROUP BY event, next_event
ORDER BY event, transitions DESC;
```

Матрица переходов «что делают после шага» — основа для анализа путей (path analysis): где пользователи уходят, куда возвращаются.

## Подходы

| Техника | Плюсы | Минусы |
|---|---|---|
| `COUNT(DISTINCT) FILTER` | просто, быстро | без порядка |
| MIN(время шага) + сравнения | порядок, окно | только первые события |
| коррелированный поиск «первое после» | строгий порядок | медленно на больших данных |
| LEAD / LAG | переходы, пути | шаги должны идти подряд |
| self-join шагов | гибко | размножение строк, нужен DISTINCT |
"""),
('Сегменты и ошибки воронок', r"""
# Воронка по сегментам

Воронка без разреза говорит «где теряем», с разрезом — «у кого теряем». Добавьте ключ сегмента в GROUP BY:

```sql
SELECT u.channel,
       COUNT(DISTINCT e.user_id) FILTER (WHERE e.event = 'visit')    AS visit,
       COUNT(DISTINCT e.user_id) FILTER (WHERE e.event = 'homework') AS homework,
       COUNT(DISTINCT e.user_id) FILTER (WHERE e.event = 'purchase') AS purchase,
       ROUND(1.0 * COUNT(DISTINCT e.user_id) FILTER (WHERE e.event = 'purchase')
                 / COUNT(DISTINCT e.user_id) FILTER (WHERE e.event = 'visit'), 3) AS cr
FROM lms_users u JOIN lms_events e ON e.user_id = u.user_id
GROUP BY u.channel
ORDER BY cr DESC;
```

## Ошибки

| Ошибка | Что получается | Как правильно |
|---|---|---|
| `COUNT(*)` вместо `COUNT(DISTINCT user_id)` | считаются события: у активных пользователей «конверсия» больше 100% | уникальные пользователи |
| нет порядка шагов | люди, купившие без урока, «прошли» урок | закрытая воронка |
| нет окна | старые когорты выглядят лучше новых | фиксированное окно |
| знаменатель — все пользователи, а не вошедшие в воронку | конверсия занижена | шаг 1 = пользователи с первым событием |
| смешаны платформы с разными шагами | бессмысленные шаги | отдельные воронки |
| сравнение периодов разной длины | | одинаковые окна |

## Шпаргалка

| Похожие | Разница |
|---|---|
| открытая и закрытая воронка | без порядка и с порядком шагов |
| воронка по пользователям и по событиям | дошёл ли человек / сколько раз |
| шаговая конверсия и от начала | N / N−1 и N / 1 |
| конверсия с окном и без | сравнимая между когортами и растущая со временем |
| LAG/LEAD и MIN по шагам | переходы подряд и первые события |
"""),
MARKET_PAGE,
]

M14 = [
('Когорты и retention', r"""
# Когортный анализ
""" + LMS + r"""
**Когорта** — группа пользователей с общим стартовым событием в одном периоде: зарегистрировались в марте, впервые купили на неделе 12. **Возраст (lifetime)** — сколько периодов прошло от старта когорты до события.

Зачем: общие метрики смешивают старых и новых пользователей. Рост DAU может прятать то, что новые пользователи уходят быстрее, чем раньше. Когорты сравнивают «одинаковых по возрасту».

## Виды retention

| Вид | Пользователь удержан на день N, если… | Свойство |
|---|---|---|
| **классический (N-day)** | был активен ровно в день N | кривая может «прыгать» |
| **rolling (unbounded)** | был активен в день N **или позже** | монотонно убывает; ближе к «ещё не ушёл» |
| **по диапазону (bracket)** | был активен в интервале, например 7–13 день | сглаживает шум отдельных дней |

**Churn** (отток) = 1 − retention, но его определение тоже надо задать: «не был активен 30 дней» — самое частое.

## Шаг 1: старт и возраст для каждого события

```sql
SELECT u.user_id, u.signup_date,
       strftime('%Y-%m', u.signup_date) AS cohort,
       CAST(julianday(date(e.event_time)) - julianday(u.signup_date) AS INTEGER) AS day_n
FROM lms_users u JOIN lms_events e ON e.user_id = u.user_id
LIMIT 8;
```

## Шаг 2: retention на D1, D7, D30 (классический)

```sql
WITH act AS (
  SELECT DISTINCT u.user_id, strftime('%Y-%m', u.signup_date) AS cohort,
         CAST(julianday(date(e.event_time)) - julianday(u.signup_date) AS INTEGER) AS day_n
  FROM lms_users u JOIN lms_events e ON e.user_id = u.user_id
),
sizes AS (SELECT strftime('%Y-%m', signup_date) AS cohort, COUNT(*) AS n FROM lms_users GROUP BY 1)
SELECT s.cohort, s.n,
       ROUND(1.0 * COUNT(DISTINCT CASE WHEN a.day_n = 1  THEN a.user_id END) / s.n, 3) AS d1,
       ROUND(1.0 * COUNT(DISTINCT CASE WHEN a.day_n = 7  THEN a.user_id END) / s.n, 3) AS d7,
       ROUND(1.0 * COUNT(DISTINCT CASE WHEN a.day_n >= 30 THEN a.user_id END) / s.n, 3) AS d30_rolling
FROM sizes s LEFT JOIN act a ON a.cohort = s.cohort
GROUP BY s.cohort, s.n
ORDER BY s.cohort;
```

Знаменатель — **размер когорты** из таблицы пользователей, а не число активных в день 0: иначе пользователи, не сделавшие ни одного события, исчезнут из расчёта.

## Незрелые когорты

Июньская когорта на 1 июля физически не может иметь D30. Её D30 = 0 — это не «все ушли», а «ещё не наступило». Либо отсекайте возраст, который когорта не прожила (`WHERE date(signup_date, '+30 day') < '2025-07-01'`), либо показывайте NULL.
"""),
('Когортная таблица: длинная и пивот', r"""
# Когортная таблица

Классический вид: строки — когорты, столбцы — возраст (месяц 0, 1, 2, …), в ячейках — доля активных.

## Длинная форма

```sql
WITH act AS (
  SELECT DISTINCT u.user_id,
         strftime('%Y-%m', u.signup_date) AS cohort,
         (CAST(strftime('%Y', e.event_time) AS INTEGER) * 12 + CAST(strftime('%m', e.event_time) AS INTEGER))
       - (CAST(strftime('%Y', u.signup_date) AS INTEGER) * 12 + CAST(strftime('%m', u.signup_date) AS INTEGER)) AS month_n
  FROM lms_users u JOIN lms_events e ON e.user_id = u.user_id
),
sizes AS (SELECT strftime('%Y-%m', signup_date) AS cohort, COUNT(*) AS n FROM lms_users GROUP BY 1)
SELECT a.cohort, a.month_n, COUNT(*) AS active, s.n,
       ROUND(1.0 * COUNT(*) / s.n, 3) AS retention
FROM act a JOIN sizes s ON s.cohort = a.cohort
GROUP BY a.cohort, a.month_n, s.n
ORDER BY a.cohort, a.month_n;
```

Номер месяца как `год * 12 + месяц` — простой способ получить разницу в календарных месяцах. В PostgreSQL: `(date_part('year', age(date_trunc('month', e), date_trunc('month', s))) * 12 + date_part('month', age(...)))` или та же арифметика с `extract`.

## Пивот

Из длинной формы пивот делается условной агрегацией (модуль 3):

```
SELECT cohort,
       MAX(CASE WHEN month_n = 0 THEN retention END) AS m0,
       MAX(CASE WHEN month_n = 1 THEN retention END) AS m1,
       ...
FROM long_form GROUP BY cohort;
```

`MAX` здесь не «максимум», а способ вытащить единственное значение из группы. Длинная форма удобнее для BI-инструментов и графиков, пивот — для чтения глазами.

## Месяцы календарные и «по 30 дней»

| Возраст | Как считать | Особенность |
|---|---|---|
| календарный месяц | разница номеров месяцев | регистрация 31 января и активность 1 февраля — уже «месяц 1» |
| 30-дневные окна | `(день_события − день_старта) / 30` | одинаковая длина для всех, но не совпадает с календарём |

Для подписочных продуктов чаще берут календарные месяцы оплат, для приложений — дни и недели от регистрации.
"""),
('LTV и MRR', r"""
# LTV — сколько приносит пользователь

**LTV (lifetime value)** — суммарный доход (или маржа) с пользователя. На практике считают **LTV за N дней** (LTV30, LTV90, LTV180): «сколько в среднем принёс пользователь когорты за первые N дней жизни».

```sql
WITH sizes AS (SELECT strftime('%Y-%m', signup_date) AS cohort, COUNT(*) AS n FROM lms_users GROUP BY 1),
rev AS (
  SELECT strftime('%Y-%m', u.signup_date) AS cohort, SUM(p.amount) AS revenue_90d
  FROM lms_users u
  JOIN lms_payments p ON p.user_id = u.user_id
   AND p.paid_at < datetime(u.signup_date, '+90 day')
  GROUP BY 1
)
SELECT s.cohort, s.n, COALESCE(r.revenue_90d, 0) AS revenue_90d,
       ROUND(1.0 * COALESCE(r.revenue_90d, 0) / s.n, 1) AS ltv90
FROM sizes s LEFT JOIN rev r ON r.cohort = s.cohort
WHERE date(s.cohort || '-01', '+1 month', '+90 day') <= '2025-07-01'   -- только когорты, прожившие 90 дней
ORDER BY s.cohort;
```

Ключевые решения:
- **знаменатель** — все пользователи когорты (это LTV на привлечённого, его сравнивают с CAC), а не платящие;
- **окно** считается от старта **каждого пользователя**, а не от начала месяца когорты;
- когорты, не прожившие окно, исключаются, иначе их LTV занижен.

Накопительную кривую LTV по дням строят оконной `SUM(...) OVER (PARTITION BY cohort ORDER BY day_n)` поверх выручки «когорта × день жизни».

# MRR — регулярная выручка подписок

**MRR (monthly recurring revenue)** — сколько денег в месяц приносят активные подписки. Годовая подписка входит в MRR как 1/12 в каждом месяце.

Разложение изменений MRR между месяцами:

| Компонент | Кто |
|---|---|
| New MRR | платят в этом месяце, не платили никогда раньше |
| Expansion | платят больше, чем в прошлом месяце |
| Contraction | платят меньше |
| Churned MRR | платили в прошлом месяце, в этом — нет |
| Reactivation | вернулись после перерыва |

```sql
WITH monthly AS (
  SELECT user_id, strftime('%Y-%m', paid_at) AS month, SUM(amount) AS paid
  FROM lms_payments WHERE plan = 'month'
  GROUP BY user_id, month
),
flagged AS (
  SELECT m.*,
         LAG(month) OVER (PARTITION BY user_id ORDER BY month) AS prev_month
  FROM monthly m
)
SELECT month,
       SUM(paid) AS mrr,
       COUNT(*) FILTER (WHERE prev_month IS NULL) AS new_payers,
       COUNT(*) FILTER (WHERE prev_month = strftime('%Y-%m', date(month || '-01', '-1 month'))) AS retained,
       COUNT(*) FILTER (WHERE prev_month < strftime('%Y-%m', date(month || '-01', '-1 month'))) AS reactivated
FROM flagged
GROUP BY month ORDER BY month;
```

Ушедших (churned) в этой таблице нет — их строки отсутствуют в месяце ухода. Чтобы их посчитать, нужен каркас «пользователь × месяц» (модуль 6) или сравнение множеств прошлого и текущего месяца через NOT EXISTS.

## Шпаргалка

| Похожие | Разница |
|---|---|
| классический и rolling retention | активен в день N и в день N или позже |
| retention и churn | доли оставшихся и ушедших; churn требует определения ухода |
| знаменатель: размер когорты и активные в день 0 | второе теряет неактивных |
| календарный месяц и 30 дней | разные границы возраста |
| LTV на пользователя и на платящего | первое сравнивают с CAC |
| LTV с окном от пользователя и от когорты | первое честнее |
| cash и MRR | дата оплаты и регулярная месячная выручка |
| new, retained, reactivated, churned | компоненты движения MRR и аудитории |
"""),
MARKET_PAGE,
]

M15 = [
('Дедупликация', r"""
# Дедупликация
""" + LMS + r"""
Дубли бывают **полными** (все столбцы совпадают) и **по ключу** (один и тот же человек с разным регистром email, повторная отправка формы через минуту).

| Способ | Что даёт | Когда |
|---|---|---|
| `SELECT DISTINCT *` | убирает полные дубли | дубли полностью одинаковые |
| `GROUP BY ключ` + агрегаты | одна строка на ключ, остальные столбцы — агрегатами (MIN, MAX) | нужна сводка: первая дата, последняя дата |
| `ROW_NUMBER() OVER (PARTITION BY ключ ORDER BY ...) = 1` | **целая** исходная строка, выбранная по правилу | «оставить самую раннюю / самую полную запись» |
| `DISTINCT ON (ключ)` | то же, только PostgreSQL | |
| `DELETE ... WHERE ctid/rowid NOT IN (...)` | физическое удаление дублей | чистка таблицы |

```sql
-- в lms_events бывают повторы одного и того же события пользователя в один день?
SELECT user_id, date(event_time) AS day, event, COUNT(*) AS n
FROM lms_events
GROUP BY user_id, date(event_time), event
HAVING COUNT(*) > 1
ORDER BY n DESC
LIMIT 5;
```

```sql
-- оставить по одному событию каждого типа в день: самое раннее
SELECT user_id, event, event_time FROM (
  SELECT user_id, event, event_time,
         ROW_NUMBER() OVER (PARTITION BY user_id, date(event_time), event ORDER BY event_time) AS rn
  FROM lms_events
) t
WHERE rn = 1
LIMIT 10;
```

`GROUP BY` против `ROW_NUMBER`: GROUP BY с `MIN(event_time)` и `MIN(какой-то_другой_столбец)` может собрать «франкенштейна» — значения из разных исходных строк. ROW_NUMBER всегда возвращает настоящую строку целиком.

## Нормализация ключа

Перед поиском дублей приведите ключ к общему виду: `lower(trim(email))`, номера телефонов без пробелов и скобок, ФИО без двойных пробелов. Иначе `'Ivan@Uni.ru '` и `'ivan@uni.ru'` — разные строки.

## Удаление дублей из таблицы

```sql
BEGIN;
DELETE FROM lms_events
WHERE rowid NOT IN (
  SELECT MIN(rowid) FROM lms_events GROUP BY user_id, event_time, event
);
SELECT changes() AS deleted;   -- полных дублей в lms_events нет, поэтому 0
ROLLBACK;
```

В PostgreSQL вместо rowid — системный столбец `ctid` или, лучше, первичный ключ таблицы.
"""),
('Острова и пробелы: серии и сессии', r"""
# Gaps and islands

Задачи вида «самая длинная серия дней подряд», «разбить события на сессии», «периоды непрерывной подписки» решаются одним приёмом: **пометить начало каждой группы и накопительной суммой превратить метки в номер группы**.

## Сессии: пауза больше 30 минут — новая сессия

```sql
WITH marked AS (
  SELECT user_id, event_time, event,
         CASE WHEN julianday(event_time)
                 - julianday(LAG(event_time) OVER (PARTITION BY user_id ORDER BY event_time)) > 30.0 / 1440
                OR LAG(event_time) OVER (PARTITION BY user_id ORDER BY event_time) IS NULL
              THEN 1 ELSE 0 END AS is_new
  FROM lms_events
),
sessions AS (
  SELECT *, SUM(is_new) OVER (PARTITION BY user_id ORDER BY event_time ROWS UNBOUNDED PRECEDING) AS session_no
  FROM marked
)
SELECT user_id, session_no, MIN(event_time) AS started, COUNT(*) AS events
FROM sessions
WHERE user_id <= 3
GROUP BY user_id, session_no
ORDER BY user_id, session_no;
```

Логика: LAG сравнивает событие с предыдущим → флаг «здесь начинается новая сессия» → накопительная сумма флагов = номер сессии → GROUP BY по номеру.

## Серии подряд идущих дней: трюк «дата минус номер»

Если дни идут подряд, то `дата − ROW_NUMBER()` для всех них одинакова. Разрыв в датах меняет это значение.

```sql
WITH days AS (
  SELECT DISTINCT user_id, date(event_time) AS day FROM lms_events
),
grp AS (
  SELECT user_id, day,
         julianday(day) - ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY day) AS island
  FROM days
)
SELECT user_id, MIN(day) AS streak_start, MAX(day) AS streak_end, COUNT(*) AS streak_days
FROM grp
GROUP BY user_id, island
ORDER BY streak_days DESC, user_id
LIMIT 5;
```

`DISTINCT` по дню обязателен: два события в один день дали бы два разных номера строки при одной дате и сломали трюк.

| Приём | Когда |
|---|---|
| LAG + флаг + накопительная сумма | границы групп задаются условием (пауза, смена значения) |
| значение − ROW_NUMBER | шаг ряда постоянный (дни подряд, номера подряд) |
| разность двух ROW_NUMBER | непрерывные отрезки с одинаковым значением (статус не менялся) |
"""),
('A/B-тесты', r"""
# A/B-тест в SQL

В онлайн-школе у пользователей есть `variant` A или B. Что надо посчитать:

## 1. Проверка разбиения (SRM)

Сначала — равны ли группы по размеру и составу. Если ждали 50/50, а получили 45/55, разбиение сломано (sample ratio mismatch), и результатам верить нельзя.

```sql
SELECT variant, COUNT(*) AS users,
       ROUND(1.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 3) AS share,
       ROUND(AVG(channel = 'ads'), 3) AS ads_share
FROM lms_users GROUP BY variant;
```

## 2. Метрики по группам

```sql
WITH u AS (
  SELECT lu.user_id, lu.variant,
         EXISTS (SELECT 1 FROM lms_payments p WHERE p.user_id = lu.user_id) AS paid,
         COALESCE((SELECT SUM(amount) FROM lms_payments p WHERE p.user_id = lu.user_id), 0) AS revenue
  FROM lms_users lu
)
SELECT variant, COUNT(*) AS n, SUM(paid) AS payers,
       ROUND(AVG(paid), 4) AS cr,
       ROUND(AVG(revenue), 1) AS arpu,
       ROUND(stddev(revenue), 1) AS sd_revenue
FROM u GROUP BY variant;
```

Единица анализа — **пользователь** (как при разбиении). Считать конверсию по событиям или сессиям нельзя: наблюдения одного человека зависимы.

## 3. Значимость разницы долей: z-тест

```
p1, p2 — конверсии групп, n1, n2 — размеры
p = (x1 + x2) / (n1 + n2)                      -- общая доля
se = sqrt(p · (1 − p) · (1/n1 + 1/n2))
z = (p2 − p1) / se                              -- |z| > 1.96 → значимо на уровне 5%
```

```sql
WITH g AS (
  SELECT variant, COUNT(*) AS n,
         SUM(EXISTS (SELECT 1 FROM lms_payments p WHERE p.user_id = u.user_id)) AS x
  FROM lms_users u GROUP BY variant
),
w AS (
  SELECT MAX(CASE WHEN variant = 'A' THEN n END) AS n1, MAX(CASE WHEN variant = 'A' THEN x END) AS x1,
         MAX(CASE WHEN variant = 'B' THEN n END) AS n2, MAX(CASE WHEN variant = 'B' THEN x END) AS x2
  FROM g
)
SELECT 1.0 * x1 / n1 AS p1, 1.0 * x2 / n2 AS p2,
       (1.0 * x2 / n2 - 1.0 * x1 / n1)
       / sqrt((1.0 * (x1 + x2) / (n1 + n2)) * (1 - 1.0 * (x1 + x2) / (n1 + n2)) * (1.0 / n1 + 1.0 / n2)) AS z
FROM w;
```

В наших данных z ≈ 1.7: конверсия B выше, но на уровне 5% разница не значима — типичная ситуация для выборки в 300 человек на группу. Нужно больше пользователей или больше времени.

Для средних (ARPU) — t-тест Уэлча: `t = (m2 − m1) / sqrt(s1²/n1 + s2²/n2)`. Денежные метрики сильно скошены, поэтому часто применяют бутстреп или логарифмирование — это уже делают в Python.

## Ошибки A/B

| Ошибка | Последствие |
|---|---|
| подглядывание и остановка теста при первом «значимом» результате | ложноположительные выводы |
| много метрик и сегментов без поправки | найдётся случайная «значимая» разница |
| единица анализа — события, а не пользователи | заниженная дисперсия, ложная значимость |
| пользователь попал в обе группы | размытый эффект |
| сравнение в первые дни (эффект новизны) | эффект исчезнет |
| SRM не проверен | всё остальное бессмысленно |
"""),
('Сегментация: ABC, RFM, перцентили', r"""
# Сегментация

## ABC / Парето

Сортируем объекты по вкладу, считаем накопленную долю: A — до 80% выручки, B — следующие 15%, C — остальное.

```sql
WITH rev AS (
  SELECT user_id, SUM(amount) AS revenue FROM lms_payments GROUP BY user_id
),
cum AS (
  SELECT user_id, revenue,
         SUM(revenue) OVER (ORDER BY revenue DESC, user_id ROWS UNBOUNDED PRECEDING) * 1.0
         / SUM(revenue) OVER () AS cum_share
  FROM rev
)
SELECT CASE WHEN cum_share <= 0.8 THEN 'A' WHEN cum_share <= 0.95 THEN 'B' ELSE 'C' END AS abc,
       COUNT(*) AS users, SUM(revenue) AS revenue
FROM cum GROUP BY abc ORDER BY abc;
```

`ROWS UNBOUNDED PRECEDING` и уникальный ключ в ORDER BY — чтобы одинаковые суммы не получили одинаковую накопленную долю (вспомните RANGE в модуле 7).

## RFM

Три оценки клиента: **R**ecency — как давно платил, **F**requency — как часто, **M**onetary — сколько. Каждую режут на 3–5 групп, чаще всего через `NTILE`:

```sql
WITH base AS (
  SELECT user_id,
         julianday('2025-07-01') - julianday(MAX(paid_at)) AS recency_days,
         COUNT(*) AS frequency,
         SUM(amount) AS monetary
  FROM lms_payments GROUP BY user_id
)
SELECT user_id, ROUND(recency_days) AS recency_days, frequency, monetary,
       NTILE(3) OVER (ORDER BY recency_days DESC) AS r,     -- 3 = платил недавно
       NTILE(3) OVER (ORDER BY frequency)         AS f,
       NTILE(3) OVER (ORDER BY monetary)          AS m
FROM base
ORDER BY r DESC, f DESC, m DESC
LIMIT 10;
```

Направление сортировки в каждом NTILE выбирается так, чтобы «больше = лучше». NTILE разносит одинаковые значения по разным корзинам; если это критично (много клиентов с frequency = 1), лучше пороги через CASE или `PERCENT_RANK`.

## Перцентили

| Функция | Что даёт |
|---|---|
| `percentile_cont(p)` | интерполированное значение (может не существовать в данных) |
| `percentile_disc(p)` | ближайшее существующее значение |
| `NTILE(n)` | номер корзины для каждой строки |
| `PERCENT_RANK()` / `CUME_DIST()` | положение строки в распределении от 0 до 1 |

```sql
SELECT percentile_cont(amount, 0.5) AS p50, percentile_cont(amount, 0.9) AS p90,
       percentile_cont(amount, 0.99) AS p99
FROM lms_payments;
```

```pg
SELECT percentile_cont(ARRAY[0.5, 0.9, 0.99]) WITHIN GROUP (ORDER BY amount) FROM lms_payments;
```
"""),
('Пивоты и «что делают вместе»', r"""
# Пивоты и пары

## Пивот по сегментам

Условная агрегация (модуль 3) превращает значения сегмента в столбцы:

```sql
SELECT strftime('%Y-%m', signup_date) AS month,
       COUNT(*) FILTER (WHERE channel = 'ads')    AS ads,
       COUNT(*) FILTER (WHERE channel = 'blog')   AS blog,
       COUNT(*) FILTER (WHERE channel = 'friend') AS friend,
       COUNT(*) AS total
FROM lms_users
GROUP BY month ORDER BY month;
```

## Анализ пар (market basket)

«Что встречается вместе» — self-join по общему ключу с условием `a < b`, чтобы каждая пара считалась один раз:

```sql
-- какие курсы университета чаще всего берут вместе
SELECT c1.title AS course_a, c2.title AS course_b, COUNT(*) AS students
FROM enrollments e1
JOIN enrollments e2 ON e2.student_id = e1.student_id AND e1.course_id < e2.course_id
JOIN courses c1 ON c1.course_id = e1.course_id
JOIN courses c2 ON c2.course_id = e2.course_id
GROUP BY c1.title, c2.title
ORDER BY students DESC, course_a;
```

Метрики пар: **support** — доля корзин с парой; **confidence** A→B — доля корзин с A, где есть и B; **lift** — во сколько раз пара встречается чаще, чем при независимости (`support(AB) / (support(A) · support(B))`). Lift > 1 — товары действительно связаны.

Предупреждение о размере: self-join корзин даёт квадратичный рост. На больших данных ограничивают популярные товары или считают по выборке.

## Шпаргалка модуля

| Похожие | Разница |
|---|---|
| `DISTINCT`, `GROUP BY`, `ROW_NUMBER` для дублей | полные дубли / сводка / целая строка по правилу |
| LAG + накопительная сумма и «дата − номер» | границы по условию и ряды с постоянным шагом |
| z-тест и t-тест | доли и средние |
| пользователь и событие как единица A/B | события зависимы — нельзя |
| ABC и RFM | вклад в итог и поведенческие оценки |
| `NTILE` и `PERCENT_RANK` | равные корзины и положение без разрыва ничьих |
| `percentile_cont` и `percentile_disc` | интерполяция и существующее значение |
| `a < b` и `a <> b` в self-join | пара один раз и пара дважды |
"""),
MARKET_PAGE,
]

M16 = [
('Как решать задачу на собеседовании', r"""
# Как решать SQL-задачу на собеседовании

Интервьюер оценивает не только правильный запрос, но и то, как вы думаете.

1. **Уточните определения.** «Активный пользователь» — какое событие? «За месяц» — календарный или 30 дней? Выручка с возвратами или без? Что делать при ничьих?
2. **Назовите краевые случаи.** NULL, пользователи без событий, пустые периоды, дубли, часовые пояса, одинаковые значения при ранжировании.
3. **Опишите план словами**, потом пишите. «Сначала соберу по пользователю дату первой покупки, потом соединю с событиями и посчитаю…»
4. **Пишите по шагам через CTE.** Каждый шаг можно проверить и объяснить.
5. **Проверьте на маленьком примере** и скажите, как бы проверили на реальных данных: сверить итог, посчитать строки до и после JOIN.
6. **Скажите о производительности,** если просят: какие индексы, где размножение, можно ли без коррелированного подзапроса.

## Классические формулировки и приёмы

| Формулировка | Приём |
|---|---|
| N-я по величине зарплата / второй по величине заказ | `DENSE_RANK() = N` (или `LIMIT 1 OFFSET N-1` по DISTINCT) |
| топ-N в каждой группе | `ROW_NUMBER/RANK OVER (PARTITION BY …)` + фильтр снаружи |
| найти дубли | `GROUP BY ключ HAVING COUNT(*) > 1` |
| удалить дубли, оставить одну | `ROW_NUMBER() … = 1` / `MIN(id)` |
| у кого нет … | `NOT EXISTS` / `LEFT JOIN … IS NULL` |
| был активен каждый месяц периода | `GROUP BY user HAVING COUNT(DISTINCT месяц) = число_месяцев` |
| N дней подряд | gaps and islands: `дата − ROW_NUMBER()` |
| рост к прошлому периоду | `LAG` по агрегату периода |
| накопительный итог, скользящее среднее | окно с рамкой `ROWS` |
| доля от итога | `x / SUM(x) OVER ()` |
| медиана без функции медианы | `ROW_NUMBER` и `COUNT` в окне, среднее двух центральных |
| первая покупка каждого | `MIN(дата)` по пользователю или `ROW_NUMBER = 1` |
| сравнить этот год с прошлым | условная агрегация по годам или self-join периода со сдвигом |
"""),
('Разбор классических приёмов', r"""
# Классика на данных uni
""" + LMS + r"""
## Вторая по величине зарплата: три способа

```sql
SELECT
  (SELECT DISTINCT salary FROM teachers ORDER BY salary DESC LIMIT 1 OFFSET 1)          AS "LIMIT OFFSET",
  (SELECT MAX(salary) FROM teachers WHERE salary < (SELECT MAX(salary) FROM teachers))   AS "MAX меньше MAX",
  (SELECT salary FROM (SELECT salary, DENSE_RANK() OVER (ORDER BY salary DESC) AS r FROM teachers) t
   WHERE r = 2 LIMIT 1)                                                                 AS "DENSE_RANK";
```

Обсуждаемые детали: что вернуть, если второй зарплаты нет (NULL, а не пустой результат — поэтому скалярный подзапрос); почему `DISTINCT` (две одинаковые максимальные зарплаты); DENSE_RANK обобщается на N-ю.

## Медиана без функции median

```sql
WITH o AS (
  SELECT salary,
         ROW_NUMBER() OVER (ORDER BY salary) AS rn,
         COUNT(*) OVER () AS n
  FROM teachers
)
SELECT AVG(salary) AS median
FROM o
WHERE rn IN ((n + 1) / 2, (n + 2) / 2);
```

При нечётном n оба номера совпадают, при чётном — берутся два центральных. Работает за счёт целочисленного деления.

## Каждый месяц периода

Ученики, у которых был хотя бы один урок в каждом месяце второго квартала:

```sql
SELECT user_id
FROM lms_events
WHERE event = 'lesson' AND event_time >= '2025-04-01' AND event_time < '2025-07-01'
GROUP BY user_id
HAVING COUNT(DISTINCT strftime('%Y-%m', event_time)) = 3;
```

Ловушка: `COUNT(*) >= 3` вместо `COUNT(DISTINCT месяц) = 3` посчитает трёх уроков за один месяц.

## Период к периоду

```sql
WITH m AS (
  SELECT strftime('%Y-%m', paid_at) AS month, SUM(amount) AS revenue
  FROM lms_payments GROUP BY month
)
SELECT month, revenue,
       LAG(revenue) OVER (ORDER BY month) AS prev,
       ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY month)) / LAG(revenue) OVER (ORDER BY month), 1) AS growth_pct
FROM m ORDER BY month;
```

Обсуждаемые детали: пропущенный месяц (LAG возьмёт позапрошлый — нужен календарь); деление на ноль (`NULLIF`); рост с нуля бесконечен.
"""),
('Теоретические вопросы', r"""
# Частые теоретические вопросы

Попробуйте ответить сами, потом сверьтесь с разделами курса.

| Вопрос | Короткий ответ | Где подробно |
|---|---|---|
| WHERE и HAVING? | строки до группировки и группы после | модуль 3 |
| порядок выполнения SELECT? | FROM → WHERE → GROUP BY → HAVING → окна → SELECT → DISTINCT → ORDER BY → LIMIT | модуль 1 |
| виды JOIN? | INNER, LEFT, RIGHT, FULL, CROSS; плюс self, semi, anti | модуль 4 |
| условие в ON или в WHERE при LEFT JOIN? | ON — отбор пар, WHERE — фильтр результата, превращает LEFT в INNER | модуль 4 |
| UNION и UNION ALL? | без дублей и со всеми строками; ALL быстрее | модуль 4 |
| IN и EXISTS? NOT IN и NOT EXISTS? | для положительной проверки равны; NOT IN ломается от NULL | модуль 5 |
| COUNT(*), COUNT(col), COUNT(DISTINCT col)? | строки, не-NULL, уникальные не-NULL | модуль 3 |
| что такое NULL, почему NULL = NULL не истина? | неизвестное значение, трёхзначная логика | модуль 1 |
| ROW_NUMBER, RANK, DENSE_RANK? | 1,2,3 / 1,1,3 / 1,1,2 | модуль 7 |
| окно и GROUP BY? | окно сохраняет строки | модуль 7 |
| ROWS и RANGE? | физические строки и значения ключа | модуль 7 |
| CTE и подзапрос? временная таблица? VIEW? | время жизни, хранение данных, читаемость | модуль 6 |
| DELETE, TRUNCATE, DROP? | строки с условием, все строки быстро, таблица целиком | модуль 8 |
| ACID? | атомарность, согласованность, изоляция, долговечность | модуль 8 |
| уровни изоляции и аномалии? | RC по умолчанию в PG; RR; Serializable | модуль 8 |
| нормальные формы? | 1НФ атомарность, 2НФ весь ключ, 3НФ нет транзитивных | модуль 9 |
| PRIMARY KEY и UNIQUE? | PK один и NOT NULL, UNIQUE допускает NULL | модуль 9 |
| что такое индекс, когда он не работает? | B-tree и др.; функции над столбцом, ведущий %, малая селективность | модуль 10 |
| составной индекс (a, b), запрос по b? | не поможет (почти) | модуль 10 |
| VIEW и MATERIALIZED VIEW? | запрос и снимок | модуль 10 |
| функция и процедура? | значение в SELECT и CALL с транзакциями | модуль 10 |
| json и jsonb? | текст и двоичный с индексами | модуль 10 |
| Nested Loop, Hash Join, Merge Join? | маленький × индекс, большой равенство, отсортированные | модуль 10 |
| OLTP и OLAP? | много коротких транзакций и тяжёлые аналитические запросы по большим объёмам | ниже |

## OLTP и OLAP

| | OLTP | OLAP |
|---|---|---|
| нагрузка | много коротких транзакций (заказ, оплата) | редкие тяжёлые запросы по истории |
| схема | нормализованная | денормализованная, «звезда»: факты + измерения |
| хранение | строковое (PostgreSQL) | колоночное (ClickHouse, BigQuery, Vertica) |
| запросы | по ключу, единицы строк | агрегаты по миллионам строк |

Аналитик обычно работает с OLAP-хранилищем, куда данные из OLTP-баз переносятся ETL/ELT-процессами. SQL там тот же, но на первый план выходят окна, агрегаты и производительность сканирования.
"""),
MARKET_PAGE,
]

PAGES = {'m11': M11, 'm12': M12, 'm13': M13, 'm14': M14, 'm15': M15, 'm16': M16}
