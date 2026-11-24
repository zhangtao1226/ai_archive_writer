"""表格对话的列式 JSON 校验。"""
import json
import math


def parse_excel_content(value):
    """解析表头到字符串数组的映射，允许空单元格及零行。"""
    def unique_pairs(pairs):
        """拒绝重复表头，避免 JSON 解析时静默丢列。"""
        result = {}
        for key, item in pairs:
            if key in result:
                raise ValueError(f'重复表头: {key}')
            result[key] = item
        return result
    try:
        data = json.loads(value, object_pairs_hook=unique_pairs)
    except json.JSONDecodeError as exc:
        raise ValueError('excel content 必须是合法 JSON 字符串，请使用双引号') from exc
    if not isinstance(data, dict) or not data:
        raise ValueError('表格必须包含至少一个表头')
    lengths = set()
    for header, cells in data.items():
        if not header.strip() or not isinstance(cells, list):
            raise ValueError('表头不能为空，列内容必须是数组')
        if any(type(cell) not in (str, int, float) or (type(cell) is float and not math.isfinite(cell)) for cell in cells):
            raise ValueError('单元格必须是字符串或有限数字，空值请使用空字符串')
        lengths.add(len(cells))
    if len(lengths) != 1:
        raise ValueError('各列行数必须一致，缺失单元格请用空字符串补齐')
    return data
