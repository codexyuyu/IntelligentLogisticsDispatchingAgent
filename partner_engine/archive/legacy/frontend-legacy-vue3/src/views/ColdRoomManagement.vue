<template>
  <section class="merged-view">
    <header class="merged-head">
      <div>
        <p class="eyebrow">协同调度 / 冷间资源</p>
        <h1>冷间资源</h1>
        <p>统一查看冷间容量、温区、设备状态和未来占用时间，调度单位为“冷间 × 时间窗”。</p>
      </div>
      <div class="view-switch">
        <el-button :type="tab==='resource' ? 'primary' : 'default'" @click="tab='resource'">资源状态</el-button>
        <el-button :type="tab==='timeline' ? 'primary' : 'default'" @click="tab='timeline'">占用时间轴</el-button>
      </div>
    </header>
    <ColdRoomResource v-if="tab==='resource'" />
    <ColdRoomTimeline v-else />
  </section>
</template>

<script setup>
import { ref } from 'vue'
import ColdRoomResource from './ColdRoomResource.vue'
import ColdRoomTimeline from './ColdRoomTimeline.vue'

const tab = ref('resource')
</script>

<style scoped>
.merged-view{display:flex;flex-direction:column;gap:16px}.merged-head{display:flex;align-items:flex-start;justify-content:space-between;gap:20px;padding:22px 24px;border-radius:18px;background:#fff;border:1px solid #cbd5e1}.merged-head h1{margin:4px 0 8px;font-size:27px}.merged-head p{margin:0;color:#64748b;line-height:1.6}.eyebrow{font-size:12px!important;font-weight:800;color:#2563eb!important;letter-spacing:.08em}.view-switch{display:flex;gap:8px;flex-wrap:wrap}@media(max-width:900px){.merged-head{flex-direction:column}}
</style>
