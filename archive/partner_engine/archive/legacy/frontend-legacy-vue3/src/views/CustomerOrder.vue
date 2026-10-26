<template>
  <div>
    <div class="page-title">下游订单</div>
    <div class="page-subtitle">订单的数量、交付期限和最低剩余可售期，将作为出库调度的硬约束。</div>
    <el-row :gutter="16">
      <el-col :span="7">
        <el-card><template #header>新增订单</template>
          <el-form label-width="96px">
            <el-form-item label="客户"><el-input v-model="form.customer"/></el-form-item>
            <el-form-item label="果品"><el-select v-model="form.product" style="width:100%"><el-option label="脐橙" value="脐橙"/><el-option label="葡萄" value="葡萄"/></el-select></el-form-item>
            <el-form-item label="数量"><el-input-number v-model="form.quantity" :min="1" :max="1000"/></el-form-item>
            <el-form-item label="品质等级"><el-select v-model="form.grade" style="width:100%"><el-option label="A" value="A"/><el-option label="B及以上" value="B及以上"/></el-select></el-form-item>
            <el-form-item label="最迟交付"><el-date-picker v-model="form.latestDelivery" type="datetime" value-format="YYYY-MM-DDTHH:mm" style="width:100%"/></el-form-item>
            <el-form-item label="最低可售期"><el-input-number v-model="form.minShelfLife" :min="1" :max="30"/><span class="unit">天</span></el-form-item>
            <el-button type="primary" @click="submit">保存订单</el-button>
          </el-form>
        </el-card>
      </el-col>
      <el-col :span="17"><el-card><template #header>订单列表</template>
        <el-table :data="state.orders" height="500">
          <el-table-column prop="code" label="订单号" width="100"/><el-table-column prop="customer" label="客户" min-width="140"/><el-table-column prop="product" label="果品" width="80"/><el-table-column prop="quantity" label="数量" width="80"/><el-table-column prop="grade" label="等级" width="90"/><el-table-column prop="latestDelivery" label="最迟交付" min-width="145"/><el-table-column prop="minShelfLife" label="最低可售期" width="100"/><el-table-column prop="status" label="状态" width="90"><template #default="s"><el-tag :type="s.row.status==='已匹配'?'success':'warning'">{{s.row.status}}</el-tag></template></el-table-column>
        </el-table>
      </el-card></el-col>
    </el-row>
  </div>
</template>
<script setup>
import { reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { schedulingState as state, addOrder } from '../data/schedulingDemo'
const form=reactive({customer:'县域采购商',product:'脐橙',quantity:80,grade:'A',latestDelivery:new Date(Date.now()+4*86400000).toISOString().slice(0,16),minShelfLife:4})
function submit(){addOrder({...form});ElMessage.success('订单已保存并进入待匹配队列')}
</script>
<style scoped>.unit{margin-left:8px;color:#64748b}</style>
