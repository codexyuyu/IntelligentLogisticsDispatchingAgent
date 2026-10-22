// R23 minimal wiring check, intentionally runs with Node alone (no npm modules).
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { join } = require('node:path');
const root = join(__dirname, '..');
const read = (path) => readFileSync(join(root, path), 'utf8');
const app = read('src/App.tsx');
const consolePage = read('src/features/postgres/Page.tsx');
const api = read('src/features/postgres/api.ts');
const proxy = read('vite.config.ts');
assert.match(app, /postgres: PostgresPage/);
assert.match(app, /key: 'postgres', title: '本机数据库调度'/);
assert.match(read('src/features/orders/Page.tsx'), /<PgResourcePanel kind="orders" \/>/);
assert.match(read('src/features/vehicles/Page.tsx'), /<PgResourcePanel kind="vehicles" \/>/);
assert.match(proxy, /'\/local-pg':'http:\/\/127\.0\.0\.1:8000'/);
for (const endpoint of ['/orders', '/vehicles', '/summary', '/route', '/saved']) {
  assert.ok(consolePage.includes(`'${endpoint}`) || consolePage.includes(`\`${endpoint}`), `Missing endpoint ${endpoint}`);
}
assert.match(api, /local-pg\/pg-preview/);
assert.match(consolePage, /acknowledge_store_simulation_only: true/);
assert.match(consolePage, /pg_simulation_previews/);
assert.match(consolePage, /iframe/);
console.log('R23 frontend wiring smoke check: PASS (10 checks; no browser build claimed)');
