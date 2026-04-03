from __future__ import annotations

import time
from typing import Dict, List, Tuple

import cv2
from paddleocr import PaddleOCR


class OCREngine:
    def __init__(self, lang: str = "ch") -> None:
        self.mode, self.ocr = self._build_ocr(lang=lang)
        print(f"[OCR] 当前识别模式: {self.mode}")

    @staticmethod
    def _gpu_available() -> bool:
        try:
            import paddle

            return bool(paddle.device.is_compiled_with_cuda() and paddle.device.cuda.device_count() > 0)
        except Exception:
            return False

    @staticmethod
    def _build_ocr(lang: str) -> Tuple[str, PaddleOCR]:
        preferred_mode = "gpu" if OCREngine._gpu_available() else "cpu"

        # 优先尝试 3.x 风格（device 参数）
        try:
            device = "gpu:0" if preferred_mode == "gpu" else "cpu"
            return preferred_mode, PaddleOCR(lang=lang, device=device, enable_mkldnn=False)
        except Exception as device_error:
            if preferred_mode == "gpu":
                print(f"[OCR] GPU不可用，回退CPU。原因: {device_error}")
                try:
                    return "cpu", PaddleOCR(lang=lang, device="cpu", enable_mkldnn=False)
                except Exception:
                    pass

        # 回退尝试 2.x 风格（use_gpu 参数）
        try:
            if preferred_mode == "gpu":
                return "gpu", PaddleOCR(lang=lang, use_gpu=True, use_angle_cls=False)
            return "cpu", PaddleOCR(lang=lang, use_gpu=False, use_angle_cls=False)
        except Exception as old_style_error:
            if preferred_mode == "gpu":
                print(f"[OCR] GPU旧参数不可用，回退CPU。原因: {old_style_error}")
                return "cpu", PaddleOCR(lang=lang, use_gpu=False, use_angle_cls=False)
            raise

    @staticmethod
    def _extract_text(ocr_result: object) -> str:
        if ocr_result is None:
            return ""

        # PaddleOCR 3.x 常见结构: list[dict], dict中含 rec_texts
        if isinstance(ocr_result, list) and ocr_result:
            first = ocr_result[0]
            if isinstance(first, dict):
                rec_texts = first.get("rec_texts")
                if isinstance(rec_texts, list):
                    return " ".join(str(x) for x in rec_texts if x).strip()
                if "text" in first:
                    return str(first["text"]).strip()

            # PaddleOCR 2.x 常见结构: list[list[[box, (text, score)], ...]]
            if isinstance(first, list):
                parts = []
                for line in first:
                    if isinstance(line, (list, tuple)) and len(line) > 1:
                        info = line[1]
                        if isinstance(info, (list, tuple)) and info:
                            parts.append(str(info[0]))
                return " ".join(parts).strip()

        # 兜底处理：部分版本返回对象
        if hasattr(ocr_result, "rec_texts"):
            rec_texts = getattr(ocr_result, "rec_texts")
            if isinstance(rec_texts, list):
                return " ".join(str(x) for x in rec_texts if x).strip()

        return ""

    def recognize_regions(
        self,
        image_path: str,
        cells: List[Dict[str, int]],
        max_recognitions: int,
    ) -> List[Dict[str, object]]:
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"无法读取图片: {image_path}")

        results: List[Dict[str, object]] = []
        total = len(cells)
        limit = min(max_recognitions, total)
        if limit < total:
            print(f"[OCR] 识别次数限制生效: {limit}/{total}")

        for idx, cell in enumerate(cells):
            x1, y1, x2, y2 = int(cell["x1"]), int(cell["y1"]), int(cell["x2"]), int(cell["y2"])
            if idx >= limit:
                results.append({**cell, "text": "", "elapsed_ms": 0.0, "skipped": True})
                continue
            roi = image[max(y1, 0) : max(y2, 0), max(x1, 0) : max(x2, 0)]
            start = time.perf_counter()
            text = ""
            if roi.size > 0:
                ocr_result = self.ocr.ocr(roi)
                text = self._extract_text(ocr_result)
            elapsed_ms = (time.perf_counter() - start) * 1000
            print(
                f"[OCR] region=({x1},{y1},{x2},{y2}) text='{text}' elapsed={elapsed_ms:.1f}ms"
            )
            results.append({**cell, "text": text, "elapsed_ms": round(elapsed_ms, 3), "skipped": False})

        return results
