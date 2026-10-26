<template>
  <div>
    <div class="page-title">调度方案对比</div>
    <div class="page-subtitle">对比原方案与重调度方案的履约率、成本、风险和变更范围，辅助人工确认。</div>
    <el-alert v-if="!reschedule" type="warning" :closable="false" title="请先在“局部重调度”页面生成一个方案。" style="margin-bottom:14px"/>
    <el-row :gutter="16">
      <el-col :span="12"><el-card><template #header>方案A：{{base?.code||'原方案'}}</template><MetricPanel :metrics="base?.metrics"/></el-card></el-col>
      <el-col :span="12"><el-card><template #header>方案B：{{reschedule?.code||'重调度方案'}}</template><MetricPanel :metrics="reschedule?.metrics"/></el-card></el-col>
    </el-row>
    <el-card style="margin-top:16px"><template #header>指标变化</template>
      <el-table :data="comparison">
        <el-table-column prop="name" label="指标"/><el-table-column prop="before" label="原方案"/><el-table-column prop="after" label="重调度"/><el-table-column prop="change" label="变化"><template #default="s"><el-tag :type="s.row.good?'success':'warning'">{{s.row.change}}</el-tag></template></el-table-column>
      </el-table>
    </el-card>
  </div>
</template>
<script setup>
import { computed, defineComponent, h } from 'vue'
import { schedulingState as state } from '../data/schedulingDemo'
const base=computed(()=>state.schedules[0]);const reschedule=computed(()=>state.reschedules[0])
const comparison=computed(()=>{
  const a=base.value?.metrics||{},b=reschedule.value?.metrics||{}
  return [
    {name:'冷间利用率',before:(a.utilization||0)+'%',after:(b.utilization||0)+'%',change:`${(b.utilization||0)-(a.utilization||0)}个百分点`,good:(b.utilization||0)>=(a.utilization||0)},
    {name:'订单履约率',before:(a.fulfillment||0)+'%',after:(b.fulfillment||0)+'%',change:`${(b.fulfillment||0)-(a.fulfillment||0)}个百分点`,good:(b.fulfillment||0)>=(a.fulfillment||0)},
    {name:'总成本',before:'¥'+(a.totalCost||0),after:'¥'+(b.totalCost||0),change:'¥'+((b.totalCost||0)-(a.totalCost||0)),good:(b.totalCost||0)<=(a.totalCost||0)},
    {name:'高风险批次',before:a.highRisk||0,after:b.highRisk||0,change:String((b.highRisk||0)-(a.highRisk||0)),good:(b.highRisk||0)<=(a.highRisk||0)},
    {name:'调整范围',before:a.changed||0,after:b.changed||0,change:(b.changed||0)+'项',good:(b.changed||0)<=2}
  ]
})
const MetricPanel=defineComponent({props:{metrics:Object},setup(p){return()=>h('div',{class:'metric-panel'},Object.entries(p.metrics||{}).map(([k,v])=>h('div',{class:'metric-line'},[h('span',label(k)),h('b',format(k,v))])))}})
function label(k){return({utilization:'冷间利用率',fulfillment:'订单履约率',onTimeInbound:'按时入库率',highRisk:'高风险批次',totalCost:'总成本',changed:'调整项数',solveMs:'求解耗时'}[k]||k)}
function format(k,v){if(['utilization','fulfillment','onTimeInbound'].includes(k))return v+'%';if(k==='totalCost')return '¥'+v;if(k==='solveMs')return v+'ms';return v}
</script>
<style scoped>:deep(.metric-panel){display:grid;grid-template-columns:1fr 1fr;gap:12px}:deep(.metric-line){padding:14px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px}:deep(.metric-line span),:deep(.metric-line b){display:block}:deep(.metric-line span){font-size:12px;color:#64748b}:deep(.metric-line b){font-size:22px;margin-top:5px}</style>
