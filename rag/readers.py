# -*-coding  : utf-8 -*-
# @Author    : zhangtao
# @File      : readers.py
# @Desc      : 从文件字节提取正文，避免将 PDF/DOCX
# @Time      : 2026/11/6 10:50
# @Software  : PyCharm

from io import BytesIO


def extract_text(data: bytes, suffix: str) -> str:
    suffix = suffix.lower()
    if suffix in {'.txt', '.md'}:
        text = data.decode('utf-8-sig')
    elif suffix == '.pdf':
        from pypdf import PdfReader
        text = '\n\n'.join(page.extract_text() or '' for page in PdfReader(BytesIO(data)).pages)
    elif suffix == '.xls':
        import xlrd
        book = xlrd.open_workbook(file_contents=data)
        try:
            text = '\n'.join(sheet.name + '\n' + '\n'.join(
                '\t'.join(str(v) for v in sheet.row_values(i)) for i in range(sheet.nrows)) for sheet in book.sheets())
        finally:
            book.release_resources()
    elif suffix == '.xlsx':
        from openpyxl import load_workbook
        book = load_workbook(BytesIO(data), read_only=True, data_only=True)
        try:
            text = '\n'.join(sheet.title + '\n' + '\n'.join(
                '\t'.join('' if v is None else str(v) for v in row) for row in sheet.iter_rows(values_only=True)) for sheet in book)
        finally:
            book.close()
    elif suffix == '.docx':
        from docx import Document
        doc = Document(BytesIO(data))
        text = '\n'.join([p.text for p in doc.paragraphs] +
                         ['\t'.join(c.text for c in row.cells) for table in doc.tables for row in table.rows])
    else:
        raise ValueError(f'不支持的文件格式：{suffix}')
    if not text.strip():
        raise ValueError('文件没有可提取的正文；扫描版 PDF 需要先进行 OCR')
    return text
