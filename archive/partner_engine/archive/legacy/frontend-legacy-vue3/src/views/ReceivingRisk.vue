<template>
  <div>
    <div class="page-title">收货与预冷：到货验收、品质分级、预冷要求与批次生成</div>
    <el-row :gutter="16">
      <el-col :span="9">
        <el-card>
          <template #header>收货验收、预冷确认并生成生鲜批次</template>
          <el-form label-width="94px">
            <el-form-item label="商品">
              <el-select v-model="form.productId" style="width:100%;" placeholder="请选择商品">
                <el-option v-for="p in products" :key="p.id" :label="`${p.productName} / ${p.category}`" :value="p.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="入库货架">
              <el-select v-model="form.shelfId" style="width:100%;" placeholder="请选择货架">
                <el-option v-for="s in shelves" :key="s.id" :label="`${s.code} / 剩余${s.free}`" :value="s.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="到货数量"><el-input-number v-model="form.quantity" :min="1" :max="500" /></el-form-item>
            <el-form-item label="供应商"><el-input v-model="form.supplier" /></el-form-item>
            <el-form-item label="产地"><el-input v-model="form.originPlace" /></el-form-item>
            <el-form-item label="品质评分"><el-input-number v-model="form.initialQualityScore" :min="0" :max="100" /></el-form-item>
            <el-form-item label="到货温度"><el-input-number v-model="form.storageTemperature" :min="-30" :max="60" :step="0.1" /></el-form-item>
            <el-form-item label="到货湿度"><el-input-number v-model="form.storageHumidity" :min="0" :max="100" /></el-form-item>
            <el-button type="primary" @click="confirmReceive">确认收货、预冷并生成批次</el-button>
          </el-form>
          <p class="hint">验收成功后，系统会生成 fresh_batch、增加库存，并根据品质和温湿度预测保鲜期与风险状态。</p>
        </el-card>
      </el-col>

      <el-col :span="15">
        <el-card>
          <template #header>
            <div class="header-row"><span>风险批次</span><el-button @click="loadBatches">刷新</el-button></div>
          </template>
          <el-table :data="riskBatches" height="390">
            <el-table-column prop="batchCode" label="批次号" width="180" />
            <el-table-column prop="productName" label="商品" width="130" />
            <el-table-column prop="shelfCode" label="货架" width="90" />
            <el-table-column prop="quantityRemaining" label="剩余数量" width="90" />
            <el-table-column prop="remainingDays" label="剩余天数" width="90" />
            <el-table-column prop="freshnessScore" label="新鲜度" width="90" />
            <el-table-column prop="status" label="风险状态" width="120">
              <template #default="scope"><el-tag :type="riskType(scope.row.status)">{{ scope.row.status }}</el-tag></template>
            </el-table-column>
          </el-table>
        </el-card>

        <el-card style="margin-top:14px;">
          <template #header>全部收货批次</template>
          <el-table :data="batches" height="260">
            <el-table-column prop="batchCode" label="批次号" width="180" />
            <el-table-column prop="productName" label="商品" width="130" />
            <el-table-column prop="supplier" label="供应商" />
            <el-table-column prop="storageTemperature" label="温度(℃)" width="90" />
            <el-table-column prop="remainingDays" label="剩余天数" width="90" />
            <el-table-column prop="status" label="状态" width="110" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../api/http'

const products = ref([])
const shelves = ref([])
const batches = ref([])
const riskBatches = ref([])
const form = ref({
  productId: null,
  shelfId: null,
  quantity: 20,
  supplier: '华南生鲜供应商',
  originPlace: '广东',
  purchasePrice: 18.5,
  qualityGrade: 'A',
  initialQualityScore: 90,
  storageTemperature: 4,
  storageHumidity: 80
})

function riskType(status) {
  if (status === 'EXPIRED' || status === 'TEMP_ABNORMAL') return 'danger'
  if (status === 'EXPIRING') return 'warning'
  return 'success'
}

async function loadBase() {
  products.value = await api.getProducts()
  const twin = await api.getTwin()
  shelves.value = twin.shelves || []
  form.value.productId ||= products.value[0]?.id
  form.value.shelfId ||= shelves.value[0]?.id
}

async function loadBatches() {
  const [all, risk] = await Promise.all([api.getFreshBatches(), api.getRiskBatches()])
  batches.value = all
  riskBatches.value = risk
}

async function confirmReceive() {
  const result = await api.confirmFreshReceive(form.value)
  ElMessage.success(result.message || '收货成功')
  await loadBatches()
}

onMounted(async () => {
  await Promise.all([loadBase(), loadBatches()])
})
</script>

<style scoped>
.header-row { display:flex; align-items:center; justify-content:space-between; }
</style>
