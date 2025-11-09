# master_service.py
import os
import asyncio
from dotenv import load_dotenv
from oxygent import MAS, Config, oxy, OxyRequest
from mcp_servers import multi_file_tools_server  # 调用 prepare_file_for_llm
from mcp_servers import delivery_tools
from mcp_servers import inventory_tools

# ----------------------------
# 加载环境变量 & LLM 配置
# ----------------------------
load_dotenv(dotenv_path="demo.env")
Config.set_agent_llm_model("default_llm")
Config.set_message_is_show_in_terminal(True)

# ----------------------------
# Master Agent 工作流（并行调用子 Agent）
# ----------------------------
async def master_workflow(oxy_request: OxyRequest):
    user_query = oxy_request.get_query(master_level=True)

    # 调用 Intent Agent 决定要并行的 Agent
    intent_resp = await oxy_request.call(
        callee="intent_agent",
        arguments={"query": user_query}
    )
    agents_to_call = getattr(intent_resp, "output", ["chat_gpt"])

    # 并行调用选中的 Agent
    tasks = [oxy_request.call(callee=agent, arguments={"query": user_query}) for agent in agents_to_call]
    results = await asyncio.gather(*tasks)

    # 汇总输出
    summary_prompt = f"用户问题: {user_query}\n\n"
    for agent, resp in zip(agents_to_call, results):
        summary_prompt += f"[{agent}]: {getattr(resp,'output',str(resp))}\n"

    # 最终用 LLM 生成自然语言总结
    final_resp = await oxy_request.call(
        callee="default_llm",
        arguments={"messages":[{"role":"user","content": summary_prompt}]}
    )
    return getattr(final_resp, "output", str(final_resp))


# ----------------------------
# 配置空间
# ----------------------------
oxy_space = [
    # 1. LLM 核心
    oxy.HttpLLM(
        name="default_llm",
        api_key=os.getenv("DEFAULT_LLM_API_KEY"),
        base_url=os.getenv("DEFAULT_LLM_BASE_URL"),
        model_name=os.getenv("DEFAULT_LLM_MODEL_NAME"),
        llm_params={"temperature":0.3},
        semaphore=4,
        timeout=300,
    ),

    # 2. MCP 工具：文件处理
    oxy.MCPTool(
        name="file_tools",
        func=multi_file_tools_server.prepare_file_for_llm,
        description="处理 Excel/TXT/PPTX/Image/Audio/Video/PDF 文件"
    ),

    # 3. 文件处理智能体
    oxy.ReActAgent(
        name="multi_format_agent",
        desc="处理文件问题",
        tools=["file_tools"]
    ),

    # 4. MCP 客户端：时间查询
    oxy.StdioMCPClient(
        name="time_tools",
        params={"command":"uvx", "args":["mcp-server-time","--local-timezone=Asia/Shanghai"]},
    ),
    oxy.ReActAgent(
        name="time_agent",
        desc="查询时间",
        tools=["time_tools"]
    ),

    # 5. Chat 系统 Agent
    oxy.ReActAgent(
        name="chat_gpt",
        desc="处理普通对话或问答"
    ),

    # 6. MCP 工具：订单管理
    oxy.StdioMCPClient(
        name="delivery_tools",
        params={"command": "python", "args": ["mcp_servers/delivery_tools.py"]},
    ),
    oxy.ReActAgent(
        name="delivery_agent",
        desc="处理与订单管理相关任务",
        tools=["delivery_tools"]
    ),

    # 7. MCP 工具：库存管理
    oxy.StdioMCPClient(
        name="inventory_tools",
        params={"command": "python", "args": ["mcp_servers/inventory_tools.py"]},
    ),
    oxy.ReActAgent(
        name="inventory_agent",
        desc="处理库存管理任务",
        tools=["inventory_tools"]
    ),

    # 8. Intent Agent（关键词或语义识别要调用的 Agent）
    oxy.ReActAgent(
        name="intent_agent",
        desc="根据用户问题判断要调用哪些子 Agent",
    ),

    # 9. Master Agent
    oxy.ReActAgent(
        is_master=True,
        name="master_agent",
        sub_agents=["chat_gpt","multi_format_agent","time_agent","delivery_agent","inventory_agent","intent_agent"],
        func_workflow=master_workflow,
        additional_prompt="Master Agent 汇总子 Agent 输出"
    ),
]

# ----------------------------
# 启动服务
# ----------------------------
async def main():
    async with MAS(oxy_space=oxy_space) as mas:
        await mas.start_web_service(
            first_query="Hello! What time it is now?",
            welcome_message="Hi, I'm your Master Agent. How can I assist you today?"
        )

if __name__ == "__main__":
    asyncio.run(main())
