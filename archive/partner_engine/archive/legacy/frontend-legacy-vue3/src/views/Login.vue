<template>
  <div class="auth-page">
    <div class="auth-hero">
      <div class="badge">County Cold-Chain Scheduling</div>
      <h1>县域产地冷链调度系统</h1>
      <p>以现有仓储系统为执行基础，展示农户供货、合作社组批、冷间时间窗调度与异常重调度。</p>
      <div class="hero-grid">
        <div><b>供货与组批</b><span>汇总农户采收计划，形成可调度标准批次</span></div>
        <div><b>冷间时间窗</b><span>综合容量、温区、清洁与设备状态安排批次</span></div>
        <div><b>异常重调度</b><span>应对到货偏差、订单变化与冷间故障</span></div>
      </div>
    </div>

    <el-card class="auth-card">
      <template #header>
        <div class="auth-tabs">
          <button :class="{ active: mode === 'login' }" @click="mode = 'login'">登录</button>
          <button :class="{ active: mode === 'register' }" @click="mode = 'register'">注册用户</button>
        </div>
      </template>

      <el-form label-position="top" @keyup.enter="submit">
        <el-form-item label="用户名">
          <el-input v-model.trim="form.username" placeholder="例如：admin / demo" size="large" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password placeholder="不少于 6 位" size="large" />
        </el-form-item>
        <el-button type="primary" size="large" class="auth-submit" :loading="loading" @click="submit">
          {{ mode === 'login' ? '进入系统' : '创建账号并进入系统' }}
        </el-button>
      </el-form>

      <div class="demo-account">
        <b>演示账号</b>
        <span>admin / admin123</span>
        <span>demo / demo123</span>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api, authStorage } from '../api/http'

const emit = defineEmits(['loggedIn'])
const mode = ref('login')
const loading = ref(false)
const form = reactive({ username: 'admin', password: 'admin123' })

async function submit() {
  if (!form.username || !form.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    const payload = mode.value === 'login'
      ? { username: form.username, password: form.password }
      : { username: form.username, password: form.password }
    const result = mode.value === 'login' ? await api.login(payload) : await api.register(payload)
    authStorage.save(result)
    ElMessage.success(mode.value === 'login' ? '登录成功' : '注册成功')
    emit('loggedIn', result.user)
  } catch (error) {
    ElMessage.error(error.message || '操作失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 1.15fr 440px;
  gap: 36px;
  align-items: center;
  padding: 52px;
  background:
    radial-gradient(circle at 18% 20%, rgba(37, 99, 235, 0.45), transparent 34%),
    radial-gradient(circle at 75% 35%, rgba(20, 184, 166, 0.28), transparent 28%),
    linear-gradient(135deg, #020617, #0f172a 54%, #111827);
  color: #f8fafc;
}
.auth-hero { max-width: 720px; }
.badge { display: inline-flex; padding: 8px 12px; border: 1px solid rgba(148, 163, 184, 0.35); border-radius: 999px; color: #bfdbfe; background: rgba(15, 23, 42, 0.72); font-size: 13px; }
h1 { font-size: 48px; line-height: 1.12; margin: 22px 0 14px; letter-spacing: -1px; }
p { color: #cbd5e1; font-size: 17px; line-height: 1.8; margin: 0; }
.hero-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-top: 34px; }
.hero-grid div { min-height: 112px; padding: 16px; border: 1px solid rgba(148, 163, 184, 0.25); border-radius: 18px; background: rgba(15, 23, 42, 0.62); box-shadow: 0 18px 48px rgba(0,0,0,0.22); }
.hero-grid b { display: block; margin-bottom: 8px; font-size: 18px; }
.hero-grid span { color: #94a3b8; font-size: 13px; line-height: 1.6; }
.auth-card { border: 1px solid rgba(148, 163, 184, 0.32); border-radius: 22px; box-shadow: 0 28px 80px rgba(0,0,0,0.32); }
.auth-tabs { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.auth-tabs button { border: 0; border-radius: 12px; padding: 11px 0; background: #e2e8f0; color: #334155; cursor: pointer; font-weight: 700; }
.auth-tabs button.active { background: #2563eb; color: white; }
.auth-submit { width: 100%; margin-top: 4px; }
.demo-account { margin-top: 18px; padding: 12px; border-radius: 14px; background: #f1f5f9; color: #334155; display: grid; gap: 6px; font-size: 13px; }
.demo-account b { color: #0f172a; }
@media (max-width: 980px) {
  .auth-page { grid-template-columns: 1fr; padding: 24px; }
  .hero-grid { grid-template-columns: 1fr; }
}
</style>
