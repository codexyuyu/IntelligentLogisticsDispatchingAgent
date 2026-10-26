<template>
  <div>
    <div class="page-title">合作社组批</div>
    <div class="page-subtitle">将多个农户的同类供货记录合并为标准批次，再提交冷间调度。</div>
    <el-row :gutter="16">
      <el-col :span="13">
        <el-card>
          <template #header>待组批供货记录</template>
          <el-table :data="available" height="430" @selection-change="selected = $event">
            <el-table-column type="selection" width="48"/>
            <el-table-column prop="code" label="编号" width="95"/>
            <el-table-column prop="farmer" label="来源"/>
            <el-table-column prop="product" label="果品" width="80"/>
            <el-table-column prop="expectedQty" label="计划数量" width="90"/>
            <el-table-column prop="actualQty" label="实际数量" width="90"/>
            <el-table-column prop="status" label="状态" width="90"/>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="11">
        <el-card>
          <template #header>批次配置</template>
          <el-form label-width="100px">
            <el-form-item label="果品"><el-select v-model="form.product" style="width:100%"><el-option label="脐橙" value="脐橙"/><el-option label="葡萄" value="葡萄"/></el-select></el-form-item>
            <el-form-item label="品质等级"><el-select v-model="form.grade" style="width:100%"><el-option label="A" value="A"/><el-option label="B" value="B"/></el-select></el-form-item>
            <el-form-item label="批次数量"><el-input-number v-model="form.quantity" :min="1" :max="1000"/></el-form-item>
            <el-form-item label="需要预冷"><el-switch v-model="form.preCooling"/></el-form-item>
            <el-form-item label="预计入库"><el-date-picker v-model="form.expectedInbound" type="datetime" value-format="YYYY-MM-DDTHH:mm" style="width:100%"/></el-form-item>
            <el-form-item label="最长储藏"><el-input-number v-model="form.maxStorageDays" :min="1" :max="60"/><span class="unit">天</span></el-form-item>
            <el-button type="primary" :disabled="!selected.length" @click="create">生成标准批次</el-button>
          </el-form>
          <el-alert style="margin-top:14px" :closable="false" type="info" title="组批后，批次将进入“正常调度”页面，等待分配冷间和时间窗。"/>
        </el-card>
      </el-col>
    </el-row>
    <el-card style="margin-top:16px">
      <template #header>已生成批次</template>
      <el-table :data="state.batches">
        <el-table-column prop="code" label="批次号" width="130"/><el-table-column prop="product" label="果品" width="80"/><el-table-column prop="grade" label="等级" width="70"/><el-table-column prop="quantity" label="数量" width="80"/><el-table-column prop="expectedInbound" label="预计入库"/><el-table-column prop="maxStorageDays" label="最长储藏(天)" width="115"/><el-table-column prop="risk" label="风险" width="75"/><el-table-column prop="status" label="状态" width="90"/>
      </el-table>
    </el-card>
  </div>
</template>
<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { schedulingState as state, composeBatch } from '../data/schedulingDemo'
const selected = ref([])
const form = reactive({ product:'脐橙', grade:'A', quantity:100, preCooling:true, expectedInbound:new Date().toISOString().slice(0,16), maxStorageDays:14 })
const available = computed(()=>state.supplyPlans.filter(x=>['待到货','已到货'].includes(x.status)))
watch(selected, rows => { if(rows.length){ form.product=rows[0].product; form.quantity=rows.reduce((s,x)=>s+(x.actualQty||x.expectedQty),0) } })
function create(){ composeBatch(selected.value.map(x=>x.id), {...form}); selected.value=[]; ElMessage.success('标准批次已生成') }
</script>
<style scoped>.unit{margin-left:8px;color:#64748b}</style>
