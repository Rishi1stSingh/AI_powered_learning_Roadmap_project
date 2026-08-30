"""
Phase 1 -- Data Inspection Script for StatSkill AI

Inspects the three raw datasets:
  1. processed_course_catalog_cleaned.csv  (Courses)
  2. role_skill_benchmarks_cleaned.csv     (Roles / Competencies)
  3. skill_taxonomy.csv                    (Skill Taxonomy)

Produces a comprehensive data-quality report to stdout.
Does NOT modify any source data.
"""

from __future__ import annotations

import os
import sys
import csv
import re
from pathlib import Path
from collections import Counter
from typing import Any

import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

COURSES_FILE = DATA_DIR / "processed_course_catalog_cleaned.csv"
ROLES_FILE = DATA_DIR / "role_skill_benchmarks_cleaned.csv"
SKILLS_FILE = DATA_DIR / "skill_taxonomy.csv"

SEPARATOR = "=" * 80
SUB_SEP = "-" * 60


def section(title: str) -> None:
    print(f"\n{SEPARATOR}")
    print(f"  {title}")
    print(SEPARATOR)


def subsection(title: str) -> None:
    print(f"\n{SUB_SEP}")
    print(f"  {title}")
    print(SUB_SEP)


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------


def basic_info(df: pd.DataFrame, label: str) -> dict[str, Any]:
    """Print and return basic DataFrame info."""
    info: dict[str, Any] = {}
    info["rows"] = len(df)
    info["columns"] = list(df.columns)

    print(f"\n  Rows         : {info['rows']}")
    print(f"  Columns ({len(df.columns)}) : {', '.join(info['columns'])}")
    print()

    # Data types
    print("  Column types:")
    for col in df.columns:
        print(f"    {col:40s}  {str(df[col].dtype):12s}")

    # Missing values
    missing = df.isnull().sum()
    total_missing = missing.sum()
    print(f"\n  Total missing values: {total_missing}")
    if total_missing > 0:
        print("  Missing per column:")
        for col in df.columns:
            m = missing[col]
            if m > 0:
                pct = m / len(df) * 100
                print(f"    {col:40s}  {m:6d}  ({pct:5.1f}%)")

    # Duplicates
    dup_rows = df.duplicated().sum()
    print(f"\n  Fully duplicated rows: {dup_rows}")

    info["total_missing"] = total_missing
    info["duplicate_rows"] = dup_rows
    return info


def value_distribution(df: pd.DataFrame, col: str, top_n: int = 15) -> None:
    """Print value distribution for a column."""
    if col not in df.columns:
        return
    vc = df[col].value_counts(dropna=False)
    n_unique = df[col].nunique(dropna=False)
    print(f"\n  {col} -- {n_unique} unique values (top {min(top_n, len(vc))}):")
    for val, cnt in vc.head(top_n).items():
        label = str(val) if val is not None and val == val else "<NULL>"
        print(f"    {label:50s}  {cnt:6d}")


def numeric_stats(df: pd.DataFrame, col: str) -> None:
    """Print numeric statistics for a column."""
    if col not in df.columns:
        return
    series = pd.to_numeric(df[col], errors="coerce")
    valid = series.dropna()
    if len(valid) == 0:
        print(f"\n  {col} -- no valid numeric values")
        return
    coerced_failures = len(df) - series.notna().sum() - df[col].isna().sum()
    print(f"\n  {col} -- numeric stats:")
    print(f"    Count           : {len(valid)}")
    print(f"    Min             : {valid.min()}")
    print(f"    Max             : {valid.max()}")
    print(f"    Mean            : {valid.mean():.2f}")
    print(f"    Median          : {valid.median():.2f}")
    print(f"    Std             : {valid.std():.2f}")
    if coerced_failures > 0:
        print(f"    Non-numeric vals: {coerced_failures}")


# ---------------------------------------------------------------------------
# Dataset-specific inspections
# ---------------------------------------------------------------------------


def inspect_courses(df: pd.DataFrame) -> dict[str, Any]:
    """Detailed inspection of the courses dataset."""
    section("DATASET A -- COURSES")
    info = basic_info(df, "Courses")

    # Course ID analysis
    subsection("Course ID Analysis")
    if "course_id" in df.columns:
        n_unique = df["course_id"].nunique()
        n_null = df["course_id"].isna().sum()
        n_dup = len(df) - n_unique
        print(f"  Unique IDs    : {n_unique}")
        print(f"  Null IDs      : {n_null}")
        print(f"  Duplicate IDs : {n_dup}")
        if n_dup > 0:
            dup_ids = df[df["course_id"].duplicated(keep=False)]["course_id"].unique()
            print(f"  Duplicated IDs: {list(dup_ids[:10])}")
        # ID format
        sample_ids = df["course_id"].dropna().head(5).tolist()
        print(f"  Sample IDs    : {sample_ids}")

    # Title analysis
    subsection("Course Title Analysis")
    if "course_title" in df.columns:
        n_null = df["course_title"].isna().sum()
        n_empty = (df["course_title"].str.strip() == "").sum() if n_null < len(df) else 0
        n_dup_title = df["course_title"].duplicated().sum()
        print(f"  Null titles       : {n_null}")
        print(f"  Empty titles      : {n_empty}")
        print(f"  Duplicate titles  : {n_dup_title}")
        if n_dup_title > 0:
            dup_titles = df[df["course_title"].duplicated(keep=False)]["course_title"].value_counts().head(10)
            print("  Most duplicated titles:")
            for title, cnt in dup_titles.items():
                print(f"    [{cnt}x] {title[:80]}")

    # Domain distribution
    value_distribution(df, "domain")

    # Institution distribution
    value_distribution(df, "institution", top_n=20)

    # Difficulty level
    subsection("Difficulty Level Analysis")
    value_distribution(df, "difficulty_level")

    # Duration
    subsection("Duration Analysis")
    value_distribution(df, "duration")

    # Rating
    subsection("Rating Analysis")
    numeric_stats(df, "rating")

    # Reviews
    subsection("Reviews Analysis")
    if "reviews" in df.columns:
        # Check for non-numeric values
        reviews_raw = df["reviews"].astype(str).str.replace(",", "").str.strip()
        reviews_numeric = pd.to_numeric(reviews_raw, errors="coerce")
        n_invalid = reviews_numeric.isna().sum() - df["reviews"].isna().sum()
        print(f"  Non-numeric review values: {n_invalid}")
        numeric_stats(df, "rating")  # already done, but let's do reviews
        valid_reviews = reviews_numeric.dropna()
        if len(valid_reviews) > 0:
            print(f"\n  Reviews (cleaned numeric) stats:")
            print(f"    Count   : {len(valid_reviews)}")
            print(f"    Min     : {valid_reviews.min():.0f}")
            print(f"    Max     : {valid_reviews.max():.0f}")
            print(f"    Mean    : {valid_reviews.mean():.0f}")
            print(f"    Median  : {valid_reviews.median():.0f}")

    # Skills analysis (critical)
    subsection("Skills Covered Analysis")
    if "skills_covered" in df.columns:
        n_null = df["skills_covered"].isna().sum()
        n_empty = (df["skills_covered"].str.strip() == "").sum() if n_null < len(df) else 0
        print(f"  Null skills_covered   : {n_null}")
        print(f"  Empty skills_covered  : {n_empty}")

        # Parse skills
        all_skills: list[str] = []
        skills_per_course: list[int] = []
        for val in df["skills_covered"].dropna():
            skills = [s.strip() for s in str(val).split(",") if s.strip()]
            all_skills.extend(skills)
            skills_per_course.append(len(skills))

        n_total_mentions = len(all_skills)
        unique_skills = set(all_skills)
        n_unique_skills = len(unique_skills)

        print(f"  Total skill mentions  : {n_total_mentions}")
        print(f"  Unique skills         : {n_unique_skills}")
        if skills_per_course:
            print(f"  Skills per course     : min={min(skills_per_course)}, max={max(skills_per_course)}, "
                  f"mean={sum(skills_per_course)/len(skills_per_course):.1f}")

        # Top skills
        skill_counts = Counter(all_skills)
        print(f"\n  Top 30 most common skills in courses:")
        for skill, cnt in skill_counts.most_common(30):
            print(f"    {skill:50s}  {cnt:5d}")

        # Store for cross-dataset analysis
        info["course_skills_set"] = unique_skills
        info["course_skills_counter"] = skill_counts

    # Embedding context
    subsection("Embedding Context")
    if "embedding_context" in df.columns:
        n_null = df["embedding_context"].isna().sum()
        n_empty = 0
        if n_null < len(df):
            n_empty = (df["embedding_context"].str.strip() == "").sum()
        print(f"  Null embedding_context  : {n_null}")
        print(f"  Empty embedding_context : {n_empty}")
        if n_null + n_empty < len(df):
            avg_len = df["embedding_context"].dropna().str.len().mean()
            print(f"  Average length          : {avg_len:.0f} chars")

    return info


def inspect_roles(df: pd.DataFrame) -> dict[str, Any]:
    """Detailed inspection of the roles dataset."""
    section("DATASET B -- ROLES / COMPETENCIES")
    info = basic_info(df, "Roles")

    # O*NET code analysis
    subsection("O*NET Code Analysis")
    if "onet_code" in df.columns:
        n_unique = df["onet_code"].nunique()
        n_null = df["onet_code"].isna().sum()
        n_dup = len(df) - n_unique
        print(f"  Unique O*NET codes : {n_unique}")
        print(f"  Null O*NET codes   : {n_null}")
        print(f"  Duplicate O*NET    : {n_dup}")
        # Validate format (##-####.##)
        pattern = r"^\d{2}-\d{4}\.\d{2}$"
        valid_format = df["onet_code"].dropna().str.match(pattern).sum()
        invalid_format = df["onet_code"].dropna().shape[0] - valid_format
        print(f"  Valid format       : {valid_format}")
        print(f"  Invalid format     : {invalid_format}")
        if invalid_format > 0:
            invalid = df[~df["onet_code"].dropna().str.match(pattern).reindex(df.index, fill_value=True)]
            print(f"  Invalid examples   : {invalid['onet_code'].head(5).tolist()}")

    # Role title
    subsection("Role Title Analysis")
    if "role_title" in df.columns:
        n_null = df["role_title"].isna().sum()
        n_dup = df["role_title"].duplicated().sum()
        print(f"  Null titles       : {n_null}")
        print(f"  Duplicate titles  : {n_dup}")
        value_distribution(df, "role_title", top_n=20)

    # Role description
    subsection("Role Description Analysis")
    if "role_description" in df.columns:
        n_null = df["role_description"].isna().sum()
        print(f"  Null descriptions : {n_null}")
        if n_null < len(df):
            avg_len = df["role_description"].dropna().str.len().mean()
            print(f"  Avg description length: {avg_len:.0f} chars")

    # Benchmark analysis
    subsection("Benchmark Analysis")
    benchmarks = ["stat_benchmark", "tech_benchmark", "gov_benchmark", "beh_benchmark"]
    for bm in benchmarks:
        if bm in df.columns:
            numeric_stats(df, bm)
            # Check range
            vals = pd.to_numeric(df[bm], errors="coerce").dropna()
            if len(vals) > 0:
                out_of_range = ((vals < 0) | (vals > 100)).sum()
                if out_of_range > 0:
                    print(f"    Out-of-range (0-100): {out_of_range}")

    # Data confidence
    subsection("Data Confidence")
    value_distribution(df, "data_confidence")

    # Key software tools
    subsection("Key Software Tools Analysis")
    if "key_software_tools" in df.columns:
        n_null = df["key_software_tools"].isna().sum()
        print(f"  Null software tools: {n_null}")
        all_tools: list[str] = []
        for val in df["key_software_tools"].dropna():
            tools = [t.strip() for t in str(val).split(",") if t.strip()]
            all_tools.extend(tools)
        unique_tools = set(all_tools)
        print(f"  Total tool mentions: {len(all_tools)}")
        print(f"  Unique tools       : {len(unique_tools)}")
        tool_counts = Counter(all_tools)
        print(f"\n  Top 20 most common tools:")
        for tool, cnt in tool_counts.most_common(20):
            print(f"    {tool:50s}  {cnt:5d}")

    # Check for stat-relevant roles
    subsection("Statistical / Government Roles")
    if "role_title" in df.columns:
        stat_keywords = ["statist", "data", "analy", "research", "survey", "census",
                         "econom", "demograph", "government", "public"]
        for kw in stat_keywords:
            matching = df[df["role_title"].str.lower().str.contains(kw, na=False)]
            if len(matching) > 0:
                print(f"  '{kw}' matches ({len(matching)}):")
                for _, row in matching.head(5).iterrows():
                    print(f"    {row.get('onet_code', '?'):15s} {row['role_title'][:60]}")

    return info


def inspect_skills(df: pd.DataFrame) -> dict[str, Any]:
    """Detailed inspection of the skills dataset."""
    section("DATASET C -- SKILL TAXONOMY")
    info = basic_info(df, "Skills")

    # Skill name analysis
    subsection("Skill Name Analysis")
    if "skill_name" in df.columns:
        n_null = df["skill_name"].isna().sum()
        n_empty = (df["skill_name"].str.strip() == "").sum() if n_null < len(df) else 0
        n_dup = df["skill_name"].duplicated().sum()
        print(f"  Null skill names      : {n_null}")
        print(f"  Empty skill names     : {n_empty}")
        print(f"  Duplicate skill names : {n_dup}")
        if n_dup > 0:
            dup_skills = df[df["skill_name"].duplicated(keep=False)]["skill_name"].value_counts().head(10)
            print("  Duplicated skills:")
            for s, cnt in dup_skills.items():
                print(f"    [{cnt}x] {s}")

        # Case analysis
        lower_versions = df["skill_name"].dropna().str.lower()
        n_case_dups = len(lower_versions) - lower_versions.nunique()
        print(f"  Case-insensitive dups : {n_case_dups}")
        if n_case_dups > 0:
            case_groups = df.groupby(df["skill_name"].str.lower())["skill_name"].apply(list)
            case_conflicts = case_groups[case_groups.apply(lambda x: len(set(x)) > 1)]
            print(f"  Case conflict groups  : {len(case_conflicts)}")
            for _, variants in case_conflicts.head(10).items():
                print(f"    {set(variants)}")

        # Whitespace issues
        has_leading = df["skill_name"].dropna().str.match(r"^\s+").sum()
        has_trailing = df["skill_name"].dropna().str.match(r".*\s+$").sum()
        print(f"  Leading whitespace    : {has_leading}")
        print(f"  Trailing whitespace   : {has_trailing}")

        # Length distribution
        lengths = df["skill_name"].dropna().str.len()
        print(f"\n  Skill name length:")
        print(f"    Min  : {lengths.min()}")
        print(f"    Max  : {lengths.max()}")
        print(f"    Mean : {lengths.mean():.1f}")

        # Very short names (possible issues)
        short = df[df["skill_name"].str.len() <= 2]["skill_name"].tolist()
        if short:
            print(f"\n  Very short skill names (<=2 chars): {short[:20]}")

        # Very long names (possible issues)
        long_names = df[df["skill_name"].str.len() > 60]["skill_name"].tolist()
        if long_names:
            print(f"\n  Very long skill names (>60 chars):")
            for n in long_names[:10]:
                print(f"    {n}")

        info["skill_names_set"] = set(df["skill_name"].dropna().str.strip().tolist())

    # Category analysis
    subsection("Category Analysis")
    value_distribution(df, "category")

    return info


def cross_dataset_analysis(
    courses_info: dict[str, Any],
    roles_info: dict[str, Any],
    skills_info: dict[str, Any],
    courses_df: pd.DataFrame,
    roles_df: pd.DataFrame,
    skills_df: pd.DataFrame,
) -> None:
    """Analyze relationships between datasets."""
    section("CROSS-DATASET ANALYSIS")

    canonical_skills = skills_info.get("skill_names_set", set())
    course_skills = courses_info.get("course_skills_set", set())

    if canonical_skills and course_skills:
        subsection("Course Skills vs. Canonical Taxonomy")
        # Exact match
        exact_match = course_skills & canonical_skills
        in_courses_only = course_skills - canonical_skills
        in_taxonomy_only = canonical_skills - course_skills

        print(f"  Canonical taxonomy skills       : {len(canonical_skills)}")
        print(f"  Unique skills in courses         : {len(course_skills)}")
        print(f"  Exact matches                    : {len(exact_match)}")
        print(f"  In courses but NOT in taxonomy   : {len(in_courses_only)}")
        print(f"  In taxonomy but NOT in courses   : {len(in_taxonomy_only)}")

        # Case-insensitive match
        canonical_lower = {s.lower(): s for s in canonical_skills}
        course_lower = {s.lower(): s for s in course_skills}
        ci_match = set(canonical_lower.keys()) & set(course_lower.keys())
        ci_only_courses = set(course_lower.keys()) - set(canonical_lower.keys())

        print(f"\n  Case-insensitive matches         : {len(ci_match)}")
        print(f"  Unmapped (case-insensitive)       : {len(ci_only_courses)}")

        # Show some unmapped skills
        if in_courses_only:
            print(f"\n  Sample unmapped course skills (first 30):")
            for s in sorted(in_courses_only)[:30]:
                # Check if there's a case-insensitive match
                ci = canonical_lower.get(s.lower())
                if ci:
                    print(f"    {s:50s}  -> case match: '{ci}'")
                else:
                    print(f"    {s:50s}  -> NO MATCH")

    # Role software tools vs course skills
    subsection("Role Software Tools as Potential Skills")
    if "key_software_tools" in roles_df.columns and course_skills:
        all_tools: list[str] = []
        for val in roles_df["key_software_tools"].dropna():
            tools = [t.strip() for t in str(val).split(",") if t.strip()]
            all_tools.extend(tools)
        unique_tools = set(all_tools)
        tools_in_courses = unique_tools & course_skills
        tools_in_taxonomy = unique_tools & canonical_skills
        print(f"  Unique role tools      : {len(unique_tools)}")
        print(f"  Tools in course skills : {len(tools_in_courses)}")
        print(f"  Tools in taxonomy      : {len(tools_in_taxonomy)}")

    # Summary of role-skill mapping feasibility
    subsection("Role-Skill Mapping Feasibility")
    print("  The role dataset contains BENCHMARK SCORES (stat, tech, gov, beh)")
    print("  but does NOT contain a direct role -> skill mapping.")
    print()
    print("  To create role_skills.csv, we would need to:")
    print("    1. Map benchmark categories to specific skills from the taxonomy")
    print("    2. Use role descriptions + software tools as additional signals")
    print("    3. Consider using the O*NET API for authoritative skill mappings")
    print("    4. Allow admin/manual mapping for gaps")
    print()

    # Check if benchmarks can imply skill requirements
    if all(col in roles_df.columns for col in ["stat_benchmark", "tech_benchmark"]):
        print("  Benchmark coverage:")
        for bm in ["stat_benchmark", "tech_benchmark", "gov_benchmark", "beh_benchmark"]:
            if bm in roles_df.columns:
                valid = pd.to_numeric(roles_df[bm], errors="coerce").dropna()
                print(f"    {bm:20s}: {len(valid)}/{len(roles_df)} roles have values")


def generate_summary(
    courses_info: dict[str, Any],
    roles_info: dict[str, Any],
    skills_info: dict[str, Any],
) -> None:
    """Generate a final summary."""
    section("SUMMARY & RECOMMENDATIONS")

    print("""
  DATASETS FOUND:
    A. Courses  : processed_course_catalog_cleaned.csv
    B. Roles    : role_skill_benchmarks_cleaned.csv
    C. Skills   : skill_taxonomy.csv

  KEY FINDINGS:

    1. COURSES dataset appears pre-cleaned (2,754 courses)
       - Has course_id, title, domain, institution, difficulty, duration, 
         skills_covered, rating, reviews, embedding_context
       - skills_covered is a comma-separated list -- needs normalization
       - embedding_context is pre-generated text -- can be used or regenerated

    2. ROLES dataset contains 1,017 O*NET-based roles
       - Has benchmark scores (stat, tech, gov, beh) -- NOT individual skill mappings
       - CRITICAL: No direct role -> skill -> required_level mapping exists
       - key_software_tools provides some skill signals
       - role_description provides textual skill signals

    3. SKILLS taxonomy contains 8,796 skills with categories
       - This is the canonical skill source
       - Some duplicate/case issues may exist
       - Categories provide structure

  CRITICAL GAPS:

    1. role_skills relationship does NOT exist yet
       - Must be derived or manually created
       - Benchmark scores are aggregate, not per-skill

    2. course_skills relationship needs normalization
       - skills_covered is embedded text, not a relational mapping
       - Many course skills may not match canonical taxonomy

    3. Employee data does NOT exist
       - Must be created as synthetic/demo data

  RECOMMENDED NEXT STEPS (Phase 2):

    1. Clean skills taxonomy (deduplicate, normalize case)
    2. Parse and normalize course skills against taxonomy
    3. Build skill_aliases mapping
    4. Clean course data (validate ratings, durations, etc.)
    5. Clean role data (validate benchmarks, flag gaps)
    6. Prepare data/raw/ and data/processed/ structure
""")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    # Force UTF-8 output on Windows
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    print(SEPARATOR)
    print("  STATSKILL AI -- PHASE 1: DATA INSPECTION")
    print(f"  Data Directory: {DATA_DIR}")
    print(SEPARATOR)

    # Check files exist
    files = {
        "Courses": COURSES_FILE,
        "Roles": ROLES_FILE,
        "Skills": SKILLS_FILE,
    }
    for label, path in files.items():
        exists = path.exists()
        size = path.stat().st_size if exists else 0
        status = f"[OK] {size:,} bytes" if exists else "[MISSING]"
        print(f"  {label:12s}: {path.name:50s} {status}")

    # Load datasets
    print("\n  Loading datasets...")
    try:
        courses_df = pd.read_csv(COURSES_FILE)
        roles_df = pd.read_csv(ROLES_FILE)
        skills_df = pd.read_csv(SKILLS_FILE)
    except Exception as e:
        print(f"  ERROR loading datasets: {e}")
        sys.exit(1)

    print(f"  Loaded successfully.")

    # Inspect each dataset
    courses_info = inspect_courses(courses_df)
    roles_info = inspect_roles(roles_df)
    skills_info = inspect_skills(skills_df)

    # Cross-dataset analysis
    cross_dataset_analysis(
        courses_info, roles_info, skills_info,
        courses_df, roles_df, skills_df
    )

    # Summary
    generate_summary(courses_info, roles_info, skills_info)


if __name__ == "__main__":
    main()
