# mcp_servers/github_tools.py
"""GitHub API tools."""

import json
import requests
from mcp.server.fastmcp import FastMCP

mcp = FastMCP()
GITHUB_API_URL = "https://api.github.com"

@mcp.tool(description="获取仓库最新发布版本")
def get_repo_latest_release(owner: str, repo: str) -> str:
    """获取仓库最新发布版本"""
    try:
        url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/releases/latest"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json().get("tag_name", "No release found")
        return f"API request failed with status {response.status_code}"
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool(description="获取指定日期的issue")
def get_issue_by_date(owner: str, repo: str, date: str) -> str:
    """获取指定日期的issue"""
    try:
        url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/issues"
        params = {
            "since": f"{date}T00:00:00Z",
            "until": f"{date}T23:59:59Z",
            "state": "all"
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return json.dumps(response.json(), ensure_ascii=False)
        return f"API request failed with status {response.status_code}"
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    mcp.run()