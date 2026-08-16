# rag/rerank.py —— 重排器（百炼 gte-rerank-v2）
# 作用：三重检索的"路3"——对融合后的候选块逐个精算"和问题多相关"，取最准的前几名。
# 为什么需要：向量/BM25 是"快而糙"的粗筛（一眼扫过），重排是"慢而准"的精排（逐字比对）。
#   粗筛看整体相似，精排看逐词关联，更准但只能处理少量候选，所以放最后。
# 类比：HR 初筛简历（粗筛）→ 面试官逐份精读（精排）。
# 注意：这是 DashScope 原生接口（不是 OpenAI 兼容），所以用 requests 直连。

import os
import requests

RERANK_URL = "https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank"

def rerank(query, docs, top_n=3):
    """输入：问题 + 候选块列表（最多几十块）
    输出：精排后最相关的 top_n 块原文"""
    resp = requests.post(
        RERANK_URL,
        headers={"Authorization": f"Bearer {os.getenv('DASHSCOPE_API_KEY')}"},
        json={
            "model": "gte-rerank-v2",                # 百炼重排模型（gte-rerank 旧名已下线）
            "input": {"query": query, "documents": docs},
            "parameters": {"top_n": top_n, "return_documents": False},
        },
        timeout=30,
    )
    resp.raise_for_status()                          # 网络/接口出错直接抛异常，方便排查
    results = resp.json()["output"]["results"]       # 按相关分降序，每项带原列表下标
    return [docs[item["index"]] for item in results]  # 按下标还原成原文