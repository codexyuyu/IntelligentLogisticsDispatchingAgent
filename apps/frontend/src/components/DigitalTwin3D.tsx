// Owner: CODEX_FRONTEND. 3D digital twin rendered from real plan routes and the
// shared simulation clock. Node positions are schematic (see lib/twin.ts) because
// the contract carries travel matrices, not geo coordinates.
import { useEffect, useMemo, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import type { TwinRoute } from '../appTypes';
import { layoutNodes } from '../lib/twin';
import { buildRouteMotion, geoProjection } from '../lib/replayPaths';
import { fmtClock } from '../lib/format';
import { routeDisplayColor, vehicleDisplayName, visualVehiclePose, vehicleReplayStatus, countDistinctVehicles } from '../lib/replayVisual';
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';

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
  const [focusedVehicle, setFocusedVehicle] = useState<string | null>(null);
  const [showAllRoutes, setShowAllRoutes] = useState(false);
  const [cameraMode, setCameraMode] = useState<'overview' | 'follow'>('overview');
  const effectiveSelected = selectedVehicleId ?? focusedVehicle;
  const focusRef = useRef<string | null>(effectiveSelected);
  focusRef.current = effectiveSelected;
  const showAllRef = useRef(showAllRoutes);
  showAllRef.current = showAllRoutes;
  const resetCameraRef = useRef(false);
  const cameraModeRef = useRef(cameraMode);
  cameraModeRef.current = cameraMode;
  const selectVehicle = (id: string | null) => { setFocusedVehicle(id); onPickVehicle?.(id); };

  const simTimeRef = useRef(simTimeS);
  simTimeRef.current = simTimeS;
  const getTimeRef = useRef(getTime);
  getTimeRef.current = getTime;
  const selectedRef = useRef(selectedVehicleId);
  selectedRef.current = effectiveSelected;
  const followRef = useRef(followVehicleId);
  followRef.current = followVehicleId;
  const pickRef = useRef((id: string | null) => { setFocusedVehicle(id); onPickVehicle?.(id); });
  pickRef.current = (id: string | null) => { setFocusedVehicle(id); onPickVehicle?.(id); };
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
  const motionSummary = useMemo(() => routes.map(route => {
    const projected = geoProjection(routes);
    const roadPoints = projected && route.roadCoordinates ? route.roadCoordinates.map(([lng, lat]) => projected(lng, lat)) : undefined;
    return { route, motion: buildRouteMotion(route, positions, roadPoints) };
  }), [sceneKey]); // eslint-disable-line react-hooks/exhaustive-deps
  const roadProjection = useMemo(() => geoProjection(routes), [sceneKey]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xbacbd2);
    scene.fog = new THREE.Fog(0xbacbd2, 100, 195);

    const width = container.clientWidth || 960;
    const heightPx = container.clientHeight || height;
    const camera = new THREE.PerspectiveCamera(46, width / heightPx, 0.1, 400);
    camera.position.set(10, 54, 55);

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
    renderer.setSize(width, heightPx);
    renderer.outputColorSpace=THREE.SRGBColorSpace;
    renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.12;
    renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;
    container.replaceChildren(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.target.set(6, 0, 0);
    controls.minDistance = 16;
    controls.maxDistance = 110;
    controls.maxPolarAngle = Math.PI * 0.47;
    controls.minPolarAngle = 0.15;

    scene.add(new THREE.HemisphereLight(0xffffff, 0x687d81, 1.6));
    const key = new THREE.DirectionalLight(0xffffff, 1.5);
    key.position.set(18, 40, 16);
    key.castShadow=true;key.shadow.mapSize.set(1024,1024);
    Object.assign(key.shadow.camera,{left:-55,right:55,top:45,bottom:-45,near:1,far:120});key.shadow.normalBias=.04;
    scene.add(key);
    const rim = new THREE.DirectionalLight(0xd9e3e7, 0.7);
    rim.position.set(-24, 14, -18);
    scene.add(rim);

    const floor = new THREE.Mesh(
      new THREE.BoxGeometry(140, 0.3, 116),
      new THREE.MeshStandardMaterial({color: 0xb6bcb2, roughness: 0.99}),
    );
    floor.position.set(4, -0.21, 0);
    floor.receiveShadow = true;
    scene.add(floor);
    // Landscape framing: the streets and buildings, not the editor grid,
    // communicate the layout. Geometry is presentation-only for schematic data.
    const vergeMaterial = new THREE.MeshStandardMaterial({color: 0x91aa8d, roughness: 1});
    for (const z of [-43, 43]) {
      const verge = new THREE.Mesh(new THREE.BoxGeometry(120, 0.03, 6), vergeMaterial);
      verge.position.set(3, -0.025, z); verge.receiveShadow = true; scene.add(verge);
    }

    // Keep buildings away from the mapped route corridors; never use anonymous
    // black blocks standing on top of roads. A few landscape props give scale.
    if (!roadProjection) {
      const trunk = new THREE.MeshStandardMaterial({ color: 0x646d63, roughness: 0.97 });
      const leaf = new THREE.MeshStandardMaterial({ color: 0x527c61, roughness: 0.98 });
      for (let i = 0; i < 13; i++) {
        const x = -33 + i * 5.8;
        const z = i % 2 ? 43.7 : -43.7;
        const tree = new THREE.Group();
        const stem = new THREE.Mesh(new THREE.CylinderGeometry(.14, .18, 2, 6), trunk);
        stem.position.y = 1; tree.add(stem);
        const crown = new THREE.Mesh(new THREE.IcosahedronGeometry(1.2 + (i % 3) * .16, 1), leaf);
        crown.position.y = 2.75; crown.castShadow = true; tree.add(crown);
        tree.position.set(x, 0, z); scene.add(tree);
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
      // The solver's depot node is the gate, not the middle of the building.
      group.position.x -= 9;
      group.userData.warehouseId = wh.id;
      const concrete = new THREE.MeshStandardMaterial({color: 0x636f76, roughness: .85});
      const wall = new THREE.MeshStandardMaterial({color: 0xdce6e8, metalness: .18, roughness: .75});
      const roofMaterial = new THREE.MeshStandardMaterial({color: 0x8198a3, metalness: .26, roughness: .67});
      const base = new THREE.Mesh(new THREE.BoxGeometry(17.5, .28, 17.8), concrete);
      base.position.y = .17; base.receiveShadow = true; group.add(base);
      const main = new THREE.Mesh(new THREE.BoxGeometry(12.4, 5.0, 13.8), wall);
      main.position.set(-1.9, 2.65, 0); main.castShadow = true; main.receiveShadow = true; group.add(main);
      const roof = new THREE.Mesh(new THREE.BoxGeometry(13.3, .36, 14.7), roofMaterial);
      roof.position.set(-1.9, 5.32, 0); roof.castShadow = true; group.add(roof);
      for (let d = 0; d < 3; d += 1) {
        const doorZ = -4.6 + d * 4.55;
        const roller = new THREE.Mesh(new THREE.BoxGeometry(.08, 2.55, 2.6),
          new THREE.MeshStandardMaterial({color: 0x7196aa, metalness: .45, roughness: .48}));
        roller.position.set(4.37, 1.55, doorZ); group.add(roller);
        const dock = new THREE.Mesh(new THREE.BoxGeometry(3.5, .42, 3.1),
          new THREE.MeshStandardMaterial({color: 0x556368, roughness: .88}));
        dock.position.set(6.2, .34, doorZ); dock.receiveShadow = true; group.add(dock);
        const marker = makeLabel(`月台 ${d+1}`, '#fff', 28);
        marker.position.set(4.8, 3.35, doorZ); marker.scale.set(2.4, .55, 1); group.add(marker);
        for (let stripe = 0; stripe < 3; stripe++) {
          const yellow = new THREE.Mesh(new THREE.BoxGeometry(.13, .015, .55),
            new THREE.MeshBasicMaterial({color: 0xf2cb64}));
          yellow.position.set(7.4 + stripe * .5, .58, doorZ); group.add(yellow);
        }
      }
      const cooling = new THREE.Mesh(new THREE.BoxGeometry(1.7, .9, 2.4),
        new THREE.MeshStandardMaterial({color: 0xe7edf0, metalness: .3, roughness: .48}));
      cooling.position.set(-6.6, 5.9, -3.4); cooling.castShadow = true; group.add(cooling);
      const zones = wh.zones.length ? wh.zones : (['chilled', 'frozen'] as const);
      const badge = makeLabel(`冷链配送中心 ${index+1}`, '#effefa', 30);
      badge.position.set(-1.5, 7.6, 0); badge.scale.set(6.9, 1.0, 1); group.add(badge);
      const zoneLabel = makeLabel(zones.map(z => z === 'frozen' ? '冷冻区' : '冷藏区').join(' · '), '#f5fffb', 29);
      zoneLabel.position.set(-1.5, 6.6, 0); zoneLabel.scale.set(4, .75, 1); group.add(zoneLabel);
      // Clear numbered vehicle bays. Vehicle visuals use these locations while
      // waiting at their logical depot; scheduling timestamps remain unchanged.
      for (let bay = 0; bay < 5; bay++) {
        const outline = new THREE.Mesh(new THREE.BoxGeometry(2.3, .014, 2.2),
          new THREE.MeshBasicMaterial({color: 0xecf5ec}));
        outline.position.set(14.1 + Math.floor(bay / 4) * 2.6, .045, -4.4 + (bay % 4) * 2.65);
        group.add(outline);
      }
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
      const pad = new THREE.Mesh(new THREE.BoxGeometry(3.4, .16, 3.5),
        new THREE.MeshStandardMaterial({color:0x738187, roughness:.92}));
      pad.position.set(2.0, .09, 2.2); pad.receiveShadow=true; group.add(pad);
      const store = new THREE.Mesh(new THREE.BoxGeometry(2.65, 2.3, 2.4),
        new THREE.MeshStandardMaterial({color: zone === 'frozen' ? 0xc9e4ee : 0xe8e8dd, roughness:.79}));
      store.position.set(2.0, 1.28, 2.6); store.castShadow=true; group.add(store);
      const storeRoof = new THREE.Mesh(new THREE.BoxGeometry(3.0,.25,2.7),
        new THREE.MeshStandardMaterial({color:0x52707b, roughness:.64}));
      storeRoof.position.set(2.0,2.56,2.6);group.add(storeRoof);
      const door = new THREE.Mesh(new THREE.BoxGeometry(.95,1.4,.06),
        new THREE.MeshStandardMaterial({color:0x628f9a, metalness:.25, roughness:.45}));
      door.position.set(2.0,.92,1.35);group.add(door);
      const title = makeLabel(`配送点 ${String(pickables.length+1).padStart(2,'0')}`, '#ffffff', 28);
      title.position.set(2.0,4.15,2.5);title.scale.set(4.0,.82,1);group.add(title);
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
    const vehicleIds = [...new Set(routes.map(route => route.vehicleId))];
    const roadSegmentKeys = new Set<string>();
    const asphaltMat = new THREE.MeshStandardMaterial({color: 0x505b62, roughness: .95});
    const shoulderMat = new THREE.MeshStandardMaterial({color: 0x8a999a, roughness: .96});
    const lineMarkMat = new THREE.MeshBasicMaterial({color: 0xdbe8e8});
    // One road surface for shared paths, independent route overlays for trucks.
    routes.forEach((route) => {
      const projectedRoad = roadProjection && route.roadCoordinates
        ? route.roadCoordinates.map(([lng, lat]) => roadProjection(lng, lat)) : undefined;
      const motion = buildRouteMotion(route, positions, projectedRoad);
      if (!motion) return;
      const color = routeDisplayColor(route.vehicleId, routes);
      const routeLines: THREE.Line[] = [];
      motion.legs.forEach((leg) => {
        if (!projectedRoad) {
          for (let j = 1; j < leg.points.length; j++) {
            const a = leg.points[j-1], b = leg.points[j];
            const distance = Math.hypot(b.x-a.x, b.z-a.z);
            if (distance < .03) continue;
            const key = [a,b].map(p => `${p.x.toFixed(2)}:${p.z.toFixed(2)}`).sort().join('|');
            if (roadSegmentKeys.has(key)) continue;
            roadSegmentKeys.add(key);
            const heading = Math.atan2(-(b.z-a.z), b.x-a.x);
            for (const [width, y, mat] of [[3.4,.022,shoulderMat],[2.92,.055,asphaltMat]] as [number, number, THREE.Material][]) {
              const road = new THREE.Mesh(new THREE.BoxGeometry(distance + .1, .055, width), mat);
              road.position.set((a.x+b.x)/2, y, (a.z+b.z)/2);
              road.rotation.y = heading; road.receiveShadow=true;scene.add(road);
            }
            if (distance > 2.2) {
              for (let dash = 1.8; dash < distance - .4; dash += 3.4) {
                const m = new THREE.Mesh(new THREE.BoxGeometry(Math.min(1.3,distance-dash),.015,.065),lineMarkMat);
                const u = dash/distance;
                m.position.set(a.x+(b.x-a.x)*u,.104,a.z+(b.z-a.z)*u);
                m.rotation.y=heading;scene.add(m);
              }
            }
          }
        }
        const vertices = leg.points.map(p => new THREE.Vector3(p.x,.21,p.z));
        for (const point of vertices) bounds.expandByPoint(point);
        const path = new THREE.Line(new THREE.BufferGeometry().setFromPoints(vertices),
          new THREE.LineBasicMaterial({color,transparent:true,opacity:.15,depthTest:false}));
        path.renderOrder=12;scene.add(path);routeLines.push(path);
      });
      const truck = new THREE.Group();
      const light = new THREE.MeshStandardMaterial({ color: 0xf1f2ee, roughness: 0.38, metalness: 0.18, emissive: 0x1f2a1f, emissiveIntensity: 0.24 });
      const body = new THREE.Mesh(new RoundedBoxGeometry(1.65, 0.86, 0.93,2,.035), light);
      body.position.set(0, 0.92, 0);
      truck.add(body);
      const cabin = new THREE.Mesh(new RoundedBoxGeometry(0.65, 0.82, 0.85,2,.07),
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
      const trim=new THREE.MeshStandardMaterial({color:0xaeb6b0,metalness:.72,roughness:.36});
      function detail(size:[number,number,number],position:[number,number,number],material:THREE.Material) {
        const mesh=new THREE.Mesh(new THREE.BoxGeometry(...size),material);mesh.position.set(...position);truck.add(mesh);return mesh;
      }
      // Insulated rear doors, locking rods and lower crash bar.
      detail([.035,.75,.86],[-.846,.95,0],trim);
      detail([.045,.7,.018],[-.87,.96,0],wheelMaterial);
      for(const side of [-1,1]) {
        detail([.045,.63,.023],[-.879,.95,side*.24],trim);
        detail([.055,.035,.12],[-.895,.93,side*.24],wheelMaterial);
        for(const y of [.69,1.2])detail([.045,.06,.13],[-.88,y,side*.36],trim);
        detail([.15,.07,.045],[1.33,.98,side*.48],trim);
        detail([.055,.19,.11],[1.38,1.05,side*.5],wheelMaterial);
        detail([.38,.3,.025],[1.08,1.02,side*.438],windscreen.material);
        detail([.31,.035,.06],[1.08,.49,side*.48],trim);
        const headlight=new THREE.MeshStandardMaterial({color:0xfff1c9,emissive:0xffe3a2,emissiveIntensity:.6});
        detail([.035,.12,.17],[1.46,.6,side*.28],headlight);
      }
      detail([.12,.12,.9],[1.47,.4,0],trim);
      detail([.08,.12,.84],[-.88,.4,0],trim);
      for(let vent=0;vent<7;vent++)detail([.015,.2,.035],[.818,1.53,-.28+vent*.09],wheelMaterial);
      detail([.04,.18,.31],[1.48,.61,0],wheelMaterial);
      for(let rib=0;rib<6;rib++)detail([.012,.025,.32],[1.505,.54+rib*.027,0],trim);
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
      const tag = makeLabel(vehicleDisplayName(route.vehicleId, routes), '#ffffff', 30);
      tag.position.set(0, 2.35, 0);
      tag.scale.set(3.3, .82, 1);
      truck.add(tag);
      truck.userData.vehicleId = route.vehicleId;
      truck.traverse(object=>{if(object instanceof THREE.Mesh){object.castShadow=true;object.receiveShadow=true;}});
      const point = visualVehiclePose(motion, 0, vehicleIds.indexOf(route.vehicleId), vehicleIds.length,
        positions[route.stops[0]?.nodeId] ?? motion.start, !projectedRoad);
      truck.position.set(point.x, .12, point.z);
      pickables.push(truck);
      scene.add(truck);
      trucks.set(route.vehicleId, { motion, truck, line: routeLines, wheels, light });
    });
    // Expand the camera for real road networks (which may span a wider area).
    if (!bounds.isEmpty()) {
      const center = bounds.getCenter(new THREE.Vector3());
      const size = bounds.getSize(new THREE.Vector3());
      controls.target.copy(center);
      const d = Math.max(34, size.x * 1.25, size.z * 1.25);
      camera.position.set(center.x + d * .24, d * 1.15, center.z + d * 1.0);
      camera.far = Math.max(400, d * 6);
      camera.updateProjectionMatrix();
      controls.maxDistance = Math.max(110, d * 3);
    }

    const overviewPosition = camera.position.clone();
    const overviewTarget = controls.target.clone();
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
        const index = vehicleIds.indexOf(vehicleId);
        const route = routes.find(item => item.vehicleId === vehicleId);
        const depot = route ? positions[route.stops[0]?.nodeId] ?? entry.motion.start : entry.motion.start;
        const p = visualVehiclePose(entry.motion, effectiveT, index, vehicleIds.length, depot, !roadProjection);
        entry.truck.position.set(p.x, .12, p.z);
        if (p.moving) entry.truck.rotation.y = p.heading;
        const movingSeconds = p.moving ? Math.max(0, effectiveT - lastSimulationTime) : 0;
        for (const wheel of entry.wheels) wheel.rotation.z -= Math.min(0.3, movingSeconds * 0.08);
        const selected = selectedRef.current === vehicleId;
        const affected = affectedRef.current.includes(vehicleId);
        entry.light.emissive.setHex(affected ? COLORS.alert : selected ? COLORS.chilled : 0x1f2a1f);
        entry.light.emissiveIntensity = affected ? 0.4 + 0.15 * Math.sin(now / 170) : selected ? 0.5 : 0.24;
        const highlighted = selectedRef.current ? selected : showAllRef.current || affected;
        for (const line of entry.line) (line.material as THREE.LineBasicMaterial).opacity = highlighted ? .96 : .085;
        entry.truck.scale.setScalar(selected ? 1.12 : 1);
        if (cameraModeRef.current === 'follow' && (followRef.current ?? focusRef.current) === vehicleId) cameraTarget.copy(entry.truck.position);
      });
      lastSimulationTime = t;
      if (resetCameraRef.current && cameraModeRef.current === 'overview') {
        const factor = Math.min(1, frameDt * 3.8);
        camera.position.lerp(overviewPosition, factor);
        controls.target.lerp(overviewTarget, factor);
        if (camera.position.distanceTo(overviewPosition) < .06 && controls.target.distanceTo(overviewTarget) < .06) {
          camera.position.copy(overviewPosition);
          controls.target.copy(overviewTarget);
          resetCameraRef.current = false;
        }
      }
      if (cameraModeRef.current === 'follow' && (followRef.current ?? focusRef.current) && trucks.has((followRef.current ?? focusRef.current)!)) {
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
      key.shadow.dispose();renderer.dispose();
      container.replaceChildren();
      scene.clear();
    };
  }, [sceneKey, height]); // eslint-disable-line react-hooks/exhaustive-deps

  const servedOrders = routes.reduce((n, r) => n + r.stops.filter((s) => s.kind === 'delivery').length, 0);
  const affectedHere = affectedVehicleIds.length > 0;
  const hasRoadGeometry = routes.length > 0 && routes.every(r => (r.roadCoordinates?.length ?? 0) > 1 && r.stopCoordinates?.length === r.stops.length);
  const cars = motionSummary.filter(item => item.motion).map(({route,motion}) => ({
    id:route.vehicleId,
    name:vehicleDisplayName(route.vehicleId, routes),
    status: vehicleReplayStatus(motion!, simTimeS),
    nextStop: route.stops.find(s => s.arrivalS > simTimeS)?.nodeId,
    color: `#${routeDisplayColor(route.vehicleId, routes).toString(16).padStart(6, '0')}`,
    affected:affectedVehicleIds.includes(route.vehicleId),
  }));

  return (
    <div className="twin-shell">
      <div className="twin-header">
        <div>
          
          <h3>冷链物流数字孪生</h3>
        </div>
        <div className="twin-topstats">
          <span><b>{warehouses.length}</b> 仓库</span>
          <span><b>{countDistinctVehicles(routes)}</b> 车辆</span>
          <span><b>{orderCount}</b> 订单</span>
          <span><b>{fmtClock(simTimeS)}</b> 仿真时间</span>
          <span className={eventActive || affectedHere ? 'alert-text' : ''}><i />{eventActive || affectedHere ? '异常处置中' : '运行正常'}</span>
        </div>
      </div>
      <div className="twin-toolbar">
        <div className="twin-toolbar-left"><b>配送网络沙盘</b><span>{hasRoadGeometry ? '地理道路坐标' : '拓扑示意道路 · 非 GPS'}</span></div>
        <div className="twin-toolbar-actions">
          <button type="button" className={cameraMode === 'overview' ? 'twin-tool active' : 'twin-tool'} onClick={() => {setCameraMode('overview');resetCameraRef.current=true;}}>全局鸟瞰</button>
          <button type="button" className={cameraMode === 'follow' ? 'twin-tool active' : 'twin-tool'}
            disabled={!effectiveSelected} onClick={() => setCameraMode('follow')}>跟随车辆</button>
          <button type="button" className={showAllRoutes ? 'twin-tool active' : 'twin-tool'}
            onClick={() => setShowAllRoutes(v => !v)}>{showAllRoutes ? '隐藏全部路线' : '显示全部路线'}</button>
        </div>
      </div>
      <div className="twin-stage" style={{ height }}>
        <div ref={containerRef} className="twin-canvas" />
        <div className="twin-legend">
          <span><i className="legend-dot chilled"/>冷藏配送中心</span>
          <span><i className="legend-dot frozen"/>配送站</span>
          <span><i className="legend-dot warning"/>异常车辆</span>
          <span><i className="legend-dot route"/>{hasRoadGeometry ? '实际道路形状' : '示意道路（非导航）'}</span>
        </div>
        <div className="twin-overlay-card">
          <span className="overlay-title">当前仿真时刻 · {fmtClock(simTimeS)}</span>
          <div><b>{cars.length}</b><small>轨迹车辆 / 可选择</small></div>
          <div><b>{cars.filter(c => c.status === 'moving').length}</b><small>按轨迹计算在途</small></div>
          <div><b>{servedOrders || '—'}</b><small>配送停靠点</small></div>
          <div><b>{affectedHere ? affectedVehicleIds.length : 0}</b><small>异常关联车辆</small></div>
        </div>
        {routes.length === 0 && (
          <div className="twin-waiting"><span>{waitingText}</span></div>
        )}
      </div>
      <div className="twin-vehicle-roster" aria-label="车辆运行列表">
        <div className="twin-roster-head"><strong>车队监控</strong><span>点击车辆可高亮路线与车辆 · 位置偏移仅用于示意画面避让</span></div>
        <div className="twin-roster-grid">
          {cars.map(car => <button type="button" key={car.id} className={`twin-car-card ${effectiveSelected === car.id ? 'selected' : ''}`}
            onClick={() => selectVehicle(effectiveSelected === car.id ? null : car.id)}>
            <span className="twin-car-swatch" style={{ backgroundColor: car.color }}/>
            <span className="twin-car-body"><b>{car.name}</b><small title={car.id}>{car.id.slice(0, 8)} · {car.nextStop ? `下一站 ${car.nextStop.slice(0, 8)}` : '无后续停靠'}</small></span>
            <span className={car.affected ? 'twin-car-status impacted' : 'twin-car-status'}>{car.affected ? '异常关注 · ' : ''}{({waiting:'待发车',moving:'行驶中',stopped:'站点停靠',completed:'已完成'} as const)[car.status]}</span>
          </button>)}
        </div>
        {!hasRoadGeometry && <p className="twin-visual-note">本页道路、车位与建筑是示意建模；算法节点顺序、时间、距离与费用保持原始数据。多车共线时仅将车模移到邻近可视车道，不改变真实轨迹。</p>}
      </div>
    </div>
  );
}
