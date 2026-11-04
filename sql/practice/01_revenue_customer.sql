-- ==============-- 01_revenue_customer.sql
-- What this file fixes :what each subscriber paid
 -- Defect numbers     : 1 and 6 from tab 3
   -- Window : 2025-01-01 to 2025-06-30

DROP VIEW IF EXISTS v_revenue_customer;      -- runnable twice
CREATE VIEW v_revenue_customer AS            -- name the rule
SELECT c.customer_id,                        -- one row per sub
       COALESCE(r.n_payments, 0)             -- no payments = 0
         AS recharge_count,                  -- how many paid
       COALESCE(r.total_inr, 0)              -- no money = 0
         AS recharge_total_6m,               -- rupees, 6 months
       ROUND(COALESCE(r.total_inr, 0)        -- the same total
             / 6.0, 2) AS actual_arpu_6m     -- per month
FROM   customers c                           -- all 22,000
LEFT JOIN (                                  -- keep everyone
    SELECT customer_id,                      -- roll up FIRST
           COUNT(*)        AS n_payments,    -- how many
           SUM(amount_inr) AS total_inr      -- how much
    FROM   recharges                         -- one row = payment
    WHERE  recharge_date BETWEEN '2025-01-01' -- the window
                            AND '2025-06-30' -- the window
    GROUP  BY customer_id                    -- one row per sub
) r ON r.customer_id = c.customer_id;        -- one to one
