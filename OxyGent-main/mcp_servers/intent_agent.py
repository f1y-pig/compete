# mcp_servers/intent_agent.py
from mcp.server.fastmcp import FastMCP
from pydantic import Field

mcp = FastMCP()

# 每个 Agent 对应的关键词或意图
agent_keywords = {
    "multi_format_agent": ["文件", "pdf", "excel", "ppt", "image", "视频", "音频", "mp3", "mp4", "文档", "表格",
                           "幻灯片"],
    "time_agent": ["时间", "日期", "现在", "几点", "今天", "明天", "星期", "月份", "年份", "当前时间"],
    "delivery_agent": ["订单", "下单", "查询订单", "发货", "快递", "配送", "物流", "运输", "派送", "收货地址"],
    "inventory_agent": ["库存", "补货", "查看库存", "库存状态", "剩余数量", "存货", "库存量", "库存查询", "库存管理"],
    "web_agent": ["网页", "网站", "url", "http", "https", "京东", "商品", "产品信息", "网页内容", "网址", "链接",
                  "浏览器"],
    "github_agent": ["github", "git", "仓库", "代码", "开源", "版本", "release", "issue", "问题", "提交", "分支",
                     "pull request"],
    "media_agent": ["视频", "音频", "mp4", "mp3", "wav", "avi", "mov", "mkv", "时长", "帧", "截图", "声音", "录音",
                    "播放"],
    "pdf_agent": ["pdf", "文档", "文本", "文字", "提取", "图片数量", "页数", "内容", "阅读", "转换"],
    "video_agent": ["视频", "mp4", "avi", "mov", "mkv", "时长", "帧", "截图", "时间点", "播放", "剪辑", "分辨率"],
    "external_search_agent": ["搜索", "查询", "查找", "了解", "知道", "信息", "数据", "统计", "报告", "分析",
                              "微博", "weibo", "抖音", "外部", "网络", "在线", "最新", "实时", "热点", "新闻",
                              "百度", "搜索不到", "无法访问", "没有权限", "图片", "内容", "详情", "具体", "增长",
                              "同比", "增加", "提升", "减少", "下降", "成交额", "销售额", "破千万", "百分比", "%",
                              "电商", "大促", "618", "双11", "战报", "数据", "数字", "数值", "多少"]
}

# 特殊规则：某些关键词需要更精确的匹配
special_rules = {
    "web_agent": ["jd.com", "taobao.com", "tmall.com", "商品编号", "产品id"],
    "github_agent": ["github.com", "repo", "repository", "star", "fork"],
    "pdf_agent": [".pdf", "adobe", "acrobat", "扫描件"],
    "video_agent": [".mp4", ".avi", ".mov", ".mkv", "视频文件", "影片"],
    "external_search_agent": ["微博.com", "weibo.com", "baidu.com", "搜索不到", "无法访问", "没有权限",
                              "受限", "外部资源", "网络内容", "实时数据", "最新消息", "同比增长", "增长数据"]
}


@mcp.tool(description="根据用户问题选择需要调用的 Agent")
def decide_agents(query: str = Field(description="用户输入的自然语言问题")) -> list:
    query_lower = query.lower()
    selected_agents = []

    # 优先检查外部搜索相关关键词
    external_search_priority = False

    # 检查是否需要优先使用外部搜索
    priority_keywords = ["增长", "同比", "数据", "统计", "百分比", "%", "成交额", "销售额", "破千万",
                         "微博", "weibo", "最新", "实时", "百度", "搜索"]
    if any(kw in query_lower for kw in priority_keywords):
        external_search_priority = True
        if "external_search_agent" not in selected_agents:
            selected_agents.append("external_search_agent")

    # 首先检查特殊规则
    for agent, special_keywords in special_rules.items():
        if any(kw in query_lower for kw in special_keywords):
            if agent not in selected_agents:
                selected_agents.append(agent)

    # 然后检查一般关键词
    for agent, keywords in agent_keywords.items():
        if any(kw in query_lower for kw in keywords):
            if agent not in selected_agents:
                selected_agents.append(agent)

    # 处理媒体相关的特殊逻辑
    if any(kw in query_lower for kw in ["视频", "音频", "媒体"]) and "media_agent" not in selected_agents:
        selected_agents.append("media_agent")

    # 如果选择了多个媒体相关的agent，只保留media_agent
    media_agents = ["video_agent", "pdf_agent", "media_agent"]
    selected_media = [agent for agent in selected_agents if agent in media_agents]
    if len(selected_media) > 1:
        for agent in selected_media:
            if agent != "media_agent":
                selected_agents.remove(agent)

    # 外部搜索兜底逻辑：如果问题涉及网络内容或实时数据，确保外部搜索在列表中
    has_web_content = any(kw in query_lower for kw in [
        "微博", "weibo", "网页", "网站", "京东", "电商", "新闻", "热点",
        "百度", "搜索", "最新", "实时", "图片", "内容", "数据", "增长"
    ])

    if has_web_content and "external_search_agent" not in selected_agents:
        selected_agents.append("external_search_agent")

    # 如果外部搜索是优先项，将其移到列表前面
    if external_search_priority and "external_search_agent" in selected_agents:
        selected_agents.remove("external_search_agent")
        selected_agents.insert(0, "external_search_agent")

    # 如果没有选择任何agent，使用external_search_agent作为默认（而不是chat_gpt）
    if not selected_agents:
        selected_agents.append("external_search_agent")

    return selected_agents


if __name__ == "__main__":
    mcp.run()