"""Local OCR using EasyOCR for reading card text from images."""

from pathlib import Path

import easyocr

# Model files stored in the repo for offline use
_MODEL_DIR = str(Path(__file__).resolve().parent.parent.parent / "models" / "ocr")


def run_ocr(image_path: str) -> list[str]:
    """
    Run EasyOCR on an image and return extracted text fragments.

    Args:
        image_path: Path to the image file

    Returns:
        List of text strings found in the image
    """
    reader = easyocr.Reader(
        ["en"],
        model_storage_directory=_MODEL_DIR,
        verbose=False,
    )
    results = reader.readtext(image_path, detail=0)
    return results


def run_ocr_with_boxes(image_path: str) -> list[dict]:
    """
    Run EasyOCR on an image and return text fragments with bounding boxes.

    Returns:
        List of dicts with keys: text, bbox ({x, y, w, h}), confidence
    """
    reader = easyocr.Reader(
        ["en"],
        model_storage_directory=_MODEL_DIR,
        verbose=False,
    )
    results = reader.readtext(image_path, detail=1)
    fragments = []
    for bbox, text, conf in results:
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
