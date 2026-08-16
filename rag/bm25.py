# rag/bm25.py —— 关键词检索（BM25）
# 作用：三重检索的"路2"——不看语义，看"词撞没撞上"。
#   路1 向量检索擅长同义句（"报销要发票"≈"报销需要保留发票"），
#   但专名（"小达"）在向量里会被稀释、排名靠后；
#   BM25 反过来：专名精确命中极强，两条路正好互补。
# 类比：向量=阅读理解，BM25=Ctrl+F 加权版。
# 实现：rank_bm25 包（已装好）。中文分词用"相邻两字"（bigram），零额外依赖。

from rank_bm25 import BM25Okapi

def tokenize(text):
    """把中文切成"相邻两字"：'小达负责' → ['小达','达负','负责']
    为什么不用 jieba 分词：专名（小达）可能被切碎成'小'+'达'，
    反而丢命中；两字一组保证专名一定完整出现。
    BM25 只能处理"词列表"，所以所有文本进 BM25 前都要过这道工序。"""
    text = text.replace("\n", "").replace(" ", "")   # 去换行去空格，避免切出无意义的两字
    if len(text) <= 1:
        return [text] if text else []                # 1个字直接返回；空文本返回空列表
    return [text[i:i + 2] for i in range(len(text) - 1)]  # 窗口滑动：每两个相邻字一组

def top_k(query, corpus, k=10):
    """输入：问题 + 全部块原文列表（corpus）
    输出：最相关的 k 块原文（按相关度降序）——和 store.query_topk 返回值同构
    注意：corpus 不自己存，每次从 Chroma 全量取（store.get_all_docs()），
    保证和向量库永远同一份数据，新上传的文档自动被检索到。"""
    q_tokens = tokenize(query)                        # 问题也切词
    if not q_tokens or not corpus:                    # 空问题/空库直接返回，防报错
        return []
    # 过滤空文档（切完没词），但保留原下标，避免和 corpus 错位
    pairs = [(i, tokenize(c)) for i, c in enumerate(corpus)]
    pairs = [(i, t) for i, t in pairs if t]
    if not pairs:
        return []
    bm25 = BM25Okapi([t for _, t in pairs])           # 建索引（语料小，毫秒级，每次现建）
    scores = bm25.get_scores(q_tokens)                # 每块一个分数，和 pairs 对齐
    ranked = sorted(range(len(pairs)), key=lambda i: scores[i], reverse=True)  # 分数降序的名次
    return [corpus[pairs[i][0]] for i in ranked[:k]]  # 按名次取原文，截前 k 块