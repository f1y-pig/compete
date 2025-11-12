
"""增强版视频处理工具（支持帧提取、文字识别和视频信息解析）"""

import json
import cv2
import numpy as np
import os
import pytesseract
from PIL import Image
from mcp.server.fastmcp import FastMCP
import tempfile
import numpy as np
import cv2


# 确保Tesseract OCR可执行文件路径正确（根据你的安装路径修改）
# Windows示例: pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

pytesseract.pytesseract.tesseract_cmd = "/opt/homebrew/bin/tesseract"
os.environ["TESSDATA_PREFIX"] = "/opt/homebrew/share/tessdata"

mcp = FastMCP()
def load_image_unicode(path):
    data = np.fromfile(path, dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    return image

def preprocess_for_ocr(image_bgr: np.ndarray) -> Image.Image:
    """
    放大 + CLAHE + Otsu 二值化，返回适合 OCR 的 PIL Image。
    """
    lang = "chi_sim+eng"
    scale_factor = 3
    enlarged = cv2.resize(
        image_bgr,
        (image_bgr.shape[1] * scale_factor, image_bgr.shape[0] * scale_factor),
        interpolation=cv2.INTER_CUBIC
    )
    gray = cv2.cvtColor(enlarged, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    _, thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return Image.fromarray(thresh)

@mcp.tool(description="获取视频详细信息（时长、分辨率、帧率等） 但不包括视频中文文字等关键信息 如果需要识别文字请调用下面的工具")
def get_video_info(video_path: str) -> str:
    """获取视频的完整信息，包括时长、分辨率、帧率等"""
    try:
        lang = "chi_sim+eng"
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return json.dumps({"error": "无法打开视频文件"})

        # 提取视频属性
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        duration = frame_count / fps if fps > 0 else 0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        codec = int(cap.get(cv2.CAP_PROP_FOURCC))
        codec_name = "".join([chr((codec >> 8 * i) & 0xFF) for i in range(4)])

        cap.release()

        return json.dumps({
            "duration_seconds": round(duration, 2),
            "duration_minutes": round(duration / 60, 2),
            "fps": round(fps, 2),
            "frame_count": int(frame_count),
            "resolution": f"{width}x{height}",
            "width": width,
            "height": height,
            "codec": codec_name,
            "status": "success"
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.tool(description="提取指定时间点的帧并保存为图片")
def extract_frame_at_second(video_path: str, second: float) -> str:
    """提取视频指定时间点的帧，返回临时图片路径"""
    try:
        lang = "chi_sim+eng"
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return json.dumps({"error": "无法打开视频文件"})

        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_number = int(fps * second)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = cap.read()
        cap.release()

        if ret:
            # 保存帧到临时文件
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
                cv2.imwrite(temp_file.name, frame)
                return json.dumps({
                    "status": "success",
                    "frame_path": temp_file.name,
                    "frame_number": frame_number,
                    "timestamp_second": second
                })
        return json.dumps({"error": "无法提取帧"})
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.tool(description="从视频指定时间点的帧中识别文字")
def ocr_frame_at_second(video_path: str, second: float, lang: str = "chi_sim+eng") -> str:
    """提取视频指定时间点的帧并识别其中的文字（支持中英文）"""
    try:
        lang = "chi_sim+eng"
        # 先提取帧
        frame_result = json.loads(extract_frame_at_second(video_path, second))
        if "error" in frame_result:
            return json.dumps({"error": frame_result["error"]})

        # 读取图片并进行OCR识别
        frame = Image.open(frame_result["frame_path"])
        
        # 预处理：转为灰度图提高识别率
        frame_gray = frame.convert('L')
        # 放大2倍（保持抗锯齿）
        scale = 2
        width = int(frame_gray.width * scale)
        height = int(frame_gray.height * scale)
        frame_gray = frame_gray.resize((width, height), Image.Resampling.LANCZOS)  # 高清放大
        np_img = np.array(frame_gray)
        processed_img = frame_gray
        # 文字识别（限制字符集，提升数字/容量识别准确度）
        ocr_config = '--psm 6 -c tessedit_char_whitelist=0123456789GBMB'
        text = pytesseract.image_to_string(processed_img, lang=lang, config=ocr_config)
       
        # 清理临时文件
        os.unlink(frame_result["frame_path"])

        return json.dumps({
            "status": "success",
            "timestamp_second": second,
            "recognized_text": text.strip(),
            "language": lang
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.tool(description="批量提取视频关键帧并识别文字")
def batch_ocr_key_frames(video_path: str, interval_seconds: float = 1) -> str:
    """按时间间隔提取视频关键帧并识别文字，默认每1秒提取一帧"""
    try:
        lang = "chi_sim+eng"
        # 获取视频信息
        info = json.loads(get_video_info(video_path))
        if "error" in info:
            return json.dumps({"error": info["error"]})

        duration = info["duration_seconds"]
        key_frames = []
        
        # 按间隔提取帧并识别文字
        for second in np.arange(0, duration, interval_seconds):
            ocr_result = json.loads(ocr_frame_at_second(video_path, second))
            if "recognized_text" in ocr_result:
                key_frames.append({
                    "timestamp_second": round(second, 2),
                    "text": ocr_result["recognized_text"]
                })

        return json.dumps({
            "status": "success",
            "total_frames": len(key_frames),
            "interval_seconds": interval_seconds,
            "key_frames": key_frames
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})
    
@mcp.tool(description="优先提取视频中后段（15-35 秒，通常是商品详情展示时段）的帧，而非全时段均匀提取")
@mcp.tool(description="重点提取视频中可能展示商品规格的时段（5-45秒），每0.1秒一帧，提高覆盖密度")
def batch_ocr_specs_period(video_path: str, start_second: float = 5, end_second: float = 45, interval: float = 1):
    """
    重点覆盖商品规格大概率出现的时段（5-45秒），缩小提取间隔到0.5秒
    避免错过短时间展示的规格文字
    """
    try:
        lang = "chi_sim+eng"
        info = json.loads(get_video_info(video_path))
        if "error" in info:
            return json.dumps({"error": info["error"]})

        duration = info["duration_seconds"]
        key_frames = []
        # 按0.5秒间隔提取，覆盖更密集
        for second in np.arange(start_second, min(end_second, duration), interval):
            ocr_result = json.loads(ocr_frame_at_second(video_path, second))
            text = ocr_result.get("recognized_text", "").strip()
            if text:  # 只保留识别到文字的结果，减少无效数据
                key_frames.append({
                    "timestamp_second": round(second, 2),
                    "text": text
                })

        return json.dumps({
            "status": "success",
            "total_valid_frames": len(key_frames),
            "key_frames": key_frames
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})
    
@mcp.tool(description="根据已识别到的数字，补充周边时间点的帧，获取完整规格")
def ocr_supplement_frames(video_path: str, base_second: float = 24, range_seconds: float = 3):
    """
    已知某时间点（如24秒）识别到数字，补充前后3秒内的帧（每0.2秒一帧）
    精准捕捉完整的规格文字（如“2”→“256GB”）
    """
    try:
        lang = "chi_sim+eng"
        key_frames = []
        # 补充 base_second 前后 range_seconds 内的帧，间隔0.2秒
        start = max(0, base_second - range_seconds)
        end = base_second + range_seconds
        for second in np.arange(start, end, 0.2):
            ocr_result = json.loads(ocr_frame_at_second(video_path, second))
            text = ocr_result.get("recognized_text", "").strip()
            if text and any(char in text for char in ["G", "B", "M"]):  # 优先保留包含存储单位的结果
                key_frames.append({
                    "timestamp_second": round(second, 2),
                    "text": text
                })

        return json.dumps({
            "status": "success",
            "base_second": base_second,
            "supplement_range": f"{start}-{end}s",
            "key_frames": key_frames
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})
    
@mcp.tool(description="OCR识别任意图片文件中的文字（支持中英文）")
def ocr_image_file(image_path: str, lang: str = "chi_sim+eng") -> str:
    """
    读取图片并识别文字，复用视频帧的预处理逻辑。
    返回 JSON：{"status": "success", "recognized_text": "...", "language": lang}
    """
    try:
        lang = "chi_sim+eng"
        image_bgr = load_image_unicode(image_path)
        if image_bgr is None:
            return json.dumps({"error": f"无法打开图片: {image_path}"})

        processed_img = preprocess_for_ocr(image_bgr)
        text = pytesseract.image_to_string(processed_img, lang=lang, config='--psm 6')

        return json.dumps({
            "status": "success",
            "recognized_text": text.strip(),
            "language": lang
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    mcp.run()
