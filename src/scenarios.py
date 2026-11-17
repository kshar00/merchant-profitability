"""Scenario model: what do volume and pricing changes do to contribution?

Base year: 2025 actuals from the synthetic data. Each scenario changes one lever
and keeps everything else at 2025 levels. Assumptions (elasticities, churn) are
stated in the code and in the output, because they matter more than the arithmetic.

Run:  python src/scenarios.py
"""

import numpy as np
import pandas as pd

from db import ROOT, connect, query

OUT = ROOT / "outputs"


def money(x):
    return f"EUR {x / 1e6:,.2f}m"


def base_by_segment(con):
    return query(con, """
        SELECT segment,
               SUM(tpv_eur) AS tpv, SUM(net_revenue_eur) AS net_rev,
               SUM(transaction_costs_eur) AS txn_costs,
               SUM(cost_to_serve_eur) AS cts, SUM(contribution_2_eur) AS cm2
        FROM merchant_month WHERE month >= '2025-01-01'
        GROUP BY segment""").set_index("segment")


# ---------------------------------------------------------------------------
# 1. Volume grows while take rate falls (an enterprise renewal)
# ---------------------------------------------------------------------------
def enterprise_volume_vs_price(base):
    """Contribution change for a grid of volume growth x take-rate cut.

    Net revenue scales with volume and with the take rate; transaction costs scale
    with volume only; cost to serve does not change.
    """
    e = base.loc["Enterprise retail"]
    growth = np.array([0, 0.10, 0.20, 0.30, 0.40, 0.50])
    cuts = np.array([0, 0.05, 0.10, 0.15, 0.20, 0.30])
    grid = pd.DataFrame(index=[f"{c:.0%}" for c in cuts], columns=[f"+{g:.0%}" for g in growth], dtype=float)
    for c in cuts:
        for g in growth:
            cm2 = (1 + g) * (e.net_rev * (1 - c) - e.txn_costs) - e.cts
            grid.loc[f"{c:.0%}", f"+{g:.0%}"] = cm2 - e.cm2
    grid.index.name = "take_rate_cut"

    # Breakeven: extra volume needed to keep contribution flat after a cut
    unit_margin = e.net_rev - e.txn_costs  # contribution before cost to serve, at base volume
    breakeven = pd.DataFrame({
        "take_rate_cut": cuts[1:],
        "volume_growth_needed": [unit_margin / (e.net_rev * (1 - c) - e.txn_costs) - 1 for c in cuts[1:]],
    })
    return grid, breakeven, e


# ---------------------------------------------------------------------------
# 2. Minimum monthly fee for small merchants
# ---------------------------------------------------------------------------
def minimum_fee(con, minimum=250.0, churn_rates=(0.0, 0.2, 0.4)):
    """Blended-pricing merchants pay at least `minimum` EUR net revenue a month.

    Merchants below the minimum are billed the difference. Some of them leave
    instead (churn); a merchant who leaves takes all of its contribution with it,
    and its cost to serve goes away too. Leavers are assumed to be an average
    affected merchant, not the worst ones, so the result does not depend on
    guessing who leaves.
    """
    mm = query(con, """
        SELECT merchant_id, segment, net_revenue_eur, contribution_2_eur
        FROM merchant_month
        WHERE month >= '2025-01-01' AND pricing_model = 'blended'""")
    mm["top_up"] = (minimum - mm.net_revenue_eur).clip(lower=0)
    per_merchant = mm.groupby("merchant_id").agg(top_up=("top_up", "sum"), cm2=("contribution_2_eur", "sum"))
    affected = per_merchant[per_merchant.top_up > 0]
    tpv = query(con, """
        SELECT merchant_id, SUM(tpv_eur) AS tpv FROM merchant_month
        WHERE month >= '2025-01-01' AND pricing_model = 'blended' GROUP BY merchant_id""").set_index("merchant_id")
    affected = affected.join(tpv)
    rows = []
    for churn in churn_rates:
        stay = 1 - churn
        uplift = stay * affected.top_up.sum() - churn * affected.cm2.sum()
        rows.append(dict(churn_of_affected=churn, merchants_affected=len(affected),
                         affected_contribution_today_eur=affected.cm2.sum(),
                         tpv_lost_eur=churn * affected.tpv.sum(),
                         extra_fees_eur=stay * affected.top_up.sum(),
                         contribution_change_from_leavers_eur=-churn * affected.cm2.sum(),
                         contribution_change_eur=uplift))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 3. Reprice BNPL for marketplaces
# ---------------------------------------------------------------------------
def bnpl_reprice(con, price_rise=0.003, shift_rates=(0.0, 0.25, 0.5)):
    """Marketplaces: BNPL price +0.3 percentage points.

    Some BNPL volume moves to cards (shoppers or merchants switch method); that
    volume then earns the marketplaces' 2025 card-and-wallet contribution per euro.
    """
    d = query(con, """
        SELECT CASE WHEN f.payment_method = 'bnpl' THEN 'bnpl' ELSE 'cards' END AS grp,
               SUM(f.tpv_eur) AS tpv,
               SUM(f.net_revenue_eur - f.processing_cost_eur - f.fraud_chargeback_loss_eur) AS cm1
        FROM fact_economics f JOIN merchants m ON m.merchant_id = f.merchant_id
        WHERE m.segment = 'Marketplaces' AND f.month >= '2025-01-01'
          AND f.payment_method IN ('bnpl', 'debit_card', 'credit_card', 'digital_wallet')
        GROUP BY grp""").set_index("grp")
    bnpl, cards = d.loc["bnpl"], d.loc["cards"]
    bnpl_bps, card_bps = bnpl.cm1 / bnpl.tpv, cards.cm1 / cards.tpv
    rows = []
    for s in shift_rates:
        kept = bnpl.tpv * (1 - s)
        new_cm1 = kept * (bnpl_bps + price_rise) + bnpl.tpv * s * card_bps
        rows.append(dict(bnpl_volume_moving_to_cards=s,
                         bnpl_contribution_bps_before=bnpl_bps * 1e4,
                         card_contribution_bps=card_bps * 1e4,
                         contribution_change_eur=new_cm1 - bnpl.cm1))
    return pd.DataFrame(rows)


def main():
    OUT.mkdir(exist_ok=True)
    con = connect()
    base = base_by_segment(con)

    grid, breakeven, e = enterprise_volume_vs_price(base)
    grid.to_csv(OUT / "scenario_enterprise_grid.csv")
    breakeven.to_csv(OUT / "scenario_enterprise_breakeven.csv", index=False)

    minfee = minimum_fee(con)
    minfee.to_csv(OUT / "scenario_minimum_fee.csv", index=False)

    bnpl = bnpl_reprice(con)
    bnpl.to_csv(OUT / "scenario_bnpl_reprice.csv", index=False)

    print("Base 2025 contribution by segment (EUR m):")
    print((base.cm2 / 1e6).round(2).to_string())
    print(f"\n1. Enterprise: net revenue {money(e.net_rev)}, contribution {money(e.cm2)}")
    print("   Contribution change (EUR m), rows = take-rate cut, columns = volume growth:")
    print((grid / 1e6).round(2).to_string())
    print("   Volume growth needed to stand still:")
    for r in breakeven.itertuples():
        print(f"     {r.take_rate_cut:.0%} cut -> +{r.volume_growth_needed:.1%} volume")
    print("\n2. Minimum monthly net revenue of EUR 250 (blended-pricing merchants):")
    print(minfee.round(2).to_string(index=False))
    print("\n3. Marketplaces BNPL +0.3pp:")
    print(bnpl.round(1).to_string(index=False))


if __name__ == "__main__":
    main()
