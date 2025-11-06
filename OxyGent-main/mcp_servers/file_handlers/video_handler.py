from pathlib import Path
from typing import Dict, Any
import base64
import io
from PIL import Image

def handle_video(file_path: str) -> Dict[str, Any]:
    """
    处理视频文件（MP4/AVI），提取关键帧并转 Base64
    llm_input 包含视频信息和 key_frames 列表
    :param file_path: 视频文件路径
    :return: dict -> {file, type, llm_input, error}
    """
    path = Path(file_path)
    result = {"file": str(path), "type": "video", "llm_input": None, "error": None}

    try:
        import cv2

        # 打开视频
        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            raise Exception("Failed to open video")

        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        key_frames = []

        # 每5秒取1帧，最多取前5帧
        step = max(1, int(fps * 5))
        for i in range(0, min(frame_count, step * 5), step):
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ret, frame = cap.read()
            if ret:
                # BGR -> RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                img.thumbnail((640, 480))
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format="JPEG")
                img_base64 = base64.b64encode(img_byte_arr.getvalue()).decode("utf-8")
                key_frames.append({
                    "time_second": round(i / fps, 1),
                    "frame_base64": img_base64
                })

        cap.release()
        result["llm_input"] = {
            "video_info": {
                "file_name": path.name,
                "duration_second": round(frame_count / fps, 1),
                "fps": round(fps, 1),
                "key_frame_count": len(key_frames)
            },
            "key_frames": key_frames
        }

    except Exception as e:
        result["error"] = f"Video read error: {str(e)}"

    return result
