from mcp.server.fastmcp import FastMCP
from pydantic import Field
from multi_file_tools_server import prepare_file_for_llm  # 引入统一文件解析

import json

mcp = FastMCP()

@mcp.tool(description="Answer questions based on any supported file")
def multi_format_qa(
        file_path: str = Field(..., description="文件路径"),
        question: str = Field(..., description="问题"),
        format_req: str = Field(..., description="答案格式要求")
):
    # 调用 file_tools 的解析函数
    file_info = prepare_file_for_llm(file_path)

    if file_info.get("error"):
        return {"error": file_info["error"], "prompt_for_llm": ""}

    file_type = file_info["type"]

    # 根据文件类型生成提示词
    content_preview = ""
    if file_type in ["text", "pdf"]:
        content_preview = file_info.get("llm_input", "")[:1000]
    elif file_type == "excel":
        content_preview = json.dumps(file_info.get("content", [])[:5], indent=2)
    elif file_type == "pptx":
        content_preview = json.dumps(file_info.get("llm_input", {}), indent=2)
    elif file_type in ["image", "audio", "video"]:
        content_preview = json.dumps(file_info.get("llm_input", {}), indent=2)
    else:
        content_preview = "Unsupported file type"

    prompt = f"""
You are a multi-format file analysis expert.
File Type: {file_type}
File Preview: {content_preview}
Question: {question}
Answer Format Requirement: {format_req}
Rules:
1. Only use information from the file.
2. Answer strictly in the required format.
3. If not found, return 'Not found in file'.
4. No extra text.
"""

    return {
        "prompt_for_llm": prompt,
        "file_type": file_type,
        "is_valid_file": True
    }

if __name__ == "__main__":
    print("Starting Multi-Format QA Tool (MCP Server)...")
    mcp.run()
