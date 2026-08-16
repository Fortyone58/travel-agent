<template>
  <div class="app">
    <header class="header">
      <h1>🗺️ 旅行规划多Agent系统</h1>
      <span class="tag">规划-执行-评审</span>
      <span class="tag">手搓三角色</span>
      <span class="tag">三重混合RAG</span>
    </header>

    <div class="layout">
      <!-- ===== 左侧 ===== -->
      <aside class="sidebar">
        <!-- 旅行需求表单 -->
        <div class="card">
          <h3>✏️ 旅行需求</h3>
          <label>目的地</label>
          <input v-model="form.city" placeholder="如：石家庄">
          <label>旅行天数</label>
          <input v-model="form.days" placeholder="如：3">
          <label>预算（元）</label>
          <input v-model="form.budget" placeholder="如：1000">
          <label>兴趣偏好</label>
          <input v-model="form.interests" placeholder="如：美食、博物馆">
          <label>或直接输入自然语言</label>
          <textarea v-model="form.nl" placeholder="3天2晚石家庄，预算1000，喜欢吃"></textarea>
          <button class="btn" :disabled="generating" @click="generate">
            {{ generating ? '⏳ 生成中…' : '🚀 生成旅行方案' }}
          </button>
        </div>

        <!-- 攻略管理（上传 + 列表） -->
        <div class="card">
          <h3>📚 攻略知识库</h3>
          <input type="file" accept=".txt,.pdf" ref="fileInput" class="file-input">
          <button class="btn" :disabled="uploading" @click="uploadGuide">
            {{ uploading ? '⏳ 上传中…' : '⬆️ 上传攻略（txt/pdf）' }}
          </button>
          <div class="upload-msg" :class="{ err: uploadErr }">{{ uploadMsg }}</div>
          <div class="guide-list">
            <div v-for="g in guides" :key="g.name" class="guide-item">
              <span class="g-name" :title="g.name">{{ g.name }}</span>
              <span class="g-chunks">{{ g.chunks }} 块</span>
              <button class="del-btn" @click="deleteGuide(g.name)">删除</button>
            </div>
            <div v-if="!guides.length" class="empty-small">暂无攻略</div>
          </div>
        </div>

        <!-- 历史记录 -->
        <div class="card">
          <h3>🗂️ 历史记录</h3>
          <div class="history-list">
            <div v-for="h in history" :key="h.id" class="guide-item">
              <span class="g-name" :title="h.task" @click="openHistory(h.id)">{{ h.task }}</span>
              <span class="g-chunks">{{ h.created_at }}</span>
              <button class="del-btn" @click="delHistory(h.id)">删除</button>
            </div>
            <div v-if="!history.length" class="empty-small">暂无历史</div>
          </div>
        </div>
      </aside>

      <!-- ===== 右侧 ===== -->
      <main class="main">
        <div class="card">
          <h3>🔍 运行过程（Trace）</h3>
          <div class="trace" ref="traceBox">
            <div v-for="(line, i) in traceLines" :key="i" :class="line.cls">{{ line.text }}</div>
          </div>
        </div>

        <div class="card">
          <div class="result-head">
            <h3>📄 行程方案</h3>
            <button class="btn btn-gray" :disabled="!canSave" @click="saveTrip">💾 保存</button>
          </div>
          <div id="result-box" class="result-body">
            <div v-if="resultHtml" class="md" v-html="resultHtml"></div>
            <div v-else class="empty">生成结果会显示在这里</div>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick } from 'vue'
import { marked } from 'marked'

// ===== 状态 =====
const form = reactive({ city: '', days: '', budget: '', interests: '', nl: '' })
const generating = ref(false)
const uploading = ref(false)
const uploadMsg = ref('')
const uploadErr = ref(false)
const traceLines = ref([])
const resultHtml = ref('')
const canSave = ref(false)
let currentResult = null
const guides = ref([])
const history = ref([])
const fileInput = ref(null)
const traceBox = ref(null)

// ===== Trace =====
function trace(text, cls = 't-info') {
  traceLines.value.push({ text, cls })
  nextTick(() => { if (traceBox.value) traceBox.value.scrollTop = traceBox.value.scrollHeight })
}

// ===== 生成（流式：实时显示过程） =====
async function generate() {
  const nl = form.nl.trim()
  let task
  if (nl) {
    task = nl
  } else {
    if (!form.city.trim()) { alert('请填写目的地'); return }
    task = `${form.days || 1}天${form.city}，预算${form.budget || 500}${form.interests ? '，喜欢' + form.interests : ''}`
  }

  generating.value = true
  traceLines.value = []
  resultHtml.value = ''
  canSave.value = false
  currentResult = null
  trace(`🧾 任务：${task}`)

  try {
    const resp = await fetch('/api/generate/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task }),
    })
    if (!resp.ok) throw new Error('请求失败')

    // 读取流：逐行解析 NDJSON 事件（项目2 的流式经验）
    const reader = resp.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })   // {stream:true} 防半个汉字
      const lines = buffer.split('\n')
      buffer = lines.pop()                                 // 最后一段可能不完整，留到下次
      for (const line of lines) {
        if (!line.trim()) continue
        handleEvent(JSON.parse(line))
      }
    }
  } catch (e) {
    trace(`❌ 错误：${e.message}`, 't-err')
    resultHtml.value = `<div class="empty" style="color:#dc2626">${e.message}</div>`
  } finally {
    generating.value = false
  }
}

// ===== 流式事件处理 =====
function handleEvent(event) {
  switch (event.type) {
    case 'constraints':
      trace(`📐 约束解析：${JSON.stringify(event.data)}`, 't-ok')
      break
    case 'plan':
      trace(`📋 计划：${event.data.join(' → ')}`, 't-ok')
      break
    case 'step':
      trace(`⚙️ 执行【${event.step}】：${String(event.data).slice(0, 60)}...`, 't-ok')
      break
    case 'review':
      if (event.data.passed) trace(`✅ 评审通过（第${event.round}轮）：${event.data.opinion}`, 't-ok')
      else trace(`❌ 评审未通过（第${event.round}轮）：${event.data.opinion}`, 't-err')
      break
    case 'retry':
      trace(`↩️ 打回重做（第${event.round}轮）：${event.opinion}`, 't-warn')
      break
    case 'blocked':
      trace(`🚫 ${event.data.opinion}`, 't-err')
      break
    case 'done':
      currentResult = event.data
      const final = event.data.results['写方案'] || ''
      if (event.data.review.passed) {
        resultHtml.value = marked.parse(final || '（无行程内容）')
        canSave.value = true
      } else {
        resultHtml.value = `<div class="empty" style="color:#dc2626">${event.data.review.opinion}</div>`
      }
      break
  }
}

// ===== 约束预览（和 parse.py 同逻辑） =====
function previewConstraints(task) {
  const days = (task.match(/(\d+)天/) || [])[1] || ''
  const budget = (task.match(/预算\s*(\d+)/) || [])[1] || ''
  let cleaned = task.replace(/(帮我|请|规划|制定|安排)/g, '')
  let city = (cleaned.match(/([\u4e00-\u9fa5]{2,4})\s*(?=\d+天)/) || [])[1] || ''
  if (!city) {
    cleaned = cleaned.replace(/\d+天/g, '').replace(/\d+晚/g, '')
    city = (cleaned.match(/(?:去|到|在|玩)([\u4e00-\u9fa5]{2,4})/) || [])[1] || ''
    if (!city) city = (cleaned.match(/([\u4e00-\u9fa5]{2,4})\s*[,，]\s*预算/) || [])[1] || ''
  }
  return { city, days, budget }
}

// ===== 上传攻略 =====
async function uploadGuide() {
  const file = fileInput.value.files[0]
  if (!file) { uploadMsg.value = '请先选择 txt 或 pdf 文件'; uploadErr.value = true; return }
  const formData = new FormData()
  formData.append('file', file)
  uploading.value = true
  uploadMsg.value = '上传中…（向量化约 10-30 秒）'
  uploadErr.value = false
  try {
    const resp = await fetch('/api/upload', { method: 'POST', body: formData })
    const data = await resp.json()
    if (!resp.ok) throw new Error(data.detail || '上传失败')
    uploadMsg.value = '✅ ' + data.message
    trace(`📚 攻略已入库：${data.message}`, 't-ok')
    loadGuides()
  } catch (e) {
    uploadMsg.value = '❌ ' + e.message
    uploadErr.value = true
  } finally {
    uploading.value = false
    fileInput.value.value = ''
  }
}

// ===== 攻略列表 =====
async function loadGuides() {
  const resp = await fetch('/api/guides')
  guides.value = await resp.json()
}

async function deleteGuide(name) {
  if (!confirm(`删除攻略「${name}」？`)) return
  const resp = await fetch(`/api/guides/${encodeURIComponent(name)}`, { method: 'DELETE' })
  const data = await resp.json()
  trace(`🗑️ ${data.message}`, 't-warn')
  loadGuides()
}

// ===== 保存历史 =====
async function saveTrip() {
  if (!currentResult) return
  const resp = await fetch('/api/save', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ task: currentResult.task, result: currentResult }),
  })
  const data = await resp.json()
  trace(`💾 已保存（ID ${data.id}）`, 't-ok')
  loadHistory()
}

// ===== 历史 =====
async function loadHistory() {
  const resp = await fetch('/api/history')
  history.value = await resp.json()
}

async function openHistory(id) {
  const resp = await fetch(`/api/history/${id}`)
  const data = await resp.json()
  currentResult = data.result
  traceLines.value = []
  trace(`🧾 历史任务：${data.task}`)
  trace(`📋 计划：${data.result.plan.join(' → ')}`, 't-ok')
  for (const [step, result] of Object.entries(data.result.results)) {
    trace(`⚙️ 【${step}】：${String(result).slice(0, 60)}...`, 't-ok')
  }
  trace(`✅ 评审：${data.result.review.opinion}`, 't-ok')
  resultHtml.value = marked.parse(data.result.final_answer || '（无行程内容）')
  canSave.value = false
}

async function delHistory(id) {
  await fetch(`/api/history/${id}`, { method: 'DELETE' })
  loadHistory()
}

// ===== 初始化 =====
onMounted(() => {
  loadGuides()
  loadHistory()
})
</script>

<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: "Microsoft YaHei", sans-serif; background: #f1f5f9; color: #1e293b; }
.header { background: #0f172a; color: #fff; padding: 16px 24px; display: flex; align-items: center; gap: 12px; }
.header h1 { font-size: 20px; }
.tag { background: #334155; padding: 4px 10px; border-radius: 12px; font-size: 12px; }
.layout { display: flex; gap: 16px; padding: 16px; max-width: 1400px; margin: 0 auto; }
.sidebar { width: 320px; flex-shrink: 0; display: flex; flex-direction: column; gap: 16px; }
.card { background: #fff; border-radius: 12px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }
.card h3 { font-size: 15px; margin-bottom: 12px; color: #0f172a; }
label { display: block; font-size: 13px; margin: 10px 0 4px; color: #475569; }
input, textarea { width: 100%; padding: 8px 10px; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 14px; font-family: inherit; }
textarea { height: 70px; resize: vertical; }
.file-input { font-size: 12px; margin-bottom: 8px; }
.btn { width: 100%; padding: 10px; border: none; border-radius: 8px; font-size: 14px; cursor: pointer; margin-top: 14px; background: #2563eb; color: #fff; font-weight: bold; }
.btn:hover { background: #1d4ed8; }
.btn:disabled { background: #94a3b8; cursor: not-allowed; }
.btn-gray { background: #475569; width: auto; margin-top: 0; padding: 6px 14px; }
.btn-gray:hover { background: #334155; }
.upload-msg { font-size: 12px; color: #475569; margin-top: 8px; }
.upload-msg.err { color: #dc2626; }
.guide-list, .history-list { max-height: 200px; overflow-y: auto; margin-top: 8px; }
.guide-item { display: flex; justify-content: space-between; align-items: center; padding: 8px; border: 1px solid #e2e8f0; border-radius: 8px; margin-bottom: 6px; font-size: 12px; }
.g-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; cursor: pointer; }
.g-chunks { color: #94a3b8; font-size: 11px; margin: 0 6px; }
.del-btn { border: none; background: #fee2e2; color: #b91c1c; border-radius: 6px; padding: 4px 8px; cursor: pointer; font-size: 12px; }
.empty-small { color: #94a3b8; text-align: center; padding: 12px; font-size: 13px; }
.main { flex: 1; display: flex; flex-direction: column; gap: 16px; min-width: 0; }
.trace { max-height: 240px; overflow-y: auto; background: #0f172a; color: #e2e8f0; border-radius: 8px; padding: 12px; font-size: 12px; font-family: Consolas, monospace; line-height: 1.8; }
.t-ok { color: #4ade80; }
.t-info { color: #93c5fd; }
.t-warn { color: #fbbf24; }
.t-err { color: #f87171; }
.result-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.result-body { min-height: 300px; }
.md { line-height: 1.8; font-size: 14px; }
.md h1, .md h2, .md h3 { margin: 16px 0 8px; }
.md table { border-collapse: collapse; width: 100%; margin: 8px 0; }
.md th, .md td { border: 1px solid #e2e8f0; padding: 6px 8px; font-size: 13px; }
.md th { background: #f8fafc; }
.md code { background: #f1f5f9; padding: 1px 5px; border-radius: 4px; }
.empty { color: #94a3b8; text-align: center; padding: 60px 0; }
</style>
