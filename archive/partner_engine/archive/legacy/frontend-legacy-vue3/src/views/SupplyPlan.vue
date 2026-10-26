<template>
  <div>
    <div class="page-title">农户供货计划</div>
    <div class="page-subtitle">记录预计采收、预计数量和实际到货偏差，为合作社组批与调度提供输入。</div>
    <el-row :gutter="16">
      <el-col :span="7">
        <el-card>
          <template #header>新增供货计划</template>
          <el-form label-width="92px">
            <el-form-item label="农户/基地"><el-input v-model="form.farmer" /></el-form-item>
            <el-form-item label="果品"><el-select v-model="form.product" style="width:100%"><el-option label="脐橙" value="脐橙"/><el-option label="葡萄" value="葡萄"/></el-select></el-form-item>
            <el-form-item label="预计采收"><el-date-picker v-model="form.expectedTime" type="datetime" value-format="YYYY-MM-DDTHH:mm" style="width:100%"/></el-form-item>
            <el-form-item label="预计数量"><el-input-number v-model="form.expectedQty" :min="1" :max="1000"/></el-form-item>
            <el-form-item label="地块位置"><el-input v-model="form.location" /></el-form-item>
            <el-button type="primary" @click="submit">保存计划</el-button>
          </el-form>
        </el-card>
      </el-col>
      <el-col :span="17">
        <el-row :gutter="12" class="metric-row">
          <el-col v-for="card in cards" :key="card.label" :span="6"><el-card class="metric-card"><div class="metric-label">{{ card.label }}</div><div class="metric-value">{{ card.value }}</div></el-card></el-col>
        </el-row>
        <el-card style="margin-top:14px">
          <template #header>供货计划列表</template>
          <el-table :data="state.supplyPlans" height="470">
            <el-table-column prop="code" label="编号" width="95"/>
            <el-table-column prop="farmer" label="农户/基地" min-width="130"/>
            <el-table-column prop="product" label="果品" width="75"/>
            <el-table-column prop="expectedTime" label="预计采收" min-width="145"/>
            <el-table-column prop="expectedQty" label="预计数量" width="85"/>
            <el-table-column prop="actualQty" label="实际数量" width="85"/>
            <el-table-column prop="location" label="地块" min-width="130"/>
            <el-table-column prop="status" label="状态" width="95"><template #default="s"><el-tag :type="tagType(s.row.status)">{{ s.row.status }}</el-tag></template></el-table-column>
            <el-table-column label="操作" width="90"><template #default="s"><el-button size="small" :disabled="s.row.status !== '待到货'" @click="arrive(s.row.id)">确认到货</el-button></template></el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>
<script setup>
import { computed, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { schedulingState as state, addSupplyPlan, confirmSupplyArrival } from '../data/schedulingDemo'
const form = reactive({ farmer: '示范农户', product: '脐橙', expectedTime: new Date().toISOString().slice(0,16), expectedQty: 100, location: '示范种植基地' })
const cards = computed(() => [
  { label: '计划总量', value: state.supplyPlans.reduce((s,x)=>s+x.expectedQty,0) },
  { label: '待到货', value: state.supplyPlans.filter(x=>x.status==='待到货').length },
  { label: '已到货', value: state.supplyPlans.filter(x=>x.status==='已到货').length },
  { label: '偏差计划', value: state.supplyPlans.filter(x=>x.status.includes('延迟')).length }
])
function submit(){ addSupplyPlan({...form}); ElMessage.success('供货计划已保存') }
function arrive(id){ confirmSupplyArrival(id); ElMessage.success('已记录实际到货') }
function tagType(status){ if(status.includes('延迟')) return 'danger'; if(status==='已到货'||status==='已组批') return 'success'; return 'warning' }
</script>
