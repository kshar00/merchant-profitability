-- Q: Why is a segment's take rate moving?
-- Payment method mix by segment, Q4 2024 vs Q4 2025, with each method's contribution per euro.
WITH q AS (
    SELECT m.segment, f.payment_method,
           SUM(CASE WHEN f.month BETWEEN '2024-10-01' AND '2024-12-01' THEN f.tpv_eur ELSE 0 END) AS tpv_q4_2024,
           SUM(CASE WHEN f.month BETWEEN '2025-10-01' AND '2025-12-01' THEN f.tpv_eur ELSE 0 END) AS tpv_q4_2025,
           SUM(CASE WHEN f.month >= '2025-01-01' THEN f.net_revenue_eur
                    - f.processing_cost_eur - f.fraud_chargeback_loss_eur END)
             / SUM(CASE WHEN f.month >= '2025-01-01' THEN f.tpv_eur END) * 1e4         AS contribution_1_bps_2025
    FROM fact_economics f
    JOIN merchants m ON m.merchant_id = f.merchant_id
    GROUP BY m.segment, f.payment_method
)
SELECT segment, payment_method,
       ROUND(tpv_q4_2024 * 100.0 / SUM(tpv_q4_2024) OVER (PARTITION BY segment), 1) AS share_q4_2024_pct,
       ROUND(tpv_q4_2025 * 100.0 / SUM(tpv_q4_2025) OVER (PARTITION BY segment), 1) AS share_q4_2025_pct,
       ROUND(contribution_1_bps_2025, 1)                                             AS contribution_1_bps_2025
FROM q
ORDER BY segment, payment_method;
