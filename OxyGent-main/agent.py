import asyncio
import os
import json
import re
from pathlib import Path
from dotenv import load_dotenv
from oxygent import MAS, Config, oxy, OxyRequest
from mcp_servers import multi_file_tools_server
from mcp_servers import delivery_tools
from mcp_servers import inventory_tools

# -------------------------- 基础配置 --------------------------
load_dotenv(dotenv_path="demo.env")
Config.set_app_name('multi_format_qa_task_v1')
Config.set_agent_llm_model("default_llm")
Config.set_message_is_show_in_terminal(True)


# -------------------------- Master Agent 工作流 --------------------------
async def master_workflow(oxy_request: OxyRequest):
    user_query = oxy_request.get_query(master_level=True)
    intent_resp = await oxy_request.call(
        callee="intent_agent",
        arguments={"query": user_query}
    )
    agents_to_call = getattr(intent_resp, "output", ["external_search_agent"])  # 默认使用外部搜索

    # 移除百度搜索工具调用逻辑
    tasks = [oxy_request.call(callee=agent, arguments={"query": user_query}) for agent in agents_to_call]
    results = await asyncio.gather(*tasks)
    summary_prompt = f"用户问题: {user_query}\n\n"
    for agent, resp in zip(agents_to_call, results):
        agent_output = getattr(resp, "output", str(resp))
        summary_prompt += f"[{agent}]: {agent_output}\n"
    summary_prompt += """
请按以下规则生成答案：
1. 优先使用百度API搜索的真实数据
2. 若有对应工具的有效结果，优先基于该结果回答
3. 无对应工具或结果为Not found类提示，使用常识回答
4. 严格遵守用户要求的输出格式（日期xxxx-xx-xx，颜色小写英文等）
5. 回答中不要包含换行符，仅保留单行核心信息
6. 无答案时输出Not found
7. 对于网络内容查询，明确说明数据来源
"""
    final_resp = await oxy_request.call(
        callee="default_llm",
        arguments={"messages": [{"role": "user", "content": summary_prompt}]}
    )
    return getattr(final_resp, "output", str(final_resp))


# -------------------------- OxyGent 空间配置 --------------------------
oxy_space = [
    # 1. 核心 LLM
    oxy.HttpLLM(
        name="default_llm",
        api_key=os.getenv("DEFAULT_LLM_API_KEY"),
        base_url=os.getenv("DEFAULT_LLM_BASE_URL"),
        model_name=os.getenv("DEFAULT_LLM_MODEL_NAME"),
        llm_params={"temperature": 0.3},
        semaphore=8,
        timeout=300,
    ),

    # 2. 文件处理相关
    oxy.MCPTool(
        name="file_tools",
        func=multi_file_tools_server.prepare_file_for_llm,
        description="处理各类文件预处理（Excel/TXT/PPTX/PDF/图片等）"
    ),
    oxy.StdioMCPClient(
        name="multi_format_qa_tools",
        params={
            "command": "uv",
            "args": ["--directory", "./mcp_servers", "run", "multi_format_qa_tools.py"]
        },
        description="多格式文件问答工具，解析文件内容并回答问题"
    ),
    oxy.ReActAgent(
        name="multi_format_agent",
        llm_model="default_llm",
        tools=["file_tools", "multi_format_qa_tools"],
        desc="处理文件相关问题，基于文件内容回答",
        additional_prompt="""
    请按以下规则回答：
    1. 按需选择文件工具，先解析文件再回答；
    2. 严格按格式要求输出（如阿拉伯数字、小写英文）；
    3. 如果无法从文件中找到确切答案，基于相关知识给出合理答案；
    4. 不要输出"Not found in file"，直接给出基于知识的最佳答案；
    5. 答案仅含核心信息，无多余描述，不包含换行符，仅占一行。
    """
    ),

    # 3. 新增工具
    oxy.StdioMCPClient(
        name="web_tools",
        params={"command": "python", "args": ["mcp_servers/web_tools.py"]},
        description="获取网页内容，特别是京东商品信息"
    ),
    oxy.StdioMCPClient(
        name="video_tools",
        params={"command": "python", "args": ["mcp_servers/video_tools.py"]},
        description="处理视频文件，获取时长、提取帧等"
    ),
    oxy.StdioMCPClient(
        name="github_tools",
        params={"command": "python", "args": ["mcp_servers/github_tools.py"]},
        description="获取GitHub仓库信息、发布版本和issues"
    ),
    oxy.StdioMCPClient(
        name="pdf_tools",
        params={"command": "python", "args": ["mcp_servers/pdf_tools.py"]},
        description="提取PDF文本内容和统计图片数量"
    ),
    oxy.StdioMCPClient(
        name="media_tools",
        params={"command": "python", "args": ["mcp_servers/media_tools.py"]},
        description="处理音频文件，获取时长和提取文本"
    ),

    # 4. 增强版外部搜索工具（集成百度API）
    oxy.StdioMCPClient(
        name="external_search_tools",
        params={"command": "python", "args": ["mcp_servers/external_search_tools.py"]},
        description="增强版外部搜索工具，集成百度API实时搜索和数据分析"
    ),

    # 5. 其他功能智能体
    oxy.StdioMCPClient(
        name="time_tools",
        params={"command": "uvx", "args": ["mcp-server-time", "--local-timezone=Asia/Shanghai"]},
        description="查询当前时间"
    ),
    oxy.ReActAgent(
        name="time_agent",
        llm_model="default_llm",
        tools=["time_tools"],
        desc="处理时间查询相关问题"
    ),
    oxy.ReActAgent(
        name="web_agent",
        llm_model="default_llm",
        tools=["web_tools"],
        desc="处理网页内容查询，特别是京东商品信息",
        additional_prompt="""
        1. 需要解析URL或网页内容时调用web_tools
        2. 京东商品查询需提取商品ID
        3. 严格按格式要求输出结果
        """
    ),
    oxy.ReActAgent(
        name="github_agent",
        llm_model="default_llm",
        tools=["github_tools"],
        desc="处理GitHub相关查询，如版本、issues等"
    ),
    oxy.ReActAgent(
        name="media_agent",
        llm_model="default_llm",
        tools=["video_tools", "media_tools", "pdf_tools"],
        desc="处理视频、音频、PDF等媒体文件相关问题"
    ),
    # 新增：pdf_agent 和 video_agent
    oxy.ReActAgent(
        name="pdf_agent",
        llm_model="default_llm",
        tools=["pdf_tools"],
        desc="专门处理PDF文件相关问题"
    ),
    oxy.ReActAgent(
        name="video_agent",
        llm_model="default_llm",
        tools=["video_tools"],
        desc="专门处理视频文件相关问题"
    ),
    # 增强版外部搜索智能体
    oxy.ReActAgent(
        name="external_search_agent",
        llm_model="default_llm",
        tools=["external_search_tools"],
        desc="处理需要外部网络搜索的查询，集成百度API实时搜索",
        additional_prompt="""
    1. 优先使用百度API获取实时网络信息
    2. 如果搜索工具无法获取具体信息，基于自身知识给出合理答案
    3. 不要输出"Not found"或"无法获取"等否定性回答
    4. 直接输出基于知识的最佳答案
    5. 明确说明数据来源（如"基于技术知识"或"根据搜索结果"）
    6. 答案格式简洁明了，不包含换行符
    """
    ),
    oxy.ReActAgent(
        name="chat_gpt",
        llm_model="default_llm",
        desc="处理普通对话、常识问答等无文件/无链接的任务，基于知识给出合理答案",
        additional_prompt="基于相关知识给出最佳答案，不要输出Not found，答案不包含换行符，仅占一行"
    ),
    oxy.StdioMCPClient(
        name="delivery_tools",
        params={"command": "python", "args": ["mcp_servers/delivery_tools.py"]},
        description="订单管理相关工具"
    ),
    oxy.ReActAgent(
        name="delivery_agent",
        llm_model="default_llm",
        tools=["delivery_tools"],
        desc="处理订单管理相关任务"
    ),
    oxy.StdioMCPClient(
        name="inventory_tools",
        params={"command": "python", "args": ["mcp_servers/inventory_tools.py"]},
        description="库存管理相关工具"
    ),
    oxy.ReActAgent(
        name="inventory_agent",
        llm_model="default_llm",
        tools=["inventory_tools"],
        desc="处理库存管理相关任务"
    ),

    # 6. 意图识别智能体（核心调度逻辑）
    oxy.ReActAgent(
        name="intent_agent",
        llm_model="default_llm",
        desc="根据用户问题识别意图，输出需调用的智能体列表",
        additional_prompt="""
1. 问题含文件名称/路径或需解析文件→["multi_format_agent"]；
2. 时间查询相关→["time_agent"]；
3. 订单相关→["delivery_agent"]；
4. 库存相关→["inventory_agent"]；
5. 网页URL或京东商品相关→优先["external_search_agent"]，其次["web_agent"]；
6. GitHub相关→["github_agent"]；
7. 视频、音频、PDF相关→["media_agent", "pdf_agent", "video_agent"]；
8. 涉及网络搜索、实时数据、增长数据→优先["external_search_agent"]；
9. 其他情况→["chat_gpt"]；
10. 仅输出智能体名称列表，无其他文字（如 ["external_search_agent"]）。
注意：对于网络内容查询，优先使用external_search_agent获取实时数据。
"""
    ),

    # 7. 主智能体（调度中心）
    oxy.ReActAgent(
        is_master=True,
        name="master_agent",
        llm_model="default_llm",
        sub_agents=["chat_gpt", "multi_format_agent", "time_agent", "delivery_agent",
                    "inventory_agent", "intent_agent", "web_agent", "github_agent",
                    "media_agent", "pdf_agent", "video_agent", "external_search_agent"],
        func_workflow=master_workflow,
        additional_prompt="通过 intent_agent 识别用户意图，优先使用external_search_agent获取实时数据，如果无法获取具体信息则基于知识给出合理答案，汇总结果后按要求格式输出，答案不包含换行符，仅占一行"
    ),
]


# -------------------------- 核心任务处理函数 --------------------------
async def process_tasks(test_dir: str = "test", output_file: str = "result.jsonl"):
    """
    处理 test/data.jsonl 中的批量任务，输出规范 JSON 数组格式：
    - 开头[，结尾]
    - 每个对象空两格，字段空四格
    - task_id和answer各占一行，answer无换行
    - 冒号后带空格
    """
    # 使用绝对路径
    TEST_DIR_ABS = r"E:\大三大四\compete\compete\OxyGent-main\test"
    data_path = Path(TEST_DIR_ABS) / "data.jsonl"

    if not data_path.exists():
        print(f"❌ Error: {data_path} not found. Please check the path.")
        return

    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    all_results = []

    with open(data_path, "r", encoding="utf-8") as f_in:
        async with MAS(oxy_space=oxy_space) as mas:
            task_idx = 0
            for line in f_in:
                task_idx += 1
                try:
                    task = json.loads(line.strip())
                    task_id = task.get("task_id", f"task_{task_idx}")
                    query = task.get("query", "")
                    file_name = task.get("file_name", "")

                    # 处理文件路径
                    if file_name:
                        # 如果是多文件，使用 multi_file_qa 工具
                        if file_name.startswith('[') and file_name.endswith(']'):
                            # 多文件问题
                            full_query = f"""
任务信息：
- 文件列表：{file_name}
- 问题：{query}
回答规则：
1. 基于所有文件内容综合分析回答；
2. 严格按格式要求输出；
3. 如果无法从文件中找到确切答案，基于相关知识给出合理答案；
4. 答案仅含核心信息，无多余文字，不包含换行符，仅占一行。
"""
                        else:
                            # 单文件问题
                            full_file_path = str(Path(TEST_DIR_ABS) / file_name) if file_name else ""
                            full_query = f"""
任务信息：
- 文件路径：{full_file_path}
- 问题：{query}
回答规则：
1. 优先基于文件内容回答；
2. 严格按格式要求输出；
3. 如果无法从文件中找到确切答案，基于相关知识给出合理答案；
4. 答案仅含核心信息，无多余文字，不包含换行符，仅占一行。
"""
                    else:
                        # 无文件问题
                        full_query = f"""
任务信息：
- 问题：{query}
回答规则：
1. 优先使用百度API搜索获取实时数据；
2. 如果搜索工具无法获取信息，基于相关知识给出合理答案；
3. 严格按格式要求输出；
4. 答案不包含换行符，仅占一行。
"""

                    payload = {
                        "query": full_query,
                        "callee": "master_agent"
                    }
                    oxy_response = await mas.chat_with_agent(payload=payload)
                    result = oxy_response.output
                    clean_result = result.strip()

                    # 强制格式修正 - 移除换行符
                    clean_result = re.sub(r"\n|\r", "", clean_result)

                    # 检查是否是错误或未找到的信息
                    if "not found" in clean_result.lower() or "无法获取" in clean_result or "搜索失败" in clean_result:
                        # 如果是未找到信息，但结果中包含有用的内容，保留有用内容
                        useful_content = re.sub(r'(not found|无法获取|搜索失败|error|错误)[^.]*\.?', '', clean_result,
                                                flags=re.IGNORECASE)
                        if useful_content.strip() and len(useful_content.strip()) > 10:
                            clean_result = useful_content.strip()

                    # 提取格式要求并优化输出
                    format_match = re.search(r"请用(\w+.*?)(回答|输出)", query)
                    format_req = format_match.group(1).strip() if format_match else "plain text"

                    if "阿拉伯数字" in format_req:
                        num_match = re.search(r"\d+", clean_result)
                        if not num_match and file_name:
                            # 对于文件问题，如果没有找到数字，检查是否有其他有用信息
                            if len(clean_result) > 20 and "not found" not in clean_result.lower():
                                # 保留原有答案，不强制改为Not found
                                pass
                            else:
                                clean_result = "Not found in file"
                        elif not num_match:
                            # 对于非文件问题，如果没有数字但有内容，保留内容
                            if len(clean_result) > 20:
                                pass
                            else:
                                clean_result = "Not found"
                        else:
                            clean_result = num_match.group()
                    elif "小写英文" in format_req:
                        clean_result = clean_result.lower()
                        color_match = re.search(
                            r"(red|blue|green|yellow|black|white|gray|grey|purple|orange|brown|pink|cyan|magenta)",
                            clean_result)
                        if not color_match and file_name:
                            if len(clean_result) > 20 and "not found" not in clean_result.lower():
                                pass
                            else:
                                clean_result = "Not found in file"
                        elif not color_match:
                            if len(clean_result) > 20:
                                pass
                            else:
                                clean_result = "Not found"
                        else:
                            clean_result = color_match.group()
                    elif "文本" in format_req:
                        clean_result = re.sub(r"\s+", " ", clean_result)[:200]

                    # 最终清理：移除可能的错误提示但保留有用内容
                    final_clean = re.sub(r'(以上信息仅供参考|建议.*?获取|搜索.*?失败|无法.*?获取)[^.]*\.?', '',
                                         clean_result)
                    if final_clean.strip():
                        clean_result = final_clean.strip()

                    all_results.append({
                        "task_id": task_id,
                        "answer": clean_result
                    })
                    print(
                        f"✅ Processed task {task_idx} (ID: {task_id}) | Type: {file_name and 'File' or 'Common'} | Answer: {clean_result[:50]}...")

                except json.JSONDecodeError:
                    error_msg = "Error: Invalid JSON format"
                    all_results.append({
                        "task_id": f"invalid_task_{task_idx}",
                        "answer": error_msg
                    })
                    print(f"❌ Task {task_idx} failed: Invalid JSON")
                except Exception as e:
                    # 处理异常字符串
                    raw_error = str(e)[:50]
                    cleaned_error = raw_error.replace('\n', ' ')
                    # 构建安全的错误信息
                    error_str = str(e)[:100]
                    safe_error_str = re.sub(r'["\'\n\r\t\\]', ' ', error_str)
                    safe_error_str = re.sub(r'\s+', ' ', safe_error_str).strip()
                    error_msg = f"Error: {safe_error_str}" if safe_error_str else "Error: Unknown error"
                    # 添加到结果列表
                    all_results.append({
                        "task_id": f"error_task_{task_idx}",
                        "answer": error_msg
                    })
                    # 终端输出
                    print(f"❌ Task {task_idx} failed: {cleaned_error}...")

    # 按要求格式写入文件
    with open(output_file, "w", encoding="utf-8") as f_out:
        f_out.write("[\n")
        for i, res in enumerate(all_results):
            f_out.write("  {\n")
            f_out.write(f'    "task_id": "{res["task_id"]}",\n')
            f_out.write(f'    "answer": "{res["answer"]}"\n')
            if i == len(all_results) - 1:
                f_out.write("  }\n")
            else:
                f_out.write("  },\n")
        f_out.write("]\n")

    print(f"\n🎉 All tasks processed! Result saved to: {output_file}")


# -------------------------- 主函数 --------------------------
async def main():
    print("⚠️  Please confirm data desensitization is completed.")
    print("1. Run desensitization script (if needed):")
    print("   python desensitize_data.py --directory=./cache_dir/local_es_data/ --prefix=multi_format_qa_task_v1")
    print("2. Confirm desensitized files are in: ./cache_dir/local_es_data/local_es_data/ (if applicable)")
    input("\nPress Enter to continue...")

    await process_tasks(
        test_dir="test",
        output_file="result.jsonl"
    )


if __name__ == "__main__":
    asyncio.run(main())