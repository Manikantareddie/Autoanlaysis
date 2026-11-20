from __future__ import annotations

import re
from typing import Literal

QueryRoute = Literal["structured_sql", "semantic_rag", "hybrid"]

# Math / aggregation indicators
SQL_KEYWORDS = {
    "total", "sum", "average", "avg", "mean", "median", "count", "percentage",
    "pct", "ratio", "rate", "trend", "monthly", "yearly", "growth", "top", "bottom",
    "highest", "lowest", "distribution", "breakdown", "revenue", "profit", "sales",
    "quantity", "margin", "discount", "volume", "compare", "min", "max", "how", "many", "number"
}

# Qualitative / semantic indicators
SEMANTIC_KEYWORDS = {
    "mention", "mentions", "mentioned", "complaint", "complaints", "feedback",
    "issue", "issues", "problem", "problems", "review", "reviews", "comment",
    "comments", "reason", "reasons", "defect", "defective", "broken", "damaged",
    "late", "delayed", "delay", "service", "experience", "text", "description",
    "describe", "why", "qualitative", "unhappy", "dissatisfied"
}


def classify_query(question: str) -> QueryRoute:
    """
    Intelligent query router:
    - structured_sql: Aggregation & metrics without semantic text search
    - semantic_rag: Finding specific text records or qualitative observations
    - hybrid: Mathematical aggregation conditioned on semantic text retrieval
    """
    q_lower = question.lower()
    tokens = set(re.findall(r"\w+", q_lower))

    has_sql = bool(tokens & SQL_KEYWORDS)
    has_semantic = bool(tokens & SEMANTIC_KEYWORDS)

    # Detect hybrid patterns: (how many / total / average) + (mention / complaint / feedback / damaged / ...)
    if has_sql and has_semantic:
        return "hybrid"

    if has_semantic:
        return "semantic_rag"

    # Default to structured SQL analytics for tabular datasets
    return "structured_sql"
