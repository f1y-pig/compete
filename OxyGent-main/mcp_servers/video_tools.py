# mcp_servers/video_tools.py
"""Video processing tools."""

import json
import cv2
import numpy as np
import os
from mcp.server.fastmcp import FastMCP

mcp = FastMCP()

@mcp.tool(description="获取视频时长(秒)")
def get_video_duration(video_path: str) -> str:
    """获取视频时长(秒)"""
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return "Error opening video file"

        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        duration = frame_count / fps if fps > 0 else 0
        cap.release()
        return str(int(duration))
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool(description="提取指定时间点的帧")
def extract_frame_at_second(video_path: str, second: float) -> str:
    """提取指定时间点的帧"""
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return "Error opening video file"

        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_number = int(fps * second)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = cap.read()
        cap.release()

        if ret:
            return "Frame extracted successfully (processing not implemented)"
        return "Could not extract frame"
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    mcp.run()