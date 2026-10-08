import unittest
from datetime import date
from follower_insights import fb_daily_rows, ig_daily_row, monthly_report, summarize


class FollowerInsightsTests(unittest.TestCase):
    def test_fb_end_boundary_and_zero(self):
        rows = fb_daily_rows({'data': [{'name': 'page_daily_follows', 'values': [{'end_time': '2026-10-01T07:00:00+0000', 'value': 0}]}]})
        self.assertEqual(rows[0]['date'], '2026-09-30')
        self.assertEqual(rows[0]['follows'], 0)
        self.assertIsNone(rows[0]['unfollows'])

    def test_ig_breakdown_and_missing(self):
        payload = {'data': [{'name': 'follows_and_unfollows', 'total_value': {'breakdowns': [{'dimension_keys': ['follow_type'], 'results': [{'dimension_values': ['FOLLOWER'], 'value': 2}, {'dimension_values': ['NON_FOLLOWER'], 'value': 0}]}]}}]}
        self.assertEqual(ig_daily_row('2026-09-01', payload)['unfollows'], 0)
        self.assertIsNone(ig_daily_row('2026-09-01', {'data': []})['follows'])

    def test_incomplete_totals_do_not_fabricate_net(self):
        total = summarize([{'follows': 4, 'unfollows': 1}, {'follows': None, 'unfollows': None}])
        self.assertEqual(total['follows'], 4)
        self.assertIsNone(total['net'])
        self.assertFalse(total['is_complete'])

    def test_partial_month_compares_same_days_and_excludes_today(self):
        rows = [{'date': f'2026-{month:02d}-{day:02d}', 'platform': 'fb', 'follows': month, 'unfollows': 1} for month in (9, 10) for day in range(1, 9)]
        report = monthly_report({'rows': rows}, '2026-10', date(2026, 10, 8))['platforms']['fb']
        self.assertEqual(len(report['rows']), 7)
        self.assertEqual(report['previous']['expected_days'], 7)
        self.assertEqual(report['change']['follows'], 7)

    def test_partial_month_with_short_previous_month(self):
        rows = [{'date': f'2026-{month:02d}-{day:02d}', 'platform': 'fb', 'follows': 1, 'unfollows': 0} for month, count in [(2, 28), (3, 30)] for day in range(1, count + 1)]
        report = monthly_report({'rows': rows}, '2026-03', date(2026, 3, 31))['platforms']['fb']
        self.assertEqual(report['comparison_current']['expected_days'], 28)
        self.assertEqual(report['change']['follows'], 0)

    def test_future_month_is_rejected(self):
        with self.assertRaises(ValueError):
            monthly_report({}, '2026-11', date(2026, 10, 8))


if __name__ == '__main__':
    unittest.main()
