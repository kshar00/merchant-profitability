-- Q: How are volume, revenue and margin trending month by month?
SELECT month,
       ROUND(SUM(tpv_eur) / 1e6, 1)                                    AS tpv_m,
       ROUND(SUM(net_revenue_eur) / 1e6, 3)                            AS net_revenue_m,
       ROUND(SUM(net_revenue_eur) / SUM(tpv_eur) * 1e4, 2)             AS take_rate_bps,
       ROUND(SUM(contribution_2_eur) / 1e6, 3)                         AS contribution_2_m,
       ROUND(SUM(contribution_2_eur) / SUM(net_revenue_eur) * 100, 1)  AS margin_pct
FROM merchant_month
GROUP BY month
ORDER BY month;
