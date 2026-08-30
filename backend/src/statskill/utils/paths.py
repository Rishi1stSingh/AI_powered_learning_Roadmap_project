from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
CONFIG_DIR = PROJECT_ROOT / "config"

RAW_COURSES = RAW_DIR / "processed_course_catalog_cleaned.csv"
RAW_ROLES = RAW_DIR / "role_skill_benchmarks_cleaned.csv"
RAW_TAXONOMY = RAW_DIR / "skill_taxonomy.csv"

PROCESSED_UNIFIED_TAXONOMY = PROCESSED_DIR / "unified_taxonomy.csv"
PROCESSED_SKILL_ALIASES = PROCESSED_DIR / "skill_aliases.csv"
PROCESSED_COURSE_SKILLS = PROCESSED_DIR / "course_skills.csv"
PROCESSED_ROLE_SKILLS = PROCESSED_DIR / "role_skills.csv"
PROCESSED_MVP_ROLES = PROCESSED_DIR / "mvp_roles.csv"
PROCESSED_ROLE_SKILL_SOURCES = PROCESSED_DIR / "role_skill_sources.csv"

MVP_ROLES_CONFIG = CONFIG_DIR / "mvp_roles.yaml"
MANUAL_ROLE_SKILLS_CONFIG = CONFIG_DIR / "manual_role_skills.yaml"
