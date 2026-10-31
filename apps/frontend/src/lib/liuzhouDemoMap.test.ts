import { describe, expect, it } from 'vitest';
import { assertDemoRouteIntegrity, buildDemoMotion, buildWenchangFourTruckShowcase,
  createDemoNodes, sampleDemoMotion, visualMarkerOffset, WENCHANG_CAMPUS } from './liuzhouDemoMap';

describe('Wenchang campus 2D demo routes', () => {
  const routes = buildWenchangFourTruckShowcase(2620);
  const nodes = createDemoNodes(routes);

  it('has four independent, clearly demo-labelled vehicles', () => {
    expect(routes).toHaveLength(4);
    expect(new Set(routes.map(route => route.vehicleId)).size).toBe(4);
    expect(routes.every(route => route.vehicleId.startsWith('SHOWCASE_'))).toBe(true);
  });
  it('does not change stop order or event timing', () => {
    for (const route of routes) {
      const motion = buildDemoMotion(route, nodes)!;
      expect(assertDemoRouteIntegrity(route, motion)).toBe(true);
      expect(motion.stops.map(stop => stop.nodeId)).toEqual(route.stops.map(stop => stop.nodeId));
      expect(motion.legs.map(leg => leg.toS)).toEqual(route.stops.slice(1).map(stop => stop.arrivalS));
    }
  });
  it('returns independent timed poses at waiting and completion', () => {
    for (const route of routes) {
      const motion = buildDemoMotion(route, nodes)!;
      expect(sampleDemoMotion(motion, 0).state).toBe('waiting');
      expect(sampleDemoMotion(motion, 2620).state).toBe('completed');
      expect(sampleDemoMotion(motion, 2620).point).toEqual(motion.end);
    }
  });
  it('anchors the demo near the university, not an arbitrary overseas city', () => {
    expect(WENCHANG_CAMPUS[0]).toBeGreaterThan(24.3);
    expect(WENCHANG_CAMPUS[1]).toBeGreaterThan(109.4);
    expect(Object.values(nodes).filter(node => node.isDepot)).toHaveLength(1);
  });  it('moves continuously on each visible route leg and does not jump across stops', () => {
    for (const route of routes) {
      const motion = buildDemoMotion(route, nodes)!;
      for (let i = 0; i < motion.legs.length; i++) {
        const leg = motion.legs[i];
        const endPose = sampleDemoMotion(motion, leg.toS);
        const expectedEnd = leg.points.at(-1)!;
        expect(endPose.point[0]).toBeCloseTo(expectedEnd[0], 5);
        expect(endPose.point[1]).toBeCloseTo(expectedEnd[1], 5);
        // A one-millisecond advance must never teleport to another stop.
        const after = sampleDemoMotion(motion, leg.toS + .001);
        expect(Math.hypot((after.point[0] - endPose.point[0]) * 111000,
          (after.point[1] - endPose.point[1]) * 101000)).toBeLessThan(1);
        for (let t = leg.fromS + 1; t <= leg.toS; t += 3) {
          const a = sampleDemoMotion(motion, t - 1).point;
          const b = sampleDemoMotion(motion, t).point;
          const stepM = Math.hypot((b[0]-a[0])*111000, (b[1]-a[1])*101000);
          // A simulator-second step may travel tens of metres, not kilometres.
          expect(stepM).toBeLessThan(120);
        }
      }
    }
  });
  it('parking offsets shrink smoothly and never snap sideways when trucks get close', () => {
    const motion = buildDemoMotion(routes[0], nodes)!;
    const start = motion.legs[0].fromS;
    const a = visualMarkerOffset(motion, start, 0, 4);
    const b = visualMarkerOffset(motion, start + 1, 0, 4);
    const c = visualMarkerOffset(motion, start + 45, 0, 4);
    expect(Math.hypot(a.x, a.y)).toBeGreaterThan(30);
    expect(Math.hypot(c.x, c.y)).toBeLessThan(0.01);
    expect(Math.hypot(b.x-a.x, b.y-a.y)).toBeLessThan(2);
    const midway = motion.legs[1].fromS + 15;
    expect(visualMarkerOffset(motion, midway, 0, 4)).toEqual({x:0,y:0});
    expect(visualMarkerOffset(motion, midway, 0, 1)).toEqual({x:0,y:0});
  });

});
