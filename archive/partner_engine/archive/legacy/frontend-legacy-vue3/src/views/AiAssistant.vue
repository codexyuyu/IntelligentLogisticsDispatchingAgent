<template>
  <div>
    <div class="page-title">调度 Agent：查询状态、调用调度能力并解释方案</div>
    <el-row :gutter="16">
      <el-col :span="14">
        <el-card>
          <template #header>自然语言提问</template>
          <el-input v-model="question" type="textarea" :rows="4" placeholder="例如：每日鲜语低温鲜牛奶库存在哪？哪些批次需要优先调度？出库路径怎么规划？" />
          <div style="margin-top:12px;">
            <el-button type="primary" @click="ask">发送问题</el-button>
            <el-button @click="question='哪些批次需要优先调度？'">调度示例</el-button>
            <el-button @click="question='每日鲜语低温鲜牛奶库存在哪？'">库存示例</el-button>
          </div>
        </el-card>
        <el-card v-if="answer" style="margin-top:12px;">
          <template #header>回答结果</template>
          <el-tag>{{ mode }}</el-tag>
          <pre class="answer">{{ answer }}</pre>
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card>
          <template #header>调度 Agent 的职责</template>
          <ol class="hint">
            <li>调用品质风险评估、调度求解和重调度能力。</li>
            <li>理解用户问题，查询供货、订单、冷间、批次和异常事件。</li>
            <li>最终方案由确定性求解器产生，Agent负责调用和解释。</li>
            <li>AI 只给建议，真正改变库存必须由管理员点击确认。</li>
          </ol>
        </el-card>
        <el-card v-if="context" style="margin-top:12px;">
          <template #header>本次检索到的上下文</template>
          <pre class="context">{{ context }}</pre>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../api/http'

const question = ref('哪些批次需要优先调度？')
const answer = ref('')
const context = ref('')
const mode = ref('')
async function ask() {
  const res = await api.chat(question.value)
  answer.value = res.answer
  context.value = res.context
  mode.value = res.mode
  ElMessage.success('AI 已回答')
}
</script>

<style scoped>
.answer, .context { white-space: pre-wrap; line-height: 1.7; background: #0f172a; color: #e5e7eb; border-radius: 12px; padding: 12px; }
.context { max-height: 330px; overflow: auto; font-size: 12px; }
</style>
