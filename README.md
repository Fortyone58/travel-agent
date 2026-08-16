# 🧳 旅行规划多 Agent 系统（规划-执行-评审）

> 融合大模型与真实数据工具（天气/地理编码）的手搓多 Agent 旅行规划系统。
> 更新记录见 [CHANGELOG.md](./CHANGELOG.md)

用户输入目的地、天数、预算和兴趣后，系统自动生成结构化旅行方案：行程总览、每日计划、预算拆分、备选方案——全过程由 **"规划-执行-评审"三个 Agent 协作完成**，评审不通过自动打回重做，高风险请求（付款/预订）代码级拦截。

---

## ✨ 项目亮点

- 🧠 **多 Agent 架构（规划-执行-评审）**：不是单 Agent 一条链——规划者拆步骤、执行者调真实工具、评审者强制把关，三个角色各司其职，流程由代码控制
- 🔄 **评审打回机制**：评审不通过自动打回重做（最多 3 轮）——实测：行程未应对"下雨"需求，第 1 轮被打回，第 2 轮修正通过
- 🛡️ **代码兜底（可靠性设计）**：
  - 约束用正则解析——预算 1000 永远不会被模型改成 800（实测对比）
  - "付款/银行卡/身份证"等高风险请求代码级拦截（human-in-the-loop），不靠模型自觉
- 🌦️ **真实数据工具**：Open-Meteo 天气 + Nominatim 地理编码（免费 API，零成本）
- 📚 **攻略知识库检索（三重混合 RAG）**：预置城市攻略（杭州/石家庄），执行者生成行程前先检索攻略——景点/价格有真实依据，不靠模型编（向量+BM25+RRF+rerank）
- 🖥️ **网页交互**：Vue 3 前端——表单/自然语言输入 → **流式 Trace 实时展示**（生成过程可见）→ Markdown 行程渲染 → SQLite 历史保存
- ⚡ **流式输出**：SSE 逐事件推送（约束→计划→每步执行→评审），前端实时渲染，多 Agent 协作过程全程可见
- 🧪 **验收体系**：5 类 case（常规/预算约束/偏好约束/天气变化/安全边界），全部通过

---

## 🏗️ 技术架构

### 技术栈

| 层 | 技术 |
|---|---|
| 后端 | FastAPI + SQLite（历史保存）+ SSE 流式输出 |
| LLM | OpenAI 兼容 API（OpenCode Go，mimo-v2.5） |
| 框架（阶段 1） | LangChain `create_agent` + LangGraph `SqliteSaver`（会话记忆） |
| **手搓（阶段 2）** | **纯 Python 三角色（规划-执行-评审），0 框架** |
| 外部服务 | Open-Meteo（天气）、Nominatim（地理编码）——均免费无 key |
| 前端 | Vue 3 + Vite（组件化） |

### 核心架构分层

```
用户输入："3天2晚石家庄，预算1000，喜欢吃"
    ↓
parse.py —— 代码解析约束（正则：城市/天数/预算，数字不经过模型 = 0 幻觉）
    ↓
planner（规划者人格）—— 解析兴趣 + 拆步骤（查天气/查地点/排行程/算预算/写方案）
    ↓
executor（执行者人格）—— 按步骤干活：
    ├─ 查天气/查地点 → 真实 API 工具（Open-Meteo / Nominatim）
    ├─ 排行程/算预算/写方案 → 攻略知识库检索（rag/ 三重混合）+ 模型生成
    ↓
reviewer（评审者人格）—— ①代码安全拦截（付款/银行卡→直接终止）②模型质量评审
    ↓
不通过 → 打回执行者重做（最多 3 轮）→ 通过 → 输出行程方案（Markdown）
```

### 设计说明（每个技术点"为什么"）

1. **为什么约束用代码解析（正则）**：实测模型会把预算 1000 改成 800、把 2 天改成 3 天——数字必须不过模型的手，用正则提取 100% 准确
2. **为什么评审要打回重做**：单 Agent 靠模型自觉（可能偷懒），评审者是独立强制环节——不合格必须重做，质量有保障
3. **为什么安全要代码拦截**：付款/预订/敏感凭据是高危动作，不靠模型自觉——检测到关键词直接终审终止（human-in-the-loop）
4. **为什么先框架后手搓**：阶段 1 用 LangChain `create_agent` 快速跑通验证功能；阶段 2 手搓三角色复现其内部（节点/边/状态 = LangGraph 思想）——理解框架封装了什么，每行代码都懂

---

## 🔍 RAG 检索流程（三重混合）

```
用户问题："杭州 景点 美食 攻略"
    ↓
① 向量检索（语义）   问题 → 百炼 embedding → Chroma 查 top10     ← 懂同义句
② BM25 检索（关键词）  问题分词(bigram) → 全量语料打分 top10      ← 专名精确
③ RRF 融合           两路排名表合成一张（只看名次，不看分数）
④ 候选 top10 → rerank 精排（百炼 gte-rerank-v2）→ top3
    ↓
攻略资料（top3 片段）→ 拼进执行者 prompt → 模型基于真实攻略生成
```

**攻略入库流程**：
```
上传（网页 txt/pdf）或预置（guides/*.md）
    ↓
chunk.py 切块（200字/50重叠）→ embed.py 向量化（分批≤10）→ chroma_db
```

**跨城市隔离**：块 id 带文件名前缀（如 `成都.txt_0`），删除/统计按前缀精确操作。

---

## 🗄️ 数据存储与缓存分工

| 存储 | 类型 | 存什么 | 生命周期 |
|---|---|---|---|
| `chroma_db/` | 向量库（Chroma 嵌入式） | 攻略切块 + 向量 | 持久（重新 build_kb 可重建） |
| `trips.db` | SQLite | 历史行程（task + 完整结果） | 持久 |
| `checkpoints.sqlite` | SQLite（LangGraph Checkpointer） | 会话记忆（阶段 1 用） | 持久 |
| `guides/` | 文件 | 攻略源文档（上传/预置） | 持久（可删除） |
| 前端状态 | Vue 响应式内存 | 当前表单/结果/trace | 会话内（刷新即失） |

**分工原则**：向量库管"检索"（攻略语义），SQLite 管"业务数据"（历史），文件管"源文档"（可读可删），内存管"临时交互状态"。

---

## 🔄 系统数据流

```
【行程生成】
网页表单/自然语言 → POST /api/generate
  → parse.py 约束解析（正则）
  → planner（模型拆步骤）
  → executor（真实工具 + RAG 攻略检索 + 模型生成）
  → reviewer（代码拦截 + 模型评审）→ 不合格打回（≤3轮）
  → 返回完整 state → 前端渲染（Trace + Markdown 行程）

【保存历史】
点击保存 → POST /api/save → trips.db → 刷新历史列表

【攻略管理】
上传 → POST /api/upload → guides/ + chroma_db → 立即可检索
删除 → DELETE /api/guides/{name} → 删 chroma 块 + 删文件
列表 → GET /api/guides → 文件清单 + 块数
```

---

## 🏛️ 核心架构分层

```
┌─────────────────────────────────────────┐
│ 前端层（Vue 3 + Vite）                    │
│   表单 / Trace 展示 / 结果渲染 / 攻略管理   │
├─────────────────────────────────────────┤
│ 接口层（FastAPI web.py）                  │
│   /api/generate /api/save /api/history   │
│   /api/upload /api/guides                │
├─────────────────────────────────────────┤
│ Agent 层（手搓三角色 roles.py）            │
│   planner → executor → reviewer → 打回    │
├─────────────────────────────────────────┤
│ 数据层                                    │
│   parse（约束）/ state（状态）/ tools（工具）│
│   rag/（三重检索）/ chroma_db / trips.db   │
├─────────────────────────────────────────┤
│ 外部服务层                                │
│   OpenCode Go（LLM）· 百炼（embed/rerank）│
│   Open-Meteo（天气）· Nominatim（地理）    │
└─────────────────────────────────────────┘
```

---

## 📁 关键文件职责

| 文件 | 职责 | 关键点 |
|---|---|---|
| `main.py` | 命令行入口（薄壳） | 实际逻辑在 core/pipeline |
| `core/pipeline.py` | 主流程编排（run_task + 流式生成器） | while 循环 = 图执行器 |
| `core/roles.py` | 三角色 + call_model + query_kb | 多 Agent 本体（三种人格） |
| `core/parse.py` | 约束解析（正则） | 数字 0 幻觉的关键 |
| `core/state.py` | 状态结构（new_state） | 三角色共享账本 |
| `services/tools.py` | 天气/地点/计算工具 | @tool，真实 API |
| `services/build_kb.py` | 预置攻略入库 | 跑一次 |
| `services/rag/` | 三重混合检索零件 | chunk/embed/store/bm25/fusion/rerank |
| `services/guides/` | 攻略源文档 | 可上传可删除 |
| `app/web.py` | FastAPI 接口（9 个） | 生成/历史/攻略管理/流式 |
| `app/frontend/` | Vue 3 前端 | Vite + 组件化 |
| `start.ps1` | 一键启动（后端+前端+浏览器） | 开发体验 |

---

## 🚀 快速开始

```powershell
# ① 环境
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install openai python-dotenv langchain langchain-openai langgraph-checkpoint-sqlite fastapi uvicorn requests chromadb rank-bm25 pypdf python-multipart

# ② 配置 .env（key 从环境变量读，不写进代码；DASHSCOPE_API_KEY 用于攻略向量化/重排）
OPENCODE_GO_KEY=sk-你的key
DASHSCOPE_API_KEY=sk-你的百炼key

# ③ 攻略入库（跑一次：guides/*.md → 切块 → 向量化 → chroma_db）
$env:PYTHONPATH=""
.\.venv\Scripts\python.exe build_kb.py

# ④ 启动后端（FastAPI，端口 8000）
.\.venv\Scripts\python.exe -m uvicorn web:app --port 8000

# ⑤ 启动前端（Vue 3 + Vite，端口 5173，API 自动代理到 8000）
cd app/frontend
npm install
npm run dev
# 浏览器打开 http://localhost:5173/
```

---

## 🧪 验收结果（5 类 case）

| Case | 输入 | 结果 |
|---|---|---|
| 常规规划 | 2天1晚杭州，预算1500，喜欢博物馆 | ✅ 通过（第 1 轮） |
| 预算约束 | 3天成都，预算500 | ✅ 通过（预算严格 500） |
| 偏好约束 | 北京2天，预算2000，亲子游 | ✅ 通过 |
| 天气变化 | 明天去西安，下雨怎么办，预算800 | ✅ 打回重做后通过（第 2 轮） |
| 安全边界 | 帮我订酒店付款 | ✅ 代码拦截（轮次 1 终止） |

---

## 📝 学习过程（为什么有阶段 1 和阶段 2）

```
阶段 1：LangChain create_agent 快速跑通（单 Agent，验证功能）
   ↓ 发现：模型不遵守约束（1000→800）、无评审、无安全兜底
阶段 2：手搓三角色（规划-执行-评审）+ 代码兜底
   ↓ 结果：约束 0 幻觉、评审打回、安全拦截——每行都懂
```

这个演进过程本身 = 面试故事：**先用框架跑通，再手搓理解内部，最后用代码补框架的短板**。

---

## ⚠️ 数据边界

- 天气/地点数据来自 Open-Meteo / Nominatim 免费 API，实时获取
- 门票、酒店价格、营业状态为模型估算，**不代表实时核验**（行程中已注明"以实际为准"）
- 系统不自动付款、不保存敏感凭据（human-in-the-loop 设计）
