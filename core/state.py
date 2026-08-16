# state.py —— 任务状态结构（多 Agent 共享的工作台）
def new_state(task: str) -> dict:
    """创建初始任务状态（每次调用造一本新账本）"""
    return {
        "task": task,                          # 任务原文（用户说的）
        "constraints": {                       # 约束（代码解析的，0 幻觉）
            "city": "",                        # 城市
            "days": 0,                         # 天数
            "budget": 0,                       # 预算（数字！评审者要比较）
            "interests": [],                   # 兴趣（列表）
        },
        "plan": [],                            # 规划者的步骤列表
        "results": {},                         # 执行者的结果（步骤→结果）
        "review": {"passed": False, "opinion": ""},   # 评审结论
        "round": 1,                            # 轮次（防死循环）
    }