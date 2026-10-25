<template>
  <div>
    <div class="page-title">冷间时间轴</div>
    <div class="page-subtitle">以未来七天为计划窗口，直观显示储藏、预冷、清洁、温区切换和故障占用。</div>
    <el-card>
      <template #header><div class="header-row"><span>冷间 × 时间窗甘特视图</span><div class="legend"><i class="storage"></i>储藏 <i class="cool"></i>预冷 <i class="clean"></i>清洁 <i class="maintenance"></i>维护 <i class="idle"></i>空闲</div></div></template>
      <div class="scale"><span v-for="d in 8" :key="d">第{{d}}天</span></div>
      <div v-for="row in state.timeline" :key="row.roomId" class="timeline-row">
        <div class="room-label">{{row.roomCode}}</div>
        <div class="track">
          <div v-for="(block,i) in row.blocks" :key="i" class="block" :class="block.type.toLowerCase()" :style="{left:block.start+'%',width:block.width+'%'}" :title="block.label">
            {{block.label}}
          </div>
        </div>
      </div>
    </el-card>
    <el-alert style="margin-top:14px" type="info" :closable="false" title="后续接入 OR-Tools 后，时间块由调度结果自动生成；当前为可交互页面结构与演示数据。"/>
  </div>
</template>
<script setup>import { schedulingState as state } from '../data/schedulingDemo'</script>
<style scoped>
.header-row{display:flex;justify-content:space-between;align-items:center;gap:16px}.legend{font-size:12px;color:#64748b;display:flex;align-items:center;gap:6px}.legend i{width:12px;height:12px;border-radius:3px;display:inline-block;margin-left:6px}.scale{margin-left:92px;display:grid;grid-template-columns:repeat(8,1fr);color:#64748b;font-size:12px;padding:0 0 8px}.timeline-row{display:grid;grid-template-columns:80px 1fr;gap:12px;align-items:center;margin:14px 0}.room-label{font-weight:800}.track{height:48px;position:relative;background:repeating-linear-gradient(90deg,#f8fafc 0,#f8fafc calc(12.5% - 1px),#cbd5e1 calc(12.5% - 1px),#cbd5e1 12.5%);border:1px solid #cbd5e1;border-radius:10px;overflow:hidden}.block{position:absolute;top:6px;height:34px;border-radius:7px;padding:8px;color:white;font-size:12px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}.storage,.legend .storage{background:#16a34a}.pre_cooling,.legend .cool{background:#0284c7}.cleaning,.legend .clean{background:#f59e0b}.maintenance,.legend .maintenance{background:#dc2626}.idle,.legend .idle{background:#94a3b8}
</style>
