import asyncio
import os
import json
import re
from pathlib import Path
from dotenv import load_dotenv
from oxygent import MAS, Config, oxy
<<<<<<< HEAD
from multi_file_tools import prepare_file_for_llm
=======
from mcp_servers.multi_file_tools_server import prepare_file_for_llm
>>>>>>> 4ae3d2f38c74da4ffe036e1ac737de7a33df678d

# -------------------------- 基础配置 --------------------------
load_dotenv(dotenv_path="demo.env")
Config.set_app_name('multi_format_qa_task_v1')
Config.set_agent_llm_model("default_llm")
Config.set_message_is_show_in_terminal(True)  # 显示终端消息

# -------------------------- OxyGent 空间配置 --------------------------
oxy_space = [
    # 1. 大语言模型
    oxy.HttpLLM(
        name="default_llm",
        api_key=os.getenv("DEFAULT_LLM_API_KEY"),
        base_url=os.getenv("DEFAULT_LLM_BASE_URL"),
        model_name=os.getenv("DEFAULT_LLM_MODEL_NAME"),
        llm_params={"temperature": 0.3},
        semaphore=8,
        timeout=300,
    ),

    # 2. 多格式问答工具
    oxy.StdioMCPClient(
        name="multi_format_qa_tools",
        params={
            "command": "uv",
            "args": ["--directory", "./mcp_servers", "run", "multi_format_qa_tools.py"]
        },
    ),

    # 3. 多格式问答智能体（ReActAgent 支持工具调用）
    oxy.ReActAgent(
        name="multi_format_agent",
        llm_model="default_llm",
        tools=["multi_format_qa_tools"],
        additional_prompt="""
        1. 先解析文件内容（调用 multi_format_qa_tools），再回答问题；
        2. 严格按格式要求输出；
        3. 答案仅包含核心信息，无多余描述。
        """,
    ),
]

# -------------------------- 核心任务处理函数 --------------------------
async def process_tasks(test_dir: str = "test", output_file: str = "result.jsonl"):
    data_path = Path(test_dir) / "data.jsonl"
    if not data_path.exists():
        print(f"❌ Error: {data_path} not found.")
        return

    Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    with open(data_path, "r", encoding="utf-8") as f_in, \
         open(output_file, "w", encoding="utf-8") as f_out:

        async with MAS(oxy_space=oxy_space) as mas:
            task_idx = 0
            for line in f_in:
                task_idx += 1
                try:
                    task = json.loads(line.strip())
                    task_id = task.get("task_id", f"task_{task_idx}")
                    query = task.get("query", "")
                    file_name = task.get("file_name", "")

                    # 构建完整查询（逻辑不变）
                    full_file_path = str(Path(test_dir) / file_name) if file_name else ""
                    format_match = re.search(r"请用(\w+.*?)(回答|输出)", query)
                    format_req = format_match.group(1).strip() if format_match else "plain text"

                    full_query = f"""
                    任务信息：
                    - 文件路径：{full_file_path}
                    - 问题：{query}
                    - 输出格式要求：{format_req}
                    回答规则：
                    1. 仅基于文件内容回答；
                    2. 严格按格式要求输出；
                    3. 找不到答案时输出“Not found in file”；
                    4. 答案仅含核心信息。
                    """ if file_name else f"""
                    任务信息：
                    - 问题：{query}
                    - 输出格式要求：{format_req}
                    回答规则：
                    1. 基于常识回答；
                    2. 严格按格式要求输出；
                    3. 找不到答案时输出“Not found”。
                    """

                    # -------------------------- 关键修正：用 chat_with_agent 调用智能体 --------------------------
                    # 按照 MAS 源码要求，构建 payload 并调用正确方法
                    payload = {
                        "query": full_query,
                        "callee": "multi_format_agent"  # 明确指定目标智能体
                    }
                    oxy_response = await mas.chat_with_agent(payload=payload)
                    result = oxy_response.output  # 从响应对象中提取结果
                    clean_result = result.strip()

                    # 格式修正（逻辑不变）
                    if "阿拉伯数字" in format_req:
                        num_match = re.search(r"\d+", clean_result)
                        clean_result = num_match.group() if num_match else "Not found in file"
                    elif "小写英文" in format_req:
                        clean_result = clean_result.lower()
                        color_match = re.search(r"(red|blue|green|yellow|black|white|gray|purple|orange)", clean_result)
                        clean_result = color_match.group() if color_match else "Not found in file"
                    elif "文本" in format_req:
                        clean_result = re.sub(r"\s+", " ", clean_result)[:200]

                    # 写入结果
                    output_json = {"task_id":task_id,"answer":clean_result}
                    f_out.write(json.dumps(output_json, ensure_ascii=False) + "\n")
                    print(f"✅ Processed task {task_idx} (ID: {task_id})")

                except Exception as e:
                    error_msg = f"Error: {str(e)[:100]}"
                    f_out.write(json.dumps({"task_id": f"error_task_{task_idx}", "answer": error_msg}, ensure_ascii=False) + "\n")
                    print(f"❌ Task {task_idx} failed: {str(e)[:50]}...")

    print(f"\n🎉 All tasks processed! Result saved to: {output_file}")

# -------------------------- 主函数 --------------------------
async def main():
    print("⚠️  Please confirm data desensitization is completed.")
    print("1. Run desensitization script:")
    print("   python desensitize_data.py --directory=./cache_dir/local_es_data/ --prefix=multi_format_qa_task_v1")
    print("2. Confirm desensitized files are in: ./cache_dir/local_es_data/local_es_data/")
    input("\nPress Enter to continue...")

    await process_tasks(
        test_dir="test1",
        output_file="result.jsonl"
    )

if __name__ == "__main__":
    asyncio.run(main())