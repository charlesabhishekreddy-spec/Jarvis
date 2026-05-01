from __future__ import annotations

from typing import Any

try:
    import pytesseract
except ImportError:  # pragma: no cover
    pytesseract = None


class OCRService:
    provider = "pytesseract"

    @property
    def provider_available(self) -> bool:
        return pytesseract is not None

    def extract_text(self, image: object) -> str:
        if pytesseract is None or image is None:
            return ""
        return pytesseract.image_to_string(image)

    def summarize_text(self, image: object, max_chars: int = 4000) -> dict[str, Any]:
        text = self.extract_text(image)
        normalized = text.strip()
        return {
            "provider": self.provider,
            "available": self.provider_available,
            "text": normalized[:max_chars],
            "char_count": len(normalized),
            "line_count": len([line for line in normalized.splitlines() if line.strip()]),
        }

    def snapshot(self) -> dict[str, Any]:
        return {"provider": self.provider, "available": self.provider_available}
