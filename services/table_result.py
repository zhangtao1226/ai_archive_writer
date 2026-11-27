# -*-coding : utf-8 -*-
# @Author   : zhangtao
# @FileName : table_result.py
# @Desc     : 大事件输出表格格式
# @Time     : 2026/11/18 19:48
# @Software : PyCharm

from copy import deepcopy

from services.citation_codec import decode_citations

def table_to_nodes(table):
    if not isinstance(table, dict):
        raise ValueError('大事记表格必须是对象')

    if table.get('format') != 'chronology_table':
        nodes = table.get('nodes')
        columns = table.get('columns')
        if not isinstance(nodes, list) or not isinstance(columns, list) or len(nodes) != len(columns):
            raise ValueError(f"大事记列式数据无效")

        length = None
        for title, node in zip(columns, nodes):
            if not isinstance(node, dict) or node.get('title') != title or not isinstance(node.get('content'), list) or not isinstance(node.get('source'), list):
                raise ValueError('大事记列式节点无效')

            if length is None:
                length = len(node['content'])

            if len(node['content']) != length or len(node['source']) != length:
                raise ValueError('大事记列式数组长度不一致')

            for sources in node['source']:
                decode_citations(sources)

        return deepcopy(nodes)

    columns, rows = table.get('columns'), table.get('rows')
    if not isinstance(columns, list) or not all(isinstance(c, str) for c in columns) or len(set(columns)) != len(columns) or not isinstance(rows, list):
        raise ValueError('大事记列或行格式无效')

    nodes = [{'title': title, 'level':1, 'content':[], 'source': []} for title in columns]
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict) or not isinstance(row.get('cells'), dict) or set(row['cells']) != set(columns):
            raise ValueError('大事记行与表头不匹配')

        citations = decode_citations(row.get('citations', []))
        for node in nodes:
            value = row['cells'][node['title']]
            if not isinstance(value, (str, int, float)) or isinstance(value, bool):
                raise ValueError('大事记单元格式无效')
            node['content'].append(index if node['title'] == '序号' else value)
            if node['title'] not in ('序号', '日期', '备注', '时间', '节点'):
                node['source'].append(deepcopy(citations))
        return nodes