<template>
  <section class="merged-view">
    <header class="merged-head">
      <div>
        <p class="eyebrow">仓储作业 / 库存与出库</p>
        <h1>库存与出库</h1>
        <p>在批次库存详情中查看冷间位置、风险状态和订单关联，并完成出库履约。</p>
      </div>
      <div class="view-switch">
        <el-button :type="tab==='inventory' ? 'primary' : 'default'" @click="tab='inventory'">库存与批次</el-button>
        <el-button :type="tab==='outbound' ? 'primary' : 'default'" @click="tab='outbound'">出库作业</el-button>
      </div>
    </header>
    <InventoryBatch v-if="tab==='inventory'" />
    <Outbound v-else />
  </section>
</template>

<script setup>
import { ref } from 'vue'
import InventoryBatch from './InventoryBatch.vue'
import Outbound from './Outbound.vue'

const tab = ref('inventory')
</script>

<style scoped>
.merged-view{display:flex;flex-direction:column;gap:16px}.merged-head{display:flex;align-items:flex-start;justify-content:space-between;gap:20px;padding:22px 24px;border-radius:18px;background:#fff;border:1px solid #cbd5e1}.merged-head h1{margin:4px 0 8px;font-size:27px}.merged-head p{margin:0;color:#64748b;line-height:1.6}.eyebrow{font-size:12px!important;font-weight:800;color:#2563eb!important;letter-spacing:.08em}.view-switch{display:flex;gap:8px;flex-wrap:wrap}@media(max-width:900px){.merged-head{flex-direction:column}}
</style>
