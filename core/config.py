# -*-coding : utf-8 -*-
# @Author   : zhangtao
# @FileName : config.py
# @Desc     : 
# @Time     : 2026/11/9 11:23
# @Software : PyCharm

import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

load_dotenv(verbose=True)

current_file_path = Path(__file__).resolve()
root_path = current_file_path.parent.parent

class Config(BaseSettings):

    material_api_base_url: str = os.getenv("BASE_API_URL", "")
    material_contain_row: bool = True
    material_unlimited_row: int = Field(default=50, ge=1)
    material_api_url: str = os.getenv("MATERIAL_API_URL", "")
    material_api_callback_url: str = os.getenv("MATERIAL_API_CALLBACK_URL", "")
    material_attachment_download_path: str = os.getenv("MATERIAL_ATTACHMENT_DOWNLOAD_PATH", "")
    material_callback_retry_seconds: int = Field(default=60, ge=1)
    material_api_token: str = ""
    material_api_api_key: str = "erren_lantai_2026"
    material_attachment_root: str = ""
    material_api_timeout_seconds: float = Field(default=30, ge=0)
    material_attachment_max_bytes: int = Field(default=20 * 1024 * 1024, ge=1)

    vllm_base_url: str = os.getenv("VLLM_BASE_URL", "")
    vllm_model_name: str = os.getenv("VLLM_MODEL_NAME", "")
    vllm_api_key: str = "EMPTY"
    vllm_timeout_seconds: float = Field(default=300, gt=0)
    chat_context_tokens: int = Field(default=4096, ge=512)
    chat_max_tokens: int = Field(default=2048, ge=1)
    vllm_max_tokens: int = Field(default=4096, ge=1)
    llm_context_max_chars: int = Field(default=20000, ge=1)

    # 嵌入模型路径
    embedding_model_path:str = f"{root_path}/resources/models/Qwen3-Embedding-4B"

    # RAG 召回候选， 再用交叉编码器重排序
    rag_rerank_enabled: bool = True
    rag_initial_k: int = Field(default=10, ge=1)
    reranker_model_path: str = f"{root_path}/resources/models/bge-reranker-v2-m3"
    reranker_device: str = "cuda:0"
    reranker_batch_size: int = Field(default=16, ge=1)

    # 业务数据库地址
    application_db_path: str = f"{root_path}/resources/databases/application.db"
    # 知识库数据地址
    knowledge_db_path: str = f"{root_path}/resources/databases/chroma_db"
    # 工作流检查点
    checkpoint_db_path: str = f"{root_path}/resources/databases/checkpoint.db"

    # RAG定时任务设置(支持跨午夜， 如：23：00 到 06：00)
    rag_scheduler_enabled: bool = True
    start_time:str = "08:00"
    end_time:str = "06:00"
    rag_timezone:str = "Asia/Shanghai"
    rag_scan_interval_seconds: int = Field(default=300, ge=1)

    # 待入库的原始资料库（临时测试用）
    rag_default_category_id: str = "unassigned"
    rag_source_dir: str = f"{root_path}/resources/knowledge"
    embedding_device: str = "cuda:0"

    # 日志配置
    log_info: dict = {
        "log_name": "app",
        "log_level": "INFO",
        "log_dir": f"{root_path}/logs",
        "log_size": 50,
        "log_retention": 7
    }

configs = Config()


