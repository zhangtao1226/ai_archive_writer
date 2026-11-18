"""兼容文本列及已被 ORM/服务层解析的引用数组。"""
import json
from copy import deepcopy


def decode_citations(value):
    if isinstance(value, (str, bytes, bytearray)):
        value = json.loads(value)
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise ValueError('citations 必须是 JSON 对象数组')
    return deepcopy(value)
