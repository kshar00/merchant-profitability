-- The unit economics model. Builds two views the analysis queries read from.
--
-- Definitions (all amounts in EUR):
--   TPV                 total payment volume processed
--   Gross revenue       what the merchant is billed
--   Pass-through costs  third-party fees paid on: interchange and scheme fees to card
--                       issuers and schemes, and partner fees to BNPL providers
--   Net revenue         gross revenue - pass-through costs (what the business keeps)
--   Take rate           net revenue / TPV, shown in basis points (1 bp = 0.01%)
--   Transaction costs   own processing cost + fraud and chargeback losses
--   Contribution 1      net revenue - transaction costs
--   Cost to serve       allocated account management and support, per merchant per month
--   Contribution 2      contribution 1 - cost to serve  ("merchant profitability")

DROP VIEW IF EXISTS fact_economics;
CREATE VIEW fact_economics AS
WITH priced AS (
    SELECT t.merchant_id, t.month, t.payment_method, t.transactions, t.tpv_eur,
           t.cross_border_tpv_eur, t.fraud_chargeback_loss_eur,
           p.pct_fee, p.fixed_fee_eur, p.passes_through_interchange,
           c.processing_cost_per_txn_eur,
           (t.tpv_eur - t.cross_border_tpv_eur) * c.interchange_scheme_pct_domestic
             + t.cross_border_tpv_eur * c.interchange_scheme_pct_cross_border
             + t.transactions * c.scheme_fee_fixed_eur
             + t.tpv_eur * c.partner_fee_pct                           AS pass_through_cost_eur
    FROM monthly_transactions t
    JOIN pricing p
      ON p.merchant_id = t.merchant_id
     AND p.payment_method = t.payment_method
     AND t.month >= p.valid_from AND t.month < p.valid_to
    JOIN payment_method_costs c
      ON c.payment_method = t.payment_method
),
billed AS (
    SELECT *,
           -- Interchange++ merchants are billed interchange and scheme fees at cost
           -- (passes_through_interchange = 1); blended merchants are not, so those
           -- fees come out of our fee. BNPL partner fees are never billed at cost.
           pass_through_cost_eur * passes_through_interchange
             + tpv_eur * pct_fee + transactions * fixed_fee_eur        AS gross_revenue_eur
    FROM priced
)
SELECT merchant_id, month, payment_method, transactions, tpv_eur, cross_border_tpv_eur,
       gross_revenue_eur,
       pass_through_cost_eur,
       gross_revenue_eur - pass_through_cost_eur                       AS net_revenue_eur,
       transactions * processing_cost_per_txn_eur                      AS processing_cost_eur,
       fraud_chargeback_loss_eur
FROM billed;

DROP VIEW IF EXISTS merchant_month;
CREATE VIEW merchant_month AS
SELECT f.merchant_id, f.month, m.segment, m.country, m.pricing_model,
       SUM(f.transactions)                                             AS transactions,
       SUM(f.tpv_eur)                                                  AS tpv_eur,
       SUM(f.gross_revenue_eur)                                        AS gross_revenue_eur,
       SUM(f.pass_through_cost_eur)                                    AS pass_through_cost_eur,
       SUM(f.net_revenue_eur)                                          AS net_revenue_eur,
       SUM(f.processing_cost_eur + f.fraud_chargeback_loss_eur)
                                                                       AS transaction_costs_eur,
       SUM(f.net_revenue_eur - f.processing_cost_eur
           - f.fraud_chargeback_loss_eur)                              AS contribution_1_eur,
       MAX(m.cost_to_serve_eur_month)                                  AS cost_to_serve_eur,
       SUM(f.net_revenue_eur - f.processing_cost_eur
           - f.fraud_chargeback_loss_eur)
         - MAX(m.cost_to_serve_eur_month)                              AS contribution_2_eur
FROM fact_economics f
JOIN merchants m ON m.merchant_id = f.merchant_id
GROUP BY f.merchant_id, f.month, m.segment, m.country, m.pricing_model;
