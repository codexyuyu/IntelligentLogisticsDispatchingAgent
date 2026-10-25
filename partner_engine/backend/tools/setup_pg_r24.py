"""Explicit opt-in forward-only R24 additive schema installation. Never seeds real data."""
from __future__ import annotations

import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description='R24 增量表创建：只有显式传入 --create-tables 才会执行')
    parser.add_argument('--create-tables', action='store_true')
    args = parser.parse_args()
    if not args.create_tables:
        parser.error('缺少 --create-tables；默认不修改数据库')
    from app.adapters.persistence.pg_simulation_archive import _connection
    source = Path(__file__).resolve().parents[1] / 'migrations' / 'R24_pg_coldchain_additive.sql'
    sql = source.read_text(encoding='utf-8')
    # SQL contains its own BEGIN / COMMIT, no destructive or seed statements.
    conn = _connection()
    try:
        conn.autocommit = True
        conn.execute(sql, prepare=False)
    finally:
        conn.close()
    print('R24 增量表已执行；原业务数据未修改，扩展业务字段尚需人工录入。')


if __name__ == '__main__':
    main()
