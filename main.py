# main.py —— 阶段 2 完整版：规划→执行→评审→打回循环
from state import new_state
from parse import parse_constraints
from roles import planner, executor, reviewer

MAX_ROUND = 3                              # 最多打回 3 轮（防死循环 = demo2 的 range(5)）

def run_task(task: str) -> dict:
    """跑一个完整任务：规划→执行→评审→打回"""
    state = new_state(task)                                   # ① 造账本
    state["constraints"] = parse_constraints(state["task"])   # ② 代码解析约束

    state = planner(state)                                    # ③ 规划者拆步骤
    state = executor(state)                                   # ④ 执行者干活
    state = reviewer(state)                                   # ⑤ 评审者检查

    while not state["review"]["passed"] and state["round"] < MAX_ROUND:
        # 安全拦截 = 终审，直接停（不打回——重做多少次都一样危险）
        if state["review"]["opinion"].startswith("安全拦截"):
            print("🚫 高风险请求，终止处理")
            break
        # ⑥ 打回：评审不通过 → 带着意见重做（= ReAct 循环的回绕）
        print(f"↩️ 第{state['round']}轮未通过，打回重做：{state['review']['opinion'][:30]}...")
        state["round"] += 1
        state = executor(state)                               # 执行者重做（可带意见）
        state = reviewer(state)                               # 再评审

    return state

def run_task_stream(task: str):
    """流式版：逐步 yield 事件（前端实时显示过程）
    事件类型：constraints / plan / step / review / retry / blocked / done"""
    state = new_state(task)
    state["constraints"] = parse_constraints(state["task"])
    yield {"type": "constraints", "data": state["constraints"]}

    state = planner(state)
    yield {"type": "plan", "data": state["plan"]}

    state = executor(state)
    for step, result in state["results"].items():
        yield {"type": "step", "step": step, "data": str(result)[:100]}

    state = reviewer(state)
    yield {"type": "review", "data": state["review"], "round": state["round"]}

    while not state["review"]["passed"] and state["round"] < MAX_ROUND:
        if state["review"]["opinion"].startswith("安全拦截"):
            yield {"type": "blocked", "data": state["review"]}
            break
        state["round"] += 1
        yield {"type": "retry", "round": state["round"],
               "opinion": state["review"]["opinion"][:60]}
        state = executor(state)
        for step, result in state["results"].items():
            yield {"type": "step", "step": step, "data": str(result)[:100]}
        state = reviewer(state)
        yield {"type": "review", "data": state["review"], "round": state["round"]}

    yield {"type": "done", "data": state}

if __name__ == "__main__":
    state = run_task("3天2晚石家庄，预算1000，喜欢吃")
    print("约束:", state["constraints"])
    print("评审:", state["review"])
    print("轮次:", state["round"])
    for step, result in state["results"].items():
        print(f"\n【{step}】\n{result[:100]}")