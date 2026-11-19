"""表格输出仅允许一次纠正重试，不掩盖 HTTP 或存储异常。"""
from services.generation_output import parse_table_output
from core.LoggerDetector import logger


def generate_table(request_choice, messages, hits, columns, task_id):
    base_messages = list(messages)
    for attempt in range(2):
        choice = request_choice(messages)
        try:
            if choice.get('finish_reason') != 'stop':
                raise ValueError(f"生成未正常完成：{choice.get('finish_reason')}")
            content = choice.get('message', {}).get('content')
            if not isinstance(content, str):
                raise ValueError('模型未返回表格 JSON 文本')
            return parse_table_output(content, hits, columns)
        except ValueError as exc:
            if attempt:
                raise ValueError(f'大事记纠正重试后仍不合格: {exc}') from exc
            logger.warning(f'大事记校验失败，纠正重试一次 task_id={task_id} error={exc}')
            # 不重复附带错误长输出，防止占满上下文；保留同一资料编号。
            messages = base_messages + [{'role':'user', 'content':
                '上次响应未通过校验：' + str(exc)[:600] +
                '。请重新生成完整且精简的 JSON nodes。每列必须包含 title、level、content、source；'
                '各列等长，禁止空白占位行，不要复制其他列引用来补字段。'
                '仅生成资料支持且在时间范围内的事件；资料不足时保留所有表头，各列 content/source 均为 []。'}]
