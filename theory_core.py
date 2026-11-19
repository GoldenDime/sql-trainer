"""Теория модулей 0–5. Примеры — на демо-базе uni, а не на базах заданий.

Разметка: ```sql — пример, который можно выполнить кнопкой (база uni);
```pg — синтаксис только PostgreSQL; ```bad — так делать не надо; ``` — схема синтаксиса.
"""

M00 = [
('Как устроен тренажёр', r"""
# Как устроен тренажёр

Слева — модули. В каждом модуле есть раздел **«Теория»** из нескольких страниц и **задания**. Теория рассказывает тему целиком: все варианты конструкции, чем они отличаются и где ломаются. Задания — отдельная практика, готовых решений в теории нет.

## Три базы

| База | Зачем | Что внутри |
|---|---|---|
| uni | примеры в теории и эксперименты | университет (кафедры, преподаватели, группы, студенты, курсы, оценки) и онлайн-школа (lms_users, lms_events, lms_payments) |
| shop | задания модулей 1–10 | магазин из лекций |
| market | задания модулей 4–16 | маркетплейс за 2025 год |

Примеры теории нарочно написаны на другой предметной области: технику вы видите, а перенести её на магазин или маркетплейс — уже работа для заданий.

## Как пользоваться теорией

- Под каждым примером есть кнопка **▶ Выполнить пример**: запрос попадает в редактор и выполняется на базе uni. Меняйте его, запускайте снова (F5) — это песочница, сломать ничего нельзя.
- Блоки с пометкой **PostgreSQL** показывают синтаксис, которого нет во встроенном SQLite. Их можно проверить в своём PostgreSQL 17 после «Экспорта в PostgreSQL».
- Блоки с пометкой **так не надо** — типичные ошибки.
- Внизу страницы ссылки «← назад» и «далее →».

## Задания

- **F5 / Ctrl+Enter** — выполнить, **F9 / Ctrl+Shift+Enter** — проверить.
- «Подсказка» открывает подсказки по одной (каждая уменьшает опыт), «Решение» показывает эталон (задание засчитывается без опыта).
- Проверяется результат, а не текст запроса. Имена столбцов не важны, порядок строк — только если в условии сказано «отсортируйте». Числа сравниваются с точностью до 0.01.

Прогресс хранится в `progress.json` рядом с программой. Решённые задания возвращаются в «Повторение» через 2, 6, 15, 35 и 80 дней.
"""),
('Демо-база uni', r"""
# Демо-база uni

Маленькая база, на которой удобно видеть разницу между конструкциями: в ней специально есть пустые значения, «сироты» и повторы.

## Университет

| Таблица | Столбцы | Особенности |
|---|---|---|
| departments | dept_id, name, parent_id | дерево: институты → кафедры → лаборатория; у кафедры маркетинга нет преподавателей |
| teachers | teacher_id, full_name, dept_id, hired_on, salary, mentor_id | Гусев без кафедры (dept_id NULL); mentor_id — ссылка на другого преподавателя |
| study_groups | group_id, code, year, curator_id | у группы ЭК-23 нет куратора |
| students | student_id, full_name, group_id, city, birth_date, email, scholarship | Миронова без группы; у двоих нет email; стипендия у многих NULL |
| courses | course_id, title, credits, teacher_id, meta | meta — JSON; у «Философии» нет преподавателя и нет записей |
| enrollments | student_id, course_id, grade, exam_date | оценка NULL — экзамен ещё не сдавался; много одинаковых оценок |
| club_members | email | члены шахматного клуба; один email NULL, один «чужой» |
| dorm_payments | payment_id, student_id, paid_on, amount | оплаты общежития за осень 2025, с пропущенными месяцами |
| library_visits | day, visits | посещаемость библиотеки, воскресений нет (закрыто) |

## Онлайн-школа

| Таблица | Столбцы |
|---|---|
| lms_users | user_id, signup_date, channel (ads / blog / friend), variant (A / B) |
| lms_events | user_id, event_time, event (visit / lesson / homework / purchase) |
| lms_payments | payment_id, user_id, paid_at, amount, plan (month / year) |

600 учеников, январь–июнь 2025. На ней показаны метрики, воронки, когорты и A/B-тесты.

Посмотреть всё сразу:
```sql
SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name;
```
"""),
('SQLite здесь, PostgreSQL на парах', r"""
# SQLite здесь, PostgreSQL на парах

Тренажёр работает на встроенном SQLite, чтобы ничего не ставить. Стандартная часть SQL (SELECT, JOIN, GROUP BY, подзапросы, CTE, окна, INSERT/UPDATE/DELETE, ON CONFLICT, RETURNING) совпадает. Для привычности добавлены функции PostgreSQL: `date_trunc`, `date_part`, `greatest`, `least`, `split_part`, `string_agg`, `median`, `percentile_cont`, `stddev`, `corr`, `bool_and`, `bool_or`.

| Тема | PostgreSQL | SQLite в тренажёре |
|---|---|---|
| приведение типа | `x::int`, `CAST(x AS int)` | только `CAST(x AS INTEGER)` |
| целочисленное деление | `5/2 = 2` | `5/2 = 2` (так же) |
| логический тип | `boolean`, `true/false` | числа 1/0 |
| даты | типы `date`, `timestamp`, `interval` | текст `'2025-11-03 10:00:00'` + функции `date()`, `datetime()`, `julianday()` |
| сдвиг даты | `d + interval '7 days'` | `date(d, '+7 day')` |
| разница дат в днях | `d2 - d1` (для date) | `julianday(d2) - julianday(d1)` |
| регистронезависимый LIKE | `ILIKE` | `LIKE` уже без учёта регистра для латиницы; надёжно: `lower(x) LIKE ...` |
| регулярки | `~`, `~*`, `regexp_replace` | `regexp_like(x, p)`, `x REGEXP p`, `regexp_replace` (добавлены) |
| ряд чисел/дат | `generate_series` | рекурсивный CTE |
| `ANY`/`ALL` | есть | нет — заменяем на `IN`, `MIN`, `MAX`, `EXISTS` |
| `ROLLUP`, `CUBE` | есть | нет — заменяем на `UNION ALL` |
| `DISTINCT ON` | есть | нет — заменяем на `ROW_NUMBER()` |
| JSON | `json`/`jsonb`, `->`, `->>`, `@>`, `?` | `->`, `->>`, `json_extract`, `json_each` |
| процедуры, plpgsql | есть | нет (только триггеры на SQL) |
| изоляция транзакций | 4 уровня, MVCC | одна запись в каждый момент, всегда serializable |

В теории синтаксис PostgreSQL дан отдельными блоками, а запускаемые примеры написаны так, чтобы работать в обоих СУБД, где это возможно.
"""),
]

M01 = [
('Анатомия SELECT и порядок выполнения', r"""
# Анатомия SELECT

```
SELECT [DISTINCT] выражение [AS алиас], ...
FROM источник
[JOIN ... ON ...]
[WHERE условие_для_строки]
[GROUP BY выражения]
[HAVING условие_для_группы]
[WINDOW ...]
[ORDER BY выражение [ASC|DESC] [NULLS FIRST|LAST], ...]
[LIMIT n [OFFSET k]];
```

Пишем мы в этом порядке, а СУБД **логически** выполняет запрос в другом. Если запомнить этот порядок, почти все «почему не работает» объясняются сами.

| Шаг | Часть | Что происходит | Что уже видно |
|---|---|---|---|
| 1 | FROM, JOIN | собирается исходный набор строк | столбцы таблиц |
| 2 | WHERE | отбрасываются строки | столбцы таблиц |
| 3 | GROUP BY | строки схлопываются в группы | ключи группировки |
| 4 | HAVING | отбрасываются группы | ключи и агрегаты |
| 5 | оконные функции | считаются окна поверх результата | всё выше |
| 6 | SELECT | вычисляются выражения и алиасы | всё выше |
| 7 | DISTINCT | убираются повторы | итоговые столбцы |
| 8 | ORDER BY | сортировка | алиасы из SELECT |
| 9 | LIMIT / OFFSET | обрезка | — |

## Что из этого следует

- Алиас из SELECT **нельзя** использовать в WHERE: на шаге 2 его ещё нет. В ORDER BY — можно.
- Агрегат (`COUNT`, `AVG`) нельзя писать в WHERE: группы появятся только на шаге 3. Для условий на агрегаты есть HAVING.
- Оконную функцию нельзя фильтровать в WHERE и HAVING: она считается на шаге 5. Нужен подзапрос или CTE.
- `LIMIT` срабатывает последним: «первые 3» — это первые 3 **после** сортировки.

```bad
SELECT full_name, salary * 12 AS year_salary
FROM teachers
WHERE year_salary > 1500000;      -- алиаса ещё нет
```

```sql
SELECT full_name, salary * 12 AS year_salary
FROM teachers
WHERE salary * 12 > 1500000       -- повторяем выражение
ORDER BY year_salary DESC;        -- а тут алиас уже есть
```

SQLite разрешает алиас в WHERE как расширение, PostgreSQL — нет. Привыкайте писать переносимо.

Реальный план выполнения может отличаться (оптимизатор переставляет шаги), но результат всегда такой, как будто шаги шли по таблице выше.
"""),
('WHERE: условия отбора', r"""
# WHERE: условия отбора строк

WHERE проверяет условие для **каждой строки** отдельно. Строка остаётся, только если условие дало TRUE. FALSE и **UNKNOWN** (результат сравнения с NULL) строку отбрасывают.

## Операторы

| Оператор | Пример | Замечание |
|---|---|---|
| `=`, `<>` (`!=`), `<`, `<=`, `>`, `>=` | `credits >= 5` | с NULL всегда дают UNKNOWN |
| `BETWEEN a AND b` | `salary BETWEEN 90000 AND 150000` | включает обе границы: это `>= a AND <= b` |
| `IN (список)` | `city IN ('Тула', 'Тверь')` | короткая запись для цепочки `OR` |
| `LIKE` | `full_name LIKE 'Б%'` | `%` — любая строка, `_` — один символ |
| `IS NULL`, `IS NOT NULL` | `email IS NULL` | единственный правильный способ проверить NULL |
| `AND`, `OR`, `NOT` | | приоритет: NOT, затем AND, затем OR |

## Приоритет AND и OR

`AND` связывает сильнее, чем `OR`. Это частый источник ошибок:

```sql
-- Хотели: студенты из Москвы или Тулы, у которых есть стипендия
SELECT full_name, city, scholarship
FROM students
WHERE city = 'Москва' OR city = 'Тула' AND scholarship IS NOT NULL;
-- А получили: все москвичи + туляки со стипендией
```

```sql
SELECT full_name, city, scholarship
FROM students
WHERE (city = 'Москва' OR city = 'Тула') AND scholarship IS NOT NULL;
```

Правило: если в условии есть и AND, и OR — ставьте скобки всегда, даже когда они не нужны.

## BETWEEN и полуинтервал

`BETWEEN` удобен для чисел. Для дат со временем он опасен: `paid_on BETWEEN '2025-10-01' AND '2025-10-31'` потеряет всё, что случилось 31-го позже полуночи, если в столбце есть время. Надёжная форма — полуинтервал: `>= начало AND < следующее_начало`.

```sql
SELECT student_id, paid_on, amount
FROM dorm_payments
WHERE paid_on >= '2025-10-01' AND paid_on < '2025-11-01';
```

## IN против цепочки OR

`x IN (1, 2, 3)` — то же самое, что `x = 1 OR x = 2 OR x = 3`. Отличия появляются только с NULL и с подзапросами, об этом в модуле 5.

## LIKE

- `'Б%'` — начинается с Б; `'%ова'` — заканчивается на «ова»; `'%@uni.ru'` — домен; `'_____'` — ровно 5 символов.
- Чтобы найти сам символ `%` или `_`, нужен `ESCAPE`: `LIKE '%10\%%' ESCAPE '\'`.
- В PostgreSQL `LIKE` чувствителен к регистру, для поиска без учёта регистра — `ILIKE` или `lower(x) LIKE lower(шаблон)`.

```sql
SELECT full_name FROM students WHERE full_name LIKE '%ова %';
```
"""),
('NULL и трёхзначная логика', r"""
# NULL и трёхзначная логика

NULL — это не ноль и не пустая строка, а «значение неизвестно». Любое сравнение с неизвестным тоже неизвестно: `NULL = NULL` даёт не TRUE, а **UNKNOWN**.

## Таблицы истинности

| a | b | a AND b | a OR b | NOT a |
|---|---|---|---|---|
| TRUE | UNKNOWN | UNKNOWN | TRUE | FALSE |
| FALSE | UNKNOWN | FALSE | UNKNOWN | TRUE |
| UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |

WHERE пропускает только TRUE. Поэтому строки, где условие UNKNOWN, исчезают **и из условия, и из его отрицания**:

```sql
SELECT
  (SELECT COUNT(*) FROM students)                          AS всего,
  (SELECT COUNT(*) FROM students WHERE scholarship > 4000)  AS больше_4000,
  (SELECT COUNT(*) FROM students WHERE NOT scholarship > 4000) AS не_больше_4000;
```

Сумма двух последних чисел меньше общего количества: студенты без стипендии не попали ни туда, ни туда.

## Как правильно

| Задача | Правильно | Неправильно |
|---|---|---|
| значение отсутствует | `email IS NULL` | `email = NULL` (всегда пусто) |
| значение есть | `email IS NOT NULL` | `email <> NULL` |
| «не равно X, включая пустые» | `city <> 'Москва' OR city IS NULL` | `city <> 'Москва'` |
| сравнить, считая NULL равными | `a IS NOT DISTINCT FROM b` (PG, SQLite 3.39+), `a IS b` (SQLite) | `a = b` |
| подставить значение вместо NULL | `COALESCE(scholarship, 0)` | |

```sql
SELECT full_name, scholarship,
       scholarship > 4000                AS "сравнение",
       scholarship IS NULL               AS "пусто",
       COALESCE(scholarship, 0) > 4000   AS "с COALESCE"
FROM students;
```

## NULL в выражениях и функциях

- Арифметика: `NULL + 1 = NULL`, `NULL * 0 = NULL`.
- Склейка строк: `'a' || NULL = NULL` (а `concat('a', NULL) = 'a'`).
- Агрегаты (SUM, AVG, MIN, MAX, COUNT(столбец)) пропускают NULL. `COUNT(*)` считает строки целиком.
- Сортировка: в PostgreSQL NULL считается **больше** всех значений (в конце при ASC), в SQLite — **меньше** (в начале). Управлять: `NULLS FIRST` / `NULLS LAST`.
- `DISTINCT` и `GROUP BY` считают все NULL одинаковыми: получится одна группа NULL.
- `UNIQUE` разрешает много NULL (они «не равны» друг другу); в PostgreSQL 15+ можно `UNIQUE NULLS NOT DISTINCT`.

## Где NULL кусается сильнее всего

1. `NOT IN (подзапрос)`, если в подзапросе есть NULL, — пустой результат (модуль 5).
2. Условие на правую таблицу LEFT JOIN в WHERE — внешнее соединение превращается во внутреннее (модуль 4).
3. `AVG(x)` не равно `SUM(x) / COUNT(*)`, если в x есть NULL (модуль 3).
"""),
('ORDER BY, LIMIT и пагинация', r"""
# ORDER BY, LIMIT и пагинация

Без ORDER BY порядок строк **не определён**. Сегодня он совпадает с порядком вставки, завтра после VACUUM или параллельного плана — нет. Если порядок важен, сортируйте явно.

## Варианты сортировки

```sql
SELECT full_name, city, birth_date
FROM students
ORDER BY city ASC, birth_date DESC;   -- сначала по городу, внутри города — младшие выше
```

- По нескольким ключам: второй ключ работает только внутри одинаковых значений первого.
- По выражению: `ORDER BY length(full_name)`, `ORDER BY CASE WHEN city = 'Москва' THEN 0 ELSE 1 END, city`.
- По алиасу из SELECT: `ORDER BY year_salary`.
- По номеру столбца: `ORDER BY 2 DESC` — коротко, но ломается при правке SELECT.
- NULL: `ORDER BY scholarship DESC NULLS LAST` (PostgreSQL и SQLite 3.30+).

```sql
SELECT full_name, scholarship
FROM students
ORDER BY scholarship DESC NULLS LAST, full_name;
```

## LIMIT, OFFSET и FETCH

| Запись | Где работает |
|---|---|
| `LIMIT 5 OFFSET 10` | PostgreSQL, SQLite, MySQL |
| `OFFSET 10 ROWS FETCH FIRST 5 ROWS ONLY` | стандарт SQL, PostgreSQL |
| `FETCH FIRST 3 ROWS WITH TIES` | PostgreSQL 13+: добавит строки, равные последней по ключу сортировки |

`LIMIT` без `ORDER BY` возвращает «какие-то» строки. «Топ-3» без сортировки — ошибка.

## Ничьи

Если ключ сортировки не уникален, порядок равных строк случаен, и «первые 3» могут отличаться между запусками. Добавляйте уникальный ключ последним: `ORDER BY salary DESC, teacher_id`.

```sql
SELECT student_id, course_id, grade
FROM enrollments
WHERE grade IS NOT NULL
ORDER BY grade DESC, student_id, course_id
LIMIT 5;
```

```pg
SELECT student_id, course_id, grade
FROM enrollments
ORDER BY grade DESC NULLS LAST
FETCH FIRST 5 ROWS WITH TIES;     -- все пятёрки, даже если их больше пяти
```

## OFFSET-пагинация против keyset-пагинации

| | `LIMIT 20 OFFSET 10000` | keyset: `WHERE id > :последний LIMIT 20` |
|---|---|---|
| скорость на дальних страницах | падает: СУБД читает и выбрасывает 10000 строк | постоянная, идёт по индексу |
| перейти на страницу N | можно | нельзя, только «следующая» |
| если между запросами добавили строки | строки дублируются или пропадают | стабильно |

```sql
-- следующая «страница» студентов после student_id = 5
SELECT student_id, full_name FROM students
WHERE student_id > 5
ORDER BY student_id
LIMIT 4;
```
"""),
('DISTINCT, DISTINCT ON и GROUP BY', r"""
# DISTINCT и его родственники

`SELECT DISTINCT a, b` убирает строки, у которых совпадают **все** выбранные столбцы сразу, а не каждый по отдельности.

```sql
SELECT DISTINCT city FROM students ORDER BY city;
```

```sql
SELECT DISTINCT city, group_id FROM students ORDER BY city, group_id;
-- пар «город + группа» больше, чем городов
```

## DISTINCT против GROUP BY

Для простого «уникального списка» оба дают одно и то же, планы почти одинаковые:

```sql
SELECT city FROM students GROUP BY city ORDER BY city;
```

| | DISTINCT | GROUP BY |
|---|---|---|
| назначение | убрать дубликаты из результата | собрать группы, чтобы посчитать агрегаты |
| агрегаты | нет | `COUNT`, `SUM`, … по каждой группе |
| условие на группу | нет | `HAVING` |
| когда выбрать | нужен только список значений | нужно что-то посчитать |

`COUNT(DISTINCT x)` — отдельная вещь: число разных значений внутри группы.

## DISTINCT ON (только PostgreSQL)

«Одна строка на каждое значение ключа, а какая именно — решает ORDER BY». Например, самый высокооплачиваемый преподаватель каждой кафедры:

```pg
SELECT DISTINCT ON (dept_id) dept_id, full_name, salary
FROM teachers
ORDER BY dept_id, salary DESC;   -- ORDER BY обязан начинаться с ключа DISTINCT ON
```

В SQLite и в любом другом SQL то же самое делается оконной функцией `ROW_NUMBER()` (модуль 7). Это переносимый способ, и он гибче: можно взять не одну, а N строк на группу.

## Когда DISTINCT — признак ошибки

Если после JOIN «вдруг появились дубли» и вы лечите их `DISTINCT`, скорее всего, соединение размножило строки (связь один-ко-многим). DISTINCT прячет симптом, а суммы при этом остаются раздутыми. Сначала разберитесь, откуда повторы (модуль 4, «Размножение строк»).
"""),
('Шпаргалка: похожие конструкции', r"""
# Шпаргалка: похожие конструкции модуля

| Похожие | Разница | Что выбрать |
|---|---|---|
| `= NULL` и `IS NULL` | первое всегда UNKNOWN, строк не будет | только `IS NULL` |
| `<>` и `IS DISTINCT FROM` | `<>` теряет строки с NULL | второе, если NULL нужно учитывать |
| `IN (...)` и `OR` | одно и то же для списка значений | `IN` короче |
| `BETWEEN` и `>= AND <` | BETWEEN включает правую границу | для дат со временем — полуинтервал |
| `LIKE` и `ILIKE` | ILIKE без учёта регистра, только PG | переносимо: `lower(x) LIKE ...` |
| `LIKE` и `=` | `=` без шаблонов и быстрее по индексу | `=`, если шаблон не нужен |
| `LIMIT/OFFSET` и `FETCH FIRST` | одно и то же, FETCH — стандарт и умеет WITH TIES | что принято в проекте |
| `OFFSET` и keyset | OFFSET медленнее на дальних страницах | keyset для лент и API |
| `DISTINCT` и `GROUP BY` | GROUP BY нужен для агрегатов | DISTINCT для списка значений |
| `DISTINCT ON` и `ROW_NUMBER()` | первое короче, только PG | второе переносимо и даёт N строк |
| алиас в `WHERE` и в `ORDER BY` | в WHERE его ещё нет (PG), в ORDER BY уже есть | в WHERE повторить выражение или вынести в подзапрос |

## Проверьте себя (ответы ниже)

1. Сколько строк вернёт `WHERE scholarship <> 3000`, если у половины студентов стипендия NULL?
2. Почему `SELECT ... LIMIT 3` без ORDER BY — ошибка, даже если сейчас результат правильный?
3. Что вернёт `SELECT DISTINCT city, group_id`: уникальные города или уникальные пары?

_Ответы: 1) только строки с известной стипендией, не равной 3000; NULL выпадут. 2) Порядок без сортировки не гарантирован. 3) Пары._
"""),
]

M02 = [
('Типы, приведение и арифметика', r"""
# Типы, приведение и арифметика

## Числа

| Тип PostgreSQL | Что хранит | Когда брать |
|---|---|---|
| `smallint`, `integer`, `bigint` | целые | количества, идентификаторы |
| `numeric(p, s)` | точные десятичные | **деньги**, всё, где важна каждая копейка |
| `real`, `double precision` | приближённые (двоичные) | физика, статистика; не для денег |

`0.1 + 0.2` во float — это `0.30000000000000004`. В numeric — ровно `0.3`.

## Целочисленное деление

В PostgreSQL и SQLite деление целого на целое — целое: `7 / 2 = 3`. Это самая частая ошибка в метриках: «конверсия 0%».

```sql
SELECT 7 / 2           AS "целые",
       7.0 / 2         AS "один операнд дробный",
       CAST(7 AS REAL) / 2 AS "явное приведение",
       7 % 2           AS "остаток";
```

```pg
SELECT 7 / 2, 7::numeric / 2, 7 / 2.0, round(7::numeric / 3, 2);
```

## CAST и ::

| Запись | Где | Пример |
|---|---|---|
| `CAST(x AS тип)` | стандарт, везде | `CAST('42' AS INTEGER)` |
| `x::тип` | только PostgreSQL | `'2025-01-01'::date` |

Приведение строки к числу, которая числом не является: PostgreSQL выдаст ошибку, SQLite молча вернёт 0. Будьте осторожны с «грязными» данными.

## Округление

| Функция | 2.5 | -2.5 | 2.567 |
|---|---|---|---|
| `round(x)` | 3 | -3 | 3 |
| `round(x, 2)` | 2.5 | -2.5 | 2.57 |
| `trunc(x)` (PG) | 2 | -2 | 2 |
| `floor(x)` — вниз | 2 | -3 | 2 |
| `ceil(x)` — вверх | 3 | -2 | 3 |

```sql
SELECT round(2.567, 2), floor(-2.5), ceil(-2.5), round(salary / 1000.0) AS salary_k
FROM teachers LIMIT 3;
```

## Неявные приведения

SQLite сравнивает «как получится»: `'10' = 10` может быть истиной в одном столбце и ложью в другом в зависимости от его типа. PostgreSQL строг: сравнить текст с числом без приведения нельзя. Поэтому храните числа числами, даты датами.
"""),
('CASE: ветвление в выражениях', r"""
# CASE

CASE — это `if … else` внутри выражения. Он возвращает значение, а значит, может стоять везде, где стоит выражение: в SELECT, WHERE, ORDER BY, GROUP BY, внутри агрегатов.

## Две формы

```
-- «поисковая»: любое условие в каждой ветке
CASE WHEN условие1 THEN значение1
     WHEN условие2 THEN значение2
     ELSE значение_иначе END

-- «простая»: сравнение одного выражения на равенство
CASE выражение WHEN v1 THEN r1 WHEN v2 THEN r2 ELSE r END
```

| | Поисковая | Простая |
|---|---|---|
| условия | любые: `>`, `LIKE`, `IS NULL`, AND/OR | только равенство |
| проверка NULL | можно: `WHEN x IS NULL` | нельзя: `WHEN NULL` никогда не сработает |
| когда брать | диапазоны, сложные правила | перевод кодов в названия |

```sql
SELECT full_name, salary,
       CASE WHEN salary >= 150000 THEN 'высокая'
            WHEN salary >= 100000 THEN 'средняя'
            ELSE 'начальная' END AS salary_band,
       CASE dept_id WHEN 2 THEN 'прогр.' WHEN 3 THEN 'БД' ELSE '—' END AS dept_short
FROM teachers;
```

## Правила, которые надо знать

1. **Ветки проверяются по порядку**, срабатывает первая истинная. Поэтому диапазоны пишут от самого строгого: если поставить `>= 100000` первым, до `>= 150000` дело не дойдёт.
2. **Без ELSE** результат для неподошедших строк — NULL.
3. Все ветки должны давать **один тип**. PostgreSQL не даст смешать текст и число.
4. `WHEN x = NULL` не сработает никогда — пишите `WHEN x IS NULL`.

## CASE в разных частях запроса

```sql
-- своя сортировка: сначала Москва, потом остальные по алфавиту
SELECT full_name, city FROM students
ORDER BY CASE WHEN city = 'Москва' THEN 0 ELSE 1 END, city, full_name;
```

```sql
-- группировка по вычисленной категории
SELECT CASE WHEN birth_date < '2004-01-01' THEN 'до 2004' ELSE '2004 и позже' END AS born,
       COUNT(*) AS students
FROM students
GROUP BY born;
```

CASE внутри агрегатов («условная агрегация») — отдельная важная техника, она в модуле 3.
"""),
('COALESCE, NULLIF и компания', r"""
# Функции для работы с NULL

| Функция | Что делает | Пример | Результат |
|---|---|---|---|
| `COALESCE(a, b, c)` | первое не-NULL значение | `COALESCE(NULL, NULL, 5)` | 5 |
| `NULLIF(a, b)` | NULL, если a = b, иначе a | `NULLIF(0, 0)` | NULL |
| `CASE WHEN a IS NULL THEN b ELSE a END` | то же, что COALESCE(a, b) | | |
| `IFNULL(a, b)` | COALESCE на 2 аргумента, SQLite/MySQL | | |
| `greatest(a, b)`, `least(a, b)` | максимум/минимум из списка | `greatest(3, 7)` | 7 |

COALESCE и NULLIF — противоположности: COALESCE **убирает** NULL, NULLIF **создаёт** NULL.

## COALESCE: значение по умолчанию

```sql
SELECT full_name,
       COALESCE(email, 'нет почты')   AS email,
       COALESCE(scholarship, 0)       AS scholarship
FROM students;
```

Цепочка резервных вариантов: `COALESCE(work_phone, mobile_phone, home_phone, 'нет связи')`.

## NULLIF: защита от деления на ноль

`x / 0` в PostgreSQL — ошибка, в SQLite — NULL. `x / NULLIF(y, 0)` даёт NULL вместо ошибки в обеих СУБД, и это обычный приём для метрик:

```sql
SELECT 100 / NULLIF(0, 0)                       AS "деление на 0 → NULL",
       COALESCE(100.0 / NULLIF(0, 0), 0)        AS "и подставить 0";
```

Второе применение — превратить «мусорное» значение в NULL: `NULLIF(trim(email), '')` считает пустую строку отсутствующим значением.

## greatest и least

Не путать с MAX/MIN: `MAX` — агрегат по **строкам**, `greatest` — максимум из **столбцов одной строки**.

```sql
SELECT full_name, scholarship, greatest(COALESCE(scholarship, 0), 4000) AS "не меньше 4000"
FROM students;
```

В PostgreSQL `greatest` игнорирует NULL, в SQLite встроенный `max(a, b)` возвращает NULL, если среди аргументов есть NULL. В тренажёре `greatest/least` добавлены и ведут себя как в PostgreSQL.
"""),
('Строковые функции', r"""
# Строки

## Склейка: || против concat

```sql
SELECT 'Студент: ' || full_name || ', ' || email           AS "через ||",
       concat('Студент: ', full_name, ', ', email)         AS "через concat"
FROM students WHERE email IS NULL;
```

| | `a || b` | `concat(a, b)` | `concat_ws(', ', a, b)` |
|---|---|---|---|
| NULL внутри | весь результат NULL | NULL пропускается | NULL пропускается, разделитель тоже |

## Справочник

| Задача | PostgreSQL | SQLite |
|---|---|---|
| длина | `length(s)` | `length(s)` |
| подстрока | `substr(s, from, len)`, `left(s, n)`, `right(s, n)` | `substr(s, from, len)`; с конца: `substr(s, -3)` |
| позиция подстроки | `position('@' IN s)`, `strpos(s, '@')` | `instr(s, '@')` |
| регистр | `upper`, `lower`, `initcap` | `upper`, `lower` (+ `initcap` в тренажёре) |
| обрезка пробелов | `trim`, `ltrim`, `rtrim`, `btrim` | `trim`, `ltrim`, `rtrim` |
| замена | `replace(s, from, to)` | `replace` |
| часть по разделителю | `split_part(s, '@', 2)` | `split_part` (добавлена) |
| повтор, дополнение | `repeat`, `lpad`, `rpad` | `printf('%05d', n)` |
| регулярки | `s ~ 'шаблон'`, `regexp_replace`, `substring(s from 'шаблон')` | `s REGEXP 'шаблон'`, `regexp_replace` (добавлены) |

```sql
SELECT email,
       substr(email, 1, instr(email, '@') - 1) AS login,
       split_part(email, '@', 2)              AS domain,
       upper(substr(full_name, 1, 1))        AS first_letter,
       length(full_name)                     AS name_len
FROM students
WHERE email IS NOT NULL;
```

## Поиск по тексту: LIKE, ILIKE, регулярки

| Способ | Пример | Плюсы | Минусы |
|---|---|---|---|
| `=` | `city = 'Тула'` | быстрый, индекс | только точное совпадение |
| `LIKE` | `email LIKE '%@uni.ru'` | просто | только `%` и `_`; ведущий `%` не использует обычный индекс |
| `ILIKE` (PG) | `full_name ILIKE '%ова%'` | без учёта регистра | только PostgreSQL |
| регулярные выражения | `full_name ~ '^[А-Я]\w+ова '` | очень гибко | медленнее, сложнее читать |
| полнотекстовый поиск (PG) | `to_tsvector(...) @@ to_tsquery(...)` | морфология, ранжирование | нужен отдельный индекс |

```sql
SELECT full_name FROM students WHERE full_name REGEXP 'ова? ';   -- «ов » или «ова »
```

## Чистка данных

Классика: email с пробелами и разным регистром. Сравнивать нужно нормализованные значения: `lower(trim(email))`. Пустые строки превращать в NULL: `NULLIF(trim(x), '')`.
"""),
('Шпаргалка: выражения', r"""
# Шпаргалка: похожие функции и выражения

| Похожие | Разница |
|---|---|
| `7/2` и `7.0/2` | 3 и 3.5: деление целых — целое |
| `CAST(x AS INT)` и `x::int` | одно и то же, `::` только в PostgreSQL |
| `round`, `trunc`, `floor`, `ceil` | к ближайшему, отбросить дробь, вниз, вверх (для отрицательных trunc ≠ floor) |
| `numeric` и `double precision` | точно и приближённо; деньги — только numeric |
| простой `CASE x WHEN` и поисковый `CASE WHEN` | простой умеет только равенство и не ловит NULL |
| CASE без ELSE и с ELSE | без ELSE — NULL для остальных |
| `COALESCE` и `NULLIF` | убрать NULL и получить NULL |
| `COALESCE` и `IFNULL` | IFNULL — 2 аргумента и не стандарт |
| `greatest` и `MAX` | по столбцам одной строки и по строкам группы |
| `||` и `concat` | `||` с NULL даёт NULL, concat пропускает NULL |
| `LIKE`, `ILIKE`, `~` | шаблон, шаблон без регистра (PG), регулярка (PG) |
| `position`, `strpos`, `instr` | одно и то же в разных СУБД |
| `substr(s, -3)` и `right(s, 3)` | последние 3 символа в SQLite и PG |

## Проверьте себя

1. Что вернёт `CASE WHEN 5 > 3 THEN 'a' WHEN 5 > 1 THEN 'b' END`?
2. Чему равно `'id-' || NULL` и `concat('id-', NULL)`?
3. Как посчитать долю `a / b` в процентах с двумя знаками так, чтобы не было ни деления целых, ни деления на ноль?

_Ответы: 1) 'a' — первая истинная ветка. 2) NULL и 'id-'. 3) round(100.0 * a / NULLIF(b, 0), 2)._
"""),
]

M03 = [
('Агрегатные функции', r"""
# Агрегатные функции

Агрегат сворачивает много строк в одно значение.

| Функция | Что считает | NULL |
|---|---|---|
| `COUNT(*)` | число строк | считает все строки |
| `COUNT(x)` | число строк, где x не NULL | пропускает |
| `COUNT(DISTINCT x)` | число разных не-NULL значений | пропускает |
| `SUM(x)` | сумма | пропускает; по пустому набору — **NULL**, не 0 |
| `AVG(x)` | среднее по не-NULL | пропускает |
| `MIN(x)`, `MAX(x)` | минимум, максимум (числа, строки, даты) | пропускает |
| `string_agg(x, ', ')` | склейка строк | пропускает |
| `median(x)`, `percentile_cont(p)` | медиана, перцентиль | пропускает |
| `stddev`, `variance`, `corr` | разброс, корреляция | пропускает |
| `bool_and`, `bool_or` | «у всех», «хотя бы у одного» | пропускает |

## Три COUNT — три разных числа

```sql
SELECT COUNT(*)                 AS "строк",
       COUNT(email)             AS "с email",
       COUNT(DISTINCT city)     AS "разных городов",
       COUNT(scholarship)       AS "со стипендией"
FROM students;
```

## AVG и NULL

`AVG` делит на число **известных** значений. Если NULL на самом деле означает 0, результат получится завышенным:

```sql
SELECT AVG(scholarship)               AS "среди получающих",
       AVG(COALESCE(scholarship, 0))  AS "среди всех",
       SUM(scholarship) * 1.0 / COUNT(*) AS "то же самое"
FROM students;
```

Какое из чисел правильное — зависит от вопроса. «Средняя стипендия у тех, кто её получает» — первое. «Сколько в среднем платим на одного студента» — второе. Задавайте себе этот вопрос каждый раз.

## Агрегаты по пустому набору

```sql
SELECT COUNT(*), SUM(amount), AVG(amount), MAX(amount)
FROM dorm_payments WHERE amount > 100000;
```

`COUNT` вернёт 0, остальные — NULL. Если нужна сумма 0, пишите `COALESCE(SUM(...), 0)`.

## Медиана против среднего

Среднее чувствительно к выбросам, медиана — нет. Для зарплат, чеков, времени — смотрите на обе:

```sql
SELECT AVG(salary), median(salary) FROM teachers;
```

```pg
SELECT AVG(salary),
       percentile_cont(0.5) WITHIN GROUP (ORDER BY salary) AS median,
       percentile_disc(0.5) WITHIN GROUP (ORDER BY salary) AS median_existing
FROM teachers;
```

`percentile_cont` интерполирует между соседними значениями, `percentile_disc` возвращает реально существующее значение. В тренажёре: `percentile_cont(x, 0.5)`.
"""),
('GROUP BY', r"""
# GROUP BY

GROUP BY раскладывает строки по «корзинам» с одинаковым значением ключа, и агрегаты считаются отдельно для каждой корзины. На выходе — **одна строка на группу**.

```sql
SELECT city, COUNT(*) AS students, MIN(birth_date) AS oldest_born
FROM students
GROUP BY city
ORDER BY students DESC, city;
```

## Главное правило

Каждый столбец в SELECT должен быть **либо в GROUP BY, либо внутри агрегата**. Иначе непонятно, какое из многих значений группы показать.

```bad
SELECT city, full_name, COUNT(*)   -- какое имя из трёх москвичей?
FROM students GROUP BY city;
```

PostgreSQL на этот запрос выдаст ошибку. SQLite молча возьмёт значение из случайной строки группы, и это одна из самых коварных ошибок: результат выглядит правдоподобно. Исключение в PostgreSQL: если группируете по первичному ключу таблицы, остальные её столбцы можно выводить без агрегата (они однозначно определены).

## Группировка по нескольким столбцам и по выражению

```sql
SELECT group_id, city, COUNT(*) AS n
FROM students
GROUP BY group_id, city
ORDER BY group_id, city;
```

```sql
SELECT substr(birth_date, 1, 4) AS birth_year, COUNT(*) AS n
FROM students
GROUP BY substr(birth_date, 1, 4)    -- в PG и SQLite можно и GROUP BY birth_year
ORDER BY birth_year;
```

## NULL как группа

Все строки с NULL в ключе попадают в **одну** группу:

```sql
SELECT group_id, COUNT(*) FROM students GROUP BY group_id;
```

## GROUP BY без агрегатов и агрегаты без GROUP BY

- `SELECT city FROM students GROUP BY city` — то же, что `SELECT DISTINCT city`.
- `SELECT COUNT(*) FROM students` — агрегат без GROUP BY: вся таблица — одна группа, одна строка результата. Даже если таблица пустая, строка будет (с 0 и NULL).
- `SELECT COUNT(*) FROM students GROUP BY city` по пустой таблице вернёт **ноль строк**: нет групп — нет строк.
"""),
('WHERE против HAVING', r"""
# WHERE против HAVING

Оба фильтруют, но в разные моменты и разные вещи.

| | WHERE | HAVING |
|---|---|---|
| когда работает | **до** группировки | **после** группировки |
| что фильтрует | отдельные строки | целые группы |
| можно ли агрегаты | нет | да: `HAVING COUNT(*) > 2` |
| можно ли обычные столбцы | да | только ключи группировки |
| влияние на агрегаты | меняет то, что попадёт в COUNT/SUM | не меняет, только отбрасывает группы |
| производительность | отсекает строки рано, может использовать индекс | работает по уже посчитанным группам |

## Один вопрос — два разных ответа

```sql
-- Курсы, на которых минимум две ПЯТЁРКИ: сначала отбираем строки, потом группы
SELECT course_id, COUNT(*) AS fives
FROM enrollments
WHERE grade = 5
GROUP BY course_id
HAVING COUNT(*) >= 2;
```

```sql
-- Курсы, где больше двух студентов, и сколько там пятёрок
SELECT course_id, COUNT(*) AS students,
       SUM(CASE WHEN grade = 5 THEN 1 ELSE 0 END) AS fives
FROM enrollments
GROUP BY course_id
HAVING COUNT(*) > 2;
```

Перенос условия `grade = 5` из WHERE в HAVING невозможен (в группе много оценок), а `COUNT(*) > 2` из HAVING в WHERE — тоже (в отдельной строке нет «количества»).

## Условие, которое можно писать в обоих местах

Условие на ключ группировки допустимо и в WHERE, и в HAVING, результат одинаковый. Но в WHERE оно лучше: строки отсекаются до группировки.

```sql
SELECT city, COUNT(*) FROM students WHERE city <> 'Москва' GROUP BY city;   -- так
SELECT city, COUNT(*) FROM students GROUP BY city HAVING city <> 'Москва';  -- работает, но хуже
```

## Порядок частей

`WHERE → GROUP BY → HAVING → SELECT → ORDER BY`. Поэтому в HAVING нельзя полагаться на алиас из SELECT в PostgreSQL (`HAVING students > 2` — ошибка, нужно `HAVING COUNT(*) > 2`). SQLite такое разрешает.

## HAVING без GROUP BY

Допустим: вся таблица считается одной группой. `SELECT COUNT(*) FROM students HAVING COUNT(*) > 100` вернёт либо одну строку, либо ни одной.
"""),
('Условная агрегация и пивот', r"""
# Условная агрегация

Нужно посчитать несколько разных вещей за один проход по таблице: сколько всего, сколько пятёрок, сколько не сдали. Для этого условие ставят **внутрь** агрегата.

## Три способа записать одно и то же

```sql
SELECT course_id,
       COUNT(*)                                    AS всего,
       COUNT(*) FILTER (WHERE grade = 5)           AS "пятёрки: FILTER",
       SUM(CASE WHEN grade = 5 THEN 1 ELSE 0 END)  AS "пятёрки: SUM(CASE)",
       COUNT(CASE WHEN grade = 5 THEN 1 END)       AS "пятёрки: COUNT(CASE)",
       AVG(grade) FILTER (WHERE grade >= 3)        AS "средний среди сдавших"
FROM enrollments
GROUP BY course_id;
```

| Запись | Где работает | Замечание |
|---|---|---|
| `AGG(x) FILTER (WHERE усл)` | PostgreSQL, SQLite 3.30+ | самая читаемая, стандарт SQL |
| `SUM(CASE WHEN усл THEN 1 ELSE 0 END)` | везде | для пустой группы даст 0 |
| `COUNT(CASE WHEN усл THEN 1 END)` | везде | без ELSE: NULL не считается |
| `AVG(CASE WHEN усл THEN x END)` | везде | среднее по подмножеству |
| `SUM(усл::int)` (PG), `SUM(усл)` (SQLite) | | коротко, но непереносимо |

Ловушка: `COUNT(CASE WHEN усл THEN 1 ELSE 0 END)` посчитает **все** строки — 0 тоже не NULL.

## Доля через условную агрегацию

```sql
SELECT course_id,
       ROUND(100.0 * COUNT(*) FILTER (WHERE grade >= 4) / COUNT(*), 1) AS pct_good
FROM enrollments
GROUP BY course_id;
```

`AVG(CASE WHEN усл THEN 1.0 ELSE 0 END)` — то же самое одной функцией: среднее от нулей и единиц равно доле единиц.

## Пивот: строки в столбцы

Таблица «курс × оценка» в длинном виде — по строке на пару. Пивот разворачивает значения в столбцы:

```sql
SELECT c.title,
       COUNT(*) FILTER (WHERE e.grade = 5) AS "5",
       COUNT(*) FILTER (WHERE e.grade = 4) AS "4",
       COUNT(*) FILTER (WHERE e.grade = 3) AS "3",
       COUNT(*) FILTER (WHERE e.grade = 2) AS "2",
       COUNT(*) FILTER (WHERE e.grade IS NULL) AS "не сдавали"
FROM courses c JOIN enrollments e ON e.course_id = c.course_id
GROUP BY c.course_id, c.title;
```

Столбцы пивота перечисляются вручную: SQL не умеет создавать столбцы по данным. В PostgreSQL есть `crosstab` из расширения tablefunc, но на практике чаще пишут условную агрегацию.

## WHERE или FILTER?

`WHERE grade = 5` выкинет строки до группировки — пропадут и курсы без пятёрок, и общий COUNT посчитает только пятёрки. `FILTER` влияет только на свой агрегат. Нужны разные условия в одной строке — только FILTER/CASE.
"""),
('ROLLUP, CUBE и итоги', r"""
# Подытоги: ROLLUP, CUBE, GROUPING SETS

Отчёт часто требует и детали, и итоги: по городам, по группам внутри городов и общий итог.

```pg
SELECT city, group_id, COUNT(*)
FROM students
GROUP BY ROLLUP (city, group_id)
ORDER BY city, group_id;
```

| Конструкция | Какие группировки строит |
|---|---|
| `GROUP BY a, b` | (a, b) |
| `ROLLUP (a, b)` | (a, b), (a), () — иерархия: детали → подытог → итог |
| `CUBE (a, b)` | (a, b), (a), (b), () — все сочетания |
| `GROUPING SETS ((a), (b), ())` | ровно перечисленные |

В строках подытогов «свёрнутый» столбец равен NULL. Чтобы отличить такой NULL от настоящего, есть `GROUPING(col)`: 1 — столбец свёрнут.

```pg
SELECT CASE WHEN GROUPING(city) = 1 THEN 'ИТОГО' ELSE city END AS city,
       COUNT(*)
FROM students
GROUP BY ROLLUP (city);
```

## В SQLite: UNION ALL

ROLLUP — это просто несколько GROUP BY, склеенных вместе:

```sql
SELECT city, students FROM (
  SELECT city, COUNT(*) AS students, 0 AS is_total FROM students GROUP BY city
  UNION ALL
  SELECT 'ИТОГО', COUNT(*), 1 FROM students
) t
ORDER BY is_total, city;
```

Итог можно получить и оконной функцией, не теряя детальных строк: `SUM(COUNT(*)) OVER ()` (модуль 7).
"""),
('Ошибки и шпаргалка агрегатов', r"""
# Типичные ошибки с агрегатами

1. **Столбец вне GROUP BY.** PostgreSQL запретит, SQLite возьмёт случайное значение. Всегда проверяйте: всё в SELECT — в GROUP BY или в агрегате.
2. **COUNT(*) там, где нужен COUNT(x).** После LEFT JOIN `COUNT(*)` считает и «пустую» строку (модуль 4).
3. **AVG с NULL.** Решите, NULL — это «не участвует» или «ноль».
4. **SUM по пустому набору = NULL.** В отчётах оборачивайте в COALESCE.
5. **Среднее средних.** Средняя оценка по институту ≠ среднее из средних по курсам, если на курсах разное число студентов:

```sql
WITH by_course AS (
  SELECT course_id, AVG(grade) AS avg_grade, COUNT(grade) AS n
  FROM enrollments GROUP BY course_id
)
SELECT (SELECT AVG(grade) FROM enrollments)       AS "по всем оценкам",
       AVG(avg_grade)                              AS "среднее средних",
       SUM(avg_grade * n) / SUM(n)                 AS "взвешенное = по всем оценкам"
FROM by_course;
```

6. **Агрегат в WHERE.** Нельзя: используйте HAVING или подзапрос.
7. **Деление целых** в долях: `100.0 *` или `CAST`.

## Шпаргалка

| Похожие | Разница |
|---|---|
| `COUNT(*)`, `COUNT(x)`, `COUNT(DISTINCT x)` | строки; не-NULL значения; разные не-NULL значения |
| `AVG(x)` и `AVG(COALESCE(x, 0))` | среди известных и среди всех |
| `AVG` и `median` | среднее чувствительно к выбросам |
| `percentile_cont` и `percentile_disc` | интерполяция и существующее значение |
| `WHERE` и `HAVING` | строки до группировки и группы после |
| `FILTER` и `WHERE` | условие одного агрегата и условие всего запроса |
| `FILTER` и `SUM(CASE)` | одно и то же; FILTER читаемее |
| `GROUP BY` и `DISTINCT` | агрегаты и просто уникальные строки |
| `ROLLUP` и `CUBE` | иерархические подытоги и все сочетания |
| `GROUP BY` и окно `OVER (PARTITION BY)` | схлопывает строки и сохраняет их (модуль 7) |
"""),
]

M04 = [
('Как работает JOIN', r"""
# Как работает JOIN

Логически любое соединение — это два шага:
1. взять **все пары** строк левой и правой таблицы (декартово произведение);
2. оставить пары, для которых условие `ON` истинно.

Для внешних соединений есть третий шаг: вернуть строки, которые не нашли пары, дополнив их NULL.

На практике СУБД не строит все пары, а использует индексы и хеш-таблицы (модуль 10), но результат всегда такой, как будто шаги выполнялись буквально.

## Связи между таблицами

| Связь | Пример в uni | Что даёт JOIN |
|---|---|---|
| многие к одному | студент → группа | строка студента получает данные группы, число строк не растёт |
| один ко многим | группа → студенты | строка группы повторяется для каждого студента |
| многие ко многим | студенты ↔ курсы через enrollments | нужны две связи через таблицу-мост |
| иерархия | преподаватель → наставник (mentor_id) | соединение таблицы с самой собой |

```sql
SELECT s.full_name, g.code AS group_code
FROM students s
JOIN study_groups g ON g.group_id = s.group_id;
```

## Алиасы

`students s` — короткое имя таблицы. Когда в запросе больше одной таблицы, **всегда** пишите столбцы с префиксом (`s.full_name`): так ясно, откуда столбец, и запрос не сломается, если в другой таблице появится столбец с тем же именем.

## Многие ко многим

```sql
SELECT s.full_name, c.title, e.grade
FROM students s
JOIN enrollments e ON e.student_id = s.student_id
JOIN courses c     ON c.course_id  = e.course_id
ORDER BY s.full_name, c.title;
```

Каждый следующий JOIN присоединяется к **результату** предыдущих. Порядок INNER JOIN на результат не влияет, порядок внешних — влияет.
"""),
('INNER, LEFT, RIGHT, FULL: в чём разница', r"""
# INNER, LEFT, RIGHT, FULL

Возьмём преподавателей и кафедры. Есть преподаватель без кафедры (Гусев, dept_id NULL) и кафедра без преподавателей (маркетинг). Это ровно тот случай, где виды JOIN расходятся.

| Вид | Что остаётся | Гусев без кафедры | Кафедра маркетинга |
|---|---|---|---|
| `INNER JOIN` | только пары, где условие истинно | пропадёт | пропадёт |
| `LEFT JOIN` | все строки **левой** + пары | останется, кафедра NULL | пропадёт |
| `RIGHT JOIN` | все строки **правой** + пары | пропадёт | останется, преподаватель NULL |
| `FULL JOIN` | все строки обеих | останется | останется |

```sql
SELECT t.full_name, d.name AS dept
FROM teachers t INNER JOIN departments d ON d.dept_id = t.dept_id
ORDER BY t.teacher_id;
```

```sql
SELECT t.full_name, d.name AS dept
FROM teachers t LEFT JOIN departments d ON d.dept_id = t.dept_id
ORDER BY t.teacher_id;
```

```sql
SELECT t.full_name, d.name AS dept
FROM teachers t RIGHT JOIN departments d ON d.dept_id = t.dept_id
ORDER BY d.dept_id;
```

```sql
SELECT t.full_name, d.name AS dept
FROM teachers t FULL JOIN departments d ON d.dept_id = t.dept_id;
```

Посчитайте строки: INNER — 7, LEFT — 8 (+Гусев), RIGHT — сколько пар плюс пустые кафедры (институты и маркетинг), FULL — всё вместе.

## Важные детали

- `JOIN` = `INNER JOIN`, `LEFT JOIN` = `LEFT OUTER JOIN`. Слова INNER и OUTER необязательны.
- `A RIGHT JOIN B` = `B LEFT JOIN A`. На практике RIGHT почти не пишут: читать запрос «слева направо» проще, когда главная таблица стоит первой.
- NULL в ключе **никогда** не соединяется: `NULL = NULL` — UNKNOWN. Гусев не найдёт пару даже с кафедрой, у которой dept_id NULL.
- Как отличить «нет пары» от «пара есть, но в столбце NULL»? Проверяйте столбец, который у правой таблицы не может быть NULL — её первичный ключ: `d.dept_id IS NULL`.

## Как выбирать

| Вопрос | Соединение |
|---|---|
| «покажи заказы с именами клиентов» — пары нужны обязательно | INNER |
| «все студенты и их оценки, включая тех, у кого их нет» | LEFT от главной таблицы |
| «сравнить два списка и найти расхождения в обе стороны» | FULL |
| «все сочетания» (календарь × товары, размеры × цвета) | CROSS |
"""),
('ON против WHERE во внешних соединениях', r"""
# ON против WHERE во внешних соединениях

Для INNER JOIN неважно, где стоит условие — в ON или в WHERE. Для LEFT JOIN это **два разных запроса**.

- Условие в **ON** решает, какие строки правой таблицы считаются парой. Строки левой таблицы остаются всегда.
- Условие в **WHERE** выполняется после соединения и выбрасывает **строки результата** — включая левые строки без пары, у которых справа NULL.

Вопрос: «все курсы и число **пятёрок** на каждом, курсы без пятёрок — с нулём».

```bad
SELECT c.title, COUNT(e.student_id) AS fives
FROM courses c
LEFT JOIN enrollments e ON e.course_id = c.course_id
WHERE e.grade = 5                        -- у курсов без пятёрок e.grade NULL → строка выброшена
GROUP BY c.course_id, c.title;
```

```sql
SELECT c.title, COUNT(e.student_id) AS fives
FROM courses c
LEFT JOIN enrollments e ON e.course_id = c.course_id AND e.grade = 5
GROUP BY c.course_id, c.title;
```

В первом запросе пропали «Философия» и «Машинное обучение» — LEFT JOIN тихо превратился в INNER. Во втором все курсы на месте.

## Правило

| Условие на … | при LEFT JOIN ставить в |
|---|---|
| правую (необязательную) таблицу | **ON** |
| левую (главную) таблицу | **WHERE** |
| проверку «пары нет» (`right.id IS NULL`) | WHERE — это и есть anti-join |

Условие на левую таблицу в ON ведёт себя неожиданно: строки левой таблицы всё равно останутся, просто без пары.

```sql
-- условие на левую таблицу в ON: московские студенты НЕ отфильтровались,
-- у остальных просто не нашлось групп
SELECT s.full_name, s.city, g.code
FROM students s
LEFT JOIN study_groups g ON g.group_id = s.group_id AND s.city = 'Москва';
```

## Цепочки LEFT JOIN

Если после LEFT JOIN идёт обычный JOIN по правой таблице, строки без пары снова пропадут:

```bad
FROM courses c
LEFT JOIN enrollments e ON e.course_id = c.course_id
JOIN students s ON s.student_id = e.student_id   -- e.student_id NULL → строка курса исчезла
```

Дальше по цепочке тоже нужен LEFT JOIN (или соединение в скобках).
"""),
('ON, USING, NATURAL и CROSS', r"""
# Способы записать условие соединения

| Запись | Пример | Плюсы | Минусы |
|---|---|---|---|
| `ON` | `ON e.course_id = c.course_id` | любые условия, явно | длиннее |
| `USING (col)` | `JOIN enrollments USING (course_id)` | коротко; столбец в результате один | столбцы обязаны называться одинаково |
| `NATURAL JOIN` | `students NATURAL JOIN enrollments` | очень коротко | соединяет по **всем** одноимённым столбцам; новый столбец ломает запрос |
| через запятую + WHERE | `FROM a, b WHERE a.id = b.a_id` | старый стиль | легко забыть условие и получить CROSS JOIN |

```sql
SELECT student_id, full_name, course_id, grade
FROM students JOIN enrollments USING (student_id)
ORDER BY student_id LIMIT 6;
```

С USING столбец `student_id` в результате один и пишется без префикса.

```bad
SELECT * FROM courses NATURAL JOIN teachers;
-- общие столбцы: teacher_id ... и больше никаких? А если завтра в обе таблицы
-- добавят столбец created_at — условие молча станет teacher_id AND created_at.
```

NATURAL JOIN в рабочем коде не используйте.

## CROSS JOIN

Все сочетания без условия. Строк получится `|A| × |B|`.

```sql
SELECT g.code, c.title
FROM study_groups g CROSS JOIN courses c
WHERE c.credits >= 5
ORDER BY g.code, c.title;
```

Зачем нужен:
- сетка «все группы × все курсы», к которой потом LEFT JOIN-ом цепляют факты — так в отчёте появляются нули;
- «календарь × категории» для отчётов без пропусков;
- сравнение «каждого с каждым».

Случайный CROSS JOIN — классическая ошибка старого стиля: `FROM a, b` без условия в WHERE. На маленьких таблицах незаметно, на больших — миллиарды строк.

## Соединение не по равенству

ON может содержать любое условие: диапазоны, неравенства, функции.

```sql
-- кто из преподавателей пришёл раньше своего наставника? (проверка данных)
-- и шкала: попадание зарплаты в диапазон
WITH bands(name, lo, hi) AS (VALUES ('начальная', 0, 99999), ('средняя', 100000, 149999), ('высокая', 150000, 10000000))
SELECT t.full_name, t.salary, b.name AS band
FROM teachers t JOIN bands b ON t.salary BETWEEN b.lo AND b.hi
ORDER BY t.salary DESC;
```
"""),
('Self-join и иерархии', r"""
# Соединение таблицы с самой собой

Таблицу можно присоединить к самой себе под разными алиасами. Типичные случаи:

- ссылка на «родителя» в той же таблице: преподаватель → наставник, кафедра → институт;
- сравнение строк между собой: пары студентов из одного города, повторяющиеся значения.

```sql
SELECT t.full_name AS teacher, m.full_name AS mentor
FROM teachers t
LEFT JOIN teachers m ON m.teacher_id = t.mentor_id
ORDER BY t.teacher_id;
```

LEFT, потому что у некоторых наставника нет. С INNER они бы пропали.

## Иерархия на фиксированную глубину

Каждый уровень вверх — ещё одно соединение:

```sql
SELECT d.name AS unit, p.name AS parent, gp.name AS grandparent
FROM departments d
LEFT JOIN departments p  ON p.dept_id  = d.parent_id
LEFT JOIN departments gp ON gp.dept_id = p.parent_id;
```

Если глубина неизвестна заранее, нужен рекурсивный CTE (модуль 6).

## Пары «каждый с каждым»

```sql
SELECT a.full_name, b.full_name, a.city
FROM students a
JOIN students b ON a.city = b.city AND a.student_id < b.student_id
ORDER BY a.city;
```

Условие `a.student_id < b.student_id` убирает пары «сам с собой» и зеркальные повторы (А–Б и Б–А). С `<>` каждая пара была бы дважды.

## Сравнение со «соседом»

Self-join по условию «предыдущая запись» (`b.paid_on < a.paid_on` + поиск максимума) работает, но громоздок и медленный. Для «предыдущей/следующей строки» есть оконные функции `LAG/LEAD` (модуль 7) — это современная замена.
"""),
('Размножение строк и агрегаты после JOIN', r"""
# Размножение строк (fan-out)

JOIN по связи «один ко многим» повторяет строку «одного» для каждой строки «многих». Если после этого сложить столбец «одного», сумма раздуется.

```sql
-- зарплатный фонд кафедр — НЕПРАВИЛЬНО: соединили ещё и с курсами
SELECT d.name, SUM(t.salary) AS payroll
FROM departments d
JOIN teachers t ON t.dept_id = d.dept_id
LEFT JOIN courses c ON c.teacher_id = t.teacher_id
GROUP BY d.dept_id, d.name;
```

Если у преподавателя два курса, его зарплата посчитается дважды. Если ноль курсов — один раз (из-за LEFT). Цифра выглядит правдоподобно, и это хуже, чем ошибка.

## Три лечения

1. **Агрегировать до соединения.** Каждая сторона сначала схлопывается до нужного уровня, потом соединяются уже итоги «один к одному»:

```sql
WITH payroll AS (
  SELECT dept_id, SUM(salary) AS payroll FROM teachers GROUP BY dept_id
), load AS (
  SELECT t.dept_id, COUNT(*) AS courses
  FROM courses c JOIN teachers t ON t.teacher_id = c.teacher_id
  GROUP BY t.dept_id
)
SELECT d.name, p.payroll, COALESCE(l.courses, 0) AS courses
FROM departments d
LEFT JOIN payroll p ON p.dept_id = d.dept_id
LEFT JOIN load l    ON l.dept_id = d.dept_id
ORDER BY d.dept_id;
```

2. **COUNT(DISTINCT ...)** — для подсчёта уникальных объектов после размножения. Для сумм не работает: `SUM(DISTINCT salary)` склеит разных людей с одинаковой зарплатой.
3. **EXISTS вместо JOIN**, если правая таблица нужна только для проверки «есть ли» (модуль 5).

## COUNT(*) после LEFT JOIN

Строка без пары всё равно строка. `COUNT(*)` посчитает её как 1:

```sql
SELECT c.title,
       COUNT(*)            AS "COUNT(*) — врёт",
       COUNT(e.student_id) AS "COUNT(e.student_id) — честно"
FROM courses c
LEFT JOIN enrollments e ON e.course_id = c.course_id
GROUP BY c.course_id, c.title;
```

У «Философии» записей нет, но `COUNT(*)` показывает 1. Считайте столбец правой таблицы, который не бывает NULL у настоящих пар (обычно ключ).

## Как заметить размножение

Сравните число строк до и после JOIN: `SELECT COUNT(*), COUNT(DISTINCT t.teacher_id) FROM ...`. Если строк больше, чем уникальных ключей главной таблицы, — строки размножились.
"""),
('UNION, INTERSECT, EXCEPT — и чем они не JOIN', r"""
# Операции над множествами

JOIN склеивает таблицы **по горизонтали**: столбцы одной строки дополняются столбцами другой. Операции над множествами склеивают **по вертикали**: строки одного запроса добавляются к строкам другого.

| Операция | Результат | Дубликаты |
|---|---|---|
| `A UNION B` | строки из A или B | убираются |
| `A UNION ALL B` | все строки A, потом все строки B | остаются |
| `A INTERSECT B` | строки, которые есть и в A, и в B | убираются |
| `A EXCEPT B` | строки A, которых нет в B | убираются |

Требования: одинаковое число столбцов, совместимые типы. Имена столбцов берутся из первого запроса. `ORDER BY` пишется один раз, в конце.

## UNION против UNION ALL

```sql
SELECT city FROM students WHERE scholarship IS NOT NULL
UNION
SELECT city FROM students WHERE group_id = 1;
```

```sql
SELECT city FROM students WHERE scholarship IS NOT NULL
UNION ALL
SELECT city FROM students WHERE group_id = 1;
```

`UNION` должен найти и удалить повторы — это сортировка или хеширование всего результата. `UNION ALL` просто дописывает строки и всегда быстрее. Правило: **пишите UNION ALL, если не нужно специально убирать дубли** — например, когда склеиваете заведомо непересекающиеся части или считаете события (там повторы — это данные).

## INTERSECT и EXCEPT

```sql
-- email-ы, которые есть и у студентов, и в клубе
SELECT email FROM students
INTERSECT
SELECT email FROM club_members;
```

```sql
-- студенты, которые НЕ в клубе
SELECT email FROM students WHERE email IS NOT NULL
EXCEPT
SELECT email FROM club_members;
```

Особенность: операции над множествами считают NULL равными друг другу (как DISTINCT), в отличие от `=` в JOIN и `IN`.

## JOIN или UNION?

| Задача | Инструмент |
|---|---|
| к каждому студенту добавить название его группы | JOIN |
| один список из студентов и преподавателей | UNION ALL |
| найти, какие email есть и там, и там | INTERSECT или semi-join (EXISTS) |
| найти, каких email нет во втором списке | EXCEPT или anti-join (NOT EXISTS) |
| сравнить два списка и показать расхождения в обе стороны | FULL JOIN … WHERE одна сторона IS NULL |

```sql
-- общий справочник людей: по вертикали
SELECT 'студент' AS role, full_name FROM students
UNION ALL
SELECT 'преподаватель', full_name FROM teachers
ORDER BY role, full_name;
```

EXCEPT и INTERSECT сравнивают **целые строки**. Если нужно сравнить по ключу, но вывести другие столбцы, используйте EXISTS/NOT EXISTS (модуль 5).
"""),
('LATERAL и шпаргалка JOIN', r"""
# LATERAL (PostgreSQL)

Обычный подзапрос в FROM не видит соседние таблицы. `LATERAL` разрешает подзапросу ссылаться на строку слева — он выполняется «для каждой строки». Типичная задача: топ-N связанных строк для каждой строки.

```pg
-- два последних экзамена каждого студента
SELECT s.full_name, last2.title, last2.exam_date
FROM students s
CROSS JOIN LATERAL (
    SELECT c.title, e.exam_date
    FROM enrollments e JOIN courses c USING (course_id)
    WHERE e.student_id = s.student_id AND e.exam_date IS NOT NULL
    ORDER BY e.exam_date DESC
    LIMIT 2
) AS last2;
-- LEFT JOIN LATERAL (...) ON true — чтобы оставить студентов без экзаменов
```

В SQLite LATERAL нет; ту же задачу решают оконной функцией `ROW_NUMBER()` (модуль 7). При наличии индекса LATERAL с LIMIT бывает быстрее окна на больших таблицах: он читает только N строк на каждую внешнюю.

# Шпаргалка JOIN

| Похожие | Разница |
|---|---|
| `INNER` и `LEFT` | LEFT сохраняет строки левой таблицы без пары |
| `LEFT` и `RIGHT` | зеркальны; пишите LEFT, главная таблица первой |
| `LEFT` и `FULL` | FULL сохраняет непарные строки обеих сторон |
| `CROSS JOIN` и `JOIN ... ON true` | одно и то же |
| `FROM a, b WHERE ...` и `JOIN ... ON` | одно и то же для INNER; JOIN нагляднее и не забудешь условие |
| условие в `ON` и в `WHERE` | для LEFT: ON отбирает пары, WHERE режет результат |
| `ON`, `USING`, `NATURAL` | явно; коротко при одинаковых именах; опасно |
| `JOIN` и `UNION` | по горизонтали и по вертикали |
| `UNION` и `UNION ALL` | без дублей (дороже) и все строки |
| `EXCEPT` и `NOT EXISTS` | целые строки и проверка по ключу |
| `COUNT(*)` и `COUNT(right.id)` после LEFT | второе не считает пустые пары |
| JOIN + SUM и агрегат до JOIN | первое раздувает суммы при один-ко-многим |
| self-join «предыдущая строка» и `LAG` | LAG проще и быстрее |
| `LATERAL` и `ROW_NUMBER()` | топ-N на строку; LATERAL только в PG |
"""),
]

M05 = [
('Виды подзапросов', r"""
# Подзапросы

Подзапрос — SELECT внутри другого запроса. Классифицируют по двум признакам: **что возвращает** и **зависит ли от внешнего запроса**.

## По результату

| Вид | Возвращает | Где стоит | Пример |
|---|---|---|---|
| скалярный | одно значение (1 строка × 1 столбец) | почти везде, где значение | `salary > (SELECT AVG(salary) FROM teachers)` |
| столбец | много строк × 1 столбец | `IN`, `ANY`, `ALL`, `EXISTS` | `dept_id IN (SELECT dept_id FROM ...)` |
| строка | 1 строка × несколько столбцов | сравнение кортежей | `(a, b) = (SELECT x, y ...)` |
| таблица | много строк × много столбцов | FROM, JOIN, WITH | `FROM (SELECT ...) AS t` |

Скалярный подзапрос, вернувший **0 строк**, даёт NULL. Вернувший **больше одной** строки — ошибку в PostgreSQL (SQLite молча возьмёт первую).

```sql
SELECT full_name, salary,
       salary - (SELECT AVG(salary) FROM teachers) AS diff_from_avg
FROM teachers
WHERE salary > (SELECT AVG(salary) FROM teachers);
```

## По месту в запросе

```sql
SELECT
  c.title,
  (SELECT COUNT(*) FROM enrollments e WHERE e.course_id = c.course_id) AS students   -- в SELECT
FROM courses c
WHERE c.teacher_id IN (SELECT teacher_id FROM teachers WHERE salary > 100000)       -- в WHERE
ORDER BY students DESC;
```

```sql
SELECT city, avg_age
FROM (                                           -- в FROM: «производная таблица»
  SELECT city, AVG(2025 - CAST(substr(birth_date, 1, 4) AS INTEGER)) AS avg_age
  FROM students GROUP BY city
) AS t
WHERE avg_age > 21;
```

```sql
SELECT course_id, AVG(grade) AS avg_grade
FROM enrollments
GROUP BY course_id
HAVING AVG(grade) > (SELECT AVG(grade) FROM enrollments);   -- в HAVING
```

В PostgreSQL у подзапроса в FROM обязателен алиас (с версии 16 — уже нет, но писать его всё равно стоит).
"""),
('Коррелированные и некоррелированные', r"""
# Коррелированный подзапрос

- **Некоррелированный** не ссылается на внешний запрос. Его можно выполнить отдельно, он вычисляется один раз.
- **Коррелированный** ссылается на столбец внешнего запроса и логически выполняется **для каждой внешней строки** заново.

```sql
-- некоррелированный: средняя по всем, считается один раз
SELECT full_name, salary FROM teachers
WHERE salary > (SELECT AVG(salary) FROM teachers);
```

```sql
-- коррелированный: средняя по СВОЕЙ кафедре, своя для каждой строки
SELECT t.full_name, t.dept_id, t.salary
FROM teachers t
WHERE t.salary > (SELECT AVG(t2.salary) FROM teachers t2 WHERE t2.dept_id = t.dept_id);
```

Во втором запросе внутренний `t2.dept_id = t.dept_id` берёт `t.dept_id` из текущей внешней строки. Алиасы `t` и `t2` обязательны: иначе непонятно, о какой строке речь.

## Производительность

«Для каждой строки» звучит медленно, и иногда так и есть. Но оптимизатор PostgreSQL часто сам превращает коррелированный EXISTS/IN в соединение (semi-join), а скалярный подзапрос с агрегатом — нет. Сравните три способа решить одну задачу:

```sql
-- 1. коррелированный подзапрос
SELECT t.full_name, t.salary
FROM teachers t
WHERE t.salary = (SELECT MAX(salary) FROM teachers t2 WHERE t2.dept_id = t.dept_id);
```

```sql
-- 2. агрегат в производной таблице + JOIN: агрегат считается один раз на кафедру
SELECT t.full_name, t.salary
FROM teachers t
JOIN (SELECT dept_id, MAX(salary) AS mx FROM teachers GROUP BY dept_id) m
  ON m.dept_id = t.dept_id AND t.salary = m.mx;
```

```sql
-- 3. окно (модуль 7): один проход по таблице
SELECT full_name, salary FROM (
  SELECT full_name, salary, MAX(salary) OVER (PARTITION BY dept_id) AS mx FROM teachers
) x WHERE salary = mx;
```

Все три дают одинаковый результат. На больших таблицах обычно быстрее 2 и 3. Начинайте с самого понятного, а оптимизируйте по EXPLAIN.

## Где коррелированный подзапрос незаменим

- `EXISTS / NOT EXISTS` — естественно коррелированные.
- «Значение из связанной таблицы» в SELECT, когда связь может отсутствовать и нужно ровно одно значение (`(SELECT MAX(exam_date) FROM enrollments e WHERE e.student_id = s.student_id)`) — без размножения строк.
"""),
('IN, EXISTS или JOIN', r"""
# Semi-join: «у кого есть хотя бы одна связанная строка»

Задача: студенты, у которых есть хотя бы одна пятёрка. Три способа:

```sql
-- IN: список подходящих id
SELECT full_name FROM students
WHERE student_id IN (SELECT student_id FROM enrollments WHERE grade = 5);
```

```sql
-- EXISTS: есть ли подходящая строка для ЭТОГО студента
SELECT s.full_name FROM students s
WHERE EXISTS (SELECT 1 FROM enrollments e WHERE e.student_id = s.student_id AND e.grade = 5);
```

```sql
-- JOIN: даёт ДУБЛИ — по строке на каждую пятёрку
SELECT s.full_name FROM students s
JOIN enrollments e ON e.student_id = s.student_id AND e.grade = 5;
```

У Ивана две пятёрки и у Полины две — в JOIN-версии они повторятся. `JOIN + DISTINCT` уберёт повторы, но это лишняя работа и риск склеить разных людей с одинаковыми именами.

## Сравнение

| | `IN (подзапрос)` | `EXISTS` | `JOIN` |
|---|---|---|---|
| смысл | значение входит в набор | есть хотя бы одна строка | все пары |
| дубли в результате | нет | нет | да, при один-ко-многим |
| столбцы правой таблицы в SELECT | нельзя | нельзя | можно |
| условие из нескольких столбцов | `(a, b) IN (SELECT x, y ...)` | любое условие в WHERE подзапроса | любое в ON |
| что выбирать внутри | ровно один столбец | неважно, принято `SELECT 1` | — |
| NULL | `x IN (…NULL…)` даёт TRUE или UNKNOWN, на результат положительного IN не влияет | NULL не мешает | NULL не соединяется |
| скорость в PostgreSQL | обычно одинаково с EXISTS: оба превращаются в semi-join | | может быть хуже из-за DISTINCT |

## Как выбрать

- Нужны **столбцы** второй таблицы (оценка, название курса) → JOIN.
- Нужна только **проверка факта** → EXISTS или IN. IN короче для простого списка значений; EXISTS — когда условие сложнее «равенства одного столбца» (диапазоны, несколько условий, корреляция по двум столбцам).
- `IN (1, 2, 3)` со списком констант и `IN (SELECT …)` — разные вещи по смыслу, но записываются одинаково.

EXISTS прекращает поиск на первой найденной строке, поэтому `SELECT 1`, `SELECT *` или `SELECT NULL` внутри работают одинаково — значения никто не читает.

```sql
-- EXISTS со сложным условием: студенты, сдавшие экзамен у собственного куратора группы
SELECT s.full_name FROM students s
WHERE EXISTS (
  SELECT 1 FROM enrollments e
  JOIN courses c ON c.course_id = e.course_id
  JOIN study_groups g ON g.group_id = s.group_id
  WHERE e.student_id = s.student_id AND c.teacher_id = g.curator_id AND e.grade IS NOT NULL
);
```
"""),
('NOT IN, NOT EXISTS, LEFT JOIN … IS NULL', r"""
# Anti-join: «у кого нет ни одной связанной строки»

Задача: студенты, которых **нет** в шахматном клубе (сравниваем по email). В club_members есть строка с email = NULL.

```sql
-- NOT IN — ловушка: результат ПУСТОЙ
SELECT full_name FROM students
WHERE email NOT IN (SELECT email FROM club_members);
```

Почему: `x NOT IN (a, b, NULL)` раскрывается в `x <> a AND x <> b AND x <> NULL`. Последнее — UNKNOWN, а `TRUE AND UNKNOWN = UNKNOWN`. WHERE не пропускает ни одной строки. Ошибки нет, просто пусто — и в больших данных это легко не заметить.

```sql
-- NOT EXISTS — правильно
SELECT s.full_name FROM students s
WHERE NOT EXISTS (SELECT 1 FROM club_members m WHERE m.email = s.email);
```

```sql
-- LEFT JOIN … IS NULL — тоже правильно
SELECT s.full_name FROM students s
LEFT JOIN club_members m ON m.email = s.email
WHERE m.email IS NULL;
```

```sql
-- EXCEPT — правильно, но сравнивает целые строки и возвращает только email
SELECT email FROM students
EXCEPT
SELECT email FROM club_members;
```

Обратите внимание: студенты **без email** (Волков, Лосев) попадают в результат NOT EXISTS и LEFT JOIN — их «нет в клубе», раз сравнивать нечего. В EXCEPT они схлопнутся с NULL из клуба и пропадут: операции над множествами считают NULL равными. Какое поведение правильное — решает вопрос задачи.

## Сравнение

| | `NOT IN` | `NOT EXISTS` | `LEFT JOIN … IS NULL` | `EXCEPT` |
|---|---|---|---|---|
| NULL в подзапросе | **пустой результат** | не мешает | не мешает | NULL = NULL |
| NULL в проверяемом столбце | строка выпадает | строка остаётся | строка остаётся | схлопывается |
| дубли | нет | нет | нет (если проверяем IS NULL по ключу) | убирает |
| другие столбцы в выводе | да | да | да, и даже правой таблицы (все NULL) | только сравниваемые |
| скорость в PostgreSQL | часто хуже, не всегда превращается в anti-join | anti-join | anti-join | сортировка/хеш |

## Правило

- По умолчанию для «нет связанных строк» пишите **NOT EXISTS**.
- `NOT IN` допустим только со списком констант или если столбец подзапроса `NOT NULL` по схеме. Иначе добавляйте `WHERE email IS NOT NULL` внутрь — но проще не рисковать.
- В LEFT JOIN-версии проверяйте на NULL столбец, который **не может** быть NULL у настоящей пары (первичный ключ или столбец из условия ON).
"""),
('ANY, ALL и сравнение с набором', r"""
# ANY, SOME, ALL

Сравнение значения с каждым элементом набора.

| Запись | Смысл | Эквивалент |
|---|---|---|
| `x = ANY (подзапрос)` | равно хотя бы одному | `x IN (подзапрос)` |
| `x > ANY (подзапрос)` | больше хотя бы одного | `x > (SELECT MIN(...))` |
| `x > ALL (подзапрос)` | больше всех | `x > (SELECT MAX(...))` |
| `x <> ALL (подзапрос)` | не равно ни одному | `x NOT IN (подзапрос)` — с той же ловушкой NULL |
| `SOME` | синоним ANY | |

```pg
-- преподаватели, получающие больше ЛЮБОГО преподавателя кафедры финансов
SELECT full_name, salary FROM teachers
WHERE salary > ALL (SELECT salary FROM teachers WHERE dept_id = 5);

-- PostgreSQL умеет ANY с массивом: удобно для параметров из приложения
SELECT * FROM students WHERE city = ANY (ARRAY['Тула', 'Тверь']);
```

В SQLite ANY/ALL нет. Переписываем через MIN/MAX:

```sql
SELECT full_name, salary FROM teachers
WHERE salary > (SELECT MAX(salary) FROM teachers WHERE dept_id = 5);
```

## Тонкости

- `x > ALL (пустой набор)` — **TRUE** (больше всех из никого), а `x > (SELECT MAX(...))` от пустого набора — NULL, строк не будет. Это не одно и то же на краевом случае.
- `x > ALL (…NULL…)` — UNKNOWN, как и NOT IN. MAX просто пропустит NULL.
- `x = ANY` и `IN` ведут себя одинаково, `x <> ANY` — **не** «не входит»: это «отличается хотя бы от одного», почти всегда TRUE.

## Сравнение кортежей

Можно сравнивать несколько столбцов сразу:

```sql
-- экзамены, сданные в ту же дату, что и последний экзамен по курсу 1
SELECT student_id, course_id, exam_date FROM enrollments
WHERE (course_id, exam_date) IN (SELECT course_id, MAX(exam_date) FROM enrollments GROUP BY course_id);
```
"""),
('Подзапрос или JOIN: как выбирать', r"""
# Подзапрос или JOIN

Многие задачи решаются и так, и так. Ориентиры:

| Ситуация | Лучше | Почему |
|---|---|---|
| нужны столбцы обеих таблиц | JOIN | подзапрос столбцы не отдаёт (кроме скалярного) |
| проверить «есть / нет» | EXISTS / NOT EXISTS | нет дублей, нет ловушки NULL |
| сравнить с общим агрегатом (средним, максимумом) | скалярный подзапрос или окно | |
| сравнить с агрегатом своей группы | окно или JOIN с агрегатом | коррелированный подзапрос читается хуже и бывает медленнее |
| одно значение из связанной таблицы, связь может отсутствовать | скалярный подзапрос в SELECT | не размножает строки, даёт NULL при отсутствии |
| несколько значений из одной связанной таблицы | JOIN с агрегатом (или LATERAL) | несколько скалярных подзапросов — несколько проходов |
| многоступенчатая логика | CTE (модуль 6) | читаемость |

## Скалярный подзапрос в SELECT против JOIN + GROUP BY

```sql
-- подзапрос: сразу видно, что считаем
SELECT s.full_name,
       (SELECT COUNT(*)  FROM enrollments e WHERE e.student_id = s.student_id) AS courses,
       (SELECT AVG(grade) FROM enrollments e WHERE e.student_id = s.student_id) AS avg_grade
FROM students s;
```

```sql
-- JOIN + GROUP BY: один проход по enrollments
SELECT s.full_name, COUNT(e.course_id) AS courses, AVG(e.grade) AS avg_grade
FROM students s
LEFT JOIN enrollments e ON e.student_id = s.student_id
GROUP BY s.student_id, s.full_name;
```

Результаты совпадают. Когда метрик две-три — разницы почти нет. Когда десять — JOIN-версия заметно выгоднее.

# Шпаргалка подзапросов

| Похожие | Разница |
|---|---|
| скалярный и табличный | одно значение и набор строк |
| коррелированный и некоррелированный | зависит от внешней строки или вычисляется один раз |
| `IN` и `EXISTS` | одинаковы по результату для положительной проверки; EXISTS гибче |
| `IN`/`EXISTS` и `JOIN` | JOIN даёт дубли и столбцы второй таблицы |
| `NOT IN` и `NOT EXISTS` | NOT IN ломается от NULL в подзапросе |
| `NOT EXISTS` и `LEFT JOIN … IS NULL` | одинаковый результат, NOT EXISTS понятнее |
| `NOT EXISTS` и `EXCEPT` | EXCEPT сравнивает целые строки и считает NULL равными |
| `= ANY` и `IN` | одно и то же |
| `> ALL` и `> MAX` | различаются на пустом наборе и при NULL |
| подзапрос в FROM и CTE | одно и то же по смыслу, CTE читаемее (модуль 6) |
"""),
]

PAGES = {'m00': M00, 'm01': M01, 'm02': M02, 'm03': M03, 'm04': M04, 'm05': M05}
