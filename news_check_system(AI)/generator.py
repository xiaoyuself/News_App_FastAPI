# -*- coding: utf-8 -*-
"""
generator.py —— 回答生成（生成侧）

职责：把问题 + 检索片段拼成提示词，调用 DeepSeek 生成回答；
      提示词要求回答只依据片段、末尾输出参考来源。
"""
from __future__ import annotations


def ask(question: str, hits: list[tuple[str, str, float]]) -> str:
    """hits: [(片段文本, 来源, 相似度)]；返回模型回答文本。"""
    from langchain.chat_models import init_chat_model
    from langchain_core.messages import HumanMessage, SystemMessage

    from config import CHAT_API_KEY, CHAT_BASE_URL, CHAT_MODEL

    chat = init_chat_model(
        model=CHAT_MODEL,
        model_provider="deepseek",
        api_key=CHAT_API_KEY,
        base_url=CHAT_BASE_URL,
        temperature=0.2, max_tokens=2048,
    )
    ctx_blk = "\n\n---\n\n".join(
        f"[片段{i + 1}]（来源：{src}）\n{t}" for i, (t, src, _) in enumerate(hits))
    sys_prompt = (
        "你是新闻资讯 App 的智能客服。请只依据给定的知识片段回答，片段中没有的信息不要编造。\n"
        "回答要求：\n"
        "1) 直接、简洁地回答用户问题，2~3 句话即可，不要展开与问题无关的细节；\n"
        "2) 内容准确、用词精炼；\n"
        "3) 回答末尾单独输出一行「参考来源：」，只列实际引用的来源编号（如 FQA-101），不要解释；\n"
        "4) 若片段不足以回答，直接回复“知识库中暂无相关信息”，参考来源输出“无”。"
    )
    resp = chat.invoke([SystemMessage(content=sys_prompt),
                        HumanMessage(content=f"问题：{question}\n\n知识片段：\n{ctx_blk}")])
    return str(resp.content or "").strip()
