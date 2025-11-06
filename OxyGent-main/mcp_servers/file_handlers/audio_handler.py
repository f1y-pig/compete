from pathlib import Path
from typing import Dict, Any
import base64

def handle_audio(file_path: str) -> Dict[str, Any]:
    """
    处理音频文件（MP3/WAV），返回统一结构
    llm_input 包含音频信息和 Base64 编码
    :param file_path: 音频文件路径
    :return: dict -> {file, type, llm_input, error}
    """
    path = Path(file_path)
    result = {"file": str(path), "type": "audio", "llm_input": None, "error": None}

    try:
        audio_info = {}

        # WAV 文件：提取基本信息
        if path.suffix.lower() == ".wav":
            import wave
            with wave.open(file_path, "rb") as wf:
                audio_info["channels"] = wf.getnchannels()
                audio_info["sample_rate"] = wf.getframerate()
                audio_info["duration_second"] = round(wf.getnframes() / wf.getframerate(), 1)

        # MP3 文件：提取基本信息
        elif path.suffix.lower() == ".mp3":
            import mutagen
            mp3 = mutagen.File(file_path)
            audio_info["duration_second"] = round(mp3.info.length, 1)
            audio_info["bitrate_kbps"] = mp3.info.bitrate // 1000

        # 读取音频二进制，限制 5MB
        max_size = 5 * 1024 * 1024
        with open(file_path, "rb") as f:
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
