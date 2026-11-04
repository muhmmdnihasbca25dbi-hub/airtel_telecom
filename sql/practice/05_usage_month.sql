-- ==================================================-- 05_usage_month.sql-- What this file fixes : a monthly view, from usage
-- Defect numbers       : 4 from the Quality Log-- THE JUNE RULE        : recharges stops on 2025-06-27--   and June payments are incomplete. No monthly--   revenue series may include June 2025. usage_daily--   is complete to 2025-06-30 and is not affected.-- Written by           : <your name>-- ==================================================
DROP VIEW IF EXISTS v_usage_month;           -- runnable twice
CREATE VIEW v_usage_month AS                 -- name the rule
SELECT customer_id,                          -- the subscriber
       strftime('%Y-%m', usage_date)         -- '2025-03'
         AS month,                           -- the bucket
       COUNT(*)           AS usage_days,     -- days seen
       SUM(data_mb)       AS total_mb,       -- data
       SUM(voice_minutes) AS total_voice,    -- voice
       SUM(is_roaming)    AS roaming_days    -- roaming
FROM   usage_daily                           -- complete table
GROUP  BY customer_id,                       -- one row per sub
          strftime('%Y-%m', usage_date);     -- per month