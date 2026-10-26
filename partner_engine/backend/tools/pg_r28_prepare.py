"""Generate operator-editable, empty R24/R27 CSV worklists from real database codes.

Read-only database connection, no defaults for business values, no import/write SQL.
Generated local files are templates only; never interpreted as real observations.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from app.adapters.persistence.pg_routing_preview import load_view_data
from app.adapters.persistence.pg_r28_diagnostics import diagnostics
from tools.pg_r26_single_warehouse import inspect, _connection
from tools.r24_import_csv import FIELDS
from tools.pg_r27_import import COLUMNS


def operator_worklists(data: dict) -> dict[str, tuple[tuple[str, ...], list[dict]]]:
    """Only include missing codes; no warehouse/zone/volume/duration fabrication."""
    r24 = data.get('r24') or {}
    details = {r['order_code'] for r in r24.get('orders', [])}
    handoffs = {r['order_code'] for r in r24.get('handoffs', [])}
    vehicles = {r['vehicle_code'] for r in r24.get('vehicles', [])}
    loaded_by_final_step = {r['order_code'] for r in data.get('r27', {}).get('operations', []) if r['operation_kind'] == 'load'}
    def rows(kind, codes, idfield):
        return [{name: code if name == idfield else '' for name in FIELDS[kind]} for code in sorted(codes)]
    orders = {r['order_code'] for r in data['orders']}
    vehicle_codes = {r['vehicle_code'] for r in data['vehicles']}
    result = {
        'orders': (FIELDS['orders'], rows('orders', orders-details, 'order_code')),
        'vehicles': (FIELDS['vehicles'], rows('vehicles', vehicle_codes-vehicles, 'vehicle_code')),
        'handoffs': (FIELDS['handoffs'], rows('handoffs', orders-handoffs, 'order_code')),
    }
    # Warehouse operations require operator design (actual pick/stage/load steps).
    # Never synthesize fictitious operation IDs or predecessor chains.
    result['work_operations'] = (COLUMNS, [
        {name: code if name == 'order_code' else '' for name in COLUMNS}
        for code in sorted(orders - loaded_by_final_step)
    ])
    for kind in ('zones', 'lots', 'resources'):
        result[kind] = (FIELDS[kind], [])  # fully blank templates, no fictional stock/resources
    return result


def export_worklists(data: dict, directory: Path) -> dict:
    directory.mkdir(parents=True, exist_ok=True)
    if any(directory.iterdir()):
        raise ValueError('r28_output_directory_must_be_empty_do_not_overwrite_operator_data')
    counts = {}
    for kind, (headers, rows) in operator_worklists(data).items():
        with (directory / (kind + '.csv')).open('w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)
        counts[kind] = len(rows)
    return counts


def main():
    parser = argparse.ArgumentParser(description='R28 只读数据库诊断和空白补录清单')
    parser.add_argument('--output', type=Path, help='导出含真实编号、其余字段留空的 CSV；路径必须为空目录')
    args = parser.parse_args()
    data = load_view_data(include_r27=True)
    conn = _connection()
    try:
        conn.execute('SET TRANSACTION READ ONLY')
        warehouse = inspect(conn)
        conn.rollback()
    finally:
        conn.close()
    report = diagnostics(data, warehouse)
    if args.output is not None:
        report['operator_csv_rows'] = export_worklists(data, args.output)
        (args.output / 'READ_ME.txt').write_text(
            'R28 本地补录模板：仅编号源自实库，所有温区、库存、容积、时间、资源、工时均留空；不得作为实际数据直接导入。\n'
            '先备份数据库并验证，再使用 R24/R27 已有的校验和 INSERT ONLY 导入工具。\n'
            'work_operations.csv 每单只有一行待设计提示，不是完整作业计划；必须由业务人员补足全部真实 pick/stage/load 行、资源和前置依赖。\n'
            'WH002 迁移必须按 R26 单仓只读预检处理；若有历史 FK 阻挡，不要强行删除历史数据。\n',
            encoding='utf-8-sig')
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))


if __name__ == '__main__':
    main()
