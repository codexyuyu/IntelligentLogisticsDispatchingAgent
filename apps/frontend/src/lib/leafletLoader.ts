/** Leaflet is optional at build time. CDN load keeps this ZIP usable offline
 * without installing another npm dependency; a clearly-labelled schematic
 * fallback renders if CDN or live OSM tiles are unavailable. */
export interface LeafletPoint { x: number; y: number }
export interface LeafletMarker {
  setLatLng(p: [number, number]): LeafletMarker;
  setIcon(icon: unknown): LeafletMarker;
  addTo(map: LeafletMap): LeafletMarker;
  bindTooltip(html: string, options?: Record<string, unknown>): LeafletMarker;
  on(event: string, callback: () => void): LeafletMarker;
  remove(): void;
  getElement(): HTMLElement | undefined;
  setZIndexOffset(offset: number): LeafletMarker;
}
export interface LeafletMap {
  setView(latlng: [number, number], zoom: number, options?: Record<string, unknown>): LeafletMap;
  fitBounds(bounds: [number, number][], options?: Record<string, unknown>): LeafletMap;
  panTo(latlng: [number, number], options?: Record<string, unknown>): LeafletMap;
  invalidateSize(): void;
  remove(): void;
  latLngToLayerPoint(p: [number, number]): LeafletPoint;
  layerPointToLatLng(p: LeafletPoint): { lat: number; lng: number };
  on(event: string, callback: () => void): LeafletMap;
}
export interface LeafletPolyline {
  setStyle(style: Record<string, unknown>): LeafletPolyline;
  addTo(map: LeafletMap): LeafletPolyline;
  remove(): void;
}
export interface LeafletLibrary {
  map(node: HTMLElement, options?: Record<string, unknown>): LeafletMap;
  tileLayer(url: string, options?: Record<string, unknown>): { addTo(map: LeafletMap): unknown; on(event: string, cb: () => void): unknown };
  marker(latlng: [number, number], options?: Record<string, unknown>): LeafletMarker;
  polyline(points: [number, number][], options?: Record<string, unknown>): LeafletPolyline;
  circleMarker(point: [number, number], options?: Record<string, unknown>): { addTo(map: LeafletMap): unknown; bindTooltip(text: string, options?: Record<string, unknown>): unknown };
  divIcon(options: Record<string, unknown>): unknown;
}

declare global { interface Window { L?: LeafletLibrary } }
let request: Promise<LeafletLibrary> | null = null;
const LEAFLET_JS = 'https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js';
const LEAFLET_CSS = 'https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css';

export function loadLeaflet(): Promise<LeafletLibrary> {
  if (window.L) return Promise.resolve(window.L);
  if (request) return request;
  request = new Promise<LeafletLibrary>((resolve, reject) => {
    if (!document.querySelector('link[data-demo-leaflet]')) {
      const link = document.createElement('link');
      link.rel = 'stylesheet'; link.href = LEAFLET_CSS; link.dataset.demoLeaflet = 'true';
      document.head.appendChild(link);
    }
    const script = document.createElement('script');
    script.src = LEAFLET_JS;
    script.async = true;
    script.referrerPolicy = 'strict-origin-when-cross-origin';
    script.onload = () => window.L ? resolve(window.L) : reject(new Error('Leaflet 未初始化'));
    script.onerror = () => reject(new Error('地图组件 CDN 暂不可用'));
    document.head.appendChild(script);
  }).catch(error => { request = null; throw error; });
  return request;
}
