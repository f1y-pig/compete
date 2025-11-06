import asyncio
import os
from dotenv import load_dotenv
from oxygent import MAS, Config, oxy, OxyRequest

# ----------------------------
# 配置
# ----------------------------
load_dotenv(dotenv_path="demo.env")
Config.set_agent_llm_model("default_llm")
Config.set_message_is_show_in_terminal(True)

# ----------------------------
# 路由工作流
# ----------------------------
async def router_workflow(oxy_request: OxyRequest):
    user_query = oxy_request.get_query(master_level=True).lower()
    tasks = []

    # 专家评估请求
    if any(k in user_query for k in ["project evaluation", "项目评估", "feasibility", "可行性", "recommendation"]):
        resp = await oxy_request.call(callee="expert_panel", arguments={"query": user_query})
        return resp.output if hasattr(resp, "output") else str(resp)

    # 普通任务路由
    if "http://" in user_query or "https://" in user_query or any(k in user_query for k in ["search","google","bing","baidu","网页","检索","搜索","京东","问大家"]):
        tasks.append("web_agent")
    if any(k in user_query for k in ["time","现在几点","几点了","current time","北京时间"]):
        tasks.append("time_agent")
    if any(k in user_query for k in ["pi","圆周率","calculate","digits","位小数"]):
        tasks.append("math_agent")
    if any(k in user_query for k in ["保存","写入","读取"]):
        tasks.append("file_agent")

    # 没有匹配，调用默认 LLM
    if not tasks:
        resp = await oxy_request.call(
            callee="default_llm",
            arguments={"messages": [{"role": "user", "content": user_query}]},
        )
        return resp.output if hasattr(resp, "output") else str(resp)

    # 并发调用普通任务
    results = await asyncio.gather(*[
        oxy_request.call(callee=agent_name, arguments={"query": user_query}) for agent_name in tasks
    ])
    return "\n".join([r.output if hasattr(r, "output") else str(r) for r in results])

# ----------------------------
# MCP Client + LLM + Agent 配置
# ----------------------------
oxy_space = [
    # MCP 工具
    oxy.StdioMCPClient(
        name="time_tools",
        params={"command": "uvx", "args": ["mcp-server-time", "--local-timezone=Asia/Shanghai"]},
    ),
    oxy.StdioMCPClient(
        name="file_tools",
        params={"command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "./local_file"]},
    ),
    oxy.StdioMCPClient(
        name="math_tools",
        params={"command": "uv", "args": ["--directory", "./mcp_servers", "run", "math_tools.py"]},
    ),
    oxy.StdioMCPClient(
        name="web_tools",
        params={"command": "uv", "args": ["--directory", "./mcp_servers/browser", "run", "server.py"]},
    ),

    # LLM
    oxy.HttpLLM(
        name="default_llm",
        api_key=os.getenv("DEFAULT_LLM_API_KEY"),
        base_url=os.getenv("DEFAULT_LLM_BASE_URL"),
        model_name=os.getenv("DEFAULT_LLM_MODEL_NAME"),
        llm_params={"temperature": 0.5},
        semaphore=4,
        timeout=240,
    ),

    # 普通功能 Agent
    oxy.ReActAgent(name="time_agent", desc="Query time", tools=["time_tools"]),
    oxy.ReActAgent(name="file_agent", desc="Filesystem ops", tools=["file_tools"]),
    oxy.ReActAgent(name="math_agent", desc="Math ops", tools=["math_tools"]),
    oxy.ReActAgent(name="web_agent", desc="Web search", tools=["web_tools"]),
    # 专家评估系统
    oxy.ChatAgent(
        name="tech_expert",
        llm_model="default_llm",
        description="AI product technical feasibility expert",
        prompt="...tech expert prompt..."
    ),
    oxy.ChatAgent(
        name="business_expert",
        llm_model="default_llm",
        description="AI product business value expert",
        prompt="...business expert prompt..."
    ),
    oxy.ChatAgent(
        name="risk_expert",
        llm_model="default_llm",
        description="AI project risk expert",
        prompt="...risk expert prompt..."
    ),
    oxy.ChatAgent(
        name="legal_expert",
        llm_model="default_llm",
        description="AI legal compliance expert",
        prompt="...legal expert prompt..."
    ),
    oxy.ParallelAgent(
        name="expert_panel",
        llm_model="default_llm",
        desc="Expert panel parallel evaluation",
        permitted_tool_name_list=["tech_expert", "business_expert", "risk_expert", "legal_expert"],
        is_master=True,
    ),

    # Master Agent
    oxy.WorkflowAgent(
        name="master_agent",
        desc="Unified router: ordinary queries + expert evaluation",
        sub_agents=[
            "time_agent","file_agent","math_agent","web_agent","default_llm","expert_panel"
        ],
        func_workflow=router_workflow,
        is_master=True,
        is_retain_master_short_memory=True,
    ),
]

# ----------------------------
# 启动服务
# ----------------------------
async def main():
    async with MAS(oxy_space=oxy_space) as mas:
        await mas.start_web_service(
            first_query="Hello! Please tell me the current time and save it into a file.",
            welcome_message="Hi, I'm OxyGent. How can I assist you today?",
        )

if __name__ == "__main__":
    asyncio.run(main())
