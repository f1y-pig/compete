from PyPDF2 import PdfReader

def handle_pdf(file_path: str):
    """
    处理 PDF 文件，返回统一结构字典
    :param file_path: PDF 文件路径
    :return: dict, 包含 file, type, content, error
    """
    try:
        # 打开 PDF 文件并读取所有页面文本
        reader = PdfReader(file_path)
        text = "\n".join([page.extract_text() or "" for page in reader.pages])
        
        # 返回统一格式
        return {
            "file": file_path,
            "type": "pdf",
            "content": text,  # 文本内容
            "error": None     # 无错误
        }
    except Exception as e:
        # 出现异常时返回错误信息
        return {
            "file": file_path,
            "type": "pdf",
            "content": None,
            "error": str(e)
        }
