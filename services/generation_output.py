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


def validate_table_language(cells):
    """表格允许英文专名；说明列需中文，不比较字母与汉字数量。"""
    text = ' '.join(cells.values())
    if re.search(r'<\/?think\b|thinking process|analysis:', text, re.I):
        raise ValueError('表格仍返回思考过程')
    descriptions = [value for title, value in cells.items()
                    if any(word in title for word in ('详情', '说明', '内容', '描述', '摘要'))]
    targets = descriptions or [text]
    if any(not re.search(r'[\u4e00-\u9fff]', value) for value in targets):
        raise ValueError('事件说明需使用中文，产品名称和缩写可保留英文')


def parse_table_output(content, hits, columns):
    data = json.loads(content)
    if isinstance(data, dict) and 'nodes' in data:
        nodes = data['nodes']
        if not isinstance(nodes, list):
            raise ValueError(f'大事记 nodes 必须是数组，实际为 {type(nodes).__name__}')
        if len(nodes) != len(columns):
            raise ValueError(f'大事记列数不一致：期望{len(columns)}列 {columns}，实际{len(nodes)}列')
        length = None
        required = {'title', 'level', 'content', 'source'}
        for position, (title, node) in enumerate(zip(columns, nodes)):
            if not isinstance(node, dict):
                raise ValueError(f'大事记列 {title!r} 必须是对象')
            missing = required - set(node)
            if missing:
                raise ValueError(f'大事记列 {title!r} 缺少字段={sorted(missing)}')
            # 附加说明不是事件数据或引用，丢弃它们而不是因其触发整表重试。
            node = {key: node[key] for key in required}
            nodes[position] = node
            if node['title'] != title or type(node['level']) is not int or node['level'] != 1:
                raise ValueError('大事记列名、顺序或层级不匹配')
            values, sources = node['content'], node['source']
            if not isinstance(values, list) or not isinstance(sources, list):
                raise ValueError(f'列 {title!r} 的 content/source 必须是数组，实际类型为 {type(values).__name__}/{type(sources).__name__}')
            # 明确的空数组表示整列未引用，不伪造、不丢弃任何引用。
            if not sources:
                sources = [[] for _ in values]
                node['source'] = sources
            if len(values) != len(sources):
                raise ValueError(f'列 {title!r} 的 content/source 长度不一致：{len(values)}/{len(sources)}，非空引用不能自动补齐或截断')
            if title != '序号' and any(not isinstance(v, str) or not v.strip() for v in values):
                raise ValueError(f'大事记列 {title!r} 含空白或非字符串单元格，禁止占位行')
            if length is None:
                length = len(values)
            if len(values) != length:
                raise ValueError('大事记所有列的 content 长度必须一致')
            if title == '序号':
                # 展示序号由后端维护，不依赖模型的数字类型或编号。
                node['content'] = list(range(1, len(values) + 1))
                node['source'] = [[] for _ in values]
                sources = node['source']
            for ids in sources:
                if not isinstance(ids, list) or any(type(i) is not int or not 1 <= i <= len(hits) for i in ids):
                    raise ValueError('大事记 source 引用编号无效')
        all_citations = {}
        for index in range(length or 0):
            validate_table_language({n['title']: n['content'][index]
                                     for n in nodes if n['title'] != '序号'})
        for node in nodes:
            resolved = []
            for ids in node['source']:
                if node['title'] == '序号':
                    ids = []
                _, citations = parse_output(json.dumps({'body':'引用校验','citation_ids':ids}), hits)
                resolved.append(citations)
                all_citations.update({c['citation_id']:c for c in citations})
            node['source'] = resolved
        return json.dumps({'format':'chronology_columns', 'columns':columns, 'nodes':nodes}, ensure_ascii=False), list(all_citations.values())
    if not isinstance(data, dict) or set(data) != {'rows'} or not isinstance(data['rows'], list):
        raise ValueError('大事记必须返回包含 nodes 数组的 JSON 对象（兼容旧 rows 格式）')
    rows, all_citations = [], {}
    for index, row in enumerate(data['rows'], 1):
        if not isinstance(row, dict) or set(row) != {'cells', 'citation_ids'}:
            raise ValueError('大事记行结构无效')
        cells = row['cells']
        expected = set(columns) - {'序号'}
        if not isinstance(cells, dict) or set(cells) != expected or any(not isinstance(v, str) or not v.strip() for v in cells.values()):
            raise ValueError('大事记列名或单元格内容无效')
        validate_table_language(cells)
        _, citations = parse_output(json.dumps({'body':'引用校验',
            'citation_ids':row['citation_ids']}, ensure_ascii=False), hits)
        ordered = {key: str(index) if key == '序号' else cells[key] for key in columns}
        rows.append({'cells': ordered, 'citations': citations})
        all_citations.update({c['citation_id']:c for c in citations})
    return json.dumps({'format':'chronology_table', 'columns':columns, 'rows':rows}, ensure_ascii=False), list(all_citations.values())
