# -*- coding: utf-8 -*-
"""
loader.py —— 文档加载与切块（知识侧）

职责：读原始知识文件 → 切成检索单元（chunk），并给每个 chunk 绑定 source 来源。
      doc_a 按 Markdown 标题层级切章节；doc_b 每条记录一个 chunk。
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
from langchain_core.documents import Document

from config import DOC_A_PATH, DOC_B_PATH, PDF_DIR

CHUNK_SIZE = 400
CHUNK_OVERLAP = 80
SEPARATORS = ["\n\n", "\n", "。", "！", "？", "；", " ", ""]


def load_pdf_chunks(pdf_dir=PDF_DIR) -> list[Document]:
    """把 data/pdf/*.pdf 逐页转成切块，来源标成《文件名》第 N 页。

    PDF 是可选知识源：目录不存在或没有 PDF 时返回空列表，不影响原有 md/csv。
    """
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    import pdf_loader

    pdf_dir = Path(pdf_dir)
    if not pdf_dir.exists():
        return []

    files = sorted(pdf_dir.glob("*.pdf"))
    if not files:
        return []

    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP,
                                             separators=SEPARATORS)
    docs: list[Document] = []
    for pdf in files:
        pages = pdf_loader.pdf_pages(pdf)
        before = len(docs)
        for page_no, page_text in pages:
            source = f"《{pdf.stem}》第 {page_no} 页"
            for piece in splitter.split_text(page_text):
                if piece.strip():
                    docs.append(Document(page_content=piece, metadata={"source": source}))
        print(f"[pdf] {pdf.name}：{len(pages)} 页有内容，产出 {len(docs) - before} 块")

    print(f"[pdf] 共 {len(files)} 个 PDF，合计 {len(docs)} 块")
    return docs


def knowledge_fingerprint(doc_a_path=DOC_A_PATH, doc_b_path=DOC_B_PATH) -> str:
    """知识库文件的"指纹"：文件名 + 大小 + 修改时间。

    只用来判断"知识文件有没有被改过"，不读内容，所以很快。
    用它来决定是否必须重建向量索引。
    """
    h = hashlib.sha1()
    for p in (doc_a_path, doc_b_path):
        st = p.stat()
        h.update(p.name.encode("utf-8"))
        h.update(str(st.st_size).encode())
        h.update(str(int(st.st_mtime)).encode())
    return h.hexdigest()[:16]


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

    # doc_c：PDF（data/pdf/*.pdf）—— 逐页转文本，一页一个来源
    docs.extend(load_pdf_chunks())

    return docs
