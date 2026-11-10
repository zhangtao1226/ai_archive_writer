# -*-coding  : utf-8 -*-
# @Author    : zhangtao
# @File      : config.py
# @Desc      : 配置加载与路径管理
# @Time      : 2026/10/28 11:18
# @Software  : PyCharm

from pathlib import Path
from typing import Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


current_file_path = Path(__file__).resolve()
root_path = current_file_path.parent.parent

class Configs(BaseSettings):

    vllm_base_url: str = "http://127.0.0.1:8001/v1"
    vllm_model_name: str = "Qwen3.8-27B"
    vllm_api_key: str = "EMPTY"
    vllm_timeout_seconds: float = Field(default=300, gt=0)
    vllm_max_tokens: int = Field(default=4096, ge=1)
    llm_context_max_chars: int = Field(default=20000, ge=1)

    # 推理模型路径
    llm_model_path: str = f"{root_path}/resources/models/"
    #嵌入模型路径
    embedding_model_path: str = f"{root_path}/resources/embeddings/Embedding_model"

    # 两阶段检索：先召回候选，再用交叉编码器重排序
    rag_rerank_enabled: bool = True
    rag_initial_k: int = Field(default=20, ge=1)
    reranker_model_path: str = "BAAI/bge-reranker-v2-m3"
    reranker_device: str = "cpu"
    reranker_batch_size: int = Field(default=16, ge=1)


    # 业务数据地址
    application_db_patth: str = f"{root_path}/resources/databases/application.db"
    # 知识数据地址
    knowledge_db_patth: str = f"{root_path}/resources/databases/chroma_db"
    # 工作流检查点与恢复状态数据地址
    checkpoint_db_patth: str = f"{root_path}/resources/databases/checkpoint.db"

    # 入库时间设置（北京时间，支持跨午夜，例如 23:00 到 06:00）
    rag_scheduler_enabled: bool = False
    start_time: str = "08:00"
    end_time: str = "06:00"
    rag_timezone: str = "Asia/Shanghai"
    rag_scan_interval_seconds: int = Field(default=60, ge=1)
    # 待入库的 TXT/Markdown 原始资料目录，启动时自动创建；与 Chroma 存储目录分开
    rag_source_dir: str = f"{root_path}/resources/knowledge"
    embedding_device: str = "cpu"

    # 日志文件配置信息
    log_info: dict = {
        "log_name": "app",
        "log_level": "INFO",
        "log_dir": f"{root_path}/logs",
        "log_size": 50,
        "log_retention": 7,
    }

configs = Configs()
