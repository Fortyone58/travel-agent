# parse.py —— 代码解析约束（0 幻觉：数字不经过模型）
import re

def parse_constraints(task: str) -> dict:
    """从任务文字里用正则提取约束（城市/天数/预算）"""
    days_match = re.search(r"(\d+)天", task)          # 天数："2天"里的数字
    days = int(days_match.group(1)) if days_match else 0

    budget_match = re.search(r"预算\s*(\d+)", task)   # 预算："预算1000"或"预算 1000"
    budget = int(budget_match.group(1)) if budget_match else 0

    city = parse_city(task)                            # 城市（独立函数，多个模式试）
    return {"city": city, "days": days, "budget": budget, "interests": []}

def parse_city(task: str) -> str:
    """提取城市名：先试最可靠模式，再清理干扰，再试其他模式"""
    # ① 去掉引导词（防止"规划"被当成城市）
    cleaned = re.sub(r"(帮我|请|规划|制定|安排)", "", task)

    # ② 最可靠模式先试：X 后面跟"数字天"（杭州2天 / 成都 5天）
    m = re.search(r"([\u4e00-\u9fa5]{2,4})\s*(?=\d+天)", cleaned)
    if m:
        return m.group(1)

    # ③ 到这里说明"数字天"模式没命中 → 清掉"3天""2晚"（防止"天""晚"混进城市）
    cleaned = re.sub(r"\d+天", "", cleaned)
    cleaned = re.sub(r"\d+晚", "", cleaned)

    # ④ 其他模式逐个试（可靠性排序：明确的介词标记"去/到"优先于宽泛的"X，预算"）
    patterns = [
        r"(?:去|到|在|玩)([\u4e00-\u9fa5]{2,4})",    # 去西安（介词标记最可靠，放最前）
        r"([\u4e00-\u9fa5]{2,4})\s*[,，]\s*预算",    # 石家庄，预算（宽泛，靠后）
        r"([\u4e00-\u9fa5]{2,4})(?:旅|游)",          # 杭州旅
    ]
    for p in patterns:
        m = re.search(p, cleaned)
        if m:
            return m.group(1)
    return ""