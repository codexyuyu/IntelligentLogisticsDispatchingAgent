<template>
  <div>
    <div class="page-title">正常调度中心</div>
    <div class="page-subtitle">选择待调度批次、订单和目标偏好，生成“批次—冷间—时间窗—订单—车辆”方案。</div>
    <el-row :gutter="16">
      <el-col :span="7">
        <el-card><template #header>调度配置</template>
          <el-form label-width="96px">
            <el-form-item label="计划周期"><el-select v-model="form.horizon" style="width:100%"><el-option label="未来7天" :value="7"/><el-option label="未来14天" :value="14"/></el-select></el-form-item>
            <el-form-item label="调度目标"><el-select v-model="form.objective" style="width:100%"><el-option label="履约优先 + 品质风险最小" value="履约优先 + 品质风险最小"/><el-option label="冷间利用率优先" value="冷间利用率优先"/><el-option label="综合成本最低" value="综合成本最低"/></el-select></el-form-item>
            <el-form-item label="待调度批次"><b>{{pendingBatches}}</b></el-form-item>
            <el-form-item label="待匹配订单"><b>{{pendingOrders}}</b></el-form-item>
            <el-form-item label="可用冷间"><b>{{availableRooms}}</b></el-form-item>
            <el-form-item label="可用车辆"><b>{{availableVehicles}}</b></el-form-item>
            <el-button type="primary" @click="run">生成调度方案</el-button>
          </el-form>
          <el-alert style="margin-top:14px" type="warning" :closable="false" title="当前页面优先调用 Spring Boot → FastAPI；FastAPI 提供确定性调度服务。算法服务不可用时仅保留演示回退。"/>
        </el-card>
      </el-col>
      <el-col :span="17">
        <el-card><template #header><div class="header-row"><span>最新调度方案</span><el-tag v-if="current" :type="current.status==='CONFIRMED' || current.status==='已确认'?'success':'warning'">{{current.status}}</el-tag></div></template>
          <div v-if="current">
            <el-row :gutter="10" class="mini-metrics"><el-col v-for="m in metricCards" :key="m.label" :span="6"><div class="mini-card"><span>{{m.label}}</span><b>{{m.value}}</b></div></el-col></el-row>
            <el-table :data="current.assignments" height="330" v-loading="loading">
              <el-table-column :prop="source==='backend'?'batch_code':'batch'" label="批次" width="125"/><el-table-column prop="product" label="果品" width="70"/><el-table-column :prop="source==='backend'?'room_code':'room'" label="冷间" width="75"/><el-table-column :prop="source==='backend'?'planned_inbound':'inbound'" label="计划入库" min-width="140"/><el-table-column :prop="source==='backend'?'planned_outbound':'outbound'" label="计划出库" min-width="140"/><el-table-column :prop="source==='backend'?'order_code':'order'" label="订单" width="90"/><el-table-column :prop="source==='backend'?'vehicle_code':'vehicle'" label="车辆" width="105"/><el-table-column v-if="source==='backend'" prop="route_code" label="路线" width="85"/><el-table-column :prop="source==='backend'?'quality_risk':'risk'" label="风险" width="65"/><el-table-column prop="feasible" label="可行" width="65"><template #default="s"><el-tag :type="s.row.feasible?'success':'danger'">{{s.row.feasible?'是':'否'}}</el-tag></template></el-table-column>
            </el-table>
            <el-button style="margin-top:12px" type="success" :disabled="current.status==='CONFIRMED' || current.status==='已确认'" @click="confirm">确认并生成执行任务</el-button>
          </div>
          <el-empty v-else description="尚未生成调度方案"/>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>
<script setup>
import { computed, reactive, ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../api/http'
import { schedulingState as state, generateSchedule as demoGenerate, confirmSchedule as demoConfirm } from '../data/schedulingDemo'

const form=reactive({horizon:7,objective:'履约优先 + 品质风险最小'})
const current=ref(null)
const loading=ref(false)
const source=ref('backend')
const pendingBatches=ref(0)
const pendingOrders=ref(0)
const availableRooms=ref(0)
const availableVehicles=ref(0)

const metricCards=computed(()=>current.value ? [
  {label:'冷间利用率',value:(current.value.utilization ?? current.value.metrics?.utilization ?? 0)+'%'},
  {label:'订单履约率',value:(current.value.fulfillment ?? current.value.metrics?.fulfillment ?? 0)+'%'},
  {label:'总成本',value:'¥'+(current.value.totalCost ?? current.value.metrics?.totalCost ?? 0)},
  {label:'求解耗时',value:(current.value.solveMs ?? current.value.metrics?.solveMs ?? 0)+'ms'}
] : [])

async function refreshCounts(){
  try{
    const [b,o,r,v]=await Promise.all([api.listScheduleBatches(),api.listScheduleOrders(),api.listColdRoomsForSchedule(),api.listScheduleVehicles()])
    pendingBatches.value=b.length; pendingOrders.value=o.length; availableRooms.value=r.filter(x=>String(x.device_status||x.deviceStatus).toUpperCase()==='NORMAL').length; availableVehicles.value=v.length
  }catch(e){
    source.value='demo'
    pendingBatches.value=state.batches.filter(x=>x.status==='待调度').length
    pendingOrders.value=state.orders.filter(x=>x.status==='待匹配').length
    availableRooms.value=state.coldRooms.filter(x=>x.deviceStatus==='正常').length
    availableVehicles.value=0
  }
}

async function run(){
  loading.value=true
  try{
    current.value=await api.solveSchedule(form)
    source.value='backend'
    ElMessage.success('已通过调度服务生成方案')
  }catch(e){
    source.value='demo'
    current.value=demoGenerate(form)
    ElMessage.warning('FastAPI暂不可用，已切换到前端演示方案；启动算法服务后将自动走真实调度链路')
  }finally{loading.value=false}
}

async function confirm(){
  if(!current.value) return
  if(current.value.id && source.value==='backend'){
    await api.confirmSchedule(current.value.id)
  }else if(current.value.id){
    demoConfirm(current.value.id)
  }
  ElMessage.success('方案已确认，进入仓储执行流程')
  await refreshCounts()
}

onMounted(refreshCounts)
</script>
<style scoped>.header-row{display:flex;justify-content:space-between;align-items:center}.mini-metrics{margin-bottom:12px}.mini-card{padding:10px;border:1px solid #e2e8f0;background:#f8fafc;border-radius:10px}.mini-card span,.mini-card b{display:block}.mini-card span{font-size:12px;color:#64748b}.mini-card b{font-size:20px;margin-top:4px}</style>
