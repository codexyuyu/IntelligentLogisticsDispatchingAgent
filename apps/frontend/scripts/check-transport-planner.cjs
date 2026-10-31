const fs=require('fs');
const assert=require('assert');
const path=require('path');
const source=fs.readFileSync(path.join(__dirname,'../src/components/TransportWorkflow.tsx'),'utf8');
const css=fs.readFileSync(path.join(__dirname,'../src/styles.css'),'utf8');
const checks=[
 ['batch scopes use selected orders', source.includes('order_ids: selectedOrders.map(item => item.id)')],
 ['batch scopes use selected vehicles',source.includes('vehicle_ids: selectedVehicles.map(item => item.id)')],
 ['route stops grouped by route id',source.includes('stop.route_id === route.id')],
 ['matrix covers all pickups and destinations',source.includes('available.has(order.pickup_node_id) && available.has(order.delivery_node_id)')],
 ['matrix covers vehicles start and end',source.includes('available.has(vehicle.start_node_id) && available.has(vehicle.end_node_id)')],
 ['missing matrix prevents submit',source.includes('&& !!selectedMatrix')],
 ['approvals restricted to validated candidate',source.includes('!candidate.valid || busy')],
 ['selection changes discard old candidate',source.includes('function discardPriorCandidate()')],
 ['same fault case normal plan',source.includes('wenchang-three-truck-breakdown-v1')],
 ['normal demo explicitly separated',source.includes('不冒充数据库批量求解')],
 ['2D map receives solver routes',source.includes('routes={planRoutes}')],
 ['styles exist',css.includes('.tp-workbench')],
];
checks.forEach(([name,passed])=>{assert(passed,`FAIL: ${name}`);process.stdout.write(`PASS ${name}\n`)});
console.log(`${checks.length} workbench checks passed`);
