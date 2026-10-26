const fs = require('node:fs');
const assert = require('node:assert/strict');
const src = fs.readFileSync('src/features/postgres/Page.tsx', 'utf8');
const api = fs.readFileSync('src/features/postgres/api.ts', 'utf8');
assert.match(src, /R29 单仓业务检查/);
assert.match(src, /历史路线/);
assert.match(src, /migrate_pg_r29_local\.ps1/);
assert.match(api, /r29_active_warehouse/);
console.log('R29 frontend active-warehouse wiring: PASS');
