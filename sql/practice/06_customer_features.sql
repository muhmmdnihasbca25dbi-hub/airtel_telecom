DROP TABLE IF EXISTS customer_features;      -- rebuild every run
CREATE TABLE customer_features AS            -- store the answer
SELECT c.customer_id, c.activation_date,     -- who, and since
       CAST(julianday('2025-06-30')          -- days on the
          - julianday(c.activation_date)     -- network at the
            AS INT) AS tenure_days,          -- window end
       CAST((julianday('2025-06-30')         -- whole years
          - julianday(c.activation_date))    -- in days
            / 365 AS INT) AS tenure_years,   -- whole years
       CAST(julianday(CASE                   -- end: churn date
              WHEN c.churn_date < '2025-06-30' -- if before the
              THEN c.churn_date              -- window's end,
              ELSE '2025-06-30' END)         -- else window end
          - julianday(CASE                   -- start: activation
              WHEN c.activation_date > '2025-01-01' -- if later
              THEN c.activation_date         -- than the window's
              ELSE '2025-01-01' END)         -- start, else start
            AS INT) AS observed_days,        -- days in window
       ci.circle_name, ci.region,            -- where
       p.plan_name, p.plan_type,             -- what they bought
       p.price_inr, p.validity_days,         -- price, validity
       p.monthly_gb, p.quota_basis,          -- from sql/04
       c.age_band, c.gender, c.device_type,  -- who they are
       c.os, c.acquisition_channel,          -- handset, signup
       c.connection_type, c.ab_group,        -- type, A/B group
       c.is_churned, c.churn_date,           -- the outcome
       CAST(julianday(c.churn_date)          -- NULL if stayed
          - julianday(c.activation_date)     -- minus the start
            AS INT) AS days_to_churn,        -- NULL if stayed
       u.usage_days, u.total_data_mb,        -- from sql/02
       u.total_voice_min, u.total_sms,       -- voice, texts
       u.roaming_days, u.mb_per_active_day,  -- roaming, ratio
       u.mb_per_observed_day,                -- the other ratio
       u.last_usage_date, u.recency_days,    -- last use
       r.recharge_count, r.recharge_total_6m, -- from sql/01
       r.actual_arpu_6m,                     -- per month
       c.arpu_inr AS stated_arpu,            -- renamed, on purpose
       ROUND(c.arpu_inr                      -- stated minus
             - r.actual_arpu_6m, 2)          -- actual
         AS arpu_gap,                        -- the difference
       x.complaint_count, x.unresolved_count, -- from sql/03
       x.resolved_count, x.avg_resolution_days -- and the average
FROM   customers c                           -- all 22,000
JOIN   circles       ci                      -- every sub has one
       ON ci.circle_id = c.circle_id         -- circle match
JOIN   v_plans_clean p                       -- every sub has one
       ON p.plan_id = c.current_plan_id      -- plan match
LEFT JOIN v_usage_customer     u             -- keep everyone
       ON u.customer_id = c.customer_id      -- one to one
LEFT JOIN v_revenue_customer   r             -- keep everyone
       ON r.customer_id = c.customer_id      -- one to one
LEFT JOIN v_complaint_customer x             -- keep everyone
       ON x.customer_id = c.customer_id;     -- one to one
       