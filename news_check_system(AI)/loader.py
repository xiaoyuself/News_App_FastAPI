# -*- coding: utf-8 -*-
"""
loader.py —— 文档加载与切块（知识侧）

职责：读原始知识文件 → 切成检索单元（chunk），并给每个 chunk 绑定 source 来源。
      doc_a 按 Markdown 标题层级切章节；doc_b 每条记录一个 chunk。
"""
from __future__ import annotations

import pandas as pd
from langchain_core.documents import Document

from config import DOC_A_PATH, DOC_B_PATH

CHUNK_SIZE = 400
CHUNK_OVERLAP = 80
SEPARATORS = ["\n\n", "\n", "。", "！", "？", "；", " ", ""]


def load_chunks(doc_a_path=DOC_A_PATH, doc_b_path=DOC_B_PATH) -> list[Document]:
    """返回带 source 元数据的切块列表，供入库与回答时标注参考来源。"""
    from langchain_text_splitters import (
        MarkdownHeaderTextSplitter,
        RecursiveCharacterTextSplitter,
    )

    docs: list[Document] = []

    # doc_a：叙述型手册 —— 先按标题切成章节，章节太长再递归切小（子块继承标题元数据）
    md = doc_a_path.read_text(encoding="utf-8")
    md_split = MarkdownHeaderTextSplitter(headers_to_split_on=[("#", "H1"), ("##", "H2"), ("###", "H3")])
    sub = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP,
                                         separators=SEPARATORS)
    for d in sub.split_documents(md_split.split_text(md)):
        chain = " > ".join(d.metadata[k] for k in ("H1", "H2", "H3") if d.metadata.get(k))
        source = f"《产品手册》{('：' + chain) if chain else ''}"
        docs.append(Document(page_content=d.page_content, metadata={"source": source}))

    # doc_b：FAQ / 错误码表 —— 一条记录 = 一个切块，source 取记录 code
    df = pd.read_csv(doc_b_path, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    for _, r in df.iterrows():
        text = f"【{r['record_type']} {r['code']}】{r['category']}：{r['title']}\n{r['answer']}"
        docs.append(Document(page_content=text, metadata={"source": r["code"]}))

    return docs
