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
