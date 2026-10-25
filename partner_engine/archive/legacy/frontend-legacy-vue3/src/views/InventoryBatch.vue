<template>
  <div>
    <div class="page-title">库存与批次</div>
    <div class="page-subtitle">统一查看现有仓储批次与调度批次，连接仓储执行和调度计划。</div>
    <el-row :gutter="16">
      <el-col :span="8" v-for="card in cards" :key="card.label"><el-card class="metric-card"><div class="metric-label">{{card.label}}</div><div class="metric-value">{{card.value}}</div></el-card></el-col>
    </el-row>
    <el-card style="margin-top:16px"><template #header>调度批次</template>
      <el-table :data="state.batches">
        <el-table-column prop="code" label="批次号" width="130"/><el-table-column prop="product" label="果品" width="80"/><el-table-column prop="quantity" label="数量" width="80"/><el-table-column prop="grade" label="等级" width="70"/><el-table-column prop="expectedInbound" label="计划入库"/><el-table-column prop="maxStorageDays" label="最长储藏" width="90"/><el-table-column prop="risk" label="风险" width="75"><template #default="s"><el-tag :type="s.row.risk==='高'?'danger':s.row.risk==='中'?'warning':'success'">{{s.row.risk}}</el-tag></template></el-table-column><el-table-column prop="status" label="调度状态" width="100"/>
      </el-table>
    </el-card>
    <el-card style="margin-top:16px"><template #header>仓储系统生鲜批次</template>
      <el-table :data="freshBatches" height="300">
        <el-table-column prop="batchCode" label="批次号" width="180"/><el-table-column prop="productName" label="商品"/><el-table-column prop="shelfCode" label="货架" width="90"/><el-table-column prop="quantityRemaining" label="剩余数量" width="100"/><el-table-column prop="remainingDays" label="剩余天数" width="90"/><el-table-column prop="status" label="状态" width="110"/>
      </el-table>
    </el-card>
  </div>
</template>
<script setup>
import { computed, onMounted, ref } from 'vue'
import { schedulingState as state } from '../data/schedulingDemo'
import { api } from '../api/http'
const freshBatches=ref([])
const cards=computed(()=>[
  {label:'调度批次',value:state.batches.length},
  {label:'待调度',value:state.batches.filter(x=>x.status==='待调度').length},
  {label:'高/中风险',value:state.batches.filter(x=>x.risk!=='低').length}
])
onMounted(async()=>{try{freshBatches.value=await api.getFreshBatches()}catch{freshBatches.value=[]}})
</script>
