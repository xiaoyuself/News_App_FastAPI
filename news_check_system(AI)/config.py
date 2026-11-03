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
# server 模式（默认）：连独立的 Milvus 服务（http://host:19530），约吃 1.2G 内存
# lite   模式：用 milvus-lite，向量存本地 .db 文件，无独立进程（2G 小机器用这个）
MILVUS_MODE = os.getenv("MILVUS_MODE", "server")
# server 模式：Milvus 服务的地址
MILVUS_URI = os.getenv("MILVUS_URI", "http://localhost:19530")
# lite 模式：本地 .db 文件的路径。
# ⚠️ 这里必须用独立的变量名，不能复用 MILVUS_URI —— pymilvus 3.x 在 import 时就会读取
#    环境变量 MILVUS_URI 并校验成 http(s):// 形式，传文件路径会直接抛 ConnectionConfigException
MILVUS_LITE_PATH = os.getenv("MILVUS_LITE_PATH", str(ROOT / "milvus_data" / "milvus.db"))
MILVUS_DB = "rag_new"        # 仅 server 模式使用（lite 只有默认库）
COLLECTION = "doc_chunks"
DIM = 1024                   # Qwen3-Embedding-0.6B 维度
TOPK = 4                     # 问答默认检索片段数
EVAL_TOPK = 5                # 评估收集答案时用的检索 top-k

# 检索置信度阈值：top1 精排分数低于它，就认为"没检索到"，改走 Multi-Query 或直接兜底。
# 原来写死在 ai_server.py 里，现在可以用 .env 的 LOW_CONF_THRESHOLD 调（不同知识库适合的值不同）
LOW_CONF_THRESHOLD = float(os.getenv("LOW_CONF_THRESHOLD", "0.6"))

# 知识库指纹文件：记录"上次建索引时知识文件的样子"，
# 服务启动/提问时对比一下，文件变了就自动重建索引（免得改了文档还在答旧内容）
def _default_index_meta_path() -> str:
    # lite 模式的向量库是本地 .db 文件（Docker 里在持久卷上），指纹放它旁边最保险；
    # server 模式没有本地库文件，就放项目目录（不需要 data/ 的写权限）
    if MILVUS_MODE == "lite":
        p = Path(MILVUS_LITE_PATH)
        if p.suffix == ".db":
            return str(p.parent / ".index_meta.json")
    return str(ROOT / ".index_meta.json")


INDEX_META_PATH = os.getenv("INDEX_META_PATH") or _default_index_meta_path()

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

# ---------- PDF 知识库（data/pdf/*.pdf） ----------
PDF_DIR = DATA_DIR / "pdf"
PDF_DPI = 200                    # 图片页 / 图片区域渲染成图时的清晰度
PDF_OCR = os.getenv("PDF_OCR", "1") == "1"   # 关掉则只处理文本型 PDF，不依赖 rapidocr
# 判断一页属于哪种类型的阈值
PDF_TEXT_MAX_IMG_RATIO = 0.10    # 图片 <= 页面 10%   -> 文本页（图可以忽略，哪怕字数不多）
PDF_IMAGE_MAX_CHARS = 50         # 文字 <= 50 字，且
PDF_IMAGE_MIN_RATIO = 0.50       #   图片 >= 页面 50%  -> 图片页
                                 # 其余（有字也有图） -> 混合页

# ---------- 检索链路（语义 + BM25 → RRF 融合 → Rerank 精排） ----------
K_VECTOR = 12        # 向量路召回条数（Milvus 余弦）
K_LEXICAL = 12       # BM25 词法路召回条数
RRF_K = 60           # RRF 融合常数（只看排名：score = Σ 1/(rrf_k + rank)）
K_FUSE = 10          # 融合后进 Rerank 的候选数
# Rerank 精排模型（硅基流动，OpenAI 兼容 /rerank，复用 SI Key）
RERANK_MODEL = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-v2-m3")
RERANK_BASE_URL = os.getenv("SI_BASE_URL")
RERANK_API_KEY = os.getenv("SI_API_KEY")
