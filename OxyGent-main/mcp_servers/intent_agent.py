# mcp_servers/intent_agent.py
from mcp.server.fastmcp import FastMCP
from pydantic import Field

mcp = FastMCP()

# 每个 Agent 对应的关键词或意图
agent_keywords = {
    "multi_format_agent": ["文件", "pdf", "excel", "ppt", "image", "video", "音频", "mp3", "mp4"],
    "time_agent": ["时间", "日期", "现在"],
    "delivery_agent": ["订单", "下单", "查询订单", "发货", "快递"],
    "inventory_agent": ["库存", "补货", "查看库存", "库存状态", "剩余数量"]
}

@mcp.tool(description="根据用户问题选择需要调用的 Agent")
def decide_agents(query: str = Field(description="用户输入的自然语言问题")) -> list:
    query_lower = query.lower()
    selected_agents = ["chat_gpt"]  # Chat Agent 总是被调用
    for agent, keywords in agent_keywords.items():
        if any(kw in query_lower for kw in keywords):
            selected_agents.append(agent)
    return selected_agents

if __name__ == "__main__":
    mcp.run()
