"""R28 fact-completeness report and safe single-depot migration preflight.

No synthetic values; all reported missing codes are explicit database gaps.
"""
from __future__ import annotations

from app.adapters.persistence.pg_r27_workflow import readiness as r27_readiness


def diagnostics(data: dict, warehouse_report: dict) -> dict:
    current = r27_readiness(data)
    statuses = []
    if not current['single_warehouse']:
        statuses.append({'stage': 'single_depot', 'ready': False,
                         'action': 'review_R26_WH002_FK_preflight_and_backup_before_explicit_migration'})
    else:
        statuses.append({'stage': 'single_depot', 'ready': True, 'action': 'none'})
    statuses.append({'stage': 'r24_business_facts', 'ready': current['r24_reference_data_present']
                     and current['r24_tables_installed']
                     and all(not current['missing'][k] for k in ('order_details', 'vehicle_details', 'dock_handoffs')),
                     'action': 'fill_R24_CSV_with_actual_volumes_lots_shifts_and_handoffs'})
    statuses.append({'stage': 'r27_work_standards', 'ready': current['r27_table_installed']
                     and not current['missing']['work_operations']
                     and not current['missing']['loading_operations'],
                     'action': 'fill_R27_CSV_with_observed_task_durations_and_dependencies'})
    report = {
        'mode': 'r28_readonly_fact_diagnostics', 'database_mutated': False,
        'warehouse': warehouse_report, 'business': current,
        'r29_historical_fk_warehouse_retained': bool(data.get('r29_active_depot')),
        'r29_active_business_warehouse_codes': ['WH001'] if data.get('r29_active_depot') else None,
        'stages': statuses, 'ready_to_try_verified_solver': current['complete_presence'],
        'disclaimer': 'presence_only_no_operational_approval; actual_solution_still_requires_full_validation',
    }
    return report
