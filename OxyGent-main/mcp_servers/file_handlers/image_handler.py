def handle_image(file_path: str):
    """
    处理图片文件，返回统一结构字典
    :param file_path: 图片文件路径
    :return: dict, 包含 file, type, content, error
    """
    try:
        # 以二进制方式打开图片，并转换为 hex 编码
        with open(file_path, "rb") as f:
            hex_data = f.read().hex()
        
        return {
            "file": file_path,
            "type": "image",
            "content": hex_data,  # 图片 hex 字符串
            "error": None
        }
    except Exception as e:
        return {
            "file": file_path,
            "type": "image",
            "content": None,
            "error": str(e)
        }
