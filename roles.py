# roles.py —— 阶段 2：手搓三角色（同一个 client，三种人格）
from dotenv import load_dotenv
import os
import json
from openai import OpenAI
from tools import get_weather, search_places, calc   # 导入工具（@tool 对象）

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENCODE_GO_KEY"),
    base_url="https://opencode.ai/zen/go/v1",
)

def call_model(system_prompt: str, user_content: str) -> str:
    """通用：调一次模型，返回回复文字"""
    resp = client.chat.completions.create(
        model="mimo-v2.5",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        timeout=30,          # 防卡死（你学过的坑）
    )
    return resp.choices[0].message.content

def planner(state: dict) -> dict:
    """规划者：模型解析兴趣 + 拆步骤（数字不碰，已在 parse.py 定死）"""
    system_prompt = """你是旅行规划者。
用户已给出城市、天数、预算（由系统解析，你不要改这些数字）。
你的任务：
1. 从任务文字里提取兴趣偏好（如美食、博物馆、自然风光），输出 JSON 数组
2. 把规划任务拆成步骤，步骤必须使用以下【固定名称】，不要添加任何其他文字：
   "查天气"、"查地点"、"排行程"、"算预算"、"写方案"
   （这 5 个名称按顺序使用，一个都不能少）

严格按 JSON 输出，不要输出其他文字：
{"interests": ["兴趣1", "兴趣2"], "plan": ["查天气", "查地点", "排行程", "算预算", "写方案"]}"""

    user_content = f"任务：{state['task']}\n已解析约束：{state['constraints']}"
    reply = call_model(system_prompt, user_content)
    data = json.loads(reply)                          # 解析 JSON
    state["constraints"]["interests"] = data["interests"]   # 兴趣填进 state
    state["plan"] = data["plan"]                             # 步骤填进 state
    return state

def executor(state: dict) -> dict:
    """执行者：按步骤干活（代码分发工具 + 模型生成内容）"""
    city = state["constraints"]["city"]              # 城市（代码定的，不会错）
    for step in state["plan"]:                       # 遍历每个步骤
        if "天气" in step:                            # 含"天气" → 调天气工具
            state["results"][step] = get_weather.invoke(city)     # .invoke()！不是直接调用
        elif "地点" in step or "景点" in step:        # 含"地点/景点" → 调地点工具
            state["results"][step] = search_places.invoke(city)   # .invoke()！
        else:                                        # 其他（排行程/算预算/写方案）→ 模型生成
            sys_prompt = """你是旅行执行者。严格按步骤和约束执行，输出详细结果。
约束：{constraints}"""
            state["results"][step] = call_model(
                sys_prompt.format(constraints=state["constraints"]),
                f"步骤：{step}")
    return state

def reviewer(state: dict) -> dict:
    """评审者：代码安全拦截 + 模型质量评审（双保险）"""
    # ① 代码安全拦截：只检查【用户输入】（危险请求来自用户，模型生成的建议不算）
    all_text = state["task"]                       # ← 只检查 task，不检查 results！
    danger_words = ["付款", "银行卡", "身份证", "转账", "密码"]   # ← 去掉"预订"（太宽泛）
    for word in danger_words:
        if word in all_text:
            state["review"] = {"passed": False,
                               "opinion": f"安全拦截：检测到'{word}'（高风险动作必须人工确认）"}
            return state

    # ② 模型评审（不变）...

    # ② 模型评审（需要智能的用模型）：检查预算/行程合理性
    sys_prompt = """你是旅行评审者。检查以下旅行计划：
1. 预算是否超过用户给出的预算（超出则 passed=false）
2. 行程是否合理（路线/时间安排）
3. 是否满足用户兴趣
只输出 JSON：{"passed": true/false, "opinion": "简短评审意见"}"""

    user_content = (f"任务：{state['task']}\n"
                    f"约束：{state['constraints']}\n"
                    f"计划：{state['plan']}\n"
                    f"结果：{state['results']}")
    reply = call_model(sys_prompt, user_content)
    data = json.loads(reply)                          # 解析 JSON
    state["review"] = {"passed": data["passed"], "opinion": data["opinion"]}
    return state