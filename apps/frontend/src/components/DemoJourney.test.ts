import { describe, expect, it } from 'vitest';
import { nextDemoStep } from './DemoJourney';
import type { Simulation } from '../features/stageB/api';

const checked = { status: 'checked', joint_validation: { valid: true } };
const emptySim = { simulation_id: 'simulation-1', active_version: 0, horizon_s: 4000, tracks: [], events: [] } as Simulation;

describe('demo workflow from authoritative backend state', () => {
  it('starts with validated joint dispatch and never assumes old browser state is checked', () => {
    expect(nextDemoStep(null, null)).toBe('plan');
    expect(nextDemoStep({ status: 'queued' }, emptySim)).toBe('plan');
    expect(nextDemoStep({ status: 'checked', joint_validation: { valid: false } }, emptySim)).toBe('plan');
  });
  it('requires an explicit simulation start for a checked run', () => {
    expect(nextDemoStep(checked, null)).toBe('start');
    expect(nextDemoStep(checked, emptySim)).toBe('incident');
  });
  it('does not skip a pending human decision and supports both final decisions', () => {
    const incident = { id: 'incident-1', status: 'pending', row_version: 0 } as const;
    expect(nextDemoStep(checked, { ...emptySim, incident })).toBe('incident');
    expect(nextDemoStep(checked, { ...emptySim, incident: { ...incident, status: 'approved' } })).toBe('replay');
    expect(nextDemoStep(checked, { ...emptySim, incident: { ...incident, status: 'rejected' } })).toBe('replay');
  });
});
