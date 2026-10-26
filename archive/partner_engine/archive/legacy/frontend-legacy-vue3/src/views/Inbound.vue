<template>
  <div>
    <div class="page-title">入库管理：AI 推荐货位 + 人工确认</div>
    <el-row :gutter="16">
      <el-col :span="9">
        <el-card>
          <template #header>1. 添加入库任务</template>
          <el-form label-width="90px">
            <el-form-item label="商品">
              <el-select v-model="form.productId" placeholder="请选择商品" style="width:100%;">
                <el-option v-for="p in products" :key="p.id" :label="`${p.name} / ${p.category}`" :value="p.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="数量">
              <el-input-number v-model="form.quantity" :min="1" :max="500" />
            </el-form-item>
            <el-button type="primary" @click="recommend">生成推荐货架</el-button>
          </el-form>
          <p class="hint">为什么这样做：先让系统根据容量、品类和距离算推荐，再由管理员确认，体现“AI 建议 + 人工确认”。</p>
        </el-card>
        <el-card v-if="result" style="margin-top:12px;">
          <template #header>2. 推荐结果</template>
          <p><b>最佳货架：</b>{{ result.best.shelfCode }}</p>
          <p><b>推荐理由：</b>{{ result.best.reason }}</p>
          <p><b>评分说明：</b>{{ result.explain }}</p>
          <el-button type="success" @click="confirm">管理员确认入库</el-button>
        </el-card>
      </el-col>
      <el-col :span="15">
        <el-card>
          <template #header>候选货架评分</template>
          <el-table :data="result?.candidates || []" height="360">
            <el-table-column prop="shelfCode" label="货架" width="90" />
            <el-table-column prop="category" label="品类" width="90" />
            <el-table-column prop="free" label="剩余容量" width="90" />
            <el-table-column prop="distanceToExit" label="距出口" width="90" />
            <el-table-column prop="score" label="评分" width="90" />
            <el-table-column prop="reason" label="原因" />
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
const form = ref({ productId: null, quantity: 20 })
const result = ref(null)
async function loadProducts() { products.value = await api.getProducts(); form.value.productId = products.value[0]?.id }
async function recommend() {
  result.value = await api.recommendInbound(form.value)
  ElMessage.success('已生成推荐货架')
}
async function confirm() {
  await api.confirmInbound({ ...form.value, shelfId: result.value.best.shelfId })
  ElMessage.success('入库成功，3D 大屏会实时刷新')
  result.value = null
}
onMounted(loadProducts)
</script>
