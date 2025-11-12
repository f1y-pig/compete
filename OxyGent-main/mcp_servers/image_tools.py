
import os
import json
import base64
import mimetypes
from pathlib import Path
from mcp.server.fastmcp import FastMCP
import dashscope
import re

# 配置 DashScope（支持新加坡地域）
# dashscope.base_http_api_url = "https://dashscope-intl.aliyuncs.com/api/v1"

mcp = FastMCP()

# 项目路径配置
PROJECT_ROOT = r"/Users/dengken/Desktop/数据挖掘比赛/compete"
TEST_DIR = r"/Users/dengken/Desktop/数据挖掘比赛/compete/OxyGent-main/test"


@mcp.tool(description="调用 Qwen3-VL 生成多图内容摘要")
def describe_images_with_qwen(image_urls: str, question: str = "请概括这些图片的主要内容") -> str:
    """
    image_urls: JSON 字符串，例如 '["https://.../img1.png", "https://.../img2.png"]'
    自动将本地文件路径转换为 Base64 数据 URL。
    """
    try:
        # 解析图片 URL 列表
        try:
            urls = json.loads(image_urls)
            if isinstance(urls, str):
                urls = [urls]
        except json.JSONDecodeError:
            urls = [image_urls]

        # 本地路径转可访问 URL
        def to_accessible_url(raw: str) -> str:
            if not raw:
                return ""
            low = raw.lower()
            if low.startswith(("http://", "https://", "data:")):
                return raw

            # 先尝试 TEST_DIR，再 PROJECT_ROOT
            test_path = Path(TEST_DIR) / raw
            project_path = Path(PROJECT_ROOT) / raw
            if test_path.exists():
                path = test_path.resolve()
            elif project_path.exists():
                path = project_path.resolve()
            else:
                return raw  # 文件不存在，返回原始路径给模型，模型会报错

            mime_type, _ = mimetypes.guess_type(path.name)
            if not mime_type:
                mime_type = "image/png"
            data = base64.b64encode(path.read_bytes()).decode("utf-8")
            return f"data:{mime_type};base64,{data}"

        # 构造消息
        message_content = [{"image": to_accessible_url(url)} for url in urls if url]
        message_content.append({"text": question})

        # 调用模型
        response = dashscope.MultiModalConversation.call(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            model="qwen3-vl-plus",
            messages=[{"role": "user", "content": message_content}]
        )

        if response.status_code == 200 and hasattr(response.output, "choices"):
            answer = response.output.choices[0].message.content[0]["text"]
            return json.dumps({"status": "success", "summary": answer}, ensure_ascii=False)
        else:
            return json.dumps({"status": "error", "message": f"模型调用失败: {response.message}"}, ensure_ascii=False)

    except Exception as exc:
        return json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False)


# ✅ 新增路径调试接口
@mcp.tool(description="调试图片文件路径解析")
def debug_image_path(file_input: str) -> dict:
    """
    检查本地文件路径解析，返回 TEST_DIR 或 PROJECT_ROOT 下的路径信息。
    支持列表格式输入。
    """
    # 清理输入
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
