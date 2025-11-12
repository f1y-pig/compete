# mcp_servers/web_tools.py
"""简化版网页内容提取工具，专注于核心功能."""

import re
import os
import requests
from urllib.parse import urljoin
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from typing import List, Dict, Any

# 简化导入，只保留必要的BeautifulSoup
try:
    from bs4 import BeautifulSoup

    BEAUTIFULSOUP_AVAILABLE = True
except ImportError:
    BEAUTIFULSOUP_AVAILABLE = False

mcp = FastMCP()


class SimplifiedWebCrawler:
    """简化版网页爬取工具，专注于核心内容提取"""

    def __init__(self):
        self.timeout = 8  # 缩短超时时间

    def get_web_content(self, url: str) -> Dict[str, Any]:
        """
        获取网页核心内容（简化版）
        """
        try:
            # 确保URL格式正确
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()

            # 基础信息提取
            base_info = self._extract_base_info(response.text, url)

            return {
                "url": url,
                "base_info": base_info,
                "status": "success"
            }

        except Exception as e:
            return {
                "url": url,
                "status": "error",
                "error": str(e)
            }

    def _extract_base_info(self, html: str, url: str) -> Dict[str, str]:
        """提取基础网页信息"""
        # 提取标题
        title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else "无标题"

        # 提取描述
        desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\'](.*?)["\']', html, re.IGNORECASE)
        description = desc_match.group(1).strip() if desc_match else ""

        # 提取主要内容
        main_content = self._extract_main_content(html)

        return {
            "title": title,
            "description": description,
            "main_content": main_content[:1500] if len(main_content) > 1500 else main_content,
            "content_length": len(main_content)
        }

    def _extract_main_content(self, html: str) -> str:
        """提取主要文本内容"""
        # 移除脚本和样式
        cleaned_html = re.sub(r'<script[^>]*>.*?</script>', ' ', html, flags=re.DOTALL)
        cleaned_html = re.sub(r'<style[^>]*>.*?</style>', ' ', cleaned_html, flags=re.DOTALL)

        # 提取文本内容
        text = re.sub(r'<[^>]+>', ' ', cleaned_html)
        text = re.sub(r'\s+', ' ', text).strip()

        return text


# 初始化爬虫
crawler = SimplifiedWebCrawler()


@mcp.tool(description="直接访问URL并提取主要内容")
def direct_url_access(url: str) -> str:
    """直接访问URL并提取核心内容"""
    try:
        result = crawler.get_web_content(url)

        if result["status"] == "success":
            base_info = result["base_info"]
            title = base_info.get("title", "无标题")
            main_content = base_info.get("main_content", "")

            if main_content:
                # 返回简洁格式
                return f"标题: {title}\n内容: {main_content[:1000]}..."
            else:
                return f"标题: {title}\n内容: 页面内容为空或无法提取"
        else:
            return f"访问失败: {result.get('error', '未知错误')}"

    except Exception as e:
        return f"URL访问错误: {str(e)}"


@mcp.tool(description="快速获取网页文本内容")
def get_web_content(url: str) -> str:
    """快速获取网页文本内容"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=8)
        response.raise_for_status()

        # 简单的内容提取
        text = re.sub(r'<[^>]+>', ' ', response.text)
        text = re.sub(r'\s+', ' ', text).strip()

        return text[:2000] + "..." if len(text) > 2000 else text

    except Exception as e:
        return f"获取网页内容失败: {str(e)}"


@mcp.tool(description="获取网页标题和基础信息")
def get_page_info(url: str) -> str:
    """获取网页标题和基础信息"""
    try:
        result = crawler.get_web_content(url)

        if result["status"] == "success":
            base_info = result["base_info"]
            title = base_info.get("title", "无标题")
            description = base_info.get("description", "")
            content_length = base_info.get("content_length", 0)

            info_parts = [f"标题: {title}"]
            if description:
                info_parts.append(f"描述: {description[:200]}...")
            info_parts.append(f"内容长度: {content_length} 字符")

            return "\n".join(info_parts)
        else:
            return f"获取页面信息失败: {result.get('error', '未知错误')}"

    except Exception as e:
        return f"获取页面信息错误: {str(e)}"


@mcp.tool(description="检查URL可访问性")
def check_url_accessibility(url: str) -> str:
    """检查URL是否可以正常访问"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        response = requests.get(url, headers=headers, timeout=5)

        if response.status_code == 200:
            return f"URL可正常访问: {url}"
        else:
            return f"URL访问返回状态码: {response.status_code}"

    except requests.exceptions.Timeout:
        return "URL访问超时"
    except requests.exceptions.ConnectionError:
        return "URL连接失败"
    except Exception as e:
        return f"URL访问错误: {str(e)}"


if __name__ == "__main__":
    mcp.run()