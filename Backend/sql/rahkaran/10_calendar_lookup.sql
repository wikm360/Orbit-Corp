-- ai.calendar (see below): one row per Gregorian day 2000-01-01..2040-12-31 with Jalali (Shamsi) parts and the company's fiscal calendar
-- (fiscal year starts on 1 Mehr = Jalali month 7). Derived from SYS3.JalaliStartDate (1 Farvardin of each Jalali year, first row = 1278).
CREATE OR ALTER VIEW ai.calendar_generator AS
WITH d AS (
    SELECT CAST(DATEADD(DAY, gs.value, '2000-01-01') AS date) AS gregorian_date
    FROM GENERATE_SERIES(0, 14975) AS gs
),
j AS (
    SELECT d.gregorian_date,
           ys.start_date AS jalali_year_start,
           1278 + ys.idx - 1 AS jalali_year
    FROM d
    CROSS APPLY (
        SELECT TOP 1 CAST(x.StartDate AS date) AS start_date,
               (SELECT COUNT(*) FROM SYS3.JalaliStartDate y WHERE y.StartDate <= x.StartDate) AS idx
        FROM SYS3.JalaliStartDate x
        WHERE x.StartDate <= d.gregorian_date
        ORDER BY x.StartDate DESC
    ) ys
),
m AS (
    SELECT gregorian_date, jalali_year,
           DATEDIFF(DAY, jalali_year_start, gregorian_date) + 1 AS day_of_year
    FROM j
),
p AS (
    SELECT gregorian_date, jalali_year, day_of_year,
           CASE WHEN day_of_year <= 186 THEN (day_of_year - 1) / 31 + 1 ELSE (day_of_year - 187) / 30 + 7 END AS jalali_month,
           CASE WHEN day_of_year <= 186 THEN (day_of_year - 1) % 31 + 1 ELSE (day_of_year - 187) % 30 + 1 END AS jalali_day
    FROM m
)
SELECT
    p.gregorian_date,
    p.jalali_year,
    p.jalali_month,
    p.jalali_day,
    p.jalali_year * 10000 + p.jalali_month * 100 + p.jalali_day AS jalali_date_int,
    p.jalali_year * 100 + p.jalali_month AS jalali_ym,
    CAST(p.jalali_year AS varchar(4)) + '/' + RIGHT('0' + CAST(p.jalali_month AS varchar(2)), 2) + '/' + RIGHT('0' + CAST(p.jalali_day AS varchar(2)), 2) AS jalali_date,
    CASE p.jalali_month WHEN 1 THEN N'فروردین' WHEN 2 THEN N'اردیبهشت' WHEN 3 THEN N'خرداد' WHEN 4 THEN N'تیر' WHEN 5 THEN N'مرداد'
        WHEN 6 THEN N'شهریور' WHEN 7 THEN N'مهر' WHEN 8 THEN N'آبان' WHEN 9 THEN N'آذر' WHEN 10 THEN N'دی' WHEN 11 THEN N'بهمن' ELSE N'اسفند' END AS jalali_month_name,
    (p.jalali_month - 1) / 3 + 1 AS jalali_quarter,
    CASE WHEN p.jalali_month >= 7 THEN p.jalali_year ELSE p.jalali_year - 1 END AS fiscal_year,
    CASE WHEN p.jalali_month >= 7 THEN p.jalali_month - 6 ELSE p.jalali_month + 6 END AS fiscal_month_no,
    (CASE WHEN p.jalali_month >= 7 THEN p.jalali_month - 7 ELSE p.jalali_month + 5 END) / 3 + 1 AS fiscal_quarter,
    DATEDIFF(DAY, '1900-01-06', p.gregorian_date) % 7 AS weekday_no,   -- 0 = Saturday ... 6 = Friday
    CASE DATEDIFF(DAY, '1900-01-06', p.gregorian_date) % 7 WHEN 0 THEN N'شنبه' WHEN 1 THEN N'یکشنبه' WHEN 2 THEN N'دوشنبه' WHEN 3 THEN N'سه‌شنبه'
        WHEN 4 THEN N'چهارشنبه' WHEN 5 THEN N'پنجشنبه' ELSE N'جمعه' END AS weekday_name,
    CASE WHEN DATEDIFF(DAY, '1900-01-06', p.gregorian_date) % 7 = 6 THEN 1 ELSE 0 END AS is_friday
FROM p;
GO

-- The generated calendar is materialised into a small indexed table (15K rows) so joins from the big fact views are index seeks, then ai.calendar is a
-- plain view over it. (Re-created on every apply.)
DROP VIEW IF EXISTS ai.calendar;
GO
DROP TABLE IF EXISTS ai.calendar_data;
GO
SELECT * INTO ai.calendar_data FROM ai.calendar_generator;
GO
ALTER TABLE ai.calendar_data ALTER COLUMN gregorian_date date NOT NULL;
GO
ALTER TABLE ai.calendar_data ADD CONSTRAINT PK_ai_calendar_data PRIMARY KEY CLUSTERED (gregorian_date);
GO
DROP VIEW ai.calendar_generator;
GO
CREATE VIEW ai.calendar AS SELECT * FROM ai.calendar_data;
GO

-- ai.lookup_values: flattened SYS3.Lookup enumeration dictionary (Persian value + English translation).
CREATE OR ALTER VIEW ai.lookup_values AS
SELECT l.System AS module,
       l.Type AS lookup_type,
       li.Title AS lookup_type_title,
       l.Code AS code,
       l.Value AS value_fa,
       t.Value AS value_en
FROM SYS3.Lookup l
LEFT JOIN SYS3.LookupInfo li ON li.Type = l.Type
LEFT JOIN SYS3.LookupTranslation t ON t.LookupRef = l.LookupID AND t.Culture = 'en-us';
GO
