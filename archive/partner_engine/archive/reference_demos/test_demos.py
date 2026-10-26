from copy import deepcopy
import unittest
import warehouse
import transport
import exception_replan
from validation import warehouse_errors, transport_errors


class DemoTests(unittest.TestCase):
    def test_warehouse_valid(self):
        tasks = warehouse.scenario()
        self.assertEqual(warehouse_errors(tasks, warehouse.solve(tasks)), [])

    def test_impossible_warehouse_deadline(self):
        tasks = warehouse.scenario()
        tasks[0]['deadline'] = 2
        plan = warehouse.solve(tasks)
        self.assertEqual(plan['status'], 'INFEASIBLE')
        self.assertTrue(warehouse_errors(tasks, plan))

    def test_omitted_task_rejected(self):
        tasks = warehouse.scenario()
        plan = warehouse.solve(tasks)
        plan['tasks'].pop()
        self.assertIn('task_coverage', warehouse_errors(tasks, plan))

    def test_changed_frozen_fact_rejected(self):
        tasks = warehouse.scenario()
        plan = warehouse.solve(tasks)
        frozen = deepcopy(plan['tasks'][:1])
        plan['tasks'][0]['end'] += 1
        self.assertIn('frozen:unload-A', warehouse_errors(tasks, plan, frozen=frozen))

    def test_transport_valid(self):
        data = transport.scenario()
        self.assertEqual(transport_errors(data, transport.solve(data)), [])

    def test_missing_temperature_vehicle(self):
        data = transport.scenario()
        data['temperatures'][1] = 'unsupported'
        self.assertEqual(transport.solve(data)['status'], 'INFEASIBLE_INPUT')

    def test_over_capacity_has_no_plan(self):
        data = transport.scenario()
        data['demands'][1] = 99
        self.assertEqual(transport.solve(data)['status'], 'NO_SOLUTION_FOUND')

    def test_impossible_transport_window(self):
        data = transport.scenario()
        data['windows'][1] = [0, 0]
        self.assertEqual(transport.solve(data)['status'], 'NO_SOLUTION_FOUND')

    def test_validator_catches_wrong_temperature_and_capacity(self):
        data = transport.scenario()
        plan = transport.solve(data)
        data['vehicles'][0].update(capacity=1, temperature='frozen')
        errors = transport_errors(data, plan)
        self.assertIn('capacity', errors)
        self.assertIn('temperature', errors)

    def test_forged_travel_time(self):
        data = transport.scenario()
        plan = transport.solve(data)
        plan['routes'][0]['stops'][1]['time'] = 0
        self.assertIn('travel_time', transport_errors(data, plan))

    def test_fault_replan_preserves_completed_work_and_blocks_forgery(self):
        result = exception_replan.run()
        self.assertEqual(result['validation_errors'], [])
        self.assertTrue(result['rejected_candidate_errors'])
        after = {t['id']: t for t in result['after']['tasks']}
        for row in result['frozen']:
            self.assertEqual(after[row['id']], row)
        self.assertGreaterEqual(after['load-A']['start'], 10)


if __name__ == '__main__':
    unittest.main()
