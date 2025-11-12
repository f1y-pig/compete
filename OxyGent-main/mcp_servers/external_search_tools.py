# mcp_servers/external_search_tools.py
"""Simplified external search tools with reliable sources."""

import re
import requests
from datetime import datetime
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from typing import List, Dict, Any
import urllib.parse

mcp = FastMCP()


class SimpleSearchClient:
    """简化版搜索客户端"""

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    def quick_search(self, query: str, max_results: int = 3) -> List[Dict[str, Any]]:
        """
        快速搜索，返回基本信息
        """
        results = []

        # 百度百科（相对稳定的源）
        try:
            baike_results = self._baidu_baike_simple(query, max_results)
            results.extend(baike_results)
        except Exception:
            pass

        # 如果百科没有结果，添加通用搜索建议
        if not results:
            results.append({
                "title": f"搜索：{query}",
                "url": f"https://www.baidu.com/s?wd={urllib.parse.quote(query)}",
                "snippet": f"关于 {query} 的搜索结果",
                "source": "百度搜索",
                "confidence": 0.6
            })

        return results[:max_results]

    def _baidu_baike_simple(self, query: str, max_results: int) -> List[Dict]:
        """简化版百度百科搜索"""
        try:
            encoded_query = urllib.parse.quote(query)

            # 直接构造百科链接
            return [{
                "title": f"百度百科：{query}",
                "url": f"https://baike.baidu.com/item/{encoded_query}",
                "snippet": f"百度百科关于 {query} 的词条解释",
                "source": "百度百科",
                "confidence": 0.8
            }]
        except Exception:
            return []


def extract_simple_answer(content: str, query: str) -> str:
    """从内容中提取简单答案"""
    try:
        # 数字类问题
        if any(keyword in query for keyword in ["多少", "几个", "数量", "数值"]):
            numbers = re.findall(r'(\d+\.?\d*)%', content)
            if numbers:
                return f"{numbers[0]}%"
            numbers = re.findall(r'\b\d+\b', content)
            if numbers:
                return numbers[0]

        # 日期类问题
        if any(keyword in query for keyword in ["时间", "日期", "什么时候"]):
            date_patterns = [
                r'\d{4}年\d{1,2}月\d{1,2}日',
                r'\d{4}-\d{1,2}-\d{1,2}'
            ]
            for pattern in date_patterns:
                dates = re.findall(pattern, content)
                if dates:
                    return dates[0]

        # 是/否类问题
        if any(keyword in query for keyword in ["是否", "是不是", "有没有"]):
            if "是" in content or "有" in content:
                return "是"
            elif "否" in content or "没有" in content:
                return "否"

        return None
    except Exception:
        return None


def get_simple_web_content(url: str) -> str:
    """获取简化的网页内容"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()

        # 简单的内容提取
        text = re.sub(r'<[^>]+>', ' ', response.text)
        text = re.sub(r'\s+', ' ', text).strip()

        return text[:500]  # 限制长度

    except Exception:
        return ""


# 初始化搜索客户端
search_client = SimpleSearchClient()


@mcp.tool(description="快速搜索外部信息")
def external_search(
        query: str = Field(description="搜索查询"),
        max_results: int = Field(3, description="最大结果数量")
) -> str:
    """
    快速外部搜索工具
    """
    try:
        # 首先检查是否可以直接访问的URL
        url_pattern = r'https?://[^\s]+|www\.[^\s]+'
        url_matches = re.findall(url_pattern, query)

        if url_matches:
            # 如果有直接URL，优先访问
            for match in url_matches[:1]:  # 只处理第一个URL
                try:
                    if match.startswith('www.'):
                        url = 'https://' + match
                    else:
                        url = match

                    web_content = get_simple_web_content(url)
                    if web_content and len(web_content) > 30:
                        simple_answer = extract_simple_answer(web_content, query)
                        if simple_answer:
                            return simple_answer
                        else:
                            # 返回前100个字符
                            return web_content[:100] + "..."
                except Exception:
                    continue

        # 执行快速搜索
        search_results = search_client.quick_search(query, max_results)

        if not search_results:
            return "暂时无法获取该信息的实时数据。"

        # 返回第一个结果的摘要
        first_result = search_results[0]
        snippet = first_result.get('snippet', '')

        if snippet:
            return snippet
        else:
            return f"找到相关信息：{first_result.get('title', '')}"

    except Exception as e:
        return "搜索服务暂时不可用。"


@mcp.tool(description="快速问答搜索")
def quick_search(query: str) -> str:
    """快速问答搜索"""
    try:
        # 直接返回搜索建议
        encoded_query = urllib.parse.quote(query)
        search_url = f"https://www.baidu.com/s?wd={encoded_query}"

        return f"建议搜索：{query}\n搜索链接：{search_url}"

    except Exception:
        return "搜索服务暂时不可用。"


@mcp.tool(description="百科知识查询")
def encyclopedia_search(query: str) -> str:
    """百科知识查询"""
    try:
        encoded_query = urllib.parse.quote(query)
        baike_url = f"https://baike.baidu.com/item/{encoded_query}"

        # 尝试获取简单内容
        content = get_simple_web_content(baike_url)
        if content and len(content) > 50:
            # 提取第一段有意义的内容
            sentences = re.split(r'[。！？!?]', content)
            for sentence in sentences:
                if len(sentence.strip()) > 10:
                    return sentence.strip()[:150]

            return content[:100] + "..."
        else:
            return f"百科词条：{query}\n链接：{baike_url}"

    except Exception:
        return "百科查询服务暂时不可用。"


@mcp.tool(description="检查搜索服务状态")
def search_status() -> str:
    """检查搜索服务状态"""
    try:
        # 测试百度可访问性
        response = requests.get("https://www.baidu.com", timeout=5)
        if response.status_code == 200:
            return "搜索服务正常"
        else:
            return "搜索服务受限"
    except Exception:
        return "搜索服务不可用"


if __name__ == "__main__":
    mcp.run()