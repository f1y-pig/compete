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
    """基于任何支持的文件回答问题"""
    print(f"📁 原始文件路径：{file_path}")

    # 修复：正确处理列表格式 ['file1.pptx', 'file2.pptx']
    if file_path.startswith('[') and file_path.endswith(']'):
        try:
            # 安全解析JSON列表
            file_list = json.loads(file_path.replace("'", '"'))
            if file_list and len(file_list) > 0:
                # 取第一个文件名（不包含路径符号）
                file_path = file_list[0]
                print(f"🔧 从列表提取文件名：{file_path}")
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析错误：{e}")
            # 如果JSON解析失败，使用字符串清理
            file_path = re.sub(r"['\"\[\]]", "", file_path)
    else:
        # 清理可能的引号和括号
        file_path = re.sub(r"['\"\[\]]", "", file_path)

    # 现在 file_path 应该是干净的文件名，如 "kadj4.mp4"
    print(f"🔧 清理后文件名：{file_path}")

    # 构建相对路径（基于TEST_DIR）
    absolute_path = os.path.join(TEST_DIR, file_path)
    absolute_path = os.path.normpath(absolute_path)

    print(f"📍 构建的绝对路径：{absolute_path}")
    print(f"📊 文件是否存在：{os.path.exists(absolute_path)}")

    # 如果文件不存在，尝试在项目根目录查找
    if not os.path.exists(absolute_path):
        # 备选路径：在项目根目录中查找
        alternative_path = os.path.join(PROJECT_ROOT, file_path)
        alternative_path = os.path.normpath(alternative_path)

        if os.path.exists(alternative_path):
            absolute_path = alternative_path
            print(f"🔄 使用备选路径：{absolute_path}")
        else:
            return {
                "error": f"文件不存在。尝试的路径：\n- {absolute_path}\n- {alternative_path}",
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
    print(f"📁 多文件原始路径：{file_list}")

    try:
        # 修复：正确解析文件列表
        if file_list.startswith('[') and file_list.endswith(']'):
            files = json.loads(file_list.replace("'", '"'))
        else:
            # 如果不是列表格式，尝试清理后作为单个文件
            files = [re.sub(r"['\"\[\]]", "", file_list)]

        print(f"🔧 解析后的文件列表：{files}")

        file_contents = {}

        for file_name in files:
            # 清理文件名（确保没有多余的符号）
            clean_file_name = re.sub(r"['\"\[\]]", "", file_name)

            # 构建基于TEST_DIR的相对路径
            absolute_path = os.path.join(TEST_DIR, clean_file_name)
            absolute_path = os.path.normpath(absolute_path)

            print(f"🔧 处理文件：{clean_file_name}")
            print(f"📍 绝对路径：{absolute_path}")

            if os.path.exists(absolute_path):
                file_info = prepare_file_for_llm(absolute_path)
                if not file_info.get("error"):
                    file_contents[clean_file_name] = {
                        "type": file_info["type"],
                        "content": file_info.get("llm_input", file_info.get("content", ""))
                    }
                else:
                    file_contents[clean_file_name] = {
                        "type": "error",
                        "content": f"Error: {file_info['error']}"
                    }
            else:
                # 尝试在项目根目录查找
                alternative_path = os.path.join(PROJECT_ROOT, clean_file_name)
                alternative_path = os.path.normpath(alternative_path)

                if os.path.exists(alternative_path):
                    file_info = prepare_file_for_llm(alternative_path)
                    if not file_info.get("error"):
                        file_contents[clean_file_name] = {
                            "type": file_info["type"],
                            "content": file_info.get("llm_input", file_info.get("content", ""))
                        }
                    else:
                        file_contents[clean_file_name] = {
                            "type": "error",
                            "content": f"Error: {file_info['error']}"
                        }
                else:
                    file_contents[clean_file_name] = {
                        "type": "error",
                        "content": f"File not found. Tried: {absolute_path}, {alternative_path}"
                    }

        # 检查是否有有效文件
        valid_files = [name for name, info in file_contents.items() if info.get("type") != "error"]
        is_valid = len(valid_files) > 0

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
            "valid_files": valid_files,
            "is_valid_file": is_valid
        }

    except Exception as e:
        return {
            "error": f"多文件处理错误: {str(e)}",
            "prompt_for_llm": "",
            "is_valid_file": False
        }


# 添加路径调试工具（可选）
@mcp.tool(description="Debug file path resolution")
def debug_file_path(file_input: str = Field(..., description="文件路径输入")):
    """调试文件路径解析"""
    print(f"🔍 调试输入：{file_input}")

    # 测试路径解析逻辑
    test_path = file_input

    # 解析列表格式
    if test_path.startswith('[') and test_path.endswith(']'):
        try:
            file_list = json.loads(test_path.replace("'", '"'))
            if file_list and len(file_list) > 0:
                test_path = file_list[0]
                print(f"✅ 解析列表成功：{test_path}")
        except json.JSONDecodeError as e:
            print(f"❌ 列表解析失败：{e}")
            test_path = re.sub(r"['\"\[\]]", "", test_path)
    else:
        test_path = re.sub(r"['\"\[\]]", "", test_path)

    print(f"🔧 清理后文件名：{test_path}")

    # 构建路径
    test_dir_path = os.path.join(TEST_DIR, test_path)
    project_root_path = os.path.join(PROJECT_ROOT, test_path)

    test_dir_path = os.path.normpath(test_dir_path)
    project_root_path = os.path.normpath(project_root_path)

    return {
        "cleaned_filename": test_path,
        "test_dir_path": test_dir_path,
        "test_dir_exists": os.path.exists(test_dir_path),
        "project_root_path": project_root_path,
        "project_root_exists": os.path.exists(project_root_path),
        "recommended_path": test_dir_path if os.path.exists(test_dir_path) else project_root_path
    }


if __name__ == "__main__":
    print("Starting Multi-Format QA Tool (MCP Server)...")
    print(f"项目根目录: {PROJECT_ROOT}")
    print(f"测试目录: {TEST_DIR}")
    mcp.run()