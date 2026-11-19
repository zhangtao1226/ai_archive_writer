"""将已保存的事件行转为前端要求的列式 nodes。"""
from copy import deepcopy
from services.citation_codec import decode_citations


def table_to_nodes(table):
    if not isinstance(table, dict):
        raise ValueError('大事记表格必须是对象')
    columns, rows = table.get('columns'), table.get('rows')
    if not isinstance(columns, list) or not all(isinstance(c, str) for c in columns) or len(set(columns)) != len(columns) or not isinstance(rows, list):
        raise ValueError('大事记列或行格式无效')
    nodes = [{'title': title, 'level': 1, 'content': [], 'source': []} for title in columns]
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict) or not isinstance(row.get('cells'), dict) or set(row['cells']) != set(columns):
            raise ValueError('大事记行与表头不匹配')
        citations = decode_citations(row.get('citations', []))
        for node in nodes:
            value = row['cells'][node['title']]
            if not isinstance(value, (str, int, float)) or isinstance(value, bool):
                raise ValueError('大事记单元格格式无效')
            node['content'].append(index if node['title'] == '序号' else value)
            node['source'].append(deepcopy(citations))
    return nodes
