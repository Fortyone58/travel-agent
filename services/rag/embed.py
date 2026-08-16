# rag/embed.py —— 向量化
# 作用：把文本变成一串数字（向量），调百炼的 embedding API。
# 和 v1 的聊天 API 是同一个 client，只是方法从 chat.completions 换成 embeddings。

import os
from openai import OpenAI
client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),   # 环境变量，和 v1 同一个 key
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)
def embed_texts(texts):
    """输入：文本列表 ["第一句","第二句",...]
       输出：向量列表 [[0.1,0.2,...],[...],...] 每条文本一个向量"""
    resp = client.embeddings.create(
        model="text-embedding-v3",   # 百炼的向量模型
        input=texts,                 # 一次可以传多条
    )
    return [item.embedding for item in resp.data]
# if __name__ == "__main__":
#     vecs = embed_texts(["你好", "世界"])
#     print(f"2条文本 → 2个向量，每个 {len(vecs[0])} 维")
#     print(f"第一条前10个数字：{vecs[0][:10]}")
#此注释代码为注释代码 （非项目必要 学习用）