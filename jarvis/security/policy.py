from __future__ import annotations

import re

from jarvis.core.models import RiskAssessment, RiskLevel


CRITICAL_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\brm\b",
        r"\bdel\b",
        r"\bformat\b",
        r"\bshutdown\b",
        r"\breboot\b",
        r"\breg\s+delete\b",
        r"\bnet\s+user\b",
    )
]

HIGH_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bpip\s+install\b",
        r"\bgit\s+push\b",
        r"\btaskkill\b",
        r"\bsc\b",
        r"\bwmic\b",
        r"\bsubprocess\b",
        r"\bexecute\b",
    )
]


class CommandSafetyPolicy:
    def assess(self, text: str, confirm_dangerous: bool) -> RiskAssessment:
        normalized = text.strip()
        for pattern in CRITICAL_PATTERNS:
            if pattern.search(normalized):
                return RiskAssessment(
                    level=RiskLevel.CRITICAL,
                    reason="The request appears to contain a destructive or privilege-sensitive system command.",
                    requires_confirmation=confirm_dangerous,
                    recommended_action="Ask the user for explicit confirmation before continuing.",
                )
        for pattern in HIGH_PATTERNS:
            if pattern.search(normalized):
                return RiskAssessment(
                    level=RiskLevel.HIGH,
                    reason="The request may change the system state or external resources.",
                    requires_confirmation=confirm_dangerous,
                    recommended_action="Proceed only if the user intended a system-level action.",
                )
        if any(word in normalized.lower() for word in ("open", "launch", "search", "remember", "summarize", "report")):
            return RiskAssessment(
                level=RiskLevel.LOW,
                reason="The request is a normal assistant action.",
                requires_confirmation=False,
                recommended_action="Proceed.",
            )
        return RiskAssessment(
            level=RiskLevel.MEDIUM,
            reason="The request is not explicitly dangerous but may require system context.",
            requires_confirmation=False,
            recommended_action="Proceed with normal safeguards.",
        )
