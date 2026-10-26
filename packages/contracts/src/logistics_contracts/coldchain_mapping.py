"""Mapping from the optional R05 domain snapshot to its wire projection."""

from __future__ import annotations

from logistics_contracts import coldchain as dto
from logistics_domain import coldchain as domain


def _capacity(value: domain.CapacityAmount) -> dto.CapacityAmountDTO:
    return dto.CapacityAmountDTO(unit=value.unit, amount=value.amount)


def coldchain_dto(value: domain.ColdChainSnapshot | None) -> dto.ColdChainSnapshotDTO | None:
    if value is None:
        return None
    return dto.ColdChainSnapshotDTO(
        rule_version=value.rule_version, horizon_s=value.horizon_s,
        zones=tuple(dto.ColdChainZoneDTO(
            zone_id=item.zone_id, warehouse_id=item.warehouse_id, version=item.version,
            setpoint_decic=item.setpoint_decic,
            capacities=tuple(_capacity(c) for c in item.capacities)) for item in value.zones),
        storage_locations=tuple(dto.ColdChainStorageLocationDTO(
            location_id=item.location_id, warehouse_id=item.warehouse_id, zone_id=item.zone_id,
            version=item.version, capacities=tuple(_capacity(c) for c in item.capacities),
            available_windows=tuple(
                __import__("logistics_contracts.entities", fromlist=["TimeWindowDTO"]).TimeWindowDTO(
                    earliest_s=window.earliest_s, latest_s=window.latest_s)
                for window in item.available_windows),
            capacity_periods=tuple(dto.CapacityPeriodDTO(
                start_s=period.start_s, end_s=period.end_s,
                capacities=tuple(_capacity(capacity) for capacity in period.capacities))
                for period in item.capacity_periods)) for item in value.storage_locations),
        occupancies=tuple(dto.StorageOccupancyDTO(
            occupancy_id=item.occupancy_id, batch_id=item.batch_id, location_id=item.location_id,
            capacity_use=tuple(_capacity(c) for c in item.capacity_use), origin=item.origin,
            inbound_operation_id=item.inbound_operation_id,
            outbound_operation_id=item.outbound_operation_id,
            declared_start_s=item.declared_start_s) for item in value.occupancies),
        setup_policies=tuple(dto.ColdChainSetupPolicyDTO(
            policy_id=item.policy_id, version=item.version, rule_version=item.rule_version,
            rendering=item.rendering,
            rules=tuple(dto.ChangeoverRuleDTO(from_class=rule.from_class,
                to_class=rule.to_class, duration_s=rule.duration_s) for rule in item.rules),
            default_duration_s=item.default_duration_s) for item in value.setup_policies),
        precool_requirements=tuple(dto.PrecoolRequirementDTO(
            requirement_id=item.requirement_id, batch_id=item.batch_id,
            warehouse_id=item.warehouse_id, precool_operation_id=item.precool_operation_id,
            loading_operation_ids=item.loading_operation_ids,
            min_duration_s=item.min_duration_s, target_zone=item.target_zone,
            eligible_resource_ids=item.eligible_resource_ids)
            for item in value.precool_requirements),
        exposure_limits=tuple(dto.ExposureLimitDTO(
            limit_id=item.limit_id, batch_id=item.batch_id, max_exposure_s=item.max_exposure_s,
            scopes=item.scopes, rule_version=item.rule_version, source=item.source)
            for item in value.exposure_limits),
        reuse_rules=tuple(dto.ReuseRuleDTO(
            location_id=item.location_id, max_batch_age_s=item.max_batch_age_s,
            min_gap_s=item.min_gap_s) for item in value.reuse_rules),
        batch_compatibility=tuple(dto.BatchCompatibilityDTO(
            batch_id=item.batch_id, warehouse_id=item.warehouse_id,
            temperature_zone=item.temperature_zone,
            min_temperature_decic=item.min_temperature_decic,
            max_temperature_decic=item.max_temperature_decic,
            compatibility_class=item.compatibility_class)
            for item in value.batch_compatibility),
        compatibility_policy=(dto.CompatibilityPolicyDTO(
            policy_id=value.compatibility_policy.policy_id,
            version=value.compatibility_policy.version,
            rule_version=value.compatibility_policy.rule_version,
            incompatible_class_pairs=value.compatibility_policy.incompatible_class_pairs)
            if value.compatibility_policy is not None else None),
    )


__all__ = ["coldchain_dto"]
