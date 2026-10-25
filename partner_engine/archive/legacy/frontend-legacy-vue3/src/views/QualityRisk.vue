<template>
  <div>
    <div class="page-title">品质与风险评估</div>
    <div class="page-subtitle">把运输温度、仓储环境、剩余可售期和客户要求转化为调度约束，而不是只做事后报警。</div>
    <el-row :gutter="16">
      <el-col :span="8" v-for="c in cards" :key="c.label"><el-card class="metric-card"><div class="metric-label">{{c.label}}</div><div class="metric-value">{{c.value}}</div></el-card></el-col>
    </el-row>
    <el-card style="margin-top:16px"><template #header>调度批次品质风险</template>
      <el-table :data="state.batches">
        <el-table-column prop="code" label="批次" width="130"/><el-table-column prop="product" label="果品" width="80"/><el-table-column prop="quantity" label="数量" width="80"/><el-table-column prop="maxStorageDays" label="最长储藏" width="100"/><el-table-column prop="risk" label="风险" width="80"><template #default="s"><el-tag :type="riskType(s.row.risk)">{{s.row.risk}}</el-tag></template></el-table-column><el-table-column label="建议处理"><template #default="s">{{suggestion(s.row)}}</template></el-table-column><el-table-column prop="status" label="调度状态" width="100"/>
      </el-table>
    </el-card>
    <el-card style="margin-top:16px"><template #header>仓储系统风险批次</template>
      <el-table :data="riskBatches" height="280"><el-table-column prop="batchCode" label="批次" width="180"/><el-table-column prop="productName" label="商品"/><el-table-column prop="shelfCode" label="货架" width="90"/><el-table-column prop="remainingDays" label="剩余天数" width="90"/><el-table-column prop="freshnessScore" label="新鲜度" width="90"/><el-table-column prop="status" label="状态" width="120"/></el-table>
    </el-card>
  </div>
</template>
<script setup>
import { computed, onMounted, ref } from 'vue'
import { schedulingState as state } from '../data/schedulingDemo'
import { api } from '../api/http'
const riskBatches=ref([])
const cards=computed(()=>[{label:'待评估批次',value:state.batches.length},{label:'中高风险',value:state.batches.filter(x=>x.risk!=='低').length},{label:'优先出库建议',value:state.batches.filter(x=>x.risk==='高'||x.maxStorageDays<=7).length}])
function riskType(x){return x==='高'?'danger':x==='中'?'warning':'success'}
function suggestion(x){if(x.risk==='高')return '优先出库或改派低温冷间';if(x.risk==='中')return '缩短储藏时间并加强监测';return '按计划储藏'}
onMounted(async()=>{try{riskBatches.value=await api.getRiskBatches()}catch{riskBatches.value=[]}})
</script>
