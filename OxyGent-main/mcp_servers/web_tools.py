# mcp_servers/web_tools.py
"""Web content extraction tools."""

import json
import requests
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP

mcp = FastMCP()

@mcp.tool(description="获取网页文本内容")
def get_web_content(url: str) -> str:
    """获取网页文本内容"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        return soup.get_text(separator=' ', strip=True)
    except Exception as e:
        return f"Error fetching web content: {str(e)}"

@mcp.tool(description="获取京东商品信息")
def get_jd_product_info(product_id: str) -> str:
    """获取京东商品信息"""
    try:
        url = f"https://item.jd.com/{product_id}.html"
        return get_web_content(url)
    except Exception as e:
        return f"Error fetching JD product info: {str(e)}"

if __name__ == "__main__":
    mcp.run()