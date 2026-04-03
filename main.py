from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract table data from scanned PDF to Excel."
    )
    parser.add_argument("--input", required=True, help="Input single-page PDF path.")
    parser.add_argument("--out", required=True, help="Output directory path.")
    parser.add_argument("--dpi", type=int, default=200, help="PNG render DPI.")
    parser.add_argument(
        "--detect-dpi",
        type=int,
        default=300,
        help="DPI for table cell detection on PDF raster.",
    )
    parser.add_argument(
        "--max-recognitions",
        type=int,
        default=500,
        help="Maximum number of OCR regions to process.",
    )
    parser.add_argument(
        "--lang",
        default="ch",
        help="PaddleOCR language, default is ch.",
    )
    parser.add_argument(
        "--min-cell-width-px",
        type=int,
        default=15,
        help="Filter out cells smaller than this width in detection raster image.",
    )
    parser.add_argument(
        "--min-cell-height-px",
        type=int,
        default=15,
        help="Filter out cells smaller than this height in detection raster image.",
    )
    parser.add_argument(
        "--min-cell-area-px",
        type=int,
        default=225,
        help="Filter out cells smaller than this area in detection raster image.",
    )
    parser.add_argument(
        "--max-cell-width-ratio",
        type=float,
        default=0.98,
        help="Filter out cells larger than this page width ratio.",
    )
    parser.add_argument(
        "--max-cell-height-ratio",
        type=float,
        default=0.98,
        help="Filter out cells larger than this page height ratio.",
    )
    parser.add_argument(
        "--max-cell-area-ratio",
        type=float,
        default=0.95,
        help="Filter out cells larger than this page area ratio.",
    )
    parser.add_argument(
        "--dedup-overlap-ratio",
        type=float,
        default=0.98,
        help="Drop near-duplicate boxes when overlap on smaller box exceeds this ratio.",
    )
    parser.add_argument(
        "--container-min-children",
        type=int,
        default=4,
        help="Drop a large box if it contains at least this many smaller boxes.",
    )
    parser.add_argument(
        "--container-child-overlap-ratio",
        type=float,
        default=0.95,
        help="Containment threshold between large box and child boxes.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    from src.pipeline import run_pipeline

    run_pipeline(
        input_pdf=Path(args.input),
        out_dir=Path(args.out),
        dpi=args.dpi,
        detect_dpi=args.detect_dpi,
        max_recognitions=args.max_recognitions,
        lang=args.lang,
        min_cell_width_px=args.min_cell_width_px,
        min_cell_height_px=args.min_cell_height_px,
        min_cell_area_px=args.min_cell_area_px,
        max_cell_width_ratio=args.max_cell_width_ratio,
        max_cell_height_ratio=args.max_cell_height_ratio,
        max_cell_area_ratio=args.max_cell_area_ratio,
        dedup_overlap_ratio=args.dedup_overlap_ratio,
        container_min_children=args.container_min_children,
        container_child_overlap_ratio=args.container_child_overlap_ratio,
    )


if __name__ == "__main__":
    main()
