from __future__ import annotations

import unittest
import pandas as pd

from trade_engine import build_long_trade_plan
from utils import format_report, to_number


class FormatterTests(unittest.TestCase):
    def test_mixed_numeric_columns_do_not_crash(self):
        source = pd.DataFrame({
            "Asset": ["A", "B", "C", "D"],
            "Prezzo": [10.1234, None, "12.5", "—"],
            "Entry": [11.0, "N/D", None, 14],
            "Volume/Media": [1.234, "non disponibile", 0.9, None],
        })
        result = format_report(source)
        self.assertEqual(result.loc[0, "Prezzo"], 10.12)
        self.assertEqual(result.loc[2, "Prezzo"], 12.5)
        self.assertTrue(pd.isna(result.loc[3, "Prezzo"]))
        self.assertTrue(pd.isna(result.loc[1, "Entry"]))

    def test_to_number(self):
        self.assertEqual(to_number("12.4"), 12.4)
        self.assertIsNone(to_number("—"))
        self.assertEqual(to_number(None, 0.0), 0.0)


class TradePlanTests(unittest.TestCase):
    def test_valid_breakout_plan(self):
        plan = build_long_trade_plan(
            setup="🟢 Breakout confermato",
            confidence=95,
            close=110.0,
            candle_low=108.0,
            atr=2.0,
            breakout_level=109.0,
            next_resistance=120.0,
            volume_ratio=1.20,
            rsi=60.0,
        )
        self.assertTrue(plan.valid)
        self.assertEqual(plan.entry, 110.0)
        self.assertGreater(plan.tp1, plan.entry)
        self.assertLess(plan.stop_loss, plan.entry)
        self.assertGreaterEqual(plan.rr1, 2.0)

    def test_non_breakout_has_no_plan(self):
        plan = build_long_trade_plan(
            setup="⚪ Nessun setup",
            confidence=95,
            close=110.0,
            candle_low=108.0,
            atr=2.0,
            breakout_level=109.0,
            next_resistance=120.0,
            volume_ratio=1.20,
            rsi=60.0,
        )
        self.assertFalse(plan.valid)
        self.assertIsNone(plan.entry)


if __name__ == "__main__":
    unittest.main()

class TradeManagerTests(unittest.TestCase):
    def test_snapshot_profit_and_tp(self):
        from trade_manager import trade_snapshot
        trade={"entry":100,"stop_loss":95,"tp1":110,"tp2":120}
        snap=trade_snapshot(trade,111)
        self.assertGreater(snap["pnl_pct"],10)
        self.assertIn("TP1",snap["state"])
