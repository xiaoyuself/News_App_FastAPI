# -*- coding: utf-8 -*-
"""
embeddings.py —— 向量化模型客户端（模型侧）

职责：创建文本向量模型（硅基流动 Qwen3-Embedding-0.6B，OpenAI 兼容协议）。
"""
from __future__ import annotations

from config import EMBED_API_KEY, EMBED_BASE_URL, EMBED_MODEL


def get_embeddings():
    from langchain_openai import OpenAIEmbeddings

    # 必须关掉 check_embedding_ctx_length：默认会先把文本按 OpenAI 词表“预分词”再发送，
    # 导致 Qwen 向量畸变；关掉后直发原文才是正确向量。
    return OpenAIEmbeddings(
        model=EMBED_MODEL,
        api_key=EMBED_API_KEY,
        base_url=EMBED_BASE_URL,
        check_embedding_ctx_length=False,
    )
