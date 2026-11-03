# -*-coding  : utf-8 -*-
# @Author    : zhangtao
# @File      : config.py
# @Desc      : 配置加载与路径管理
# @Time      : 2026/10/28 11:18
# @Software  : PyCharm

from pathlib import Path
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


current_file_path = Path(__file__).resolve()
root_path = current_file_path.parent.parent

class Configs(BaseSettings):

    # 模型路径
    model_path: str = f"{root_path}/resources/models/Qwen3.8-27B"

    # 业务数据地址
    application_db_patth: str = f"{root_path}/resources/databases/application.db"
    # 知识数据地址
    knowledge_db_patth: str = f"{root_path}/resources/databases/knowledge.db"
    # 工作流检查点与恢复状态数据地址
    checkpoint_db_patth: str = f"{root_path}/resources/databases/checkpoint.db"

    # 日志文件配置信息
    log_info: dict = {
        "log_name": "app",
        "log_level": "INFO",
        "log_dir": f"{root_path}/logs",
        "log_size": 50,
        "log_retention": 7,
    }

configs = Configs()
