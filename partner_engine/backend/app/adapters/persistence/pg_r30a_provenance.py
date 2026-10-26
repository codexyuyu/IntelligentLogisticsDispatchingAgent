"""Read-only source tagging for R30A synthetic demonstration extension records."""
from __future__ import annotations


def load_provenance(conn) -> dict:
    exists = conn.execute('''SELECT 1 FROM pg_catalog.pg_tables
        WHERE schemaname='public' AND tablename='pg_r30a_data_provenance' ''').fetchone()
    if not exists:
        return {'installed': False, 'source_kind': 'unmarked_operator_or_legacy_rows'}
    records = conn.execute('''SELECT source_kind, warehouse_code, base_digest_sha256,
        bundle_digest_sha256, created_at FROM public.pg_r30a_data_provenance''').fetchall()
    if len(records) != 1 or records[0]['source_kind'] != 'explicit_synthetic_demo' or records[0]['warehouse_code'] != 'WH001':
        raise ValueError('r30a_invalid_provenance_table_contents')
    return {'installed': True, 'source_kind': 'explicit_synthetic_demo',
            'warehouse_code': 'WH001', 'base_digest_sha256':records[0]['base_digest_sha256'],
            'bundle_digest_sha256':records[0]['bundle_digest_sha256'],
            'created_at':str(records[0]['created_at'])}
