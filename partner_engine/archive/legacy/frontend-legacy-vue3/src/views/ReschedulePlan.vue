<template>
  <div>
    <div class="page-title">局部重调度</div>
    <div class="page-subtitle">只调整受异常影响的批次、冷间和订单，尽量保持其他计划不变。</div>
    <el-row :gutter="16">
      <el-col :span="7"><el-card><template #header>选择异常事件</template>
        <el-select v-model="eventId" style="width:100%" placeholder="选择待处理异常"><el-option v-for="e in state.events" :key="e.id" :label="`${e.code} · ${e.type} · ${e.source}`" :value="e.id"/></el-select>
        <el-button style="margin-top:14px" type="primary" :disabled="!eventId" @click="run">生成局部重调度方案</el-button>
        <el-alert style="margin-top:14px" type="info" :closable="false" title="正式版将由 FastAPI 调用 OR-Tools，只释放受影响变量并重新求解。"/>
      </el-card>
      <el-card v-if="result" style="margin-top:14px"><template #header>变化摘要</template>
        <p>基础方案：{{result.baseScheduleCode}}</p><p>异常事件：{{result.eventCode}}</p><p>受影响安排：{{result.metrics.changed}}项</p><p>成本增加：¥{{costIncrease}}</p><p>求解耗时：{{result.metrics.solveMs}}ms</p>
      </el-card></el-col>
      <el-col :span="17"><el-card><template #header>重调度结果</template>
        <el-table :data="result?.assignments||[]" height="500">
          <el-table-column prop="batch" label="批次" width="125"/><el-table-column prop="room" label="新冷间" width="80"/><el-table-column prop="inbound" label="新入库时间" min-width="145"/><el-table-column prop="outbound" label="出库时间" min-width="145"/><el-table-column prop="order" label="订单" width="90"/><el-table-column prop="risk" label="风险" width="65"/><el-table-column prop="changeNote" label="调整说明" min-width="220"/>
        </el-table>
      </el-card></el-col>
    </el-row>
  </div>
</template>
<script setup>
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { schedulingState as state, generateReschedule } from '../data/schedulingDemo'
const eventId=ref(state.events[0]?.id||null);const result=ref(state.reschedules[0]||null)
const costIncrease=computed(()=>result.value?result.value.metrics.totalCost-(state.schedules[0]?.metrics.totalCost||0):0)
function run(){result.value=generateReschedule(eventId.value);ElMessage.success('局部重调度方案已生成')}
</script>
