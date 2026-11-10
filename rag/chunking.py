# -*-coding  : utf-8 -*-
# @Author    : zhangtao
# @File      : scheduler.py
# @Desc      : 对中文或英文文本按字符分块，保留重叠上下文
# @Time      : 2026/11/6 10:50
# @Software  : PyCharm


def split_text(text: str, chunk_size: int = 800, chunk_overlap: int = 120) -> list[str]:
    if chunk_size <= 0 or not 0 <= chunk_overlap < chunk_size:
        raise ValueError("需要 chunk_size > 0 且 0 <= chunk_overlap < chunk_size")
    text = text.strip()
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(text):
            break
        start = end - chunk_overlap
    return chunks
