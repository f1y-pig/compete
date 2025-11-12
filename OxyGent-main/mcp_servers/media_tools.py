"""Audio processing tools with path debug."""

import json, re
import eyed3
from pathlib import Path
from mcp.server.fastmcp import FastMCP

mcp = FastMCP()

# 可配置路径
PROJECT_ROOT = r"/Users/dengken/Desktop/数据挖掘比赛/compete"
TEST_DIR = r"/Users/dengken/Desktop/数据挖掘比赛/compete/OxyGent-main/test"

def resolve_file_path(file_input: str) -> Path:
    """根据 TEST_DIR / PROJECT_ROOT 自动选择存在的路径"""
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

@mcp.tool(description="获取音频文件时长(秒)")
def get_audio_duration(audio_path: str) -> str:
    """获取音频时长(秒)"""
    path = resolve_file_path(audio_path)
    try:
        audio = eyed3.load(str(path))
        if audio is None:
            return "Invalid audio file"
        return str(int(audio.info.time_secs))
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool(description="提取音频文本(模拟)")
def extract_audio_text(audio_path: str) -> str:
    """提取音频文本(模拟，实际需语音识别)"""
    path = resolve_file_path(audio_path)
    try:
        # 实际应用中需要集成语音识别API
        return "Audio text extraction not implemented"
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool(description="调试音频文件路径解析")
def debug_audio_path(file_input: str) -> dict:
    """调试音频文件路径"""
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

if __name__ == "__main__":
    mcp.run()
