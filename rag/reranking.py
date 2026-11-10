# -*-coding  : utf-8 -*-
# @Author    : zhangtao
# @File      : reranking.py
# @Desc      : 交叉编码器精排；模型在首次查询时加载
# @Time      : 2026/11/6 10:50
# @Software  : PyCharm

import math
from threading import Lock


class Reranker:
    def __init__(self, model_name, device="cpu", batch_size=16):
        self.model_name = model_name
        self.device = device
        self.batch_size = batch_size
        self._model = None
        self._lock = Lock()

    def rerank(self, question, documents, top_k):
        if top_k <= 0:
            raise ValueError("top_k 必须大于 0")
        if not documents:
            return []
        with self._lock:
            if self._model is None:
                from sentence_transformers import CrossEncoder
                self._model = CrossEncoder(self.model_name, device=self.device)
            scores = self._model.predict(
                [(question, doc["text"]) for doc in documents],
                batch_size=self.batch_size, show_progress_bar=False)
        if len(scores) != len(documents):
            raise ValueError("重排序模型返回的分数数量不匹配")
        ranked = []
        for doc, score in zip(documents, scores):
            value = float(score)
            if not math.isfinite(value):
                raise ValueError("重排序模型返回无效分数")
            ranked.append({**doc, "rerank_score": value})
        return sorted(ranked, key=lambda doc: doc["rerank_score"], reverse=True)[:top_k]
