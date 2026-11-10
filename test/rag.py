# -*-coding  : utf-8 -*-
# @Author    : zhangtao
# @File      : rag.py
# @Desc      : 
# @Time      : 2026/11/5 13:14
# @Software  : PyCharm

class SimpleRAG:
    """
    简化版 RAG 系统实现
    包含三个核心组件：嵌入器、向量存储、生成器
    """

    def __init__(self, embedder, vector_store, generator):
        # 嵌入器：负责把文本转换为向量
        self.embedder = embedder
        # 向量数据库：负责存储向量并支持相似度检索
        self.vector_store = vector_store
        # 生成器：基于上下文生成回答
        self.generator = generator

    def add_documents(self, documents):
        """
        将文档添加到知识库
        :param documents: 原始文档列表（每个元素是一段完整文本）
        """
        # 第一步：把长文档切分为较小的文本块，便于精确检索
        chunks = self.chunk_documents(documents)

        # 第二步：将所有文本块转换为向量
        embeddings = self.embedder.embed(chunks)

        # 第三步：把向量与对应的原文一起存入向量数据库
        self.vector_store.add(embeddings, chunks)

    def chunk_documents(self, documents, chunk_size=500, overlap=50):
        """
        文档切分：把长文档拆成固定长度、有一定重叠的文本块

        :param documents: 原始文档列表
        :param chunk_size: 每个文本块的字符数
        :param overlap: 相邻文本块之间的重叠字符数（避免语义在切分处被截断）
        :return: 切分后的文本块列表
        """
        chunks = []
        for doc in documents:
            # 按 (chunk_size - overlap) 的步长滑动切分，保留一定重叠区域
            for i in range(0, len(doc), chunk_size - overlap):
                chunk = doc[i:i + chunk_size]
                chunks.append(chunk)
        return chunks

    def query(self, question, top_k=5):
        """
        处理用户查询，返回生成的回答

        :param question: 用户提出的问题
        :param top_k: 检索时返回的相关文本块数量
        :return: 生成模型给出的最终回答
        """
        # 1. 把问题转换为向量，才能与知识库中的向量做比较
        question_embedding = self.embedder.embed([question])[0]

        # 2. 在向量数据库中检索最相似的 top_k 个文本块
        results = self.vector_store.search(question_embedding, top_k)

        # 3. 把检索到的文本块拼接成上下文
        context = "\n".join([doc for doc, _ in results])

        # 4. 把上下文和原始问题一起组织成提示词
        prompt = f"基于以下内容回答问题：\n{context}\n\n问题：{question}"

        # 5. 交给生成模型产出最终回答
        return self.generator.generate(prompt)


class AdvancedRAG:
    """
    高级 RAG 系统
    在基础流程之上增加重排序环节
    """

    def __init__(self, embedder, vector_store, reranker, generator):
        # 嵌入器
        self.embedder = embedder
        # 向量数据库
        self.vector_store = vector_store
        # 重排序模型（交叉编码器），用于精细化排序
        self.reranker = reranker
        # 生成器
        self.generator = generator

    def query(self, question, initial_k=20, final_k=5):
        """
        处理查询，包含"粗筛 + 精排"两阶段检索

        :param question: 用户问题
        :param initial_k: 第一阶段向量检索返回的候选数量
        :param final_k: 重排序后最终保留的数量
        """
        # ==================== 阶段1：初步检索（粗筛） ====================
        # 把问题转换为向量
        question_embedding = self.embedder.embed([question])[0]

        # 用向量相似度快速召回一批候选文本（速度快，精度一般）
        initial_results = self.vector_store.search(
            question_embedding,
            initial_k
        )

        # ==================== 阶段2：重排序（精排） ====================
        # 构造 (问题, 候选文档) 配对，交给交叉编码器逐一打分
        doc_pairs = [(question, doc) for doc, _ in initial_results]

        # 交叉编码器会同时编码问题和文档，能更精确地判断两者的相关性
        reranked = self.reranker.rerank(doc_pairs)

        # 取重排序后真正最相关的 final_k 条
        final_context = "\n".join([doc for doc, _ in reranked[:final_k]])

        # ==================== 阶段3：生成 ====================
        prompt = f"上下文：{final_context}\n\n问题：{question}"
        return self.generator.generate(prompt)
