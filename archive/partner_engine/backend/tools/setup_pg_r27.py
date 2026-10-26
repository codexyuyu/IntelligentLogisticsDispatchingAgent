"""Explicit additive R27 warehouse operation standards schema; no automatic seeding."""
from __future__ import annotations
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description='R27 additive warehouse work schema (opt-in)')
    parser.add_argument('--create-tables', action='store_true')
    args = parser.parse_args()
    if not args.create_tables:
        parser.error('R27 migration requires --create-tables, database backup recommended')
    from app.adapters.persistence.pg_simulation_archive import _connection
    path = Path(__file__).resolve().parents[1] / 'migrations' / 'R27_pg_warehouse_operations_additive.sql'
    conn = _connection()
    try:
        conn.autocommit = True
        conn.execute(path.read_text(encoding='utf-8'), prepare=False)
    finally:
        conn.close()
    print('R27 作业标准表已创建（未导入数据，不改写任何旧业务记录）。')


if __name__ == '__main__':
    main()
