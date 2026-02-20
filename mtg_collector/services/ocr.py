"""Local OCR using PaddleOCR for reading card text from images."""

from paddleocr import PaddleOCR

_ocr = None


def _get_ocr() -> PaddleOCR:
    global _ocr
    if _ocr is None:
        _ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
    return _ocr


def run_ocr(image_path: str) -> list[str]:
    """
    Run OCR on an image and return extracted text fragments.

    Args:
        image_path: Path to the image file

    Returns:
        List of text strings found in the image
    """
    ocr = _get_ocr()
    results = ocr.ocr(image_path, cls=True)
    return [text for _, (text, _) in results[0]]


def run_ocr_with_boxes(image_path: str) -> list[dict]:
    """
    Run OCR on an image and return text fragments with bounding boxes.

    Returns:
        List of dicts with keys: text, bbox ({x, y, w, h}), confidence
    """
    ocr = _get_ocr()
    results = ocr.ocr(image_path, cls=True)
    fragments = []
    for bbox, (text, conf) in results[0]:
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
