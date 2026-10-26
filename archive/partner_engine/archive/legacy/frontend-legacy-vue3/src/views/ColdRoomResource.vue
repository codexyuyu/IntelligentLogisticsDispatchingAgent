<template>
  <div>
    <div class="page-title">冷间资源</div>
    <div class="page-subtitle">调度单位由“冷库总容量”细化为“冷间 × 时间窗”，同时考虑温区、清洁、切换和设备状态。</div>
    <el-row :gutter="16">
      <el-col v-for="room in state.coldRooms" :key="room.id" :span="12" style="margin-bottom:16px">
        <el-card class="room-card" :class="room.deviceStatus==='正常'?'':'room-disabled'">
          <template #header><div class="header-row"><b>{{room.code}} · {{room.warehouse}}</b><el-tag :type="room.deviceStatus==='正常'?'success':'danger'">{{room.deviceStatus}}</el-tag></div></template>
          <div class="room-grid">
            <div><span>容量</span><b>{{room.used}} / {{room.capacity}} 吨</b></div>
            <div><span>温区</span><b>{{room.minTemp}}～{{room.maxTemp}}℃</b></div>
            <div><span>适用品类</span><b>{{room.categories}}</b></div>
            <div><span>预冷能力</span><b>{{room.preCooling?'支持':'不支持'}}</b></div>
            <div><span>清洁耗时</span><b>{{room.cleaningHours}}小时</b></div>
            <div><span>温区切换</span><b>{{room.switchHours}}小时</b></div>
            <div><span>参考费用</span><b>{{room.cost}}元/吨·小时</b></div>
            <div><span>有效可用容量</span><b>{{room.deviceStatus==='正常'?room.capacity-room.used:0}}吨</b></div>
          </div>
          <el-progress :percentage="Math.round(room.used/room.capacity*100)" :status="room.deviceStatus==='正常'?undefined:'exception'"/>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>
<script setup>import { schedulingState as state } from '../data/schedulingDemo'</script>
<style scoped>
.header-row{display:flex;justify-content:space-between;align-items:center}.room-card{border-left:5px solid #2563eb}.room-disabled{border-left-color:#ef4444;opacity:.86}.room-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:16px}.room-grid div{background:#f8fafc;border:1px solid #e2e8f0;padding:12px;border-radius:12px}.room-grid span,.room-grid b{display:block}.room-grid span{color:#64748b;font-size:12px;margin-bottom:5px}
</style>
