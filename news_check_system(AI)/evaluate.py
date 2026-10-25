# -*- coding: utf-8 -*-
"""
evaluate.py —— 官方 ragas 框架评估（极简版）

输入两个文件（都是“顶层数组、每条只含必要列”）：
  1) evals/eval_set_v1.json   标准集：[{question, ground_truths:[标准答案]}]
  2) evals/collected_v1.json  问答结果：[{question, answer, contexts:[检索片段]}]

读取/合并只需 zip 按顺序拼接成 RAGAS 四列（+0.4.3 需要的 reference 别名）：
  question / answer / contexts / ground_truths / reference
再直接 evaluate(dataset, metrics=[faithfulness, answer_relevancy,
                                  context_precision, context_recall], llm=…, embeddings=…)

PyCharm 直接运行；前提：已装官方 ragas（见 requirements-eval.txt）。
"""
from __future__ import annotations

import json
from pathlib import Path

from config import ROOT

EVAL_DIR = ROOT / "evals"
EVAL_SET_PATH = EVAL_DIR / "eval_set_v1.json"
COLLECTED_PATH = EVAL_DIR / "collected_v1.json"
REPORT_PATH = EVAL_DIR / "ragas_report_v1.json"
METRICS = ("faithfulness", "answer_relevancy", "context_precision", "context_recall")


def main():
    from ragas import evaluate
    from ragas.metrics import context_precision, context_recall, faithfulness
    from ragas.metrics._answer_relevance import AnswerRelevancy
    from datasets import Dataset
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings

    from config import (CHAT_API_KEY, CHAT_BASE_URL, CHAT_MODEL,
                        EMBED_API_KEY, EMBED_BASE_URL, EMBED_MODEL)

    # ---- 读两份文件并按顺序合并成 RAGAS 数据集（就这么几行）----
    std = json.loads(EVAL_SET_PATH.read_text(encoding="utf-8"))      # [{question, ground_truths}]
    col = json.loads(COLLECTED_PATH.read_text(encoding="utf-8"))     # [{question, answer, contexts}]
    rows = [{"question": c["question"], "answer": c["answer"], "contexts": c["contexts"],
             "ground_truths": s["ground_truths"],
             "reference": s["ground_truths"][0] if s["ground_truths"] else ""}
            for s, c in zip(std, col)]
    rows = [r for r in rows if r["ground_truths"]]                    # 负例无标准答案，跳过打分

    # ---- 判官 LLM/Embedding 复用 DeepSeek + 硅基流动（OpenAI 兼容）----
    judge_llm = ChatOpenAI(model=CHAT_MODEL, base_url=CHAT_BASE_URL,
                           api_key=CHAT_API_KEY, temperature=0)
    judge_emb = OpenAIEmbeddings(model=EMBED_MODEL, base_url=EMBED_BASE_URL,
                                 api_key=EMBED_API_KEY,
                                 check_embedding_ctx_length=False)

    # DeepSeek 只支持 n=1，answer_relevancy 默认要生成 3 个问题(n=3)会报 400，这里改成 1
    answer_relevancy = AnswerRelevancy(strictness=1)

    dataset = Dataset.from_list(rows)
    print(f"[ragas] 参与打分：{len(rows)} 条，列 = {list(dataset.features.keys())}\n")

    result = evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        llm=judge_llm,
        embeddings=judge_emb,
    )
    print("\n" + "=" * 60)
    print(result)

    # ScoreType 按指标名取到“逐例数组”，求非空均值存档
    scores = {}
    for name in METRICS:
        arr = [x for x in result[name] if x == x]                 # 过滤 NaN
        scores[name] = round(sum(arr) / len(arr), 4) if arr else None
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps({"n": len(rows), "scores": scores},
                                      ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n报告已保存：{REPORT_PATH}")


if __name__ == "__main__":
    main()
