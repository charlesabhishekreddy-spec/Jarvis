from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class KnowledgeFact:
    subject: str
    predicate: str
    object_value: str
    metadata: dict[str, Any] = field(default_factory=dict)


class KnowledgeGraphExtractor:
    def extract(self, text: str, metadata: dict[str, Any] | None = None) -> list[KnowledgeFact]:
        metadata = metadata or {}
        lowered = text.strip()
        facts: list[KnowledgeFact] = []

        favorite_match = re.search(r"my favorite ([a-zA-Z0-9 _-]+?) is ([a-zA-Z0-9 _+.#-]+)", lowered, re.IGNORECASE)
        if favorite_match:
            category = self._slugify(favorite_match.group(1))
            facts.append(
                KnowledgeFact(
                    subject="user",
                    predicate=f"favorite_{category}",
                    object_value=favorite_match.group(2).strip(),
                    metadata=metadata,
                )
            )

        prefer_match = re.search(r"i prefer ([a-zA-Z0-9 _+.#-]+)", lowered, re.IGNORECASE)
        if prefer_match:
            facts.append(KnowledgeFact(subject="user", predicate="prefers", object_value=prefer_match.group(1).strip(), metadata=metadata))

        use_match = re.search(r"i use ([a-zA-Z0-9 _+.#-]+)", lowered, re.IGNORECASE)
        if use_match:
            facts.append(KnowledgeFact(subject="user", predicate="uses", object_value=use_match.group(1).strip(), metadata=metadata))

        work_match = re.search(r"i work (?:on|with) ([a-zA-Z0-9 _+.#-]+)", lowered, re.IGNORECASE)
        if work_match:
            facts.append(
                KnowledgeFact(subject="user", predicate="works_with", object_value=work_match.group(1).strip(), metadata=metadata)
            )

        name_match = re.search(r"my name is ([a-zA-Z0-9 _.-]+)", lowered, re.IGNORECASE)
        if name_match:
            facts.append(KnowledgeFact(subject="user", predicate="name", object_value=name_match.group(1).strip(), metadata=metadata))

        return facts

    def _slugify(self, text: str) -> str:
        return re.sub(r"[^a-zA-Z0-9]+", "_", text.strip().lower()).strip("_")
