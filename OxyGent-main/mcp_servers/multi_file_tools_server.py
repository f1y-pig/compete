# mcp_service/file_tools.py
"""
文件处理工具模块，用于 MCP 服务调用
支持 Excel/TXT/PPTX/PDF/图片/音频/视频文件
"""

from pathlib import Path
from typing import Dict, Any
from datetime import datetime
import base64
import io

import pandas as pd
from PyPDF2 import PdfReader
from pptx import Presentation
from PIL import Image

# 音频处理
import wave
import mutagen

# 视频处理
import cv2


# -------------------- 文件处理函数 --------------------
def handle_excel(file_path: str) -> Dict[str, Any]:
    try:
        df = pd.read_excel(file_path)
        data = df.to_dict(orient="records")
        return {"file": file_path, "type": "excel", "content": data, "error": None}
    except Exception as e:
        return {"file": file_path, "type": "excel", "content": None, "error": str(e)}


def handle_txt(file_path: str) -> Dict[str, Any]:
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


def handle_pptx(file_path: str) -> Dict[str, Any]:
    path = Path(file_path)
    result = {"file": str(path), "type": "pptx", "llm_input": None, "error": None}
    try:
        prs = Presentation(file_path)
        ppt_content, image_count = [], 0
        for idx, slide in enumerate(prs.slides, 1):
            slide_text = []
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    slide_text.append(shape.text.strip())
                if shape.shape_type == 13:
                    image_count += 1
            ppt_content.append({"slide_index": idx, "text": "\n".join(slide_text) or "No text"})
        result["llm_input"] = {
            "pptx_info": {"file_name": path.name, "slide_count": len(prs.slides), "image_count": image_count},
            "slide_content": ppt_content
        }
    except Exception as e:
        result["error"] = f"PPTX read error: {str(e)}"
    return result


def handle_pdf(file_path: str) -> Dict[str, Any]:
    try:
        reader = PdfReader(file_path)
        text = "\n".join([page.extract_text() or "" for page in reader.pages])
        return {"file": file_path, "type": "pdf", "content": text, "error": None}
    except Exception as e:
        return {"file": file_path, "type": "pdf", "content": None, "error": str(e)}


def handle_image(file_path: str) -> Dict[str, Any]:
    try:
        with open(file_path, "rb") as f:
            hex_data = f.read().hex()
        return {"file": file_path, "type": "image", "content": hex_data, "error": None}
    except Exception as e:
        return {"file": file_path, "type": "image", "content": None, "error": str(e)}


def handle_audio(file_path: str) -> Dict[str, Any]:
    path = Path(file_path)
    result = {"file": str(path), "type": "audio", "llm_input": None, "error": None}
    try:
        audio_info = {}
        if path.suffix.lower() == ".wav":
            with wave.open(file_path, "rb") as wf:
                audio_info["channels"] = wf.getnchannels()
                audio_info["sample_rate"] = wf.getframerate()
                audio_info["duration_second"] = round(wf.getnframes() / wf.getframerate(), 1)
        elif path.suffix.lower() == ".mp3":
            mp3 = mutagen.File(file_path)
            audio_info["duration_second"] = round(mp3.info.length, 1)
            audio_info["bitrate_kbps"] = mp3.info.bitrate // 1000

        max_size = 5 * 1024 * 1024
        with open(file_path, "rb") as f:
            audio_data = f.read(max_size)
            if len(audio_data) >= max_size:
                audio_info["warning"] = "Truncated to 5MB"
            audio_base64 = base64.b64encode(audio_data).decode("utf-8")
        result["llm_input"] = {"audio_info": audio_info, "audio_base64": audio_base64}
    except Exception as e:
        result["error"] = f"Audio read error: {str(e)}"
    return result


def handle_video(file_path: str) -> Dict[str, Any]:
    path = Path(file_path)
    result = {"file": str(path), "type": "video", "llm_input": None, "error": None}
    try:
        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            raise Exception("Failed to open video")
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        key_frames = []
        step = max(1, int(fps * 5))
        for i in range(0, min(frame_count, step * 5), step):
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ret, frame = cap.read()
            if ret:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                img.thumbnail((640, 480))
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format="JPEG")
                img_base64 = base64.b64encode(img_byte_arr.getvalue()).decode("utf-8")
                key_frames.append({"time_second": round(i / fps, 1), "frame_base64": img_base64})
        cap.release()
        result["llm_input"] = {
            "video_info": {"file_name": path.name, "duration_second": round(frame_count / fps, 1), "fps": round(fps, 1), "key_frame_count": len(key_frames)},
            "key_frames": key_frames
        }
    except Exception as e:
        result["error"] = f"Video read error: {str(e)}"
    return result


# -------------------- 统一分发函数 --------------------
def prepare_file_for_llm(file_path: str) -> Dict[str, Any]:
    """根据文件后缀调用对应处理函数"""
    ext = Path(file_path).suffix.lower()
    if ext in [".xls", ".xlsx"]:
        return handle_excel(file_path)
    elif ext == ".txt":
        return handle_txt(file_path)
    elif ext == ".pptx":
        return handle_pptx(file_path)
    elif ext in [".jpg", ".jpeg", ".png", ".bmp"]:
        return handle_image(file_path)
    elif ext in [".mp3", ".wav"]:
        return handle_audio(file_path)
    elif ext in [".mp4", ".avi"]:
        return handle_video(file_path)
    elif ext == ".pdf":
        return handle_pdf(file_path)
    else:
        return {"file": file_path, "type": "unknown", "llm_input": None, "error": f"Unsupported file type: {ext}"}
