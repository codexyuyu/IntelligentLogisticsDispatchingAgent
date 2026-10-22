<template>
  <section class="merged-view">
    <header class="merged-head">
      <div>
        <p class="eyebrow">品质与数字孪生 / 异常与品质风险</p>
        <h1>异常与品质风险</h1>
        <p>统一管理批次品质评估、温度异常、设备告警和处置状态，并判断是否触发重调度。</p>
      </div>
      <div class="view-switch">
        <el-button :type="tab==='quality' ? 'primary' : 'default'" @click="tab='quality'">品质风险</el-button>
        <el-button :type="tab==='warning' ? 'primary' : 'default'" @click="tab='warning'">异常预警</el-button>
      </div>
    </header>
    <QualityRisk v-if="tab==='quality'" />
    <Warning v-else />
  </section>
</template>

<script setup>
import { ref } from 'vue'
import QualityRisk from './QualityRisk.vue'
import Warning from './Warning.vue'

const tab = ref('quality')
</script>

<style scoped>
.merged-view{display:flex;flex-direction:column;gap:16px}.merged-head{display:flex;align-items:flex-start;justify-content:space-between;gap:20px;padding:22px 24px;border-radius:18px;background:#fff;border:1px solid #cbd5e1}.merged-head h1{margin:4px 0 8px;font-size:27px}.merged-head p{margin:0;color:#64748b;line-height:1.6}.eyebrow{font-size:12px!important;font-weight:800;color:#2563eb!important;letter-spacing:.08em}.view-switch{display:flex;gap:8px;flex-wrap:wrap}@media(max-width:900px){.merged-head{flex-direction:column}}
</style>
