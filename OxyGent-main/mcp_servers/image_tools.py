
import os
import json
import base64
import mimetypes
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

mcp = FastMCP()

client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    # api_key="sk-1c5ef9f54c7c48e8a7c04c950da145b9",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

@mcp.tool(description="调用 Qwen3-VL 生成多图内容摘要")
def describe_images_with_qwen(image_urls: str, question: str = "请概括这些图片的主要内容") -> str:
    """
    image_urls: JSON 字符串，例如 '["https://.../img1.png", "https://.../img2.png"]'
    """
    try:
        try:
            urls = json.loads(image_urls)
            if isinstance(urls, str):
                urls = [urls]
        except json.JSONDecodeError:
            urls = [image_urls]
        def to_accessible_url(raw: str) -> str:
            if not raw:
                return ""
            low = raw.lower()
            if low.startswith("http://") or low.startswith("https://") or low.startswith("data:"):
                return raw
            path = Path(raw)
            if not path.exists():
                return raw
            mime_type, _ = mimetypes.guess_type(path.name)
            if not mime_type:
                mime_type = "image/png"
            data = base64.b64encode(path.read_bytes()).decode("utf-8")
            return f"data:{mime_type};base64,{data}"

        msg_content = [
            {"type": "image_url", "image_url": {"url": to_accessible_url(url)}}
            for url in urls
            if url
        ]
        msg_content.append({"type": "text", "text": question})

        resp = client.chat.completions.create(
            model="qwen3-vl-plus",
            messages=[{"role": "user", "content": msg_content}],
            temperature=0.2,
        )
        answer = resp.choices[0].message.content
        return json.dumps({"status": "success", "summary": answer}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False)

if __name__ == "__main__":
    mcp.run()
