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


# -------------------------- 智能答案提取函数 --------------------------
def extract_core_answer(text, query):
    """智能提取核心答案，根据问题类型采用不同策略"""
    text = text.strip()

    # 1. 数字类问题 - 直接提取数字
    if any(keyword in query for keyword in
           ["数值", "数字", "数量", "多少", "几个", "第几", "排名", "容量", "重量", "时长", "秒", "分钟", "小时", "天",
            "年", "月", "日"]):
        # 提取百分比
        percent_match = re.search(r'([0-9]+\.?[0-9]*)%', text)
        if percent_match:
            return f"{percent_match.group(1)}%"

        # 提取纯数字
        num_match = re.search(r'\b\d+(?:\.\d+)?\b', text)
        if num_match:
            return num_match.group()

    # 2. 英文格式类问题
    if "英文大写" in query or "大写英文" in query:
        uppercase_matches = re.findall(r'\b[A-Z][A-Z]+\b', text)
        if uppercase_matches:
            return max(uppercase_matches, key=len)

    if "小写英文" in query:
        # 提取颜色等小写英文单词
        color_match = re.search(
            r'\b(red|blue|green|yellow|black|white|gray|grey|purple|orange|brown|pink|cyan|magenta)\b', text.lower())
        if color_match:
            return color_match.group()

    # 3. 特定格式类问题
    if "xxxx-xx-xx" in query or "2000-01-01" in query:
        date_match = re.search(r'\d{4}-\d{2}-\d{2}', text)
        if date_match:
            return date_match.group()

    if "2000年8月14日" in query or "年" in query and "月" in query and "日" in query:
        date_match = re.search(r'\d{4}年\d{1,2}月\d{1,2}日', text)
        if date_match:
            return date_match.group()

    # 4. 是/否类问题
    if any(keyword in query for keyword in ["是否", "是不是", "有没有", "能否"]):
        if "是" in text and len(text) < 10:
            return "是"
        elif "否" in text and len(text) < 10:
            return "否"
        elif "有" in text and len(text) < 10:
            return "有"
        elif "没有" in text and len(text) < 10:
            return "没有"

    # 5. 颜色类问题
    if "颜色" in query:
        color_matches = re.findall(r'(红色|蓝色|绿色|黄色|黑色|白色|灰色|紫色|橙色|棕色|粉色|深色|浅色)', text)
        if color_matches:
            return color_matches[0]

    # 6. 品牌/名称类问题
    if any(keyword in query for keyword in ["品牌", "名称", "公司", "厂商", "店铺"]):
        # 提取引号内的内容
        quoted_matches = re.findall(r'["「」『』]([^"「」『』]+)["「」『』]', text)
        if quoted_matches:
            return quoted_matches[0]

    # 7. 化学符号类问题
    if "化学符号" in query:
        chem_match = re.search(r'[A-Z][a-z]?\d*', text)
        if chem_match:
            return chem_match.group()

    # 8. 链接/URL类问题
    if "链接" in query or "URL" in query or "网址" in query:
        url_match = re.search(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text)
        if url_match:
            return url_match.group()

    # 9. 版本号类问题
    if "版本" in query or "v." in query.lower():
        version_match = re.search(r'v?\.?\d+(?:\.\d+)*', text)
        if version_match:
            return version_match.group()

    # 10. 电话号码类问题
    if "电话" in query or "手机" in query:
        phone_match = re.search(r'[\d\-\s\(\)]{7,}', text)
        if phone_match:
            return phone_match.group().strip()

    # 11. 对于描述性问题，进行智能精简但保留核心信息
    if any(keyword in query for keyword in ["描述", "什么", "如何", "哪些", "服装", "穿着", "内容", "详情"]):
        # 移除数据来源说明
        text = re.sub(r'数据来源[^。]*[。]?', '', text)
        text = re.sub(r'来源[^。]*[。]?', '', text)
        text = re.sub(r'基于[^。]*[。]?', '', text)
        text = re.sub(r'根据[^。]*[。]?', '', text)

        # 提取核心句子（第一个完整句子）
        sentences = re.split(r'[。！？!?]', text)
        if sentences and len(sentences[0].strip()) > 0:
            return sentences[0].strip()

    # 12. 列表类问题（逗号分隔）
    if "英文逗号间隔" in query or "顿号分割" in query:
        # 提取列表格式的内容
        list_match = re.search(r'[^，,]*([^，,]+(?:[，,]\s*[^，,]+)+)', text)
        if list_match:
            return list_match.group(1)

    # 通用清理：移除请求文件路径的提示信息
    path_request_patterns = [
        r'请提供.*文件路径.*',
        r'我需要您提供.*',
        r'您提供的文件路径.*',
        r'请确认.*文件路径.*',
        r'请问您能提供.*',
        r'您提到的文件路径.*',
        r'请提供正确的.*',
        r'我需要您提供PDF文件的完整路径.*',
        r'您提供的文件路径test.*',
        r'请提供您要分析的视频文件的具体路径.*',
        r'请提供订单ID.*',
        r'请提供您希望搜索的时间范围.*',
        r'请确认项目名称.*',
        r'请问您具体指的是哪个.*',
        r'请问您知道.*具体发布日期吗.*',
        r'请问您能提供.*注册地址信息吗.*',
        r'请提供图片文件.*'
    ]

    for pattern in path_request_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)

    return text.strip()


def should_use_extracted_answer(original, extracted, query):
    """判断是否应该使用提取的答案"""
    if not extracted or len(extracted) == 0:
        return False

    # 如果提取结果明显更简洁且保留了核心信息
    if len(extracted) < len(original) and len(extracted) > 0:
        # 对于数字类问题，优先使用提取结果
        if any(keyword in query for keyword in ["数值", "数字", "数量", "百分比", "%", "排名"]):
            return True

        # 对于格式要求严格的问题，使用提取结果
        if any(keyword in query for keyword in ["英文大写", "小写英文", "阿拉伯数字", "xxxx-xx-xx"]):
            return True

        # 防止过度简化：如果原答案很短或者提取结果丢失了重要信息，不使用
        if len(original) < 30 or len(extracted) < 5:
            return False

        return True

    return False


# -------------------------- Master Agent 工作流 --------------------------
async def master_workflow(oxy_request: OxyRequest):
    user_query = oxy_request.get_query(master_level=True)
    intent_resp = await oxy_request.call(
        callee="intent_agent",
        arguments={"query": user_query}
    )
    agents_to_call = getattr(intent_resp, "output", ["external_search_agent"])

    tasks = [oxy_request.call(callee=agent, arguments={"query": user_query}) for agent in agents_to_call]
    results = await asyncio.gather(*tasks)

    summary_prompt = f"用户问题: {user_query}\n\n"
    agent_outputs = {}

    for agent, resp in zip(agents_to_call, results):
        agent_output = getattr(resp, "output", str(resp))
        agent_outputs[agent] = agent_output
        summary_prompt += f"[{agent}]: {agent_output}\n"

    # 添加答案验证和选择逻辑
    summary_prompt += """
请按以下规则生成最终答案：

【答案选择优先级】
1. 首先验证答案的正确性：如果发现明显错误（数学计算错误、事实错误等），请纠正
2. 对于数学问题，请重新计算验证，不要盲目接受可能错误的结果
3. 优先选择逻辑合理、计算正确的答案
4. 如果多个答案冲突，选择最符合常识和逻辑的答案

【输出要求】
1. 严格遵守用户要求的输出格式
2. 回答中不要包含换行符，仅保留单行核心信息
3. 不要包含"数据来源"等说明性文字
4. 直接给出正确答案

【特别提醒】
请运用你的判断力，如果工具给出的答案明显错误，请基于正确知识给出答案。
例如数学计算问题，请确保计算逻辑正确。
"""

    # 首先尝试默认LLM
    try:
        final_resp = await oxy_request.call(
            callee="default_llm",
            arguments={"messages": [{"role": "user", "content": summary_prompt}]}
        )
        result = getattr(final_resp, "output", str(final_resp))

        # 检查结果质量
        if (len(result.strip()) < 10 or
                "not found" in result.lower() or
                "无法获取" in result or
                "搜索失败" in result or
                "error" in result.lower()):
            print("🔄 默认LLM结果不理想，切换到千问模型...")
            final_resp = await oxy_request.call(
                callee="qwen_llm",
                arguments={"messages": [{"role": "user", "content": summary_prompt}]}
            )
            result = getattr(final_resp, "output", str(final_resp))

    except Exception as e:
        print(f"🔄 默认LLM调用失败，切换到千问模型: {e}")
        final_resp = await oxy_request.call(
            callee="qwen_llm",
            arguments={"messages": [{"role": "user", "content": summary_prompt}]}
        )
        result = getattr(final_resp, "output", str(final_resp))

    return result


# -------------------------- OxyGent 空间配置 --------------------------
oxy_space = [
    # 1. 核心 LLM - 默认模型
    oxy.HttpLLM(
        name="default_llm",
        api_key=os.getenv("DEFAULT_LLM_API_KEY"),
        base_url=os.getenv("DEFAULT_LLM_BASE_URL"),
        model_name=os.getenv("DEFAULT_LLM_MODEL_NAME"),
        llm_params={"temperature": 0.3},
        semaphore=8,
        timeout=300,
    ),

    # 2. 千问模型作为备用LLM
    oxy.HttpLLM(
        name="qwen_llm",
        api_key="sk-1c5ef9f54c7c48e8a7c04c950da145b9",  # 你的千问API Key
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        model_name="qwen-plus",  # 可以根据需要改为 qwen-turbo, qwen-max 等
        llm_params={"temperature": 0.3},
        semaphore=8,
        timeout=300,
    ),

    # 3. 文件处理相关
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
    oxy.StdioMCPClient(
        name="pdf_tools",
        params={"command": "python", "args": ["mcp_servers/pdf_tools.py"]},
        description="提取PDF文本内容和统计图片数量"
    ),
    oxy.StdioMCPClient(
        name="video_tools",
        params={"command": "python", "args": ["mcp_servers/video_tools.py"]},
        description="处理视频文件，获取时长、提取帧等"
    ),
    oxy.StdioMCPClient(
        name="media_tools",
        params={"command": "python", "args": ["mcp_servers/media_tools.py"]},
        description="处理音频文件，获取时长和提取文本"
    ),

    # 4. 主要文件处理智能体
    oxy.ReActAgent(
        name="multi_format_agent",
        llm_model="default_llm",
        tools=["file_tools", "multi_format_qa_tools", "pdf_tools", "video_tools", "media_tools"],
        desc="处理所有文件相关问题，基于文件内容回答",
        additional_prompt="""
请按以下规则回答：
1. 优先使用 multi_format_qa_tools 处理文件问答；
2. 对于特定文件类型，可以按需使用对应的专用工具；
3. 严格按格式要求输出（如阿拉伯数字、小写英文）；
4. 如果无法从文件中找到确切答案，基于相关知识给出合理答案；
5. 不要输出"Not found in file"，直接给出基于知识的最佳答案；
6. 答案仅含核心信息，无多余描述，不包含换行符，仅占一行；
7. 不要包含"数据来源"等说明性文字。
"""
    ),

    # 5. 其他工具
    oxy.StdioMCPClient(
        name="web_tools",
        params={"command": "python", "args": ["mcp_servers/web_tools.py"]},
        description="获取网页内容，特别是京东商品信息"
    ),
    oxy.StdioMCPClient(
        name="github_tools",
        params={"command": "python", "args": ["mcp_servers/github_tools.py"]},
        description="获取GitHub仓库信息、发布版本和issues"
    ),

    # 6. 增强版外部搜索工具（集成百度API）
    oxy.StdioMCPClient(
        name="external_search_tools",
        params={"command": "python", "args": ["mcp_servers/external_search_tools.py"]},
        description="增强版外部搜索工具，集成百度API实时搜索和数据分析"
    ),

    # 7. 其他功能智能体
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
        4. 不要包含"数据来源"等说明性文字
        """
    ),
    oxy.ReActAgent(
        name="github_agent",
        llm_model="default_llm",
        tools=["github_tools"],
        desc="处理GitHub相关查询，如版本、issues等"
    ),

    # 8. 增强版外部搜索智能体
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
    5. 不要包含"数据来源"等说明性文字
    6. 答案格式简洁明了，不包含换行符
    """
    ),
    oxy.ReActAgent(
        name="chat_gpt",
        llm_model="default_llm",
        desc="处理普通对话、常识问答等无文件/无链接的任务，基于知识给出合理答案",
        additional_prompt="基于相关知识给出最佳答案，不要输出Not found，答案不包含换行符，仅占一行，不要包含数据来源等说明性文字"
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

    # 9. 意图识别智能体（核心调度逻辑）
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
7. 涉及网络搜索、实时数据、增长数据→优先["external_search_agent"]；
8. 其他情况→["chat_gpt"]；
9. 仅输出智能体名称列表，无其他文字（如 ["multi_format_agent"]）。
注意：所有文件处理问题都使用 multi_format_agent，它会自动处理路径和内容解析。
"""
    ),

    # 10. 主智能体（调度中心）
    oxy.ReActAgent(
        is_master=True,
        name="master_agent",
        llm_model="default_llm",
        sub_agents=["chat_gpt", "multi_format_agent", "time_agent", "delivery_agent",
                    "inventory_agent", "intent_agent", "web_agent", "github_agent",
                    "external_search_agent"],
        func_workflow=master_workflow,
        additional_prompt="通过 intent_agent 识别用户意图，优先使用external_search_agent获取实时数据，如果无法获取具体信息则基于知识给出合理答案，汇总结果后按要求格式输出，答案不包含换行符，仅占一行，不要包含数据来源等说明性文字"
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

                    # 处理文件路径（保持原有逻辑）
                    if file_name:
                        if file_name.startswith('[') and file_name.endswith(']'):
                            full_query = f"""
任务信息：
- 文件列表：{file_name}
- 问题：{query}
回答规则：
1. 基于所有文件内容综合分析回答；
2. 严格按格式要求输出；
3. 如果无法从文件中找到确切答案，基于相关知识给出合理答案；
4. 答案仅含核心信息，无多余文字，不包含换行符，仅占一行；
5. 不要包含"数据来源"等说明性文字。
"""
                        else:
                            full_file_path = str(Path(TEST_DIR_ABS) / file_name) if file_name else ""
                            full_query = f"""
任务信息：
- 文件路径：{full_file_path}
- 问题：{query}
回答规则：
1. 优先基于文件内容回答；
2. 严格按格式要求输出；
3. 如果无法从文件中找到确切答案，基于相关知识给出合理答案；
4. 答案仅含核心信息，无多余文字，不包含换行符，仅占一行；
5. 不要包含"数据来源"等说明性文字。
"""
                    else:
                        full_query = f"""
任务信息：
- 问题：{query}
回答规则：
1. 优先使用百度API搜索获取实时数据；
2. 如果搜索工具无法获取信息，基于相关知识给出合理答案；
3. 严格按格式要求输出；
4. 答案不包含换行符，仅占一行；
5. 不要包含"数据来源"等说明性文字。
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

                    # 🔧 增强版智能提取核心答案
                    core_answer = extract_core_answer(clean_result, query)

                    # 判断是否应该使用提取的答案
                    if should_use_extracted_answer(clean_result, core_answer, query):
                        clean_result = core_answer

                    # 移除数据来源等说明性文字
                    clean_result = re.sub(r'数据来源[^。]*[。]?', '', clean_result)
                    clean_result = re.sub(r'来源[^。]*[。]?', '', clean_result)
                    clean_result = re.sub(r'基于[^。]*[。]?', '', clean_result)
                    clean_result = re.sub(r'根据[^。]*[。]?', '', clean_result)

                    # 移除请求文件路径的提示信息（保持原有逻辑）
                    path_request_patterns = [
                        r'请提供.*文件路径.*',
                        r'我需要您提供.*',
                        r'您提供的文件路径.*',
                        r'请确认.*文件路径.*',
                        r'请问您能提供.*',
                        r'您提到的文件路径.*',
                        r'请提供正确的.*',
                        r'我需要您提供PDF文件的完整路径.*',
                        r'您提供的文件路径test.*',
                        r'请提供您要分析的视频文件的具体路径.*',
                        r'请提供订单ID.*',
                        r'请提供您希望搜索的时间范围.*',
                        r'请确认项目名称.*',
                        r'请问您具体指的是哪个.*',
                        r'请问您知道.*具体发布日期吗.*',
                        r'请问您能提供.*注册地址信息吗.*',
                        r'请提供图片文件.*'
                    ]

                    for pattern in path_request_patterns:
                        clean_result = re.sub(pattern, '', clean_result, flags=re.IGNORECASE)

                    # 清理多余的空格和标点
                    clean_result = re.sub(r'\s+', ' ', clean_result).strip()
                    clean_result = re.sub(r'^[，。、；]', '', clean_result)
                    clean_result = re.sub(r'[，。、；]$', '', clean_result)

                    # 检查是否是错误或未找到的信息
                    if (("not found" in clean_result.lower() or
                         "无法获取" in clean_result or
                         "搜索失败" in clean_result or
                         "error" in clean_result.lower() or
                         len(clean_result.strip()) == 0) and
                            len(clean_result) < 50):
                        clean_result = "Not found"
                    elif "not found in file" in clean_result.lower():
                        clean_result = "Not found"

                    # 提取格式要求并优化输出
                    format_match = re.search(r"请用(\w+.*?)(回答|输出)", query)
                    format_req = format_match.group(1).strip() if format_match else "plain text"

                    if "阿拉伯数字" in format_req:
                        num_match = re.search(r"\d+", clean_result)
                        if num_match:
                            clean_result = num_match.group()
                        else:
                            clean_result = "Not found"
                    elif "小写英文" in format_req:
                        clean_result = clean_result.lower()
                        color_match = re.search(
                            r"(red|blue|green|yellow|black|white|gray|grey|purple|orange|brown|pink|cyan|magenta)",
                            clean_result)
                        if color_match:
                            clean_result = color_match.group()
                        else:
                            clean_result = clean_result.lower()
                    elif "英文大写" in format_req or "大写英文" in format_req:
                        # 确保英文大写
                        clean_result = clean_result.upper()
                        # 提取核心大写单词
                        uppercase_words = re.findall(r'\b[A-Z][A-Z]+\b', clean_result)
                        if uppercase_words:
                            clean_result = max(uppercase_words, key=len)
                    elif "文本" in format_req:
                        clean_result = re.sub(r"\s+", " ", clean_result)[:200]

                    # 最终清理：移除可能的错误提示但保留有用内容
                    final_clean = re.sub(r'(以上信息仅供参考|建议.*?获取|搜索.*?失败|无法.*?获取)[^.]*\.?', '',
                                         clean_result)
                    if final_clean.strip():
                        clean_result = final_clean.strip()

                    # 如果清理后结果为空，设置为Not found
                    if not clean_result.strip():
                        clean_result = "Not found"

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
                    error_str = str(e)[:100]
                    safe_error_str = re.sub(r'["\'\n\r\t\\]', ' ', error_str)
                    safe_error_str = re.sub(r'\s+', ' ', safe_error_str).strip()
                    error_msg = f"Error: {safe_error_str}" if safe_error_str else "Error: Unknown error"
                    all_results.append({
                        "task_id": f"error_task_{task_idx}",
                        "answer": error_msg
                    })
                    print(f"❌ Task {task_idx} failed: {str(e)[:50]}...")

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