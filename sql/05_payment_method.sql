-- Q: Which payment methods earn the most per euro, and how is the mix moving?
-- Contribution here is before cost to serve, which is a per-merchant cost.
SELECT payment_method,
       substr(month, 1, 4)                                             AS year,
       ROUND(SUM(tpv_eur) / 1e6, 1)                                    AS tpv_m,
       ROUND(SUM(tpv_eur) * 100.0
             / SUM(SUM(tpv_eur)) OVER (PARTITION BY substr(month, 1, 4)), 1) AS share_of_tpv_pct,
       ROUND(SUM(net_revenue_eur) / SUM(tpv_eur) * 1e4, 1)             AS take_rate_bps,
       ROUND(SUM(net_revenue_eur - processing_cost_eur
                 - fraud_chargeback_loss_eur) / SUM(tpv_eur) * 1e4, 1) AS contribution_1_bps
FROM fact_economics
GROUP BY payment_method, year
ORDER BY payment_method, year;
