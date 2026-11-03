# -*- coding: utf-8 -*-
"""
generator.py —— 回答生成（生成侧）

职责：把问题 + 检索片段拼成提示词，调用 DeepSeek 生成回答；
      提示词要求回答只依据片段、末尾输出参考来源。
"""
from __future__ import annotations

import threading

# 复用一个 chat 模型实例：每问一句都 init_chat_model() 一次会重复建客户端/建连接池，
# 单次问答能省几十毫秒，并发时省得更多
_chat = None
_chat_lock = threading.Lock()

SYS_PROMPT = (
    "你是新闻资讯 App 的智能客服。请只依据给定的知识片段回答，片段中没有的信息不要编造。\n"
    "回答要求：\n"
    "1) 直接、简洁地回答用户问题，2~3 句话即可，不要展开与问题无关的细节；\n"
    "2) 内容准确、用词精炼；\n"
    "3) 回答末尾单独输出一行「参考来源：」，只写片段出处本身"
    "（如 FQA-101、ERR-108、或《文件名》第 N 页），不要写「片段1」这种序号，不要解释；\n"
    "4) 若片段不足以回答，直接回复“知识库中暂无相关信息”，参考来源输出“无”。"
)


def _get_chat():
    global _chat
    if _chat is not None:
        return _chat
    with _chat_lock:
        if _chat is None:
            from langchain.chat_models import init_chat_model

            from config import CHAT_API_KEY, CHAT_BASE_URL, CHAT_MODEL

            _chat = init_chat_model(
                model=CHAT_MODEL,
                model_provider="deepseek",
                api_key=CHAT_API_KEY,
                base_url=CHAT_BASE_URL,
                temperature=0.2, max_tokens=2048,
            )
    return _chat


def ask(question: str, hits: list[tuple[str, str, float]], history: list[dict] | None = None) -> str:
    """hits: [(片段文本, 来源, 相似度)]；history: [{"role": "user"/"assistant", "content": "..."}]

    多轮时把最近几轮对话按原角色拼进 messages，让模型能理解"它/这个"指的是什么。
    注意：history 里只有问答内容，**不含检索片段**（片段每轮重新检索，不累积）。
    """
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

    chat = _get_chat()
    ctx_blk = "\n\n---\n\n".join(
        f"[片段{i + 1}]（来源：{src}）\n{t}" for i, (t, src, _) in enumerate(hits))

    msgs = [SystemMessage(content=SYS_PROMPT)]
    for h in (history or []):
        content = (h.get("content") or "").strip()
        if not content:
            continue
        if h.get("role") == "user":
            msgs.append(HumanMessage(content=content))
        else:
            msgs.append(AIMessage(content=content))
    msgs.append(HumanMessage(content=f"问题：{question}\n\n知识片段：\n{ctx_blk}"))

    resp = chat.invoke(msgs)
    return str(resp.content or "").strip()
