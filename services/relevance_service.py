# -*-coding : utf-8 -*-
# @Author   : zhangtao
# @FileName : research_request.py
# @Desc     : 重排序后的主题筛选；格式/服务错误不伪装成知识库无资料
# @Time     : 2026/11/18 15:36
# @Software : PyCharm

import json
from core.LoggerDetector import logger
from prompts.prompt_template import build_relevance_messages


def parse_relevance(content, count):
    if not isinstance(content, str):
        raise ValueError('相关性输出必须是 JSON 文本')

    data = json.loads(content)
    if not isinstance(data, dict) or 'relevant_ids' not in data:
        shape = sorted(data) if isinstance(data, dict) else type(data).__name__
        raise ValueError(f"缺少 relevant_ids 数组，实际结构={shape}")

    ids = data['relevant_ids']
    if not isinstance(ids, list) or any(type(i) is not int or not 1 <= i <= count for i in ids):
        raise ValueError(f'relevant_ids 必须是1至{count}的整数数组， 无相关资料返回 []')
    return set(ids)

def filter_relevant_hits(request_choice, project, hits):
    if not hits:
        return []
    base = build_relevance_messages(project, hits)
    messages = base
    for attempt in range(2):
        choice = request_choice(messages)
        try:
            if choice.get('finish_reason') != 'stop':
                raise ValueError(f'资料相关性判断未正常完成; {choice.get("finish_reason")}')
            ids = parse_relevance(choice.get('message', {}).get('content'), len(hits))
            return [hit for i, hit in enumerate(hits, 1) if i in ids]
        except ValueError as exc:
            if attempt:
                raise ValueError(f"资料相关纠正重试后仍无效：{exc}")
            logger.warning(f'资料相关性格式校验失败， 重试一下：{exc}')
            messages = base + [
                {
                    'role': 'user',
                    'content': '上次响应格式错误：' + str(exc)[:500] +
                    '。 这一步只筛选资料， 不生成事件或表格。'
                    '必须返回 {"relevant_ids": [1,2]}, 编号仅做示例。'
                    '只填写直接相关的实际候选编号， 没有相关资料时返回 {"relevant_ids":[]}'
                }
            ]
