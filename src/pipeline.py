from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from .cell_detect import detect_cells_from_pdf
from .excel_export import export_to_excel
from .ocr_engine import OCREngine
from .pdf_ops import get_pdf_page_size, normalize_pdf_to_landscape, pdf_to_png
from .visualize import draw_cells_on_pdf


def _scale_cells(
    cells: List[Dict[str, float]], scale_x: float, scale_y: float
) -> List[Dict[str, int]]:
    scaled: List[Dict[str, int]] = []
    for idx, cell in enumerate(cells):
        scaled.append(
            {
                "index": int(cell.get("index", idx)),
                "x1": int(round(float(cell["x1"]) * scale_x)),
                "y1": int(round(float(cell["y1"]) * scale_y)),
                "x2": int(round(float(cell["x2"]) * scale_x)),
                "y2": int(round(float(cell["y2"]) * scale_y)),
            }
        )
    return scaled


def run_pipeline(
    input_pdf: Path,
    out_dir: Path,
    dpi: int = 200,
    detect_dpi: int = 300,
    max_recognitions: int = 500,
    lang: str = "ch",
    min_cell_width_px: int = 15,
    min_cell_height_px: int = 15,
    min_cell_area_px: int = 225,
    max_cell_width_ratio: float = 0.98,
    max_cell_height_ratio: float = 0.98,
    max_cell_area_ratio: float = 0.95,
    dedup_overlap_ratio: float = 0.98,
    container_min_children: int = 4,
    container_child_overlap_ratio: float = 0.95,
) -> None:
    if input_pdf.suffix.lower() != ".pdf":
        raise ValueError("输入文件必须为PDF。")
    if not input_pdf.exists():
        raise FileNotFoundError(f"输入文件不存在: {input_pdf}")
    if dpi <= 0 or detect_dpi <= 0:
        raise ValueError("dpi与detect-dpi必须为正整数。")
    if max_recognitions <= 0:
        raise ValueError("max-recognitions必须为正整数。")
    if min_cell_width_px <= 0 or min_cell_height_px <= 0 or min_cell_area_px <= 0:
        raise ValueError("最小单元格宽高面积参数必须为正整数。")
    if not (0 < max_cell_width_ratio <= 1):
        raise ValueError("max-cell-width-ratio 必须在 (0, 1]。")
    if not (0 < max_cell_height_ratio <= 1):
        raise ValueError("max-cell-height-ratio 必须在 (0, 1]。")
    if not (0 < max_cell_area_ratio <= 1):
        raise ValueError("max-cell-area-ratio 必须在 (0, 1]。")
    if not (0 < dedup_overlap_ratio <= 1):
        raise ValueError("dedup-overlap-ratio 必须在 (0, 1]。")
    if container_min_children < 0:
        raise ValueError("container-min-children 必须 >= 0。")
    if not (0 < container_child_overlap_ratio <= 1):
        raise ValueError("container-child-overlap-ratio 必须在 (0, 1]。")

    out_dir.mkdir(parents=True, exist_ok=True)
    stem = input_pdf.stem
    out_pdf = out_dir / f"{stem}-out.pdf"
    cells_json = out_dir / "cells.json"
    boxed_pdf = out_dir / f"{stem}-out-boxed.pdf"
    out_png = out_dir / f"{stem}-out.png"
    scaled_cells_json = out_dir / f"cells-{dpi}.json"
    out_xlsx = out_dir / f"{stem}-out.xlsx"

    normalize_pdf_to_landscape(input_pdf, out_pdf)
    page_w, page_h = get_pdf_page_size(out_pdf)
    print(f"[DEBUG] input-out.pdf 页面尺寸: width={page_w:.2f}, height={page_h:.2f}")
    cells = detect_cells_from_pdf(
        out_pdf,
        cells_json,
        detect_dpi=detect_dpi,
        min_cell_width_px=min_cell_width_px,
        min_cell_height_px=min_cell_height_px,
        min_cell_area_px=min_cell_area_px,
        max_cell_width_ratio=max_cell_width_ratio,
        max_cell_height_ratio=max_cell_height_ratio,
        max_cell_area_ratio=max_cell_area_ratio,
        dedup_overlap_ratio=dedup_overlap_ratio,
        container_min_children=container_min_children,
        container_child_overlap_ratio=container_child_overlap_ratio,
    )
    preview_count = min(5, len(cells))
    print(f"[DEBUG] cells.json 前{preview_count}个坐标样例:")
    for i in range(preview_count):
        cell = cells[i]
        print(
            "[DEBUG] "
            f"idx={int(cell.get('index', i))}, "
            f"x1={cell['x1']}, y1={cell['y1']}, x2={cell['x2']}, y2={cell['y2']}"
        )
    draw_cells_on_pdf(out_pdf, cells, boxed_pdf)

    _, scale_x, scale_y, _, _ = pdf_to_png(out_pdf, out_png, dpi=dpi)
    scaled_cells = _scale_cells(cells, scale_x=scale_x, scale_y=scale_y)
    with scaled_cells_json.open("w", encoding="utf-8") as f:
        json.dump(scaled_cells, f, ensure_ascii=False, indent=2)
    print(f"[CELL] 已输出缩放坐标: {scaled_cells_json}")

    ocr_engine = OCREngine(lang=lang)
    ocr_results = ocr_engine.recognize_regions(
        image_path=str(out_png),
        cells=scaled_cells,
        max_recognitions=max_recognitions,
    )

    export_to_excel(ocr_results, str(out_xlsx))
    print("[DONE] 全流程完成。")
