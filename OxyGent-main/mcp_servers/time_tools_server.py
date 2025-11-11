# OxyGent-main/mcp_servers/time_tools_server.py
from datetime import datetime
from mcp.server.fastmcp import FastMCP

mcp = FastMCP()

@mcp.tool(description="获取当前时间")
def get_time() -> dict:
    """返回本地当前时间"""
    now = datetime.now()
    return {"current_time": now.strftime("%Y-%m-%d %H:%M:%S")}


@mcp.tool(description="获取UTC时间")
def get_utc_time() -> dict:
    """返回UTC时间"""
    from datetime import datetime
    now = datetime.utcnow()
    return {"utc_time": now.strftime("%Y-%m-%d %H:%M:%S")}


if __name__ == "__main__":
    mcp.run()
