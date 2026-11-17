-- Q: How does performance differ by merchant country? (2025)
SELECT country,
       COUNT(DISTINCT merchant_id)                                     AS merchants,
       ROUND(SUM(tpv_eur) / 1e6, 1)                                    AS tpv_m,
       ROUND(SUM(net_revenue_eur) / SUM(tpv_eur) * 1e4, 1)             AS take_rate_bps,
       ROUND(SUM(contribution_2_eur) / 1e6, 2)                         AS contribution_2_m,
       ROUND(SUM(contribution_2_eur) / SUM(net_revenue_eur) * 100, 1)  AS margin_pct
FROM merchant_month
WHERE month >= '2025-01-01'
GROUP BY country
ORDER BY contribution_2_m DESC;
