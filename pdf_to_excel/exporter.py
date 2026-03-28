"""Excel 导出模块"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Union

import pandas as pd

logger = logging.getLogger(__name__)

MAX_SHEET_NAME_LEN = 31  # Excel sheet 名称最大长度


def _make_sheet_name(page: int, index: int, total: int) -> str:
    """生成 sheet 名称，确保不超过 Excel 31 字符限制。"""
    if total == 1:
        return f"Page{page + 1}"
    return f"Page{page + 1}_Table{index + 1}"


def export_to_excel(
    tables: list[dict],
    output_path: Union[str, Path],
) -> Path:
    """将表格列表导出到 Excel 文件，每个表格一个 sheet。

    :param tables: extract_tables 返回的字典列表
    :param output_path: 输出 Excel 文件路径
    :return: 输出文件的 Path 对象
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not tables:
        logger.warning("没有可导出的表格数据")
        wb = pd.ExcelWriter(output_path, engine="openpyxl")
        wb.close()
        return output_path

    seen_names: dict[str, int] = {}
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        for table_info in tables:
            name = _make_sheet_name(
                table_info["page"],
                table_info["index"],
                len(tables),
            )
            # 处理重名
            if name in seen_names:
                seen_names[name] += 1
                name = f"{name}_{seen_names[name]}"
            else:
                seen_names[name] = 0

            name = name[:MAX_SHEET_NAME_LEN]

            df: pd.DataFrame = table_info["dataframe"]
            df.to_excel(writer, sheet_name=name, index=False)
            logger.info("  写入 sheet: %s (%d 行)", name, len(df))

    logger.info("Excel 文件已保存: %s", output_path)
    return output_path
