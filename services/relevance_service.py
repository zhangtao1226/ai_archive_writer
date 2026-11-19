"""相关性筛选最多纠正一次；异常不等同于无相关资料。"""
import json
import logging
from prompts.prompt_template import build_relevance_messages

logger = logging.getLogger(__name__)


def parse_relevance(content, count):
    if not isinstance(content, str):
        raise ValueError('相关性输出必须是 JSON 文本')
    data = json.loads(content)
    if not isinstance(data, dict) or 'relevant_ids' not in data:
        shape = sorted(data) if isinstance(data, dict) else type(data).__name__
        raise ValueError(f'缺少 relevant_ids 数组，实际结构={shape}')
    # 模型附带 reason 等说明不影响编号解析，不将这些字段传入生成流程。
    ids = data['relevant_ids']
    if not isinstance(ids, list) or any(type(i) is not int or not 1 <= i <= count for i in ids):
        raise ValueError(f'relevant_ids 必须是1至{count}的整数数组，无相关资料返回 []')
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
                raise ValueError(f"相关性判断未正常完成: {choice.get('finish_reason')}")
            ids = parse_relevance(choice.get('message', {}).get('content'), len(hits))
            return [hit for i, hit in enumerate(hits, 1) if i in ids]
        except ValueError as exc:
            if attempt:
                raise ValueError(f'资料相关性纠正重试后仍无效: {exc}') from exc
            logger.warning('资料相关性格式校验失败，重试一次: %s', exc)
            messages = base + [{'role':'user', 'content':
                '上次响应格式错误：' + str(exc)[:500] +
                '。这一步只筛选候选资料，不生成事件或表格。'
                '必须返回 {"relevant_ids":[1,2]}，编号仅作示例。'
                '只填写直接相关的实际候选编号，没有相关资料时返回 {"relevant_ids":[]}。'}]
