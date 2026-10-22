<template>
  <div>
    <div class="page-title">冷链运输：任务进度、车辆状态与温湿度监控</div>
    <el-alert
      type="info"
      :closable="false"
      show-icon
      title="当前版本使用演示运输数据；后续接入运输任务、GPS、温湿度传感器与数据库表时，页面结构无需重做。"
      style="margin-bottom:14px;"
    />

    <el-row :gutter="16">
      <el-col :span="6"><el-card class="metric-card"><div class="metric-label">运输中任务</div><div class="metric-value">{{ overview.runningTasks || 0 }}</div></el-card></el-col>
      <el-col :span="6"><el-card class="metric-card"><div class="metric-label">待收货任务</div><div class="metric-value">{{ overview.pendingReceiving || 0 }}</div></el-card></el-col>
      <el-col :span="6"><el-card class="metric-card"><div class="metric-label">温度异常</div><div class="metric-value">{{ overview.temperatureWarnings || 0 }}</div></el-card></el-col>
      <el-col :span="6"><el-card class="metric-card"><div class="metric-label">风险批次</div><div class="metric-value">{{ overview.riskBatchCount || 0 }}</div></el-card></el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top:16px;">
      <el-col :span="14">
        <el-card>
          <template #header>
            <div class="header-row"><span>冷链运输任务</span><el-button @click="load">刷新</el-button></div>
          </template>
          <div v-for="task in overview.tasks || []" :key="task.taskCode" class="task-card">
            <div class="task-head">
              <div>
                <b>{{ task.taskCode }} · {{ task.productName }}</b>
                <div class="hint">{{ task.origin }} → {{ task.destination }} · {{ task.vehicleNo }}</div>
              </div>
              <el-tag :type="statusType(task.status)">{{ task.status }}</el-tag>
            </div>
            <el-progress :percentage="task.progress" :status="task.status === '温度异常' ? 'exception' : undefined" />
            <div class="task-values">
              <span>车厢温度：<b>{{ task.temperature }}℃</b></span>
              <span>湿度：<b>{{ task.humidity }}%</b></span>
              <span>进度：<b>{{ task.progress }}%</b></span>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="10">
        <el-card>
          <template #header>冷链流转节点</template>
          <el-steps direction="vertical" :active="2" finish-status="success" style="height:300px;">
            <el-step title="创建运输任务" description="绑定商品、批次、车辆与目的仓库" />
            <el-step title="运输监控" description="持续采集 GPS、温度、湿度与运输时长" />
            <el-step title="到货收货" description="读取运输记录并执行质量验收" />
            <el-step title="生成批次并入库" description="预测保鲜期、分配货位并增加库存" />
          </el-steps>
        </el-card>
      </el-col>
    </el-row>

    <el-card style="margin-top:16px;">
      <template #header>最新运输传感器记录</template>
      <el-table :data="overview.sensorLogs || []" height="330">
        <el-table-column prop="taskCode" label="运输任务" width="160" />
        <el-table-column prop="collectTime" label="采集时间" width="100" />
        <el-table-column prop="temperature" label="温度(℃)" width="100" />
        <el-table-column prop="humidity" label="湿度(%)" width="100" />
        <el-table-column prop="location" label="GPS位置" />
        <el-table-column prop="status" label="状态" width="110">
          <template #default="scope"><el-tag :type="statusType(scope.row.status)">{{ scope.row.status }}</el-tag></template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../api/http'

const overview = ref({})

function statusType(status) {
  if (status === '高风险' || status === '温度异常') return 'danger'
  if (status === '预警' || status === '待收货') return 'warning'
  return 'success'
}

async function load() {
  overview.value = await api.getColdChainOverview()
  ElMessage.success('冷链运输数据已刷新')
}

onMounted(load)
</script>

<style scoped>
.header-row { display:flex; align-items:center; justify-content:space-between; }
.task-card { padding:14px; margin-bottom:12px; border:1px solid #e2e8f0; border-radius:14px; background:#f8fafc; }
.task-card:last-child { margin-bottom:0; }
.task-head { display:flex; align-items:flex-start; justify-content:space-between; margin-bottom:12px; }
.task-values { display:flex; gap:24px; margin-top:10px; color:#475569; font-size:13px; }
</style>
