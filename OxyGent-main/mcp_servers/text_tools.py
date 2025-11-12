from pathlib import Path
from typing import Dict, Any
import json, re

# 可配置路径
PROJECT_ROOT = r"/Users/dengken/Desktop/数据挖掘比赛/compete"
TEST_DIR = r"/Users/dengken/Desktop/数据挖掘比赛/compete/OxyGent-main/test"

def resolve_file_path(file_input: str) -> Path:
    """根据 TEST_DIR / PROJECT_ROOT 自动选择存在的路径"""
    # 清理输入
    if file_input.startswith('[') and file_input.endswith(']'):
        try:
            file_list = json.loads(file_input.replace("'", '"'))
            file_input = file_list[0] if file_list else ''
        except json.JSONDecodeError:
            file_input = re.sub(r"['\"\[\]]", "", file_input)
    else:
        file_input = re.sub(r"['\"\[\]]", "", file_input)

    test_dir_path = Path(TEST_DIR) / file_input
    project_root_path = Path(PROJECT_ROOT) / file_input
    recommended_path = test_dir_path if test_dir_path.exists() else project_root_path
    return recommended_path.resolve()

def handle_txt(file_path: str) -> Dict[str, Any]:
    """读取 TXT 文件内容，并限制长度"""
    path = resolve_file_path(file_path)
    result = {"file": str(path), "type": "text", "llm_input": None, "error": None}
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read(10000)
            if len(text) >= 10000:
                text += "\n...[Truncated: over 10000 characters]"
            result["llm_input"] = text
    except Exception as e:
        result["error"] = f"TXT read error: {str(e)}"
    return result

def debug_txt_path(file_input: str) -> dict:
    """调试 TXT 文件路径解析"""
    if file_input.startswith('[') and file_input.endswith(']'):
        try:
            file_list = json.loads(file_input.replace("'", '"'))
            file_input = file_list[0] if file_list else ''
        except json.JSONDecodeError:
            file_input = re.sub(r"['\"\[\]]", "", file_input)
    else:
        file_input = re.sub(r"['\"\[\]]", "", file_input)

    test_dir_path = (Path(TEST_DIR) / file_input).resolve()
    project_root_path = (Path(PROJECT_ROOT) / file_input).resolve()
    recommended_path = test_dir_path if test_dir_path.exists() else project_root_path

    return {
        "cleaned_filename": file_input,
        "test_dir_path": str(test_dir_path),
        "test_dir_exists": test_dir_path.exists(),
        "project_root_path": str(project_root_path),
        "project_root_exists": project_root_path.exists(),
        "recommended_path": str(recommended_path)
    }
