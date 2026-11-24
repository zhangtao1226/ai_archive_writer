# -*-coding  : utf-8 -*-
# @Author    : zhangtao
# @File      : chat_stream.py
# @Desc      : SSE 编码及模型 JSON 正文的增量提取
# @Time      : 2026/11/3 17:19
# @Software  : PyCharm

import json
import re


def sse(event, data):
    """把事件名称和数据编码为一条完整 SSE 消息。"""
    return f'event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n'


def partial_body(raw):
    """提取尚未完整的 JSON body 字符串；保留未完成转义，等待下一片段。"""
    match = re.search(r'"body"\s*:\s*"', raw)
    if not match:
        return ''
    start = match.end()
    i = start
    while i < len(raw):
        if raw[i] == '"':
            return json.loads('"' + raw[start:i] + '"')
        if raw[i] == '\\':
            if i + 1 >= len(raw):
                break
            length = 6 if raw[i+1] == 'u' else 2
            if i + length > len(raw):
                break
            i += length
        else:
            i += 1
    value = json.loads('"' + raw[start:i] + '"')
    # UTF-16代理对可能跨片段，不把半个字符发给客户端。
    return value.rstrip(''.join(chr(c) for c in range(0xD800, 0xE000)))


def partial_table(raw, allow_direct=False):
    """提取 table 对象的原始 JSON 增量，忽略字符串中的括号。"""
    match = re.match(r'\s*\{\s*"table"\s*:\s*\{', raw)
    if not match:
        if allow_direct and re.match(r'\s*\{\s*"(?:[^"\\]|\\.)*"\s*:\s*\[', raw):
            return raw.lstrip()
        return ''
    start = match.end() - 1
    depth, quoted, escaped = 0, False, False
    for index in range(start, len(raw)):
        char = raw[index]
        if quoted:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                return raw[start:index + 1]
    return raw[start:]
