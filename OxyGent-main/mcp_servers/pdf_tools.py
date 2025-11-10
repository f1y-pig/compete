# mcp_servers/pdf_tools.py
"""PDF processing tools."""

import json
import fitz  # PyMuPDF
from mcp.server.fastmcp import FastMCP

mcp = FastMCP()

@mcp.tool(description="提取PDF文本内容")
def extract_pdf_text(pdf_path: str) -> str:
    """提取PDF文本内容"""
    try:
        doc = fitz.open(pdf_path)
        text = []
        for page in doc:
            text.append(page.get_text())
        doc.close()
        return "\n".join(text)
    except Exception as e:
        return f"Error extracting PDF text: {str(e)}"

@mcp.tool(description="统计PDF中的图片数量")
def count_pdf_images(pdf_path: str) -> str:
    """统计PDF中的图片数量"""
    try:
        doc = fitz.open(pdf_path)
        count = 0
        for page in doc:
            count += len(page.get_images())
        doc.close()
        return str(count)
    except Exception as e:
        return f"Error counting PDF images: {str(e)}"

if __name__ == "__main__":
    mcp.run()