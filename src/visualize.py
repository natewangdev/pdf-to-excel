from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import fitz


def draw_cells_on_pdf(pdf_path: Path, cells: List[Dict[str, float]], output_pdf: Path) -> Path:
    doc = fitz.open(str(pdf_path))
    try:
        if doc.page_count != 1:
            raise ValueError("当前实现仅支持单页PDF。")
        page = doc.load_page(0)
        for idx, cell in enumerate(cells):
            x1, y1, x2, y2 = cell["x1"], cell["y1"], cell["x2"], cell["y2"]
            rect = fitz.Rect(x1, y1, x2, y2)
            page.draw_rect(rect, color=(1, 0, 0), width=0.8)
            text = str(idx)
            fontsize = 5.0
            text_width = fitz.get_text_length(text, fontsize=fontsize)
            cx = (x1 + x2) / 2.0
            cy = (y1 + y2) / 2.0
            text_x = cx - (text_width / 2.0)
            # insert_text 使用基线坐标，这里用近似系数把文本视觉上放到垂直居中。
            text_y = cy + (fontsize * 0.35)
            page.insert_text(
                fitz.Point(text_x, text_y),
                text,
                fontsize=fontsize,
                color=(0, 0, 1),
            )
        output_pdf.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(output_pdf))
    finally:
        doc.close()
    print(f"[VIS] 已输出带框PDF: {output_pdf}")
    return output_pdf
