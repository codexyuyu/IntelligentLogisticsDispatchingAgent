<template>
  <Login v-if="!currentUser" @loggedIn="handleLoggedIn" />
  <el-container v-else class="app-shell">
    <el-aside width="286px" class="aside">
      <div class="logo">县域产地冷链调度系统</div>
      <div class="sub-logo">仓储作业为基础 · 冷间时间窗调度为核心</div>
      <div class="user-card">
        <div class="avatar">{{ currentUser.displayName?.slice(0, 1) || '用' }}</div>
        <div><b>{{ currentUser.displayName }}</b><span>{{ currentUser.role }} · {{ currentUser.username }}</span></div>
      </div>
      <el-menu
        :default-active="active"
        :default-openeds="['supply','warehouse','scheduling','qualityTwin']"
        class="menu"
        @select="active = $event"
      >
        <el-sub-menu index="supply">
          <template #title>1. 供货与订单</template>
          <el-menu-item index="supplyBatch">1.1 供货与批次</el-menu-item>
          <el-menu-item index="customerOrder">1.2 销售订单</el-menu-item>
        </el-sub-menu>
        <el-sub-menu index="warehouse">
          <template #title>2. 仓储作业</template>
          <el-menu-item index="inboundOperation">2.1 入库作业</el-menu-item>
          <el-menu-item index="inventoryOutbound">2.2 库存与出库</el-menu-item>
        </el-sub-menu>
        <el-sub-menu index="scheduling">
          <template #title>3. 协同调度</template>
          <el-menu-item index="coldRoomManagement">3.1 冷间资源</el-menu-item>
          <el-menu-item index="dispatchCenter">3.2 调度中心</el-menu-item>
        </el-sub-menu>
        <el-sub-menu index="qualityTwin">
          <template #title>4. 品质与数字孪生</template>
          <el-menu-item index="riskCenter">4.1 异常与品质风险</el-menu-item>
          <el-menu-item index="twinCockpit">4.2 数字孪生驾驶舱</el-menu-item>
        </el-sub-menu>
      </el-menu>
      <el-button class="logout" plain @click="logout">退出登录</el-button>
    </el-aside>
    <el-main class="main">
      <SupplyBatch v-if="active==='supplyBatch'" />
      <CustomerOrder v-else-if="active==='customerOrder'" />
      <InboundOperation v-else-if="active==='inboundOperation'" />
      <InventoryOutbound v-else-if="active==='inventoryOutbound'" />
      <ColdRoomManagement v-else-if="active==='coldRoomManagement'" />
      <DispatchCenter v-else-if="active==='dispatchCenter'" />
      <RiskCenter v-else-if="active==='riskCenter'" />
      <TwinCockpit v-else-if="active==='twinCockpit'" />
    </el-main>
  </el-container>
</template>

<script setup>
import { ref } from 'vue'
import { authStorage } from './api/http'
import Login from './views/Login.vue'
import SupplyBatch from './views/SupplyBatch.vue'
import CustomerOrder from './views/CustomerOrder.vue'
import InboundOperation from './views/InboundOperation.vue'
import InventoryOutbound from './views/InventoryOutbound.vue'
import ColdRoomManagement from './views/ColdRoomManagement.vue'
import DispatchCenter from './views/DispatchCenter.vue'
import RiskCenter from './views/RiskCenter.vue'
import TwinCockpit from './views/TwinCockpit.vue'

const active = ref('twinCockpit')
const currentUser = ref(authStorage.user())

function handleLoggedIn(user) {
  currentUser.value = user
}

function logout() {
  authStorage.clear()
  currentUser.value = null
  active.value = 'twinCockpit'
}
</script>

<style scoped>
.app-shell{min-height:100vh}.aside{background:#0f172a;color:white;padding:18px 12px;border-right:1px solid #243047;display:flex;flex-direction:column}.logo{font-size:20px;font-weight:800;margin:8px 8px 0}.sub-logo{color:#94a3b8;margin:6px 8px 14px;font-size:12px;line-height:1.5}.user-card{display:flex;gap:10px;align-items:center;margin:4px 8px 12px;padding:11px;border-radius:14px;background:#111827;border:1px solid #334155}.avatar{width:38px;height:38px;border-radius:13px;display:grid;place-items:center;background:#2563eb;font-weight:800}.user-card b{display:block}.user-card span{display:block;color:#94a3b8;font-size:12px;margin-top:4px}.menu{background:transparent;border:none;overflow-y:auto;flex:1}:deep(.el-menu-item),:deep(.el-sub-menu__title){color:#dbeafe;border-radius:10px;margin:3px 0}:deep(.el-menu-item.is-active){background:#2563eb;color:white}:deep(.el-menu-item:hover),:deep(.el-sub-menu__title:hover){background:#1e293b;color:white}:deep(.el-sub-menu .el-menu){background:transparent}:deep(.el-sub-menu .el-menu-item){min-width:auto;padding-left:38px!important;color:#bfdbfe}.main{padding:20px;background:#e2e8f0;color:#111827;overflow-x:hidden}.logout{margin:12px 8px 0;color:#dbeafe;border-color:#334155;background:transparent}
</style>
