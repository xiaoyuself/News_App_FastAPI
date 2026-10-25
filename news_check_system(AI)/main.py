# -*- coding: utf-8 -*-
"""
main.py —— 程序入口（PyCharm 直接运行本文件）

职责：
  - 默认“问答模式”：对 DEMO_QUESTIONS 逐题检索并回答；
  - “收集模式”（COLLECT_EVAL_DATA=True）：把标准集(evals/eval_set_v1.json)里的问题
    逐个跑一遍主链路，把 answer / contexts / hit_sources 存成 evals/collected_v1.json，
    供 evaluate.py 纯打分（评估不自己跑 RAG）。
"""
from __future__ import annotations

import json
import os

from config import EVAL_TOPK, ROOT
from embeddings import get_embeddings
from generator import ask
from loader import load_chunks
from vector_store import build_index, retrieve

# ================= 在这里改提问 / 重建索引 =================
DEMO_QUESTIONS = [                 # 问答模式下依次回答的问题
    "如何注册账号？",
    "账号被锁定（ERR-108）怎么解锁？",
    "收不到短信验证码怎么办？",
]
REBUILD = False                    # True = 强制重建索引（重新向量化入库）
COLLECT_EVAL_DATA = os.getenv("COLLECT_EVAL", "0") == "1"   # True = 收集模式
# =========================================================

EVAL_DIR = ROOT / "evals"
EVAL_SET_PATH = EVAL_DIR / "eval_set_v1.json"
COLLECTED_PATH = EVAL_DIR / "collected_v1.json"


def collect_eval_answers(embeddings) -> None:
    """收集模式：对标准集每个问题跑 检索+回答，结果写 evals/collected_v1.json。

    每条只存 RAGAS 需要的内容：question / answer(模型答案) / contexts(检索片段)，
    ground_truth 在标准集文件里，evaluate.py 按顺序合并（两文件无 id 等附加字段）。
    """
    if not EVAL_SET_PATH.exists():
        raise FileNotFoundError(f"缺少标准集：{EVAL_SET_PATH}")
    questions = [c["question"] for c in json.loads(EVAL_SET_PATH.read_text(encoding="utf-8"))]
    print(f"[collect] 标准集 {len(questions)} 条，逐条 检索+回答（top-{EVAL_TOPK}）……")

    rows = []
    for i, q in enumerate(questions, 1):
        hits = retrieve(q, embeddings, k=EVAL_TOPK)
        rows.append({"question": q,
                     "answer": ask(q, hits),
                     "contexts": [txt for txt, _, _ in hits]})
        print(f"[{i}/{len(questions)}] 完成")

    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    COLLECTED_PATH.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[collect] 收集完成 -> {COLLECTED_PATH}（{len(rows)} 条）")


def main():
    print("=" * 50)
    print("基础 RAG（LangChain + Milvus）开始，请稍候……")

    # 1) 知识侧：加载并切块（带 source）
    chunks = load_chunks()
    # 2) 模型侧：向量模型
    embeddings = get_embeddings()
    # 3) 存储侧：写入 Milvus（已就绪则跳过）
    build_index(chunks, embeddings, force=REBUILD)

    # 收集模式：跑标准集，产出 evaluate.py 的输入
    if COLLECT_EVAL_DATA:
        collect_eval_answers(embeddings)
        print("收集模式结束。接下来运行 evaluate.py 即可对收集结果打分。")
        return

    # 4) 问答模式：逐题问答
    for q in DEMO_QUESTIONS:
        hits = retrieve(q, embeddings)
        print("\n" + "=" * 50)
        print(f"Q：{q}")
        print(f"检索 top-{len(hits)}（来源 | 相似度）：")
        for _, src, score in hits:
            print(f"  - {src}  {score:.3f}")
        print("-" * 50)
        print(f"A：{ask(q, hits)}\n")

    print("=" * 50)
    print("运行结束。如需提问别的问题，修改上方 DEMO_QUESTIONS 后再次运行即可。")


if __name__ == "__main__":
    main()
