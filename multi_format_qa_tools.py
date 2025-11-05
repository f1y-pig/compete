# mcp_servers/multi_format_qa_tools.py
"""
统一多格式问答工具：
支持 xlsx/txt/pptx/image/audio/video/pdf，提供标准化 LLM 提示词。
"""
from mcp.server.fastmcp import FastMCP
from pydantic import Field
import json
from multi_file_tools import prepare_file_for_llm

# 初始化 MCP 工具
mcp = FastMCP()


@mcp.tool(description="Answer questions based on xlsx/txt/pptx/image/audio/video/pdf files")
def multi_format_qa(
        file_path: str = Field(description="Full path of the file (e.g., './test/data.xlsx')"),
        question: str = Field(description="Question to answer (e.g., 'What color is the chair in the image?')"),
        format_req: str = Field(description="Answer format (e.g., 'lowercase English', 'Arabic numerals')")
) -> dict:
    """
    核心功能：
    1. 调用 multi_file_tools 解析文件；
    2. 根据文件类型构建针对性提示词；
    3. 返回提示词给 LLM 生成答案。
    """
    # 1. 解析文件内容
    file_info = prepare_file_for_llm(file_path)
    if "error" in str(file_info["llm_input"]):
        return {"error": file_info["llm_input"], "prompt_for_llm": ""}

    # 2. 根据文件类型构建提示词内容
    file_type = file_info["type"]
    content_preview = ""

    # 不同格式的内容预览模板
    if file_type == "text":
        content_preview = f"TXT Content (first 10000 chars):\n{file_info['llm_input'][:500]}..."
    elif file_type == "excel":
        content_preview = f"Excel Data (first 5 rows):\n{json.dumps(file_info['llm_input'][:5], indent=2)}..."
    elif file_type == "pptx":
        content_preview = f"PPTX Info: {json.dumps(file_info['llm_input']['pptx_info'], indent=2)}\nSlide 1-3 Content: {json.dumps(file_info['llm_input']['slide_content'][:3], indent=2)}..."
    elif file_type == "image":
        content_preview = f"Image Info: {json.dumps(file_info['llm_input']['image_info'], indent=2)}\nImage is encoded in Base64 (analyze visual content to answer the question)."
    elif file_type == "audio":
        content_preview = f"Audio Info: {json.dumps(file_info['llm_input']['audio_info'], indent=2)}\nAudio is encoded in Base64 (analyze audio content to answer the question)."
    elif file_type == "video":
        content_preview = f"Video Info: {json.dumps(file_info['llm_input']['video_info'], indent=2)}\nKey Frames (5 frames max) encoded in Base64 (analyze visual content)."
    elif file_type == "pdf":
        content_preview = f"PDF Text (first 1000 chars):\n{file_info['llm_input'][:1000]}..."
    else:
        content_preview = f"Unsupported file type: {file_type}"

    # 3. 构建 LLM 提示词（强调格式要求）
    prompt = f"""
    You are a multi-format file analysis expert. Follow these rules strictly:

    1. File Information:
       - File Path: {file_path}
       - File Type: {file_type}
       - Content Preview:
         {content_preview}

    2. Task:
       - Question: {question}
       - Answer Format Requirement: {format_req}

    3. Critical Rules:
       a. Only use information from the file (NO external knowledge);
       b. Answer in the required format exactly (e.g., 'red' not 'Red', '5' not 'five');
       c. If the answer is not in the file, return "Not found in file";
       d. No extra text (e.g., no explanations, only the answer itself).
    """

    # 返回提示词和文件信息
    return {
        "prompt_for_llm": prompt,
        "file_type": file_type,
        "is_valid_file": True,
        "content_preview_length": len(str(content_preview))
    }


# -------------------------- 工具启动入口 --------------------------
if __name__ == "__main__":
    print("🚀 Starting Multi-Format QA Tool (MCP Server)...")
    print("Listening for requests...")
    mcp.run()  # 启动 MCP 服务，等待调用