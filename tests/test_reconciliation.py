"""Reconciliation checks: the economics model must tie back to the raw data.

Run:  pytest
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from db import connect, query  # noqa: E402


@pytest.fixture(scope="module")
def con():
    return connect()


def scalar(con, sql):
    return query(con, sql).iloc[0, 0]


def test_every_transaction_row_matches_exactly_one_price(con):
    # A gap or overlap in pricing dates would drop or double-count volume
    raw = scalar(con, "SELECT COUNT(*) FROM monthly_transactions")
    modelled = scalar(con, "SELECT COUNT(*) FROM fact_economics")
    assert raw == modelled


def test_tpv_ties_to_raw(con):
    raw = scalar(con, "SELECT SUM(tpv_eur) FROM monthly_transactions")
    assert scalar(con, "SELECT SUM(tpv_eur) FROM fact_economics") == pytest.approx(raw)
    assert scalar(con, "SELECT SUM(tpv_eur) FROM merchant_month") == pytest.approx(raw)


def test_pricing_periods_do_not_overlap(con):
    overlaps = scalar(con, """
        SELECT COUNT(*) FROM pricing a JOIN pricing b
          ON a.merchant_id = b.merchant_id AND a.payment_method = b.payment_method
         AND a.rowid < b.rowid
         AND a.valid_from < b.valid_to AND b.valid_from < a.valid_to""")
    assert overlaps == 0


def test_revenue_waterfall_adds_up(con):
    d = query(con, """
        SELECT SUM(gross_revenue_eur) g, SUM(pass_through_cost_eur) p, SUM(net_revenue_eur) n,
               SUM(transaction_costs_eur) t, SUM(contribution_1_eur) c1,
               SUM(cost_to_serve_eur) s, SUM(contribution_2_eur) c2
        FROM merchant_month""").iloc[0]
    assert d.g - d.p == pytest.approx(d.n)
    assert d.n - d.t == pytest.approx(d.c1)
    assert d.c1 - d.s == pytest.approx(d.c2)


def test_ic_plus_cards_earn_only_markup_and_fixed_fee(con):
    # Interchange++: interchange and scheme fees are billed at cost, so net revenue
    # must equal markup x TPV + fixed fee x transactions
    d = query(con, """
        SELECT f.net_revenue_eur, f.tpv_eur * p.pct_fee + f.transactions * p.fixed_fee_eur AS expected
        FROM fact_economics f
        JOIN pricing p ON p.merchant_id = f.merchant_id AND p.payment_method = f.payment_method
                      AND f.month >= p.valid_from AND f.month < p.valid_to
        WHERE p.passes_through_interchange = 1""")
    assert len(d) > 0
    pd.testing.assert_series_equal(d.net_revenue_eur, d.expected, check_names=False)


def test_cost_to_serve_charged_once_per_active_merchant_month(con):
    expected = scalar(con, """
        SELECT SUM(m.cost_to_serve_eur_month)
        FROM (SELECT DISTINCT merchant_id, month FROM monthly_transactions) t
        JOIN merchants m ON m.merchant_id = t.merchant_id""")
    assert scalar(con, "SELECT SUM(cost_to_serve_eur) FROM merchant_month") == pytest.approx(expected)
