# -*- coding: utf-8 -*-
"""
query_rewrite.py —— Query 改写：Multi-Query（一条 query 拆成多条检索）

做法：把一个用户问题，用 LLM 扩展成 N 条语义等价、但措辞不同的查询，
然后对每条查询分别检索，最后按分数合并去重，取 top-k。
"""
from __future__ import annotations

import threading

from langchain_core.messages import HumanMessage, SystemMessage

from config import CHAT_API_KEY, CHAT_BASE_URL, CHAT_MODEL, TOPK

_MQ_SYS = (
    "你是检索查询扩展助手。把用户问题改写成若干个语义等价、但措辞不同的查询，"
    "每个查询单独一行。要求：\n"
    "1) 口语转书面、补全缩写和省略；\n"
    "2) 保留原意，不要新增信息；\n"
    "3) 只输出查询本身，不要编号、不要解释。"
)

# 复用 chat 实例（低置信度时才会走到这里，但一次问答要调 1 次，同样别重复初始化）
_chat = None
_chat_lock = threading.Lock()


def _get_chat():
    global _chat
    if _chat is not None:
        return _chat
    with _chat_lock:
        if _chat is None:
            from langchain.chat_models import init_chat_model

            _chat = init_chat_model(
                model=CHAT_MODEL,
                model_provider="deepseek",
                api_key=CHAT_API_KEY,
                base_url=CHAT_BASE_URL,
                temperature=0.0,
                max_tokens=256,
            )
    return _chat


_RW_SYS = (
    "你是对话改写助手。请结合对话历史，把用户最后一句话改写成一句"
    "不依赖上下文、可以单独拿去检索的完整问题。\n"
    "要求：1) 补全代词指代（它 / 这个 / 那个）和省略的主语；2) 保留原意，不要新增信息；"
    "3) 只输出改写后的问题本身，不要解释、不要加引号。"
)


def rewrite_with_history(question: str, history: list[dict]) -> str:
    """多轮对话里把 "它要收费吗" 改写成 "收藏功能要收费吗" 再做检索。

    不改写的话，拿 "它要收费吗" 去向量库检索什么都搜不到，
    模型只能靠历史硬答，容易脱离知识库编答案。
    改写失败就退回原问题，不让主链路中断。
    """
    if not history:
        return question
    lines = []
    for h in history:
        content = (h.get("content") or "").strip()
        if not content:
            continue
        who = "用户" if h.get("role") == "user" else "客服"
        lines.append(f"{who}：{content}")
    if not lines:
        return question

    prompt = ("对话历史：\n" + "\n".join(lines)
              + f"\n\n用户最后一句话：{question}\n\n改写后的完整问题：")
    try:
        resp = _get_chat().invoke([SystemMessage(content=_RW_SYS), HumanMessage(content=prompt)])
        out = str(resp.content or "").strip().strip('"').strip("“”").strip()
        return out or question
    except Exception as e:  # noqa: BLE001
        print(f"[rewrite] 改写失败，改用原问题：{type(e).__name__}: {str(e)[:80]}")
        return question


def multi_query(question: str, n: int = 3) -> list[str]:
    """把一个问题拆成 n 条不同表述的查询（Multi-Query）。"""
    chat = _get_chat()
    resp = chat.invoke([
        SystemMessage(content=_MQ_SYS),
        HumanMessage(content=f"用户问题：{question}\n请生成 {n} 条不同表述："),
    ])
    lines = [ln.strip() for ln in str(resp.content or "").split("\n") if ln.strip()]
    # 去掉模型可能加的编号前缀，如 "1." "1、" "-"
    clean = []
    for ln in lines:
        for sep in (".", "、", ")", "）", "-", " "):
            idx = ln.find(sep)
            if 0 <= idx <= 2 and ln[:idx].isdigit():
                ln = ln[idx + 1:].strip()
                break
        if ln:
            clean.append(ln)
    return clean[:n]


def multi_query_retrieve(question: str, embeddings, k: int = TOPK):
    """Multi-Query 检索：原始问题 + N 条变体分别检索，按分数合并去重，取 top-k。

    返回 [(文本, 来源, 分数)]，与 vector_store.retrieve 的签名一致。
    """
    from vector_store import retrieve

    merged: dict[tuple[str, str], tuple[str, str, float]] = {}
    for q in [question] + multi_query(question):
        for text, src, score in retrieve(q, embeddings, k=k * 3):
            key = (text, src)
            if key not in merged or score > merged[key][2]:
                merged[key] = (text, src, score)
    ranked = sorted(merged.values(), key=lambda x: -x[2])
    return ranked[:k]
