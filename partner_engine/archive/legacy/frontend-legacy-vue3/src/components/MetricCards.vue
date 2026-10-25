<template>
  <el-row :gutter="12">
    <el-col :span="6" v-for="item in items" :key="item.label">
      <el-card class="metric-card" shadow="hover">
        <div class="metric-label">{{ item.label }}</div>
        <div class="metric-value">{{ item.value }}</div>
      </el-card>
    </el-col>
  </el-row>
</template>

<script setup>
defineProps({ items: { type: Array, default: () => [] } })
</script>
