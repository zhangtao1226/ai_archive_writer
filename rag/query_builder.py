# -*-coding  : utf-8 -*-
# @Author    : zhangtao
# @File      : query_builder.py
# @Desc      : 将立项信息转换成语义检索文本
# @Time      : 2026/11/3 17:19
# @Software  : PyCharm

def build_retrieval_query(*, title: str, type: str, description: str = "",
                          person: str = "", time_range: str = "", directory_template: str = "") -> str:
    fields = (("选题名称", title), ("选题说明", description),
              ("责任人", person), ("时间范围", time_range), ("编研类型", type), ("目录模板", directory_template))
    lines = []
    for label, value in fields:
        if not isinstance(value, str):
            raise ValueError(f"{label}必须为字符串")
        value = " ".join(value.split())
        if label in {"编研主题", "编研类型"} and not value:
            raise ValueError(f"{label}不能为空")
        if label == "目录模板" and value == "":
            continue
        if value:
            lines.append(f"{label}：{value}")
    return "\n".join(lines)
