"""PDF processing tools with path debug and OCR support."""

import json
import fitz  # PyMuPDF
from mcp.server.fastmcp import FastMCP
from pdf2image import convert_from_path
from pathlib import Path
import re
import pytesseract

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
    if test_dir_path.exists():
        return test_dir_path.resolve()
    elif project_root_path.exists():
        return project_root_path.resolve()
    else:
        raise FileNotFoundError(f"File not found in TEST_DIR or PROJECT_ROOT: {file_input}")


@mcp.tool(description="提取PDF文本内容，支持扫描件OCR")
def extract_pdf_text(pdf_path: str, use_ocr: bool = True) -> str:
    """提取PDF文本内容，如果是扫描 PDF 可启用 OCR"""
    try:
        path = resolve_file_path(pdf_path)
        doc = fitz.open(path)
        text_pages = []

        for page_no, page in enumerate(doc):
            text = page.get_text().strip()
            if not text and use_ocr:
                # OCR 提取
                images = convert_from_path(str(path), first_page=page_no+1, last_page=page_no+1)
                if images:
                    ocr_text = pytesseract.image_to_string(images[0], lang='chi_sim')
                    text_pages.append(ocr_text)
                else:
                    text_pages.append("")
            else:
                text_pages.append(text)
        doc.close()
        return "\n".join(text_pages)
    except Exception as e:
        return f"Error extracting PDF text: {str(e)}"


@mcp.tool(description="统计PDF中的图片数量（嵌入 + 扫描页）")
def count_pdf_images(pdf_path: str) -> str:
    """统计 PDF 中的图片数量，包括扫描页"""
    try:
        path = resolve_file_path(pdf_path)
        doc = fitz.open(path)
        total_images = 0

        for page_no, page in enumerate(doc):
            imgs = page.get_images(full=True)
            if imgs:
                total_images += len(imgs)
            else:
                # 判断扫描页（无内嵌图片或无文本）
                text = page.get_text().strip()
                if not text:
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
    doc.close()
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
    recommended_path = None
    if test_dir_path.exists():
        recommended_path = test_dir_path
    elif project_root_path.exists():
        recommended_path = project_root_path

    return {
        "cleaned_filename": file_input,
        "test_dir_path": str(test_dir_path),
        "test_dir_exists": test_dir_path.exists(),
        
        "project_root_path": str(project_root_path),
        "project_root_exists": project_root_path.exists(),
        "recommended_path": str(recommended_path) if recommended_path else None
    }


if __name__ == "__main__":
    mcp.run()
