"""PDF processing tools with path debug."""

import json
import fitz  # PyMuPDF
from mcp.server.fastmcp import FastMCP
from pdf2image import convert_from_path
from pathlib import Path
import re

mcp = FastMCP()

# 可配置路径
PROJECT_ROOT = r"/Users/dengken/Desktop/数据挖掘比赛/compete"
TEST_DIR = r"/Users/dengken/Desktop/数据挖掘比赛/compete/OxyGent-main/test"


def resolve_file_path(file_input: str) -> Path:
    """根据 TEST_DIR / PROJECT_ROOT 自动选择存在的路径"""
    # 清理输入
    if file_input.startswith('[') and file_input.endswith(']'):
        try:
            file_list = json.loads(file_input.replace("'", '"'))
            file_input = file_list[0] if file_list else ''
        except json.JSONDecodeError:
            file_input = re.sub(r"['\"\[\]]", "", file_input)
    else:
        file_input = re.sub(r"['\"\[\]]", "", file_input)

    test_dir_path = Path(TEST_DIR) / file_input
    project_root_path = Path(PROJECT_ROOT) / file_input
    recommended_path = test_dir_path if test_dir_path.exists() else project_root_path
    return recommended_path.resolve()


@mcp.tool(description="提取PDF文本内容")
def extract_pdf_text(pdf_path: str) -> str:
    """提取PDF文本内容"""
    try:
        path = resolve_file_path(pdf_path)
        doc = fitz.open(path)
        text = []
        for page in doc:
            text.append(page.get_text())
        doc.close()
        return "\n".join(text)
    except Exception as e:
        return f"Error extracting PDF text: {str(e)}"


@mcp.tool(description="统计PDF中的图片数量（嵌入 + 扫描）")
def count_pdf_images(pdf_path: str) -> str:
    """统计PDF中的图片数量"""
    try:
        path = resolve_file_path(pdf_path)
        doc = fitz.open(path)
        total_images = 0
        for page in doc:
            imgs = page.get_images(full=True)
            total_images += len(imgs)

        # 扫描页至少算一张
        pages = convert_from_path(path)
        for i, _ in enumerate(pages):
            if len(doc[i].get_images(full=True)) == 0:
                total_images += 1

        doc.close()
        return str(total_images)
    except Exception as e:
        return f"Error counting PDF images: {str(e)}"


def _page_to_md(page: fitz.Page, page_no: int) -> str:
    text = page.get_text("text")
    cleaned = text.strip() or "_No text._"
    return f"## Page {page_no}\n{cleaned}"


@mcp.tool(description="PDF -> Markdown")
def pdf_to_markdown(file_path: str, max_pages: int = 20) -> str:
    path = resolve_file_path(file_path)
    doc = fitz.open(path)
    pages = [
        _page_to_md(page, idx + 1)
        for idx, page in enumerate(doc)
        if idx < max_pages
    ]
    return "# PDF Summary\n" + "\n\n".join(pages)


@mcp.tool(description="调试PDF或图片文件路径解析")
def debug_file_path(file_input: str) -> dict:
    """检查本地文件路径解析，返回 TEST_DIR / PROJECT_ROOT 路径信息"""
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
