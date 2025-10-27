# multi_file_tools.py - 为多模态 LLM 准备文件输入
import os
from pathlib import Path
from typing import Dict, Any

# 可处理的文件类型
EXCEL_EXT = [".xls", ".xlsx"]
PDF_EXT = [".pdf"]
IMAGE_EXT = [".jpg", ".jpeg", ".png", ".bmp"]
AUDIO_EXT = [".mp3", ".wav"]
VIDEO_EXT = [".mp4", ".avi"]

def prepare_file_for_llm(file_path: str) -> Dict[str, Any]:
    """
    根据文件类型读取并准备文件内容给多模态 LLM 使用
    """
    path = Path(file_path)
    ext = path.suffix.lower()

    result = {"file": str(path), "type": None, "llm_input": None}

    # Excel - 读取表格内容为 JSON
    if ext in EXCEL_EXT:
        result["type"] = "excel"
        try:
            import pandas as pd
            df = pd.read_excel(file_path)
            result["llm_input"] = df.to_dict(orient="records")  # 转成列表字典
        except Exception as e:
            result["llm_input"] = f"Failed to read Excel: {str(e)}"

    # PDF - 提取文本
    elif ext in PDF_EXT:
        result["type"] = "pdf"
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(file_path)
            text = "\n".join([page.extract_text() or "" for page in reader.pages])
            result["llm_input"] = text
        except Exception as e:
            result["llm_input"] = f"Failed to read PDF: {str(e)}"

    # 图片 - 直接传二进制给多模态 LLM
    elif ext in IMAGE_EXT:
        result["type"] = "image"
        try:
            with open(file_path, "rb") as f:
                result["llm_input"] = f.read()
        except Exception as e:
            result["llm_input"] = f"Failed to read image: {str(e)}"

    # 音频 - 直接传二进制
    elif ext in AUDIO_EXT:
        result["type"] = "audio"
        try:
            with open(file_path, "rb") as f:
                result["llm_input"] = f.read()
        except Exception as e:
            result["llm_input"] = f"Failed to read audio: {str(e)}"

    # 视频 - 直接传二进制
    elif ext in VIDEO_EXT:
        result["type"] = "video"
        try:
            with open(file_path, "rb") as f:
                result["llm_input"] = f.read()
        except Exception as e:
            result["llm_input"] = f"Failed to read video: {str(e)}"

    # 其他类型
    else:
        result["type"] = "unknown"
        result["llm_input"] = None

    return result


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python multi_file_tools.py <file_path>")
        exit(1)

    file_path = sys.argv[1]
    info = prepare_file_for_llm(file_path)
    print(f"Prepared for LLM: {info['type']}")
