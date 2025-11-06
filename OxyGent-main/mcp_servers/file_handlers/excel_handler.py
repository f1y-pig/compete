import pandas as pd

def handle_excel(file_path: str):
    """
    处理 Excel 文件，返回统一结构字典
    :param file_path: Excel 文件路径
    :return: dict, 包含 file, type, content, error
    """
    try:
        # 读取 Excel 文件为 DataFrame
        df = pd.read_excel(file_path)
        # 转换为列表字典形式，便于 LLM 或 Agent 使用
        data = df.to_dict(orient="records")
        
        return {
            "file": file_path,
            "type": "excel",
            "content": data,  # Excel 数据
            "error": None
        }
    except Exception as e:
        return {
            "file": file_path,
            "type": "excel",
            "content": None,
            "error": str(e)
        }
