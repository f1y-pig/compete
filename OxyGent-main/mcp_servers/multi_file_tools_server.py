from pathlib import Path
from mcp.server import Server
try:
    from mcp.types import ToolRequest, TextContent
except ImportError:
    from mcp.server import ToolRequest
    from mcp.server.types import TextContent

from .file_handlers.excel_handler import handle_excel
from .file_handlers.txt_handler import handle_txt
from .file_handlers.pptx_handler import handle_pptx
from .file_handlers.image_handler import handle_image
from .file_handlers.audio_handler import handle_audio  
from .file_handlers.video_handler import handle_video  
from .file_handlers.pdf_handler import handle_pdf
import json
server = Server("multi_file_tools")

def prepare_file_for_llm(file_path: str):
    """
    根据文件后缀调用对应处理模块
    返回统一结构 dict: {file, type, llm_input, error}
    """
    path = Path(file_path)
    ext = path.suffix.lower()

    # Excel
    if ext in [".xls", ".xlsx"]:
        return handle_excel(file_path)
    # TXT
    elif ext == ".txt":
        return handle_txt(file_path)
    # PPTX
    elif ext == ".pptx":
        return handle_pptx(file_path)
    # 图片
    elif ext in [".jpg", ".jpeg", ".png", ".bmp"]:
        return handle_image(file_path)
    # 音频
    elif ext in [".mp3", ".wav"]:
        return handle_audio(file_path)
    # 视频
    elif ext in [".mp4", ".avi"]:
        return handle_video(file_path)
    # PDF
    elif ext == ".pdf":
        return handle_pdf(file_path)
    # 未知格式
    else:
        return {"file": str(path), "type": "unknown", "llm_input": None, "error": f"Unsupported file type: {ext}"}

@server.tool(name="prepare_file_for_llm", description="读取并准备文件内容给 LLM 使用")
async def handle_prepare_file_for_llm(request: ToolRequest):
    """
    MCP 工具接口，用于异步处理文件请求
    """
    if not request.arguments or "file_path" not in request.arguments:
        return TextContent(json.dumps({"error": "Missing file_path argument"}, ensure_ascii=False, indent=2))
    file_path = request.arguments["file_path"]
    result = prepare_file_for_llm(file_path)
    return TextContent(json.dumps(result, ensure_ascii=False, indent=2))
