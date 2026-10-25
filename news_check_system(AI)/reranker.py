# -*- coding: utf-8 -*-
"""
reranker.py —— Rerank 精排（模型侧）

作用：把 query 和每个候选片段【逐对拼接打分】（Cross-Encoder），
      比向量/BM25 的粗分数更准，把真正相关的片段排到前面。
      实现用硅基流动的 bge-reranker-v2-m3（OpenAI 兼容 /rerank 接口）。
      网络异常时降级为“原序返回”，不让主链路中断（fail-open）。
"""
from __future__ import annotations

import httpx

from config import RERANK_API_KEY, RERANK_BASE_URL, RERANK_MODEL

_client = None


def _http() -> httpx.Client:
    global _client
    if _client is None:
        _client = httpx.Client(timeout=30)
    return _client


def rerank(query: str, texts: list[str], top_n: int) -> list[tuple[int, float]]:
    """对候选片段精排，返回按相关度降序的 [(原下标, 分数)]；失败降级为原序。"""
    if not texts:
        return []
    try:
        resp = _http().post(
            f"{RERANK_BASE_URL}/rerank",
            headers={"Authorization": f"Bearer {RERANK_API_KEY}"},
            json={"model": RERANK_MODEL, "query": query,
                  "documents": texts, "top_n": min(top_n, len(texts))},
        )
        resp.raise_for_status()
        items = sorted(resp.json().get("results", []),
                       key=lambda x: x.get("relevance_score", 0.0), reverse=True)
        return [(it["index"], it.get("relevance_score", 0.0)) for it in items]
    except Exception as e:
        print(f"[rerank] 调用失败，降级为原序: {type(e).__name__}: {str(e)[:120]}")
        return [(i, 0.5) for i in range(len(texts))]
