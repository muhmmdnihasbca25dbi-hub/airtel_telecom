DROP VIEW IF EXISTS v_usage_customer;        -- runnable twice
CREATE VIEW v_usage_customer AS              -- name the rule
SELECT c.customer_id,                        -- one row per sub
       COALESCE(u.usage_days, 0)             -- days seen
         AS usage_days,                      -- the column name
       COALESCE(u.total_mb, 0)               -- data, all days
         AS total_data_mb,                   -- the column name
       COALESCE(u.total_voice, 0)            -- voice minutes
         AS total_voice_min,                 -- the column name
       COALESCE(u.total_sms, 0)              -- texts sent
         AS total_sms,                       -- the column name
       COALESCE(u.roaming_days, 0)           -- days roaming
         AS roaming_days,                    -- the column name
       ROUND(u.total_mb / u.usage_days, 2)   -- NULL if no days
         AS mb_per_active_day,               -- intensity
       ROUND(COALESCE(u.total_mb, 0)         -- all 181 days
             / 181.0, 2)                     -- divided by 181
         AS mb_per_observed_day,             -- volume
       u.last_usage_date,                    -- last day seen
       CAST(julianday('2025-06-30')          -- window end
          - julianday(u.last_usage_date)     -- minus last day
            AS INT) AS recency_days          -- days silent
FROM   customers c                           -- all 22,000
LEFT JOIN (                                  -- keep everyone
    SELECT customer_id,                      -- roll up FIRST
           COUNT(*)           AS usage_days, -- one row = a day
           SUM(data_mb)       AS total_mb,   -- data used
           SUM(voice_minutes) AS total_voice, -- call minutes
           SUM(sms_count)     AS total_sms,  -- texts sent
           SUM(is_roaming)    AS roaming_days, -- roaming days
           MAX(usage_date)    AS last_usage_date -- last day seen
    FROM   usage_daily                       -- 1,326,739 rows
    GROUP  BY customer_id                    -- one row per sub
) u ON u.customer_id = c.customer_id;        -- one to one
