"""Теория модулей 6–10. Примеры — на демо-базе uni."""

M06 = [
('WITH: общие табличные выражения', r"""
# CTE — WITH

CTE (common table expression) — именованный подзапрос, объявленный перед основным запросом. Внутри запроса им пользуются как таблицей.

```
WITH имя1 AS (SELECT ...),
     имя2 AS (SELECT ... FROM имя1 ...)   -- может ссылаться на предыдущие
SELECT ... FROM имя2 ...;
```

```sql
WITH grades AS (
  SELECT student_id, AVG(grade) AS avg_grade, COUNT(grade) AS exams
  FROM enrollments
  GROUP BY student_id
),
good AS (
  SELECT * FROM grades WHERE avg_grade >= 4.5
)
SELECT s.full_name, g.avg_grade, g.exams
FROM good g JOIN students s ON s.student_id = g.student_id
ORDER BY g.avg_grade DESC;
```

## Зачем

1. **Читаемость.** Запрос читается сверху вниз как последовательность шагов, у каждого шага есть имя. Вложенные подзапросы приходится читать изнутри наружу.
2. **Повторное использование.** На один CTE можно сослаться несколько раз в одном запросе.
3. **Рекурсия.** Только CTE умеет ссылаться сам на себя (WITH RECURSIVE).
4. **Отладка.** Каждый шаг легко проверить отдельно: `SELECT * FROM grades` в конце вместо основного запроса.

## Что надо помнить

- CTE живёт только в пределах **одного** запроса. В следующем запросе его уже нет.
- Имя CTE перекрывает таблицу с тем же именем.
- В PostgreSQL CTE может содержать INSERT/UPDATE/DELETE c RETURNING (см. страницу про модифицирующие CTE).
- Список столбцов можно задать явно: `WITH t(a, b) AS (...)`.

## Константы и маленькие справочники через VALUES

```sql
WITH params(min_grade, city) AS (VALUES (4, 'Москва'))
SELECT s.full_name, e.grade
FROM students s
JOIN enrollments e ON e.student_id = s.student_id
CROSS JOIN params p
WHERE e.grade >= p.min_grade AND s.city = p.city;
```

Так параметры отчёта собраны в одном месте, а не разбросаны по запросу.
"""),
('CTE, подзапрос, VIEW или временная таблица', r"""
# Где хранить промежуточный результат

| | Подзапрос в FROM | CTE | VIEW | Временная таблица | MATERIALIZED VIEW |
|---|---|---|---|---|---|
| время жизни | один запрос | один запрос | постоянно, до DROP | до конца сессии/транзакции | постоянно |
| хранит данные | нет | нет (может материализоваться на время запроса) | нет, только текст запроса | да | да, снимок |
| видят другие запросы | нет | нет | да, все пользователи с правами | только эта сессия | да |
| свежесть | всегда актуален | всегда | всегда | на момент создания | на момент REFRESH |
| индексы | нет | нет | нет (используются индексы таблиц) | можно создать | можно создать |
| рекурсия | нет | да | через рекурсивный CTE внутри | — | — |
| когда брать | короткий одноразовый шаг | многошаговый запрос | повторяемая логика, общая для всех | тяжёлый промежуточный результат, нужный в нескольких запросах | тяжёлый отчёт, допустимо отставание |

```sql
-- подзапрос
SELECT city, n FROM (SELECT city, COUNT(*) AS n FROM students GROUP BY city) t WHERE n > 2;
```

```sql
-- CTE: то же самое
WITH t AS (SELECT city, COUNT(*) AS n FROM students GROUP BY city)
SELECT city, n FROM t WHERE n > 2;
```

```sql
-- временная таблица: живёт в сессии, можно переиспользовать в следующих запросах
CREATE TEMP TABLE city_stats AS
SELECT city, COUNT(*) AS n FROM students GROUP BY city;
SELECT * FROM city_stats WHERE n > 2;
```

(Повторный запуск последнего примера в песочнице выдаст «таблица уже существует»: она живёт до сброса базы. В реальной работе — `DROP TABLE IF EXISTS` перед созданием.)

## Материализуется ли CTE (PostgreSQL)

- До PostgreSQL 12 любой CTE выполнялся отдельно и сохранялся во временный результат — «барьер оптимизации»: фильтр снаружи не проникал внутрь.
- С PostgreSQL 12: CTE, на который ссылаются **один раз** и без побочных эффектов, встраивается в запрос, как подзапрос. Если ссылок несколько — материализуется.
- Управлять вручную:

```pg
WITH heavy AS MATERIALIZED (SELECT ...)      -- посчитать один раз
WITH light AS NOT MATERIALIZED (SELECT ...)  -- встроить, чтобы работали индексы
```

Итог: подзапрос и CTE — вопрос читаемости, по скорости в современных версиях обычно одинаковы.
"""),
('WITH RECURSIVE: как работает рекурсия', r"""
# Рекурсивный CTE

```
WITH RECURSIVE r AS (
    SELECT ...                -- 1. якорь: стартовые строки
    UNION ALL
    SELECT ... FROM r JOIN ...  -- 2. шаг: строится из строк, полученных на ПРЕДЫДУЩЕМ шаге
)
SELECT * FROM r;
```

Алгоритм:
1. Выполнить якорь. Результат — «рабочая таблица» и первая порция итога.
2. Выполнить рекурсивную часть, где `r` — это **только строки предыдущей итерации**.
3. Новые строки добавить в итог и сделать их рабочей таблицей.
4. Повторять, пока шаг не вернёт ноль строк.

```sql
-- числа от 1 до 5
WITH RECURSIVE n(x) AS (
  SELECT 1
  UNION ALL
  SELECT x + 1 FROM n WHERE x < 5      -- условие остановки
)
SELECT x FROM n;
```

## UNION ALL против UNION в рекурсии

| | UNION ALL | UNION |
|---|---|---|
| повторы | сохраняются | отбрасываются, строка, уже бывшая в итоге, не попадёт в рабочую таблицу |
| циклы в данных | бесконечная рекурсия | остановится, если строка точь-в-точь повторилась |
| скорость | быстрее | дороже: проверка дублей |

Обычно пишут UNION ALL и явно защищаются от циклов (ограничение глубины или путь, см. следующую страницу).

## Типичные ошибки

- Нет условия остановки → бесконечный цикл. В тренажёре нажмите «Стоп». В PostgreSQL — `statement_timeout` или Ctrl+C.
- Агрегаты, `LIMIT`, `DISTINCT`, оконные функции в рекурсивной части запрещены (PostgreSQL).
- Ссылаться на r в рекурсивной части можно только один раз.
- В якоре и шаге должны совпадать число и типы столбцов. Если шаг удлиняет строку (путь), в PostgreSQL приводите якорь к text: `CAST(name AS text)`.

## Где применяют

| Задача | Пример |
|---|---|
| обход дерева вниз | все подразделения института |
| путь вверх до корня | цепочка наставников |
| генерация рядов | календарь, ряд чисел (замена generate_series) |
| графы | маршруты, связи «друг друга» |
| разбор строк | разбить `'a,b,c'` на строки |
"""),
('Иерархии: вниз, вверх, путь и глубина', r"""
# Обход иерархий

## Вниз: все потомки узла

```sql
-- всё, что входит в Институт ИТ (dept_id = 1), с уровнем вложенности
WITH RECURSIVE sub AS (
  SELECT dept_id, name, parent_id, 0 AS depth
  FROM departments WHERE dept_id = 1
  UNION ALL
  SELECT d.dept_id, d.name, d.parent_id, s.depth + 1
  FROM departments d JOIN sub s ON d.parent_id = s.dept_id
)
SELECT depth, name FROM sub ORDER BY depth, name;
```

Шаг соединяет **детей** (`d.parent_id`) с уже найденными узлами (`s.dept_id`).

## Вверх: путь до корня

```sql
-- цепочка наставников Фоминой (teacher_id = 8)
WITH RECURSIVE up AS (
  SELECT teacher_id, full_name, mentor_id, 0 AS lvl
  FROM teachers WHERE teacher_id = 8
  UNION ALL
  SELECT t.teacher_id, t.full_name, t.mentor_id, u.lvl + 1
  FROM teachers t JOIN up u ON t.teacher_id = u.mentor_id
)
SELECT lvl, full_name FROM up;
```

Вниз и вверх отличаются только условием соединения: `child.parent = found.id` или `parent.id = found.parent`.

## Путь строкой и сортировка «как в дереве»

```sql
WITH RECURSIVE tree AS (
  SELECT dept_id, name, CAST(name AS TEXT) AS path, 0 AS depth
  FROM departments WHERE parent_id IS NULL
  UNION ALL
  SELECT d.dept_id, d.name, t.path || ' / ' || d.name, t.depth + 1
  FROM departments d JOIN tree t ON d.parent_id = t.dept_id
)
SELECT substr('            ', 1, depth * 4) || name AS tree, path
FROM tree ORDER BY path;
```

## Защита от циклов

Если в данных ошибочно A → B → A, рекурсия не закончится. Способы:

```
-- ограничить глубину
... WHERE s.depth < 20

-- хранить путь и не заходить в уже посещённый узел
... WHERE t.path NOT LIKE '%/' || d.dept_id || '/%'
```

```pg
-- PostgreSQL 14+: встроенное обнаружение циклов
WITH RECURSIVE tree AS (...)
CYCLE dept_id SET is_cycle USING path
SELECT * FROM tree WHERE NOT is_cycle;
```

## Агрегаты по поддереву

Сначала рекурсией получить пары «предок — потомок», потом обычный GROUP BY:

```sql
-- число преподавателей в каждом подразделении вместе с вложенными
WITH RECURSIVE pairs AS (
  SELECT dept_id AS root, dept_id AS node FROM departments
  UNION ALL
  SELECT p.root, d.dept_id FROM departments d JOIN pairs p ON d.parent_id = p.node
)
SELECT r.name, COUNT(t.teacher_id) AS teachers
FROM pairs p
JOIN departments r ON r.dept_id = p.root
LEFT JOIN teachers t ON t.dept_id = p.node
GROUP BY r.dept_id, r.name
ORDER BY r.dept_id;
```
"""),
('Ряды чисел и дат, заполнение пропусков', r"""
# Генерация рядов

В отчётах дни без событий не должны исчезать: «0 посещений в воскресенье» — тоже информация. Но GROUP BY по таблице событий не может создать строку для дня, которого в таблице нет. Нужен **каркас** — ряд всех дней, к которому LEFT JOIN-ом присоединяются факты.

## generate_series против рекурсии

```pg
SELECT d::date AS day
FROM generate_series('2025-11-01'::date, '2025-11-30'::date, interval '1 day') AS d;

SELECT generate_series(1, 10) AS n;
```

```sql
-- то же самое рекурсией (работает и в PostgreSQL)
WITH RECURSIVE days(day) AS (
  SELECT '2025-11-03'
  UNION ALL
  SELECT date(day, '+1 day') FROM days WHERE day < '2025-11-17'
)
SELECT d.day, COALESCE(v.visits, 0) AS visits
FROM days d
LEFT JOIN library_visits v ON v.day = d.day
ORDER BY d.day;
```

Воскресенья 9 и 16 ноября появились с нулём.

## Каркас из двух измерений

Все дни × все группы — CROSS JOIN двух рядов, потом LEFT JOIN фактов:

```sql
WITH RECURSIVE months(m) AS (
  SELECT '2025-09'
  UNION ALL
  SELECT strftime('%Y-%m', date(m || '-01', '+1 month')) FROM months WHERE m < '2025-12'
),
payers AS (SELECT DISTINCT student_id FROM dorm_payments)
SELECT p.student_id, mo.m AS month, COALESCE(SUM(dp.amount), 0) AS paid
FROM payers p
CROSS JOIN months mo
LEFT JOIN dorm_payments dp
  ON dp.student_id = p.student_id AND strftime('%Y-%m', dp.paid_on) = mo.m
GROUP BY p.student_id, mo.m
ORDER BY p.student_id, mo.m;
```

Видно, кто и в каком месяце не заплатил — по исходной таблице этого не увидеть.

## Разбить строку на части

```sql
WITH RECURSIVE parts(rest, item) AS (
  SELECT 'sql,python,ml,' , NULL
  UNION ALL
  SELECT substr(rest, instr(rest, ',') + 1), substr(rest, 1, instr(rest, ',') - 1)
  FROM parts WHERE rest <> ''
)
SELECT item FROM parts WHERE item IS NOT NULL;
```

В PostgreSQL для этого есть `string_to_table(s, ',')` и `unnest(string_to_array(s, ','))`.
"""),
('Модифицирующие CTE и шпаргалка', r"""
# CTE с INSERT, UPDATE, DELETE (PostgreSQL)

В PostgreSQL CTE может менять данные и передавать изменённые строки дальше через RETURNING. Всё выполняется одним оператором, атомарно.

```pg
-- перенести выпускников в архив одним запросом
WITH moved AS (
    DELETE FROM students
    WHERE group_id IN (SELECT group_id FROM study_groups WHERE year <= 2021)
    RETURNING *
)
INSERT INTO students_archive
SELECT * FROM moved;
```

```pg
-- обновить и сразу посчитать, сколько и на сколько
WITH upd AS (
    UPDATE teachers SET salary = salary * 1.1
    WHERE dept_id = 3
    RETURNING teacher_id, salary
)
SELECT COUNT(*), SUM(salary) FROM upd;
```

Тонкость: все части такого запроса видят **один и тот же снимок** данных. Основной запрос не увидит изменений, сделанных в CTE, через саму таблицу — только через RETURNING.

В SQLite CTE может стоять перед INSERT/UPDATE/DELETE, но сам содержать только SELECT.

# Шпаргалка CTE

| Похожие | Разница |
|---|---|
| CTE и подзапрос в FROM | одинаковы по смыслу; CTE читаемее и можно сослаться несколько раз |
| CTE и VIEW | CTE живёт один запрос, VIEW сохраняется в базе |
| CTE и временная таблица | временная таблица хранит данные в сессии, на неё можно повесить индекс |
| `MATERIALIZED` и `NOT MATERIALIZED` | посчитать один раз или встроить в запрос (PG 12+) |
| `WITH` и `WITH RECURSIVE` | второе разрешает CTE ссылаться на себя |
| `UNION ALL` и `UNION` в рекурсии | второе отбрасывает повторы и спасает от простых циклов, но дороже |
| рекурсия вниз и вверх | `child.parent_id = found.id` или `parent.id = found.parent_id` |
| `generate_series` и рекурсивный ряд | первое короче, только PG |
| self-join на N уровней и рекурсия | фиксированная и произвольная глубина |
"""),
]

M07 = [
('Окна против GROUP BY', r"""
# Оконные функции

GROUP BY схлопывает строки: из 25 записей об экзаменах получается 7 строк по курсам. Оконная функция считает то же самое, **но оставляет все строки** и приписывает результат каждой.

```sql
-- GROUP BY: строка на курс
SELECT course_id, AVG(grade) AS avg_grade
FROM enrollments
GROUP BY course_id;
```

```sql
-- окно: строка на каждый экзамен + средняя по его курсу рядом
SELECT student_id, course_id, grade,
       AVG(grade) OVER (PARTITION BY course_id) AS course_avg,
       grade - AVG(grade) OVER (PARTITION BY course_id) AS diff
FROM enrollments
WHERE grade IS NOT NULL
ORDER BY course_id, grade DESC;
```

| | GROUP BY | Окно `OVER (...)` |
|---|---|---|
| строк на выходе | одна на группу | столько же, сколько на входе |
| можно ли вывести детальные столбцы | только ключи и агрегаты | любые |
| порядок внутри группы | не важен | важен для накопительных, рангов, LAG |
| когда считается | шаг 3 | шаг 5: после WHERE, GROUP BY, HAVING |
| можно ли фильтровать результат в WHERE | HAVING | нельзя, только во внешнем запросе |
| что умеет | агрегаты | агрегаты + ранги + смещения + накопления |

## Без окна было бы так

Средняя по курсу рядом с каждой строкой без окна — это JOIN с агрегатом или коррелированный подзапрос (модуль 5). Окно делает то же самое за один проход и читается проще.

## Окна поверх GROUP BY

Окна считаются после группировки, поэтому могут работать с агрегатами:

```sql
-- доля каждого города в общем числе студентов
SELECT city, COUNT(*) AS n,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct
FROM students
GROUP BY city
ORDER BY n DESC;
```

`SUM(COUNT(*)) OVER ()` — внутренний `COUNT(*)` из GROUP BY, внешний `SUM ... OVER ()` по всем группам. `OVER ()` с пустыми скобками — окно на весь результат.
"""),
('Синтаксис OVER: PARTITION, ORDER, рамка', r"""
# Из чего состоит окно

```
функция(...) OVER (
    PARTITION BY ...      -- на какие независимые части делить (как GROUP BY, но без схлопывания)
    ORDER BY ...          -- порядок строк внутри части
    ROWS | RANGE | GROUPS BETWEEN ... AND ...   -- рамка: какие строки видит функция
)
```

| Часть | Если не указать |
|---|---|
| PARTITION BY | весь результат — одна часть |
| ORDER BY | порядок не определён; агрегат считается по всей части |
| рамка | при наличии ORDER BY: `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW` — от начала до текущей строки **и всех равных ей**; без ORDER BY — вся часть |

## Как ORDER BY меняет смысл агрегата

```sql
SELECT student_id, paid_on, amount,
       SUM(amount) OVER (PARTITION BY student_id)                    AS total,
       SUM(amount) OVER (PARTITION BY student_id ORDER BY paid_on)   AS running_total
FROM dorm_payments
ORDER BY student_id, paid_on;
```

Без ORDER BY — сумма по всей части (одинакова во всех строках студента). С ORDER BY — накопительный итог. Это одна и та же функция SUM, разница только в рамке по умолчанию.

## WINDOW: именованные окна

Если одно окно используется несколько раз, его можно назвать:

```sql
SELECT student_id, paid_on, amount,
       SUM(amount)  OVER w AS running_total,
       COUNT(*)     OVER w AS payment_no,
       AVG(amount)  OVER w AS running_avg
FROM dorm_payments
WINDOW w AS (PARTITION BY student_id ORDER BY paid_on)
ORDER BY student_id, paid_on;
```

## Где можно писать оконные функции

- В SELECT и ORDER BY — да.
- В WHERE, GROUP BY, HAVING — **нет**: окна считаются позже. Фильтр по окну — во внешнем запросе или CTE:

```sql
WITH ranked AS (
  SELECT full_name, dept_id, salary,
         ROW_NUMBER() OVER (PARTITION BY dept_id ORDER BY salary DESC) AS rn
  FROM teachers
)
SELECT * FROM ranked WHERE rn = 1;
```

В некоторых СУБД (Snowflake, BigQuery, DuckDB) есть `QUALIFY rn = 1` — фильтр по окну без подзапроса. В PostgreSQL и SQLite его нет.
"""),
('ROW_NUMBER, RANK, DENSE_RANK, NTILE', r"""
# Ранжирующие функции

Все требуют `ORDER BY` внутри OVER. Разница — в том, как они обходятся с **ничьими**.

```sql
SELECT student_id, course_id, grade,
       ROW_NUMBER()  OVER (ORDER BY grade DESC) AS row_number,
       RANK()        OVER (ORDER BY grade DESC) AS rank,
       DENSE_RANK()  OVER (ORDER BY grade DESC) AS dense_rank,
       NTILE(4)      OVER (ORDER BY grade DESC) AS quartile,
       ROUND(PERCENT_RANK() OVER (ORDER BY grade DESC), 2) AS pct_rank,
       ROUND(CUME_DIST()    OVER (ORDER BY grade DESC), 2) AS cume_dist
FROM enrollments
WHERE grade IS NOT NULL;
```

| Функция | Оценки 5, 5, 5, 4, 4, 3 | Ничьи | Пропуски номеров |
|---|---|---|---|
| `ROW_NUMBER()` | 1, 2, 3, 4, 5, 6 | разные номера, порядок среди равных **случайный** | нет |
| `RANK()` | 1, 1, 1, 4, 4, 6 | одинаковый номер | да: после трёх первых сразу 4 |
| `DENSE_RANK()` | 1, 1, 1, 2, 2, 3 | одинаковый номер | нет |
| `NTILE(n)` | делит на n почти равных корзин | равные могут попасть в разные корзины | — |
| `PERCENT_RANK()` | (rank − 1) / (строк − 1), от 0 до 1 | одинаковый | — |
| `CUME_DIST()` | доля строк ≤ текущей | одинаковый | — |

## Что выбрать

| Задача | Функция |
|---|---|
| ровно одна строка на группу (дедупликация, «последняя запись») | ROW_NUMBER + уникальный ключ в ORDER BY для детерминизма |
| «топ-3 места» как в спорте, ничьи делят место | RANK |
| «три лучших **значения** оценки», сколько бы строк их ни имели | DENSE_RANK |
| N-я по величине зарплата | DENSE_RANK = N |
| разбить на квартили/децили | NTILE или PERCENT_RANK |
| «лучше скольких процентов» | PERCENT_RANK / CUME_DIST |

## Топ-N внутри группы

```sql
-- два лучших результата на каждом курсе (ничьи — по student_id)
SELECT * FROM (
  SELECT course_id, student_id, grade,
         ROW_NUMBER() OVER (PARTITION BY course_id ORDER BY grade DESC, student_id) AS rn
  FROM enrollments WHERE grade IS NOT NULL
) t
WHERE rn <= 2
ORDER BY course_id, rn;
```

Замените ROW_NUMBER на RANK — и при ничьей на втором месте строк станет больше двух. Какое поведение нужно, решает формулировка задачи: «два студента» или «все, кто на двух первых местах».

## NTILE против PERCENT_RANK для сегментов

`NTILE(4)` гарантирует почти одинаковый размер корзин, даже если значения равны (одинаковые оценки попадут в разные квартили). Разбиение по `PERCENT_RANK` или `CUME_DIST` держит равные значения вместе, но корзины могут быть разного размера.
"""),
('LAG, LEAD, FIRST_VALUE, LAST_VALUE', r"""
# Функции смещения

| Функция | Что возвращает |
|---|---|
| `LAG(x, n, default)` | x из строки на n позиций **раньше** (по умолчанию n = 1) |
| `LEAD(x, n, default)` | x из строки на n позиций **позже** |
| `FIRST_VALUE(x)` | x из первой строки рамки |
| `LAST_VALUE(x)` | x из последней строки рамки — **осторожно с рамкой** |
| `NTH_VALUE(x, n)` | x из n-й строки рамки |

```sql
SELECT student_id, paid_on, amount,
       LAG(paid_on)  OVER w AS prev_payment,
       LEAD(paid_on) OVER w AS next_payment,
       julianday(paid_on) - julianday(LAG(paid_on) OVER w) AS days_since_prev,
       amount - LAG(amount, 1, 0) OVER w AS change
FROM dorm_payments
WINDOW w AS (PARTITION BY student_id ORDER BY paid_on)
ORDER BY student_id, paid_on;
```

- Для первой строки части `LAG` возвращает NULL (или default, если указан). Для последней `LEAD` — NULL.
- `PARTITION BY` обязателен, если не хотите, чтобы LAG «перепрыгивал» на соседнего студента.

## Ловушка LAST_VALUE

```sql
SELECT day, visits,
       FIRST_VALUE(visits) OVER (ORDER BY day) AS first_v,
       LAST_VALUE(visits)  OVER (ORDER BY day) AS last_v_wrong,
       LAST_VALUE(visits)  OVER (ORDER BY day
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS last_v
FROM library_visits;
```

С `ORDER BY` рамка по умолчанию заканчивается на **текущей строке**, поэтому `LAST_VALUE` возвращает саму текущую строку. Нужна явная рамка до `UNBOUNDED FOLLOWING`. Альтернатива без возни с рамкой: `FIRST_VALUE(x) OVER (ORDER BY day DESC)`.

## LAG против self-join

«Предыдущая строка» без окон — это self-join с поиском максимальной даты меньше текущей. Это громоздко и требует подзапроса на каждую строку:

```sql
SELECT a.student_id, a.paid_on,
       (SELECT MAX(b.paid_on) FROM dorm_payments b
        WHERE b.student_id = a.student_id AND b.paid_on < a.paid_on) AS prev_payment
FROM dorm_payments a
ORDER BY a.student_id, a.paid_on;
```

Результат такой же, как у `LAG(paid_on)`, но LAG делает один проход и понятнее.

## LAG по строкам, а не по времени

LAG берёт предыдущую **строку**, а не «предыдущий месяц». Если месяц пропущен, LAG вернёт позапрошлый. Для сравнения «с прошлым месяцем» при пропусках сначала постройте каркас месяцев (модуль 6) или соединяйтесь по дате.
"""),
('Рамки: ROWS, RANGE, GROUPS', r"""
# Рамка окна

Рамка задаёт, какие строки части видит агрегатная функция для текущей строки.

```
{ROWS | RANGE | GROUPS} BETWEEN начало AND конец
начало/конец: UNBOUNDED PRECEDING | n PRECEDING | CURRENT ROW | n FOLLOWING | UNBOUNDED FOLLOWING
```

| Режим | Единица отсчёта | «2 PRECEDING» значит | Равные значения ORDER BY |
|---|---|---|---|
| `ROWS` | физические строки | две предыдущие строки | разделяются |
| `RANGE` | значение ключа ORDER BY | все строки, где ключ ≥ текущий − 2 | входят в рамку вместе |
| `GROUPS` | группы равных значений | две предыдущие группы ничьих | входят вместе |

## Разница на данных с ничьими

11 и 12 ноября в библиотеке было по 150 посещений. Отсортируем по числу посещений:

```sql
SELECT day, visits,
       SUM(visits) OVER (ORDER BY visits ROWS  BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS rows_sum,
       SUM(visits) OVER (ORDER BY visits RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS range_sum,
       SUM(visits) OVER (ORDER BY visits) AS default_sum
FROM library_visits
ORDER BY visits;
```

На двух строках с 150 `rows_sum` разный (строки идут по одной), а `range_sum` одинаковый: обе строки равны и попадают в рамку вместе. `default_sum` совпадает с RANGE — это рамка по умолчанию. Поэтому накопительный итог по неуникальному ключу «прыгает» — указывайте `ROWS` или добавляйте уникальный ключ в ORDER BY.

## Разница на данных с пропусками

Скользящая сумма за 7 дней. В данных нет воскресений:

```sql
SELECT day, visits,
       SUM(visits) OVER (ORDER BY day ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS last_7_rows,
       SUM(visits) OVER (ORDER BY julianday(day) RANGE BETWEEN 6 PRECEDING AND CURRENT ROW) AS last_7_days
FROM library_visits
ORDER BY day;
```

- `ROWS 6 PRECEDING` — 7 последних **строк**. Из-за пропущенных дней это может быть 8 календарных дней.
- `RANGE 6 PRECEDING` по номеру дня — ровно 7 **календарных** дней, сколько бы строк в них ни было.

В PostgreSQL RANGE работает прямо с датами: `ORDER BY day RANGE BETWEEN INTERVAL '6 days' PRECEDING AND CURRENT ROW`.

## Частые рамки

| Задача | Рамка |
|---|---|
| накопительный итог | `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW` |
| скользящее среднее по 3 строкам | `ROWS BETWEEN 2 PRECEDING AND CURRENT ROW` |
| центрированное среднее | `ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING` |
| сумма за 30 календарных дней | `RANGE BETWEEN 29 PRECEDING AND CURRENT ROW` (по числу или интервалу) |
| итог по всей части | без ORDER BY или `ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING` |

Рамка влияет только на агрегатные функции и FIRST/LAST/NTH_VALUE. На ROW_NUMBER, RANK, LAG, LEAD рамка не действует.
"""),
('Топ-N на группу: три способа и шпаргалка', r"""
# Топ-N на группу: сравнение подходов

Задача «самый высокооплачиваемый на каждой кафедре» решается разными способами, и на собеседованиях часто просят сравнить.

```sql
-- 1. окно
SELECT dept_id, full_name, salary FROM (
  SELECT dept_id, full_name, salary,
         RANK() OVER (PARTITION BY dept_id ORDER BY salary DESC) AS r
  FROM teachers WHERE dept_id IS NOT NULL
) t WHERE r = 1;
```

```sql
-- 2. JOIN с агрегатом
SELECT t.dept_id, t.full_name, t.salary
FROM teachers t
JOIN (SELECT dept_id, MAX(salary) AS mx FROM teachers GROUP BY dept_id) m
  ON m.dept_id = t.dept_id AND m.mx = t.salary;
```

```sql
-- 3. коррелированный NOT EXISTS: «нет никого с большей зарплатой на той же кафедре»
SELECT t.dept_id, t.full_name, t.salary
FROM teachers t
WHERE t.dept_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM teachers t2 WHERE t2.dept_id = t.dept_id AND t2.salary > t.salary);
```

| Способ | Топ-1 | Топ-N | Ничьи | Переносимость |
|---|---|---|---|---|
| окно ROW_NUMBER/RANK | да | да | на выбор | все современные СУБД |
| JOIN с MAX | да | нет | все равные | везде |
| NOT EXISTS | да | сложно (COUNT меньших < N) | все равные | везде |
| DISTINCT ON | да | нет | одна строка | только PG |
| LATERAL + LIMIT | да | да | одна строка на позицию | PG, не SQLite |

# Шпаргалка окон

| Похожие | Разница |
|---|---|
| `GROUP BY` и `OVER (PARTITION BY)` | схлопывает строки и сохраняет их |
| `OVER ()` и `OVER (ORDER BY …)` с SUM | итог по всем и накопительный итог |
| `ROW_NUMBER`, `RANK`, `DENSE_RANK` | 1,2,3,4 / 1,1,3,4 / 1,1,2,3 |
| `NTILE` и `PERCENT_RANK` | равные корзины и относительный ранг |
| `LAG` и `LEAD` | предыдущая и следующая строка |
| `FIRST_VALUE` и `LAST_VALUE` | LAST_VALUE требует явной рамки |
| `ROWS` и `RANGE` | физические строки и значения ключа (ничьи, пропуски) |
| `RANGE` и `GROUPS` | расстояние по значению и по числу групп ничьих |
| окно в `WHERE` и в подзапросе | в WHERE нельзя — фильтруйте снаружи |
| `WINDOW w AS (...)` | имя для повторяющегося окна |
| `LAG` и self-join | одинаковый результат, LAG проще и быстрее |
"""),
]

M08 = [
('INSERT', r"""
# INSERT

```
INSERT INTO таблица (столбцы) VALUES (...), (...);   -- одна или несколько строк
INSERT INTO таблица (столбцы) SELECT ...;            -- из запроса
INSERT INTO таблица DEFAULT VALUES;                   -- все значения по умолчанию
... RETURNING столбцы;                                -- вернуть вставленное
```

Примеры на этой странице обёрнуты в `BEGIN … ROLLBACK`: вы видите результат, а база остаётся прежней, и пример можно запускать сколько угодно раз.

```sql
BEGIN;
INSERT INTO students (full_name, group_id, city, birth_date, email)
VALUES ('Петров Лев', 2, 'Москва', '2005-02-02', 'lev@uni.ru'),
       ('Сидорова Яна', NULL, 'Тула', '2005-05-05', NULL)
RETURNING student_id, full_name;
ROLLBACK;
```

## Правила

- **Всегда перечисляйте столбцы.** `INSERT INTO t VALUES (...)` без списка ломается, как только в таблицу добавят столбец, и молча путает значения, если порядок другой.
- Пропущенный столбец получает DEFAULT, а если его нет — NULL (или ошибку при NOT NULL).
- `student_id` не указан: первичный ключ сгенерируется сам (IDENTITY / SERIAL в PG, INTEGER PRIMARY KEY в SQLite).
- Несколько строк одним INSERT быстрее, чем по одной: одна транзакция, один разбор.

## INSERT … SELECT

Копирование и преобразование данных одной командой:

```sql
BEGIN;
CREATE TEMP TABLE honor_board (student_id INTEGER, avg_grade REAL);
INSERT INTO honor_board (student_id, avg_grade)
SELECT student_id, AVG(grade) FROM enrollments
GROUP BY student_id HAVING AVG(grade) >= 4.5;
SELECT * FROM honor_board;
ROLLBACK;
```

## RETURNING

Возвращает значения вставленных строк — прежде всего сгенерированные ключи, чтобы приложению не делать второй запрос. Работает в PostgreSQL и SQLite 3.35+, есть и у UPDATE, и у DELETE.

## Массовая загрузка

Для миллионов строк в PostgreSQL используют `COPY таблица FROM 'файл.csv' WITH (FORMAT csv, HEADER)` (на сервере) или `\copy` в psql (с клиента). Это на порядок быстрее INSERT.
"""),
('UPDATE и DELETE', r"""
# UPDATE

```
UPDATE таблица SET столбец = выражение, ... [FROM ...] WHERE условие [RETURNING ...];
```

```sql
BEGIN;
UPDATE teachers
SET salary = salary * 1.10
WHERE dept_id = 3
RETURNING full_name, salary;
ROLLBACK;
```

- Без WHERE обновятся **все** строки. Перед опасным UPDATE выполните тот же WHERE в SELECT и посчитайте строки.
- В правой части SET используются **старые** значения: `SET a = b, b = a` меняет местами, а не копирует.

## UPDATE с данными из другой таблицы

| Способ | Пример | Замечание |
|---|---|---|
| подзапрос в SET | `SET x = (SELECT ... WHERE связь)` | если подзапрос ничего не нашёл — запишет **NULL** |
| `UPDATE … FROM` | `UPDATE t SET x = s.x FROM s WHERE s.id = t.id` | PostgreSQL, SQLite 3.33+; строки без пары не трогает |
| MERGE | см. страницу про UPSERT | PostgreSQL 15+ |

```sql
BEGIN;
-- стипендия 7000 всем, у кого средний балл 5
UPDATE students
SET scholarship = 7000
FROM (SELECT student_id FROM enrollments GROUP BY student_id HAVING MIN(grade) = 5) best
WHERE best.student_id = students.student_id
RETURNING full_name, scholarship;
ROLLBACK;
```

```bad
-- подзапрос в SET без WHERE: у тех, для кого подзапрос пуст, значение станет NULL
UPDATE students SET scholarship = (SELECT 7000 FROM ... WHERE ...);
```

Если в FROM у одной целевой строки несколько пар, результат не определён (возьмётся любая). Агрегируйте источник до одной строки на ключ.

# DELETE

```sql
BEGIN;
DELETE FROM enrollments WHERE grade IS NULL RETURNING *;
ROLLBACK;
```

Удаление с условием по другой таблице — через подзапрос (работает везде) или `DELETE … USING` (PostgreSQL):

```pg
DELETE FROM enrollments e
USING students s
WHERE s.student_id = e.student_id AND s.group_id IS NULL;
```
"""),
('DELETE, TRUNCATE, DROP и каскады', r"""
# DELETE против TRUNCATE против DROP

| | `DELETE FROM t [WHERE]` | `TRUNCATE t` | `DROP TABLE t` |
|---|---|---|---|
| что удаляет | выбранные строки | все строки | таблицу целиком: данные, структуру, индексы, права |
| WHERE | можно | нет | нет |
| скорость на больших таблицах | медленно: по строке, пишет журнал на каждую | мгновенно: освобождает файлы | мгновенно |
| триггеры ON DELETE | срабатывают | нет (есть ON TRUNCATE) | нет |
| RETURNING | да | нет | нет |
| откат в транзакции (PG) | да | да (в PostgreSQL TRUNCATE транзакционен) | да |
| счётчик IDENTITY | не сбрасывается | `RESTART IDENTITY` сбрасывает | исчезает с таблицей |
| внешние ключи | проверяются для каждой строки, работают каскады | запрещён, если на таблицу ссылаются, без `CASCADE` | запрещён без `CASCADE` |
| место на диске (PG) | освободится после VACUUM | сразу | сразу |

В SQLite нет TRUNCATE: `DELETE FROM t` без WHERE оптимизирован и работает быстро.

## Что происходит со ссылающимися строками

Внешний ключ определяет, что делать, если удаляют родителя:

| Правило | При удалении студента его записи в enrollments… |
|---|---|
| `NO ACTION` / `RESTRICT` (по умолчанию) | удаление запрещено, пока записи есть |
| `CASCADE` | удаляются вместе со студентом |
| `SET NULL` | student_id становится NULL |
| `SET DEFAULT` | становится значением по умолчанию |

В uni у enrollments стоит `ON DELETE CASCADE`, у остальных связей — по умолчанию:

```sql
BEGIN;
SELECT COUNT(*) AS "записей до" FROM enrollments WHERE student_id = 2;
DELETE FROM students WHERE student_id = 2;          -- CASCADE удалит и её оценки
SELECT COUNT(*) AS "записей после" FROM enrollments WHERE student_id = 2;
ROLLBACK;
```

```sql-error
BEGIN;
DELETE FROM teachers WHERE teacher_id = 2;           -- на неё ссылаются курсы → ошибка
ROLLBACK;
```

Второй пример заканчивается ошибкой внешнего ключа — так и задумано, незавершённую транзакцию тренажёр откатит сам. А вот студента 1 так удалить не выйдет: на него ссылаются оплаты общежития, а там каскада нет. Попробуйте.

`RESTRICT` и `NO ACTION` почти одинаковы; разница в том, что NO ACTION проверяется в конце оператора и может быть отложен до конца транзакции (`DEFERRABLE`).

## Мягкое удаление

Вместо DELETE ставят метку: `UPDATE ... SET deleted_at = now()`. История сохраняется, удаление обратимо, но **каждый** запрос должен помнить про `WHERE deleted_at IS NULL` — обычно это прячут во VIEW.
"""),
('UPSERT: ON CONFLICT, MERGE, REPLACE', r"""
# Вставить или обновить

Задача: если записи с таким ключом нет — вставить, если есть — обновить (или ничего не делать). Наивное «SELECT, потом INSERT или UPDATE» ломается при параллельной работе: два сеанса одновременно не найдут строку и оба попытаются вставить.

## INSERT … ON CONFLICT (PostgreSQL 9.5+, SQLite 3.24+)

```sql
BEGIN;
-- студент 1 пересдал Базы данных, студент 5 впервые сдал Базы данных
INSERT INTO enrollments (student_id, course_id, grade, exam_date)
VALUES (1, 1, 4, '2025-07-01'), (5, 1, 5, '2025-07-01')
ON CONFLICT (student_id, course_id)
DO UPDATE SET grade = excluded.grade, exam_date = excluded.exam_date;
SELECT * FROM enrollments WHERE course_id = 1 AND student_id IN (1, 5);
ROLLBACK;
```

- `ON CONFLICT (столбцы)` — какой уникальный индекс проверять. Должен существовать PRIMARY KEY или UNIQUE ровно на эти столбцы.
- `excluded` — строка, которую пытались вставить.
- `DO UPDATE ... WHERE условие` — обновлять только при условии (например, если новая оценка выше).
- `DO NOTHING` — пропустить конфликтные строки.

| Вариант | Поведение | Когда |
|---|---|---|
| `ON CONFLICT DO NOTHING` | конфликтные строки молча пропускаются | идемпотентная загрузка, «вставь, если нет» |
| `ON CONFLICT DO UPDATE` | конфликтная строка обновляется | синхронизация, счётчики, последнее значение |
| `MERGE` (PG 15+) | вставка, обновление и удаление по произвольному условию | сложная синхронизация таблицы с источником |
| `INSERT OR REPLACE` / `REPLACE` (SQLite, MySQL) | **удаляет** старую строку и вставляет новую | осторожно: срабатывают DELETE-каскады, теряются невставленные столбцы |
| `INSERT OR IGNORE` (SQLite) | аналог DO NOTHING, но глушит и другие ошибки ограничений | |

## MERGE (PostgreSQL 15+)

```pg
MERGE INTO enrollments AS e
USING new_results AS n
  ON e.student_id = n.student_id AND e.course_id = n.course_id
WHEN MATCHED AND n.grade IS NULL THEN DELETE
WHEN MATCHED THEN UPDATE SET grade = n.grade, exam_date = n.exam_date
WHEN NOT MATCHED THEN INSERT (student_id, course_id, grade, exam_date)
                     VALUES (n.student_id, n.course_id, n.grade, n.exam_date);
```

MERGE не требует уникального индекса и умеет удалять, но в отличие от ON CONFLICT не защищён от гонки при параллельных вставках: два сеанса могут оба попасть в NOT MATCHED. Для «вставь или обнови по ключу» под нагрузкой надёжнее ON CONFLICT.
"""),
('Транзакции и ACID', r"""
# Транзакции

Транзакция — группа операций, которая выполняется **целиком или никак**.

```
BEGIN;             -- или START TRANSACTION
  ... операции ...
COMMIT;            -- зафиксировать
-- или
ROLLBACK;          -- отменить всё с начала транзакции
```

Без BEGIN каждый оператор — отдельная транзакция (autocommit).

## ACID

| Буква | Свойство | Что значит на практике |
|---|---|---|
| A | атомарность | перевод денег не может списать без зачисления |
| C | согласованность | после транзакции соблюдены все ограничения (FK, CHECK, UNIQUE) |
| I | изоляция | параллельные транзакции не видят «половину» чужой работы (насколько — зависит от уровня) |
| D | долговечность | после COMMIT данные переживут падение сервера (журнал WAL) |

```sql
BEGIN;
-- перевод студента 12 в группу 4 и запись на курс — либо оба действия, либо ни одного
UPDATE students SET group_id = 4 WHERE student_id = 12;
INSERT INTO enrollments (student_id, course_id) VALUES (12, 5);
SELECT s.full_name, s.group_id, e.course_id
FROM students s LEFT JOIN enrollments e ON e.student_id = s.student_id
WHERE s.student_id = 12;
ROLLBACK;
```

## Ошибка внутри транзакции

- **PostgreSQL**: после любой ошибки транзакция переходит в состояние «aborted», все следующие команды отвергаются до ROLLBACK. Зафиксировать «то, что успело пройти», нельзя.
- **SQLite**: ошибочный оператор откатывается, транзакция продолжается.

## SAVEPOINT: частичный откат

```sql
BEGIN;
UPDATE teachers SET salary = salary + 5000 WHERE teacher_id = 3;
SAVEPOINT before_risky;
UPDATE teachers SET salary = 1;                 -- ошиблись: забыли WHERE
ROLLBACK TO SAVEPOINT before_risky;             -- откатили только то, что после точки
SELECT teacher_id, salary FROM teachers WHERE teacher_id IN (3, 4);
ROLLBACK;
```

Зарплата преподавателя 3 выросла на 5000, а ошибочное обнуление всех зарплат откатилось.

В PostgreSQL SAVEPOINT — единственный способ продолжить транзакцию после ошибки: `ROLLBACK TO SAVEPOINT` снимает состояние aborted.

## Короткие транзакции

Транзакция держит блокировки и мешает очистке старых версий строк (VACUUM). Не открывайте транзакцию и не ждите в ней ответа пользователя или внешнего API.
"""),
('Изоляция, аномалии и блокировки', r"""
# Уровни изоляции (PostgreSQL)

Когда транзакции идут параллельно, возможны **аномалии**:

| Аномалия | Что происходит |
|---|---|
| грязное чтение | видим незафиксированные изменения чужой транзакции |
| неповторяемое чтение | читаем строку дважды — значения разные, кто-то успел UPDATE + COMMIT |
| фантомы | повторяем запрос с WHERE — появились новые строки |
| потерянное обновление | две транзакции прочитали 10, обе записали 10 + 1 = 11 вместо 12 |
| аномалия сериализации (write skew) | каждая транзакция по отдельности корректна, вместе — нарушают правило («хотя бы один дежурный» и оба ушли) |

| Уровень | Грязное | Неповторяемое | Фантомы | Сериализация | В PostgreSQL |
|---|---|---|---|---|---|
| READ UNCOMMITTED | по стандарту возможно | да | да | да | ведёт себя как READ COMMITTED |
| READ COMMITTED | нет | да | да | да | **по умолчанию**: каждый оператор видит свежий снимок |
| REPEATABLE READ | нет | нет | нет (в PG) | да | вся транзакция видит один снимок; при конфликте записи — ошибка |
| SERIALIZABLE | нет | нет | нет | нет | при опасной комбинации одна транзакция получит ошибку и должна повториться |

```pg
BEGIN ISOLATION LEVEL REPEATABLE READ;
...
COMMIT;
```

## MVCC

PostgreSQL не перезаписывает строку при UPDATE, а создаёт **новую версию**. Каждая транзакция видит версии, актуальные на момент её снимка. Отсюда:
- читатели не блокируют писателей и наоборот;
- старые версии остаются в таблице, их убирает VACUUM (autovacuum);
- длинные транзакции мешают уборке, таблицы «распухают».

## Потерянное обновление и как его избежать

```pg
-- плохо: прочитали, посчитали в приложении, записали
SELECT seats FROM courses_limit WHERE course_id = 1;      -- 10
UPDATE courses_limit SET seats = 9 WHERE course_id = 1;

-- 1. атомарное выражение
UPDATE courses_limit SET seats = seats - 1 WHERE course_id = 1 AND seats > 0;

-- 2. явная блокировка строки до конца транзакции
BEGIN;
SELECT seats FROM courses_limit WHERE course_id = 1 FOR UPDATE;
UPDATE courses_limit SET seats = seats - 1 WHERE course_id = 1;
COMMIT;

-- 3. оптимистическая блокировка: столбец version
UPDATE courses_limit SET seats = 9, version = version + 1
WHERE course_id = 1 AND version = 7;   -- 0 строк → кто-то успел раньше, повторить
```

| Блокировка | Смысл |
|---|---|
| `FOR UPDATE` | никто другой не изменит и не заблокирует эти строки до конца транзакции |
| `FOR SHARE` | другие могут читать с FOR SHARE, но не менять |
| `FOR UPDATE SKIP LOCKED` | пропустить занятые строки — очередь задач из таблицы |
| `FOR UPDATE NOWAIT` | не ждать, сразу ошибка |

## Взаимная блокировка (deadlock)

Транзакция 1 заблокировала строку A и ждёт B, транзакция 2 — наоборот. PostgreSQL обнаружит цикл и прервёт одну из них. Профилактика: блокировать строки в одном и том же порядке (например, по возрастанию id) и держать транзакции короткими.

## А в SQLite

SQLite разрешает одновременно одну пишущую транзакцию на всю базу, поэтому все транзакции фактически сериализуемы. Аномалии из таблицы выше в тренажёре воспроизвести нельзя — проверьте их в PostgreSQL в двух окнах psql.
"""),
]

M09 = [
('CREATE TABLE и типы данных', r"""
# CREATE TABLE

```pg
CREATE TABLE course_reviews (
    review_id   bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    course_id   integer NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
    student_id  integer REFERENCES students(student_id) ON DELETE SET NULL,
    rating      smallint NOT NULL CHECK (rating BETWEEN 1 AND 5),
    body        text,
    is_public   boolean NOT NULL DEFAULT true,
    created_at  timestamptz NOT NULL DEFAULT now(),
    UNIQUE (course_id, student_id)
);
```

## Типы PostgreSQL: что брать

| Данные | Тип | Не путать с |
|---|---|---|
| целые id, количества | `integer`, `bigint` для больших таблиц | `numeric` — медленнее, не нужен для целых |
| деньги | `numeric(12, 2)` | `real`/`double` — ошибки округления; `money` — завязан на локаль |
| текст | `text` | `varchar(n)` — то же самое, только с ограничением длины; `char(n)` — дополняет пробелами, почти не нужен |
| дата | `date` | |
| момент времени | `timestamptz` (с часовым поясом) | `timestamp` без зоны — «настенные часы», неоднозначен при переходе между поясами |
| длительность | `interval` | |
| да/нет | `boolean` | `int` 0/1 |
| JSON | `jsonb` | `json` — хранит текст как есть, медленнее в запросах |
| уникальный идентификатор | `uuid` | `text` с uuid — больше места |
| списки | `integer[]`, `text[]` | обычно лучше отдельная таблица |
| перечисление | `CHECK (status IN (...))` или `enum` | enum трудно менять |

`varchar(255)` в PostgreSQL не быстрее `text`. Длину ограничивают, только если это бизнес-правило.

## В SQLite

SQLite использует «динамическую типизацию»: тип столбца — лишь рекомендация, в столбец INTEGER можно положить текст. Тренажёр создаёт таблицы с привычными типами, но помните, что проверка типов в PostgreSQL строже.

```sql
BEGIN;
CREATE TABLE course_reviews (
    review_id  INTEGER PRIMARY KEY,
    course_id  INTEGER NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
    student_id INTEGER REFERENCES students(student_id) ON DELETE SET NULL,
    rating     INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    body       TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (course_id, student_id)
);
INSERT INTO course_reviews (course_id, student_id, rating, body) VALUES (1, 2, 5, 'Отлично');
SELECT * FROM course_reviews;
ROLLBACK;
```

## Полезные варианты

- `CREATE TABLE IF NOT EXISTS` — не падать, если таблица уже есть.
- `CREATE TABLE t AS SELECT ...` — таблица из запроса (без ограничений и индексов!).
- `CREATE TABLE t (LIKE other INCLUDING ALL)` — копия структуры (PG).
- `GENERATED ALWAYS AS (выражение) STORED` — вычисляемый столбец (PG 12+, SQLite 3.31+).
"""),
('Ограничения целостности', r"""
# Ограничения

Ограничения — правила, которые СУБД проверяет **сама** при каждой записи. Ошибка в приложении не сможет записать некорректные данные.

| Ограничение | Проверяет | NULL | Создаёт индекс |
|---|---|---|---|
| `NOT NULL` | значение есть | запрещён | нет |
| `PRIMARY KEY` | уникальность + NOT NULL; одна на таблицу | запрещён | да |
| `UNIQUE` | нет повторов | разрешено много NULL (PG 15+: `NULLS NOT DISTINCT` — один) | да |
| `CHECK (условие)` | условие не FALSE | **проходит**: CHECK отвергает только FALSE, а не UNKNOWN | нет |
| `FOREIGN KEY` / `REFERENCES` | значение есть в родительской таблице | проходит: NULL не проверяется | нет (индекс на ссылающийся столбец создавайте сами!) |
| `EXCLUDE` (PG) | никакие две строки не «пересекаются» по оператору | | да (GiST) |
| `DEFAULT` | не ограничение, а значение по умолчанию | | |

## Проверим на uni

```sql-error
BEGIN;
INSERT INTO enrollments (student_id, course_id, grade) VALUES (1, 7, 6);     -- CHECK grade BETWEEN 2 AND 5
ROLLBACK;
```

```sql-error
BEGIN;
INSERT INTO enrollments (student_id, course_id, grade) VALUES (99, 1, 5);    -- нет студента 99 → FOREIGN KEY
ROLLBACK;
```

```sql-error
BEGIN;
INSERT INTO enrollments (student_id, course_id, grade) VALUES (1, 1, 5);     -- уже есть пара (1, 1) → PRIMARY KEY
ROLLBACK;
```

```sql
BEGIN;
INSERT INTO enrollments (student_id, course_id, grade) VALUES (1, 7, NULL);  -- проходит: CHECK с NULL не FALSE
SELECT * FROM enrollments WHERE student_id = 1;
ROLLBACK;
```

Первые три примера заканчиваются ошибкой — это и есть демонстрация: СУБД сама не пустила плохие данные.

## PRIMARY KEY против UNIQUE NOT NULL

Почти одно и то же. Отличия: первичный ключ один, на него по умолчанию ссылаются внешние ключи, это «главный» идентификатор строки. UNIQUE может быть несколько (email, код группы).

## Имена ограничений

```pg
ALTER TABLE students ADD CONSTRAINT students_scholarship_positive CHECK (scholarship > 0);
```

С именем понятнее сообщение об ошибке, и ограничение легко удалить: `ALTER TABLE ... DROP CONSTRAINT имя`.

## Отложенная проверка

```pg
FOREIGN KEY (mentor_id) REFERENCES teachers DEFERRABLE INITIALLY DEFERRED
```

Проверка выполнится при COMMIT, а не после каждого оператора. Нужна, когда строки ссылаются друг на друга по кругу и вставляются в одной транзакции.
"""),
('Ключи: естественные и суррогатные, SERIAL, IDENTITY, UUID', r"""
# Какой ключ выбрать

| | Естественный ключ | Суррогатный ключ |
|---|---|---|
| что это | значение из предметной области: email, ИНН, код группы | искусственный номер или UUID |
| пример | `study_groups.code = 'ИТ-21'` | `study_groups.group_id = 1` |
| плюсы | понятен, не нужен лишний столбец | никогда не меняется, компактный, одинаковый подход для всех таблиц |
| минусы | может измениться (человек сменил email), бывает составным и длинным | ничего не значит, поэтому естественную уникальность надо обеспечить отдельно (UNIQUE) |

Практика: суррогатный первичный ключ + UNIQUE на естественный ключ.

## Как генерировать суррогатный ключ в PostgreSQL

| Способ | Пример | Замечание |
|---|---|---|
| `serial` / `bigserial` | `id serial PRIMARY KEY` | старый способ: создаёт sequence и DEFAULT nextval; вставка явного id ломает счётчик |
| `IDENTITY` | `id bigint GENERATED ALWAYS AS IDENTITY` | стандарт SQL, рекомендуемый способ; ALWAYS запрещает ручные значения, BY DEFAULT — разрешает |
| `uuid` | `id uuid DEFAULT gen_random_uuid()` | можно генерировать в приложении, не раскрывает количество записей, удобно при слиянии баз; 16 байт и случайный порядок вставки в индекс |
| UUIDv7 | `uuidv7()` в PostgreSQL 18 | упорядочен по времени — вставка в индекс эффективнее |

Номера из sequence не идут подряд: откат транзакции «съедает» номер. Дыры в id — это нормально, не пытайтесь их заполнять.

## Составной ключ

Таблица-мост многие-ко-многим обычно получает составной ключ из двух внешних ключей: `PRIMARY KEY (student_id, course_id)` в enrollments. Он одновременно запрещает повторную запись студента на курс.

```sql
SELECT sql FROM sqlite_master WHERE name = 'enrollments';
```
"""),
('Связи и нормализация', r"""
# Связи

| Связь | Как реализуется | Пример в uni |
|---|---|---|
| 1 : N | внешний ключ на стороне «многих» | students.group_id → study_groups |
| 1 : 1 | внешний ключ + UNIQUE на нём (или общий первичный ключ) | паспорт студента в отдельной таблице |
| M : N | таблица-мост с двумя внешними ключами | enrollments между students и courses |
| иерархия | внешний ключ на свою же таблицу | departments.parent_id, teachers.mentor_id |

## Нормальные формы коротко

**1НФ** — в ячейке одно значение, нет повторяющихся групп столбцов.
Плохо: `courses_list = 'БД, Алгоритмы'` или столбцы `course1, course2, course3`. Хорошо: таблица enrollments.

**2НФ** — 1НФ + каждый неключевой столбец зависит от **всего** составного ключа.
Плохо: в enrollments (ключ student_id + course_id) хранить `course_title` — он зависит только от course_id. Хорошо: название в courses.

**3НФ** — 2НФ + неключевые столбцы не зависят друг от друга (нет транзитивных зависимостей).
Плохо: в students хранить `group_code` и `curator_name` — куратор зависит от группы, а не от студента. Хорошо: куратор в study_groups.

**НФБК** — каждый детерминант является ключом (строже 3НФ, различается в редких случаях с несколькими пересекающимися ключами).

## Зачем

| Проблема ненормализованных данных | Пример |
|---|---|
| аномалия обновления | переименовали курс, а в половине строк осталось старое название |
| аномалия вставки | нельзя завести курс, пока на него никто не записан |
| аномалия удаления | удалили последнего студента — потеряли информацию о курсе |
| избыточность | одно и то же название хранится тысячи раз |

## Денормализация

Иногда данные дублируют намеренно: аналитические витрины, кеш суммы заказа, счётчик комментариев. Это решение ради скорости чтения, и за него платят сложностью: дубли надо поддерживать согласованными (триггеры, материализованные представления, пересчёт). В OLTP-системах по умолчанию нормализуют, в аналитических хранилищах (схема «звезда») — денормализуют.

```sql
-- нормализованная схема позволяет собрать «широкую» строку в любой момент
SELECT s.full_name, g.code, t.full_name AS curator
FROM students s
LEFT JOIN study_groups g ON g.group_id = s.group_id
LEFT JOIN teachers t ON t.teacher_id = g.curator_id;
```
"""),
('ALTER TABLE и миграции', r"""
# Изменение схемы

| Действие | PostgreSQL | SQLite |
|---|---|---|
| добавить столбец | `ALTER TABLE t ADD COLUMN c type [DEFAULT ...] [NOT NULL]` | то же (с ограничениями на NOT NULL без DEFAULT) |
| удалить столбец | `ALTER TABLE t DROP COLUMN c` | с 3.35 |
| переименовать столбец | `ALTER TABLE t RENAME COLUMN a TO b` | с 3.25 |
| переименовать таблицу | `ALTER TABLE t RENAME TO t2` | да |
| сменить тип | `ALTER TABLE t ALTER COLUMN c TYPE numeric USING c::numeric` | нет: пересоздать таблицу |
| добавить/убрать NOT NULL | `ALTER COLUMN c SET NOT NULL` / `DROP NOT NULL` | нет |
| добавить ограничение | `ADD CONSTRAINT ... CHECK/UNIQUE/FOREIGN KEY` | нет: пересоздать таблицу |
| индекс | `CREATE INDEX [CONCURRENTLY] ...` | `CREATE INDEX` |

```sql
BEGIN;
ALTER TABLE students ADD COLUMN phone TEXT;
ALTER TABLE students RENAME COLUMN phone TO mobile;
SELECT student_id, full_name, mobile FROM students LIMIT 3;
ROLLBACK;
```

## Миграции

Миграция — пронумерованный скрипт изменения схемы, который хранится в git и применяется одинаково на всех окружениях (Flyway, Liquibase, Alembic, миграции Django/Rails). Схему не меняют руками на сервере.

Хорошая миграция:
- **идемпотентна** или защищена журналом применённых миграций;
- имеет **откат** (down) или хотя бы план отката;
- не держит долгую блокировку на большой таблице.

## Безопасное добавление обязательного столбца (expand → migrate → contract)

Добавить `NOT NULL` столбец в таблицу с данными за один шаг нельзя: у существующих строк значения нет.

```pg
-- 1. expand: столбец без ограничений
ALTER TABLE students ADD COLUMN status text;
-- 2. migrate: заполнить существующие строки (на больших таблицах — пачками)
UPDATE students SET status = 'active' WHERE status IS NULL;
-- 3. contract: включить ограничение и значение по умолчанию
ALTER TABLE students ALTER COLUMN status SET DEFAULT 'active';
ALTER TABLE students ALTER COLUMN status SET NOT NULL;
```

С PostgreSQL 11 `ADD COLUMN ... DEFAULT константа NOT NULL` выполняется мгновенно, без переписывания таблицы. Но шаблон expand/contract всё равно нужен при **переименовании** и **смене типа** под работающим приложением: старая версия кода должна продолжать работать, пока не выкатят новую.

## Переименование без простоя

1. Добавить новый столбец, писать в оба (или триггер).
2. Перенести старые данные.
3. Переключить чтение на новый столбец.
4. Удалить старый.

## Индексы под нагрузкой

`CREATE INDEX` блокирует запись в таблицу на всё время построения. `CREATE INDEX CONCURRENTLY` строит дольше, но не блокирует; нельзя внутри транзакции.
"""),
('Шпаргалка DDL', r"""
# Шпаргалка: похожие конструкции DDL

| Похожие | Разница |
|---|---|
| `PRIMARY KEY` и `UNIQUE NOT NULL` | PK один, на него ссылаются по умолчанию |
| `UNIQUE` и `UNIQUE NULLS NOT DISTINCT` | много NULL или один (PG 15+) |
| `CHECK` и `NOT NULL` | CHECK пропускает NULL |
| `RESTRICT` и `NO ACTION` | NO ACTION можно отложить до COMMIT |
| `CASCADE`, `SET NULL`, `SET DEFAULT` | удалить детей, обнулить ссылку, поставить значение по умолчанию |
| `serial` и `IDENTITY` | старый способ и стандартный |
| `IDENTITY ALWAYS` и `BY DEFAULT` | запрет и разрешение ручных значений |
| целочисленный ключ и `uuid` | компактный и последовательный против глобально уникального |
| естественный и суррогатный ключ | значимый, но изменчивый, против стабильного без смысла |
| `varchar(n)` и `text` | в PG одинаковы по скорости, varchar ограничивает длину |
| `timestamp` и `timestamptz` | без часового пояса и момент времени (храните timestamptz) |
| `json` и `jsonb` | текст как есть и разобранный двоичный формат с индексами |
| `numeric` и `double precision` | точно и приближённо |
| `CREATE TABLE AS` и `CREATE TABLE (LIKE ...)` | данные без ограничений и структура без данных |
| `DROP TABLE` и `TRUNCATE` | удалить таблицу и очистить строки |
| `DROP ... CASCADE` | удалит и зависящие объекты (VIEW, внешние ключи) |
| `CREATE INDEX` и `CREATE INDEX CONCURRENTLY` | быстро с блокировкой записи и медленно без неё |
| нормализация и денормализация | нет дублей и аномалий против быстрого чтения |
"""),
]

M10 = [
('VIEW и MATERIALIZED VIEW', r"""
# Представления

**VIEW** — сохранённый в базе запрос с именем. Данных не хранит: при каждом обращении выполняется заново.

```sql
BEGIN;
CREATE VIEW student_cards AS
SELECT s.student_id, s.full_name, g.code AS group_code,
       COUNT(e.course_id) AS courses, ROUND(AVG(e.grade), 2) AS avg_grade
FROM students s
LEFT JOIN study_groups g ON g.group_id = s.group_id
LEFT JOIN enrollments e ON e.student_id = s.student_id
GROUP BY s.student_id, s.full_name, g.code;

SELECT * FROM student_cards WHERE avg_grade >= 4.5;
ROLLBACK;
```

Зачем:
- спрятать сложный запрос за простым именем;
- дать единое определение метрики («активный студент», «выручка») для всех отчётов;
- ограничить доступ: пользователю выдают права на VIEW, а не на исходные таблицы (только нужные столбцы и строки).

## MATERIALIZED VIEW (PostgreSQL)

Запрос выполняется один раз, результат **сохраняется** как таблица. Обновляется только командой REFRESH.

```pg
CREATE MATERIALIZED VIEW course_stats AS
SELECT course_id, COUNT(*) AS students, AVG(grade) AS avg_grade
FROM enrollments GROUP BY course_id;

CREATE UNIQUE INDEX ON course_stats (course_id);

REFRESH MATERIALIZED VIEW course_stats;               -- блокирует чтение на время обновления
REFRESH MATERIALIZED VIEW CONCURRENTLY course_stats;  -- не блокирует, нужен UNIQUE индекс
```

## Сравнение

| | VIEW | MATERIALIZED VIEW | Таблица | CTE |
|---|---|---|---|---|
| хранит данные | нет | да, снимок | да | нет |
| актуальность | всегда | на момент REFRESH | как поддерживаете | всегда |
| скорость чтения | как у исходного запроса | как у таблицы | как у таблицы | как у запроса |
| индексы | нет | да | да | нет |
| можно ли INSERT/UPDATE | простые VIEW — да | нет | да | — |
| живёт | в базе | в базе | в базе | один запрос |
| когда | общая логика, доступ | тяжёлые отчёты, дашборды | исходные данные | один сложный запрос |

## Обновляемые представления

Простое VIEW (одна таблица, без GROUP BY, DISTINCT, агрегатов, оконных функций) в PostgreSQL можно обновлять: INSERT/UPDATE/DELETE уходят в базовую таблицу. `WITH CHECK OPTION` запрещает вставить через VIEW строку, которую само VIEW не покажет:

```pg
CREATE VIEW moscow_students AS
SELECT * FROM students WHERE city = 'Москва'
WITH CHECK OPTION;
INSERT INTO moscow_students (...) VALUES (..., 'Тула', ...);  -- ошибка: нарушает условие VIEW
```

Сложные VIEW обновляют через триггеры `INSTEAD OF`.
"""),
('Функции, процедуры и триггеры', r"""
# Функции, процедуры, триггеры (PostgreSQL)

| | Функция | Процедура | Триггер |
|---|---|---|---|
| создаётся | `CREATE FUNCTION` | `CREATE PROCEDURE` (PG 11+) | `CREATE TRIGGER` + функция `RETURNS trigger` |
| вызывается | в выражении: `SELECT f(x)` | `CALL p(x)` | автоматически при INSERT/UPDATE/DELETE/TRUNCATE |
| возвращает | значение, строку или набор строк (`RETURNS TABLE`) | ничего (или OUT-параметры) | NEW/OLD или NULL |
| транзакции внутри | нельзя COMMIT/ROLLBACK | можно COMMIT/ROLLBACK | нельзя |
| когда | вычисление, переиспользуемая логика запросов | пакетная обработка по частям с фиксацией | инварианты, аудит, производные данные |

```pg
CREATE FUNCTION student_avg(p_student_id int)
RETURNS numeric
LANGUAGE sql STABLE
AS $$
    SELECT round(avg(grade), 2) FROM enrollments WHERE student_id = p_student_id;
$$;

SELECT full_name, student_avg(student_id) FROM students;
```

```pg
CREATE PROCEDURE archive_old_payments(p_before date)
LANGUAGE plpgsql
AS $$
BEGIN
    LOOP
        DELETE FROM dorm_payments
        WHERE payment_id IN (SELECT payment_id FROM dorm_payments WHERE paid_on < p_before LIMIT 1000);
        EXIT WHEN NOT FOUND;
        COMMIT;            -- фиксируем каждую пачку: блокировки короткие
    END LOOP;
END $$;

CALL archive_old_payments('2025-01-01');
```

## Волатильность функций

| Категория | Обещание | Примеры | Что даёт |
|---|---|---|---|
| `IMMUTABLE` | одинаковые аргументы → всегда одинаковый результат, не читает базу | `lower`, `abs`, математика | можно строить индекс по выражению, вычислять заранее |
| `STABLE` | в пределах одного запроса результат не меняется, может читать базу | `now()`, чтение справочника | можно использовать в условиях индексного поиска |
| `VOLATILE` (по умолчанию) | может меняться при каждом вызове или менять данные | `random()`, `nextval()`, функции с INSERT | вызывается для каждой строки, без оптимизаций |

Если пометить функцию IMMUTABLE, а она читает таблицу, индекс по ней будет содержать устаревшие данные. Обещание проверяете вы, а не СУБД.

## SECURITY DEFINER против SECURITY INVOKER

- `SECURITY INVOKER` (по умолчанию) — функция работает с правами вызывающего.
- `SECURITY DEFINER` — с правами владельца функции. Так дают ограниченный доступ: пользователь не видит таблицу зарплат, но может вызвать функцию «средняя зарплата по кафедре».
- В SECURITY DEFINER обязательно фиксируйте `SET search_path = pg_catalog, public`, иначе злоумышленник подсунет свою функцию с тем же именем в другую схему.

## Ошибки в plpgsql

```pg
BEGIN
    INSERT INTO ...;
EXCEPTION
    WHEN unique_violation THEN
        RAISE NOTICE 'уже есть';
    WHEN OTHERS THEN
        RAISE;                         -- пробросить дальше
END;
```

Блок с EXCEPTION внутри создаёт неявный SAVEPOINT — это дорого, не ставьте его в цикл на миллион строк без необходимости. `RAISE EXCEPTION 'текст %', значение` — прервать с ошибкой.
"""),
('Триггеры подробно', r"""
# Триггеры

Триггер — действие, которое СУБД выполняет автоматически при изменении таблицы.

| Признак | Варианты | Значение |
|---|---|---|
| момент | `BEFORE` | до изменения: можно поправить NEW или отменить операцию (вернуть NULL) |
| | `AFTER` | после: строка уже записана; для аудита, каскадных действий |
| | `INSTEAD OF` | вместо операции; только для VIEW |
| уровень | `FOR EACH ROW` | для каждой изменённой строки, доступны NEW и OLD |
| | `FOR EACH STATEMENT` | один раз на оператор, даже если строк 0 (PG) |
| событие | INSERT, UPDATE [OF столбцы], DELETE, TRUNCATE | |
| условие | `WHEN (OLD.salary IS DISTINCT FROM NEW.salary)` | срабатывать только при изменении значения |

| | NEW | OLD |
|---|---|---|
| INSERT | новая строка | — |
| UPDATE | строка после | строка до |
| DELETE | — | удаляемая строка |

## Пример: журнал изменений зарплат (SQLite)

В SQLite тело триггера пишется прямо на SQL между BEGIN и END:

```sql
BEGIN;
CREATE TABLE salary_log (teacher_id INTEGER, old_salary INTEGER, new_salary INTEGER, changed_at TEXT);

CREATE TRIGGER trg_salary_log
AFTER UPDATE OF salary ON teachers
FOR EACH ROW
WHEN OLD.salary <> NEW.salary
BEGIN
    INSERT INTO salary_log VALUES (OLD.teacher_id, OLD.salary, NEW.salary, datetime('now'));
END;

UPDATE teachers SET salary = salary + 10000 WHERE dept_id = 2;
UPDATE teachers SET salary = salary WHERE dept_id = 3;      -- не изменилась → в журнал не попадёт
SELECT * FROM salary_log;
ROLLBACK;
```

## То же в PostgreSQL

```pg
CREATE FUNCTION log_salary() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO salary_log VALUES (OLD.teacher_id, OLD.salary, NEW.salary, now());
    RETURN NEW;              -- для AFTER значение игнорируется, но вернуть что-то надо
END $$;

CREATE TRIGGER trg_salary_log
AFTER UPDATE OF salary ON teachers
FOR EACH ROW
WHEN (OLD.salary IS DISTINCT FROM NEW.salary)
EXECUTE FUNCTION log_salary();
```

## BEFORE-триггер: проверка или исправление

```sql-error
BEGIN;
CREATE TRIGGER trg_no_future_exam
BEFORE INSERT ON enrollments
FOR EACH ROW
WHEN NEW.exam_date > '2026-12-31'
BEGIN
    SELECT RAISE(ABORT, 'дата экзамена слишком далеко в будущем');
END;
INSERT INTO enrollments (student_id, course_id, exam_date) VALUES (12, 1, '2030-01-01');
ROLLBACK;
```

Пример заканчивается ошибкой из триггера — так и задумано.

## Когда триггер, а когда нет

| Задача | Чем решать |
|---|---|
| простое правило на одну строку | CHECK — проще и быстрее триггера |
| ссылка на другую таблицу | FOREIGN KEY |
| аудит, история изменений | триггер AFTER |
| поддержка денормализованного поля (счётчик, сумма) | триггер или материализованное представление |
| бизнес-процесс (письмо, расчёт бонуса) | приложение: триггеры невидимы, их легко забыть при отладке |

Триггеры срабатывают неявно, и это их главный минус: «почему эта таблица изменилась?» — первый вопрос новичка в проекте с триггерами.
"""),
('JSON в SQL', r"""
# JSON

Иногда у сущностей разный набор атрибутов (у курса — аудитория и теги, у другого — ссылка на трансляцию). Такие данные хранят в JSON-столбце. В uni это `courses.meta`.

## json против jsonb (PostgreSQL)

| | json | jsonb |
|---|---|---|
| хранение | текст как есть | разобранный двоичный формат |
| запись | быстрее | немного медленнее (разбор) |
| чтение и поиск | разбирает при каждом обращении | быстро |
| порядок ключей, пробелы, дубликаты ключей | сохраняет | не сохраняет (последний ключ побеждает) |
| индексы GIN, операторы `@>`, `?` | нет | да |

Почти всегда нужен **jsonb**.

## Операторы и функции

| Задача | PostgreSQL | SQLite |
|---|---|---|
| значение как JSON | `meta -> 'tags'` | `meta -> '$.tags'` |
| значение как текст | `meta ->> 'format'` | `meta ->> '$.format'`, `json_extract(meta, '$.format')` |
| по пути | `meta #>> '{tags,0}'` | `meta ->> '$.tags[0]'` |
| содержит пару | `meta @> '{"format": "online"}'` | `meta ->> '$.format' = 'online'` |
| есть ключ | `meta ? 'room'` | `json_extract(meta, '$.room') IS NOT NULL` |
| развернуть массив в строки | `jsonb_array_elements_text(meta -> 'tags')` | `json_each(meta, '$.tags')` |
| длина массива | `jsonb_array_length(meta -> 'tags')` | `json_array_length(meta, '$.tags')` |
| собрать JSON | `jsonb_build_object('a', 1)`, `jsonb_agg(x)` | `json_object('a', 1)`, `json_group_array(x)` |

`->` возвращает JSON (строка будет в кавычках), `->>` — текст. Для сравнения со строкой или числом нужен `->>`.

```sql
SELECT title,
       meta -> '$.format'           AS format_json,
       meta ->> '$.format'          AS format_text,
       meta ->> '$.room'            AS room,
       json_array_length(meta, '$.tags') AS tags_count
FROM courses;
```

```sql
-- развернуть массив тегов: курс × тег
SELECT c.title, t.value AS tag
FROM courses c, json_each(c.meta, '$.tags') AS t
ORDER BY tag, c.title;
```

```sql
-- обратно: собрать список курсов в JSON-массив по формату
SELECT meta ->> '$.format' AS format, json_group_array(title) AS courses
FROM courses WHERE meta IS NOT NULL
GROUP BY format;
```

```pg
SELECT title FROM courses WHERE meta @> '{"tags": ["python"]}';    -- массив содержит "python"
CREATE INDEX ON courses USING gin (meta);                         -- ускоряет @> и ?
```

## Когда не стоит класть данные в JSON

Если по полю постоянно фильтруют, группируют, соединяют, или на него нужны ограничения (NOT NULL, FOREIGN KEY) — это обычный столбец. JSON хорош для редко используемых, разнородных атрибутов и для «сырых» данных из внешних API.
"""),
('Индексы', r"""
# Индексы

Индекс — отдельная структура, которая позволяет найти строки по значению без чтения всей таблицы. Аналогия — алфавитный указатель в книге.

## Виды индексов PostgreSQL

| Тип | Для чего | Операторы |
|---|---|---|
| B-tree (по умолчанию) | равенство, диапазоны, сортировка, `LIKE 'abc%'` | `= < > BETWEEN IN`, ORDER BY |
| Hash | только равенство | `=` |
| GIN | «содержит»: массивы, jsonb, полнотекстовый поиск, триграммы (`pg_trgm` для `LIKE '%abc%'`) | `@> ? && @@` |
| GiST | геометрия, диапазоны, ближайшие соседи, EXCLUDE | `&& <-> @>` |
| BRIN | огромные таблицы, где значения коррелируют с физическим порядком (время вставки) | диапазоны; индекс крошечный |

## Разновидности B-tree

```pg
CREATE INDEX ON enrollments (course_id, grade);                 -- составной
CREATE INDEX ON students (lower(email));                        -- по выражению
CREATE INDEX ON enrollments (exam_date) WHERE grade IS NULL;    -- частичный
CREATE INDEX ON enrollments (student_id) INCLUDE (grade);       -- покрывающий
CREATE UNIQUE INDEX ON students (email);                        -- уникальный
```

| Вид | Когда помогает |
|---|---|
| составной `(a, b)` | условия на `a`, на `a AND b`, сортировка `a, b`. **Не** помогает условию только на `b` — порядок столбцов важен: сначала равенство, потом диапазон |
| по выражению | запрос использует то же выражение: `WHERE lower(email) = ...` |
| частичный | запросы всегда фильтруют одно подмножество (активные, неоплаченные) — индекс меньше и быстрее |
| покрывающий (`INCLUDE`) | все нужные запросу столбцы есть в индексе → Index Only Scan без чтения таблицы |

## Когда индекс не используется

- Функция над столбцом: `WHERE date(paid_on) = '2025-10-01'` не использует индекс по paid_on. Перепишите диапазоном или создайте индекс по выражению.
- `LIKE '%abc'` — ведущий `%`. Нужен триграммный GIN.
- Несовпадение типов: столбец text, а сравниваете с числом.
- Условие выбирает большую часть таблицы — последовательное чтение дешевле, и оптимизатор прав.
- Условие на второй столбец составного индекса без первого.
- `OR` по разным столбцам (иногда решается Bitmap OR или UNION).
- Устаревшая статистика — `ANALYZE`.

## Цена индексов

Каждый индекс замедляет INSERT/UPDATE/DELETE (его тоже надо обновить) и занимает место. Индексируйте под реальные частые запросы, а не «все столбцы на всякий случай». Обязательно индексируйте внешние ключи, по которым соединяете, — PostgreSQL сам их не создаёт.
"""),
('EXPLAIN: как читать план', r"""
# EXPLAIN

`EXPLAIN запрос` показывает план: как СУБД собирается выполнить запрос. `EXPLAIN ANALYZE` **выполняет** запрос и показывает реальное время и число строк (осторожно с UPDATE/DELETE — оборачивайте в BEGIN … ROLLBACK).

```pg
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM enrollments WHERE course_id = 3;

-- Index Scan using idx_enrollments_course on enrollments  (cost=0.15..8.17 rows=4 width=20)
--                                                  (actual time=0.010..0.012 rows=5 loops=1)
--   Index Cond: (course_id = 3)
```

- `cost=начальная..полная` — оценка в условных единицах.
- `rows` — **оценка** числа строк; `actual rows` — реальное. Большое расхождение — главный признак плохого плана (статистика устарела, корреляции столбцов).
- `loops` — сколько раз выполнялся узел (у внутренней стороны Nested Loop может быть тысячи).
- План читается **изнутри наружу**, снизу вверх.

## Способы чтения таблицы

| Узел | Что делает | Когда хорош |
|---|---|---|
| Seq Scan | читает всю таблицу | маленькая таблица или нужна большая часть строк |
| Index Scan | идёт по индексу и за каждой строкой в таблицу | выбирается мало строк |
| Index Only Scan | берёт всё из индекса, таблицу не трогает | все столбцы есть в индексе (INCLUDE) |
| Bitmap Index Scan + Bitmap Heap Scan | сначала собирает список страниц, потом читает их по порядку | средняя доля строк, комбинации условий (AND/OR) |

## Способы соединения

| Алгоритм | Как работает | Когда выбирается |
|---|---|---|
| Nested Loop | для каждой строки внешней стороны ищет пары во внутренней (обычно по индексу) | внешняя сторона маленькая, на внутренней есть индекс |
| Hash Join | строит хеш-таблицу по меньшей стороне, прогоняет через неё большую | большие наборы, условие равенства, нет полезных индексов |
| Merge Join | сливает два отсортированных потока | обе стороны уже отсортированы (индексы) или нужен отсортированный результат |

## В тренажёре

SQLite показывает упрощённый план через `EXPLAIN QUERY PLAN`:

```sql
EXPLAIN QUERY PLAN
SELECT s.full_name, e.grade
FROM students s JOIN enrollments e ON e.student_id = s.student_id
WHERE e.course_id = 3;
```

```sql
EXPLAIN QUERY PLAN
SELECT * FROM students WHERE lower(email) = 'ivan@uni.ru';   -- SCAN: функция над столбцом
```

`SCAN` — полное чтение, `SEARCH ... USING INDEX` — поиск по индексу.

## Шпаргалка модуля

| Похожие | Разница |
|---|---|
| VIEW и MATERIALIZED VIEW | запрос и сохранённый снимок |
| `REFRESH` и `REFRESH CONCURRENTLY` | с блокировкой чтения и без (нужен UNIQUE индекс) |
| функция и процедура | возвращает значение, вызывается в SELECT / вызывается CALL, может COMMIT |
| `BEFORE` и `AFTER` триггер | можно изменить или отменить строку / строка уже записана |
| `FOR EACH ROW` и `FOR EACH STATEMENT` | на строку и на оператор |
| `IMMUTABLE`, `STABLE`, `VOLATILE` | всегда одинаково / в рамках запроса / как угодно |
| `SECURITY DEFINER` и `INVOKER` | права владельца и права вызывающего |
| `json` и `jsonb` | текст и двоичный формат с индексами |
| `->` и `->>` | JSON и текст |
| B-tree, Hash, GIN, GiST, BRIN | универсальный, равенство, «содержит», геометрия/диапазоны, огромные упорядоченные таблицы |
| Seq Scan и Index Scan | вся таблица и поиск по индексу |
| Nested Loop, Hash Join, Merge Join | мало строк + индекс / много строк, равенство / отсортированные входы |
| `EXPLAIN` и `EXPLAIN ANALYZE` | оценка и реальное выполнение |
"""),
]

PAGES = {'m06': M06, 'm07': M07, 'm08': M08, 'm09': M09, 'm10': M10}
