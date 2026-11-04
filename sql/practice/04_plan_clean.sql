DROP VIEW IF EXISTS v_plans_clean;           -- runnable twice
CREATE VIEW v_plans_clean AS                 -- name the rule
SELECT plan_id, plan_name, plan_type,        -- carried across
       price_inr, validity_days,             -- as they are
       data_quota,                           -- the raw text
       CASE WHEN INSTR(data_quota, '/day')   > 0 -- a daily quota?
            THEN 'per day'                   -- prepaid style
            WHEN INSTR(data_quota, '/month') > 0 -- a monthly one?
            THEN 'per month'                 -- postpaid style
       END AS quota_basis,                   -- keep the unit
       CAST(SUBSTR(data_quota, 1,            -- text before the
                INSTR(data_quota, ' ') - 1)      -- first space
            AS REAL) AS quota_gb,            -- as a number
       CASE WHEN INSTR(data_quota, '/day') > 0 -- daily: take the
            THEN CAST(SUBSTR(data_quota, 1,  -- number before
                 INSTR(data_quota, ' ') - 1) -- the first space
                 AS REAL) * 30               -- a day x 30
            ELSE CAST(SUBSTR(data_quota, 1,  -- monthly: the
                 INSTR(data_quota, ' ') - 1) -- number as it is
                 AS REAL)                    -- already monthly
       END AS monthly_gb,                    -- one basis
       ott_benefit, is_5g                    -- carried across
FROM   plans;                                -- 14 rows