"""Generate the synthetic data set for a fictional European payments business.

Everything here is made up. The patterns the analysis finds (falling enterprise
pricing, a growing share of thin-margin payment methods, a long tail of small
merchants that cost more to serve than they earn) were put into the generator on
purpose, so the analysis has something to find. The point of the project is the
method, not the numbers.

Output (data/):
  merchants.csv              one row per merchant
  pricing.csv                contract pricing per merchant and payment method, with effective dates
  payment_method_costs.csv   cost assumptions per payment method
  monthly_transactions.csv   merchant x month x payment method aggregates

Run:  python src/generate_data.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

SEED = 20251231
OUT = Path(__file__).resolve().parents[1] / "data"

MONTHS = pd.date_range("2024-01-01", "2025-12-01", freq="MS")
N_MONTHS = len(MONTHS)  # 24

METHODS = ["debit_card", "credit_card", "local_bank", "digital_wallet", "bnpl"]

# ---------------------------------------------------------------------------
# Segment assumptions
# ---------------------------------------------------------------------------
# n: merchants, size: median monthly TPV (EUR) at start, sigma: spread of merchant
# sizes (lognormal), growth: annual TPV growth, ticket: average ticket (EUR),
# xb: cross-border share of card and wallet TPV, loss: fraud and chargeback loss
# rate (% of card and wallet TPV), cts: cost to serve per merchant per month (EUR),
# pricing: interchange++ ("ic_plus") or blended.
SEGMENTS = {
    "Enterprise retail": dict(n=20, size=18e6, sigma=0.55, growth=0.28, ticket=65,
                              xb=0.15, loss=0.0001, cts=6000, pricing="ic_plus"),
    "Marketplaces": dict(n=30, size=2.5e6, sigma=0.70, growth=0.40, ticket=45,
                         xb=0.35, loss=0.0005, cts=2500, pricing="ic_plus"),
    "Travel & hospitality": dict(n=40, size=1.2e6, sigma=0.70, growth=0.10, ticket=320,
                                 xb=0.45, loss=0.0008, cts=1500, pricing="ic_plus"),
    "Digital subscriptions": dict(n=60, size=0.35e6, sigma=0.90, growth=0.18, ticket=14,
                                  xb=0.30, loss=0.0003, cts=400, pricing="blended"),
    "SMB retail": dict(n=400, size=25e3, sigma=1.10, growth=0.06, ticket=40,
                       xb=0.05, loss=0.0002, cts=250, pricing="blended"),
}

COUNTRY_WEIGHTS = {
    "Enterprise retail":     {"NL": .20, "DE": .25, "UK": .20, "FR": .15, "ES": .00, "Nordics": .00, "US": .20},
    "Marketplaces":          {"NL": .20, "DE": .20, "UK": .15, "FR": .10, "ES": .10, "Nordics": .05, "US": .20},
    "Travel & hospitality":  {"NL": .10, "DE": .15, "UK": .20, "FR": .15, "ES": .25, "Nordics": .05, "US": .10},
    "Digital subscriptions": {"NL": .15, "DE": .15, "UK": .20, "FR": .10, "ES": .05, "Nordics": .15, "US": .20},
    "SMB retail":            {"NL": .30, "DE": .20, "UK": .15, "FR": .10, "ES": .10, "Nordics": .10, "US": .05},
}

# Payment method mix at the start, by merchant country
# (debit, credit, local bank, wallet, BNPL)
COUNTRY_MIX = {
    "NL":      [.25, .10, .50, .12, .03],
    "DE":      [.30, .12, .25, .25, .08],
    "UK":      [.50, .25, .00, .22, .03],
    "FR":      [.55, .20, .05, .17, .03],
    "ES":      [.50, .20, .05, .22, .03],
    "Nordics": [.45, .15, .10, .27, .03],
    "US":      [.30, .45, .00, .22, .03],
}

# Multipliers on the mix, by segment
SEGMENT_MIX_ADJ = {
    "Enterprise retail":     [1.0, 1.0, 1.0, 1.0, 1.0],
    "Marketplaces":          [1.0, 1.0, 1.0, 1.2, 2.0],
    "Travel & hospitality":  [0.7, 2.2, 0.6, 0.8, 0.5],
    "Digital subscriptions": [1.1, 1.0, 0.4, 1.4, 0.0],
    "SMB retail":            [1.0, 0.9, 1.1, 1.0, 1.2],
}

# How each method's share drifts over the 24 months (multiplier reached at month 24)
MIX_TREND = [0.85, 0.85, 1.20, 1.55, 2.50]
MIX_TREND_MARKETPLACE_BNPL = 4.0

TICKET_MULT = {"debit_card": 0.9, "credit_card": 1.2, "local_bank": 1.3,
               "digital_wallet": 0.8, "bnpl": 2.2}

SEASONALITY = {
    # month 1..12 multipliers
    "Travel & hospitality": [0.75, 0.80, 0.95, 1.00, 1.10, 1.30, 1.45, 1.40, 1.05, 0.90, 0.75, 0.85],
    "Enterprise retail":    [0.90, 0.85, 0.92, 0.95, 0.97, 0.95, 0.95, 0.97, 0.98, 1.02, 1.20, 1.35],
    "SMB retail":           [0.92, 0.88, 0.95, 0.98, 1.00, 0.98, 0.95, 0.96, 0.99, 1.02, 1.12, 1.25],
}

# ---------------------------------------------------------------------------
# Payment method costs (fictional, simplified)
# ---------------------------------------------------------------------------
METHOD_COSTS = pd.DataFrame([
    # method, interchange + scheme % (domestic), (cross-border), scheme fixed per txn,
    # partner fee %, own processing cost per txn, carries fraud/chargeback loss
    ("debit_card",     0.0030, 0.0140, 0.00, 0.000, 0.040, 1),
    ("credit_card",    0.0055, 0.0170, 0.00, 0.000, 0.040, 1),
    ("local_bank",     0.0000, 0.0000, 0.06, 0.000, 0.030, 0),
    ("digital_wallet", 0.0045, 0.0150, 0.00, 0.000, 0.050, 1),
    ("bnpl",           0.0000, 0.0000, 0.00, 0.029, 0.060, 0),
], columns=["payment_method", "interchange_scheme_pct_domestic",
            "interchange_scheme_pct_cross_border", "scheme_fee_fixed_eur",
            "partner_fee_pct", "processing_cost_per_txn_eur", "carries_loss"])


def month_str(ts):
    return ts.strftime("%Y-%m-%d")


def build_merchants(rng):
    rows = []
    mid = 0
    for seg, p in SEGMENTS.items():
        countries = list(COUNTRY_WEIGHTS[seg])
        weights = np.array(list(COUNTRY_WEIGHTS[seg].values()))
        for _ in range(p["n"]):
            mid += 1
            # About 15% of non-enterprise merchants join during the period;
            # about 10% of SMB merchants leave during the period.
            onboard = 0
            if seg != "Enterprise retail" and rng.random() < 0.15:
                onboard = int(rng.integers(3, 20))
            churn = None
            if seg == "SMB retail" and rng.random() < 0.10:
                churn = int(rng.integers(max(onboard + 4, 6), 23))
            rows.append(dict(
                merchant_id=f"M{mid:04d}",
                segment=seg,
                country=rng.choice(countries, p=weights / weights.sum()),
                pricing_model=p["pricing"],
                start_month=month_str(MONTHS[onboard]),
                end_month=month_str(MONTHS[churn]) if churn is not None else None,
                base_monthly_tpv=float(p["size"] * rng.lognormal(0, p["sigma"])),
                cost_to_serve_eur_month=p["cts"],
            ))
    return pd.DataFrame(rows)


def build_pricing(rng, merchants):
    """Contract pricing per merchant and method, with effective dates.

    ic_plus: the merchant pays interchange and scheme fees at cost, plus a markup
             (pct_fee) and a fixed fee per transaction.
    blended: one all-in % (pct_fee) plus a fixed fee; interchange and scheme fees
             are our cost.
    Local bank payments carry a fixed fee only; BNPL a % fee (the BNPL partner
    fee is our cost under both models).
    """
    rows = []
    first, open_end = month_str(MONTHS[0]), "9999-12-01"
    for m in merchants.itertuples():
        seg = m.segment
        if m.pricing_model == "ic_plus":
            markup = {"Enterprise retail": rng.uniform(0.0012, 0.0020),
                      "Marketplaces": rng.uniform(0.0025, 0.0040),
                      "Travel & hospitality": rng.uniform(0.0035, 0.0050)}[seg]
            fixed = 0.03 if seg == "Enterprise retail" else 0.05
            terms = {
                "debit_card": (markup, fixed, 1), "credit_card": (markup, fixed, 1),
                "digital_wallet": (markup, fixed, 1),
                "local_bank": (0.0, round(rng.uniform(0.18, 0.25), 2), 0),
                "bnpl": (round(rng.uniform(0.030, 0.033), 4), 0.0, 0),
            }
        else:
            blended = rng.uniform(0.017, 0.022) if seg == "Digital subscriptions" else rng.uniform(0.016, 0.021)
            fixed = round(rng.uniform(0.10, 0.20), 2)
            terms = {
                "debit_card": (blended, fixed, 0), "credit_card": (blended, fixed, 0),
                "digital_wallet": (blended, fixed, 0),
                "local_bank": (0.0, 0.29, 0),
                "bnpl": (round(rng.uniform(0.036, 0.039), 4), 0.0, 0),
            }

        # Renewals in 2025: lower pricing in exchange for more volume
        reprice_month, factors = None, None
        if seg == "Enterprise retail" and rng.random() < 0.75:
            reprice_month = month_str(MONTHS[int(rng.integers(12, 21))])
            factors = dict(card=rng.uniform(0.50, 0.70), fixed=0.8, bnpl=-0.002)
        elif seg == "Marketplaces" and rng.random() < 0.25:
            reprice_month = month_str(MONTHS[int(rng.integers(12, 21))])
            factors = dict(card=0.8, fixed=1.0, bnpl=-0.002)

        for method, (pct, fix, passthrough) in terms.items():
            end = reprice_month or open_end
            rows.append(dict(merchant_id=m.merchant_id, payment_method=method,
                             valid_from=first, valid_to=end, pct_fee=round(pct, 5),
                             fixed_fee_eur=round(fix, 3), passes_through_interchange=passthrough))
            if reprice_month:
                if method in ("debit_card", "credit_card", "digital_wallet"):
                    new_pct, new_fix = pct * factors["card"], fix * factors["fixed"]
                elif method == "bnpl":
                    new_pct, new_fix = pct + factors["bnpl"], fix
                else:
                    new_pct, new_fix = pct, fix
                rows.append(dict(merchant_id=m.merchant_id, payment_method=method,
                                 valid_from=reprice_month, valid_to=open_end,
                                 pct_fee=round(new_pct, 5), fixed_fee_eur=round(new_fix, 3),
                                 passes_through_interchange=passthrough))
    return pd.DataFrame(rows)


def build_transactions(rng, merchants):
    rows = []
    for m in merchants.itertuples():
        p = SEGMENTS[m.segment]
        start = MONTHS.get_loc(pd.Timestamp(m.start_month))
        end = MONTHS.get_loc(pd.Timestamp(m.end_month)) if isinstance(m.end_month, str) else N_MONTHS
        base_mix = np.array(COUNTRY_MIX[m.country]) * np.array(SEGMENT_MIX_ADJ[m.segment])
        season = SEASONALITY.get(m.segment, [1.0] * 12)
        merchant_growth = p["growth"] + rng.normal(0, 0.06)
        merchant_xb = float(np.clip(p["xb"] + rng.normal(0, 0.07), 0.0, 0.8))
        for t in range(start, end):
            ramp = min(1.0, 0.35 + 0.13 * (t - start)) if start > 0 else 1.0  # new merchants ramp up
            tpv = (m.base_monthly_tpv * (1 + merchant_growth) ** (t / 12)
                   * season[MONTHS[t].month - 1] * ramp * rng.lognormal(0, 0.05))
            drift = t / (N_MONTHS - 1)
            trend = np.array(MIX_TREND, dtype=float)
            if m.segment == "Marketplaces":
                trend[4] = MIX_TREND_MARKETPLACE_BNPL
            mix = base_mix * (1 + (trend - 1) * drift) * rng.lognormal(0, 0.04, 5)
            mix = mix / mix.sum()
            for method, share in zip(METHODS, mix):
                if share <= 0:
                    continue
                m_tpv = tpv * share
                ticket = p["ticket"] * TICKET_MULT[method] * rng.lognormal(0, 0.03)
                txns = max(1, int(round(m_tpv / ticket)))
                xb = merchant_xb if method in ("debit_card", "credit_card", "digital_wallet") else 0.0
                loss_rate = p["loss"] * rng.lognormal(0, 0.35) if method in ("debit_card", "credit_card", "digital_wallet") else 0.0
                rows.append(dict(
                    merchant_id=m.merchant_id,
                    month=month_str(MONTHS[t]),
                    payment_method=method,
                    transactions=txns,
                    tpv_eur=round(m_tpv, 2),
                    cross_border_tpv_eur=round(m_tpv * xb, 2),
                    fraud_chargeback_loss_eur=round(m_tpv * loss_rate, 2),
                ))
    return pd.DataFrame(rows)


def main():
    rng = np.random.default_rng(SEED)
    OUT.mkdir(exist_ok=True)
    merchants = build_merchants(rng)
    pricing = build_pricing(rng, merchants)
    tx = build_transactions(rng, merchants)

    merchants.drop(columns=["base_monthly_tpv"]).to_csv(OUT / "merchants.csv", index=False)
    pricing.to_csv(OUT / "pricing.csv", index=False)
    METHOD_COSTS.to_csv(OUT / "payment_method_costs.csv", index=False)
    tx.to_csv(OUT / "monthly_transactions.csv", index=False)

    print(f"merchants: {len(merchants):,}  pricing rows: {len(pricing):,}  "
          f"transaction rows: {len(tx):,}  TPV: EUR {tx.tpv_eur.sum() / 1e9:,.2f}bn")


if __name__ == "__main__":
    main()
