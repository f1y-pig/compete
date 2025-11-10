from mcp.server.fastmcp import FastMCP
from pydantic import Field
from multi_file_tools_server import prepare_file_for_llm  # 引入统一文件解析
import json
import re
import os

mcp = FastMCP()

# 项目根目录和测试目录的绝对路径
PROJECT_ROOT = r"E:\大三大四\compete\compete"
TEST_DIR = r"E:\大三大四\compete\compete\OxyGent-main\test"


@mcp.tool(description="Answer questions based on any supported file")
def multi_format_qa(
        file_path: str = Field(..., description="文件路径"),
        question: str = Field(..., description="问题"),
        format_req: str = Field(..., description="答案格式要求")
):
    # -------------------------- 关键修复：处理文件路径 --------------------------
    # 处理多种可能的文件路径格式：
    # 1. 格式：['file1.pptx', 'file2.pptx'] (从data.jsonl读取的列表格式)
    # 2. 格式：test['file1.pptx'] (相对路径格式)
    # 3. 直接的文件名

    print(f"📁 原始文件路径：{file_path}")  # 调试日志

    # 如果是列表格式 ['file1.pptx', 'file2.pptx']
    if file_path.startswith('[') and file_path.endswith(']'):
        try:
            # 解析JSON列表
            file_list = json.loads(file_path.replace("'", '"'))
            # 对于多文件问题，我们只处理第一个文件，或者需要特殊处理
            if len(file_list) > 0:
                file_path = file_list[0]  # 先处理第一个文件
        except:
            # 如果JSON解析失败，使用字符串处理
            file_path = re.sub(r"['\"\[\]]", "", file_path)

    # 清理路径中的特殊字符
    cleaned_path = re.sub(r"['\"\[\]]", "", file_path)

    # 构建绝对路径
    if os.path.isabs(cleaned_path):
        # 如果已经是绝对路径，直接使用
        absolute_path = cleaned_path
    else:
        # 如果是相对路径，基于测试目录构建绝对路径
        absolute_path = os.path.join(TEST_DIR, cleaned_path)

    # 规范化路径
    absolute_path = os.path.normpath(absolute_path)

    print(f"🔧 清洗后路径：{cleaned_path}")  # 调试日志
    print(f"📍 绝对路径：{absolute_path}")  # 调试日志
    print(f"📊 文件是否存在：{os.path.exists(absolute_path)}")  # 调试日志

    # 检查文件是否存在
    if not os.path.exists(absolute_path):
        return {
            "error": f"文件不存在: {absolute_path}",
            "prompt_for_llm": "",
            "file_type": "unknown",
            "is_valid_file": False
        }

    # 调用 file_tools 的解析函数（使用绝对路径）
    file_info = prepare_file_for_llm(absolute_path)

    if file_info.get("error"):
        return {
            "error": file_info["error"],
            "prompt_for_llm": "",
            "file_type": file_info.get("type", "unknown"),
            "is_valid_file": False
        }

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


@mcp.tool(description="Handle multiple files for complex questions")
def multi_file_qa(
        file_list: str = Field(..., description="文件列表，格式为 ['file1.pptx', 'file2.pptx']"),
        question: str = Field(..., description="涉及多个文件的问题"),
        format_req: str = Field(..., description="答案格式要求")
):
    """处理涉及多个文件的问题"""

    print(f"📁 多文件原始路径：{file_list}")  # 调试日志

    try:
        # 解析文件列表
        if file_list.startswith('[') and file_list.endswith(']'):
            files = json.loads(file_list.replace("'", '"'))
        else:
            files = [file_list]

        file_contents = {}

        for file_name in files:
            # 构建绝对路径
            if os.path.isabs(file_name):
                absolute_path = file_name
            else:
                absolute_path = os.path.join(TEST_DIR, file_name)

            absolute_path = os.path.normpath(absolute_path)

            print(f"🔧 处理文件：{file_name}")  # 调试日志
            print(f"📍 绝对路径：{absolute_path}")  # 调试日志

            if os.path.exists(absolute_path):
                file_info = prepare_file_for_llm(absolute_path)
                if not file_info.get("error"):
                    file_contents[file_name] = {
                        "type": file_info["type"],
                        "content": file_info.get("llm_input", file_info.get("content", ""))
                    }
                else:
                    file_contents[file_name] = {
                        "type": "error",
                        "content": f"Error: {file_info['error']}"
                    }
            else:
                file_contents[file_name] = {
                    "type": "error",
                    "content": f"File not found: {absolute_path}"
                }

        # 生成多文件提示词
        prompt = f"""
You are a multi-format file analysis expert handling multiple files.

Files Information:
{json.dumps(file_contents, indent=2, ensure_ascii=False)}

Question: {question}
Answer Format Requirement: {format_req}

Rules:
1. Analyze information across all provided files.
2. Answer strictly in the required format.
3. If information is not found in any file, return 'Not found in files'.
4. No extra text.
"""

        return {
            "prompt_for_llm": prompt,
            "file_count": len(files),
            "processed_files": list(file_contents.keys()),
            "is_valid_file": True
        }

    except Exception as e:
        return {
            "error": f"多文件处理错误: {str(e)}",
            "prompt_for_llm": "",
            "is_valid_file": False
        }


if __name__ == "__main__":
    print("Starting Multi-Format QA Tool (MCP Server)...")
    mcp.run()