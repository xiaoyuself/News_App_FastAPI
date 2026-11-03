# -*- coding: utf-8 -*-
"""
pdf_loader.py —— PDF 逐页转文本

一页的处理链路：
  1. page_kind()   判断这页是 文本页 / 图片页 / 混合页（看文字多少 + 图片占页面多少）
  2. 文本页  直接 page.get_text("text")
     图片页  整页渲染成图 -> OCR
     混合页  page_items()：文字块 + 图片区域 OCR，统一换成页面坐标后排序拼接
  3. 来源（《文件名》第 N 页）在 loader.py 里标注

坐标说明：PDF 的原点在左上角，y 往下增大，单位 pt（1pt = 1/72 英寸）。
"""
from __future__ import annotations

import re
from pathlib import Path

import pymupdf

from config import (PDF_DPI, PDF_IMAGE_MAX_CHARS, PDF_IMAGE_MIN_RATIO,
                    PDF_OCR, PDF_TEXT_MAX_IMG_RATIO)

_ocr = None   # OCR 引擎要加载 3 个模型，很重，整个进程只建一次


def get_ocr():
    """懒加载 rapidocr（只用文本型 PDF 时不会触发，也就不用装 OCR 依赖）"""
    global _ocr
    if _ocr is None:
        from rapidocr import RapidOCR
        _ocr = RapidOCR()
    return _ocr


def image_rects(page) -> list:
    """这一页有几张图、各自画在哪（返回矩形列表）"""
    rects = []
    for xref in {img[0] for img in page.get_images()}:
        rects += page.get_image_rects(xref)
    return rects


def page_kind(page) -> str:
    """判断这一页的类型：文本页 / 图片页 / 混合页

    先看"有没有图"再看"字多不多"：
      - 图可以忽略（<=10% 页面）-> 文本页，哪怕字数不多（比如很短的一页说明）
      - 字几乎没有、图占大头   -> 图片页
      - 剩下的（有字也有图）   -> 混合页
    """
    chars = len(page.get_text("text").replace("\n", "").strip())
    ratio = sum(r.get_area() for r in image_rects(page)) / page.rect.get_area()
    if ratio <= PDF_TEXT_MAX_IMG_RATIO:
        return "文本页"
    if chars <= PDF_IMAGE_MAX_CHARS and ratio >= PDF_IMAGE_MIN_RATIO:
        return "图片页"
    return "混合页"


def fix_spaced_codes(text: str) -> str:
    """修复 OCR 把短码拆成单字符的问题：'A 1 1 Y - 5 0 1' -> 'A11Y-501'

    什么算"可拼接的碎块"：
      - 单个字符（字母/数字/短横），或
      - 纯数字且不超过 4 位（应付 'A 11 Y - 602' 里被拆开的 '11'、'602'）
    合并条件：至少 2 块、拼起来至少 2 个字符、含数字、且不以短横开头
    （含数字是为了不动 'hello world'，长度限制是为了不动 'for 30' 这种正常英文）
    """
    out, buf = [], []

    def flush():
        if not buf:
            return
        joined = "".join(buf)
        if (len(buf) >= 2 and len(joined) >= 2 and any(c.isdigit() for c in joined)
                and not joined.startswith("-")):
            out.append(joined)
        else:
            out.extend(buf)
        buf.clear()

    def is_code_token(t: str) -> bool:
        if not t or not t.isascii():
            return False
        if t.isdigit():
            return len(t) <= 4
        core = t.rstrip("-")              # 容许 "G-"、"1-" 这种"单字符+短横"粘在一起
        if len(core) == 1 and core.isalnum():
            return True
        return len(t) == 1 and (t.isalnum() or t == "-")

    for token in text.split():
        if is_code_token(token):
            buf.append(token)
        else:
            flush()
            out.append(token)
    flush()
    text = " ".join(out)

    # 第二遍：OCR 有时会把短码前半截粘在一起，只留下第一个字母分开，
    # 比如 'A 11Y-602'、'L ANG-703' -> 'A11Y-602'、'LANG-703'
    text = re.sub(r"(?<![A-Za-z0-9])([A-Za-z])\s+([A-Za-z0-9]*-\d+)(?![A-Za-z0-9])", r"\1\2", text)
    return text


def _sort_lines(items: list[tuple[float, float, str]]) -> list[str]:
    """按"从上到下、同一行内从左到右"排序：先按 y 分 10pt 档，同档内比 x"""
    items.sort(key=lambda it: (round(it[0] / 10), it[1]))
    return [text for _, _, text in items]


def ocr_lines(pixmap) -> list[str]:
    """对一张图做 OCR，结果是按阅读顺序排好的文本行"""
    out = get_ocr()(pixmap.tobytes("png"))
    if not out.txts:
        return []
    scale = PDF_DPI / 72.0          # 像素 -> pt 的换算倍数
    items = []
    for text, box in zip(out.txts, out.boxes):
        y = (box[0][1] + box[2][1]) / 2 / scale    # box 的垂直中心，换算成 pt
        x = (box[0][0] + box[2][0]) / 2 / scale    # box 的水平中心
        items.append((y, x, fix_spaced_codes(text)))
    return _sort_lines(items)


def page_items(page) -> list[str]:
    """混合页：文字块 + 图片区域 OCR，统一换算成页面坐标后按阅读顺序排好"""
    items = []
    for b in page.get_text("blocks"):
        x0, y0, x1, y1, block_text = b[0], b[1], b[2], b[3], b[4].strip()
        if block_text:
            items.append((y0, x0, block_text))

    scale = PDF_DPI / 72.0
    for r in image_rects(page):
        out = get_ocr()(page.get_pixmap(clip=r, dpi=PDF_DPI).tobytes("png"))
        if not out.txts:
            continue
        for ocr_text, box in zip(out.txts, out.boxes):
            # OCR 坐标是"裁剪图里的像素坐标"，加回裁剪图的页面偏移才是页面坐标
            y = r.y0 + (box[0][1] + box[2][1]) / 2 / scale
            x = r.x0 + (box[0][0] + box[2][0]) / 2 / scale
            items.append((y, x, fix_spaced_codes(ocr_text)))

    return _sort_lines(items)


def read_page(page) -> str:
    """读一页的文字，自动按页面类型选做法"""
    kind = page_kind(page)
    if kind == "文本页":
        return page.get_text("text").strip()
    if kind == "图片页":
        if not PDF_OCR:
            return ""
        return "\n".join(ocr_lines(page.get_pixmap(dpi=PDF_DPI)))
    # 混合页
    if not PDF_OCR:
        return page.get_text("text").strip()
    return "\n".join(page_items(page))


def pdf_pages(path) -> list[tuple[int, str]]:
    """把一份 PDF 逐页转成 [(页码, 文本)]，页码从 1 开始"""
    path = Path(path)
    doc = pymupdf.open(path)
    try:
        pages = []
        for no in range(len(doc)):
            try:
                text = read_page(doc[no])
            except Exception as e:      # 单页出问题跳过，不影响整份
                print(f"[pdf] {path.name} 第 {no + 1} 页处理失败：{type(e).__name__}: {e}")
                continue
            if text.strip():
                pages.append((no + 1, text.strip()))
        return pages
    finally:
        doc.close()
