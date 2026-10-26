<template>
  <section class="merged-view">
    <header class="merged-head">
      <div>
        <p class="eyebrow">品质与数字孪生 / 数字孪生驾驶舱</p>
        <h1>数字孪生驾驶舱</h1>
        <p>集中展示调度指标、冷间与仓内状态及统计分析，不再设置独立“大数据平台”入口。</p>
      </div>
      <div class="view-switch">
        <el-button :type="tab==='cockpit' ? 'primary' : 'default'" @click="tab='cockpit'">调度总览</el-button>
        <el-button :type="tab==='warehouse' ? 'primary' : 'default'" @click="tab='warehouse'">三维仓库</el-button>
        <el-button :type="tab==='analysis' ? 'primary' : 'default'" @click="tab='analysis'">统计分析</el-button>
      </div>
    </header>
    <SchedulingDashboard v-if="tab==='cockpit'" />
    <Dashboard v-else-if="tab==='warehouse'" />
    <DataPlatform v-else />
  </section>
</template>

<script setup>
import { ref } from 'vue'
import SchedulingDashboard from './SchedulingDashboard.vue'
import Dashboard from './Dashboard.vue'
import DataPlatform from './DataPlatform.vue'

const tab = ref('cockpit')
</script>

<style scoped>
.merged-view{display:flex;flex-direction:column;gap:16px}.merged-head{display:flex;align-items:flex-start;justify-content:space-between;gap:20px;padding:22px 24px;border-radius:18px;background:#fff;border:1px solid #cbd5e1}.merged-head h1{margin:4px 0 8px;font-size:27px}.merged-head p{margin:0;color:#64748b;line-height:1.6}.eyebrow{font-size:12px!important;font-weight:800;color:#2563eb!important;letter-spacing:.08em}.view-switch{display:flex;gap:8px;flex-wrap:wrap}@media(max-width:900px){.merged-head{flex-direction:column}}
</style>
