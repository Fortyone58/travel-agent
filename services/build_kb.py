# build_kb.py —— 攻略入库（跑一次：guides/*.md → 切块 → 向量化 → 存入 chroma_db）
import glob
import os
import sys
# 脚本直接运行时，把项目根加入搜索路径（保证 from services.xxx import 可用）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.rag.chunk import chunk_text        # 切块（200字/50重叠，项目2 同款）
from services.rag.embed import embed_texts       # 向量化（百炼 text-embedding-v3）
from services.rag.store import add_chunks        # 入库（chroma_db 本地库）

def build():
    all_chunks = []
    all_ids = []
    for path in glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), "guides", "*.md")):          # 遍历所有攻略
        with open(path, encoding="utf-8") as f:
            text = f.read()
        chunks = chunk_text(text)                  # 切块
        name = os.path.basename(path)              # 文件名（id 前缀，统计/删除用）
        all_chunks.extend(chunks)
        all_ids.extend([f"{name}_{i}" for i in range(len(chunks))])
        print(f"  {path}: {len(chunks)} 块")

    # 分批向量化（百炼 embedding 单次上限 10 条——你踩过的坑）
    vecs = []
    for i in range(0, len(all_chunks), 10):
        vecs.extend(embed_texts(all_chunks[i:i + 10]))

    add_chunks(all_ids, all_chunks, vecs)              # 入库
    print(f"✅ 入库完成：共 {len(all_chunks)} 块")

if __name__ == "__main__":
    build()
