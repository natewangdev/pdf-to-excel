"""PDF 表格检测与 OCR 提取模块"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Union

import cv2
import numpy as np
import pandas as pd
from img2table.document import PDF

from .ocr_adapter import PaddleOCRAdapter

logger = logging.getLogger(__name__)


def _render_pdf_images(
    pdf_path: str,
    pages: list[int] | None = None,
    dpi: int = 200,
) -> list[np.ndarray]:
    """使用 pypdfium2 将 PDF 渲染为图片，支持自定义 DPI。

    img2table 默认固定 200 DPI，此函数允许调整。
    DPI 越高图片越清晰，但处理速度越慢、内存占用越大。
    """
    import pypdfium2

    doc = pypdfium2.PdfDocument(pdf_path)
    scale = dpi / 72  # PDF 原始坐标系为 72 DPI

    images = []
    for page_number in pages or range(len(doc)):
        page = doc[page_number]
        img = cv2.cvtColor(page.render(scale=scale).to_numpy(), cv2.COLOR_BGR2RGB)
        images.append(img)
        logger.info("  第 %d 页渲染完成 (%dx%d, %d DPI)", page_number, img.shape[1], img.shape[0], dpi)

    doc.close()
    return images


def _rotate_portrait_images(images: list[np.ndarray]) -> list[np.ndarray]:
    """将竖版（宽 < 高）的图片顺时针旋转 90° 变为横版。"""
    rotated = []
    for i, img in enumerate(images):
        h, w = img.shape[:2]
        if w < h:
            img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
            logger.info("  第 %d 页: 竖版 (%dx%d) → 旋转为横版 (%dx%d)", i, w, h, img.shape[1], img.shape[0])
        rotated.append(img)
    return rotated


def _save_page_images(
    images: list[np.ndarray],
    output_dir: Union[str, Path],
    pages: list[int] | None = None,
) -> list[Path]:
    """将页面图片保存到目录。"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    saved: list[Path] = []
    for idx, image in enumerate(images):
        page_num = pages[idx] if pages else idx
        img_path = output_dir / f"page_{page_num + 1}.png"
        cv2.imwrite(str(img_path), image)
        saved.append(img_path)
        logger.info("  保存页面图片: %s (%dx%d)", img_path.name, image.shape[1], image.shape[0])

    return saved


def extract_tables(
    pdf_path: Union[str, Path],
    lang: str = "ch",
    implicit_rows: bool = True,
    implicit_columns: bool = True,
    borderless_tables: bool = False,
    min_confidence: int = 50,
    pages: list[int] | None = None,
    image_dir: Union[str, Path] | None = None,
    dpi: int = 200,
) -> list[dict]:
    """从 PDF 中提取所有表格，返回结构化数据列表。

    :param pdf_path: PDF 文件路径
    :param lang: OCR 识别语言，默认中文 "ch"
    :param implicit_rows: 是否拆分隐式行
    :param implicit_columns: 是否拆分隐式列
    :param borderless_tables: 是否检测无边框表格
    :param min_confidence: OCR 最低置信度 (0-99)
    :param pages: 指定要处理的页码列表（从 0 开始），None 表示处理所有页
    :param image_dir: 若指定，将 PDF 页面图片保存到该目录
    :param dpi: PDF 渲染 DPI，越高越清晰但越慢（默认 200）
    :return: 包含 page/index/dataframe 的字典列表
    """
    pdf_path = str(pdf_path)
    logger.info("正在加载 PDF: %s", pdf_path)

    ocr = PaddleOCRAdapter(lang=lang)

    # 自定义 DPI 渲染 PDF 页面，传入 _images 跳过 img2table 默认渲染
    rendered = _render_pdf_images(pdf_path, pages, dpi)
    rendered = _rotate_portrait_images(rendered)
    pdf = PDF(src=pdf_path, pages=pages, _images=rendered)

    if image_dir is not None:
        _save_page_images(pdf.images, image_dir, pages)

    logger.info("正在检测表格并执行 OCR 识别...")
    tables_by_page: dict[int, list] = pdf.extract_tables(
        ocr=ocr,
        implicit_rows=implicit_rows,
        implicit_columns=implicit_columns,
        borderless_tables=borderless_tables,
        min_confidence=min_confidence,
    )

    result: list[dict] = []
    for page_num in sorted(tables_by_page.keys()):
        page_tables = tables_by_page[page_num]
        for i, table in enumerate(page_tables):
            df: pd.DataFrame = table.df
            if df is not None and not df.empty:
                result.append({
                    "page": page_num,
                    "index": i,
                    "dataframe": df,
                })
                logger.info(
                    "  第 %d 页 - 表格 %d: %d 行 x %d 列",
                    page_num, i + 1, len(df), len(df.columns),
                )

    logger.info("共提取到 %d 个表格", len(result))
    return result
