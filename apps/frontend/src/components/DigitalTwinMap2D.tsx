/** Guangxi University of Science and Technology (Wenchang) 2D demo replay.
 * The OSM basemap is real, but this UI NEVER claims a route is real navigation.
 * Stops, vehicles and clock are taken from the solver's authoritative tracks.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { TwinRoute } from '../appTypes';
import { fmtClock } from '../lib/format';
import { loadLeaflet, type LeafletLibrary, type LeafletMap, type LeafletMarker, type LeafletPolyline } from '../lib/leafletLoader';
import {
  WENCHANG_CAMPUS, buildDemoMotion, createDemoNodes, demoRouteColor, sampleDemoMotion, visualMarkerOffset,
  type DemoMapMotion, type DemoPose, type LatLng, type DemoMapNode,
} from '../lib/liuzhouDemoMap';

type Props = {
  routes: TwinRoute[];
  nodeIds?: string[];
  simTimeS: number;
  selectedVehicleId?: string | null;
  onPickVehicle?: (id: string | null) => void;
  affectedVehicleIds?: string[];
  eventActive?: boolean;
  height?: number;
  title?: string;
  /** Explicit presentation-only vehicles, NOT the persisted simulator fleet. */
  showcase?: boolean;
  followVehicleId?: string | null;
  /** Playback clock drives continuous motion without rerendering the whole app. */
  playing?: boolean;
  playbackSpeed?: number;
  /** Exact synthetic stop coordinates when supplied by the breakdown solver. */
  demoNodes?: Record<string, DemoMapNode>;
  /** Vehicle ids that become immobilized after the scenario incident. */
  haltedVehicleIds?: string[];
};

type MapInstance = { map: LeafletMap; markers: Map<string, LeafletMarker>;
  polylines: Map<string, LeafletPolyline>; routePoints: LatLng[] };

function labelForVehicle(index: number): string { return `冷链车 ${String(index + 1).padStart(2, '0')}`; }
function statusLabel(status: DemoPose['state']): string {
  return { waiting: '等待发车', driving: '配送途中', unloading: '站点停靠', completed: '任务完成' }[status];
}
function safeLabel(text: string): string {
  return text.replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char] ?? char);
}
function markerIcon(L: LeafletLibrary, index: number, color: string, active: boolean, alert: boolean) {
  return L.divIcon({ className: 'coldmap-marker-base', iconSize: [48, 48], iconAnchor: [24, 24],
    html: `<div class="coldmap-truck ${active ? 'is-picked' : ''} ${alert ? 'is-alert' : ''}" style="--truck-color:${color}"><span class="coldmap-truck-symbol">🚚</span><b>${index + 1}</b></div>` });
}
function nodeIcon(L: LeafletLibrary, isDepot: boolean, number: number) {
  return L.divIcon({ className: 'coldmap-marker-base', iconSize: [32, 32], iconAnchor: [16, 16],
    html: `<div class="coldmap-node ${isDepot ? 'is-depot' : ''}">${isDepot ? '仓' : String(number + 1)}</div>` });
}
const BOUNDS: [number, number][] = [[24.300, 109.405], [24.360, 109.489]];
export default function DigitalTwinMap2D({ routes, nodeIds = [], simTimeS, selectedVehicleId,
  onPickVehicle, affectedVehicleIds = [], eventActive = false, height = 510, title, showcase = false, followVehicleId = null, playing = false, playbackSpeed = 1, demoNodes, haltedVehicleIds = [] }: Props) {
  const rootRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapInstance | null>(null);
  const [loadState, setLoadState] = useState<'loading' | 'ready' | 'fallback'>('loading');
  const [loadedTiles, setLoadedTiles] = useState(true);
  const [picked, setPicked] = useState<string | null>(null);
  const [follow, setFollow] = useState(false);
  const [showAll, setShowAll] = useState(true);
  const [viewRevision, setViewRevision] = useState(0);
  const selected = selectedVehicleId ?? picked;
  const pickRef = useRef(onPickVehicle);
  pickRef.current = onPickVehicle;
  const selectedRef = useRef(selected);
  selectedRef.current = selected;
  const dataKey = useMemo(() => JSON.stringify({routes, nodes: nodeIds, demoNodes}), [routes, nodeIds]);
  const nodes = useMemo(() => demoNodes ? {...createDemoNodes(routes, nodeIds), ...demoNodes} : createDemoNodes(routes, nodeIds), [dataKey]); // eslint-disable-line react-hooks/exhaustive-deps
  const motionRows = useMemo(() => routes.map((route, index) => ({ route, index,
    motion: buildDemoMotion(route, nodes) })).filter((row): row is {route: TwinRoute; index: number; motion: DemoMapMotion} => !!row.motion), [dataKey]); // eslint-disable-line react-hooks/exhaustive-deps
  const poses = useMemo(() => motionRows.map(row => ({ ...row, pose: sampleDemoMotion(row.motion, simTimeS) })), [motionRows, simTimeS]);
  const affectedSet = useMemo(() => new Set(affectedVehicleIds), [affectedVehicleIds.join('|')]); // eslint-disable-line react-hooks/exhaustive-deps
  const haltedSet = useMemo(() => new Set(haltedVehicleIds), [haltedVehicleIds.join("|")]); // eslint-disable-line react-hooks/exhaustive-deps
  const color = (index: number) => demoRouteColor(index);
  const select = useCallback((vehicleId: string | null) => {
    setPicked(vehicleId); pickRef.current?.(vehicleId);
  }, []);
  const routesRef = useRef(motionRows);
  routesRef.current = motionRows;
  const selectCallbackRef = useRef(select);
  selectCallbackRef.current = select;

  useEffect(() => {
    let cancelled = false;
    let timer: number | undefined;
    setLoadState('loading');
    setLoadedTiles(true);
    void loadLeaflet().then(L => {
      if (cancelled || !rootRef.current) return;
      const map = L.map(rootRef.current, { zoomControl: true, scrollWheelZoom: false, preferCanvas: true,
        attributionControl: true }).setView(WENCHANG_CAMPUS, 13);
      // OSM's public standard raster service: normal viewport only, no prefetch.
      // Attribution is always visible and served via HTTPS.
      const tileLayer = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 18, minZoom: 10, attribution: '© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap contributors</a>',
      });
      let tileErrors = 0, tileSuccesses = 0;
      tileLayer.on('tileerror', () => { tileErrors += 1; if (tileErrors >= 8 && tileSuccesses === 0 && !cancelled) setLoadedTiles(false); });
      tileLayer.on('tileload', () => { tileSuccesses += 1; if (!cancelled) setLoadedTiles(true); });
      tileLayer.addTo(map);
      const markers = new Map<string, LeafletMarker>();
      const polylines = new Map<string, LeafletPolyline>();
      const allPoints: LatLng[] = [];
      const visibleNodeIds = new Set(routesRef.current.flatMap(({ motion }) => motion.stops.map(s => s.nodeId)));
      Object.values(nodes).filter(node => visibleNodeIds.has(node.id)).forEach((node, nodeIndex) => {
        L.marker(node.point, { icon: nodeIcon(L, node.isDepot, nodeIndex), zIndexOffset: node.isDepot ? 80 : 0 })
          .bindTooltip(safeLabel(node.label), { direction: 'top', offset: [0, -13] }).addTo(map);
        allPoints.push(node.point);
      });
      const campusMark = L.circleMarker(WENCHANG_CAMPUS, {radius: 5, color: '#166e69', fillColor:'#ffffff', fillOpacity: 1, weight: 2});
      campusMark.addTo(map);
      campusMark.bindTooltip('广西科技大学 · 文昌校区（地理定位参考）', { direction: 'top' });
      routesRef.current.forEach(({route, index, motion}) => {
        const stroke = L.polyline(motion.polyline, { color: color(index), weight: 5, opacity: 0.82,
          lineJoin: 'round', lineCap: 'round', dashArray: '10 7' }).addTo(map);
        polylines.set(route.vehicleId, stroke);
        allPoints.push(...motion.polyline);
        const marker = L.marker(motion.start, {icon: markerIcon(L, index, color(index), selectedRef.current === route.vehicleId, false),
          zIndexOffset: 300 + index})
          .bindTooltip(`${labelForVehicle(index)} · ${safeLabel(route.vehicleId.slice(0, 8))}`, {direction: 'top', offset: [0,-22]})
          .on('click', () => selectCallbackRef.current(route.vehicleId)).addTo(map);
        markers.set(route.vehicleId, marker);
      });
      mapRef.current = {map, markers, polylines, routePoints: allPoints};
      // Refresh display-only depot parking offsets after user zooms the map.
      map.on('zoomend', () => { if (!cancelled) setViewRevision(v => v + 1); });
      map.fitBounds(BOUNDS, {padding: [20, 20], maxZoom: 13});
      window.requestAnimationFrame(() => map.invalidateSize());
      timer = window.setTimeout(() => { if (!cancelled) map.invalidateSize(); }, 120);
      setLoadState('ready');
      // First marker update is performed by the time-dependent effect below.
    }).catch(() => { if (!cancelled) setLoadState('fallback'); });
    return () => {
      cancelled = true; if (timer) window.clearTimeout(timer);
      const instance = mapRef.current;
      if (instance) { instance.map.remove(); mapRef.current = null; }
    };
  }, [dataKey]); // eslint-disable-line react-hooks/exhaustive-deps

  // Update marker *styles* only when selection/incident changes. Do NOT call
  // Calling setIcon() on clock ticks destroys/recreates the DOM
  // node on each call, which was causing the visible 1Hz truck flashing.
  useEffect(() => {
    const instance = mapRef.current;
    if (!instance || loadState !== 'ready') return;
    motionRows.forEach(({route, index}) => {
      const marker = instance.markers.get(route.vehicleId);
      const icon = marker?.getElement()?.querySelector('.coldmap-truck');
      icon?.classList.toggle('is-picked', selected === route.vehicleId);
      icon?.classList.toggle('is-alert', eventActive && affectedSet.has(route.vehicleId));
      marker?.setZIndexOffset?.(selected === route.vehicleId ? 850 : 300 + index);
      const polyline = instance.polylines.get(route.vehicleId);
      const dim = Boolean(selected && selected !== route.vehicleId);
      polyline?.setStyle({opacity: dim ? 0.16 : showAll || selected === route.vehicleId ? 0.88 : 0,
        weight: selected === route.vehicleId ? 7 : 4});
    });
  }, [loadState, motionRows, selected, showAll, eventActive, affectedSet]);

  // Interpolate the vehicle pose along the SAME visible polyline with an RAF
  // playback clock. This avoids 1-second (and 30x speed) position hops while
  // keeping React/API updates on the existing whole-second backend clock.
  useEffect(() => {
    const instance = mapRef.current;
    if (!instance || loadState !== 'ready') return;
    let raf = 0;
    const startWall = performance.now();
    let lastPanWall = 0;
    const render = (wall: number) => {
      const elapsed = playing ? Math.min(Math.max(0, (wall - startWall) / 1000) * playbackSpeed, playbackSpeed) : 0;
      const frameS = simTimeS + elapsed;
      motionRows.forEach(({route, index, motion}) => {
        const marker = instance.markers.get(route.vehicleId);
        if (!marker) return;
        const pose = sampleDemoMotion(motion, frameS);
        const spread = visualMarkerOffset(motion, frameS, index, motionRows.length);
        if (Math.abs(spread.x) + Math.abs(spread.y) < 0.01) marker.setLatLng(pose.point);
        else {
          const base = instance.map.latLngToLayerPoint(pose.point);
          const adjusted = instance.map.layerPointToLatLng({x:base.x + spread.x, y:base.y + spread.y});
          marker.setLatLng([adjusted.lat, adjusted.lng]);
        }
        if ((follow || followVehicleId === selected) && selected === route.vehicleId && wall - lastPanWall > 90) {
          lastPanWall = wall;
          instance.map.panTo(pose.point, {animate:false});
        }
      });
      if (playing) raf = window.requestAnimationFrame(render);
    };
    render(startWall);
    return () => window.cancelAnimationFrame(raf);
  }, [loadState, simTimeS, motionRows, playing, playbackSpeed, selected, follow, followVehicleId, viewRevision]);

  const resetView = () => { setFollow(false); mapRef.current?.map.fitBounds(BOUNDS, {padding:[20,20], maxZoom:13}); };
  return <section className="coldmap-shell" aria-label={title ?? '柳州文昌校区示范场景 · 运输二维地图'}>
    <div className="coldmap-bar">
      <div className="coldmap-bar-title"><strong>柳州 · 文昌校区周边</strong><span>真实道路底图 + 模拟配送路线 · 非 GPS</span></div>
      <div className="coldmap-actions">
        <button type="button" className="btn btn-sm btn-ghost" onClick={resetView}>全局地图</button>
        <button type="button" className={`btn btn-sm ${follow ? 'btn-primary' : 'btn-ghost'}`} disabled={!selected} onClick={() => setFollow(value => !value)}>跟随车辆</button>
        <button type="button" className={`btn btn-sm ${showAll ? 'btn-ghost' : 'btn-primary'}`} disabled={!selected} onClick={() => setShowAll(v => !v)}>{showAll ? '仅看选中路线' : '显示全部路线'}</button>
      </div>
    </div>
    <div className="coldmap-map-region" style={{height}}>
      <div ref={rootRef} className="coldmap-leaflet" aria-label="OpenStreetMap 柳州市真实道路底图" />
      {(loadState !== 'ready' || !loadedTiles) && <div className="coldmap-offline">
        <DemoFallbackMap rows={poses} selected={selected} onPick={select}/>
        <div className="coldmap-offline-note">{loadState === 'loading' ? '正在连接真实地图底图… 显示本地示意预览' : '网络或地图瓦片不可用 · 当前仅显示离线示意背景'}<br/>演示车辆路线不代表实际导航。</div>
      </div>}

      <div className="coldmap-time-tag">模拟时间 {fmtClock(simTimeS)} <span> · {showcase ? '四车独立演示' : '调度轨迹'}</span></div>
      <div className="coldmap-stats"><b>{motionRows.length}</b><span>载入车辆</span><b>{poses.filter(r => r.pose.state === 'driving').length}</b><span>运输途中</span></div>
      <div className="coldmap-legend"><span className="coldmap-dot-depot"/>虚拟配送中心 <span className="coldmap-dot-stop"/>模拟配送点 <span className="coldmap-dashed"/>模拟路径</div>
    </div>
    <div className="coldmap-roster">
      <div className="coldmap-roster-heading"><strong>车队监控</strong><span>点击车辆查看轨迹 · 支持跟随视角</span></div>
      <div className="coldmap-roster-items">
        {poses.length ? poses.map(({route, index, pose}) => <button type="button" key={route.vehicleId}
          className={`coldmap-vehicle-card ${selected === route.vehicleId ? 'is-selected' : ''}`}
          onClick={() => select(route.vehicleId)} style={{'--vehicle-color': color(index)} as React.CSSProperties}>
          <span className="coldmap-vehicle-num">{index + 1}</span><span className="coldmap-vehicle-info"><b>{labelForVehicle(index)}</b><small>{eventActive && haltedSet.has(route.vehicleId) ? '故障停运' : statusLabel(pose.state)} · {pose.nextNodeId && nodes[pose.nextNodeId] ? nodes[pose.nextNodeId].label : '无后续站点'}</small></span>
          {eventActive && affectedSet.has(route.vehicleId) && <span className="coldmap-vehicle-alert">异常关注</span>}
        </button>) : <span className="coldmap-empty">暂无调度轨迹，完成调度或载入模拟记录后显示。</span>}
      </div>
    </div>
    <p className="coldmap-disclaimer">示范位置：广西科技大学文昌校区周边。仓库及客户点均为<strong>虚构演示点</strong>；彩色虚线为<strong>模拟路径</strong>，不保证与道路重合；车辆数量、停靠顺序及时间取自当前轨迹。里程和费用采用调度服务指标。</p>
  </section>;
}

/** No third-party tile scraping: an in-app SVG fallback if network is missing. */
function DemoFallbackMap({rows, selected, onPick}: {rows: {route:TwinRoute;index:number;pose:DemoPose;motion:DemoMapMotion}[];
  selected:string|null;onPick:(id:string|null)=>void}) {
  const x = (lng: number) => 100 + (lng - 109.402) / (109.492 - 109.402) * 850;
  const y = (lat: number) => 580 - (lat - 24.297) / (24.362 - 24.297) * 530;
  return <svg className="coldmap-fallback-svg" viewBox="0 0 1050 640" preserveAspectRatio="xMidYMid slice" aria-label="离线柳州示意路线">
    <rect width="1050" height="640" fill="#e7ece7" />
    <path d="M70 100 L980 100 M70 220 L980 220 M70 350 L980 350 M70 480 L980 480 M180 45 L180 610 M355 45 L355 610 M555 45 L555 610 M785 45 L785 610" stroke="#ffffff" strokeWidth="22" fill="none"/>
    <path d="M70 100 L980 100 M70 220 L980 220 M70 350 L980 350 M70 480 L980 480 M180 45 L180 610 M355 45 L355 610 M555 45 L555 610 M785 45 L785 610" stroke="#c2c8c5" strokeWidth="1" fill="none"/>
    <path d="M70 185 Q390 310 1030 120" stroke="#a9d7df" strokeWidth="43" fill="none" opacity="0.75"/>
    <path d="M75 185 Q390 310 1030 120" stroke="#ceeef0" strokeWidth="28" fill="none"/>
    <rect x={x(WENCHANG_CAMPUS[1])-56} y={y(WENCHANG_CAMPUS[0])-31} width="112" height="62" rx="9" fill="#c4d5b6" stroke="#8aac80" strokeWidth="2"/>
    <text x={x(WENCHANG_CAMPUS[1])} y={y(WENCHANG_CAMPUS[0])-4} textAnchor="middle" fontSize="13" fill="#355743">广西科技大学</text>
    <text x={x(WENCHANG_CAMPUS[1])} y={y(WENCHANG_CAMPUS[0])+16} textAnchor="middle" fontSize="12" fill="#355743">文昌校区（示意）</text>
    {rows.map(({route,index,motion}) => <polyline key={route.vehicleId} fill="none" stroke={demoRouteColor(index)} strokeWidth={selected===route.vehicleId?6:4}
      strokeDasharray="10 7" opacity={selected && selected!==route.vehicleId ? .22 : .8} points={motion.polyline.map(p=>`${x(p[1])},${y(p[0])}`).join(' ')}/>)}
    {rows.map(({route,index,pose}) => <g key={route.vehicleId} transform={`translate(${x(pose.point[1]) + (pose.state==='waiting' ? (index % 2) * 29 : 0)},${y(pose.point[0]) + (pose.state==='waiting' ? Math.floor(index / 2) * 29 : 0)})`}
      onClick={()=>onPick(route.vehicleId)} role="button" aria-label={`选择冷链车 ${index+1}`} tabIndex={0}
      onKeyDown={e=>{if(e.key==='Enter')onPick(route.vehicleId);}} style={{cursor:'pointer'}}>
      <circle r="19" fill="#ffffff" stroke={demoRouteColor(index)} strokeWidth="4"/>
      <text textAnchor="middle" dominantBaseline="central" fontSize="17">🚚</text><text y="-27" textAnchor="middle" fontSize="12" fontWeight="bold" fill="#334155">{index+1}</text>
    </g>)}
    <text x="60" y="605" fontSize="14" fill="#56696b">离线示意底图 · 非真实道路</text>
  </svg>;
}
