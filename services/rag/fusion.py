# rag/fusion.py —— RRF 融合（Reciprocal Rank Fusion，倒数排名融合）
# 作用：把两条检索路的"排名表"合成一张。只看名次，不看分数。
# 公式：每条路的第 r 名，得分 += 1/(60+r)。两路都排前面的，总分最高。
# 为什么不用"分数相加"：两路的分数单位不同（余弦相似度 vs BM25 词频），
#   直接相加=拿斤和两比；名次是统一的尺子，所以 RRF 只看名次。
# k=60 是论文里的常用常数，让排名靠前的收益递减但稳定。

def rrf_merge(ranked_lists, k=60):
    """输入：[[doc1,doc2,...], [doc1,doc2,...], ...] 多条路的降序排名
    输出：[(doc, 融合分), ...] 按融合分降序（融合分只在内部排序用，不回传给模型）"""
    scores = {}
    for ranked in ranked_lists:                       # 遍历每条路
        for rank, doc in enumerate(ranked):           # 遍历这条路里的每个文档（rank从0开始）
            scores[doc] = scores.get(doc, 0) + 1.0 / (k + rank + 1)  # 累加：名次越前分越高
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)  # 按融合分降序