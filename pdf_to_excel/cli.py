"""命令行入口"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

import click

from .extractor import extract_tables
from .exporter import export_to_excel


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


@click.command(help="从 PDF 文件中提取表格数据并导出到 Excel。")
@click.argument("pdf_path", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "-o", "--output",
    default=None,
    type=click.Path(),
    help="输出 Excel 文件路径，默认与 PDF 同名 .xlsx",
)
@click.option(
    "-l", "--lang",
    default="ch",
    show_default=True,
    help="OCR 识别语言",
)
@click.option(
    "--borderless/--no-borderless",
    default=False,
    show_default=True,
    help="是否检测无边框表格",
)
@click.option(
    "--min-confidence",
    default=50,
    type=click.IntRange(0, 99),
    show_default=True,
    help="OCR 最低置信度 (0-99)",
)
@click.option(
    "--pages",
    default=None,
    help="要处理的页码，逗号分隔，从 1 开始。例如: 1,3,5",
)
@click.option(
    "--save-images",
    default=None,
    type=click.Path(),
    help="将 PDF 页面图片保存到指定目录",
)
@click.option(
    "--dpi",
    default=200,
    type=click.IntRange(72, 600),
    show_default=True,
    help="PDF 渲染 DPI，越高越清晰但越慢",
)
@click.option("-v", "--verbose", is_flag=True, help="显示详细日志")
def main(
    pdf_path: str,
    output: str | None,
    lang: str,
    borderless: bool,
    min_confidence: int,
    pages: str | None,
    save_images: str | None,
    dpi: int,
    verbose: bool,
) -> None:
    _setup_logging(verbose)

    pdf_path = Path(pdf_path)
    if output is None:
        output_path = pdf_path.with_suffix(".xlsx")
    else:
        output_path = Path(output)

    page_list: list[int] | None = None
    if pages:
        try:
            page_list = [int(p.strip()) - 1 for p in pages.split(",")]
        except ValueError:
            click.echo("错误: --pages 参数格式不正确，应为逗号分隔的数字，如 1,3,5", err=True)
            sys.exit(1)

    click.echo(f"PDF 文件: {pdf_path}")
    click.echo(f"输出路径: {output_path}")

    start = time.time()

    tables = extract_tables(
        pdf_path=pdf_path,
        lang=lang,
        borderless_tables=borderless,
        min_confidence=min_confidence,
        pages=page_list,
        image_dir=save_images,
        dpi=dpi,
    )

    if not tables:
        click.echo("未检测到任何表格。")
        sys.exit(0)

    export_to_excel(tables, output_path)

    elapsed = time.time() - start
    click.echo(f"完成！共提取 {len(tables)} 个表格，耗时 {elapsed:.1f} 秒")
    click.echo(f"已保存到: {output_path}")


if __name__ == "__main__":
    main()
