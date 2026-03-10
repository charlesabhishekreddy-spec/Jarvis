from __future__ import annotations

try:
    import pytesseract
except ImportError:  # pragma: no cover
    pytesseract = None


class OCRService:
    def extract_text(self, image: object) -> str:
        if pytesseract is None or image is None:
            return ""
        return pytesseract.image_to_string(image)
