from __future__ import annotations

import asyncio
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any


TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_]+")


class JsonVectorStore:
    def __init__(self, index_path: str) -> None:
        self.index_path = Path(index_path)
        self._items: list[dict[str, Any]] = []

    async def initialize(self) -> None:
        await asyncio.to_thread(self._initialize_sync)

    def _initialize_sync(self) -> None:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        if self.index_path.exists():
            self._items = json.loads(self.index_path.read_text(encoding="utf-8"))
        else:
            self._persist_sync()

    async def add(self, item_id: str, content: str, metadata: dict[str, Any]) -> None:
        await asyncio.to_thread(self._add_sync, item_id, content, metadata)

    def _add_sync(self, item_id: str, content: str, metadata: dict[str, Any]) -> None:
        tokens = self._tokenize(content)
        self._items.append(
            {
                "item_id": item_id,
                "content": content,
                "metadata": metadata,
                "tokens": tokens,
            }
        )
        self._persist_sync()

    async def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._search_sync, query, limit)

    def _search_sync(self, query: str, limit: int) -> list[dict[str, Any]]:
        query_tokens = self._tokenize(query)
        scores: list[tuple[float, dict[str, Any]]] = []
        for item in self._items:
            score = self._cosine_similarity(query_tokens, item["tokens"])
            if score > 0:
                scores.append((score, item))
        scores.sort(key=lambda entry: entry[0], reverse=True)
        return [
            {
                "item_id": item["item_id"],
                "content": item["content"],
                "metadata": item["metadata"],
                "score": round(score, 4),
            }
            for score, item in scores[:limit]
        ]

    def _persist_sync(self) -> None:
        self.index_path.write_text(json.dumps(self._items, indent=2), encoding="utf-8")

    def _tokenize(self, content: str) -> dict[str, int]:
        return dict(Counter(match.group(0).lower() for match in TOKEN_PATTERN.finditer(content)))

    def _cosine_similarity(self, left: dict[str, int], right: dict[str, int]) -> float:
        intersection = set(left) & set(right)
        numerator = sum(left[token] * right[token] for token in intersection)
        left_norm = math.sqrt(sum(value * value for value in left.values()))
        right_norm = math.sqrt(sum(value * value for value in right.values()))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return numerator / (left_norm * right_norm)
