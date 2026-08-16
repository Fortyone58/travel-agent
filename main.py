# main.py —— 命令行入口（薄壳，实际逻辑在 core/pipeline.py）
# 用法：.\.venv\Scripts\python.exe main.py
from core.pipeline import run_task

if __name__ == "__main__":
    import sys
    task = sys.argv[1] if len(sys.argv) > 1 else "3天2晚石家庄，预算1000，喜欢吃"
    state = run_task(task)
    print("约束:", state["constraints"])
    print("评审:", state["review"])
    print("轮次:", state["round"])
    for step, result in state["results"].items():
        print(f"\n【{step}】\n{result[:100]}")
