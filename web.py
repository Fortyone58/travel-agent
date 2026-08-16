# web.py —— 旅行助手网页版（FastAPI 后端）
# 模仿"智旅云图"的产品形态：表单输入 → 过程trace → 行程结果 → 保存历史 → 攻略上传
import sqlite3
import json
import os
import io
from datetime import datetime
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from main import run_task

app = FastAPI(title="旅行规划多Agent系统")

# 允许前端跨域访问（开发时前端由 LiveServer/静态打开）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ 历史保存（SQLite，标准库即可） ============
DB = "trips.db"

def init_db():
    conn = sqlite3.connect(DB)
    conn.execute("""CREATE TABLE IF NOT EXISTS trips (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task TEXT NOT NULL,
        result TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""")
    conn.commit()
    conn.close()

init_db()

# ============ 请求模型 ============
class GenerateRequest(BaseModel):
    task: str                 # 自然语言任务（如"3天2晚石家庄，预算1000，喜欢吃"）

class SaveRequest(BaseModel):
    task: str                 # 任务原文
    result: dict              # 完整结果（state）

# ============ 攻略上传 ============
def ingest_text(name: str, text: str) -> int:
    """攻略文本入库：切块 → 向量化（分批）→ 存入 chroma_db"""
    from rag.chunk import chunk_text        # 切块（200字/50重叠）
    from rag.embed import embed_texts       # 向量化（百炼）
    from rag.store import add_chunks        # 入库
    chunks = chunk_text(text)
    vecs = []
    for i in range(0, len(chunks), 10):     # 分批（百炼上限 10 条）
        vecs.extend(embed_texts(chunks[i:i + 10]))
    ids = [f"{name}_{i}" for i in range(len(chunks))]   # 文件名前缀防 id 冲突
    add_chunks(ids, chunks, vecs)
    return len(chunks)

@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    """上传攻略（txt/pdf）→ 提取文本 → 入库"""
    filename = file.filename or "攻略"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    content = await file.read()             # 读取上传的文件内容

    # 按类型提取文本
    if ext == "txt":
        text = content.decode("utf-8", errors="ignore")
    elif ext == "pdf":
        from pypdf import PdfReader         # PDF 解析库
        reader = PdfReader(io.BytesIO(content))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    else:
        raise HTTPException(status_code=400, detail="仅支持 txt / pdf 文件")

    if not text.strip():
        raise HTTPException(status_code=400, detail="未能从文件中提取到文本")

    # 保存原件到 guides/（保留原始文件）
    os.makedirs("guides", exist_ok=True)
    with open(os.path.join("guides", filename), "wb") as f:
        f.write(content)

    # 入库（切块→向量化→chroma_db）
    n = ingest_text(filename, text)
    return {"message": f"{filename} 已入库 {n} 块，可立即在行程中检索"}

# ============ 页面 ============
@app.get("/", response_class=FileResponse)
def index():
    return FileResponse("index.html")

# ============ 核心接口：生成行程 ============
@app.post("/api/generate")
def generate(req: GenerateRequest):
    """接收任务 → 跑三角色流水线 → 返回完整结果（含过程）"""
    state = run_task(req.task)
    return {
        "task": state["task"],
        "constraints": state["constraints"],
        "plan": state["plan"],
        "review": state["review"],
        "round": state["round"],
        "results": state["results"],        # 每步结果（含最终行程"写方案"）
        "final_answer": state["results"].get("写方案", ""),   # 最终行程（Markdown）
    }

# ============ 历史管理 ============
@app.post("/api/save")
def save(req: SaveRequest):
    """保存一次行程到历史"""
    conn = sqlite3.connect(DB)
    cur = conn.execute(
        "INSERT INTO trips (task, result, created_at) VALUES (?, ?, ?)",
        (req.task, json.dumps(req.result, ensure_ascii=False),
         datetime.now().strftime("%Y-%m-%d %H:%M")),
    )
    conn.commit()
    tid = cur.lastrowid
    conn.close()
    return {"id": tid, "message": "已保存"}

@app.get("/api/history")
def history():
    """历史列表（只返回概要）"""
    conn = sqlite3.connect(DB)
    rows = conn.execute("SELECT id, task, created_at FROM trips ORDER BY id DESC").fetchall()
    conn.close()
    return [{"id": r[0], "task": r[1], "created_at": r[2]} for r in rows]

@app.get("/api/history/{tid}")
def history_detail(tid: int):
    """单个历史详情（完整结果）"""
    conn = sqlite3.connect(DB)
    row = conn.execute("SELECT task, result FROM trips WHERE id = ?", (tid,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="记录不存在")
    return {"task": row[0], "result": json.loads(row[1])}

@app.delete("/api/history/{tid}")
def history_delete(tid: int):
    """删除一条历史"""
    conn = sqlite3.connect(DB)
    conn.execute("DELETE FROM trips WHERE id = ?", (tid,))
    conn.commit()
    conn.close()
    return {"message": "已删除"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
