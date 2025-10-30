import asyncio
import os
from dotenv import load_dotenv
from oxygent import MAS, Config, oxy, preset_tools
load_dotenv(dotenv_path="demo.env")
Config.set_agent_llm_model("default_llm")
# 放在 oxy_space 定义前面，或与其相邻

async def router_workflow(oxy_request):
    user_query = oxy_request.get_query(master_level=True)
    q = user_query.lower()
    tasks = []

    # 严格匹配（按需增删关键词/规则）
    if "http://" in q or "https://" in q or any(k in q for k in ["search","google","bing","baidu","网页","检索","搜索","京东","问大家"]):
        tasks.append(("agent", "web_agent"))
    if any(k in q for k in ["time","现在几点","几点了","current time","北京时间"]):
        tasks.append(("agent", "time_agent"))
    if any(k in q for k in ["pi","圆周率","calculate","digits","位小数"]):
        tasks.append(("agent", "math_agent"))
    if any(k in q for k in ["保存","写入","读取"]):
        tasks.append(("agent", "file_agent"))

    # 兜底到默认 LLM（无匹配）
    if not tasks:
        resp = await oxy_request.call(
            callee="default_llm",
            arguments={"messages": [{"role": "user", "content": user_query}]},
        )
        return resp.output if hasattr(resp, "output") else str(resp)

    # 顺序执行（需要并发可自行改 asyncio.gather）
    results = []
    for kind, target in tasks:
        resp = await oxy_request.call(callee=target, arguments={"query": user_query})
        results.append(resp.output if hasattr(resp, "output") else str(resp))
    return "\n".join(results)


oxy_space = [
    oxy.StdioMCPClient(
        name="web_tools",
        params={"command": "uv", "args": ["--directory", "./", "run", "mcp_servers/browser/server.py"]},
    ),
    oxy.HttpLLM(
        name="default_llm",
        api_key=os.getenv("DEFAULT_LLM_API_KEY"),
        base_url=os.getenv("DEFAULT_LLM_BASE_URL"),
        model_name=os.getenv("DEFAULT_LLM_MODEL_NAME"),
        llm_params={"temperature": 0.5},
        semaphore=4,
        timeout=240,
    ),
    preset_tools.time_tools,
    oxy.ReActAgent(name="time_agent", desc="Query time", tools=["time_tools"]),
    preset_tools.file_tools,
    oxy.ReActAgent(name="file_agent", desc="Filesystem ops", tools=["file_tools"]),
    preset_tools.math_tools,
    oxy.ReActAgent(name="math_agent", desc="Math ops", tools=["math_tools"]),
    oxy.ReActAgent(name="web_agent", desc="Web search", tools=["web_tools"]),

    # 新的 master：路由 + 兜底 default_llm
    oxy.WorkflowAgent(
        name="master_agent",
        desc="Rule-based router with fallback to default_llm",
        sub_agents=["time_agent", "file_agent", "math_agent", "web_agent", "default_llm"],  # 包含 default_llm 以通过权限检查
        func_workflow=router_workflow,
        is_master=True,
        is_retain_master_short_memory=True,
    ),
]



async def main():
    async with MAS(oxy_space=oxy_space) as mas:
        await mas.start_web_service(
            first_query="What time is it now? Please save it into time.txt."
        )


if __name__ == "__main__":
    asyncio.run(main())
