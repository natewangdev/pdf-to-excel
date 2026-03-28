"""PaddleOCR 适配器，实现 img2table 的 OCRInstance 接口。

使用 PP-OCRv4 模型避免 PP-OCRv5 在 PaddlePaddle 3.x 的 PIR+OneDNN 兼容性问题。
逐张图片处理以支持进度日志。
"""

from __future__ import annotations

import logging
from typing import Any

import polars as pl
from img2table.document.base import Document
from img2table.ocr.base import OCRInstance
from img2table.ocr.data import OCRDataframe

logger = logging.getLogger(__name__)


class PaddleOCRAdapter(OCRInstance):
    """基于 PaddleOCR PP-OCRv4 的 img2table OCR 适配器。"""

    def __init__(self, lang: str = "ch", **kwargs: Any) -> None:
        from paddleocr import PaddleOCR

        self.ocr = PaddleOCR(
            lang=lang,
            ocr_version="PP-OCRv4",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            **kwargs,
        )

    def content(self, document: Document) -> list[list]:
        results: list[list] = []
        for i, image in enumerate(document.images):
            logger.debug("  OCR 处理第 %d 张图片 (%dx%d)", i, image.shape[1], image.shape[0])
            page_results = []
            for res in self.ocr.predict(input=image):
                for text, score, box in zip(
                    res["rec_texts"], res["rec_scores"], res["rec_boxes"]
                ):
                    page_results.append((box.tolist(), text, float(score)))
            results.append(page_results)
        return results

    def to_ocr_dataframe(self, content: list[list]) -> OCRDataframe | None:
        list_elements = []

        for page, ocr_result in enumerate(content):
            for idx, (bbox, text, confidence) in enumerate(ocr_result):
                x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
                list_elements.append({
                    "page": page,
                    "class": "ocrx_word",
                    "id": f"word_{page + 1}_{idx + 1}",
                    "parent": f"word_{page + 1}_{idx + 1}",
                    "value": text,
                    "confidence": round(confidence * 100),
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                })

        if not list_elements:
            return None

        return OCRDataframe(
            df=pl.DataFrame(list_elements, schema=self.pl_schema)
        )
