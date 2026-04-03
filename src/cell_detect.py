from __future__ import annotations

import json
from pathlib import Path
from statistics import median
from typing import Dict, List

import cv2
import numpy as np

from .pdf_ops import render_pdf_page


Cell = Dict[str, float]


def _intersection_area(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    x1 = max(a[0], b[0])
    y1 = max(a[1], b[1])
    x2 = min(a[2], b[2])
    y2 = min(a[3], b[3])
    if x2 <= x1 or y2 <= y1:
        return 0.0
    return float((x2 - x1) * (y2 - y1))


def _rect_area(rect: tuple[int, int, int, int]) -> float:
    return float(max(0, rect[2] - rect[0]) * max(0, rect[3] - rect[1]))


def _filter_duplicate_and_container_rects(
    rects_px: List[tuple[int, int, int, int]],
    dedup_overlap_ratio: float,
    container_min_children: int,
    container_child_overlap_ratio: float,
) -> tuple[List[tuple[int, int, int, int]], int, int]:
    if not rects_px:
        return rects_px, 0, 0

    sorted_rects = sorted(rects_px, key=_rect_area)
    dedup_kept: List[tuple[int, int, int, int]] = []
    skipped_duplicate = 0
    for rect in sorted_rects:
        rect_area = _rect_area(rect)
        is_duplicate = False
        for kept in dedup_kept:
            inter = _intersection_area(rect, kept)
            min_area = min(rect_area, _rect_area(kept))
            if min_area <= 0:
                continue
            overlap_on_smaller = inter / min_area
            if overlap_on_smaller >= dedup_overlap_ratio:
                is_duplicate = True
                break
        if is_duplicate:
            skipped_duplicate += 1
            continue
        dedup_kept.append(rect)

    if container_min_children <= 0:
        return dedup_kept, skipped_duplicate, 0

    to_drop = set()
    n = len(dedup_kept)
    areas = [_rect_area(r) for r in dedup_kept]
    for i in range(n):
        outer = dedup_kept[i]
        outer_area = areas[i]
        contained_children = 0
        for j in range(n):
            if i == j:
                continue
            inner = dedup_kept[j]
            inner_area = areas[j]
            if inner_area <= 0 or inner_area >= outer_area:
                continue
            inter = _intersection_area(outer, inner)
            if inter / inner_area >= container_child_overlap_ratio:
                contained_children += 1
                if contained_children >= container_min_children:
                    to_drop.add(i)
                    break

    final_rects = [rect for idx, rect in enumerate(dedup_kept) if idx not in to_drop]
    return final_rects, skipped_duplicate, len(to_drop)


def _sort_cells_row_major(cells: List[Cell]) -> List[Cell]:
    if not cells:
        return []
    heights = [cell["y2"] - cell["y1"] for cell in cells]
    row_tol = max(3.0, float(median(heights)) * 0.6)
    cells_sorted = sorted(cells, key=lambda c: (c["y1"], c["x1"]))

    rows: List[List[Cell]] = []
    current_row: List[Cell] = []
    baseline_y = None

    for cell in cells_sorted:
        if baseline_y is None:
            current_row = [cell]
            baseline_y = cell["y1"]
            continue
        if abs(cell["y1"] - baseline_y) <= row_tol:
            current_row.append(cell)
            baseline_y = (baseline_y + cell["y1"]) / 2.0
        else:
            rows.append(sorted(current_row, key=lambda c: c["x1"]))
            current_row = [cell]
            baseline_y = cell["y1"]
    if current_row:
        rows.append(sorted(current_row, key=lambda c: c["x1"]))

    flattened: List[Cell] = []
    for row in rows:
        flattened.extend(row)
    for idx, cell in enumerate(flattened):
        cell["index"] = idx
    return flattened


def detect_cells_from_pdf(
    pdf_path: Path,
    cells_json_path: Path,
    detect_dpi: int = 300,
    min_cell_width_px: int = 15,
    min_cell_height_px: int = 15,
    min_cell_area_px: int = 225,
    max_cell_width_ratio: float = 0.98,
    max_cell_height_ratio: float = 0.98,
    max_cell_area_ratio: float = 0.95,
    dedup_overlap_ratio: float = 0.98,
    container_min_children: int = 4,
    container_child_overlap_ratio: float = 0.95,
) -> List[Cell]:
    rgb_image, scale_x, scale_y, _, _ = render_pdf_page(pdf_path, dpi=detect_dpi)
    bgr = rgb_image[:, :, ::-1]
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    binary = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        15,
        8,
    )

    h, w = binary.shape
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(20, w // 30), 1))
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(20, h // 30)))

    horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel, iterations=1)
    vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel, iterations=1)
    grid = cv2.add(horizontal, vertical)
    grid = cv2.dilate(grid, np.ones((3, 3), dtype=np.uint8), iterations=1)

    contours, _ = cv2.findContours(grid, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    page_area = float(w * h)
    max_cell_area_px = page_area * max_cell_area_ratio
    rects_px = []
    skipped_too_small = 0
    skipped_too_big = 0
    for contour in contours:
        x, y, cw, ch = cv2.boundingRect(contour)
        area = float(cw * ch)
        if cw < min_cell_width_px or ch < min_cell_height_px or area < min_cell_area_px:
            skipped_too_small += 1
            continue
        if (
            cw > max_cell_width_ratio * w
            or ch > max_cell_height_ratio * h
            or area > max_cell_area_px
        ):
            skipped_too_big += 1
            continue
        rects_px.append((x, y, x + cw, y + ch))

    rects_px = sorted(set(rects_px))
    rects_px, skipped_duplicate, skipped_container = _filter_duplicate_and_container_rects(
        rects_px=rects_px,
        dedup_overlap_ratio=dedup_overlap_ratio,
        container_min_children=container_min_children,
        container_child_overlap_ratio=container_child_overlap_ratio,
    )
    cells_pdf: List[Cell] = []
    for x1, y1, x2, y2 in rects_px:
        cells_pdf.append(
            {
                "x1": round(x1 / scale_x, 3),
                "y1": round(y1 / scale_y, 3),
                "x2": round(x2 / scale_x, 3),
                "y2": round(y2 / scale_y, 3),
            }
        )

    cells_pdf = _sort_cells_row_major(cells_pdf)
    cells_json_path.parent.mkdir(parents=True, exist_ok=True)
    with cells_json_path.open("w", encoding="utf-8") as f:
        json.dump(cells_pdf, f, ensure_ascii=False, indent=2)

    print(
        "[CELL] 过滤统计: "
        f"too_small={skipped_too_small}, too_big={skipped_too_big}, "
        f"duplicate={skipped_duplicate}, container={skipped_container}, kept={len(cells_pdf)}"
    )
    print(f"[CELL] 检测到单元格数量: {len(cells_pdf)}")
    print(f"[CELL] 已输出: {cells_json_path}")
    return cells_pdf
