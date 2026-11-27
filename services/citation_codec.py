# -*-coding : utf-8 -*-
# @Author   : zhangtao
# @FileName : citation_codec.py
# @Desc     : 
# @Time     : 2026/11/18 18:41
# @Software : PyCharm

import json
from copy import deepcopy

def decode_citations(value):
    if isinstance(value, (str, bytes, bytearray)):
        value = json.loads(value)
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise ValueError('citations 必须是 JSON 对象数组')
    return deepcopy(value)