from pathlib import Path
import base64
import wave
import mutagen
from typing import Dict, Any
import os
from mcp.server.fastmcp import FastMCP

mcp = FastMCP()

# 🔧 与 multi_file_tools_server.py 保持一致的路径定义
PROJECT_ROOT = r"/Users/dengken/Desktop/数据挖掘比赛/compete"
TEST_DIR = r"/Users/dengken/Desktop/数据挖掘比赛/compete/OxyGent-main/test"

def _resolve_file_path(file_path: str) -> Path:
    """
    自动在 TEST_DIR / PROJECT_ROOT 中寻找文件。
    """
    path = Path(file_path)
    if not path.is_absolute():
        test_path = Path(TEST_DIR) / path
        project_path = Path(PROJECT_ROOT) / path
        if test_path.exists():
            return test_path
        elif project_path.exists():
            return project_path
        else:
            return path
    return path


@mcp.tool(description="读取音频文件信息并编码为 Base64")
def handle_audio(file_path: str) -> Dict[str, Any]:
    """
    读取音频文件信息，包括 WAV 或 MP3。
    返回字典，包括：
    - file: 文件路径
    - type: 文件类型
    - llm_input: 包含音频信息和 Base64 编码
    - error: 错误信息（如果有）
    """
    path = _resolve_file_path(file_path)
    result = {
        "file": str(path),
        "type": "audio",
        "llm_input": None,
        "error": None
    }

    if not path.exists():
        result["error"] = f"Audio file not found -> {path}"
        return result

    try:
        audio_info = {}
        if path.suffix.lower() == ".wav":
            with wave.open(path, "rb") as wf:
                audio_info["channels"] = wf.getnchannels()
                audio_info["sample_rate"] = wf.getframerate()
                audio_info["duration_second"] = round(wf.getnframes() / wf.getframerate(), 1)
                audio_info["file_format"] = "WAV"
        elif path.suffix.lower() == ".mp3":
            mp3 = mutagen.File(path)
            audio_info["duration_second"] = round(mp3.info.length, 1)
            audio_info["bitrate_kbps"] = mp3.info.bitrate // 1000
            audio_info["file_format"] = "MP3"
        else:
            result["error"] = f"Unsupported audio type: {path.suffix}"
            return result

        # 限制最大读取 5MB
        max_size = 5 * 1024 * 1024
        with open(path, "rb") as f:
            audio_data = f.read(max_size)
            if len(audio_data) >= max_size:
                audio_info["warning"] = "Truncated to 5MB"

        audio_base64 = base64.b64encode(audio_data).decode("utf-8")

        result["llm_input"] = {
            "audio_info": audio_info,
            "audio_base64": audio_base64
        }

    except Exception as e:
        result["error"] = f"Audio read error: {str(e)}"

    return result


# ✅ 新增路径调试接口
@mcp.tool(description="调试音频文件路径解析")
def debug_audio_path(file_input: str) -> Dict[str, Any]:
    """
    用于检查路径解析逻辑，方便和 multi_file_tools_server 共用。
    """
    path = _resolve_file_path(file_input)
    return {
        "input": file_input,
        "resolved_path": str(path),
        "exists": path.exists(),
        "test_dir": TEST_DIR,
        "project_root": PROJECT_ROOT
    }


if __name__ == "__main__":
    print("Starting Audio Tools MCP...")
    print(f"PROJECT_ROOT: {PROJECT_ROOT}")
    print(f"TEST_DIR: {TEST_DIR}")
    mcp.run()
