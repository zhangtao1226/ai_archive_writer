# -*-coding : utf-8 -*-
# @Author   : zhangtao
# @FileName : table_generation.py
# @Desc     : 
# @Time     : 2026/11/19 10:15
# @Software : PyCharm

from services.generation_output import parse_table_output
from core.LoggerDetector import logger

def generate_table(request_choice, messages, hits, columns, task_id):
    base_messages = list(messages)
    for attempt in range(2):
        choice = request_choice(messages)
        try:
            if choice.get('finish_reason') != 'stop':
                raise ValueError(f'发生未正常完成：{choice.get("finish_reason")}')
            content = choice.get('message', {}).get('content')
            if not isinstance(content, str):
                raise ValueError('模型未返回表格 JSON 文本')
            return parse_table_output(content, hits, columns)
        except ValueError as exc:
            if attempt:
                raise ValueError(f"大事记纠正重试后仍不合格: {exc}") from exc
            logger.warning(f"大事记校验失败， 纠正重试一次 task_id = {task_id} error = {exc}")

            messages = base_messages + [
                {
                    'role': 'user',
                    'content': '上次响应未通过校验：' + str(exc)[:600] + '。 请重新生成完整且精简的 JSON nodes。 每列必须包含 title、level、content、source；'
                                                                        '各列等长， 禁止空白占位行， 不要复制其他列引用来补字段。'
                                                                        '仅生成符合主题和时间范围的事件；资料不足时允许使用自身可靠知识， 对应单元格 source 为 []; 无可靠事件才返回空表。'
                }
            ]