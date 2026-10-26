"""Explicit opt-in setup for the R22 *separate demonstration table* only."""
from __future__ import annotations

import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description='R22 simulated route archive table setup')
    parser.add_argument('--create-demo-table', action='store_true', required=True,
                        help='explicit consent to create public.pg_simulation_previews')
    args = parser.parse_args()
    from app.adapters.persistence.pg_simulation_archive import _connection
    sql = (Path(__file__).resolve().parents[1] / 'sql' / 'pg_simulation_previews.sql').read_text(encoding='utf-8')
    with _connection() as conn:
        with conn.transaction():
            conn.execute(sql)
    print('R22 demo table public.pg_simulation_previews is ready; no dispatch_plans tables changed')


if __name__ == '__main__':
    main()
