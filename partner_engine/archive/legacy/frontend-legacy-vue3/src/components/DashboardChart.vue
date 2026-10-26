<template>
  <div ref="chartEl" style="height:260px;width:100%;"></div>
</template>

<script setup>
import * as echarts from 'echarts'
import { onMounted, onUnmounted, ref, watch } from 'vue'

const props = defineProps({ metrics: { type: Object, default: () => ({}) } })
const chartEl = ref(null)
let chart

function render() {
  if (!chartEl.value) return
  if (!chart) chart = echarts.init(chartEl.value)
  chart.setOption({
    title: { text: '仓储关键指标', left: 'center' },
    tooltip: {},
    xAxis: { type: 'category', data: ['总库存', '库存预警', '今日入库', '今日出库', '异常数量'] },
    yAxis: { type: 'value' },
    series: [{
      name: '数量',
      type: 'bar',
      data: [
        props.metrics.totalStock || 0,
        props.metrics.lowStockWarnings || 0,
        props.metrics.todayInbound || 0,
        props.metrics.todayOutbound || 0,
        props.metrics.openWarnings || 0
      ]
    }]
  })
}

onMounted(() => { render(); window.addEventListener('resize', () => chart?.resize()) })
onUnmounted(() => chart?.dispose())
watch(() => props.metrics, render, { deep: true })
</script>
