# mcp_service/file_tools/text_tools.py
from pathlib import Path
from typing import Dict, Any
from mcp.server.fastmcp import FastMCP
import re
import json
mcp = FastMCP()

# 项目路径配置
# 🔧 与 multi_file_tools_server.py 保持一致的路径定义
PROJECT_ROOT = r"/Users/dengken/Desktop/数据挖掘比赛/compete"
TEST_DIR = r"/Users/dengken/Desktop/数据挖掘比赛/compete/OxyGent-main/test"


@mcp.tool(description="读取 TXT 文件内容并截断超过 10000 字符")
def handle_txt(file_path: str) -> Dict[str, Any]:
    """
    读取 TXT 文件的前 10000 字符内容。
    返回字典，包括：
    - file: 文件路径
    - type: 文件类型
    - llm_input: 可供 LLM 使用的文本
    - error: 错误信息（如果有）
    """
    path = Path(file_path)
    result = {"file": str(path), "type": "text", "llm_input": None, "error": None}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read(10000)
            if len(text) >= 10000:
                text += "\n...[Truncated: over 10000 characters]"
            result["llm_input"] = text
    except Exception as e:
        result["error"] = f"TXT read error: {str(e)}"
    return result

# ✅ 新增路径调试接口
@mcp.tool(description="调试 TXT 文件路径解析")
def debug_txt_path(file_input: str) -> Dict[str, Any]:
    """
    调试 TXT 文件路径解析，将文件解析到 TEST_DIR 或 PROJECT_ROOT。
    """
    # 解析列表格式 ['file1.txt','file2.txt']
    if file_input.startswith('[') and file_input.endswith(']'):
        try:
            file_list = json.loads(file_input.replace("'", '"'))
            if file_list and len(file_list) > 0:
                file_input = file_list[0]
        except Exception:
            file_input = re.sub(r"['\"\[\]]", "", file_input)
    else:
        file_input = re.sub(r"['\"\[\]]", "", file_input)

    test_dir_path = Path(TEST_DIR) / file_input
    project_root_path = Path(PROJECT_ROOT) / file_input
    test_dir_path = test_dir_path.resolve()
    project_root_path = project_root_path.resolve()

    recommended_path = test_dir_path if test_dir_path.exists() else project_root_path

    return {
        "cleaned_filename": file_input,
        "test_dir_path": str(test_dir_path),
        "test_dir_exists": test_dir_path.exists(),
        "project_root_path": str(project_root_path),
        "project_root_exists": project_root_path.exists(),
        "recommended_path": str(recommended_path)
    }


if __name__ == "__main__":
    mcp.run()
