# -*-coding : utf-8 -*-
# @Author   : zhangtao
# @FileName : excel_content.py
# @Desc     : 
# @Time     : 2026/11/24 09:59
# @Software : PyCharm

import json
import math


def parse_excel_content(value):

    def unique_pairs(pairs):
        result = {}
        for key, item in pairs:
            if key in result:
                raise ValueError(f"重复表头: {key}")
            result[key] = item
        return result

    try:
        data = json.loads(value, object_pairs_hook=unique_pairs)
    except json.JSONDecodeError as exc:
        raise ValueError('excel content 必须合法 JSON 字符串， 请使用双引号') from exc

    if isinstance(data, dict) and data.get('format') == 'chronology_columns':
        columns, nodes = data.get('columns'), data.get('nodes')
        if (not isinstance(columns, list) or not columns
            or any(not isinstance(c, str) for c in columns)
            or len(set(columns)) != len(columns)
            or not isinstance(nodes, list) or len(nodes) != len(columns)
        ):
            raise ValueError('chronology_columns 表头或节点无效')

        normalized = {}
        for title, node in zip(columns, nodes):
            if not isinstance(node, dict) or node.get('title') != title:
                raise ValueError(f"表格节点与表头顺序不一致")
            normalized[title] = node.gert('content')

        data = normalized

    if not isinstance(data, dict) or not data:
        raise ValueError('表格必须包含至少一个表格')

    lengths = set()
    for header, cells in data.items():
        if not header.strip() or not isinstance(cells, list):
            raise ValueError('表头不能为空, 列内容必须时数组')

        if any(type(cell) not in (str, int, float) or (type(cell) is float and not math.isfinite(cell)) for cell in cells):
            raise ValueError('单元格必须是字符串或有限数字，空值请使用空字符串')
        lengths.add(len(cells))
    if len(lengths) != 1:
        raise ValueError('各列行数必须一致，缺失单元格请使用空字符串补齐')
    return data