# -*-coding  : utf-8 -*-
# @Author    : zhangtao
# @File      : indexing.py
# @Desc      : Chroma 持久化知识库：文本写入、文件导入及语义查询
# @Time      : 2026/11/6 10:50
# @Software  : PyCharm
from hashlib import sha256
from pathlib import Path
from typing import Any

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from rag.chunking import split_text
from rag.readers import extract_text
from core.config import configs
from rag.reranking import Reranker

class KnowledgeBase:
    def __init__(self, collection_name="archive_knowledge", embedding_function=None, reranker=None):
        if embedding_function is None and not Path(configs.embedding_model_path).is_dir():
            raise FileNotFoundError(f"嵌入模型目录不存在，请配置 embedding_model_path：{configs.embedding_model_path}")
        self.reranker = reranker if reranker is not None else Reranker(
            configs.reranker_model_path, configs.reranker_device, configs.reranker_batch_size)
        self.client = chromadb.PersistentClient(path=configs.knowledge_db_patth)
        embedding = embedding_function if embedding_function is not None else SentenceTransformerEmbeddingFunction(
            model_name=configs.embedding_model_path, device=configs.embedding_device, normalize_embeddings=True)
        self.collection = self.client.get_or_create_collection(name=collection_name, embedding_function=embedding)

    def write(self, text: str, source: str, metadata: dict[str, Any] | None = None,
              chunk_size: int = 800, chunk_overlap: int = 120, should_continue=None, return_info=False):
        """相同来源和相同分块内容重复导入时覆盖，不删除已有资料。"""
        if not source.strip():
            raise ValueError("source 不能为空")
        chunks = split_text(text, chunk_size, chunk_overlap)
        if not chunks:
            raise ValueError("写入文本不能为空")
        metadata = dict(metadata or {})
        if any(not isinstance(v, (str, int, float, bool)) for v in metadata.values()):
            raise ValueError("metadata 值必须为字符串、数字或布尔值")
        ids = [sha256(f"{source}\0{i}\0{chunk}".encode()).hexdigest()
               for i, chunk in enumerate(chunks)]
        for start in range(0, len(chunks), 100):
            if should_continue is not None and not should_continue():
                raise InterruptedError("入库窗口已结束或服务正在关闭")
            end = start + 100
            self.collection.upsert(
                ids=ids[start:end], documents=chunks[start:end],
                metadatas=[{**metadata, "source": source, "chunk_index": i}
                           for i in range(start, min(end, len(chunks)))])
        if return_info:
            return {"collection_name": self.collection.name, "chunk_count": len(chunks),
                    "written_count": len(chunks), "chunk_ids": ids,
                    "embedding_model": configs.embedding_model_path,
                    "chunk_size": chunk_size, "chunk_overlap": chunk_overlap}
        return len(chunks)

    def write_file(self, file_path, **kwargs) -> int:
        path = Path(file_path).expanduser().resolve()
        return self.write(extract_text(path.read_bytes(), path.suffix), source=str(path), **kwargs)

    def query(self, text: str, top_k: int = 5, where: dict | None = None,
              initial_k: int | None = None, rerank: bool | None = None) -> list[dict]:
        if not text.strip() or top_k <= 0:
            raise ValueError("查询不能为空且 top_k 必须大于 0")
        enabled = configs.rag_rerank_enabled if rerank is None else rerank
        candidates = max(configs.rag_initial_k, top_k) if initial_k is None else initial_k
        if candidates <= 0 or (enabled and candidates < top_k):
            raise ValueError("initial_k 必须为正数，且精排时不能小于 top_k")
        count = self.collection.count()
        if count == 0:
            return []
        options = {"where": where} if where else {}
        result = self.collection.query(query_texts=[text], n_results=min(candidates if enabled else top_k, count),
                                       include=["documents", "metadatas", "distances"], **options)
        hits = [{"id": id_, "text": doc, "metadata": meta, "distance": distance}
                for id_, doc, meta, distance in zip(result["ids"][0], result["documents"][0],
                                                   result["metadatas"][0], result["distances"][0])]

        return self.reranker.rerank(text, hits, top_k) if enabled else hits
