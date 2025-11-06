import os
import asyncio
from dotenv import load_dotenv
from oxygent import MAS, Config, oxy, OxyRequest
from mcp_servers import multi_file_tools_server  # 导入模块化文件处理函数

# ----------------------------
# 加载环境变量 & LLM 配置
# ----------------------------
load_dotenv(dotenv_path="demo.env")
Config.set_agent_llm_model("default_llm")
Config.set_message_is_show_in_terminal(True)

# ----------------------------
# Master Agent 工作流（汇总子 Agent 输出）
# ----------------------------
async def master_workflow(oxy_request: OxyRequest):
    user_query = oxy_request.get_query(master_level=True)

    # 调用 Chat Agent
    chat_resp = await oxy_request.call(callee="chat_gpt", arguments={"query": user_query})

    # 调用文件/多模态任务 Agent
    file_resp = await oxy_request.call(callee="multi_format_agent", arguments={"query": user_query})

    # 调用时间 Agent
    time_resp = await oxy_request.call(callee="time_agent", arguments={"query": user_query})

    # 汇总输出
    summary_prompt = f"用户问题: {user_query}\n\n"
    summary_prompt += f"[Chat Agent]: {getattr(chat_resp,'output',str(chat_resp))}\n"
    summary_prompt += f"[File Agent]: {getattr(file_resp,'output',str(file_resp))}\n"
    summary_prompt += f"[Time Agent]: {getattr(time_resp,'output',str(time_resp))}\n"

    # 最终用 LLM 生成自然语言总结
    final_resp = await oxy_request.call(
        callee="default_llm",
        arguments={"messages":[{"role":"user","content": summary_prompt}]}
    )
    return getattr(final_resp, "output", str(final_resp))

# ----------------------------
# OxyGent 配置空间
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

    # 3. 文件处理智能体（独立显示）
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

    # 5. Chat 系统 Agent（独立显示）
    oxy.ReActAgent(
        name="chat_gpt",
        desc="处理普通对话或问答"
    ),

    # 6. Master Agent（总调度 + 汇总）
    oxy.ReActAgent(
        is_master=True,
        name="master_agent",
        sub_agents=["chat_gpt","multi_format_agent","time_agent"],
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
            first_query="Hello! Ask me anything or upload a file.",
            welcome_message="Hi, I'm your Master Agent. How can I assist you today?"
        )

if __name__ == "__main__":
    asyncio.run(main())
