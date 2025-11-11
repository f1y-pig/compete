# mcp_servers/pptx_qa_tools.py
"""
PPTX 专用工具：将幻灯片完整展开为 Markdown，或按页返回结构化数据。
"""
import json
from collections import defaultdict
from pathlib import Path

from pptx import Presentation
from mcp.server.fastmcp import FastMCP
from pydantic import Field

mcp = FastMCP()


def _slide_to_md(slide, index: int) -> str:
    """提取当前页的所有文本、表格、图片统计，转成 Markdown。"""
    lines = [f"## Slide {index}"]

    text_chunks = []
    table_chunks = []
    pictures = 0

    for shape in slide.shapes:
        if hasattr(shape, "text") and shape.text.strip():
            text_chunks.append(shape.text.strip())
        if shape.has_table:
            rows = []
            for row in shape.table.rows:
                rows.append(" | ".join(cell.text.strip() for cell in row.cells))
            table_chunks.append("\n".join(rows))
        if shape.shape_type == 13:  # MSO_SHAPE_TYPE.PICTURE
            pictures += 1

    if text_chunks:
        lines.append("\n".join(text_chunks))
    if table_chunks:
        lines.append("\n\n".join(f"表格:\n{tbl}" for tbl in table_chunks))
    if pictures:
        lines.append(f"*Images:* {pictures}")

    if len(lines) == 1:
        lines.append("_No textual content on this slide._")
    return "\n\n".join(lines)


@mcp.tool(description="将 PPTX 转为 Markdown，供 LLM 直接阅读")
def pptx_to_markdown(
    file_path: str = Field(..., description="PPTX 文件绝对路径或相对 test/ 的路径"),
    max_slides: int = Field(default=20, description="最多展开的页面数量，默认 20")
) -> str:
    path = Path(file_path)
    if not path.is_absolute():
        path = Path("OxyGent-main") / path  # 与 agent.py 的 test 目录保持一致
    if not path.exists():
        return f"Error: file not found -> {path}"

    try:
        prs = Presentation(path)
    except Exception as exc:
        return f"Error: cannot open pptx -> {exc}"

    slides = []
    for idx, slide in enumerate(prs.slides, 1):
        if idx > max_slides:
            slides.append(f"## Slide {idx}\n_Skipped due to max_slides limit._")
            break
        slides.append(_slide_to_md(slide, idx))

    meta = f"# PPTX Summary\n- File: {path.name}\n- Slides: {len(prs.slides)}\n"
    return meta + "\n\n".join(slides)


@mcp.tool(description="返回 PPTX 的结构化摘要（JSON）")
def pptx_to_json(
    file_path: str = Field(...),
    include_tables: bool = Field(default=True, description="是否包含表格内容"),
    include_images: bool = Field(default=True, description="是否统计图片数量")
) -> str:
    path = Path(file_path)
    if not path.is_absolute():
        path = Path("OxyGent-main") / path
    if not path.exists():
        return json.dumps({"error": f"file not found: {str(path)}"}, ensure_ascii=False)

    try:
        prs = Presentation(path)
    except Exception as exc:
        return json.dumps({"error": f"cannot open pptx: {exc}"}, ensure_ascii=False)

    summary = {
        "file": path.name,
        "slide_count": len(prs.slides),
        "slides": []
    }

    for idx, slide in enumerate(prs.slides, 1):
        slide_info = defaultdict(list)
        for shape in slide.shapes:
            if hasattr(shape, "text") and shape.text.strip():
                slide_info["texts"].append(shape.text.strip())
            if include_tables and shape.has_table:
                table_rows = []
                for row in shape.table.rows:
                    table_rows.append([cell.text.strip() for cell in row.cells])
                slide_info["tables"].append(table_rows)
            if include_images and shape.shape_type == 13:
                slide_info["images"].append("image_placeholder")

        summary["slides"].append({
            "index": idx,
            **slide_info
        })

    return json.dumps(summary, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    print("Starting PPTX QA Tool...")
    mcp.run()
