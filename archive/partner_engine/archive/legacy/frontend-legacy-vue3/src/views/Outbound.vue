<template>
  <div>
    <div class="page-title">出库管理：路径规划 + AGV 模拟 + 库存扣减</div>
    <el-row :gutter="16">
      <el-col :span="8">
        <el-card>
          <template #header>1. 创建出库订单</template>
          <el-form label-width="90px">
            <el-form-item label="商品">
              <el-select v-model="form.productId" style="width:100%;">
                <el-option v-for="p in products" :key="p.id" :label="`${p.name} / ${p.sku}`" :value="p.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="数量">
              <el-input-number v-model="form.quantity" :min="1" :max="200" />
            </el-form-item>
            <el-button type="primary" @click="createOrder">生成路径</el-button>
            <el-button type="success" :disabled="!order" @click="finishOrder">完成出库扣库存</el-button>
          </el-form>
        </el-card>
        <el-card v-if="order" style="margin-top:12px;">
          <template #header>2. 出库任务说明</template>
          <p>订单号：{{ order.id }}</p>
          <p>目标货架：{{ shelf.code }}</p>
          <p>路径点数量：{{ path.length }}</p>
          <p class="hint">{{ explain }}</p>
        </el-card>
      </el-col>
      <el-col :span="16">
        <Warehouse3D :twin="twin" :path="path" />
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../api/http'
import Warehouse3D from '../components/Warehouse3D.vue'

const products = ref([])
const twin = ref({})
const form = ref({ productId: null, quantity: 5 })
const order = ref(null)
const shelf = ref({})
const path = ref([])
const explain = ref('')

async function load() {
  products.value = await api.getProducts()
  form.value.productId = products.value[0]?.id
  twin.value = await api.getTwin()
}
async function createOrder() {
  const result = await api.createOutbound(form.value)
  order.value = result.order
  shelf.value = result.shelf
  path.value = result.path
  explain.value = result.explain
  ElMessage.success('路径已生成，请看黄色路径和 AGV 小球')
}
async function finishOrder() {
  await api.finishOutbound(order.value.id)
  ElMessage.success('出库完成，库存已扣减')
  twin.value = await api.getTwin()
  order.value = null
  path.value = []
}
onMounted(load)
</script>
