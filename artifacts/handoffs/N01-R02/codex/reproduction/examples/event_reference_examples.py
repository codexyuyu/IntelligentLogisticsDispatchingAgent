"""Bounded normative EntityRef examples, not domain classes or an event service.

The fixture wrapper contains a real-shaped ScenarioInput and earlier RegionRef
values. It is harness data, not a newly introduced business contract. All target
rules are read from the current normative decision annex, never the outline.
"""
import copy
from uuid import NAMESPACE_URL, uuid5


class DesignRejected(ValueError):
    """A named design predicate rejected an input."""


def at_path(value, path):
    for key in path.split('.'):
        value = value[key]
    return value


def structural(parse, name, value):
    try:
        parse(name, value)
    except ValueError as exc:
        raise DesignRejected('structural ' + name + ': ' + str(exc)) from exc


def fact_index(context, parse, spec):
    """Index typed records from this selected fact snapshot, not a live store."""
    input_ = context['scenario_input']
    structural(parse, 'ScenarioInput', input_)
    snapshot = input_['snapshot']
    rows = [('Order', snapshot['orders']), ('Cargo', snapshot['cargo']),
            ('Vehicle', snapshot['vehicles']), ('Driver', snapshot['drivers']),
            ('TransportTask', input_['transport_tasks']),
            ('WarehouseTask', input_['warehouse_tasks'])]
    rows += [(name, snapshot['resources'][collection]) for name, collection in
             [('Warehouse', 'warehouses'), ('WarehouseZone', 'zones'),
              ('StorageLocation', 'locations'), ('Dock', 'docks'),
              ('Worker', 'workers'), ('Equipment', 'equipment')]]
    kind_by_type = {r['type']: kind for kind, r in spec['entity_ref_targets'].items()
                    if r['category'] == 'entity'}
    index = {}
    for name, collection in rows:
        for value in collection:
            structural(parse, name, value)
            key = (kind_by_type[name], value['id'])
            if key in index:
                raise DesignRejected('duplicate typed fact identity')
            index[key] = value
    return index


def validate_event_reference(payload, context, parse, spec):
    """Check current-snapshot binding and the exact normative event mapping."""
    structural(parse, 'EventPayload', payload)
    mapping = spec['event_entity_ref_mapping'][payload['kind']]
    ref = payload['entity_ref']
    if ref['kind'] not in mapping['allowed_kinds']:
        raise DesignRejected('event target kind is not allowed')
    target = mapping['target']
    index = fact_index(context, parse, spec)
    snapshot = context['scenario_input']['snapshot']
    selected_id = at_path(payload, target['id_path'])
    if ref['id'] != selected_id:
        raise DesignRejected('entity_ref.id differs from mapped target id')
    source = target['source']
    if source in {'entity', 'resource_ref'}:
        if source == 'resource_ref':
            if ref != payload['resource_ref']:
                raise DesignRejected('entity_ref differs from complete resource_ref')
            expected_type = target['types_by_kind'][ref['kind']]
        else:
            expected_type = target['type']
        metadata = spec['entity_ref_targets'][ref['kind']]
        if metadata['type'] != expected_type:
            raise DesignRejected('mapping type differs from normative target metadata')
        fact = index.get((ref['kind'], selected_id))
        if fact is None:
            raise DesignRejected('target does not exist in selected fact snapshot')
        if target['revision'] != 'row_version_if_present':
            raise DesignRejected('unsupported entity revision policy')
        if ref['revision'] is not None and ref['revision'] != fact[metadata['revision_field']]:
            raise DesignRejected('reference revision differs from fact row_version')
    elif source == 'snapshot_matrix':
        if target['revision'] != 'matrix_version_required':
            raise DesignRejected('unsupported matrix revision policy')
        matches = [m for m in snapshot['matrices'] if m['id'] == selected_id]
        if len(matches) != 1:
            raise DesignRejected('one selected snapshot matrix is required')
        matrix = matches[0]
        if ref['revision'] is None or ref['revision'] != matrix['version']:
            raise DesignRejected('matrix revision must equal selected matrix version')
        arcs = payload['arc_refs']
        pairs = [(a['from_node_id'], a['to_node_id']) for a in arcs]
        if not pairs or len(pairs) != len(set(pairs)) or any(a == b for a, b in pairs):
            raise DesignRejected('nonempty unique directed nonself arcs required')
        nodes = set(matrix['node_ids'])
        if any(a not in nodes or b not in nodes for a, b in pairs):
            raise DesignRejected('every arc must belong to the one selected matrix')
        if payload['new_matrix_version'] <= ref['revision']:
            raise DesignRejected('new matrix version must strictly advance')
        if payload['closure']:
            if payload['travel_multiplier'] is not None:
                raise DesignRejected('closure requires null multiplier')
        elif payload['travel_multiplier'] is None:
            raise DesignRejected('open disruption requires a positive Rational')
    elif source == 'inline_region':
        if target['revision'] != 'null_required' or ref['revision'] is not None:
            raise DesignRejected('inline region has no revision and requires null')
        region = payload['region_ref']
        nodes = region['node_ids']
        if not nodes or len(nodes) != len(set(nodes)):
            raise DesignRejected('region nodes must be nonempty and unique')
        node_set = set(nodes)
        matrix_union = {n for m in snapshot['matrices'] for n in m['node_ids']}
        if not node_set <= matrix_union:
            raise DesignRejected('region node is absent from scene matrix union')
        for previous in context['prior_region_refs']:
            structural(parse, 'RegionRef', previous)
            if previous['region_id'] == region['region_id'] and set(previous['node_ids']) != node_set:
                raise DesignRejected('same region_id must preserve the same node set')
        affected = [m for m in snapshot['matrices'] if len(node_set.intersection(m['node_ids'])) >= 2]
        if any(payload['new_matrix_version'] <= m['version'] for m in affected):
            raise DesignRejected('new version must advance every affected matrix')
    else:
        raise DesignRejected('unsupported normative target source')
    return True


def make_context(parse, spec, digest, epoch):
    """Use complete named record shapes and stable UUID5 fixture identities."""
    uid = lambda label: str(uuid5(NAMESPACE_URL, 'logistics:N01-R02:design:' + label))
    actor = uid('actor')
    def entity(label, status, **fields):
        return dict(id=uid(label), status=status, created_at=epoch, updated_at=epoch,
                    row_version=3, schema_version='2.0.0', created_by=actor, **fields)
    nodes = [uid('node-' + str(i)) for i in range(1, 7)]
    cal = dict(epoch_utc=epoch, intervals=[dict(start_s=0, end_s=100, available_units=1)], version=3)
    window = dict(earliest_s=0, latest_s=100)
    order = entity('order', 'accepted', external_ref='N01-R02-design-order',
                   pickup_node_id=nodes[0], delivery_node_id=nodes[1],
                   cargo_ids=[uid('cargo')], pickup_window=window, delivery_window=window,
                   service_s=1, soft_due_at_s=None, must_serve=True, priority=1)
    cargo = entity('cargo', 'registered', order_id=uid('order'),
                   cargo_type='design_fixture_unvalidated_cargo_type', quantity_units=1,
                   weight_g=100, volume_cm3=100, min_temp_decic=0, max_temp_decic=100,
                   max_exposure_s=100, batch_ref='N01-R02-design-batch')
    driver = entity('driver', 'active', code='N01-R02-D1', qualifications=[],
                    shift=window, max_drive_s=100, max_work_s=100)
    vehicle = entity('vehicle', 'available', code='N01-R02-V1', capacity_weight_g=1000,
                     capacity_volume_cm3=1000, setpoint_decic=50, allowed_cargo_types=[],
                     start_node_id=nodes[0], end_node_id=nodes[1], calendar=cal,
                     driver_id=driver['id'], fixed_cost_cents=1, rate_cents_per_km=1)
    warehouse = entity('warehouse', 'active', code='N01-R02-W1', name='Design Warehouse',
                       node_id=nodes[0], timezone='UTC', calendar=cal)
    zone = entity('zone', 'active', warehouse_id=warehouse['id'], code='N01-R02-Z1',
                  setpoint_decic=50, capacity_weight_g=1000, capacity_volume_cm3=1000,
                  allowed_cargo_types=[])
    location = entity('location', 'available', zone_id=zone['id'], code='N01-R02-L1',
                      capacity_weight_g=1000, capacity_volume_cm3=1000, calendar=cal)
    dock = entity('dock', 'available', warehouse_id=warehouse['id'], code='N01-R02-DO1',
                  supported_operations=[], allowed_zone_ids=[zone['id']], calendar=cal)
    worker = entity('worker', 'available', warehouse_id=warehouse['id'], skills=[],
                    allowed_zone_ids=[zone['id']], calendar=cal, pool_id=None)
    equipment = entity('equipment', 'available', warehouse_id=warehouse['id'], kind='handling',
                       quantity_capacity=2, allowed_zone_ids=[zone['id']], calendar=cal)
    transport = entity('transport-task', 'pending', order_id=order['id'], leg_no=1,
                       pickup_node_id=nodes[0], delivery_node_id=nodes[1], cargo_ids=[cargo['id']],
                       predecessor_ids=[], service_s=1)
    def matrix(label, matrix_nodes, version):
        values = [[0 if i == j else 10 for j in range(len(matrix_nodes))] for i in range(len(matrix_nodes))]
        value = dict(id=uid(label), version=version, node_ids=matrix_nodes,
                     distance_m=values, travel_s=copy.deepcopy(values), source='N01-R02 synthetic design fixture',
                     observed_at=epoch, hash='0' * 64)
        value['hash'] = digest({k: v for k, v in value.items() if k != 'hash'})
        return value
    matrices = [matrix('matrix-1', nodes[:3], 3), matrix('matrix-2', nodes[3:], 7)]
    resources = dict(warehouses=[warehouse], zones=[zone], locations=[location], docks=[dock],
                     workers=[worker], equipment=[equipment], calendars=[])
    for record in [vehicle, warehouse, location, dock, worker, equipment]:
        resources['calendars'].append(dict(resource_id=record['id'], source_calendar=copy.deepcopy(cal),
                                          source_hash=digest(cal), calendar=copy.deepcopy(cal)))
    facts = [('Order', order), ('Cargo', cargo), ('Driver', driver), ('Vehicle', vehicle),
             ('Warehouse', warehouse), ('WarehouseZone', zone), ('StorageLocation', location),
             ('Dock', dock), ('Worker', worker), ('Equipment', equipment), ('TransportTask', transport)]
    kind_by_type = {v['type']: k for k, v in spec['entity_ref_targets'].items() if v['category'] == 'entity'}
    snapshot = dict(id=uid('snapshot'),
                    scope=dict(order_ids=[order['id']], warehouse_ids=[warehouse['id']], vehicle_ids=[vehicle['id']], epoch_utc=epoch, horizon_s=100),
                    orders=[order], cargo=[cargo], vehicles=[vehicle], drivers=[driver], resources=resources,
                    inventory=[], revisions=[dict(entity_ref=dict(kind=kind_by_type[n], id=v['id'], revision=v['row_version']), row_version=v['row_version']) for n, v in facts],
                    matrices=matrices, hash='0' * 64)
    snapshot['hash'] = digest({k: v for k, v in snapshot.items() if k != 'hash'})
    region = dict(region_id=uid('region'), node_ids=[nodes[0], nodes[1], nodes[3], nodes[4]])
    context = dict(scenario_input=dict(snapshot=snapshot, transport_tasks=[transport], warehouse_tasks=[]), prior_region_refs=[region])
    structural(parse, 'ScenarioInput', context['scenario_input'])
    structural(parse, 'RegionRef', region)
    return context, nodes, uid


def run_examples(check, parse, spec, digest, patch, epoch):
    """Record each actual acceptance/rejection; unexpected exceptions always fail."""
    cases = []
    def exercise(label, operation, expected=True, payload=None, context_name='base'):
        try:
            operation()
            accepted, reason, unexpected = True, 'accepted by bounded design predicate', False
        except (DesignRejected, ValueError) as exc:
            accepted, reason, unexpected = False, str(exc), False
        except Exception as exc:
            accepted, reason, unexpected = None, type(exc).__name__ + ': ' + str(exc), True
        matches = not unexpected and accepted == expected
        row = dict(name=label, expected_accepted=expected, accepted=accepted,
                   matches_expected=matches, reason=reason, context=context_name)
        if payload is not None:
            row['payload'] = copy.deepcopy(payload)
        cases.append(row)
        check('N01-R02 ' + label, lambda result=matches: result)

    enum = next(r for r in spec['types'] if r['name'] == 'EntityKind')
    exercise('EntityKind is complete normative enum, not existing leaf',
             lambda: require(enum['kind'] == 'enum' and bool(enum['members']) and len(set(enum['members'].values())) == len(enum['members'])))
    exercise('EntityRef is an explicit closed record', lambda: require(next(r for r in spec['types'] if r['name'] == 'EntityRef')['fields'] == dict(kind='EntityKind', id='UUID', revision='NonNegativeInt?')))
    exercise('target catalogue covers every normative enum value', lambda: require(set(enum['members'].values()) == set(spec['entity_ref_targets'])))
    uid = lambda label: str(uuid5(NAMESPACE_URL, 'logistics:N01-R02:design:' + label))
    for member, value in enum['members'].items():
        exercise('normative member ' + member + '=' + value + ' parses', lambda v=value: parse('EntityRef', dict(kind=v, id=uid('enum-target'), revision=None)))
    exercise('driver reference parses using normative enum', lambda: parse('EntityRef', dict(kind='driver', id=uid('driver'), revision=3)))
    for label, ref in [('unknown kind', dict(kind='unregistered_entity_kind', id=uid('enum-target'), revision=0)),
                       ('case-changed kind', dict(kind='DRIVER', id=uid('driver'), revision=0)),
                       ('missing revision', dict(kind='driver', id=uid('driver'))),
                       ('negative revision', dict(kind='driver', id=uid('driver'), revision=-1)),
                       ('boolean revision', dict(kind='driver', id=uid('driver'), revision=True)),
                       ('extra reference field', dict(kind='driver', id=uid('driver'), revision=0, live=True))]:
        exercise('EntityRef rejects ' + label, lambda r=ref: parse('EntityRef', r), False)
    context, nodes, uid = make_context(parse, spec, digest, epoch)
    index = fact_index(context, parse, spec)
    def ref(kind):
        matching = [v for (k, _), v in index.items() if k == kind]
        if len(matching) != 1:
            raise ValueError('one fixture fact required for kind ' + kind)
        return dict(kind=kind, id=matching[0]['id'], revision=matching[0]['row_version'])
    def payload(kind, entity_ref, **fields):
        return dict(kind=kind, entity_ref=entity_ref, effective_at_s=20, reason='N01-R02 design reference check', **fields)
    m1, m2 = context['scenario_input']['snapshot']['matrices']
    region = context['prior_region_refs'][0]
    examples = {
        'vehicle_failure': payload('vehicle_failure', ref('vehicle'), vehicle_id=ref('vehicle')['id'], location=dict(kind='at_node', node_id=nodes[0]), unavailable_until_s=90, cargo_condition='intact'),
        'transport_delay': payload('transport_delay', ref('transport_task'), transport_task_id=ref('transport_task')['id'], additional_seconds=10),
        'traffic_disruption': payload('traffic_disruption', dict(kind='travel_matrix', id=m1['id'], revision=m1['version']), arc_refs=[dict(from_node_id=nodes[0], to_node_id=nodes[1])], closure=True, travel_multiplier=None, new_matrix_version=4),
        'weather_change': payload('weather_change', dict(kind='region', id=region['region_id'], revision=None), region_ref=copy.deepcopy(region), profile='rain', travel_multiplier=dict(numerator=3, denominator=2), new_matrix_version=8),
        'cargo_anomaly': payload('cargo_anomaly', ref('cargo'), cargo_id=ref('cargo')['id'], condition='damaged', quantity_units=1, measured_temp_decic=None),
        'order_cancellation': payload('order_cancellation', ref('order'), order_id=ref('order')['id'], disposition_policy='return_to_origin'),
        'demand_increase': payload('demand_increase', ref('order'), order_id=ref('order')['id'], delta_quantity=1, delta_weight_g=100, delta_volume_cm3=100),
        'demand_decrease': payload('demand_decrease', ref('order'), order_id=ref('order')['id'], delta_quantity=1, delta_weight_g=100, delta_volume_cm3=100),
        'equipment_failure': payload('equipment_failure', ref('equipment'), equipment_id=ref('equipment')['id'], unavailable_until_s=90, remaining_capacity_units=0),
        'warehouse_resource_unavailable': payload('warehouse_resource_unavailable', ref('worker'), resource_ref=ref('worker'), unavailable_window=dict(earliest_s=20, latest_s=60), remaining_capacity_units=0),
    }
    exercise('event samples cover every normative event variant', lambda: require(set(examples) == set(spec['event_entity_ref_mapping']) == set(next(r for r in spec['types'] if r['name'] == 'EventPayload')['variants'])))
    exercise('complete real-shaped fact ScenarioInput parses', lambda: parse('ScenarioInput', context['scenario_input']))
    def event_case(label, value, expected=True, ctx=None, context_name='base'):
        selected = context if ctx is None else ctx
        exercise(label, lambda: validate_event_reference(value, selected, parse, spec), expected, value, context_name)
    for kind, value in examples.items():
        event_case(kind + ' mapped reference accepted', value)
        event_case(kind + ' unknown entity kind rejected', patch(value, ['entity_ref', 'kind'], 'unregistered_entity_kind'), False)
        wrong = next(v for v in enum['members'].values() if v not in spec['event_entity_ref_mapping'][kind]['allowed_kinds'])
        event_case(kind + ' wrong existing target kind rejected', patch(value, ['entity_ref', 'kind'], wrong), False)
        event_case(kind + ' inconsistent or missing target identity rejected', patch(value, ['entity_ref', 'id'], uid('missing-target')), False)
        if kind == 'warehouse_resource_unavailable':
            bad = patch(value, ['entity_ref', 'revision'], 4)
            bad = patch(bad, ['resource_ref', 'revision'], 4)
        else:
            bad = patch(value, ['entity_ref', 'revision'], 4)
        event_case(kind + ' inconsistent revision rejected', bad, False)
        policy = spec['event_entity_ref_mapping'][kind]['target']['revision']
        if policy == 'row_version_if_present':
            optional = patch(value, ['entity_ref', 'revision'], None)
            if kind == 'warehouse_resource_unavailable':
                optional = patch(optional, ['resource_ref', 'revision'], None)
            event_case(kind + ' optional unpinned identity accepted', optional)
        if spec['event_entity_ref_mapping'][kind]['target']['source'] == 'entity':
            target_path = spec['event_entity_ref_mapping'][kind]['target']['id_path'].split('.')
            missing = patch(value, target_path, uid('missing-target'))
            missing = patch(missing, ['entity_ref', 'id'], uid('missing-target'))
            event_case(kind + ' target absent from selected fact snapshot rejected', missing, False)
    traffic = examples['traffic_disruption']
    arcs = [dict(from_node_id=nodes[0], to_node_id=nodes[1]), dict(from_node_id=nodes[1], to_node_id=nodes[2])]
    event_case('traffic several arcs in the selected matrix accepted', dict(traffic, arc_refs=arcs))
    event_case('traffic reverse directions are distinct arcs accepted', dict(traffic, arc_refs=[arcs[0], dict(from_node_id=nodes[1], to_node_id=nodes[0])]))
    event_case('traffic open multiplier accepted', dict(traffic, closure=False, travel_multiplier=dict(numerator=3, denominator=2)))
    event_case('traffic empty arcs rejected', dict(traffic, arc_refs=[]), False)
    event_case('traffic duplicate directed arc rejected', dict(traffic, arc_refs=[arcs[0], arcs[0]]), False)
    event_case('traffic self arc rejected', dict(traffic, arc_refs=[dict(from_node_id=nodes[0], to_node_id=nodes[0])]), False)
    event_case('traffic arcs from two snapshot matrices rejected', dict(traffic, arc_refs=[arcs[0], dict(from_node_id=nodes[3], to_node_id=nodes[4])]), False)
    event_case('traffic reference switched to other matrix rejected', patch(traffic, ['entity_ref', 'id'], m2['id']), False)
    event_case('traffic null matrix version rejected', patch(traffic, ['entity_ref', 'revision'], None), False)
    event_case('traffic unchanged version rejected', dict(traffic, new_matrix_version=3), False)
    event_case('traffic lower version rejected', dict(traffic, new_matrix_version=2), False)
    event_case('traffic closure with multiplier rejected', dict(traffic, travel_multiplier=dict(numerator=3, denominator=2)), False)
    event_case('traffic open without multiplier rejected', dict(traffic, closure=False), False)
    event_case('traffic extra matrix selector rejected', dict(traffic, matrix_ids=[m1['id'], m2['id']]), False)
    weather = examples['weather_change']
    event_case('weather reordered region set preserves identity accepted', patch(weather, ['region_ref', 'node_ids'], list(reversed(region['node_ids']))))
    event_case('weather empty region rejected', patch(weather, ['region_ref', 'node_ids'], []), False)
    event_case('weather duplicate region node rejected', patch(weather, ['region_ref', 'node_ids'], region['node_ids'] + [region['node_ids'][0]]), False)
    event_case('weather unknown region node rejected', patch(weather, ['region_ref', 'node_ids'], region['node_ids'] + [uid('unknown-node')]), False)
    event_case('weather same region ID changed membership rejected', patch(weather, ['region_ref', 'node_ids'], [nodes[0], nodes[1]]), False)
    event_case('weather advance only first affected matrix rejected', dict(weather, new_matrix_version=4), False)
    event_case('weather unchanged second matrix version rejected', dict(weather, new_matrix_version=7), False)
    different = patch(weather, ['region_ref', 'region_id'], uid('different-region'))
    event_case('weather ref ID differs from inline region rejected', different, False)
    different = patch(different, ['entity_ref', 'id'], uid('different-region'))
    event_case('weather explicit new region identity accepted', different)
    warehouse = examples['warehouse_resource_unavailable']
    for kind in spec['event_entity_ref_mapping']['warehouse_resource_unavailable']['allowed_kinds']:
        value = dict(warehouse, entity_ref=ref(kind), resource_ref=ref(kind))
        event_case('warehouse ' + kind + ' complete resource branch accepted', value)
        event_case('warehouse ' + kind + ' resource ID mismatch rejected', patch(value, ['resource_ref', 'id'], uid('missing-resource')), False)
        event_case('warehouse ' + kind + ' resource revision mismatch rejected', patch(value, ['resource_ref', 'revision'], None), False)
        stale = patch(value, ['entity_ref', 'revision'], 4)
        stale = patch(stale, ['resource_ref', 'revision'], 4)
        event_case('warehouse ' + kind + ' both stale revisions rejected', stale, False)
    event_case('warehouse unsupported vehicle resource rejected', dict(warehouse, entity_ref=ref('vehicle'), resource_ref=ref('vehicle')), False)
    event_case('warehouse unsupported transport task resource rejected', dict(warehouse, entity_ref=ref('transport_task'), resource_ref=ref('transport_task')), False)
    typed_wrong = copy.deepcopy(context)
    typed_wrong['scenario_input']['snapshot']['vehicles'] = [copy.deepcopy(context['scenario_input']['snapshot']['orders'][0])]
    event_case('vehicle target with Order record shape rejected', examples['vehicle_failure'], False, typed_wrong, 'vehicle slot contains Order shape')
    event_case('fixed snapshot keeps valid historical fact binding accepted', examples['vehicle_failure'])
    counts = dict(total=len(cases), positive=sum(r['expected_accepted'] for r in cases),
                  negative=sum(not r['expected_accepted'] for r in cases),
                  matched=sum(r['matches_expected'] for r in cases),
                  mismatched=sum(not r['matches_expected'] for r in cases))
    return dict(normative_enum_members=enum['members'], normative_event_mapping=spec['event_entity_ref_mapping'],
                fixture_wrapper=context, base_events=examples, cases=cases, case_counts=counts,
                limitations=['These are fixed-snapshot reference predicates only, not business runtime acceptance.',
                             'The ScenarioInput fixture uses exact current named fields; its CargoType string is explicitly unvalidated by inherited structural adapters and is not a normative enum decision.',
                             'No current live state is queried to revalidate persisted audit references.',
                             'All inherited N02-R01 parse-only/full-Schema/FK/calendar limitations remain documented.'])


def require(condition):
    if not condition:
        raise DesignRejected('assertion predicate false')
    return True
