-- Q: Which merchants contribute most, and which lose money? (2025)
SELECT merchant_id, segment, country, pricing_model,
       COUNT(*)                                             AS active_months,
       ROUND(SUM(tpv_eur), 0)                               AS tpv_eur,
       ROUND(SUM(net_revenue_eur), 0)                       AS net_revenue_eur,
       ROUND(SUM(net_revenue_eur) / SUM(tpv_eur) * 1e4, 1)  AS take_rate_bps,
       ROUND(SUM(contribution_1_eur), 0)                    AS contribution_1_eur,
       ROUND(SUM(cost_to_serve_eur), 0)                     AS cost_to_serve_eur,
       ROUND(SUM(contribution_2_eur), 0)                    AS contribution_2_eur
FROM merchant_month
WHERE month >= '2025-01-01'
GROUP BY merchant_id, segment, country, pricing_model
ORDER BY contribution_2_eur DESC;
