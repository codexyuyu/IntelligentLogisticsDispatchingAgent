<template>
  <section class="merged-view">
    <header class="merged-head">
      <div>
        <p class="eyebrow">供货与订单 / 供货与批次</p>
        <h1>供货与批次</h1>
        <p>在同一工作流中完成供货计划登记、到货确认以及合作社标准批次组建。</p>
      </div>
      <div class="view-switch">
        <el-button :type="tab==='supply' ? 'primary' : 'default'" @click="tab='supply'">供货计划</el-button>
        <el-button :type="tab==='batch' ? 'primary' : 'default'" @click="tab='batch'">批次组建</el-button>
      </div>
    </header>
    <el-alert
      v-if="tab==='supply'"
      title="先登记农户或基地预计供货；确认到货后，可切换到“批次组建”合并或拆分供货记录。"
      type="info"
      :closable="false"
      show-icon
      class="workflow-tip"
    />
    <el-alert
      v-else
      title="调度系统以标准批次为对象。组批完成后，批次才能进入冷间时间窗调度。"
      type="success"
      :closable="false"
      show-icon
      class="workflow-tip"
    />
    <SupplyPlan v-if="tab==='supply'" />
    <BatchCompose v-else />
  </section>
</template>

<script setup>
import { ref } from 'vue'
import SupplyPlan from './SupplyPlan.vue'
import BatchCompose from './BatchCompose.vue'

const tab = ref('supply')
</script>

<style scoped>
.merged-view{display:flex;flex-direction:column;gap:16px}.merged-head{display:flex;align-items:flex-start;justify-content:space-between;gap:20px;padding:22px 24px;border-radius:18px;background:#fff;border:1px solid #cbd5e1}.merged-head h1{margin:4px 0 8px;font-size:27px}.merged-head p{margin:0;color:#64748b;line-height:1.6}.eyebrow{font-size:12px!important;font-weight:800;color:#2563eb!important;letter-spacing:.08em}.view-switch{display:flex;gap:8px;flex-wrap:wrap}.workflow-tip{border-radius:14px}@media(max-width:900px){.merged-head{flex-direction:column}.view-switch{width:100%}}
</style>
