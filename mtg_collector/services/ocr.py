"""Local OCR for reading card text from images.

Prefers PaddleOCR (faster, higher quality). Falls back to EasyOCR if
PaddleOCR is unavailable (e.g. paddlepaddle not built for the platform).
"""

import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)

# PaddleOCR has an intermittent IndexError in its rec batching logic.
# https://github.com/PaddlePaddle/PaddleOCR/issues/8776
_PADDLE_RETRIES = 3

_ENGINE = os.environ.get("OCR_ENGINE")
if _ENGINE is None:
    try:
        from paddleocr import PaddleOCR
        _ENGINE = "paddle"
    except ImportError:
        _ENGINE = "easyocr"
elif _ENGINE == "paddle":
    from paddleocr import PaddleOCR

_ocr = None

# EasyOCR model files stored in the repo for offline use
_EASYOCR_MODEL_DIR = str(Path(__file__).resolve().parent.parent.parent / "models" / "ocr")


def _get_ocr():
    global _ocr
    if _ocr is not None:
        return _ocr
    if _ENGINE == "paddle":
        _ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
    else:
        import easyocr
        _ocr = easyocr.Reader(
            ["en"], gpu=False, model_storage_directory=_EASYOCR_MODEL_DIR, verbose=False,
        )
    return _ocr


def _paddle_ocr_with_retry(ocr, image_path: str):
    """Call PaddleOCR with retries for its intermittent IndexError."""
    for attempt in range(_PADDLE_RETRIES):
        try:
            return ocr.ocr(image_path, cls=True)
        except IndexError:
            if attempt < _PADDLE_RETRIES - 1:
                log.warning("PaddleOCR IndexError on attempt %d, retrying", attempt + 1)
            else:
                raise


def run_ocr(image_path: str) -> list[str]:
    """
    Run OCR on an image and return extracted text fragments.

    Args:
        image_path: Path to the image file

    Returns:
        List of text strings found in the image
    """
    ocr = _get_ocr()
    if _ENGINE == "paddle":
        results = _paddle_ocr_with_retry(ocr, image_path)
        return [text for _, (text, _) in results[0]]
    else:
        img = _load_image_cv2(image_path)
        return ocr.readtext(img, detail=0, decoder="beamsearch")


def run_ocr_with_boxes(image_path: str) -> list[dict]:
    """
    Run OCR on an image and return text fragments with bounding boxes.

    Returns:
        List of dicts with keys: text, bbox ({x, y, w, h}), confidence
    """
    ocr = _get_ocr()
    if _ENGINE == "paddle":
        results = _paddle_ocr_with_retry(ocr, image_path)
        fragments = []
        for bbox, (text, conf) in results[0]:
            if not text or not text.strip():
                continue
            xs = [p[0] for p in bbox]
            ys = [p[1] for p in bbox]
            fragments.append({
                "text": text,
                "bbox": {
                    "x": min(xs),
                    "y": min(ys),
                    "w": max(xs) - min(xs),
                    "h": max(ys) - min(ys),
                },
                "confidence": round(float(conf), 3),
            })
        return fragments
    else:
        img = _load_image_cv2(image_path)
        results = ocr.readtext(img, detail=1, decoder="beamsearch")
        fragments = []
        for bbox, text, conf in results:
            if not text or not text.strip():
                continue
            xs = [float(p[0]) for p in bbox]
            ys = [float(p[1]) for p in bbox]
            fragments.append({
                "text": text,
                "bbox": {
                    "x": min(xs),
                    "y": min(ys),
                    "w": max(xs) - min(xs),
                    "h": max(ys) - min(ys),
                },
                "confidence": round(float(conf), 3),
            })
        return fragments


def _load_image_cv2(image_path: str):
    """Load an image as a numpy array, using PIL as fallback for formats OpenCV can't handle."""
    import cv2
    import numpy as np
    img = cv2.imread(image_path)
    if img is not None:
        return img
    from PIL import Image
    pil_img = Image.open(image_path)
    pil_img = pil_img.convert("RGB")
    arr = np.array(pil_img)
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
