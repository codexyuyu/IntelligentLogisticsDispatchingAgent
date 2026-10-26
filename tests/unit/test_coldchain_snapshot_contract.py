"""Minimal R05 cold-chain snapshot contract checks (no solver / no database)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from logistics_contracts.mapping import snapshot_dto
from logistics_domain.coldchain import (
    BatchCompatibility,
    CapacityAmount,
    CapacityPeriod,
    CapacityUnit,
    ChangeoverRule,
    ColdChainSetupPolicy,
    ColdChainSnapshot,
    ColdChainStorageLocation,
    ColdChainZone,
    CompatibilityPolicy,
    ExposureLimit,
    ExposureScope,
    PrecoolRequirement,
    ReuseRule,
    StorageOccupancy,
)
from logistics_domain.planning import PlanningScope, PlanningSnapshot, content_hash
from logistics_domain.resources import ResourceBundle

EPOCH = datetime(2026, 1, 1, tzinfo=UTC)


def _coldchain() -> ColdChainSnapshot:
    zone_id, warehouse_id, location_id = uuid4(), uuid4(), uuid4()
    precool_id, resource_id = uuid4(), uuid4()
    return ColdChainSnapshot(
        rule_version="r05-demo-1.0", horizon_s=86400,
        zones=(ColdChainZone(zone_id=zone_id, warehouse_id=warehouse_id, version=1,
            setpoint_decic=40, capacities=(CapacityAmount(CapacityUnit.WEIGHT_G, 1000),)),),
        storage_locations=(ColdChainStorageLocation(location_id=location_id,
            warehouse_id=warehouse_id, zone_id=zone_id, version=1,
            capacities=(CapacityAmount(CapacityUnit.WEIGHT_G, 1000),)),),
        occupancies=(StorageOccupancy(occupancy_id=uuid4(), batch_id="batch-1",
            location_id=location_id,
            capacity_use=(CapacityAmount(CapacityUnit.WEIGHT_G, 100),),
            origin="initial_stock", declared_start_s=0),),
        setup_policies=(ColdChainSetupPolicy(policy_id=uuid4(), version="1.0",
            rule_version="r05-demo-1.0", rendering="gap",
            rules=(ChangeoverRule("receive", "load", 7),)),),
        reuse_rules=(ReuseRule(location_id=location_id, max_batch_age_s=604800,
            min_gap_s=60),),
        precool_requirements=(PrecoolRequirement(requirement_id=uuid4(), batch_id="batch-1",
            warehouse_id=warehouse_id, precool_operation_id=precool_id,
            loading_operation_ids=(), min_duration_s=30, target_zone="chilled",
            eligible_resource_ids=(resource_id,)),),
        exposure_limits=(ExposureLimit(limit_id=uuid4(), batch_id="batch-1",
            max_exposure_s=120, scopes=(ExposureScope.IN_WAREHOUSE,),
            rule_version="r05-demo-1.0", source="declared"),),
        batch_compatibility=(BatchCompatibility(batch_id="batch-1",
            warehouse_id=warehouse_id, temperature_zone="chilled",
            min_temperature_decic=0, max_temperature_decic=80),),
        compatibility_policy=CompatibilityPolicy(policy_id=uuid4(), version="1.0",
            rule_version="r05-demo-1.0", incompatible_class_pairs=(("raw", "ready"),)),
    )


def test_coldchain_snapshot_survives_dto_round_trip_and_hash() -> None:
    coldchain = _coldchain()
    snapshot = PlanningSnapshot.create(
        id=uuid4(), scope=PlanningScope((), (), (), EPOCH, 3600), orders=(), cargo=(),
        vehicles=(), drivers=(), resources=ResourceBundle((), (), (), (), (), (), ()),
        inventory=(), revisions=(), matrices=(), coldchain=coldchain)
    assert snapshot.hash == content_hash({field.name: getattr(snapshot, field.name)
                                          for field in snapshot.__dataclass_fields__.values()
                                          if field.name != "hash"})
    dto = snapshot_dto(snapshot)
    assert dto.coldchain is not None
    assert dto.coldchain.rule_version == "r05-demo-1.0"
    assert dto.coldchain.storage_locations[0].location_id == coldchain.storage_locations[0].location_id
    restored = dto.to_domain()
    assert restored.coldchain == coldchain
    assert restored.hash == snapshot.hash
