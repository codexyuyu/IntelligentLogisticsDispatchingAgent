<template>
  <section class="merged-view">
    <header class="merged-head">
      <div>
        <p class="eyebrow">协同调度 / 调度中心</p>
        <h1>调度中心</h1>
        <p>在同一流程中生成正常方案、登记异常、执行局部重调度并比较调整结果。</p>
      </div>
    </header>
    <div class="step-nav">
      <button v-for="item in tabs" :key="item.key" :class="{active:tab===item.key}" @click="tab=item.key">
        <span>{{ item.no }}</span><strong>{{ item.label }}</strong>
      </button>
    </div>
    <el-alert
      v-if="tab==='agent'"
      title="调度 Agent 只负责查询、调用求解服务和解释方案，不直接绕过业务系统修改库存。"
      type="warning"
      :closable="false"
      show-icon
    />
    <ScheduleCenter v-if="tab==='normal'" />
    <AbnormalEvent v-else-if="tab==='event'" />
    <ReschedulePlan v-else-if="tab==='reschedule'" />
    <ScheduleComparison v-else-if="tab==='comparison'" />
    <AiAssistant v-else />
  </section>
</template>

<script setup>
import { ref } from 'vue'
import ScheduleCenter from './ScheduleCenter.vue'
import AbnormalEvent from './AbnormalEvent.vue'
import ReschedulePlan from './ReschedulePlan.vue'
import ScheduleComparison from './ScheduleComparison.vue'
import AiAssistant from './AiAssistant.vue'

const tab = ref('normal')
const tabs = [
  { key: 'normal', no: '1', label: '生成调度' },
  { key: 'event', no: '2', label: '登记异常' },
  { key: 'reschedule', no: '3', label: '局部重调度' },
  { key: 'comparison', no: '4', label: '方案对比' },
  { key: 'agent', no: '5', label: '方案解释' }
]
</script>

<style scoped>
.merged-view{display:flex;flex-direction:column;gap:16px}.merged-head{padding:22px 24px;border-radius:18px;background:#fff;border:1px solid #cbd5e1}.merged-head h1{margin:4px 0 8px;font-size:27px}.merged-head p{margin:0;color:#64748b;line-height:1.6}.eyebrow{font-size:12px!important;font-weight:800;color:#2563eb!important;letter-spacing:.08em}.step-nav{display:grid;grid-template-columns:repeat(5,minmax(120px,1fr));gap:10px}.step-nav button{display:flex;align-items:center;gap:9px;padding:13px 14px;border:1px solid #cbd5e1;border-radius:14px;background:#fff;color:#475569;cursor:pointer;text-align:left}.step-nav button span{width:28px;height:28px;border-radius:50%;display:grid;place-items:center;background:#e2e8f0;font-weight:800}.step-nav button.active{border-color:#2563eb;background:#eff6ff;color:#1d4ed8}.step-nav button.active span{background:#2563eb;color:#fff}@media(max-width:1000px){.step-nav{grid-template-columns:repeat(2,1fr)}}
</style>
