# mcp_service/file_tools/text_tools.py
from pathlib import Path
from typing import Dict, Any

def handle_txt(file_path: str) -> Dict[str, Any]:
    path = Path(file_path)
    result = {"file": str(path), "type": "text", "llm_input": None, "error": None}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read(10000)
            if len(text) >= 10000:
                text += "\n...[Truncated: over 10000 characters]"
            result["llm_input"] = text
    except Exception as e:
        result["error"] = f"TXT read error: {str(e)}"
    return result
