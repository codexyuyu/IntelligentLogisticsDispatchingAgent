import { reactive } from 'vue'

const now = new Date()
const iso = (offsetDays = 0, hour = 8) => {
  const d = new Date(now)
  d.setDate(d.getDate() + offsetDays)
  d.setHours(hour, 0, 0, 0)
  return d.toISOString().slice(0, 16)
}

export const schedulingState = reactive({
  supplyPlans: [
    { id: 1, code: 'SUP-001', farmer: '青河村一组', product: '脐橙', expectedTime: iso(0, 9), expectedQty: 120, actualTime: '', actualQty: 0, location: '青河村东坡基地', status: '待到货' },
    { id: 2, code: 'SUP-002', farmer: '青河村二组', product: '脐橙', expectedTime: iso(0, 11), expectedQty: 90, actualTime: iso(0, 11), actualQty: 96, location: '青河村河谷基地', status: '已到货' },
    { id: 3, code: 'SUP-003', farmer: '新桥家庭农场', product: '葡萄', expectedTime: iso(1, 8), expectedQty: 80, actualTime: '', actualQty: 0, location: '新桥村设施园', status: '待到货' },
    { id: 4, code: 'SUP-004', farmer: '丰收合作小组', product: '脐橙', expectedTime: iso(1, 14), expectedQty: 150, actualTime: '', actualQty: 0, location: '丰收村高山基地', status: '待到货' },
    { id: 5, code: 'SUP-005', farmer: '南坪种植基地', product: '葡萄', expectedTime: iso(2, 10), expectedQty: 110, actualTime: '', actualQty: 0, location: '南坪村示范园', status: '预计延迟' }
  ],
  batches: [
    { id: 1, code: 'BAT-OR-001', product: '脐橙', grade: 'A', quantity: 180, sourceIds: [1, 2], preCooling: true, expectedInbound: iso(0, 16), maxStorageDays: 14, status: '待调度', risk: '低' },
    { id: 2, code: 'BAT-GR-001', product: '葡萄', grade: 'A', quantity: 80, sourceIds: [3], preCooling: true, expectedInbound: iso(1, 12), maxStorageDays: 7, status: '待调度', risk: '中' }
  ],
  orders: [
    { id: 1, code: 'ORD-001', customer: '县城生鲜超市', product: '脐橙', quantity: 100, grade: 'A', latestDelivery: iso(4, 16), minShelfLife: 5, status: '待匹配' },
    { id: 2, code: 'ORD-002', customer: '区域批发市场', product: '葡萄', quantity: 60, grade: 'A', latestDelivery: iso(3, 10), minShelfLife: 3, status: '待匹配' },
    { id: 3, code: 'ORD-003', customer: '社区电商平台', product: '脐橙', quantity: 80, grade: 'B及以上', latestDelivery: iso(6, 14), minShelfLife: 4, status: '待匹配' }
  ],
  coldRooms: [
    { id: 1, code: 'CR-01', warehouse: '中心冷库A', capacity: 300, used: 180, minTemp: 2, maxTemp: 6, categories: '柑橘类', preCooling: true, cleaningHours: 2, switchHours: 1, deviceStatus: '正常', cost: 1.8 },
    { id: 2, code: 'CR-02', warehouse: '中心冷库A', capacity: 220, used: 80, minTemp: 0, maxTemp: 4, categories: '葡萄/浆果', preCooling: true, cleaningHours: 3, switchHours: 2, deviceStatus: '正常', cost: 2.2 },
    { id: 3, code: 'CR-03', warehouse: '乡镇冷库B', capacity: 260, used: 0, minTemp: 2, maxTemp: 8, categories: '柑橘类/综合', preCooling: false, cleaningHours: 2, switchHours: 2, deviceStatus: '正常', cost: 1.5 },
    { id: 4, code: 'CR-04', warehouse: '乡镇冷库B', capacity: 180, used: 120, minTemp: 0, maxTemp: 5, categories: '葡萄/综合', preCooling: false, cleaningHours: 3, switchHours: 2, deviceStatus: '维护中', cost: 1.6 }
  ],
  timeline: [
    { roomId: 1, roomCode: 'CR-01', blocks: [
      { type: 'STORAGE', label: '脐橙 BAT-OR-OLD', start: 0, width: 34, risk: '低' },
      { type: 'CLEANING', label: '清洁', start: 34, width: 8 },
      { type: 'STORAGE', label: 'BAT-OR-001', start: 42, width: 36, risk: '低' }
    ]},
    { roomId: 2, roomCode: 'CR-02', blocks: [
      { type: 'PRE_COOLING', label: 'BAT-GR-001预冷', start: 8, width: 16, risk: '中' },
      { type: 'STORAGE', label: 'BAT-GR-001', start: 24, width: 38, risk: '中' },
      { type: 'CLEANING', label: '清洁', start: 62, width: 10 }
    ]},
    { roomId: 3, roomCode: 'CR-03', blocks: [
      { type: 'IDLE', label: '可用时间窗', start: 0, width: 100 }
    ]},
    { roomId: 4, roomCode: 'CR-04', blocks: [
      { type: 'MAINTENANCE', label: '设备维护', start: 0, width: 46 },
      { type: 'STORAGE', label: '历史批次', start: 46, width: 34, risk: '低' }
    ]}
  ],
  schedules: [
    {
      id: 1,
      code: 'SCH-20260801-01',
      version: '原方案',
      status: '待确认',
      createdAt: iso(0, 8),
      objective: '履约优先 + 品质风险最小',
      metrics: { utilization: 68, fulfillment: 96, onTimeInbound: 92, highRisk: 1, totalCost: 1680, changed: 0, solveMs: 436 },
      assignments: [
        { batch: 'BAT-OR-001', product: '脐橙', room: 'CR-01', inbound: iso(0, 16), outbound: iso(4, 8), order: 'ORD-001', vehicle: '粤A·CL102', cost: 720, risk: '低', feasible: true },
        { batch: 'BAT-GR-001', product: '葡萄', room: 'CR-02', inbound: iso(1, 12), outbound: iso(3, 6), order: 'ORD-002', vehicle: '粤A·CL206', cost: 960, risk: '中', feasible: true }
      ]
    }
  ],
  events: [
    { id: 1, code: 'EVT-001', type: '冷间故障', source: 'CR-02', eventTime: iso(1, 18), impact: '葡萄批次 BAT-GR-001 需转移', severity: '高', status: '待重调度' }
  ],
  reschedules: []
})

let ids = { supply: 6, batch: 3, order: 4, event: 2, schedule: 2 }

export function addSupplyPlan(payload) {
  schedulingState.supplyPlans.unshift({
    id: ids.supply,
    code: `SUP-${String(ids.supply).padStart(3, '0')}`,
    actualTime: '', actualQty: 0, status: '待到货',
    ...payload
  })
  ids.supply += 1
}

export function confirmSupplyArrival(id) {
  const item = schedulingState.supplyPlans.find(x => x.id === id)
  if (!item) return
  item.actualTime = new Date().toISOString().slice(0, 16)
  item.actualQty = item.expectedQty
  item.status = '已到货'
}

export function composeBatch(sourceIds, payload) {
  const batch = {
    id: ids.batch,
    code: `BAT-${payload.product === '葡萄' ? 'GR' : 'OR'}-${String(ids.batch).padStart(3, '0')}`,
    sourceIds: [...sourceIds],
    status: '待调度', risk: payload.product === '葡萄' ? '中' : '低',
    ...payload
  }
  schedulingState.batches.unshift(batch)
  sourceIds.forEach(id => {
    const item = schedulingState.supplyPlans.find(x => x.id === id)
    if (item) item.status = '已组批'
  })
  ids.batch += 1
  return batch
}

export function addOrder(payload) {
  schedulingState.orders.unshift({
    id: ids.order,
    code: `ORD-${String(ids.order).padStart(3, '0')}`,
    status: '待匹配',
    ...payload
  })
  ids.order += 1
}

export function generateSchedule(options = {}) {
  const batchList = schedulingState.batches.filter(x => x.status === '待调度')
  const assignments = batchList.map((batch, index) => {
    const room = schedulingState.coldRooms.find(r => r.deviceStatus === '正常' && r.categories.includes(batch.product === '脐橙' ? '柑橘' : batch.product)) || schedulingState.coldRooms[index % schedulingState.coldRooms.length]
    const order = schedulingState.orders.find(o => o.product === batch.product && o.status === '待匹配')
    return {
      batch: batch.code,
      product: batch.product,
      room: room.code,
      inbound: batch.expectedInbound,
      outbound: order?.latestDelivery || iso(5, 8),
      order: order?.code || '暂未匹配',
      vehicle: index % 2 ? '粤A·CL206' : '粤A·CL102',
      cost: Math.round(batch.quantity * room.cost + 480),
      risk: batch.risk,
      feasible: room.deviceStatus === '正常'
    }
  })
  const schedule = {
    id: ids.schedule,
    code: `SCH-202608-${String(ids.schedule).padStart(2, '0')}`,
    version: '新方案',
    status: '待确认',
    createdAt: new Date().toISOString().slice(0, 16),
    objective: options.objective || '履约优先 + 品质风险最小',
    metrics: {
      utilization: 72,
      fulfillment: assignments.every(x => x.feasible) ? 98 : 88,
      onTimeInbound: 94,
      highRisk: assignments.filter(x => x.risk === '高').length,
      totalCost: assignments.reduce((s, x) => s + x.cost, 0),
      changed: assignments.length,
      solveMs: 382
    },
    assignments
  }
  schedulingState.schedules.unshift(schedule)
  ids.schedule += 1
  return schedule
}

export function confirmSchedule(id) {
  const schedule = schedulingState.schedules.find(x => x.id === id)
  if (!schedule) return
  schedule.status = '已确认'
  schedule.assignments.forEach(a => {
    const batch = schedulingState.batches.find(b => b.code === a.batch)
    if (batch) batch.status = '已排程'
    const order = schedulingState.orders.find(o => o.code === a.order)
    if (order) order.status = '已匹配'
  })
}

export function addAbnormalEvent(payload) {
  schedulingState.events.unshift({
    id: ids.event,
    code: `EVT-${String(ids.event).padStart(3, '0')}`,
    status: '待重调度',
    ...payload
  })
  ids.event += 1
}

export function generateReschedule(eventId) {
  const event = schedulingState.events.find(x => x.id === eventId)
  const base = schedulingState.schedules[0]
  if (!event || !base) return null
  const changed = base.assignments.map((item, index) => ({
    ...item,
    room: item.room === event.source ? 'CR-03' : item.room,
    inbound: item.room === event.source ? iso(2, 8) : item.inbound,
    cost: item.cost + (item.room === event.source ? 260 : 0),
    risk: item.room === event.source ? '中' : item.risk,
    changeNote: item.room === event.source ? `${event.source}不可用，转移至CR-03并延后入库` : '不受影响，保持原安排'
  }))
  const result = {
    id: schedulingState.reschedules.length + 1,
    code: `RES-${String(schedulingState.reschedules.length + 1).padStart(3, '0')}`,
    eventId,
    eventCode: event.code,
    baseScheduleCode: base.code,
    status: '待确认',
    createdAt: new Date().toISOString().slice(0, 16),
    metrics: {
      utilization: 70,
      fulfillment: 94,
      onTimeInbound: 89,
      highRisk: 1,
      totalCost: base.metrics.totalCost + 260,
      changed: changed.filter(x => x.changeNote.startsWith(event.source)).length || 1,
      solveMs: 196
    },
    assignments: changed
  }
  schedulingState.reschedules.unshift(result)
  event.status = '已生成方案'
  return result
}
