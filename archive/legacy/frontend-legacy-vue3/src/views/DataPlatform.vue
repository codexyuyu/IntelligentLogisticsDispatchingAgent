<template>
  <div>
    <div class="page-title">数据平台：供货、订单、冷间、仓储与风险数据汇总</div>
    <el-alert type="info" :closable="false" show-icon :title="overview.note || '大数据平台为 AI 模块提供数据基础。'" style="margin-bottom:14px;" />

    <el-row :gutter="16">
      <el-col v-for="item in cards" :key="item.label" :span="4">
        <el-card class="metric-card">
          <div class="metric-label">{{ item.label }}</div>
          <div class="metric-value">{{ item.value }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top:16px;">
      <el-col :span="16">
        <el-card>
          <template #header>数据采集量与商品消耗趋势</template>
          <div ref="trendEl" class="chart"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <template #header>风险数据分布</template>
          <div ref="riskEl" class="chart"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-card style="margin-top:16px;">
      <template #header>
        <div class="header-row"><span>数据源与采集任务</span><el-button @click="load">刷新数据</el-button></div>
      </template>
      <el-table :data="overview.sources || []" height="330">
        <el-table-column prop="name" label="数据源" width="210" />
        <el-table-column prop="method" label="采集方式" />
        <el-table-column prop="frequency" label="采集频率" width="120" />
        <el-table-column prop="status" label="状态" width="110">
          <template #default="scope"><el-tag :type="scope.row.status === '演示' ? 'warning' : 'success'">{{ scope.row.status }}</el-tag></template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import * as echarts from 'echarts'
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../api/http'

const overview = ref({ metrics: {} })
const trendEl = ref(null)
const riskEl = ref(null)
let trendChart
let riskChart

const cards = computed(() => [
  { label: '商品种类', value: overview.value.metrics?.productCount || 0 },
  { label: '库存总量', value: overview.value.metrics?.totalStock || 0 },
  { label: '生鲜批次', value: overview.value.metrics?.freshBatchCount || 0 },
  { label: '风险批次', value: overview.value.metrics?.riskBatchCount || 0 },
  { label: '开放预警', value: overview.value.metrics?.openWarningCount || 0 },
  { label: '今日采集', value: overview.value.metrics?.todayCollectedRecords || 0 }
])

function renderCharts() {
  if (trendEl.value) {
    trendChart ||= echarts.init(trendEl.value)
    trendChart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: ['采集记录', '消耗量'] },
      xAxis: { type: 'category', data: overview.value.dates || [] },
      yAxis: [{ type: 'value', name: '采集记录' }, { type: 'value', name: '消耗量' }],
      series: [
        { name: '采集记录', type: 'bar', data: overview.value.collectionTrend || [] },
        { name: '消耗量', type: 'line', yAxisIndex: 1, smooth: true, data: overview.value.consumptionTrend || [] }
      ]
    })
  }
  if (riskEl.value) {
    riskChart ||= echarts.init(riskEl.value)
    riskChart.setOption({
      tooltip: { trigger: 'item' },
      legend: { bottom: 0 },
      series: [{ type: 'pie', radius: ['38%', '68%'], data: overview.value.riskDistribution || [] }]
    })
  }
}

async function load() {
  overview.value = await api.getDataPlatformOverview()
  await nextTick()
  renderCharts()
  ElMessage.success('大数据平台已刷新')
}

function resize() {
  trendChart?.resize()
  riskChart?.resize()
}

onMounted(() => {
  load()
  window.addEventListener('resize', resize)
})
onUnmounted(() => {
  window.removeEventListener('resize', resize)
  trendChart?.dispose()
  riskChart?.dispose()
})
</script>

<style scoped>
.chart { width:100%; height:330px; }
.header-row { display:flex; align-items:center; justify-content:space-between; }
.metric-value { font-size:25px; }
</style>
