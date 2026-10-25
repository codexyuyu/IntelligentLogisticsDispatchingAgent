<template>
  <div>
    <div class="page-title">异常事件</div>
    <div class="page-subtitle">统一登记到货偏差、订单变化、冷间故障和温度异常，作为局部重调度触发器。</div>
    <el-row :gutter="16">
      <el-col :span="7"><el-card><template #header>新增异常</template>
        <el-form label-width="90px">
          <el-form-item label="异常类型"><el-select v-model="form.type" style="width:100%"><el-option v-for="x in types" :key="x" :label="x" :value="x"/></el-select></el-form-item>
          <el-form-item label="影响对象"><el-input v-model="form.source" placeholder="如 CR-02 / ORD-001"/></el-form-item>
          <el-form-item label="发生时间"><el-date-picker v-model="form.eventTime" type="datetime" value-format="YYYY-MM-DDTHH:mm" style="width:100%"/></el-form-item>
          <el-form-item label="影响描述"><el-input v-model="form.impact" type="textarea" :rows="3"/></el-form-item>
          <el-form-item label="严重程度"><el-radio-group v-model="form.severity"><el-radio-button label="低"/><el-radio-button label="中"/><el-radio-button label="高"/></el-radio-group></el-form-item>
          <el-button type="danger" @click="submit">登记异常</el-button>
        </el-form>
      </el-card></el-col>
      <el-col :span="17"><el-card><template #header>异常事件列表</template>
        <el-table :data="state.events" height="500">
          <el-table-column prop="code" label="事件号" width="95"/><el-table-column prop="type" label="类型" width="100"/><el-table-column prop="source" label="影响对象" width="100"/><el-table-column prop="eventTime" label="发生时间" min-width="145"/><el-table-column prop="impact" label="影响描述"/><el-table-column prop="severity" label="等级" width="70"><template #default="s"><el-tag :type="s.row.severity==='高'?'danger':s.row.severity==='中'?'warning':'info'">{{s.row.severity}}</el-tag></template></el-table-column><el-table-column prop="status" label="状态" width="100"/>
        </el-table>
      </el-card></el-col>
    </el-row>
  </div>
</template>
<script setup>
import { reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { schedulingState as state, addAbnormalEvent } from '../data/schedulingDemo'
const types=['到货延迟','数量偏差','订单取消','订单提前','冷间故障','温度异常','果品提前上市']
const form=reactive({type:'冷间故障',source:'CR-02',eventTime:new Date().toISOString().slice(0,16),impact:'受影响批次需要改派冷间',severity:'高'})
function submit(){addAbnormalEvent({...form});ElMessage.success('异常已登记，可进入重调度页面生成方案')}
</script>
