"""Dual taxonomy builder: O*NET tools + course competencies in one unified schema."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

import pandas as pd

from statskill.utils.paths import RAW_COURSES, RAW_TAXONOMY


TOOL = "tool"
COMPETENCY = "competency"


@dataclass(frozen=True)
class UnifiedSkill:
    skill_id: str
    skill_name: str
    skill_type: str
    category: str
    source: str


def _make_skill_id(skill_name: str, skill_type: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", skill_name.strip().lower()).strip("-")
    prefix = "t" if skill_type == TOOL else "c"
    digest = hashlib.sha1(f"{skill_type}:{skill_name}".encode()).hexdigest()[:8]
    return f"{prefix}_{slug[:48]}_{digest}"


def _normalize(name: str) -> str:
    return " ".join(name.strip().split())


def _collect_course_skills(courses_df: pd.DataFrame) -> set[str]:
    skills: set[str] = set()
    for value in courses_df["skills_covered"].dropna():
        for part in str(value).split(","):
            cleaned = _normalize(part)
            if cleaned:
                skills.add(cleaned)
    return skills


def build_unified_taxonomy(
    taxonomy_df: pd.DataFrame | None = None,
    courses_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Merge O*NET tool taxonomy with course competencies (dual taxonomy)."""
    if taxonomy_df is None:
        taxonomy_df = pd.read_csv(RAW_TAXONOMY)
    if courses_df is None:
        courses_df = pd.read_csv(RAW_COURSES)

    tool_names_lower = {
        _normalize(name).lower()
        for name in taxonomy_df["skill_name"].dropna()
    }
    course_skills = _collect_course_skills(courses_df)

    rows: list[dict[str, str]] = []

    for _, row in taxonomy_df.iterrows():
        name = _normalize(str(row["skill_name"]))
        category = str(row.get("category", "Uncategorized")).strip()
        rows.append(
            {
                "skill_id": _make_skill_id(name, TOOL),
                "skill_name": name,
                "skill_type": TOOL,
                "category": category,
                "source": "onet_taxonomy",
            }
        )

    for skill in sorted(course_skills):
        if skill.lower() in tool_names_lower:
            continue
        rows.append(
            {
                "skill_id": _make_skill_id(skill, COMPETENCY),
                "skill_name": skill,
                "skill_type": COMPETENCY,
                "category": "Course Competency",
                "source": "course_catalog",
            }
        )

    df = pd.DataFrame(rows)
    df = df.drop_duplicates(subset=["skill_name", "skill_type"], keep="first")
    return df.sort_values(["skill_type", "skill_name"]).reset_index(drop=True)


def build_skill_aliases(
    unified_df: pd.DataFrame,
    courses_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Map raw course skill strings to canonical unified taxonomy entries."""
    if courses_df is None:
        courses_df = pd.read_csv(RAW_COURSES)

    by_name_lower: dict[str, list[dict[str, str]]] = {}
    for _, row in unified_df.iterrows():
        key = str(row["skill_name"]).lower()
        by_name_lower.setdefault(key, []).append(row.to_dict())

    aliases: list[dict[str, str]] = []
    seen_course_skills: set[str] = set()

    for value in courses_df["skills_covered"].dropna():
        for part in str(value).split(","):
            raw = part.strip()
            if not raw or raw in seen_course_skills:
                continue
            seen_course_skills.add(raw)
            normalized = _normalize(raw)
            matches = by_name_lower.get(normalized.lower(), [])

            if len(matches) == 1:
                match = matches[0]
                aliases.append(
                    {
                        "alias": raw,
                        "canonical_skill_id": match["skill_id"],
                        "canonical_skill_name": match["skill_name"],
                        "skill_type": match["skill_type"],
                        "match_method": "exact",
                    }
                )
            elif len(matches) > 1:
                tool_match = next((m for m in matches if m["skill_type"] == TOOL), matches[0])
                aliases.append(
                    {
                        "alias": raw,
                        "canonical_skill_id": tool_match["skill_id"],
                        "canonical_skill_name": tool_match["skill_name"],
                        "skill_type": tool_match["skill_type"],
                        "match_method": "exact_dual",
                    }
                )
            else:
                comp = unified_df[
                    (unified_df["skill_name"] == normalized)
                    & (unified_df["skill_type"] == COMPETENCY)
                ]
                if not comp.empty:
                    row = comp.iloc[0]
                    aliases.append(
                        {
                            "alias": raw,
                            "canonical_skill_id": row["skill_id"],
                            "canonical_skill_name": row["skill_name"],
                            "skill_type": row["skill_type"],
                            "match_method": "competency_canonical",
                        }
                    )
                else:
                    aliases.append(
                        {
                            "alias": raw,
                            "canonical_skill_id": "",
                            "canonical_skill_name": normalized,
                            "skill_type": COMPETENCY,
                            "match_method": "unmapped",
                        }
                    )

    return pd.DataFrame(aliases).sort_values("alias").reset_index(drop=True)


def build_course_skills(
    courses_df: pd.DataFrame,
    aliases_df: pd.DataFrame,
) -> pd.DataFrame:
    """Normalize course → skill relationships."""
    alias_lookup = {
        str(row["alias"]): row
        for _, row in aliases_df.iterrows()
    }

    rows: list[dict[str, str]] = []
    for _, course in courses_df.iterrows():
        course_id = str(course["course_id"])
        for part in str(course.get("skills_covered", "")).split(","):
            raw = part.strip()
            if not raw:
                continue
            alias_row = alias_lookup.get(raw)
            if alias_row is None:
                continue
            rows.append(
                {
                    "course_id": course_id,
                    "course_title": str(course.get("course_title", "")),
                    "raw_skill": raw,
                    "skill_id": str(alias_row["canonical_skill_id"]),
                    "skill_name": str(alias_row["canonical_skill_name"]),
                    "skill_type": str(alias_row["skill_type"]),
                    "mapped": str(alias_row["match_method"]) != "unmapped",
                }
            )

    return pd.DataFrame(rows)
