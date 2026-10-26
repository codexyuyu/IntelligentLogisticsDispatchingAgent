// Owner: CODEX_FRONTEND. Schematic 2D layout for the digital twin scene.
// The backend matrix carries distances/durations but no geo coordinates, so node
// positions here are presentation-only: they preserve topology (warehouse -> stops)
// and stay deterministic for the same node set.
export type Vec2 = { x: number; z: number };

export function hash01(text: string): number {
  let h = 2166136261;
  for (let i = 0; i < text.length; i += 1) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return ((h >>> 0) % 100000) / 100000;
}

const WAREHOUSE_SLOTS: Vec2[] = [
  { x: -16, z: -7 },
  { x: -16, z: 9 },
  { x: -16, z: 1 },
  { x: -16, z: -15 },
];

/**
 * Lay out warehouse nodes on a fixed left column and every other node on a
 * jittered grid to the right, so routes flow warehouse -> market -> back.
 */
export function layoutNodes(nodeIds: string[], warehouseNodeIds: string[]): Record<string, Vec2> {
  const positions: Record<string, Vec2> = {};
  const whSet = new Set(warehouseNodeIds);
  let whSlot = 0;
  const others: string[] = [];
  for (const id of nodeIds) {
    if (whSet.has(id) && whSlot < WAREHOUSE_SLOTS.length) {
      positions[id] = { ...WAREHOUSE_SLOTS[whSlot] };
      whSlot += 1;
    } else {
      others.push(id);
    }
  }
  const cols = 5;
  const x0 = 2;
  const z0 = -14;
  const dx = 6.4;
  const dz = 5.6;
  others.forEach((id, index) => {
    const col = index % cols;
    const row = Math.floor(index / cols);
    const jitterX = (hash01(`${id}#x`) - 0.5) * 1.7;
    const jitterZ = (hash01(`${id}#z`) - 0.5) * 1.7;
    positions[id] = { x: x0 + col * dx + jitterX, z: z0 + row * dz + jitterZ };
  });
  return positions;
}
