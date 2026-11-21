"""Offline executor checks. Mocked signer/post only; never places Kalshi orders."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
spec = importlib.util.spec_from_file_location('executor_under_test', ROOT / 'tools/execute_strategy.py')
executor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(executor)


class ExecutorTest(unittest.TestCase):
    def run_plan(self, orders, limits=None, *, live=False):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            (data / 'snapshot.json').write_text(json.dumps({'markets': [{'market_ticker': o['ticker']} for o in orders]}))
            (data / 'strategy_plan.json').write_text(json.dumps({'orders': orders, 'run_limits': limits or {}}))
            env = {'KALSHI_TRADING_ENABLED': '1', 'KALSHI_MAX_NOTIONAL_USD': '25'}
            with patch.object(executor, 'DATA', data), patch.object(executor, 'DRY_RUN', not live), \
                    patch.object(executor, 'signer_from_env', return_value=object()), \
                    patch.object(executor, 'post_order', return_value={'ok': True, 'http_status': 201}) as post, \
                    patch.dict(os.environ, env, clear=True):
                self.assertEqual(executor.main(), 0)
                result = json.loads((data / 'executions.json').read_text())
                return result, post.call_args_list

    def test_no_uses_yes_book_price_and_accounts_for_no_cost(self):
        orders = [{'ticker': 'NO1', 'side': 'no', 'count': '10.00', 'price': '0.1000'},
                  {'ticker': 'NO2', 'side': 'no', 'count': '10.00', 'price': '0.1000'},
                  {'ticker': 'NO3', 'side': 'no', 'count': '10.00', 'price': '0.1000'}]
        result, calls = self.run_plan(orders, {'max_notional_usd': 25}, live=True)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0].args[1]['side'], 'ask')
        self.assertEqual(calls[0].args[1]['price'], '0.1000')
        self.assertEqual(result['planned_notional_usd'], 18)
        self.assertIn('cap', result['results'][2]['skipped'])

    def test_yes_and_no_and_plan_cannot_raise_cap(self):
        orders = [{'ticker': 'YES', 'side': 'yes', 'count': 10, 'price': '0.4000'},
                  {'ticker': 'NO', 'side': 'no', 'count': 10, 'price': '0.4000'}]
        result, calls = self.run_plan(orders, {'max_notional_usd': 1000})
        self.assertEqual(calls, [])
        self.assertEqual(result['run_notional_cap_usd'], 25)
        self.assertEqual(result['planned_notional_usd'], 10)
        self.assertEqual(result['results'][0]['request']['side'], 'bid')
        self.assertEqual(result['results'][1]['request']['price'], '0.4000')

    def test_zero_order_limit_is_respected(self):
        result, calls = self.run_plan([{'ticker': 'X', 'side': 'yes', 'count': 1, 'price': '0.5'}], {'max_orders_per_run': 0}, live=True)
        self.assertEqual(calls, [])
        self.assertIn('max_orders', result['results'][0]['skipped'])

    def test_invalid_values_fail_closed(self):
        orders = [{'ticker': 'A', 'side': 'bad', 'count': 1, 'price': '0.5'},
                  {'ticker': 'B', 'side': 'yes', 'count': 'NaN', 'price': '0.5'},
                  {'ticker': 'C', 'side': 'yes', 'count': '1.001', 'price': '0.5'},
                  {'ticker': 'D', 'side': 'no', 'count': 1, 'price': '1.0001'},
                  {'ticker': 'E', 'side': 'yes', 'count': 1, 'price': '0.12345'}]
        result, calls = self.run_plan(orders, live=True)
        self.assertEqual(calls, [])
        self.assertTrue(all('skipped' in row for row in result['results']))


if __name__ == '__main__':
    unittest.main()
