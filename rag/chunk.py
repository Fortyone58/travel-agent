# rag/chunk.py —— 分块器
# 作用：把一篇长文档切成小块。
# 为什么：向量化是按"块"来的——一块一个向量。
#         整篇文档一个向量的话，检索只能定位到"整篇"；
#         切小了才能定位到"哪一段"，回答才准。

def chunk_text(text, size=200, overlap=50):
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = end - overlap
    return chunks
# if __name__ == "__main__":
#     with open("docs/公司制度.txt", encoding="utf-8") as f:
#         text = f.read()
#     blocks = chunk_text(text)
#     print(f"文档共{len(text)}字，切成了{len(blocks)}块，每块前50字与下一块后50字有重叠。")
#     for i ,b in enumerate(blocks):
#         print(f"第{i+1}块：{b[:50]}...{b[-50:]}")
#         print(b)
#此注释代码为注释代码 （非项目必要 学习用）