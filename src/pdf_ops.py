from __future__ import annotations

from pathlib import Path
from typing import Tuple

import fitz
import numpy as np


def get_pdf_page_size(pdf_path: Path) -> Tuple[float, float]:
    doc = fitz.open(str(pdf_path))
    try:
        if doc.page_count != 1:
            raise ValueError("当前实现仅支持单页PDF。")
        page = doc.load_page(0)
        return float(page.rect.width), float(page.rect.height)
    finally:
        doc.close()


def normalize_pdf_to_landscape(input_pdf: Path, output_pdf: Path) -> Path:
    src_doc = fitz.open(str(input_pdf))
    if src_doc.page_count != 1:
        src_doc.close()
        raise ValueError("当前实现仅支持单页PDF。")

    src_page = src_doc.load_page(0)
    width = float(src_page.rect.width)
    height = float(src_page.rect.height)

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    out_doc = fitz.open()
    try:
        if width >= height:
            new_page = out_doc.new_page(width=width, height=height)
            target_rect = fitz.Rect(0, 0, width, height)
            new_page.show_pdf_page(target_rect, src_doc, 0, rotate=0)
            print(f"[PDF] 输入已是横版，已按横版坐标重建输出: {output_pdf}")
        else:
            # 创建真正横版页面（宽高互换）并将源页内容逆时针旋转90度烘焙到新坐标系。
            new_page = out_doc.new_page(width=height, height=width)
            target_rect = fitz.Rect(0, 0, height, width)
            new_page.show_pdf_page(target_rect, src_doc, 0, rotate=90)
            print(f"[PDF] 输入为竖版，已重建为横版坐标PDF: {output_pdf}")
        out_doc.save(str(output_pdf))
    finally:
        out_doc.close()
        src_doc.close()

    return output_pdf


def render_pdf_page(
    pdf_path: Path, dpi: int
) -> Tuple[np.ndarray, float, float, float, float]:
    doc = fitz.open(str(pdf_path))
    try:
        if doc.page_count != 1:
            raise ValueError("当前实现仅支持单页PDF。")
        page = doc.load_page(0)
        pdf_width = float(page.rect.width)
        pdf_height = float(page.rect.height)
        zoom = dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
    finally:
        doc.close()

    image = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    scale_x = pix.width / pdf_width
    scale_y = pix.height / pdf_height
    return image, scale_x, scale_y, pdf_width, pdf_height


def pdf_to_png(
    pdf_path: Path, output_png: Path, dpi: int
) -> Tuple[Path, float, float, float, float]:
    image, scale_x, scale_y, pdf_width, pdf_height = render_pdf_page(pdf_path, dpi=dpi)
    output_png.parent.mkdir(parents=True, exist_ok=True)
    bgr_image = image[:, :, ::-1]
    import cv2

    cv2.imwrite(str(output_png), bgr_image)
    print(
        f"[PDF->PNG] 输出: {output_png}, dpi={dpi}, scale_x={scale_x:.6f}, scale_y={scale_y:.6f}"
    )
    return output_png, scale_x, scale_y, pdf_width, pdf_height
