<template>
  <div>
    <div class="page-title">县域产地冷链调度驾驶舱</div>
    <div class="page-subtitle">从农户供货、合作社组批、冷间资源、下游订单到异常重调度的统一状态视图。</div>
    <el-row :gutter="12"><el-col v-for="c in cards" :key="c.label" :span="4"><el-card class="metric-card"><div class="metric-label">{{c.label}}</div><div class="metric-value">{{c.value}}</div></el-card></el-col></el-row>
    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="15"><el-card><template #header>县域资源关系图</template>
        <div class="county-map">
          <div class="node farmer f1">青河村<br><small>2个供货组</small></div><div class="node farmer f2">新桥村<br><small>1个农场</small></div><div class="node coop">合作社集配中心<br><small>组批 · 调度 · 质检</small></div><div class="node cold c1">中心冷库A<br><small>2个冷间</small></div><div class="node cold c2">乡镇冷库B<br><small>2个冷间</small></div><div class="node buyer b1">县城商超</div><div class="node buyer b2">批发市场</div>
          <svg viewBox="0 0 900 420" preserveAspectRatio="none"><path d="M140 100 C280 100 260 190 410 210"/><path d="M150 310 C260 300 280 235 410 210"/><path d="M500 205 C600 165 620 100 725 100"/><path d="M500 220 C610 245 610 320 725 320"/><path d="M790 100 C830 135 820 185 850 210"/><path d="M790 320 C830 285 820 235 850 210"/></svg>
        </div>
      </el-card></el-col>
      <el-col :span="9"><el-card><template #header>调度运行状态</template>
        <div class="status-list"><div><span>当前方案</span><b>{{state.schedules[0]?.code}}</b></div><div><span>方案状态</span><el-tag type="warning">{{state.schedules[0]?.status}}</el-tag></div><div><span>待处理异常</span><b class="danger">{{pendingEvents}}</b></div><div><span>可用冷间</span><b>{{availableRooms}} / {{state.coldRooms.length}}</b></div><div><span>待匹配订单</span><b>{{pendingOrders}}</b></div></div>
      </el-card><el-card style="margin-top:14px"><template #header>最近异常</template><div v-for="e in state.events.slice(0,3)" :key="e.id" class="event-item"><el-tag :type="e.severity==='高'?'danger':'warning'">{{e.type}}</el-tag><div><b>{{e.source}}</b><span>{{e.impact}}</span></div></div></el-card></el-col>
    </el-row>
  </div>
</template>
<script setup>
import { computed } from 'vue'
import { schedulingState as state } from '../data/schedulingDemo'
const pendingEvents=computed(()=>state.events.filter(x=>x.status==='待重调度').length);const availableRooms=computed(()=>state.coldRooms.filter(x=>x.deviceStatus==='正常').length);const pendingOrders=computed(()=>state.orders.filter(x=>x.status==='待匹配').length)
const cards=computed(()=>[{label:'预计供货量',value:state.supplyPlans.reduce((s,x)=>s+x.expectedQty,0)},{label:'标准批次',value:state.batches.length},{label:'待匹配订单',value:pendingOrders.value},{label:'可用冷间',value:availableRooms.value},{label:'待处理异常',value:pendingEvents.value},{label:'调度方案',value:state.schedules.length}])
</script>
<style scoped>
.county-map{height:420px;position:relative;border-radius:16px;background:linear-gradient(135deg,#e0f2fe,#ecfccb);overflow:hidden;border:1px solid #bfdbfe}.county-map svg{position:absolute;inset:0;width:100%;height:100%;z-index:1}.county-map path{fill:none;stroke:#64748b;stroke-width:3;stroke-dasharray:8 8}.node{position:absolute;z-index:2;padding:13px 18px;border-radius:15px;color:white;text-align:center;box-shadow:0 10px 25px rgba(15,23,42,.18);font-weight:800}.node small{font-weight:400;opacity:.9}.farmer{background:#16a34a}.coop{background:#2563eb;left:43%;top:43%}.cold{background:#7c3aed}.buyer{background:#ea580c}.f1{left:5%;top:12%}.f2{left:6%;bottom:14%}.c1{right:14%;top:12%}.c2{right:14%;bottom:14%}.b1{right:1%;top:44%}.b2{right:2%;bottom:8%}.status-list{display:grid;gap:12px}.status-list>div{display:flex;justify-content:space-between;align-items:center;padding:12px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px}.status-list span{color:#64748b}.danger{color:#dc2626}.event-item{display:flex;gap:10px;padding:10px 0;border-bottom:1px solid #e2e8f0}.event-item div b,.event-item div span{display:block}.event-item div span{font-size:12px;color:#64748b;margin-top:4px}
</style>
