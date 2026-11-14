"""Модули 11–16: SQL для аналитика и продакт-менеджера (база market)."""
from course_base import T

DEFS = r"""
## Договорённости в базе market

- Данные за 2025 год, «сегодня» = **2026-01-01**.
- **Активный пользователь** — сделал любое событие в `events` (app_open, view_item, add_to_cart, begin_checkout, purchase).
- **Выручка** — сумма `quantity * price` из `order_items` по заказам со статусом `'delivered'` (если в задаче не сказано иначе).
- **Сумма заказа (чек)** — сумма его позиций; стоимость доставки не учитываем.
- Даты в формате `'2025-12-31 18:05:00'`, поэтому `substr(t, 1, 7)` = месяц, `date(t)` = день.
"""


def M(id, title, theory, tasks):
    for t in tasks:
        t['db'] = 'market'
    return dict(id=id, title=title, theory=theory, tasks=tasks)


M11 = M('m11', '11. Даты и время для аналитика', r"""
# Даты и время

Почти любой продуктовый отчёт — это группировка по времени.

| Задача | PostgreSQL | В тренажёре |
|---|---|---|
| начало месяца/недели | `date_trunc('month', t)` | `date_trunc('month', t)` (добавлена) |
| часть даты | `EXTRACT(dow FROM t)` | `date_part('dow', t)`, `date_part('hour', t)` |
| день без времени | `t::date` | `date(t)` |
| сдвиг | `t + interval '7 days'` | `date(t, '+7 day')`, `datetime(t, '-1 month')` |
| разница в днях | `b::date - a::date` | `julianday(b) - julianday(a)` |
| формат | `to_char(t, 'YYYY-MM')` | `strftime('%Y-%m', t)` или `substr(t, 1, 7)` |

`date_part('dow')`: 0 — воскресенье … 6 — суббота (как в PostgreSQL); `'isodow'`: 1 — понедельник … 7 — воскресенье. Неделя в `date_trunc('week')` начинается с понедельника.

## Типичные ошибки

- `BETWEEN '2025-12-01' AND '2025-12-31'` для **timestamp** потеряет весь день 31-го после 00:00. Надёжнее полуинтервал: `t >= '2025-12-01' AND t < '2026-01-01'`.
- Часовые пояса: в PostgreSQL храните `timestamptz`, а для отчёта приводите к нужной зоне `t AT TIME ZONE 'Europe/Moscow'`.
- Медиана устойчивее среднего к выбросам — для «сколько дней до первой покупки» смотрите обе.
""" + DEFS, [
    T('m11.1', 'Заказы по дням недели', "Число заказов по дню недели: dow (1 — понедельник … 7 — воскресенье), orders. По dow.",
      "SELECT date_part('isodow', created_at) AS dow, COUNT(*) AS orders FROM orders GROUP BY dow ORDER BY dow;", ordered=True),
    T('m11.2', 'Заказы по часам', "Число заказов по часу оформления: hour (0–23), orders. По hour.",
      "SELECT date_part('hour', created_at) AS hour, COUNT(*) AS orders FROM orders GROUP BY hour ORDER BY hour;", ordered=True),
    T('m11.3', 'Регистрации по неделям', "Регистрации по неделям (неделя с понедельника) за декабрь 2025: week (дата понедельника), signups. По week.",
      "SELECT date_trunc('week', signup_date) AS week, COUNT(*) AS signups FROM users WHERE signup_date >= '2025-12-01' GROUP BY week ORDER BY week;",
      ordered=True, hints=["date_trunc('week', signup_date)"]),
    T('m11.4', 'Дни до первого заказа', """
Сколько дней проходит от регистрации до первого заказа (любой статус)? Считайте разницу между датами без времени.
Выведите среднее и медиану, округлённые до 1: avg_days, median_days.
""", """WITH f AS (SELECT user_id, MIN(created_at) AS first_order FROM orders GROUP BY user_id)
SELECT round(AVG(julianday(date(f.first_order)) - julianday(u.signup_date)), 1) AS avg_days,
       round(median(julianday(date(f.first_order)) - julianday(u.signup_date)), 1) AS median_days
FROM f JOIN users u ON u.user_id = f.user_id;""", level=2, hints=['median() — агрегат, добавленный в тренажёр (в PostgreSQL: percentile_cont(0.5) WITHIN GROUP (ORDER BY x))']),
    T('m11.5', 'Активные за 30 дней', "Сколько уникальных пользователей было активно за последние 30 дней (событие не раньше date('2026-01-01', '-30 day'))?",
      "SELECT COUNT(DISTINCT user_id) FROM events WHERE event_time >= date('2026-01-01', '-30 day');"),
    T('m11.6', 'Домены почты', """
В `raw_signups` есть дубли email (регистр, пробелы). Посчитайте уникальные нормализованные email по доменам:
domain, users. По убыванию users, затем по domain.
""", """SELECT split_part(e, '@', 2) AS domain, COUNT(*) AS users
FROM (SELECT DISTINCT lower(trim(email)) AS e FROM raw_signups)
GROUP BY domain ORDER BY users DESC, domain;""", ordered=True, level=2),
    T('m11.7', 'Возрастные группы', """
Число пользователей по возрастным группам на 2025 год: 'до 25', '25-34', '35-44', '45+', 'неизвестно'.
Столбцы: age_group, users.
""", """SELECT CASE WHEN birth_year IS NULL THEN 'неизвестно'
            WHEN 2025 - birth_year < 25 THEN 'до 25'
            WHEN 2025 - birth_year < 35 THEN '25-34'
            WHEN 2025 - birth_year < 45 THEN '35-44'
            ELSE '45+' END AS age_group,
       COUNT(*) AS users
FROM users GROUP BY age_group;"""),
    T('m11.8', 'Время жизни пользователя', """
Для пользователей с user_id от 1 до 10: первая и последняя активность (дата события без времени) и lifetime_days —
разница между ними в днях. Столбцы: user_id, first_seen, last_seen, lifetime_days. По user_id.
""", """SELECT user_id, MIN(date(event_time)) AS first_seen, MAX(date(event_time)) AS last_seen,
       julianday(MAX(date(event_time))) - julianday(MIN(date(event_time))) AS lifetime_days
FROM events WHERE user_id BETWEEN 1 AND 10 GROUP BY user_id ORDER BY user_id;""", ordered=True),
])

M12 = M('m12', '12. Продуктовые и денежные метрики', r"""
# Метрики, которые спросят на собеседовании

## Активность
- **DAU / WAU / MAU** — уникальные активные пользователи за день / неделю / месяц. Всегда `COUNT(DISTINCT user_id)`.
- **Stickiness** = средний DAU / MAU — какую долю месяца «средний» пользователь заходит.
- **New vs returning** — впервые ли пользователь сделал действие в этом периоде.

## Деньги
- **GMV** — оборот всех заказов (часто до вычета отмен/возвратов); **выручка** — то, что реально получено (у нас — delivered).
- **AOV** (средний чек) = выручка / число заказов.
- **ARPU** = выручка / все активные пользователи; **ARPPU** = выручка / платящие.
- **Paying share (конверсия в оплату)** = платящие / активные.
- **Gross profit** = выручка − себестоимость; **маржинальность** = gross profit / выручка.
- **CAC** = затраты на канал / привлечённые пользователи; **ROMI** = (прибыль − затраты) / затраты.

## Приёмы
```sql
-- метрика по периодам, считаем чек заказа ДО усреднения
WITH t AS (
    SELECT o.order_id, substr(o.created_at, 1, 7) AS month, SUM(oi.quantity * oi.price) AS total
    FROM orders o JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.status = 'delivered'
    GROUP BY o.order_id, month
)
SELECT month, COUNT(*) AS orders, SUM(total) AS revenue, round(AVG(total), 2) AS aov
FROM t GROUP BY month ORDER BY month;
```
Главная ошибка — усреднить по позициям вместо заказов или посчитать DAU без DISTINCT.
""" + DEFS, [
    T('m12.1', 'DAU', "DAU за декабрь 2025: day, dau. По дню.",
      "SELECT date(event_time) AS day, COUNT(DISTINCT user_id) AS dau FROM events WHERE event_time >= '2025-12-01' GROUP BY day ORDER BY day;", ordered=True),
    T('m12.2', 'Stickiness', "Для декабря 2025: средний DAU (округлить до 1), MAU и stickiness в % (средний DAU / MAU × 100, округлить до 2).",
      """WITH d AS (SELECT date(event_time) AS day, COUNT(DISTINCT user_id) AS dau FROM events WHERE event_time >= '2025-12-01' GROUP BY day),
m AS (SELECT COUNT(DISTINCT user_id) AS mau FROM events WHERE event_time >= '2025-12-01')
SELECT round(AVG(d.dau), 1) AS avg_dau, m.mau, round(100.0 * AVG(d.dau) / m.mau, 2) AS stickiness_pct FROM d, m;""", level=2),
    T('m12.3', 'MAU по месяцам', "MAU по месяцам 2025: month ('2025-01'), mau. По месяцу.",
      "SELECT substr(event_time, 1, 7) AS month, COUNT(DISTINCT user_id) AS mau FROM events GROUP BY month ORDER BY month;", ordered=True),
    T('m12.4', 'Средний чек', "По месяцам: число доставленных заказов, выручка и средний чек (округлить до 2): month, orders, revenue, aov.",
      """WITH t AS (SELECT o.order_id, substr(o.created_at, 1, 7) AS month, SUM(oi.quantity * oi.price) AS total
  FROM orders o JOIN order_items oi ON oi.order_id = o.order_id WHERE o.status = 'delivered' GROUP BY o.order_id, month)
SELECT month, COUNT(*) AS orders, SUM(total) AS revenue, round(AVG(total), 2) AS aov FROM t GROUP BY month ORDER BY month;""",
      ordered=True, level=2, hints=['Сначала сумма каждого заказа (CTE), потом AVG по заказам']),
    T('m12.5', 'ARPU и ARPPU', """
За ноябрь 2025: ARPU = выручка ноября / MAU ноября; ARPPU = выручка ноября / число пользователей с доставленным заказом в ноябре.
Выведите arpu, arppu, округлив до 2.
""", """WITH rev AS (SELECT SUM(oi.quantity * oi.price) AS revenue, COUNT(DISTINCT o.user_id) AS payers
  FROM orders o JOIN order_items oi ON oi.order_id = o.order_id
  WHERE o.status = 'delivered' AND o.created_at >= '2025-11-01' AND o.created_at < '2025-12-01'),
mau AS (SELECT COUNT(DISTINCT user_id) AS mau FROM events WHERE event_time >= '2025-11-01' AND event_time < '2025-12-01')
SELECT round(1.0 * revenue / mau, 2) AS arpu, round(1.0 * revenue / payers, 2) AS arppu FROM rev, mau;""", level=2),
    T('m12.6', 'Новые и вернувшиеся покупатели', """
По месяцам (заказы со статусом не 'cancelled'): new_buyers — пользователи, чей первый такой заказ был в этом месяце,
returning_buyers — те, кто покупал и раньше. Столбцы: month, new_buyers, returning_buyers. По месяцу.
""", """WITH o AS (SELECT user_id, substr(created_at, 1, 7) AS month FROM orders WHERE status <> 'cancelled'),
f AS (SELECT user_id, MIN(month) AS first_month FROM o GROUP BY user_id)
SELECT o.month,
       COUNT(DISTINCT CASE WHEN o.month = f.first_month THEN o.user_id END) AS new_buyers,
       COUNT(DISTINCT CASE WHEN o.month > f.first_month THEN o.user_id END) AS returning_buyers
FROM o JOIN f ON f.user_id = o.user_id GROUP BY o.month ORDER BY o.month;""", ordered=True, level=3,
      hints=['Найдите месяц первой покупки каждого пользователя', 'COUNT(DISTINCT CASE WHEN ... THEN user_id END)']),
    T('m12.7', 'Доля промокодов', """
Выручка по промокодам (NULL заменить на 'без промокода'): promo, orders, revenue, share_pct (доля в общей выручке, округлить до 1).
По убыванию revenue.
""", """WITH t AS (SELECT o.order_id, COALESCE(o.promo_code, 'без промокода') AS promo, SUM(oi.quantity * oi.price) AS total
  FROM orders o JOIN order_items oi ON oi.order_id = o.order_id WHERE o.status = 'delivered' GROUP BY o.order_id, promo)
SELECT promo, COUNT(*) AS orders, SUM(total) AS revenue, round(100.0 * SUM(total) / SUM(SUM(total)) OVER (), 1) AS share_pct
FROM t GROUP BY promo ORDER BY revenue DESC;""", ordered=True, level=2),
    T('m12.8', 'Маржа по брендам', """
Топ-5 брендов по валовой прибыли: brand, revenue, gross_profit = Σ quantity × (цена продажи − cost товара),
margin_pct = gross_profit / revenue × 100 (округлить до 1). Только delivered. По убыванию gross_profit.
""", """SELECT p.brand, SUM(oi.quantity * oi.price) AS revenue,
       SUM(oi.quantity * (oi.price - p.cost)) AS gross_profit,
       round(100.0 * SUM(oi.quantity * (oi.price - p.cost)) / SUM(oi.quantity * oi.price), 1) AS margin_pct
FROM order_items oi JOIN orders o ON o.order_id = oi.order_id JOIN products p ON p.product_id = oi.product_id
WHERE o.status = 'delivered' GROUP BY p.brand ORDER BY gross_profit DESC LIMIT 5;""", ordered=True, level=2),
    T('m12.9', 'CAC по каналам', """
CAC за 2025 год: затраты канала из marketing_spend / число пользователей, пришедших из этого канала.
Столбцы: channel, spend, users, cac (округлить до 2). По возрастанию cac. (organic бесплатен и в marketing_spend его нет.)
""", """WITH s AS (SELECT channel, SUM(spend) AS spend FROM marketing_spend GROUP BY channel),
u AS (SELECT channel, COUNT(*) AS users FROM users GROUP BY channel)
SELECT s.channel, s.spend, u.users, round(1.0 * s.spend / u.users, 2) AS cac FROM s JOIN u ON u.channel = s.channel ORDER BY cac;""",
      ordered=True, level=2, hints=['Агрегируйте затраты и пользователей отдельно, потом соединяйте — иначе JOIN размножит строки']),
    T('m12.10', 'ROMI', """
ROMI по платным каналам за 2025: gross_profit пользователей канала (delivered, quantity × (price − cost)),
spend канала, romi_pct = (gross_profit − spend) / spend × 100 (округлить до 1). Столбцы: channel, gross_profit, spend, romi_pct. По romi_pct убыв.
""", """WITH gp AS (SELECT u.channel, SUM(oi.quantity * (oi.price - p.cost)) AS gross_profit
  FROM orders o JOIN order_items oi ON oi.order_id = o.order_id JOIN products p ON p.product_id = oi.product_id
  JOIN users u ON u.user_id = o.user_id WHERE o.status = 'delivered' GROUP BY u.channel),
s AS (SELECT channel, SUM(spend) AS spend FROM marketing_spend GROUP BY channel)
SELECT s.channel, gp.gross_profit, s.spend, round(100.0 * (gp.gross_profit - s.spend) / s.spend, 1) AS romi_pct
FROM s JOIN gp ON gp.channel = s.channel ORDER BY romi_pct DESC;""", ordered=True, level=3),
])

M13 = M('m13', '13. Воронки и конверсии', r"""
# Воронки

Воронка — последовательность шагов, на каждом часть пользователей отваливается. В market: `app_open → view_item → add_to_cart → begin_checkout → purchase`.

## Два вида воронок

1. **Простая (нестрогая)**: сколько уникальных пользователей сделали каждый шаг за период. Быстро, но не гарантирует порядок.
2. **Строгая**: шаг засчитывается, только если он был **после** предыдущего (и, например, в тот же день/сессию). Честнее, но сложнее.

```sql
SELECT event_name, COUNT(DISTINCT user_id) AS users
FROM events
GROUP BY event_name
ORDER BY CASE event_name WHEN 'app_open' THEN 1 WHEN 'view_item' THEN 2
                         WHEN 'add_to_cart' THEN 3 WHEN 'begin_checkout' THEN 4 ELSE 5 END;
```

Конверсия шага: к предыдущему — `users / LAG(users) OVER (ORDER BY step)`, к началу — `users / FIRST_VALUE(users) OVER (ORDER BY step)`.

Строгую воронку удобно строить через «время первого шага» и коррелированные подзапросы `MIN(event_time) ... WHERE event_time >= предыдущий_шаг`, либо через `LEAD` в окне по событиям пользователя.

Разрезы воронки (устройство, канал, когорта, группа A/B) показывают, где именно теряются люди — это и есть продуктовый инсайт.
""" + DEFS, [
    T('m13.1', 'Простая воронка', "Уникальные пользователи на каждом шаге за весь 2025 год: step (event_name), users. В порядке шагов воронки.",
      """SELECT event_name AS step, COUNT(DISTINCT user_id) AS users FROM events GROUP BY event_name
ORDER BY CASE event_name WHEN 'app_open' THEN 1 WHEN 'view_item' THEN 2 WHEN 'add_to_cart' THEN 3 WHEN 'begin_checkout' THEN 4 ELSE 5 END;""",
      ordered=True, hints=['ORDER BY CASE event_name WHEN ... THEN 1 ... END']),
    T('m13.2', 'Конверсии шагов', """
К той же воронке добавьте конверсию к предыдущему шагу и к первому шагу в % (округлить до 1):
step, users, conv_prev_pct, conv_total_pct. В порядке шагов.
""", """WITH s AS (
  SELECT event_name AS step, COUNT(DISTINCT user_id) AS users,
         CASE event_name WHEN 'app_open' THEN 1 WHEN 'view_item' THEN 2 WHEN 'add_to_cart' THEN 3 WHEN 'begin_checkout' THEN 4 ELSE 5 END AS n
  FROM events GROUP BY event_name)
SELECT step, users,
       round(100.0 * users / LAG(users) OVER (ORDER BY n), 1) AS conv_prev_pct,
       round(100.0 * users / FIRST_VALUE(users) OVER (ORDER BY n), 1) AS conv_total_pct
FROM s ORDER BY n;""", ordered=True, level=2),
    T('m13.3', 'Воронка по устройствам', """
Конверсия из просмотра товара в покупку по устройствам (уникальные пользователи):
device, viewers, buyers, conversion_pct (округлить до 1). По убыванию conversion_pct.
""", """SELECT u.device,
       COUNT(DISTINCT CASE WHEN e.event_name = 'view_item' THEN e.user_id END) AS viewers,
       COUNT(DISTINCT CASE WHEN e.event_name = 'purchase' THEN e.user_id END) AS buyers,
       round(100.0 * COUNT(DISTINCT CASE WHEN e.event_name = 'purchase' THEN e.user_id END)
             / COUNT(DISTINCT CASE WHEN e.event_name = 'view_item' THEN e.user_id END), 1) AS conversion_pct
FROM events e JOIN users u ON u.user_id = e.user_id GROUP BY u.device ORDER BY conversion_pct DESC;""", ordered=True, level=2),
    T('m13.4', 'Строгая воронка в пределах дня', """
Для каждой пары (пользователь, день), где был просмотр товара: берём время первого view_item;
затем первый add_to_cart в тот же день не раньше этого времени; затем первую purchase в тот же день не раньше корзины.
Выведите одной строкой: viewed (пар с просмотром), carted (дошли до корзины), purchased (дошли до покупки).
""", """WITH v AS (
  SELECT user_id, date(event_time) AS day, MIN(event_time) AS v_time FROM events WHERE event_name = 'view_item' GROUP BY user_id, day),
c AS (
  SELECT v.*, (SELECT MIN(e.event_time) FROM events e WHERE e.user_id = v.user_id AND e.event_name = 'add_to_cart'
               AND e.event_time >= v.v_time AND e.event_time < date(v.day, '+1 day')) AS c_time FROM v),
p AS (
  SELECT c.*, (SELECT MIN(e.event_time) FROM events e WHERE e.user_id = c.user_id AND e.event_name = 'purchase'
               AND e.event_time >= c.c_time AND e.event_time < date(c.day, '+1 day')) AS p_time FROM c)
SELECT COUNT(*) AS viewed, COUNT(c_time) AS carted, COUNT(p_time) AS purchased FROM p;""", level=3,
      hints=['Шаг 1: MIN(event_time) просмотров по (user_id, date)', 'Шаг 2: коррелированный подзапрос MIN(event_time) корзины не раньше просмотра', 'COUNT(столбец) не считает NULL — это и есть «дошли»']),
    T('m13.5', 'От корзины до покупки', """
Для каждой покупки найдите последнее добавление в корзину того же пользователя в тот же день не позже покупки.
Выведите медиану времени между ними в минутах (округлить до 1).
""", """SELECT round(median((julianday(p.event_time) - julianday(
         (SELECT MAX(e.event_time) FROM events e WHERE e.user_id = p.user_id AND e.event_name = 'add_to_cart'
            AND e.event_time <= p.event_time AND e.event_time >= date(p.event_time)))) * 1440), 1) AS median_minutes
FROM events p WHERE p.event_name = 'purchase';""", level=3, hints=['(julianday(b) - julianday(a)) * 1440 — минуты']),
    T('m13.6', 'Конверсия по каналам', """
Конверсия пользователей в первую покупку по каналам привлечения: channel, users, buyers (сделали хотя бы один заказ не 'cancelled'),
conversion_pct (округлить до 1). По убыванию conversion_pct.
""", """SELECT u.channel, COUNT(*) AS users,
       SUM(CASE WHEN EXISTS (SELECT 1 FROM orders o WHERE o.user_id = u.user_id AND o.status <> 'cancelled') THEN 1 ELSE 0 END) AS buyers,
       round(100.0 * SUM(CASE WHEN EXISTS (SELECT 1 FROM orders o WHERE o.user_id = u.user_id AND o.status <> 'cancelled') THEN 1 ELSE 0 END) / COUNT(*), 1) AS conversion_pct
FROM users u GROUP BY u.channel ORDER BY conversion_pct DESC;""", ordered=True, level=2),
])

M14 = M('m14', '14. Когорты, retention, LTV', r"""
# Когортный анализ

**Когорта** — пользователи, объединённые моментом старта (обычно месяц регистрации). Сравнивая когорты, видим, улучшается ли продукт.

## Retention

- **Classic (N-day) retention**: доля когорты, активной **ровно в день N** после регистрации (D1, D7, D30).
- **Monthly retention**: доля когорты, активной в месяце k после регистрации (M1, M2, …).
- **Rolling retention**: доля, активная в день N **или позже** — 1 − rolling retention = отток.

Учитывайте **зрелость когорты**: у декабрьской когорты ещё нет D30 — её нельзя сравнивать «в лоб».

## Каркас запроса

```sql
WITH activity AS (SELECT DISTINCT user_id, substr(event_time, 1, 7) AS m FROM events),
     cohort   AS (SELECT user_id, substr(signup_date, 1, 7) AS cohort FROM users),
     x AS (
        SELECT c.cohort, a.user_id,
               (CAST(substr(a.m, 1, 4) AS INTEGER) * 12 + CAST(substr(a.m, 6, 2) AS INTEGER))
             - (CAST(substr(c.cohort, 1, 4) AS INTEGER) * 12 + CAST(substr(c.cohort, 6, 2) AS INTEGER)) AS month_offset
        FROM activity a JOIN cohort c USING (user_id)
     )
SELECT cohort, month_offset, COUNT(DISTINCT user_id) FROM x GROUP BY cohort, month_offset;
```
В PostgreSQL номер месяца удобнее: `EXTRACT(YEAR FROM age(m, cohort)) * 12 + EXTRACT(MONTH FROM age(m, cohort))`.

**Пивот** (когорты строками, месяцы столбцами) — условная агрегация `COUNT(DISTINCT CASE WHEN month_offset = 1 THEN user_id END)`.

## Деньги во времени

- **LTV** — выручка на пользователя когорты за период жизни (LTV30, LTV90…). Сравнивают с CAC: LTV/CAC > 3 — здоровая экономика.
- **MRR** (подписки) — сумма месячных платежей активных подписок на дату; **churn rate** — доля подписок, закончившихся за месяц.
""" + DEFS, [
    T('m14.1', 'Размер когорт', "Размер когорт по месяцу регистрации: cohort_month ('2025-01'), users. По месяцу.",
      "SELECT substr(signup_date, 1, 7) AS cohort_month, COUNT(*) AS users FROM users GROUP BY cohort_month ORDER BY cohort_month;", ordered=True),
    T('m14.2', 'D1 / D7 / D30', """
Для пользователей, зарегистрированных до 2025-12-01: доля активных ровно на 1-й, 7-й и 30-й день после регистрации,
в % (округлить до 1): d1_pct, d7_pct, d30_pct.
""", """WITH a AS (SELECT DISTINCT user_id, date(event_time) AS day FROM events),
u AS (SELECT user_id, signup_date FROM users WHERE signup_date < '2025-12-01')
SELECT round(100.0 * COUNT(DISTINCT CASE WHEN a.day = date(u.signup_date, '+1 day') THEN u.user_id END) / COUNT(DISTINCT u.user_id), 1) AS d1_pct,
       round(100.0 * COUNT(DISTINCT CASE WHEN a.day = date(u.signup_date, '+7 day') THEN u.user_id END) / COUNT(DISTINCT u.user_id), 1) AS d7_pct,
       round(100.0 * COUNT(DISTINCT CASE WHEN a.day = date(u.signup_date, '+30 day') THEN u.user_id END) / COUNT(DISTINCT u.user_id), 1) AS d30_pct
FROM u LEFT JOIN a ON a.user_id = u.user_id;""", level=2, hints=["date(signup_date, '+7 day')", 'Знаменатель — все пользователи когорты, поэтому LEFT JOIN']),
    T('m14.3', 'Когортная таблица (длинная)', """
Monthly retention: для каждой когорты (месяц регистрации) и month_offset от 0 до 3 — число активных пользователей
и retention_pct от размера когорты (округлить до 1). Столбцы: cohort_month, month_offset, active_users, retention_pct.
По когорте и offset.
""", """WITH a AS (SELECT DISTINCT user_id, substr(event_time, 1, 7) AS m FROM events),
u AS (SELECT user_id, substr(signup_date, 1, 7) AS cohort FROM users),
sz AS (SELECT cohort, COUNT(*) AS n FROM u GROUP BY cohort),
x AS (SELECT u.cohort, a.user_id,
        (CAST(substr(a.m, 1, 4) AS INTEGER) * 12 + CAST(substr(a.m, 6, 2) AS INTEGER))
      - (CAST(substr(u.cohort, 1, 4) AS INTEGER) * 12 + CAST(substr(u.cohort, 6, 2) AS INTEGER)) AS month_offset
      FROM a JOIN u ON u.user_id = a.user_id)
SELECT x.cohort AS cohort_month, x.month_offset, COUNT(DISTINCT x.user_id) AS active_users,
       round(100.0 * COUNT(DISTINCT x.user_id) / sz.n, 1) AS retention_pct
FROM x JOIN sz ON sz.cohort = x.cohort WHERE x.month_offset BETWEEN 0 AND 3
GROUP BY x.cohort, x.month_offset ORDER BY cohort_month, x.month_offset;""", ordered=True, level=3,
      hints=['Номер месяца = год × 12 + месяц', 'Размер когорты посчитайте отдельным CTE']),
    T('m14.4', 'Когортный пивот', """
Для когорт с января по сентябрь 2025: cohort_month, users (размер), m1, m2, m3 — retention в месяцах 1–3 в % (округлить до 1).
По когорте.
""", """WITH a AS (SELECT DISTINCT user_id, substr(event_time, 1, 7) AS m FROM events),
u AS (SELECT user_id, substr(signup_date, 1, 7) AS cohort FROM users WHERE signup_date < '2025-10-01'),
x AS (SELECT u.cohort, u.user_id,
        (CAST(substr(a.m, 1, 4) AS INTEGER) * 12 + CAST(substr(a.m, 6, 2) AS INTEGER))
      - (CAST(substr(u.cohort, 1, 4) AS INTEGER) * 12 + CAST(substr(u.cohort, 6, 2) AS INTEGER)) AS k
      FROM u LEFT JOIN a ON a.user_id = u.user_id)
SELECT cohort AS cohort_month, COUNT(DISTINCT user_id) AS users,
       round(100.0 * COUNT(DISTINCT CASE WHEN k = 1 THEN user_id END) / COUNT(DISTINCT user_id), 1) AS m1,
       round(100.0 * COUNT(DISTINCT CASE WHEN k = 2 THEN user_id END) / COUNT(DISTINCT user_id), 1) AS m2,
       round(100.0 * COUNT(DISTINCT CASE WHEN k = 3 THEN user_id END) / COUNT(DISTINCT user_id), 1) AS m3
FROM x GROUP BY cohort ORDER BY cohort;""", ordered=True, level=3, hints=['COUNT(DISTINCT CASE WHEN k = 1 THEN user_id END)']),
    T('m14.5', 'Отток', "Доля пользователей, зарегистрированных до 2025-10-01, у которых не было ни одного события в декабре 2025 (в %, округлить до 1).",
      """SELECT round(100.0 * SUM(CASE WHEN NOT EXISTS (SELECT 1 FROM events e WHERE e.user_id = u.user_id AND e.event_time >= '2025-12-01') THEN 1 ELSE 0 END) / COUNT(*), 1) AS churned_pct
FROM users u WHERE u.signup_date < '2025-10-01';""", level=2),
    T('m14.6', 'LTV90', """
Для когорт январь–сентябрь 2025: users и ltv90 — выручка (delivered) с заказов, сделанных в первые 90 дней после регистрации
(created_at < signup_date + 90 дней), делённая на размер когорты (округлить до 2). Столбцы: cohort_month, users, ltv90.
""", """WITH u AS (SELECT user_id, signup_date, substr(signup_date, 1, 7) AS cohort FROM users WHERE signup_date < '2025-10-01'),
r AS (SELECT o.user_id, SUM(oi.quantity * oi.price) AS rev
      FROM orders o JOIN order_items oi ON oi.order_id = o.order_id JOIN u ON u.user_id = o.user_id
      WHERE o.status = 'delivered' AND o.created_at < date(u.signup_date, '+90 day') GROUP BY o.user_id)
SELECT u.cohort AS cohort_month, COUNT(*) AS users, round(1.0 * COALESCE(SUM(r.rev), 0) / COUNT(*), 2) AS ltv90
FROM u LEFT JOIN r ON r.user_id = u.user_id GROUP BY u.cohort ORDER BY u.cohort;""", ordered=True, level=3,
      hints=['Знаменатель — все пользователи когорты, включая тех, кто ничего не купил']),
    T('m14.7', 'MRR', """
MRR на последний день каждого месяца 2025: подписка активна, если started_at ≤ конец месяца и (ended_at IS NULL или ended_at > конец месяца).
Столбцы: month_end, active_subs, mrr (сумма price_per_month). По месяцу.
""", """WITH RECURSIVE m(ms) AS (SELECT '2025-01-01' UNION ALL SELECT date(ms, '+1 month') FROM m WHERE ms < '2025-12-01'),
e AS (SELECT date(ms, '+1 month', '-1 day') AS month_end FROM m)
SELECT e.month_end, COUNT(s.subscription_id) AS active_subs, COALESCE(SUM(s.price_per_month), 0) AS mrr
FROM e LEFT JOIN subscriptions s ON s.started_at <= e.month_end AND (s.ended_at IS NULL OR s.ended_at > e.month_end)
GROUP BY e.month_end ORDER BY e.month_end;""", ordered=True, level=3,
      hints=["Ряд месяцев — рекурсивный CTE; конец месяца: date(ms, '+1 month', '-1 day')"]),
])

M15 = M('m15', '15. Продвинутые паттерны аналитика', r"""
# Паттерны, которые решают 80% задач

## Дедупликация
`ROW_NUMBER() OVER (PARTITION BY ключ ORDER BY created_at) = 1` — оставить первую запись по ключу. Ключ нормализуем: `lower(trim(email))`.

## A/B-тесты
1. Пользователь учитывается в группе с момента назначения (`assigned_at`).
2. Метрики считаются **на пользователя** группы (конверсия, ARPU), знаменатель — все назначенные.
3. Значимость конверсии — z-тест для двух долей:
```
p_pool = (x_A + x_B) / (n_A + n_B)
z = (p_B − p_A) / sqrt(p_pool · (1 − p_pool) · (1/n_A + 1/n_B))
```
|z| > 1.96 ≈ значимо на уровне 5%. Для денег (ARPU) нужен t-тест/бутстрап — обычно уже в Python.

## Сессии
Новая сессия начинается, если пауза с предыдущим событием больше 30 минут: `LAG(event_time)` → флаг начала → накопительная `SUM(флаг)` = номер сессии.

## Gaps & islands (серии)
Для подряд идущих дней `день − ROW_NUMBER()` постоянен внутри серии — по нему и группируем.

## Парето / ABC
Накопительная доля выручки по товарам от больших к малым: A — до 80%, B — до 95%, C — остальное.

## RFM
Recency (давность последней покупки), Frequency (число заказов), Monetary (сумма) → `NTILE(3)` по каждому → сегмент «333» = лучшие клиенты.

## Перцентили
PostgreSQL: `percentile_cont(0.9) WITHIN GROUP (ORDER BY total)`. В тренажёре: `percentile_cont(total, 0.9)` и `median(total)`.

## Пивот
`SUM(CASE WHEN device = 'ios' THEN x ELSE 0 END) AS ios` или `SUM(x) FILTER (WHERE device = 'ios')`.

## Корзинный анализ
Самосоединение позиций заказа `a.order_id = b.order_id AND a.product_id < b.product_id` даёт пары товаров.
""" + DEFS, [
    T('m15.1', 'Дедупликация', """
В `raw_signups` оставьте по одной (самой ранней по created_at) записи на нормализованный email (lower + trim).
Столбцы: email_norm, full_name, created_at. По created_at.
""", """WITH r AS (SELECT lower(trim(email)) AS email_norm, full_name, created_at,
       ROW_NUMBER() OVER (PARTITION BY lower(trim(email)) ORDER BY created_at) AS rn FROM raw_signups)
SELECT email_norm, full_name, created_at FROM r WHERE rn = 1 ORDER BY created_at;""", ordered=True, level=2),
    T('m15.2', 'A/B-тест: метрики групп', """
Тест new_checkout (таблица ab_test). Для каждой группы: users (назначено), buyers (сделали заказ не 'cancelled'
с момента assigned_at и до 2025-11-01), conversion_pct (buyers / users, округлить до 2) и arpu — сумма этих заказов / users (округлить до 2).
Столбцы: group_name, users, buyers, conversion_pct, arpu. По group_name.
""", """WITH w AS (SELECT a.user_id, a.group_name, o.order_id
  FROM ab_test a LEFT JOIN orders o ON o.user_id = a.user_id AND o.status <> 'cancelled'
       AND o.created_at >= a.assigned_at AND o.created_at < '2025-11-01'),
t AS (SELECT order_id, SUM(quantity * price) AS total FROM order_items GROUP BY order_id)
SELECT w.group_name, COUNT(DISTINCT w.user_id) AS users,
       COUNT(DISTINCT CASE WHEN w.order_id IS NOT NULL THEN w.user_id END) AS buyers,
       round(100.0 * COUNT(DISTINCT CASE WHEN w.order_id IS NOT NULL THEN w.user_id END) / COUNT(DISTINCT w.user_id), 2) AS conversion_pct,
       round(1.0 * COALESCE(SUM(t.total), 0) / COUNT(DISTINCT w.user_id), 2) AS arpu
FROM w LEFT JOIN t ON t.order_id = w.order_id GROUP BY w.group_name ORDER BY w.group_name;""", ordered=True, level=3,
      hints=['Условия на заказ — в ON, чтобы не потерять пользователей без покупок']),
    T('m15.3', 'A/B-тест: z-статистика', """
По тем же определениям посчитайте конверсии групп p_a, p_b (доли, округлить до 4) и z-статистику
разницы двух долей (округлить до 3). Значимо ли изменение?
""", """WITH b AS (SELECT a.group_name,
         EXISTS (SELECT 1 FROM orders o WHERE o.user_id = a.user_id AND o.status <> 'cancelled'
                 AND o.created_at >= a.assigned_at AND o.created_at < '2025-11-01') AS bought
  FROM ab_test a),
g AS (SELECT group_name, COUNT(*) AS n, SUM(bought) AS x FROM b GROUP BY group_name),
p AS (SELECT MAX(CASE WHEN group_name = 'A' THEN 1.0 * x / n END) AS pa, MAX(CASE WHEN group_name = 'B' THEN 1.0 * x / n END) AS pb,
             MAX(CASE WHEN group_name = 'A' THEN n END) AS na, MAX(CASE WHEN group_name = 'B' THEN n END) AS nb,
             1.0 * SUM(x) / SUM(n) AS pp FROM g)
SELECT round(pa, 4) AS p_a, round(pb, 4) AS p_b, round((pb - pa) / sqrt(pp * (1 - pp) * (1.0 / na + 1.0 / nb)), 3) AS z FROM p;""",
      level=3, hints=['Сначала флаг «купил» на пользователя, потом n и x по группам', 'sqrt() доступна']),
    T('m15.4', 'Сессии', """
Разбейте события декабря 2025 на сессии: новая сессия у пользователя начинается, если с его предыдущего события
(в пределах декабря) прошло больше 30 минут или это его первое событие. Выведите sessions (число сессий)
и avg_events_per_session (округлить до 2).
""", """WITH e AS (SELECT event_id, user_id, event_time,
         LAG(event_time) OVER (PARTITION BY user_id ORDER BY event_time, event_id) AS prev
  FROM events WHERE event_time >= '2025-12-01'),
s AS (SELECT user_id, SUM(CASE WHEN prev IS NULL OR (julianday(event_time) - julianday(prev)) * 1440 > 30 THEN 1 ELSE 0 END)
         OVER (PARTITION BY user_id ORDER BY event_time, event_id ROWS UNBOUNDED PRECEDING) AS sid FROM e)
SELECT COUNT(DISTINCT user_id || '-' || sid) AS sessions,
       round(1.0 * COUNT(*) / COUNT(DISTINCT user_id || '-' || sid), 2) AS avg_events_per_session FROM s;""", level=3,
      hints=['LAG → флаг начала сессии → накопительная SUM флага = номер сессии']),
    T('m15.5', 'Самые длинные серии', """
Gaps & islands: для каждого пользователя найдите самую длинную серию подряд идущих дней с активностью
(если таких серий несколько — самую раннюю). Выведите топ-5 пользователей: user_id, streak_days, streak_start.
Сортировка: streak_days убыв., user_id.
""", """WITH d AS (SELECT DISTINCT user_id, date(event_time) AS day FROM events),
g AS (SELECT user_id, day, julianday(day) - ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY day) AS grp FROM d),
s AS (SELECT user_id, MIN(day) AS streak_start, COUNT(*) AS streak_days FROM g GROUP BY user_id, grp),
b AS (SELECT *, ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY streak_days DESC, streak_start) AS rn FROM s)
SELECT user_id, streak_days, streak_start FROM b WHERE rn = 1 ORDER BY streak_days DESC, user_id LIMIT 5;""", ordered=True, level=3,
      hints=['julianday(day) − ROW_NUMBER() одинаков внутри серии подряд идущих дней']),
    T('m15.6', 'ABC-анализ', """
Выручка (delivered) по товарам, накопительная доля от общей выручки в порядке убывания выручки (при равенстве — по product_id),
класс: 'A' — накопительная доля ≤ 80%, 'B' — ≤ 95%, иначе 'C'. Столбцы: product_id, revenue, cum_share_pct (округлить до 1), abc.
Сортировка по revenue убыв., product_id.
""", """WITH r AS (SELECT oi.product_id, SUM(oi.quantity * oi.price) AS revenue
  FROM order_items oi JOIN orders o ON o.order_id = oi.order_id WHERE o.status = 'delivered' GROUP BY oi.product_id),
c AS (SELECT product_id, revenue,
        100.0 * SUM(revenue) OVER (ORDER BY revenue DESC, product_id ROWS UNBOUNDED PRECEDING) / SUM(revenue) OVER () AS cum FROM r)
SELECT product_id, revenue, round(cum, 1) AS cum_share_pct,
       CASE WHEN cum <= 80 THEN 'A' WHEN cum <= 95 THEN 'B' ELSE 'C' END AS abc
FROM c ORDER BY revenue DESC, product_id;""", ordered=True, level=3),
    T('m15.7', 'RFM-сегменты', """
Для пользователей с доставленными заказами: recency_days = дни от даты последнего заказа до 2026-01-01, frequency = число заказов,
monetary = сумма. Баллы: r = NTILE(3) OVER (ORDER BY recency_days DESC, user_id), f = NTILE(3) OVER (ORDER BY frequency, user_id),
m = NTILE(3) OVER (ORDER BY monetary, user_id). Сегмент = r || f || m. Выведите segment и users, по segment.
""", """WITH b AS (SELECT o.user_id, julianday('2026-01-01') - julianday(MAX(date(o.created_at))) AS recency_days,
         COUNT(DISTINCT o.order_id) AS frequency, SUM(oi.quantity * oi.price) AS monetary
  FROM orders o JOIN order_items oi ON oi.order_id = o.order_id WHERE o.status = 'delivered' GROUP BY o.user_id),
s AS (SELECT user_id, NTILE(3) OVER (ORDER BY recency_days DESC, user_id) AS r,
             NTILE(3) OVER (ORDER BY frequency, user_id) AS f,
             NTILE(3) OVER (ORDER BY monetary, user_id) AS m FROM b)
SELECT r || f || m AS segment, COUNT(*) AS users FROM s GROUP BY segment ORDER BY segment;""", ordered=True, level=3,
      hints=['frequency — COUNT(DISTINCT order_id): после JOIN с позициями заказы повторяются!']),
    T('m15.8', 'Перцентили чека', "Для доставленных заказов: средний чек, медиана и 90-й перцентиль суммы заказа (всё округлить до 2): avg_check, p50, p90.",
      """WITH t AS (SELECT o.order_id, SUM(oi.quantity * oi.price) AS total
  FROM orders o JOIN order_items oi ON oi.order_id = o.order_id WHERE o.status = 'delivered' GROUP BY o.order_id)
SELECT round(AVG(total), 2) AS avg_check, round(median(total), 2) AS p50, round(percentile_cont(total, 0.9), 2) AS p90 FROM t;""",
      level=2, hints=['percentile_cont(x, 0.9) — в тренажёре; в PostgreSQL: percentile_cont(0.9) WITHIN GROUP (ORDER BY x)']),
    T('m15.9', 'Пивот по устройствам', "Выручка (delivered) по месяцам в разрезе устройства пользователя: month, android, ios, web. По месяцу.",
      """SELECT substr(o.created_at, 1, 7) AS month,
       SUM(CASE WHEN u.device = 'android' THEN oi.quantity * oi.price ELSE 0 END) AS android,
       SUM(CASE WHEN u.device = 'ios' THEN oi.quantity * oi.price ELSE 0 END) AS ios,
       SUM(CASE WHEN u.device = 'web' THEN oi.quantity * oi.price ELSE 0 END) AS web
FROM orders o JOIN order_items oi ON oi.order_id = o.order_id JOIN users u ON u.user_id = o.user_id
WHERE o.status = 'delivered' GROUP BY month ORDER BY month;""", ordered=True, level=2),
    T('m15.10', 'Что покупают вместе', """
Пять пар товаров, которые чаще всего встречаются в одном заказе (любой статус): product_a < product_b, orders.
Сортировка: orders убыв., product_a, product_b.
""", """SELECT a.product_id AS product_a, b.product_id AS product_b, COUNT(*) AS orders
FROM order_items a JOIN order_items b ON a.order_id = b.order_id AND a.product_id < b.product_id
GROUP BY a.product_id, b.product_id ORDER BY orders DESC, product_a, product_b LIMIT 5;""", ordered=True, level=2),
    T('m15.11', 'Накопленные покупатели', """
По месяцам: new_buyers — пользователи, впервые сделавшие заказ (не 'cancelled') в этом месяце,
cumulative_buyers — накопленное число уникальных покупателей к концу месяца. По месяцу.
""", """WITH f AS (SELECT user_id, MIN(substr(created_at, 1, 7)) AS month FROM orders WHERE status <> 'cancelled' GROUP BY user_id)
SELECT month, COUNT(*) AS new_buyers, SUM(COUNT(*)) OVER (ORDER BY month ROWS UNBOUNDED PRECEDING) AS cumulative_buyers
FROM f GROUP BY month ORDER BY month;""", ordered=True, level=2,
      hints=['Накопительный COUNT(DISTINCT) по окну не работает — считайте по месяцу первой покупки и суммируйте']),
])

M16 = M('m16', '16. Задачи с собеседований', r"""
# Как решать задачи на собеседовании

1. **Уточни определения**: что такое «активный», какой статус заказа считать, включительно ли границы дат, как делить ничьи.
2. **Посмотри на гранулярность**: одна строка = что? (заказ, позиция, событие). Большинство ошибок — агрегат не на том уровне.
3. **Собирай по шагам через CTE** и проверяй промежуточный результат (`SELECT * FROM step LIMIT 10`).
4. **Проверь крайние случаи**: NULL, пользователи без заказов (LEFT JOIN), дубли после JOIN, ничьи в ORDER BY, целочисленное деление.
5. **Проговаривай сложность**: какие индексы помогут, где полный проход.

Классика: N-й по величине, топ-N в группе, пользователи «каждый месяц», разрывы между событиями, дубли, сравнение периодов, накопительные итоги.
""" + DEFS, [
    T('m16.1', 'Второй по величине заказ', "Сумма второго по величине заказа (по сумме позиций, любой статус). Одно число.",
      """WITH t AS (SELECT order_id, SUM(quantity * price) AS total FROM order_items GROUP BY order_id)
SELECT MAX(total) AS second_max FROM t WHERE total < (SELECT MAX(total) FROM t);""", level=2,
      hints=['Или DISTINCT total ORDER BY total DESC LIMIT 1 OFFSET 1', 'Если два заказа делят максимум — «второй по величине» обычно означает следующую сумму']),
    T('m16.2', 'Каждый месяц квартала', "Сколько пользователей делали заказы (не 'cancelled') в каждом из месяцев: октябрь, ноябрь и декабрь 2025?",
      """SELECT COUNT(*) FROM (
  SELECT user_id FROM orders WHERE status <> 'cancelled' AND created_at >= '2025-10-01'
  GROUP BY user_id HAVING COUNT(DISTINCT substr(created_at, 1, 7)) = 3);""", level=2, hints=['HAVING COUNT(DISTINCT месяц) = 3']),
    T('m16.3', 'Топ-3 в каждой корневой категории', """
Три товара с наибольшей выручкой (delivered) в каждой корневой категории (при равенстве — меньший product_id):
root_category, name, revenue, rn. Сортировка по root_category, rn.
""", """WITH RECURSIVE root AS (
  SELECT category_id, name AS root_name FROM categories WHERE parent_id IS NULL
  UNION ALL
  SELECT c.category_id, r.root_name FROM categories c JOIN root r ON c.parent_id = r.category_id),
rev AS (SELECT p.product_id, p.name, r.root_name, SUM(oi.quantity * oi.price) AS revenue
  FROM order_items oi JOIN orders o ON o.order_id = oi.order_id AND o.status = 'delivered'
  JOIN products p ON p.product_id = oi.product_id JOIN root r ON r.category_id = p.category_id
  GROUP BY p.product_id, p.name, r.root_name),
rk AS (SELECT root_name, name, revenue, ROW_NUMBER() OVER (PARTITION BY root_name ORDER BY revenue DESC, product_id) AS rn FROM rev)
SELECT root_name AS root_category, name, revenue, rn FROM rk WHERE rn <= 3 ORDER BY root_category, rn;""", ordered=True, level=3,
      hints=['Корень категории можно найти рекурсией: от корней вниз, протаскивая имя корня']),
    T('m16.4', 'Найти дубли', "Нормализованные email (lower + trim) из raw_signups, встречающиеся больше одного раза: email_norm, cnt. По cnt убыв., email_norm.",
      "SELECT lower(trim(email)) AS email_norm, COUNT(*) AS cnt FROM raw_signups GROUP BY email_norm HAVING COUNT(*) > 1 ORDER BY cnt DESC, email_norm;",
      ordered=True),
    T('m16.5', 'Лучший день месяца', "Для каждого месяца — день с максимальной выручкой (delivered; при равенстве — более ранний): month, day, revenue. По месяцу.",
      """WITH d AS (SELECT date(o.created_at) AS day, SUM(oi.quantity * oi.price) AS revenue
  FROM orders o JOIN order_items oi ON oi.order_id = o.order_id WHERE o.status = 'delivered' GROUP BY day),
r AS (SELECT substr(day, 1, 7) AS month, day, revenue, ROW_NUMBER() OVER (PARTITION BY substr(day, 1, 7) ORDER BY revenue DESC, day) AS rn FROM d)
SELECT month, day, revenue FROM r WHERE rn = 1 ORDER BY month;""", ordered=True, level=2),
    T('m16.6', 'Долгие перерывы', "Сколько пользователей хотя бы раз делали перерыв больше 60 дней между соседними заказами (любой статус)?",
      """WITH x AS (SELECT user_id, julianday(created_at) - julianday(LAG(created_at) OVER (PARTITION BY user_id ORDER BY created_at)) AS gap FROM orders)
SELECT COUNT(DISTINCT user_id) FROM x WHERE gap > 60;""", level=2),
    T('m16.7', 'Сравнение периодов', """
Среди пользователей, у которых были доставленные заказы в ноябре или декабре 2025, сколько потратили в декабре больше, чем в ноябре?
Выведите одно число.
""", """WITH s AS (SELECT o.user_id,
         SUM(CASE WHEN o.created_at >= '2025-11-01' AND o.created_at < '2025-12-01' THEN oi.quantity * oi.price ELSE 0 END) AS nov,
         SUM(CASE WHEN o.created_at >= '2025-12-01' THEN oi.quantity * oi.price ELSE 0 END) AS dec
  FROM orders o JOIN order_items oi ON oi.order_id = o.order_id
  WHERE o.status = 'delivered' AND o.created_at >= '2025-11-01' GROUP BY o.user_id)
SELECT COUNT(*) FROM s WHERE dec > nov;""", level=2),
    T('m16.8', 'Доля повторных покупок', """
Repeat purchase rate: среди пользователей, сделавших хотя бы один доставленный заказ, доля сделавших два и больше (в %, округлить до 1).
""", """WITH c AS (SELECT user_id, COUNT(*) AS n FROM orders WHERE status = 'delivered' GROUP BY user_id)
SELECT round(100.0 * SUM(CASE WHEN n >= 2 THEN 1 ELSE 0 END) / COUNT(*), 1) AS repeat_rate_pct FROM c;"""),
])

MODULES = [M11, M12, M13, M14, M15, M16]
