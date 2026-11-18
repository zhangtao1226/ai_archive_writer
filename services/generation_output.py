# -*-coding  : utf-8 -*-
# @Author    : zhangtao
# @File      : generation_output.py
# @Desc      : 校验最终正文，只将模型明确使用的资料编号映射为引用
# @Time      : 2026/11/6 10:50
# @Software  : PyCharm

import json
import re


def parse_output(content, hits):
    if not isinstance(content, str):
        raise ValueError('模型未返回文本')
    data = json.loads(content)
    body = data.get('body')
    ids = data.get('citation_ids')
    if not isinstance(body, str) or not body.strip():
        raise ValueError('模型返回空正文')
    if re.search(r'<\/?think\b|thinking process|analysis:', body, re.I):
        raise ValueError('模型仍返回思考过程，请检查模型聊天模板')
    chinese = len(re.findall(r'[\u4e00-\u9fff]', body))
    english = len(re.findall(r'[A-Za-z]', body))
    if not chinese or english > chinese:
        raise ValueError('正文不是以中文为主')
    if not isinstance(ids, list) or any(type(i) is not int or not 1 <= i <= len(hits) for i in ids):
        raise ValueError('引用编号无效')
    citations = []
    for i in dict.fromkeys(ids):
        hit = hits[i-1]
        citations.append({'citation_id': i, 'chunk_id': hit.get('id'),
                          'text': hit['text'], 'metadata': hit.get('metadata') or {},
                          'distance': hit.get('distance'), 'rerank_score': hit.get('rerank_score')})
    return body.strip(), citations


def parse_table_output(content, hits, columns):
    data = json.loads(content)
    if isinstance(data, dict) and 'nodes' in data:
        nodes = data['nodes']
        if set(data) != {'nodes'} or not isinstance(nodes, list) or len(nodes) != len(columns):
            raise ValueError('大事记 nodes 必须与表头列数一致')
        length = None
        for title, node in zip(columns, nodes):
            if not isinstance(node, dict) or set(node) != {'title', 'level', 'content', 'source'}:
                raise ValueError('大事记列结构无效')
            if node['title'] != title or type(node['level']) is not int or node['level'] != 1:
                raise ValueError('大事记列名、顺序或层级不匹配')
            values, sources = node['content'], node['source']
            if not isinstance(values, list) or not isinstance(sources, list) or len(values) != len(sources):
                raise ValueError('大事记 content/source 必须为等长数组')
            if length is None:
                length = len(values)
            if len(values) != length:
                raise ValueError('大事记所有列的 content 长度必须一致')
            if title == '序号' and any(type(v) is not int or v != i for i, v in enumerate(values, 1)):
                raise ValueError('序号必须为从1开始的连续整数')
            for ids in sources:
                if not isinstance(ids, list) or any(type(i) is not int or not 1 <= i <= len(hits) for i in ids):
                    raise ValueError('大事记 source 引用编号无效')
        data = {'rows': [
            {'cells': {n['title']: n['content'][i] for n in nodes if n['title'] != '序号'},
             'citation_ids': list(dict.fromkeys(cid for n in nodes for cid in n['source'][i]))}
            for i in range(length or 0)]}
    if not isinstance(data, dict) or set(data) != {'rows'} or not isinstance(data['rows'], list):
        raise ValueError('大事记必须返回 rows 数组')
    rows, all_citations = [], {}
    for index, row in enumerate(data['rows'], 1):
        if not isinstance(row, dict) or set(row) != {'cells', 'citation_ids'}:
            raise ValueError('大事记行结构无效')
        cells = row['cells']
        expected = set(columns) - {'序号'}
        if not isinstance(cells, dict) or set(cells) != expected or any(not isinstance(v, str) or not v.strip() for v in cells.values()):
            raise ValueError('大事记列名或单元格内容无效')
        if not row['citation_ids']:
            raise ValueError('大事记事件必须有引用依据')
        _, citations = parse_output(json.dumps({'body':' '.join(cells.values()),
            'citation_ids':row['citation_ids']}, ensure_ascii=False), hits)
        ordered = {key: str(index) if key == '序号' else cells[key] for key in columns}
        rows.append({'cells': ordered, 'citations': citations})
        all_citations.update({c['citation_id']:c for c in citations})
    return json.dumps({'format':'chronology_table', 'columns':columns, 'rows':rows}, ensure_ascii=False), list(all_citations.values())
