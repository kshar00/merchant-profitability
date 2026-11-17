-- Q: Which segments grow but become less profitable?
WITH y AS (
    SELECT segment, substr(month, 1, 4) AS year,
           SUM(tpv_eur) AS tpv, SUM(net_revenue_eur) AS net_rev,
           SUM(contribution_2_eur) AS cm2, COUNT(DISTINCT merchant_id) AS merchants
    FROM merchant_month
    GROUP BY segment, year
)
SELECT a.segment,
       b.merchants                                         AS merchants_2025,
       ROUND(b.tpv / 1e6, 1)                               AS tpv_2025_m,
       ROUND((b.tpv / a.tpv - 1) * 100, 1)                 AS tpv_growth_pct,
       ROUND(a.net_rev / a.tpv * 1e4, 1)                   AS take_rate_2024_bps,
       ROUND(b.net_rev / b.tpv * 1e4, 1)                   AS take_rate_2025_bps,
       ROUND((b.net_rev / a.net_rev - 1) * 100, 1)         AS net_revenue_growth_pct,
       ROUND(b.cm2 / 1e6, 2)                               AS contribution_2025_m,
       ROUND((b.cm2 / a.cm2 - 1) * 100, 1)                 AS contribution_growth_pct,
       ROUND(a.cm2 / a.net_rev * 100, 1)                   AS margin_2024_pct,
       ROUND(b.cm2 / b.net_rev * 100, 1)                   AS margin_2025_pct
FROM y a
JOIN y b ON a.segment = b.segment AND a.year = '2024' AND b.year = '2025'
ORDER BY b.cm2 DESC;
