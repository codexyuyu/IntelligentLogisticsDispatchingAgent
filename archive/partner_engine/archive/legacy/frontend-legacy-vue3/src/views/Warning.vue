<template>
  <div>
    <div class="page-title">风险预警：库存异常、临期风险与人工处置</div>
    <el-card>
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <span>预警列表</span>
          <div>
            <el-button @click="load">刷新</el-button>
            <el-button type="primary" @click="scan">扫描风险预警</el-button>
          </div>
        </div>
      </template>
      <el-table :data="warnings" height="520">
        <el-table-column prop="type" label="类型" width="110" />
        <el-table-column prop="productName" label="商品" width="120" />
        <el-table-column prop="shelfCode" label="货架" width="90" />
        <el-table-column prop="message" label="预警原因" />
        <el-table-column prop="suggestion" label="AI 建议" />
        <el-table-column prop="status" label="状态" width="110">
          <template #default="scope">
            <el-tag :type="scope.row.status === 'OPEN' ? 'danger' : 'success'">{{ scope.row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="人工确认" width="130">
          <template #default="scope">
            <el-button size="small" type="success" :disabled="scope.row.status !== 'OPEN'" @click="confirm(scope.row.id)">生成补货</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../api/http'

const warnings = ref([])
async function load() { warnings.value = await api.listWarnings() }
async function scan() { await api.scanWarnings(); ElMessage.success('扫描完成'); await load() }
async function confirm(id) { const res = await api.confirmWarning(id); ElMessage.success(res.message); await load() }
onMounted(load)
</script>
