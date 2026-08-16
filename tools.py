# tools.py —— 旅行助手工具（@tool 版）
from langchain_core.tools import tool   # 导入 @tool 装饰器（框架自动提取工具描述）
import requests                         # 抓网页/API 的库（你 demo2 用过）
import json                             # JSON 解析库

@tool                                   # 装饰器：把下面函数变成"工具"（自动生成菜单）
def get_weather(city: str) -> str:
    """查指定城市当前天气：先地理编码拿坐标，再查 Open-Meteo 免费天气
    Args:
        city: 城市名，如"杭州"
    """
    # ① 城市 → 坐标（Nominatim 免费地理编码）
    geo = requests.get(
        f"https://nominatim.openstreetmap.org/search?q={city}&format=json&limit=1",
        headers={"User-Agent": "travel-agent/1.0"},   # Nominatim 要求带 UA（usage policy）
        timeout=10,
    )
    data = geo.json()                   # 解析返回的 JSON（geo.json() = json.loads 的 requests 版）
    if not data:                        # 没找到城市
        return f"未找到城市: {city}"
    lat, lon = data[0]["lat"], data[0]["lon"]   # 取第一个结果的经纬度

    # ② 坐标 → 天气（Open-Meteo 免费天气 API，无 key）
    wx = requests.get(
        f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true",
        timeout=10,
    )
    cur = wx.json()["current_weather"]  # 取出当前天气块
    # ③ 返回人话（@tool 规范：返回值是模型能读懂的文字）
    return f"{city}当前天气：温度{cur['temperature']}℃，风速{cur['windspeed']}km/h，天气代码{cur['weathercode']}"

@tool
def search_places(city: str) -> str:
    """查城市地理信息（坐标+显示名），用于了解目的地位置
    Args:
        city: 城市名，如"杭州"
    """
    geo = requests.get(
        f"https://nominatim.openstreetmap.org/search?q={city}&format=json&limit=3",
        headers={"User-Agent": "travel-agent/1.0"},
        timeout=10,
    )
    data = geo.json()
    if not data:
        return f"未找到城市: {city}"
    lines = [f"{item['display_name']}（坐标 {item['lat']},{item['lon']}）" for item in data]
    return "\n".join(lines)             # 多行结果拼接（\n 换行）

@tool
def calc(expr: str) -> str:
    """计算数学表达式，用于预算计算
    Args:
        expr: 数学表达式，如"500+200*3"
    """
    import re                            # 正则库（安全检查用）
    if not re.fullmatch(r"[0-9+\-*/().\s]+", expr):   # 只允许数字和运算符（demo2 同款安检）
        return "错误: 表达式含非法字符"
    try:
        return str(eval(expr))           # 计算（eval 把字符串当表达式算）
    except Exception as e:
        return f"错误: {e}"