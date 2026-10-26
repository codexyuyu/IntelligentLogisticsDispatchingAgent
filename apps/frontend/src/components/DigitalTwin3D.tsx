// Owner: CODEX_FRONTEND. 3D digital twin rendered from real plan routes and the
// shared simulation clock. Node positions are schematic (see lib/twin.ts) because
// the contract carries travel matrices, not geo coordinates.
import { useEffect, useMemo, useRef } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import type { TwinRoute } from '../appTypes';
import { layoutNodes } from '../lib/twin';
import { buildRouteMotion, geoProjection, sampleMotion } from '../lib/replayPaths';
import { fmtClock } from '../lib/format';

export type TwinWarehouse = { id: string; zones: ('chilled' | 'frozen')[] };

type Props = {
  routes: TwinRoute[];
  warehouses: TwinWarehouse[];
  nodeIds: string[];
  nodeZones?: Record<string, 'chilled' | 'frozen'>;
  orderCount: number;
  simTimeS: number;
  /** Read the high-resolution clock directly without forcing React to render each frame. */
  getTime?: () => number;
  followVehicleId?: string | null;
  eventActive: boolean;
  affectedVehicleIds?: string[];
  holdWindows?: Record<string, { fromS: number; untilS: number }>;
  selectedVehicleId?: string | null;
  onPickVehicle?: (vehicleId: string | null) => void;
  onPickWarehouse?: (warehouseId: string) => void;
  height?: number;
  waitingText?: string;
};

const COLORS = {
  chilled: 0x4caf73,
  frozen: 0xd4d6d0,
  alert: 0xd18f2a,
  routeDim: 0x3a4a3a,
  floor: 0x262826,
  grid1: 0x3a3c38,
  grid2: 0x2e302d,
  building: 0x30322f,
  dock: 0x4a4d47,
};

function makeLabel(text: string, color = '#E9EBE5', size = 42): THREE.Sprite {
  const canvas = document.createElement('canvas');
  canvas.width = 256;
  canvas.height = 64;
  const ctx = canvas.getContext('2d')!;
  ctx.font = `${size}px "Microsoft YaHei", sans-serif`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillStyle = color;
  ctx.fillText(text, 128, 32);
  const texture = new THREE.CanvasTexture(canvas);
  texture.anisotropy = 4;
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: texture, transparent: true, depthWrite: false }));
  sprite.scale.set(4.4, 1.1, 1);
  return sprite;
}

export default function DigitalTwin3D({
  routes,
  warehouses,
  nodeIds,
  nodeZones = {},
  orderCount,
  simTimeS,
  getTime,
  followVehicleId = null,
  eventActive,
  affectedVehicleIds = [],
  holdWindows = {},
  selectedVehicleId = null,
  onPickVehicle,
  onPickWarehouse,
  height = 560,
  waitingText = '等待调度方案…',
}: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const simTimeRef = useRef(simTimeS);
  simTimeRef.current = simTimeS;
  const getTimeRef = useRef(getTime);
  getTimeRef.current = getTime;
  const selectedRef = useRef(selectedVehicleId);
  selectedRef.current = selectedVehicleId;
  const followRef = useRef(followVehicleId);
  followRef.current = followVehicleId;
  const pickRef = useRef(onPickVehicle);
  pickRef.current = onPickVehicle;
  const pickWarehouseRef = useRef(onPickWarehouse);
  pickWarehouseRef.current = onPickWarehouse;
  const affectedRef = useRef(affectedVehicleIds);
  affectedRef.current = affectedVehicleIds;
  const holdsRef = useRef(holdWindows);
  holdsRef.current = holdWindows;

  // Use a value-based scene identity. Inline warehouses arrays from parents used
  // to rebuild the entire WebGL scene on *every simulation clock tick* in R24.
  // Full OSRM geometry may contain tens of thousands of coordinates: serialize
  // it only when the route object itself changes, NOT at every clock UI tick.
  const routeSignature = useMemo(() => JSON.stringify(routes), [routes]);
  const warehouseSignature = JSON.stringify(warehouses);
  const nodeSignature = nodeIds.join(',');
  const zoneSignature = JSON.stringify(nodeZones);
  const sceneKey = useMemo(() => `${routeSignature}|${warehouseSignature}|${nodeSignature}|${zoneSignature}`,
    [routeSignature, warehouseSignature, nodeSignature, zoneSignature]);
  const positions = useMemo(() => {
    const warehouseStops = routes.map((r) => r.stops[0]?.nodeId).filter((x): x is string => Boolean(x));
    const result = layoutNodes(nodeIds, warehouseStops);
    const project = geoProjection(routes);
    if (project) {
      routes.forEach((r) => r.stops.forEach((stop, index) => {
        const coord = r.stopCoordinates?.[index];
        if (coord) result[stop.nodeId] = project(coord[0], coord[1]);
      }));
    }
    return result;
  }, [sceneKey]); // eslint-disable-line react-hooks/exhaustive-deps
  const roadProjection = useMemo(() => geoProjection(routes), [sceneKey]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x1e201e);
    scene.fog = new THREE.Fog(0x1e201e, 55, 120);

    const width = container.clientWidth || 960;
    const heightPx = container.clientHeight || height;
    const camera = new THREE.PerspectiveCamera(46, width / heightPx, 0.1, 400);
    camera.position.set(4, 34, 46);

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
    renderer.setSize(width, heightPx);
    container.replaceChildren(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.target.set(6, 0, 0);
    controls.minDistance = 16;
    controls.maxDistance = 110;
    controls.maxPolarAngle = Math.PI * 0.47;

    scene.add(new THREE.HemisphereLight(0xeceee8, 0x1a1b19, 1.25));
    const key = new THREE.DirectionalLight(0xffffff, 1.5);
    key.position.set(18, 40, 16);
    scene.add(key);
    const rim = new THREE.DirectionalLight(0x4caf73, 0.4);
    rim.position.set(-24, 14, -18);
    scene.add(rim);

    const floor = new THREE.Mesh(
      new THREE.BoxGeometry(96, 0.3, 72),
      new THREE.MeshStandardMaterial({ color: COLORS.floor, roughness: 0.95, metalness: 0.08 }),
    );
    floor.position.set(4, -0.15, 0);
    scene.add(floor);
    const grid = new THREE.GridHelper(96, 48, COLORS.grid1, COLORS.grid2);
    grid.position.set(4, 0.02, 0);
    (grid.material as THREE.Material).transparent = true;
    (grid.material as THREE.Material).opacity = 0.5;
    scene.add(grid);

    // R25 lightweight city massing for the *schematic* mode. No photorealism
    // claims: avoid fabricating urban buildings when OSRM geodata is available.
    if (!roadProjection) {
      const cityColors = [0x2b2d2a, 0x323430, 0x363833, 0x2f312d];
      for (let col = 0; col < 7; col++) {
        for (let row = 0; row < 5; row++) {
          const x = -5 + col * 6.8;
          const z = -19 + row * 8.5;
          const buildingH = 1.5 + ((col * 7 + row * 3) % 6) * 0.72;
          const block = new THREE.Mesh(new THREE.BoxGeometry(2.1, buildingH, 1.7),
            new THREE.MeshStandardMaterial({ color: cityColors[(col + row) % cityColors.length], metalness: 0.18, roughness: 0.7 }));
          block.position.set(x, buildingH / 2, z);
          scene.add(block);
        }
      }
    }

    // warehouses
    const pickablesWarehouse: THREE.Object3D[] = [];
    const whPositions = [new THREE.Vector3(-17, 0, -7), new THREE.Vector3(-17, 0, 9), new THREE.Vector3(-17, 0, -22), new THREE.Vector3(-17, 0, 23)];
    warehouses.forEach((wh, index) => {
      const first = routes.find((r) => r.warehouseId === wh.id)?.stops[0]?.nodeId;
      const actual = first ? positions[first] : undefined;
      const at = actual ? new THREE.Vector3(actual.x, 0, actual.z) : whPositions[index % whPositions.length];
      const group = new THREE.Group();
      group.position.copy(at);
      group.userData.warehouseId = wh.id;
      const base = new THREE.Mesh(
        new THREE.BoxGeometry(13, 0.5, 16),
        new THREE.MeshStandardMaterial({ color: 0x2a2c29, roughness: 0.8 }),
      );
      base.position.y = 0.25;
      group.add(base);
      const zones = wh.zones.length ? wh.zones : (['chilled', 'frozen'] as const);
      zones.forEach((zone, zi) => {
        const color = zone === 'frozen' ? COLORS.frozen : COLORS.chilled;
        const cold = new THREE.Mesh(
          new THREE.BoxGeometry(4.4, 3.4, 6.4),
          new THREE.MeshStandardMaterial({
            color, transparent: true, opacity: 0.2, emissive: color, emissiveIntensity: 0.32, roughness: 0.4, metalness: 0.2,
          }),
        );
        cold.position.set(-2.6, 1.7, -4.6 + zi * 9.2);
        group.add(cold);
        const frame = new THREE.Mesh(
          new THREE.BoxGeometry(4.7, 0.14, 6.7),
          new THREE.MeshStandardMaterial({ color, emissive: color, emissiveIntensity: 0.9 }),
        );
        frame.position.set(-2.6, 3.55, -4.6 + zi * 9.2);
        group.add(frame);
        for (let r = 0; r < 3; r += 1) {
          const rack = new THREE.Mesh(
            new THREE.BoxGeometry(0.5, 2.2, 1.4),
            new THREE.MeshStandardMaterial({ color: 0x50534c, roughness: 0.6, metalness: 0.4 }),
          );
          rack.position.set(-3.6 + r * 1.9, 1.1, -4.6 + zi * 9.2);
          group.add(rack);
        }
      });
      const roof = new THREE.Mesh(
        new THREE.BoxGeometry(14.2, 0.26, 17.2),
        new THREE.MeshStandardMaterial({ color: 0x9ea396, transparent: true, opacity: 0.24, roughness: 0.35, metalness: 0.3, depthWrite: false }),
      );
      roof.position.set(0, 4.3, 0);
      group.add(roof);
      for (const px of [-6.4, 6.4]) {
        for (const pz of [-7.6, 7.6]) {
          const pillar = new THREE.Mesh(
            new THREE.BoxGeometry(0.5, 4.2, 0.5),
            new THREE.MeshStandardMaterial({ color: 0x464943, roughness: 0.5, metalness: 0.5 }),
          );
          pillar.position.set(px, 2.1, pz);
          group.add(pillar);
        }
      }
      for (let d = 0; d < 3; d += 1) {
        const dock = new THREE.Mesh(
          new THREE.BoxGeometry(1.6, 0.18, 2.1),
          new THREE.MeshStandardMaterial({ color: COLORS.dock, emissive: 0x2c3a2c, emissiveIntensity: 0.6, roughness: 0.5 }),
        );
        dock.position.set(7.6, 0.32, -5 + d * 5);
        group.add(dock);
      }
      const label = makeLabel(wh.id, '#BFE3C9');
      label.position.set(0, 6.4, 0);
      group.add(label);
      const zoneLabel = makeLabel(zones.map((z) => (z === 'frozen' ? '冷冻' : '冷藏')).join(' / '), '#C2C5BD', 34);
      zoneLabel.position.set(0, 5.3, 0);
      zoneLabel.scale.set(3.6, 0.9, 1);
      group.add(zoneLabel);
      scene.add(group);
      pickablesWarehouse.push(group);
    });

    // delivery node markers
    const pickables: THREE.Object3D[] = [];
    const warehouseIdSet = new Set(routes.map((r) => r.stops[0]?.nodeId));
    Object.entries(positions).forEach(([nodeId, pos]) => {
      if (warehouseIdSet.has(nodeId)) return;
      const zone = nodeZones[nodeId] ?? 'chilled';
      const color = zone === 'frozen' ? COLORS.frozen : COLORS.chilled;
      const group = new THREE.Group();
      group.position.set(pos.x, 0, pos.z);
      const post = new THREE.Mesh(
        new THREE.CylinderGeometry(0.16, 0.16, 1.5, 8),
        new THREE.MeshStandardMaterial({ color: 0x55584f, roughness: 0.6, metalness: 0.35 }),
      );
      post.position.y = 0.75;
      group.add(post);
      const ring = new THREE.Mesh(
        new THREE.TorusGeometry(0.55, 0.07, 8, 24),
        new THREE.MeshStandardMaterial({ color, emissive: color, emissiveIntensity: 0.85 }),
      );
      ring.rotation.x = Math.PI / 2;
      ring.position.y = 1.55;
      group.add(ring);
      const dot = new THREE.Mesh(
        new THREE.SphereGeometry(0.22, 12, 12),
        new THREE.MeshStandardMaterial({ color, emissive: color, emissiveIntensity: 1.2 }),
      );
      dot.position.y = 1.55;
      group.add(dot);
      group.userData.nodeId = nodeId;
      pickables.push(group);
      scene.add(group);
    });

    // Route geometry is OSRM only when explicit, validated GeoJSON is supplied.
    // Otherwise the right-angle streets remain a labelled schematic demo.
    type TruckEntry = {
      motion: NonNullable<ReturnType<typeof buildRouteMotion>>;
      truck: THREE.Group;
      line: THREE.Line[];
      wheels: THREE.Mesh[];
      light: THREE.MeshStandardMaterial;
    };
    const trucks = new Map<string, TruckEntry>();
    const wheelGeometry = new THREE.CylinderGeometry(0.23, 0.23, 0.15, 12);
    const wheelMaterial = new THREE.MeshStandardMaterial({ color: 0x1c1d1b, roughness: 0.95 });
    const bounds = new THREE.Box3();
    routes.forEach((route) => {
      const projectedRoad = roadProjection && route.roadCoordinates
        ? route.roadCoordinates.map(([lng, lat]) => roadProjection(lng, lat)) : undefined;
      const motion = buildRouteMotion(route, positions, projectedRoad);
      if (!motion) return;
      const color = route.zone === 'frozen' ? COLORS.frozen : COLORS.chilled;
      const routeLines: THREE.Line[] = [];
      motion.legs.forEach((leg) => {
        if (!projectedRoad) {
          for (let j = 1; j < leg.points.length; j++) {
            const a = leg.points[j - 1], b = leg.points[j];
            const length = Math.hypot(b.x - a.x, b.z - a.z);
            if (length < 0.03) continue;
            const asphalt = new THREE.Mesh(new THREE.BoxGeometry(length, 0.07, 0.82),
              new THREE.MeshStandardMaterial({ color: 0x3e413b, roughness: 0.96 }));
            asphalt.position.set((a.x + b.x) / 2, 0.09, (a.z + b.z) / 2);
            asphalt.rotation.y = Math.atan2(-(b.z - a.z), b.x - a.x);
            scene.add(asphalt);
          }
        }
        const vertices = leg.points.map((p) => new THREE.Vector3(p.x, 0.25, p.z));
        for (const point of vertices) bounds.expandByPoint(point);
        const path = new THREE.Line(
          new THREE.BufferGeometry().setFromPoints(vertices),
          new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.55 }),
        );
        scene.add(path);
        routeLines.push(path);
      });
      const truck = new THREE.Group();
      const light = new THREE.MeshStandardMaterial({ color: 0xf1f2ee, roughness: 0.38, metalness: 0.18, emissive: 0x1f2a1f, emissiveIntensity: 0.24 });
      const body = new THREE.Mesh(new THREE.BoxGeometry(1.65, 0.86, 0.93), light);
      body.position.set(0, 0.92, 0);
      truck.add(body);
      const cabin = new THREE.Mesh(new THREE.BoxGeometry(0.65, 0.82, 0.85),
        new THREE.MeshStandardMaterial({ color, roughness: 0.32, metalness: 0.25 }));
      cabin.position.set(1.12, 0.78, 0);
      truck.add(cabin);
      const windscreen = new THREE.Mesh(new THREE.BoxGeometry(0.09, 0.38, 0.67),
        new THREE.MeshStandardMaterial({ color: 0x2f322d, metalness: 0.55, roughness: 0.14 }));
      windscreen.position.set(1.47, 0.93, 0);
      truck.add(windscreen);
      // Refrigeration unit and cargo temperature stripe, distinguish cold-chain
      // vans from generic moving boxes without importing bulky 3D assets.
      const chiller = new THREE.Mesh(new THREE.BoxGeometry(0.36, 0.34, 0.72),
        new THREE.MeshStandardMaterial({ color: 0xd8dbd2, roughness: 0.4, metalness: 0.28 }));
      chiller.position.set(0.63, 1.53, 0);
      truck.add(chiller);
      const stripe = new THREE.Mesh(new THREE.BoxGeometry(1.37, 0.12, 0.045),
        new THREE.MeshStandardMaterial({ color, emissive: color, emissiveIntensity: 0.2 }));
      stripe.position.set(0, 1.06, 0.49);
      truck.add(stripe);
      const wheels: THREE.Mesh[] = [];
      for (const x of [-0.53, 1.10]) {
        for (const z of [-0.53, 0.53]) {
          const wheel = new THREE.Mesh(wheelGeometry, wheelMaterial);
          wheel.rotation.x = Math.PI / 2;
          wheel.position.set(x, 0.42, z);
          truck.add(wheel);
          wheels.push(wheel);
        }
      }
      for (const z of [-0.30, 0.30]) {
        const brake = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.16, 0.18),
          new THREE.MeshStandardMaterial({ color: 0xff4c48, emissive: 0xff2316, emissiveIntensity: 0.8 }));
        brake.position.set(-0.85, 0.85, z);
        truck.add(brake);
      }
      const tag = makeLabel(route.vehicleId, '#F2F3EF', 32);
      tag.position.set(0, 2.15, 0);
      tag.scale.set(3.0, 0.75, 1);
      truck.add(tag);
      truck.userData.vehicleId = route.vehicleId;
      const point = sampleMotion(motion, 0);
      truck.position.set(point.x, 0.12, point.z);
      pickables.push(truck);
      scene.add(truck);
      trucks.set(route.vehicleId, { motion, truck, line: routeLines, wheels, light });
    });
    // Expand the camera for real road networks (which may span a wider area).
    if (!bounds.isEmpty()) {
      const center = bounds.getCenter(new THREE.Vector3());
      const size = bounds.getSize(new THREE.Vector3());
      controls.target.copy(center);
      const d = Math.max(34, size.x * 1.1, size.z * 1.3);
      camera.position.set(center.x + d * 0.12, d * 0.85, center.z + d);
      camera.far = Math.max(400, d * 6);
      camera.updateProjectionMatrix();
      controls.maxDistance = Math.max(110, d * 3);
    }

    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();
    {
      const onClick = (event: MouseEvent) => {
        const rect = renderer.domElement.getBoundingClientRect();
        mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
        raycaster.setFromCamera(mouse, camera);
        const hits = raycaster.intersectObjects([...pickables,...pickablesWarehouse], true);
        for (const hit of hits) {
          let obj: THREE.Object3D | null = hit.object;
          while (obj) {
            if (obj.userData.vehicleId) {
              pickRef.current?.(obj.userData.vehicleId);
              return;
            }
            if (obj.userData.warehouseId) {
              pickWarehouseRef.current?.(obj.userData.warehouseId);
              return;
            }
            obj = obj.parent;
          }
        }
      };
      renderer.domElement.addEventListener('click', onClick);
      (container as unknown as { __cleanupClick?: () => void }).__cleanupClick = () => renderer.domElement.removeEventListener('click', onClick);
    }

    let raf = 0;
    let previousFrame = performance.now();
    let lastSimulationTime = 0;
    const cameraTarget = new THREE.Vector3();
    const animate = (now: number) => {
      const frameDt = Math.min(0.05, Math.max(0, (now - previousFrame) / 1000));
      previousFrame = now;
      const t = getTimeRef.current?.() ?? simTimeRef.current;
      trucks.forEach((entry, vehicleId) => {
        let effectiveT = t;
        const hold = holdsRef.current[vehicleId];
        if (hold && t > hold.fromS) {
          effectiveT = t >= hold.untilS ? t - (hold.untilS - hold.fromS) : hold.fromS;
        }
        const p = sampleMotion(entry.motion, effectiveT);
        entry.truck.position.set(p.x, 0.12, p.z);
        if (p.moving) entry.truck.rotation.y = p.heading;
        const movingSeconds = p.moving ? Math.max(0, effectiveT - lastSimulationTime) : 0;
        for (const wheel of entry.wheels) wheel.rotation.z -= Math.min(0.3, movingSeconds * 0.08);
        const selected = selectedRef.current === vehicleId;
        const affected = affectedRef.current.includes(vehicleId);
        entry.light.emissive.setHex(affected ? COLORS.alert : selected ? COLORS.chilled : 0x1f2a1f);
        entry.light.emissiveIntensity = affected ? 0.4 + 0.15 * Math.sin(now / 170) : selected ? 0.5 : 0.24;
        for (const line of entry.line) (line.material as THREE.LineBasicMaterial).opacity = selected ? 0.96 : affected ? 0.85 : 0.48;
        if (followRef.current === vehicleId) cameraTarget.copy(entry.truck.position);
      });
      lastSimulationTime = t;
      if (followRef.current && trucks.has(followRef.current)) {
        const delta = cameraTarget.clone().sub(controls.target).multiplyScalar(Math.min(1, frameDt * 2.5));
        controls.target.add(delta);
        camera.position.add(delta);
      }
      controls.update();
      renderer.render(scene, camera);
      raf = requestAnimationFrame(animate);
    };
    raf = requestAnimationFrame(animate);

    const resize = () => {
      const w = container.clientWidth || width;
      const h = container.clientHeight || heightPx;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    const observer = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(resize) : null;
    observer?.observe(container);
    window.addEventListener('resize', resize);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('resize', resize);
      observer?.disconnect();
      const cleanup = (container as unknown as { __cleanupClick?: () => void }).__cleanupClick;
      if (cleanup) cleanup();
      controls.dispose();
      scene.traverse((object) => {
        const mesh = object as THREE.Mesh;
        mesh.geometry?.dispose();
        const material = (mesh as THREE.Mesh).material;
        const materials = Array.isArray(material) ? material : material ? [material] : [];
        materials.forEach((mat) => {
          const sprite = mat as THREE.SpriteMaterial;
          sprite.map?.dispose();
          mat.dispose();
        });
      });
      renderer.dispose();
      container.replaceChildren();
      scene.clear();
    };
  }, [sceneKey, height]); // eslint-disable-line react-hooks/exhaustive-deps

  const servedOrders = routes.reduce((n, r) => n + r.stops.filter((s) => s.kind === 'delivery').length, 0);
  const affectedHere = affectedVehicleIds.length > 0;
  const hasRoadGeometry = routes.length > 0 && routes.every((r) => (r.roadCoordinates?.length ?? 0) > 1 && r.stopCoordinates?.length === r.stops.length);
  const horizon = Math.max(1800, ...routes.flatMap((r) => r.stops.map((s) => s.arrivalS)));

  return (
    <div className="twin-shell">
      <div className="twin-header">
        <div>
          
          <h3>冷链物流数字孪生</h3>
        </div>
        <div className="twin-topstats">
          <span><b>{warehouses.length}</b> 仓库</span>
          <span><b>{routes.length}</b> 路线</span>
          <span><b>{orderCount}</b> 订单</span>
          <span><b>{fmtClock(simTimeS)}</b> 仿真时间</span>
          <span className={eventActive || affectedHere ? 'alert-text' : ''}><i />{eventActive || affectedHere ? '异常处置中' : '运行正常'}</span>
        </div>
      </div>
      <div className="twin-stage" style={{ height }}>
        <div ref={containerRef} className="twin-canvas" />
        <div className="twin-legend">
          <span><i className="legend-dot chilled" />冷藏 chilled</span>
          <span><i className="legend-dot frozen" />冷冻 frozen</span>
          <span><i className="legend-dot warning" />受影响车辆</span>
          <span><i className="legend-dot route" />{hasRoadGeometry ? 'OSRM 道路估计' : '示意道路'}</span>
        </div>
        <div className="twin-overlay-card">
          <span className="overlay-title">当前仿真时刻</span>
          <div><b>{fmtClock(simTimeS)}</b><small>{simTimeS >= horizon ? '回放结束' : '推进中'}</small></div>
          <div><b>{affectedHere ? affectedVehicleIds.join(', ') : '—'}</b><small>{affectedHere ? '受异常影响' : '无异常车辆'}</small></div>
          <div><b>{servedOrders || '—'}</b><small>路线配送点</small></div>
        </div>
        {routes.length === 0 && (
          <div className="twin-waiting"><span>{waitingText}</span></div>
        )}
      </div>
    </div>
  );
}
