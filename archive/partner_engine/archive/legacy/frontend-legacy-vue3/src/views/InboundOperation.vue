<template>
  <section class="merged-view">
    <header class="merged-head">
      <div>
        <p class="eyebrow">仓储作业 / 入库作业</p>
        <h1>入库作业</h1>
        <p>将运输到货、收货验收、预冷处理和正式入库合并为一条连续作业链。</p>
      </div>
      <div class="view-switch">
        <el-button :type="tab==='receiving' ? 'primary' : 'default'" @click="tab='receiving'">收货与预冷</el-button>
        <el-button :type="tab==='inbound' ? 'primary' : 'default'" @click="tab='inbound'">确认入库</el-button>
        <el-button :type="tab==='transport' ? 'primary' : 'default'" @click="tab='transport'">运输信息</el-button>
      </div>
    </header>
    <div class="flow-strip">
      <span :class="{on:tab==='transport'}">1 运输到货</span><b>→</b>
      <span :class="{on:tab==='receiving'}">2 验收预冷</span><b>→</b>
      <span :class="{on:tab==='inbound'}">3 确认入库</span>
    </div>
    <ReceivingRisk v-if="tab==='receiving'" />
    <Inbound v-else-if="tab==='inbound'" />
    <ColdChainTransport v-else />
  </section>
</template>

<script setup>
import { ref } from 'vue'
import ReceivingRisk from './ReceivingRisk.vue'
import Inbound from './Inbound.vue'
import ColdChainTransport from './ColdChainTransport.vue'

const tab = ref('receiving')
</script>

<style scoped>
.merged-view{display:flex;flex-direction:column;gap:16px}.merged-head{display:flex;align-items:flex-start;justify-content:space-between;gap:20px;padding:22px 24px;border-radius:18px;background:#fff;border:1px solid #cbd5e1}.merged-head h1{margin:4px 0 8px;font-size:27px}.merged-head p{margin:0;color:#64748b;line-height:1.6}.eyebrow{font-size:12px!important;font-weight:800;color:#2563eb!important;letter-spacing:.08em}.view-switch{display:flex;gap:8px;flex-wrap:wrap}.flow-strip{display:flex;align-items:center;justify-content:center;gap:14px;padding:14px;border-radius:14px;background:#fff;border:1px solid #cbd5e1;color:#64748b}.flow-strip span{padding:8px 14px;border-radius:999px;background:#f1f5f9;font-weight:700}.flow-strip span.on{background:#dbeafe;color:#1d4ed8}.flow-strip b{color:#94a3b8}@media(max-width:900px){.merged-head{flex-direction:column}.flow-strip{justify-content:flex-start;overflow-x:auto}}
</style>
