<script setup>
import { computed, ref } from 'vue'
import { createReport, streamChat, uploadDataset } from './api'

const file = ref(null)
const uploading = ref(false)
const dataset = ref(null)
const question = ref('')
const sessionId = ref(null)
const runId = ref(null)
const running = ref(false)
const traces = ref([])
const messages = ref([])
const answer = ref(null)
const error = ref('')

const fields = computed(() => dataset.value?.profile?.fields || [])

function selectFile(e) { file.value = e.target.files?.[0] || null }

async function doUpload() {
  if (!file.value) return
  error.value = ''; uploading.value = true
  try {
    dataset.value = await uploadDataset(file.value)
    sessionId.value = null; messages.value = []; traces.value = []; answer.value = null
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally { uploading.value = false }
}

async function ask() {
  const text = question.value.trim()
  if (!text || !dataset.value || running.value) return
  messages.value.push({ role: 'user', content: text })
  question.value = ''; traces.value = []; answer.value = null; error.value = ''; running.value = true
  try {
    await streamChat({ dataset_id: dataset.value.dataset_id, session_id: sessionId.value, message: text }, (evt) => {
      if (evt.type === 'session') { sessionId.value = evt.session_id; runId.value = evt.run_id }
      if (evt.type === 'trace') traces.value.push(evt.data)
      if (evt.type === 'done') {
        sessionId.value = evt.session_id; runId.value = evt.run_id; answer.value = evt.answer
        messages.value.push({ role: 'assistant', content: evt.answer.summary })
      }
      if (evt.type === 'error') error.value = evt.message
    })
  } catch (e) { error.value = e.message } finally { running.value = false }
}

async function exportReport() {
  if (!sessionId.value) return
  try {
    const r = await createReport(sessionId.value)
    window.open(r.url, '_blank')
  } catch (e) { error.value = e.response?.data?.detail || e.message }
}
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="brand"><span class="logo">DP</span><div><strong>DataPilot</strong><small>Agent V4</small></div></div>
      <section class="side-section">
        <h3>数据集</h3>
        <label class="upload-box">
          <input type="file" accept=".csv,.xlsx,.xls" @change="selectFile" />
          <span>{{ file?.name || '选择 CSV / Excel' }}</span>
        </label>
        <button class="primary full" :disabled="!file || uploading" @click="doUpload">{{ uploading ? '上传中...' : '上传并解析' }}</button>
      </section>

      <section v-if="dataset" class="side-section dataset-card">
        <h3>{{ dataset.filename }}</h3>
        <div class="stats"><div><b>{{ dataset.rows }}</b><span>行</span></div><div><b>{{ dataset.columns }}</b><span>列</span></div></div>
        <p class="muted">重复行：{{ dataset.profile.duplicate_rows }}</p>
      </section>

      <section v-if="fields.length" class="side-section field-list">
        <h3>字段</h3>
        <div v-for="f in fields" :key="f.name" class="field-row"><span>{{ f.name }}</span><code>{{ f.dtype }}</code></div>
      </section>
    </aside>

    <main class="main">
      <header class="topbar">
        <div><h1>智能数据分析工作台</h1><p>LangGraph · Pandas · PostgreSQL · Redis · Python Sandbox</p></div>
        <button class="ghost" :disabled="!sessionId" @click="exportReport">导出 HTML 报告</button>
      </header>

      <div v-if="!dataset" class="empty-state">
        <div class="empty-icon">↥</div><h2>先上传一个数据集</h2><p>支持 CSV、XLSX、XLS。上传后会自动生成 Dataset Profile 并写入 PostgreSQL。</p>
      </div>

      <template v-else>
        <section class="chat-card">
          <div class="messages">
            <div v-if="messages.length === 0" class="welcome">
              <h2>可以开始提问</h2><p>例如：哪个地区销售额最高？销售额和利润的分布如何？找出异常订单并解释。</p>
            </div>
            <div v-for="(m,i) in messages" :key="i" :class="['message', m.role]">
              <b>{{ m.role === 'user' ? '你' : 'DataPilot' }}</b><p>{{ m.content }}</p>
            </div>
          </div>
          <div class="composer">
            <textarea v-model="question" placeholder="用自然语言描述你想分析的问题..." @keydown.ctrl.enter.prevent="ask"></textarea>
            <button class="primary" :disabled="running || !question.trim()" @click="ask">{{ running ? '分析中...' : '开始分析' }}</button>
          </div>
        </section>

        <section v-if="traces.length" class="panel">
          <div class="panel-title"><h2>Agent 执行过程</h2><span v-if="runId" class="run-id">{{ runId }}</span></div>
          <div class="trace-list">
            <div v-for="(t,i) in traces" :key="i" class="trace-row">
              <span :class="['dot', t.status]"></span><b>{{ t.stage }}</b><span>{{ t.detail }}</span>
            </div>
          </div>
        </section>

        <section v-if="answer" class="results-grid">
          <div class="panel span-2"><h2>核心结论</h2><p class="summary">{{ answer.summary }}</p></div>
          <div class="panel"><h2>关键发现</h2><ol><li v-for="(x,i) in answer.findings" :key="i">{{ x }}</li></ol></div>
          <div class="panel"><h2>关键指标</h2><div class="metric-grid"><div v-for="(m,i) in answer.metrics" :key="i" class="metric"><span>{{ m.name }}</span><b>{{ m.value }}</b></div></div></div>
          <div v-if="answer.charts?.length" class="panel span-2"><h2>图表</h2><div class="chart-grid"><figure v-for="c in answer.charts" :key="c.id"><img :src="c.url" :alt="c.title"/><figcaption>{{ c.title }}</figcaption></figure></div></div>
          <div class="panel"><h2>建议</h2><ul><li v-for="(x,i) in answer.recommendations" :key="i">{{ x }}</li></ul></div>
          <div class="panel"><h2>限制</h2><ul v-if="answer.limitations?.length"><li v-for="(x,i) in answer.limitations" :key="i">{{ x }}</li></ul><p v-else class="muted">没有未恢复错误。</p></div>
        </section>
      </template>
      <div v-if="error" class="error-box">{{ error }}</div>
    </main>
  </div>
</template>
