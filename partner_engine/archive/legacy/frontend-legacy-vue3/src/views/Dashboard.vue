<template>
  <div>
    <div class="page-title">三维仓库执行视图</div>
    <!-- <el-alert class="demo-alert" type="info" :closable="false" show-icon title="第一阶段展示 Demo：左侧为预留分拣区，右侧为存储区；叉车默认沿黄色路线巡检并经过每一个货架。" /> -->
    <MetricCards :items="cards" />
    <el-row :gutter="16" style="margin-top:16px;">
      <el-col :span="16">
        <Warehouse3D :twin="twin" :path="path" @selectShelf="selectShelf" />
      </el-col>
      <el-col :span="8">
        <el-card>
          <template #header>货架信息</template>
          <div v-if="selectedShelf">
            <h3>{{ selectedShelf.code }} / {{ selectedShelf.category }}</h3>
            <p>状态：<el-tag :type="selectedShelf.status === 'WARNING' ? 'danger' : 'success'">{{ selectedShelf.status }}</el-tag></p>
            <p>容量：{{ selectedShelf.used }} / {{ selectedShelf.capacity }}，剩余 {{ selectedShelf.free }}</p>
            <el-table :data="selectedShelf.inventory || []" size="small" height="180">
              <el-table-column prop="productName" label="商品" />
              <el-table-column prop="layerNo" label="层" width="50" />
              <el-table-column prop="quantity" label="数量" width="70" />
            </el-table>
          </div>
          <div v-else class="hint">点击 3D 货架，就能查看商品与库存信息。</div>
        </el-card>
        <el-card style="margin-top:12px;">
          <template #header>仓储区域</template>
          <div class="zone-list">
            <div v-for="zone in twin.zones || []" :key="zone.code" class="zone-item">
              <b>{{ zone.name }}</b>
              <span>{{ zone.width }}m × {{ zone.depth }}m</span>
              <el-tag size="small" :type="zone.code === 'PICKING' ? 'info' : 'success'">{{ zone.code === 'PICKING' ? '预留空区' : '已放置货架' }}</el-tag>
            </div>
          </div>
        </el-card>
        <el-card style="margin-top:12px;">
          <DashboardChart :metrics="metrics" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { Client } from '@stomp/stompjs'
import SockJS from 'sockjs-client/dist/sockjs'
import { ElMessage } from 'element-plus'
import { api } from '../api/http'
import MetricCards from '../components/MetricCards.vue'
import Warehouse3D from '../components/Warehouse3D.vue'
import DashboardChart from '../components/DashboardChart.vue'

const metrics = ref({})
const twin = ref({})
const selectedShelf = ref(null)
const path = ref([])
const WS_URL = import.meta.env.VITE_WS_URL || '/ws'

const cards = computed(() => [
  { label: '总库存', value: metrics.value.totalStock || 0 },
  { label: '库存预警数', value: metrics.value.lowStockWarnings || 0 },
  { label: '今日入库', value: metrics.value.todayInbound || 0 },
  { label: '今日出库', value: metrics.value.todayOutbound || 0 }
])

async function load() {
  metrics.value = await api.getDashboard()
  twin.value = await api.getTwin()
  if (selectedShelf.value) {
    selectedShelf.value = twin.value.shelves?.find(s => s.id === selectedShelf.value.id) || null
  }
}
function selectShelf(shelf) { selectedShelf.value = shelf }
function connectWs() {
  const client = new Client({
    webSocketFactory: () => new SockJS(WS_URL),
    reconnectDelay: 3000,
    onConnect: () => {
      client.subscribe('/topic/warehouse', async (message) => {
        const event = JSON.parse(message.body)
        ElMessage.success(`实时事件：${event.eventType}`)
        await load()
      })
    }
  })
  client.activate()
}
onMounted(async () => { await load(); connectWs() })
</script>


<style scoped>
.demo-alert { margin-bottom: 14px; }
.zone-list { display: grid; gap: 10px; }
.zone-item { display: grid; grid-template-columns: 1fr auto; gap: 6px 10px; align-items: center; padding: 10px; border-radius: 12px; background: #f8fafc; border: 1px solid #e2e8f0; }
.zone-item span { color: #64748b; font-size: 13px; }
.zone-item .el-tag { justify-self: start; }
</style>
