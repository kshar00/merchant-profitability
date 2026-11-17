-- Q: How did the business do, year on year?
SELECT substr(month, 1, 4)                                             AS year,
       ROUND(SUM(tpv_eur) / 1e6, 1)                                    AS tpv_m,
       ROUND(SUM(gross_revenue_eur) / 1e6, 2)                          AS gross_revenue_m,
       ROUND(SUM(pass_through_cost_eur) / 1e6, 2)                      AS pass_through_m,
       ROUND(SUM(net_revenue_eur) / 1e6, 2)                            AS net_revenue_m,
       ROUND(SUM(net_revenue_eur) / SUM(tpv_eur) * 1e4, 1)             AS take_rate_bps,
       ROUND(SUM(transaction_costs_eur) / 1e6, 2)                      AS transaction_costs_m,
       ROUND(SUM(contribution_1_eur) / 1e6, 2)                         AS contribution_1_m,
       ROUND(SUM(cost_to_serve_eur) / 1e6, 2)                          AS cost_to_serve_m,
       ROUND(SUM(contribution_2_eur) / 1e6, 2)                         AS contribution_2_m,
       ROUND(SUM(contribution_2_eur) / SUM(net_revenue_eur) * 100, 1)  AS contribution_margin_pct
FROM merchant_month
GROUP BY year
ORDER BY year;
