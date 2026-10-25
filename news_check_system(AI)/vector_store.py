# -*- coding: utf-8 -*-
"""
vector_store.py —— 检索层（存储侧 + 检索策略）

职责：
  - get_milvus()    连接 Milvus 并确保独立库存在
  - build_index()   把切块(文本+来源)向量化后写入 Milvus（幂等：条数一致则跳过）
  - retrieve()      混合检索：向量路(Milvus 余弦) + BM25 词法路 → RRF 融合(粗排)
                    → Rerank 精排 → 返回 top-k 的 [(文本, 来源, 分数)]
                    对外签名不变，调用方无需感知内部升级。
"""
from __future__ import annotations

from langchain_core.documents import Document

from config import (COLLECTION, DIM, K_FUSE, K_LEXICAL, K_VECTOR,
                    MILVUS_DB, MILVUS_URI, RRF_K, TOPK)
from reranker import rerank as _rerank

# ---------- 词法路：LangChain BM25Retriever（中文需传 jieba 分词） ----------
_bm25 = None   # 缓存，一次构建复用


def _ensure_bm25(client):
    """从 Milvus 全量取回语料，用 LangChain BM25Retriever 构建词法索引（缓存复用）。"""
    global _bm25
    if _bm25 is None:
        from langchain_community.retrievers import BM25Retriever

        import jieba

        rows = client.query(collection_name=COLLECTION,
                            output_fields=["text", "source"], limit=10000)
        _bm25 = BM25Retriever.from_texts(
            texts=[r.get("text", "") for r in rows],
            metadatas=[{"source": r.get("source", "")} for r in rows],
            preprocess_func=lambda t: [w for w in jieba.lcut(t)
                                       if w.strip() and w not in
                                       " \t\n，。；：？！、（）【】《》“”‘’…—-,.;:!?()[]{}<>\"'"],
        )
        print(f"[bm25] LangChain BM25Retriever 就绪：{len(rows)} 条")
    return _bm25


def _lexical_recall(client, query: str, k: int) -> list[tuple[str, str, float]]:
    """BM25 词法路召回 top-k，返回 [(文本, 来源, 分数)]（按相关度已降序，分数仅占位）。"""
    retriever = _ensure_bm25(client)
    retriever.k = k
    docs = retriever.invoke(query)          # invoke 内部按 BM25 分数降序返回
    return [(d.page_content, d.metadata.get("source", ""), 0.0) for d in docs]


def _rrf_fuse(vector_hits: list[tuple[str, str, float]],
              lexical_hits: list[tuple[str, str, float]],
              top: int) -> list[dict]:
    """RRF 融合（粗排）：只按排名打分 score=Σ 1/(rrf_k+rank)，两路同片段合并去重。"""
    rrf: dict[tuple[str, str], float] = {}
    for path in (vector_hits, lexical_hits):
        for rank, (text, source, _) in enumerate(path, start=1):
            key = (text, source)
            rrf[key] = rrf.get(key, 0.0) + 1.0 / (RRF_K + rank)
    merged = sorted(rrf.items(), key=lambda kv: kv[1], reverse=True)[:top]
    return [{"text": t, "source": s, "rrf": score} for (t, s), score in merged]


# ---------------- Milvus 连接 / 建集合 / 入库 ----------------
def get_milvus():
    """连接 Milvus，并确保独立库存在。"""
    from pymilvus import MilvusClient

    client = MilvusClient(MILVUS_URI)
    if MILVUS_DB not in client.list_databases():
        client.create_database(MILVUS_DB)
    client.use_database(MILVUS_DB)
    return client


def build_index(docs: list[Document], embeddings, force: bool = False) -> None:
    """把切块(文本+来源)向量化后写入 Milvus；集合已就绪则跳过（幂等）。

    force=True 时强制重建：清空集合、重新向量化并入库。
    """
    from pymilvus import DataType
    from pymilvus.milvus_client import IndexParams

    client = get_milvus()
    exists = client.has_collection(COLLECTION)
    count = client.get_collection_stats(COLLECTION)["row_count"] if exists else 0
    if exists and count == len(docs) and not force:
        print(f"[milvus] 集合已就绪：{len(docs)} 条，跳过向量化")
        return

    if exists:
        client.drop_collection(COLLECTION)
    # 显式 schema：int64 自增主键 + 文本 + 来源 + 向量；HNSW 索引在建集时一并配置
    schema = client.create_schema(auto_id=False, enable_dynamic_field=False)
    schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True, auto_id=True)
    schema.add_field(field_name="text", datatype=DataType.VARCHAR, max_length=2048)
    schema.add_field(field_name="source", datatype=DataType.VARCHAR, max_length=256)
    schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=DIM)
    index = IndexParams()
    index.add_index(field_name="vector", index_type="HNSW", metric_type="COSINE",
                    params={"M": 16, "efConstruction": 200})
    client.create_collection(collection_name=COLLECTION, schema=schema, index_params=index)

    texts = [d.page_content for d in docs]
    sources = [d.metadata.get("source", "") for d in docs]
    vectors = embeddings.embed_documents(texts)          # 向量化
    for i in range(0, len(docs), 64):                    # 分批入库：文本 + 来源 + 向量
        data = [{"text": t, "source": s, "vector": v}
                for t, s, v in zip(texts[i:i + 64], sources[i:i + 64], vectors[i:i + 64])]
        client.insert(collection_name=COLLECTION, data=data)
    client.flush(COLLECTION)
    print(f"[milvus] 已向量化并入库 {len(docs)} 条 -> {MILVUS_DB}/{COLLECTION}")


# ---------------- 混合检索主入口（语义+BM25 → RRF → Rerank） ----------------
def retrieve(query: str, embeddings, k: int = TOPK) -> list[tuple[str, str, float]]:
    """混合检索：返回 [(片段文本, 来源, 分数)]，分数为 Rerank 相关度。"""
    client = get_milvus()

    # 1) 向量路：Milvus 余弦召回（比原来多召回，交给融合/精排裁）
    qv = embeddings.embed_query(query)
    vec_hits = [(h["entity"]["text"], h["entity"].get("source", ""), float(h["distance"]))
                for h in client.search(
                    collection_name=COLLECTION, data=[qv], limit=K_VECTOR,
                    output_fields=["text", "source"],
                    search_params={"metric_type": "COSINE", "params": {"ef": 64}})[0]]

    # 2) 词法路：BM25 关键词召回（专名/错误码等精确命中）
    lex_hits = _lexical_recall(client, query, K_LEXICAL)

    # 3) 粗排：RRF 融合（按排名合并两路，取前 K_FUSE 个候选）
    fused = _rrf_fuse(vec_hits, lex_hits, K_FUSE)

    # 4) 精排：Cross-Encoder Rerank，取最终 top-k
    ranked = _rerank(query, [f["text"] for f in fused], top_n=k)
    return [(fused[i]["text"], fused[i]["source"], float(score)) for i, score in ranked]
