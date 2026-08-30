"""Phase 2 data pipeline orchestrator."""

from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd

from statskill.utils.paths import (
    PROCESSED_COURSE_SKILLS,
    PROCESSED_DIR,
    PROCESSED_MVP_ROLES,
    PROCESSED_ROLE_SKILLS,
    PROCESSED_ROLE_SKILL_SOURCES,
    PROCESSED_SKILL_ALIASES,
    PROCESSED_UNIFIED_TAXONOMY,
    RAW_COURSES,
    RAW_DIR,
    RAW_ROLES,
    RAW_TAXONOMY,
)
from statskill.services.role_mapping import build_role_skills
from statskill.services.taxonomy import build_course_skills, build_skill_aliases, build_unified_taxonomy


def ensure_raw_data() -> None:
    """Copy source CSVs into data/raw/ without modifying originals."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    data_root = Path(__file__).resolve().parents[3] / "data"
    source_map = {
        RAW_COURSES: data_root / "processed_course_catalog_cleaned.csv",
        RAW_ROLES: data_root / "role_skill_benchmarks_cleaned.csv",
        RAW_TAXONOMY: data_root / "skill_taxonomy.csv",
    }

    for target, source in source_map.items():
        if not source.exists():
            raise FileNotFoundError(f"Missing source dataset: {source}")
        if not target.exists() or target.stat().st_mtime < source.stat().st_mtime:
            shutil.copy2(source, target)


def run_build() -> dict[str, int | str | bool]:
    ensure_raw_data()

    courses_df = pd.read_csv(RAW_COURSES)
    roles_df = pd.read_csv(RAW_ROLES)
    taxonomy_df = pd.read_csv(RAW_TAXONOMY)

    unified_df = build_unified_taxonomy(taxonomy_df, courses_df)
    aliases_df = build_skill_aliases(unified_df, courses_df)
    course_skills_df = build_course_skills(courses_df, aliases_df)
    role_skills_df, mvp_roles_df, sources_df = build_role_skills(
        roles_df, unified_df, taxonomy_df
    )

    unified_df.to_csv(PROCESSED_UNIFIED_TAXONOMY, index=False)
    aliases_df.to_csv(PROCESSED_SKILL_ALIASES, index=False)
    course_skills_df.to_csv(PROCESSED_COURSE_SKILLS, index=False)
    role_skills_df.to_csv(PROCESSED_ROLE_SKILLS, index=False)
    mvp_roles_df.to_csv(PROCESSED_MVP_ROLES, index=False)
    sources_df.to_csv(PROCESSED_ROLE_SKILL_SOURCES, index=False)

    tool_count = int((unified_df["skill_type"] == "tool").sum())
    competency_count = int((unified_df["skill_type"] == "competency").sum())
    mapped_aliases = int((aliases_df["match_method"] != "unmapped").sum())

    return {
        "tools_in_taxonomy": tool_count,
        "competencies_in_taxonomy": competency_count,
        "total_unified_skills": len(unified_df),
        "mapped_aliases": mapped_aliases,
        "total_aliases": len(aliases_df),
        "course_skill_links": len(course_skills_df),
        "mvp_roles": len(mvp_roles_df),
        "role_skill_rows": len(role_skills_df),
        "showcase_roles": int(mvp_roles_df["is_showcase_role"].sum()),
    }
