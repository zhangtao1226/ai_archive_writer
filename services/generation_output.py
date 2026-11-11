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
