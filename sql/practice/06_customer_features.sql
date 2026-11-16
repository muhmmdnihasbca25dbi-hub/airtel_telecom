-- ==================================================
-- 06_customer_features.sql
-- What this file builds : one row per subscriber
-- Reads                 : customers, circles and the
--                         views from sql/01 to sql/04
-- Renamed on purpose    : arpu_inr -> stated_arpu
-- Leakage columns       : churn_date, days_to_churn,
--                         recency_days, r_score
-- ==================================================

DROP TABLE IF EXISTS customer_features;

CREATE TABLE customer_features AS

WITH rfm AS (
    SELECT
        c.customer_id,

        NTILE(4) OVER (
            ORDER BY COALESCE(u.recency_days, 999) DESC
        ) AS r_score,

        NTILE(4) OVER (
            ORDER BY r.recharge_count
        ) AS f_score,

        NTILE(4) OVER (
            ORDER BY r.recharge_total_6m
        ) AS m_score

    FROM customers c

    JOIN v_usage_customer u
        ON u.customer_id = c.customer_id

    JOIN v_revenue_customer r
        ON r.customer_id = c.customer_id
)

SELECT
    c.customer_id,
    c.activation_date,

    CAST(
        julianday('2025-06-30')
        - julianday(c.activation_date)
        AS INT
    ) AS tenure_days,

    CAST(
        (julianday('2025-06-30')
        - julianday(c.activation_date)) / 365
        AS INT
    ) AS tenure_years,

    CAST(
        julianday(
            CASE
                WHEN c.churn_date < '2025-06-30'
                THEN c.churn_date
                ELSE '2025-06-30'
            END
        )
        -
        julianday(
            CASE
                WHEN c.activation_date > '2025-01-01'
                THEN c.activation_date
                ELSE '2025-01-01'
            END
        )
        AS INT
    ) AS observed_days,

    ci.circle_name,
    ci.region,

    p.plan_name,
    p.plan_type,
    p.price_inr,
    p.validity_days,
    p.monthly_gb,
    p.quota_basis,

    c.age_band,
    c.gender,
    c.device_type,
    c.os,
    c.acquisition_channel,
    c.connection_type,
    c.ab_group,

    c.is_churned,
    c.churn_date,

    CAST(
        julianday(c.churn_date)
        - julianday(c.activation_date)
        AS INT
    ) AS days_to_churn,

    u.usage_days,
    u.total_data_mb,
    u.total_voice_min,
    u.total_sms,
    u.roaming_days,
    u.mb_per_active_day,
    u.mb_per_observed_day,
    u.last_usage_date,
    u.recency_days,

    r.recharge_count,
    r.recharge_total_6m,
    r.actual_arpu_6m,

    c.arpu_inr AS stated_arpu,

    ROUND(
        c.arpu_inr - r.actual_arpu_6m,
        2
    ) AS arpu_gap,

    x.complaint_count,
    x.unresolved_count,
    x.resolved_count,
    x.avg_resolution_days,

    rfm.r_score,
    rfm.f_score,
    rfm.m_score

FROM customers c

JOIN circles ci
    ON ci.circle_id = c.circle_id

JOIN v_plans_clean p
    ON p.plan_id = c.current_plan_id

LEFT JOIN v_usage_customer u
    ON u.customer_id = c.customer_id

LEFT JOIN v_revenue_customer r
    ON r.customer_id = c.customer_id

LEFT JOIN v_complaint_customer x
    ON x.customer_id = c.customer_id

JOIN rfm
    ON rfm.customer_id = c.customer_id;


-- ==================================================
-- INDEXES
-- ==================================================

CREATE INDEX IF NOT EXISTS ix_cf_churn
    ON customer_features(is_churned);

CREATE INDEX IF NOT EXISTS ix_cf_ab
    ON customer_features(ab_group);
       