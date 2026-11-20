#!/usr/bin/env python3
"""Offline functional test for tools/collector.py.

Compiles the collector and exercises collect_scope() with stubbed HTTP so the
undefined-name defect (a NameError on `series` in the market-row loop) is caught
without any network access. Runs in CI as part of the checks.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import collector  # noqa: E402


class _StubNet:
    """Stub the three network helpers collector uses, with a tiny fixture set."""

    def __init__(self):
        self.series_records = [
            {"ticker": "KXGAS", "category": "Economics", "categories": ["Economics"],
             "tags": ["Gas"], "contract_terms_url": "ct", "contract_url": "cu"},
            {"ticker": "KXELEC", "category": "Elections", "categories": ["Elections"],
             "tags": ["Elections"], "contract_terms_url": "ct2", "contract_url": "cu2"},
            {"ticker": "KXOFFTOPIC", "category": "Sports", "categories": ["Sports"],
             "tags": ["Sports"], "contract_terms_url": None, "contract_url": None},
        ]
        self.events = [
            {"event_ticker": "KXGAS-26DEC31", "series_ticker": "KXGAS", "title": "Gas",
             "settlement_sources": ["AAA"],
             "markets": [{"ticker": "KXGAS-26DEC31Y", "title": "Yes", "status": "open",
                          "result": "", "yes_bid_dollars": "0.40", "yes_ask_dollars": "0.60",
                          "volume_fp": "10"}]},
            {"event_ticker": "KXELEC-26", "series_ticker": "KXELEC", "title": "Election",
             "settlement_sources": [],
             "markets": [{"ticker": "KXELEC-26Y", "title": "Election Yes", "status": "open"}]},
            # series with no official record -> must land in unmapped_series
            {"event_ticker": "KXMYSTERY-26", "series_ticker": "KXMYSTERY", "title": "Mystery",
             "markets": [{"ticker": "KXMYSTERY-26Y", "title": "Mystery Yes", "status": "open"}]},
            # in-catalogue but out-of-scope topic -> excluded
            {"event_ticker": "KXOFFTOPIC-26", "series_ticker": "KXOFFTOPIC", "title": "Sports",
             "markets": [{"ticker": "KXOFFTOPIC-26Y", "title": "Sports Yes", "status": "open"}]},
        ]

    def run(self):
        orig = (collector.load_series_index, collector.paginate)

        def fake_series(signer):
            return {s["ticker"]: s for s in self.series_records}

        def fake_paginate(url, key, signer=None, max_pages=30):
            return list(self.events)

        collector.load_series_index = fake_series
        collector.paginate = fake_paginate
        try:
            return collector.collect_scope(None)
        finally:
            collector.load_series_index, collector.paginate = orig


class CollectScopeTest(unittest.TestCase):
    def setUp(self):
        self.stub = _StubNet()

    def test_collect_scope_runs_and_classifies(self):
        result = self.stub.run()
        rows = result["markets_in_scope"]
        # both in-scope markets captured, catalogue/unmapped counted
        self.assertEqual(len(rows), 2, rows)
        topics = {r["series_ticker"]: r["topic"] for r in rows}
        self.assertEqual(topics, {"KXGAS": "gas", "KXELEC": "elections"})
        # series metadata was attached from the official series record
        gas = next(r for r in rows if r["series_ticker"] == "KXGAS")
        self.assertEqual(gas["series_category"], "Economics")
        self.assertEqual(gas["series_categories"], ["Economics"])
        self.assertEqual(gas["contract_terms_url"], "ct")
        self.assertEqual(gas["contract_url"], "cu")
        self.assertEqual(gas["settlement_sources"], ["AAA"])
        # catalogue reflects in-scope series; the unrecognised series is recorded
        # as unmapped (excluded, not guessed) and never reaches the market rows
        catalog = result["topic_catalog"]
        self.assertEqual(catalog["gas"]["series_in_catalog"], 1)
        self.assertIn("KXMYSTERY", result["unmapped_series"])
        self.assertIn("KXOFFTOPIC", result["unmapped_series"])
        self.assertNotIn("KXOFFTOPIC", {r["series_ticker"] for r in rows})


class CompileTest(unittest.TestCase):
    def test_collector_compiles(self):
        import py_compile
        py_compile.compile(str(ROOT / "tools" / "collector.py"), doraise=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
