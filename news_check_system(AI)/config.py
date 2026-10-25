# -*- coding: utf-8 -*-
"""
config.py —— 全局配置

职责：加载 .env、集中管理所有常量（Milvus / 模型 / 数据路径），
     其它模块统一从这里取配置，避免各处写死。
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
load_dotenv(ROOT / ".env")

# ---------- Milvus ----------
MILVUS_URI = os.getenv("MILVUS_URI", "http://localhost:19530")
MILVUS_DB = "rag_new"        # 本项目独立库，不影响已有库
COLLECTION = "doc_chunks"
DIM = 1024                   # Qwen3-Embedding-0.6B 维度
TOPK = 4                     # 问答默认检索片段数
EVAL_TOPK = 5                # 评估收集答案时用的检索 top-k

# ---------- 模型（.env 可覆盖） ----------
EMBED_MODEL = os.getenv("EMBED_MODEL", "Qwen/Qwen3-Embedding-0.6B")
EMBED_API_KEY = os.getenv("SI_API_KEY")
EMBED_BASE_URL = os.getenv("SI_BASE_URL")

CHAT_MODEL = os.getenv("CHAT_MODEL", "deepseek-v4-flash")
CHAT_API_KEY = os.getenv("DEEPSEEK_API_KEY")
CHAT_BASE_URL = os.getenv("DEEPSEEK_BASE_URL")

# ---------- 知识文件 ----------
DOC_A_PATH = DATA_DIR / "doc_a_clean.md"    # 叙述型手册
DOC_B_PATH = DATA_DIR / "doc_b_clean.csv"   # FAQ / 错误码表

# ---------- 检索链路（语义 + BM25 → RRF 融合 → Rerank 精排） ----------
K_VECTOR = 12        # 向量路召回条数（Milvus 余弦）
K_LEXICAL = 12       # BM25 词法路召回条数
RRF_K = 60           # RRF 融合常数（只看排名：score = Σ 1/(rrf_k + rank)）
K_FUSE = 10          # 融合后进 Rerank 的候选数
# Rerank 精排模型（硅基流动，OpenAI 兼容 /rerank，复用 SI Key）
RERANK_MODEL = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-v2-m3")
RERANK_BASE_URL = os.getenv("SI_BASE_URL")
RERANK_API_KEY = os.getenv("SI_API_KEY")
