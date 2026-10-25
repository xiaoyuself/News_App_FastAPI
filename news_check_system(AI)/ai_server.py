# -*- coding: utf-8 -*-
"""
ai_server.py —— 智能客服 HTTP 服务（供新闻软件前端「AI对话」页调用）

把 RAG_NEW 主链路（load_chunks → build_index → retrieve → ask）包装成 HTTP 服务，
对接前端 js/api.js 里预留的 AI 接口：

    POST {AI_BASE_URL}/api/ai/chat   body: {"question": "..."}
        -> {"code": 200, "message": "success", "data": {"answer": "..."}}
    POST {AI_BASE_URL}/api/ai/init   强制重建知识库索引（修改 data/ 后调用）
    GET  /                           健康检查

默认端口 8001，与前端 js/config.js 的 AI_BASE_URL 一致。

运行（使用 RAG 主环境，例如 D:\\miniconda\\envs\\langchain1.2）：
    python ai_server.py
或：
    uvicorn ai_server:app --host 0.0.0.0 --port 8001

容错设计（对齐旧版 ai_server.py 的加固点）：
  - 问候语（你好/您好/hi 等）直接回复，不依赖 Milvus / 大模型，秒回；
  - 提问前先 TCP 探测 Milvus 可达性（2s 超时），不可达立即返回友好提示，避免卡死；
  - 建库 / 问答放入线程池 + 超时保护（建库 120s / 问答 90s），服务始终保持可响应。
"""
from __future__ import annotations

import asyncio
import socket
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from urllib.parse import urlparse

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import vector_store
from config import MILVUS_URI
from embeddings import get_embeddings
from generator import ask
from loader import load_chunks
from vector_store import build_index, retrieve
from query_rewrite import multi_query_retrieve

# ---------------- 常量 ----------------
BUILD_TIMEOUT = 120      # 首次建库超时（秒）
ANSWER_TIMEOUT = 90      # 单次问答超时（秒）
INIT_TIMEOUT = 180       # 强制重建超时（秒）
PROBE_TIMEOUT = 2.0      # Milvus TCP 探测超时（秒）
LOW_CONF_THRESHOLD = 0.6  # 检索置信度阈值：top1 分数低于此值则走 Multi-Query 改写检索

GREETING_REPLY = (
    "您好！我是新闻软件智能客服助手 🤖\n"
    "您可以问我关于注册登录、新闻浏览、收藏、浏览记录、修改密码等问题。"
)
_GREETING_WORDS = (
    "你好", "您好", "嗨", "在吗", "早上好", "中午好", "下午好", "晚上好",
    "hi", "hello", "hey",
)

# ---------------- 全局状态 ----------------
_executor = ThreadPoolExecutor(max_workers=4)
_embeddings = None
_index_ready = False
_lock = threading.Lock()


class ChatRequest(BaseModel):
    question: str


def _milvus_host_port():
    uri = MILVUS_URI if "://" in MILVUS_URI else "//" + MILVUS_URI
    u = urlparse(uri)
    return u.hostname or "localhost", u.port or 19530


def _milvus_reachable() -> bool:
    """TCP 探测 Milvus 可达性，避免 MilvusClient 构造长时间挂起。"""
    host, port = _milvus_host_port()
    try:
        with socket.create_connection((host, port), timeout=PROBE_TIMEOUT):
            return True
    except OSError:
        return False


def _is_greeting(q: str) -> bool:
    t = q.strip().lower()
    if not t or len(t) > 12:
        return False
    return any(w in t for w in _GREETING_WORDS)


def _build(force: bool) -> None:
    """加载知识 → 建向量索引（幂等）。线程安全，可在 executor 中调用。"""
    global _embeddings, _index_ready
    with _lock:
        if force:
            _index_ready = False
            vector_store._bm25 = None   # 让 BM25 词法缓存随重建一起失效
        if _embeddings is None:
            _embeddings = get_embeddings()
        chunks = load_chunks()
        build_index(chunks, _embeddings, force=force)
        _index_ready = True


def _answer(q: str) -> str:
    # 1) 原始问题先检索
    hits = retrieve(q, _embeddings)
    top_score = hits[0][2] if hits else 0.0
    if top_score >= LOW_CONF_THRESHOLD:
        return ask(q, hits)
    # 2) 低置信 → Multi-Query：拆成多条分别检索，合并去重取 top-k
    hits = multi_query_retrieve(q, _embeddings)
    if hits and hits[0][2] >= LOW_CONF_THRESHOLD:
        return ask(q, hits)
    return "知识库中暂无相关信息，建议转人工客服协助您。"


def _try_eager_build() -> None:
    """启动时后台预建索引：Milvus 可达则提前建库，首次提问无需等待。"""
    if not _milvus_reachable():
        print("[ai_server] Milvus 未启动，跳过预建索引（首次提问将按需构建）")
        return
    try:
        _build(force=False)
        print("[ai_server] 预建索引完成")
    except Exception as e:  # noqa: BLE001
        print(f"[ai_server] 预建索引失败（首次提问会重试）：{type(e).__name__}: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    threading.Thread(target=_try_eager_build, daemon=True).start()
    yield
    _executor.shutdown(wait=False)


app = FastAPI(title="新闻软件智能客服", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _ok(answer: str):
    return {"code": 200, "message": "success", "data": {"answer": answer}}


def _err(code: int, message: str):
    return {"code": code, "message": message, "data": None}


@app.get("/")
async def root():
    return {
        "code": 200,
        "message": "智能客服服务运行中",
        "data": {"index_ready": _index_ready, "milvus_reachable": _milvus_reachable()},
    }


@app.post("/api/ai/chat")
async def ai_chat(req: ChatRequest):
    q = (req.question or "").strip()
    if not q:
        return _err(400, "问题不能为空")

    if _is_greeting(q):
        return _ok(GREETING_REPLY)

    if not _milvus_reachable():
        return _err(503, "知识库服务（Milvus）未启动，请先启动 Milvus（默认 http://localhost:19530）")

    loop = asyncio.get_running_loop()
    try:
        if not _index_ready:
            await asyncio.wait_for(loop.run_in_executor(_executor, _build, False),
                                   timeout=BUILD_TIMEOUT)
        answer = await asyncio.wait_for(loop.run_in_executor(_executor, _answer, q),
                                        timeout=ANSWER_TIMEOUT)
        return _ok(answer)
    except asyncio.TimeoutError:
        return _err(504, "智能客服响应超时，请稍后重试")
    except Exception as e:  # noqa: BLE001
        return _err(500, f"智能客服暂时无法回答：{type(e).__name__}: {e}")


@app.post("/api/ai/init")
async def ai_init():
    if not _milvus_reachable():
        return _err(503, "知识库服务（Milvus）未启动，请先启动 Milvus（默认 http://localhost:19530）")

    loop = asyncio.get_running_loop()
    try:
        await asyncio.wait_for(loop.run_in_executor(_executor, _build, True),
                               timeout=INIT_TIMEOUT)
        return {"code": 200, "message": "知识库重建成功", "data": None}
    except asyncio.TimeoutError:
        return _err(504, "知识库重建超时，请稍后重试")
    except Exception as e:  # noqa: BLE001
        return _err(500, f"知识库重建失败：{type(e).__name__}: {e}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
