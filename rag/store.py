# rag/store.py —— 向量库（Chroma）
# 作用：① 把"向量+原文"存进本地向量库（类似 MySQL 的 INSERT）
#       ② 给"问题向量"，找出最相关的 Top-K 块（类似 SELECT 按相似度排序）

import chromadb
# 数据持久化到本地文件夹 chroma_db/（嵌入式模式，不用起服务）
client = chromadb.PersistentClient(path="./chroma_db")
# collection 类似 MySQL 的"表"
collection = client.get_or_create_collection(name="docs")
def add_chunks(ids, texts, vecs):
    """入库：ids=编号列表，texts=原文列表，vecs=向量列表，三样一一对应"""
    collection.add(
        ids=ids,
        documents=texts,
        embeddings=vecs,
    )

def query_topk(question_vec, k=3):
    """检索：给问题向量，返回最相关的 k 个块原文"""
    results = collection.query(
        query_embeddings=[question_vec],
        n_results=k,
    )
    return results["documents"][0]   # documents 是嵌套列表，[0] 取第一个查询的结果

def get_all_docs():
    """取出库里全部原文（BM25 检索需要全量语料做语料库）"""
    return collection.get(include=["documents"])["documents"]   #此代码为三重混合检索新加的

# if __name__ == "__main__":
#     # 自测：存 2 句假数据，用"假的相似向量"查，验证检索流程能跑通
#     add_chunks(
#         ids=["t1", "t2"],
#         texts=["公司请假需要提前一天申请", "公司报销需要保留发票"],
#         vecs=[[0.1] * 1024, [0.9] * 1024],   # 假向量，先只测流程
#     )
#     found = query_topk([0.1] * 1024, k=1)    # 和 t1 的向量一样 → 应该命中 t1
#     print("查到的块：", found)
#此注释代码为注释代码 （非项目必要 学习用）