import asyncio
import os
import json
import re
from pathlib import Path
from dotenv import load_dotenv
from oxygent import MAS, Config, oxy
from multi_file_tools import prepare_file_for_llm

# -------------------------- 基础配置 --------------------------
# 加载环境变量（LLM 密钥/地址）
load_dotenv(dotenv_path="demo.env")
# 实验名称配置（每次实验修改，格式：任务编号+版本号）
Config.set_app_name('multi_format_qa_task_v1')
# 设置默认 LLM 模型
Config.set_agent_llm_model("default_llm")

# -------------------------- OxyGent 空间配置（工具+智能体） --------------------------
oxy_space = [
    # 1. 大语言模型（DeepSeek）
    oxy.HttpLLM(
        name="default_llm",
        api_key=os.getenv("DEFAULT_LLM_API_KEY"),
        base_url=os.getenv("DEFAULT_LLM_BASE_URL"),
        model_name=os.getenv("DEFAULT_LLM_MODEL_NAME"),
        llm_params={"temperature": 0.3},  # 低温度=结果更确定
        semaphore=4,  # 并发限制（避免 LLM 限流）
        timeout=300,  # 超时时间（300秒=5分钟，适配多媒体处理）
    ),

    # 2. 统一多格式问答工具（关联 mcp 服务）
    oxy.StdioMCPClient(
        name="multi_format_qa_tools",
        params={
            "command": "uv",
            "args": ["--directory", "./mcp_servers", "run", "multi_format_qa_tools.py"]
        },
    ),

    # 3. 多格式问答智能体（处理所有文件相关任务）
    oxy.ReActAgent(
        name="multi_format_agent",
        desc="Answer questions based on xlsx/txt/pptx/image/audio/video/pdf files",
        tools=["multi_format_qa_tools"],
        additional_prompt="""
        1. 先解析文件内容（调用 multi_format_qa_tools），再回答问题；
        2. 严格按格式要求输出（如“小写英文”“阿拉伯数字”）；
        3. 答案仅包含核心信息，无多余描述（如颜色仅输出 red/blue，数量仅输出 5/10）。
        """,
    ),

    # 4. 主智能体（调度中心）
    oxy.ReActAgent(
        is_master=True,
        name="master_agent",
        sub_agents=["multi_format_agent"],
        additional_prompt="所有任务均调用 multi_format_agent 处理，无需其他智能体。",
    ),
]

# -------------------------- 核心任务处理函数 --------------------------
async def process_tasks(test_dir: str = "test", output_file: str = "result.jsonl"):
    """
    处理流程：
    1. 读取 test/data.jsonl 中的任务；
    2. 解析关联文件（如有）；
    3. 调用智能体生成答案；
    4. 输出 result.jsonl（仅含 task_id 和 answer）。
    """
    # 检查输入文件是否存在
    data_path = Path(test_dir) / "data.jsonl"
    if not data_path.exists():
        print(f"❌ Error: {data_path} not found. Please check the path.")
        return

    # 创建输出目录（如不存在）
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    # 读取任务并处理
    with open(data_path, "r", encoding="utf-8") as f_in, \
         open(output_file, "w", encoding="utf-8") as f_out:

        async with MAS(oxy_space=oxy_space) as mas:
            task_idx = 0
            for line in f_in:
                task_idx += 1
                try:
                    # 解析单条任务
                    task = json.loads(line.strip())
                    task_id = task.get("task_id", f"task_{task_idx}")
                    query = task.get("query", "")
                    file_name = task.get("file_name", "")

                    # 1. 构建文件路径和格式要求
                    full_file_path = str(Path(test_dir) / file_name) if file_name else ""
                    # 提取问题中的格式要求（如“小写英文”“阿拉伯数字”）
                    format_match = re.search(r"请用(\w+.*?)(回答|输出)", query)
                    format_req = format_match.group(1).strip() if format_match else "plain text"

                    # 2. 构建完整查询（传递文件路径+问题+格式要求）
                    if file_name:
                        full_query = f"""
                        任务信息：
                        - 文件路径：{full_file_path}
                        - 问题：{query}
                        - 输出格式要求：{format_req}
                        回答规则：
                        1. 仅基于文件内容回答，不使用外部知识；
                        2. 严格按格式要求输出（如小写英文、纯阿拉伯数字）；
                        3. 找不到答案时输出“Not found in file”；
                        4. 答案仅含核心信息，无多余文字（如颜色仅输出单词，数量仅输出数字）。
                        """
                    else:
                        full_query = f"""
                        任务信息：
                        - 问题：{query}
                        - 输出格式要求：{format_req}
                        回答规则：
                        1. 基于常识回答（无文件时）；
                        2. 严格按格式要求输出；
                        3. 找不到答案时输出“Not found”。
                        """

                    # 3. 调用智能体生成答案
                    result = await mas.query(full_query, agent_name="multi_format_agent")
                    clean_result = result.strip()

                    # 4. 强制格式修正（确保符合要求）
                    if "阿拉伯数字" in format_req:
                        # 提取纯数字（如“5人”→“5”）
                        num_match = re.search(r"\d+", clean_result)
                        clean_result = num_match.group() if num_match else "Not found in file"
                    elif "小写英文" in format_req:
                        # 转为小写并提取核心词（如“Red Chair”→“red”）
                        clean_result = clean_result.lower()
                        # 匹配常见颜色（可扩展）
                        color_match = re.search(r"(red|blue|green|yellow|black|white|gray|purple|orange)", clean_result)
                        clean_result = color_match.group() if color_match else "Not found in file"
                    elif "文本" in format_req:
                        # 去除多余空格和换行
                        clean_result = re.sub(r"\s+", " ", clean_result)[:200]  # 限制长度

                    # 5. 写入结果文件（仅保留 task_id 和 answer）
                    output_json = {
                        "task_id": task_id,
                        "answer": clean_result
                    }
                    f_out.write(json.dumps(output_json, ensure_ascii=False) + "\n")
                    print(f"✅ Processed task {task_idx} (ID: {task_id}) | File: {file_name or 'No file'}")

                except json.JSONDecodeError:
                    error_msg = "Error: Invalid JSON format"
                    f_out.write(json.dumps({"task_id": f"invalid_task_{task_idx}", "answer": error_msg}, ensure_ascii=False) + "\n")
                    print(f"❌ Task {task_idx} failed: Invalid JSON")
                except Exception as e:
                    error_msg = f"Error: {str(e)[:100]}"  # 限制错误信息长度
                    f_out.write(json.dumps({"task_id": f"error_task_{task_idx}", "answer": error_msg}, ensure_ascii=False) + "\n")
                    print(f"❌ Task {task_idx} failed: {str(e)[:50]}...")

    print(f"\n🎉 All tasks processed! Result saved to: {output_file}")

# -------------------------- 主函数（启动入口） --------------------------
async def main():
    # 提示用户先执行脱敏处理（按实验要求）
    print("⚠️  Please confirm you have completed data desensitization:")
    print("1. Run desensitization script:")
    print("   python desensitize_data.py --directory=./cache_dir/local_es_data/ --prefix=multi_format_qa_task_v1")
    print("2. Confirm desensitized files are in: ./cache_dir/local_es_data/local_es_data/")
    input("\nPress Enter to continue...")

    # 启动任务处理
    await process_tasks(
        test_dir="test",  # 测试数据目录（含 data.jsonl 和关联文件）
        output_file="result.jsonl"  # 输出结果文件
    )

if __name__ == "__main__":
    asyncio.run(main())