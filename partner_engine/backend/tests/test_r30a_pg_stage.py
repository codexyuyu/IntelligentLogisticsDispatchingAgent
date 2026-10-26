"""R30-A: opt-in synthetic data, provenance, and unchanged PG-backed workflow."""
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
import csv
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.adapters.persistence.pg_routing_preview import BridgeInputError
from app.adapters.persistence.pg_r27_workflow import verified_snapshot
from tools.pg_r30a_bundle import export, validate_bundle, assemble, preview_generated, apply_bundle
from test_pg_routing_preview import sample


def one_wh():
    data = sample()
    data['vehicles'][1]['warehouse_code'] = 'WH001'
    data['nodes'] = [x for x in data['nodes'] if x['node_key'] != 'WH:WH002']
    data['distance_matrix'] = [x for x in data['distance_matrix']
        if x['from_node'] != 'WH:WH002' and x['to_node'] != 'WH:WH002']
    return data


def populated_candidate():
    base = one_wh()
    rows = assemble(base)
    ready = {**base,
        'r24': {k:[{**row, **({'version':1} if k in ('lots','orders','vehicles','resources','handoffs') else {})}
                   for row in rows[k]] for k in ('zones','lots','orders','vehicles','resources','handoffs')},
        'r27': {'installed':True,'operations':[{**row,'version':1} for row in rows['work_operations']]},
        'r30a': {'installed':True,'source_kind':'explicit_synthetic_demo'}}
    return ready


def test_export_and_rediscover_pg_generated_constraints(tmp_path):
    base=one_wh()
    directory=tmp_path/'demo'
    manifest=export(base,directory)
    reread, rows=validate_bundle(directory,base)
    assert reread == manifest
    assert manifest['counts']['orders'] == 2
    assert manifest['counts']['vehicles'] == 2
    assert manifest['counts']['work_operations'] == 4
    assert manifest['snapshot_adapters_validated'][0]['warehouse_operations'] == 4
    assert 'SYNTHETIC' in manifest['strict_warning']
    assert rows['work_operations'][0]['predecessor_code'] is None
    with pytest.raises(ValueError,match='must_be_empty'):
        export(base,directory)


def test_modified_csv_and_modified_pg_base_are_rejected(tmp_path):
    base=one_wh()
    directory=tmp_path/'bundle'
    export(base,directory)
    filename=directory/'orders.csv'
    filename.write_bytes(filename.read_bytes()+b'\n')
    with pytest.raises(ValueError,match='tampered'):
        validate_bundle(directory,base)
    filename.write_bytes(filename.read_bytes()[:-1])
    drift=one_wh()
    drift['orders'][0]['weight_kg']=45
    with pytest.raises(ValueError,match='base_data_changed'):
        validate_bundle(directory,drift)


def test_frozen_without_vehicle_rejected_and_no_fake_equipment():
    source=one_wh()
    source['orders'][0]['min_temp_c']=-20
    source['orders'][0]['max_temp_c']=-10
    with pytest.raises(BridgeInputError,match='no_original_vehicle_covers'):
        assemble(source)


def test_preflight_transforms_real_order_codes_but_marks_details_synthetic():
    data=populated_candidate()
    snap, meta=verified_snapshot(data, temperature_zone='chilled',
        travel_mode='straight_line_simulation',speed_kmh=30,max_orders=20,budget_ms=5000)
    assert {x.order_id for x in snap.orders}=={'ord_ORD001','ord_ORD002'}
    assert all(x.source.source_kind == 'simulation' for x in snap.orders)
    assert all(x.warehouse_id == 'wh_WH001' for x in snap.vehicles)
    assert len(snap.operations) == 4
    assert len(snap.resources) == 2
    assert meta['business_mode'] == 'verified_r24'


def test_existing_db_rows_refused_before_any_write(tmp_path):
    data=populated_candidate()
    directory=tmp_path/'demo'; export(one_wh(),directory)
    with pytest.raises(ValueError, match='existing_R24_R27'):
        apply_bundle(directory,data)


def test_pg_fact_drift_prevents_reusing_synthetic_input():
    data=populated_candidate()
    from tools.pg_r30a_bundle import base_fingerprint
    data['r30a']['base_digest_sha256']=base_fingerprint(data)
    data['orders'][0]['weight_kg'] += 1
    with pytest.raises(BridgeInputError, match='base_business_data_changed'):
        verified_snapshot(data,temperature_zone='chilled',travel_mode='straight_line_simulation',
            speed_kmh=30,max_orders=20,budget_ms=5000)


def test_provenance_and_r30a_status_endpoint_local_only(monkeypatch):
    client=TestClient(app)
    monkeypatch.delenv('PG_DEMO_ENABLED', raising=False)
    assert client.get('/local-pg/pg-preview/r30a/readiness').status_code == 503
    monkeypatch.setenv('PG_DEMO_ENABLED', '1')
    data=populated_candidate()
    with patch('app.api.routes.postgres_demo.load_view_data',return_value=data):
        response=client.get('/local-pg/pg-preview/r30a/readiness')
    assert response.status_code == 200
    report=response.json()
    assert report['complete_presence']
    assert report['provenance']['source_kind'] == 'explicit_synthetic_demo'
    assert 'synthetic' in report['provenance_warning']


def test_atomic_import_only_writes_extension_tables_and_provenance(tmp_path):
    base = one_wh()
    directory = tmp_path/'demo'
    manifest=export(base,directory)
    empty={**base,'r24':{k:[] for k in ('zones','lots','orders','vehicles','resources','handoffs')},
           'r27':{'installed':True,'operations':[]},'r30a':{'installed':False}}
    class Result:
        def __init__(self, value=None): self.value=value or {'inserted':'ok'}
        def fetchone(self): return self.value
    class Transaction:
        def __enter__(self): return self
        def __exit__(self, typ, val, tb): return False
    class Connection:
        def __init__(self):self.sql=[]
        def __enter__(self):return self
        def __exit__(self, typ, val, tb):return False
        def transaction(self): return Transaction()
        def execute(self, sql, parameters=None):
            self.sql.append(sql)
            if 'SELECT COUNT(*)' in sql: return Result({'n':0})
            return Result()
    connection = Connection()
    with patch('app.adapters.persistence.pg_simulation_archive._connection',return_value=connection):
        status=apply_bundle(directory,empty)
    assert status['database_mutated'] and not status['base_tables_mutated']
    statements='\n'.join(connection.sql).upper()
    assert 'INSERT INTO PUBLIC.PG_R24_ORDER_DETAILS' in statements
    assert 'INSERT INTO PUBLIC.PG_R27_WORK_OPERATIONS' in statements
    assert 'INSERT INTO PUBLIC.PG_R30A_DATA_PROVENANCE' in statements
    assert 'UPDATE PUBLIC.DELIVERY_ORDERS' not in statements
    assert 'DELETE FROM PUBLIC.ROUTES' not in statements


def test_unmarked_operator_rows_are_not_labeled_synthetic():
    data=populated_candidate()
    data['r30a']={'installed':False,'source_kind':'unmarked_operator_or_legacy_rows'}
    snap,_=verified_snapshot(data,temperature_zone='chilled',
        travel_mode='straight_line_simulation',speed_kmh=30,max_orders=20,budget_ms=5000)
    assert all(x.source.source_kind=='database' for x in snap.orders)
    assert all(x.source.source_ref=='r27-postgresql-operator-records' for x in snap.orders)


def test_invalid_marker_contents_fails_closed():
    from app.adapters.persistence.pg_r30a_provenance import load_provenance
    class Conn:
        def execute(self, sql):
            self.sql=sql
            return self
        def fetchone(self): return {'?column?':1}
        def fetchall(self): return [{'source_kind':'forged_real','warehouse_code':'WH001'}]
    with pytest.raises(ValueError,match='invalid_provenance'):
        load_provenance(Conn())
