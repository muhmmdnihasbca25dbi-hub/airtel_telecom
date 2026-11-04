DROP VIEW IF EXISTS v_complaint_customer;    -- runnable twice
CREATE VIEW v_complaint_customer AS          -- name the rule
SELECT c.customer_id,                        -- one row per sub
       COALESCE(x.n_total, 0)                -- never = 0
         AS complaint_count,                 -- the column name
       COALESCE(x.n_open, 0)                 -- still open
         AS unresolved_count,                -- the column name
       COALESCE(x.n_closed, 0)               -- closed
         AS resolved_count,                  -- the column name
       x.avg_resolution_days                 -- left NULL on purpose
FROM   customers c                           -- all 22,000
LEFT JOIN (                                  -- keep everyone
    SELECT customer_id,                      -- roll up FIRST
           COUNT(*) AS n_total,              -- every ticket
           SUM(CASE WHEN is_resolved = 0     -- open tickets
                    THEN 1 ELSE 0 END) AS n_open, -- open count
           SUM(CASE WHEN is_resolved = 1     -- closed tickets
                    THEN 1 ELSE 0 END) AS n_closed, -- closed count
           ROUND(AVG(resolution_days), 2)    -- closed ones only
             AS avg_resolution_days          -- the column name
    FROM   complaints                        -- one row = ticket
    GROUP  BY customer_id                    -- one row per sub
) x ON x.customer_id = c.customer_id;        -- one to one