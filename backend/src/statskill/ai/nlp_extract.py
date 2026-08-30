"""Lightweight NLP extraction from role descriptions and software tool lists."""

from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class ExtractedSkill:
    skill_id: str
    skill_name: str
    skill_type: str
    confidence: str
    source: str
    score: float


def _tokenize(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9+#.]+", text.lower())
    return set(words)


def _benchmark_to_level(benchmark: float, scale: float = 0.85) -> int:
    return max(30, min(95, int(round(benchmark * scale))))


def extract_from_tools(
    tools_text: str,
    unified_df: pd.DataFrame,
    benchmark_level: float = 50.0,
) -> list[ExtractedSkill]:
    """Match comma-separated software tools to unified tool entries."""
    if not tools_text or pd.isna(tools_text):
        return []

    tool_index = {
        str(row["skill_name"]).lower(): row
        for _, row in unified_df[unified_df["skill_type"] == "tool"].iterrows()
    }
    required_level = _benchmark_to_level(benchmark_level, 0.9)

    results: list[ExtractedSkill] = []
    for part in str(tools_text).split(","):
        name = part.strip()
        if not name:
            continue
        row = tool_index.get(name.lower())
        if row is None:
            continue
        results.append(
            ExtractedSkill(
                skill_id=str(row["skill_id"]),
                skill_name=str(row["skill_name"]),
                skill_type="tool",
                confidence="high",
                source="nlp_tools",
                score=float(required_level),
            )
        )
    return results


def extract_from_description(
    description: str,
    unified_df: pd.DataFrame,
    benchmark_level: float = 50.0,
    max_matches: int = 25,
) -> list[ExtractedSkill]:
    """Match taxonomy skill names mentioned in role descriptions."""
    if not description or pd.isna(description):
        return []

    text = str(description).lower()
    text_tokens = _tokenize(text)
    required_level = _benchmark_to_level(benchmark_level, 0.75)

    matches: list[ExtractedSkill] = []
    # Role prose describes competencies; matching every O*NET tool and short
    # verb creates false role mappings (for example Analyze/Extract/Transform).
    generic_terms = {"analyze", "extract", "transform", "apply", "report", "develop", "implement"}
    candidates = unified_df[unified_df["skill_type"].astype(str) == "competency"]
    for _, row in candidates.iterrows():
        name = str(row["skill_name"])
        name_lower = name.lower()
        if len(name_lower) < 4 or (" " not in name_lower and name_lower in generic_terms):
            continue

        hit = False
        if name_lower in text:
            hit = True
        # Require the competency phrase itself. Token-subset matching causes
        # false positives such as "3D Modeling" from "data modeling".

        if hit:
            matches.append(
                ExtractedSkill(
                    skill_id=str(row["skill_id"]),
                    skill_name=name,
                    skill_type=str(row["skill_type"]),
                    confidence="medium",
                    source="nlp_description",
                    score=float(required_level),
                )
            )

    matches.sort(key=lambda item: (-item.score, item.skill_name))
    return matches[:max_matches]


def extract_competencies_from_benchmarks(
    stat_benchmark: float,
    tech_benchmark: float,
    gov_benchmark: float,
    beh_benchmark: float,
    unified_df: pd.DataFrame,
) -> list[ExtractedSkill]:
    """Derive competency signals from aggregate benchmark scores."""
    competency_keywords = {
        "stat": (
            stat_benchmark,
            (
                "statistical",
                "statistics",
                "data analysis",
                "mathematics",
                "research",
                "survey",
                "probability",
            ),
        ),
        "tech": (
            tech_benchmark,
            (
                "programming",
                "software",
                "database",
                "machine learning",
                "python",
                "computing",
            ),
        ),
        "gov": (
            gov_benchmark,
            (
                "governance",
                "policy",
                "regulation",
                "compliance",
                "ethics",
                "government",
                "public",
            ),
        ),
        "beh": (
            beh_benchmark,
            (
                "communication",
                "leadership",
                "team",
                "management",
                "writing",
                "listening",
                "critical thinking",
            ),
        ),
    }

    competencies = unified_df[unified_df["skill_type"] == "competency"]
    results: list[ExtractedSkill] = []

    for _, row in competencies.iterrows():
        name_lower = str(row["skill_name"]).lower()
        best_score = 0.0
        for _, (benchmark, keywords) in competency_keywords.items():
            if any(keyword in name_lower for keyword in keywords):
                best_score = max(best_score, _benchmark_to_level(benchmark, 0.7))

        if best_score > 0:
            results.append(
                ExtractedSkill(
                    skill_id=str(row["skill_id"]),
                    skill_name=str(row["skill_name"]),
                    skill_type="competency",
                    confidence="low",
                    source="benchmark_derived",
                    score=best_score,
                )
            )

    results.sort(key=lambda item: -item.score)
    return results[:15]
