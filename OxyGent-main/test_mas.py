# batch_run.py
import asyncio
import json
from pathlib import Path
import aiohttp

# ----------------------------
# 配置文件
# ----------------------------
MAS_URL = "http://127.0.0.1:7860/agent_request"  # MAS Web 服务 URL
TEST_DATA_FILE = "./local_file/test/data.jsonl"
RESULT_FILE = "./result.jsonl"

async def send_request(session, query, agent="multi_intent_agent"):
    """
    发送请求到 MAS Web 服务
    """
    payload = {
        "caller": "user",
        "callee": agent,
        "arguments": {"query": query},
        "request_id": None
    }
    try:
        async with session.post(MAS_URL, json=payload, timeout=30) as resp:
            if resp.status != 200:
                return f"HTTP Error {resp.status}"
            data = await resp.json()
            # MAS 返回的数据可能在 data["output"] 或 data["content"] 中
            return data.get("output") or data.get("content") or str(data)
    except Exception as e:
        return f"Request failed: {e}"


async def main():
    if not Path(TEST_DATA_FILE).exists():
        print(f"测试集文件 {TEST_DATA_FILE} 不存在")
        return

    with open(TEST_DATA_FILE, "r", encoding="utf-8") as f:
        data = [json.loads(line) for line in f]

    print(f"共读取 {len(data)} 条测试任务")

    results = []

    async with aiohttp.ClientSession() as session:
        for item in data:
            task_id = item.get("task_id")
            query = item.get("query")
            if not task_id or not query:
                print(f"跳过无效任务: {item}")
                continue

            answer = await send_request(session, query)
            results.append({"task_id": task_id, "answer": answer})
            print(f"[{task_id}] answer: {answer}")

    # 写入 result.jsonl
    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"生成提交文件: {RESULT_FILE}")

if __name__ == "__main__":
    asyncio.run(main())
