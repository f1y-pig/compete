import asyncio
import os
import re
from oxygent import MAS, Config, OxyRequest, OxyResponse, oxy
from oxygent.prompts import INTENTION_PROMPT
from dotenv import load_dotenv
from pydantic import Field

# ----------------------------
# 配置
# ----------------------------
load_dotenv('demo.env')
Config.set_agent_short_memory_size(12)
Config.set_message_is_show_in_terminal(True)
Config.set_agent_llm_model("default_llm")
Config.set_app_name('task_1_v5_fixed')


# ----------------------------
# Query 更新和输出格式化
# ----------------------------
def update_query(oxy_request: OxyRequest) -> OxyRequest:
    user_query = oxy_request.get_query(master_level=True)
    oxy_request.arguments["query"] = user_query
    oxy_request.arguments["who"] = oxy_request.callee
    return oxy_request


def format_output(oxy_response: OxyResponse) -> OxyResponse:
    oxy_response.output = "Answer: " + oxy_response.output
    return oxy_response


# ----------------------------
# Math Agent Workflow
# ----------------------------
async def math_agent_workflow(oxy_request: OxyRequest):
    user_query = oxy_request.get_query(master_level=True)
    numbers = re.findall(r"\d+", user_query)
    n = int(numbers[-1]) if numbers else 2

    response = await oxy_request.call(
        callee="math_tools",
        arguments={"prec": n}
    )
    return f"Pi to {n} digits: {response.output}"


# ----------------------------
# Multi-intent Workflow
# ----------------------------
async def multi_intent_workflow(oxy_request: OxyRequest):
    user_query = oxy_request.get_query(master_level=True)
    print("--- User query ---", user_query)

    results = []
    tasks = []

    # 匹配任务
    if any(k in user_query.lower() for k in ["pi", "circle", "圆周率"]):
        tasks.append("math_agent")
    if any(k in user_query.lower() for k in ["time", "clock", "现在几点"]):
        tasks.append("time_agent")
    if any(k in user_query.lower() for k in ["file", "document", "excel", "pdf"]):
        tasks.append("file_agent")
    # ⚡ 不再添加 default_llm

    for agent in tasks:
        try:
            oxy_response = await oxy_request.call(
                callee=agent,
                arguments={"query": user_query}
            )
            if isinstance(oxy_response, str):
                results.append(oxy_response)
            else:
                results.append(oxy_response.output)
        except Exception as e:
            results.append(f"{agent} task failed: {e}")

    return "\n".join(results)


# ----------------------------
# 兼容 default_llm 的输入转换函数（可保留用于其他用途）
# ----------------------------
def llm_wrap_input(oxy_request: OxyRequest) -> OxyRequest:
    query = oxy_request.arguments.get("query", "")
    oxy_request.arguments["messages"] = [{"role": "user", "content": query}]
    return oxy_request


# ----------------------------
# OxyGent 空间配置
# ----------------------------
oxy_space = [
    # LLM
    oxy.HttpLLM(
        name="default_llm",
        api_key=os.getenv("DEFAULT_LLM_API_KEY"),
        base_url=os.getenv("DEFAULT_LLM_BASE_URL"),
        model_name=os.getenv("DEFAULT_LLM_MODEL_NAME"),
        llm_params={"temperature": 0.01},
        semaphore=4,
        func_process_input=llm_wrap_input,
    ),
    # Intent agent
    oxy.ChatAgent(name="intent_agent", prompt=INTENTION_PROMPT),
    # MCP clients
    oxy.StdioMCPClient(
        name="time_tools",
        params={
            "command": "uvx",
            "args": ["mcp-server-time", "--local-timezone=Asia/Shanghai"],
        },
    ),
    oxy.StdioMCPClient(
        name="file_tools",
        params={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "./local_file"],
        },
    ),
    oxy.StdioMCPClient(
        name="math_tools",
        params={
            "command": "uv",
            "args": ["--directory", "./mcp_servers", "run", "math_tools.py"],
        },
    ),
    # Master agent
    oxy.ReActAgent(
        name="master_agent",
        sub_agents=["time_agent", "file_agent", "math_agent"],
        additional_prompt="You may get several types of tasks, please choose the correct agent to finish them.",
        is_master=True,
        func_format_output=format_output,
        timeout=100,
        llm_model="default_llm",
        is_retain_master_short_memory=False,  # ⚡关闭短期记忆
    ),
    # 单个功能 agent
    oxy.ReActAgent(
        name="time_agent",
        desc="A tool for time query.",
        additional_prompt="Do not send other information except time.",
        tools=["time_tools"],
        func_process_input=update_query,
        trust_mode=False,
        timeout=10,
    ),
    oxy.ReActAgent(
        name="file_agent",
        desc="A tool for file operation.",
        tools=["file_tools"],
        func_process_input=update_query,
    ),
    oxy.WorkflowAgent(
        name="math_agent",
        desc="A tool for pi query",
        sub_agents=[],
        tools=["math_tools"],
        func_workflow=math_agent_workflow,
        is_retain_master_short_memory=True,
    ),
    oxy.WorkflowAgent(
        name="multi_intent_agent",
        desc="Multi-intent workflow agent",
        sub_agents=["time_agent", "file_agent", "math_agent"],
        func_workflow=multi_intent_workflow,
        is_retain_master_short_memory=True,
    ),
]


# ----------------------------
# 启动服务
# ----------------------------
async def main():
    async with MAS(oxy_space=oxy_space) as mas:
        await mas.start_web_service(
            first_query="Hello! Can you calculate 20 digits of pi and tell me the time?",
            welcome_message="Hi, I’m OxyGent. How can I assist you?",
        )


if __name__ == "__main__":
    asyncio.run(main())
