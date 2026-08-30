"""Offline Phase 3: profiles, skill gaps, and course recommendations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from statskill.utils.paths import PROCESSED_COURSE_SKILLS, PROCESSED_ROLE_SKILLS, PROCESSED_MVP_ROLES


@dataclass(frozen=True)
class EmployeeProfile:
    name: str
    skills: dict[str, int]


def load_profile(name: str, skills: dict[str, int]) -> EmployeeProfile:
    return EmployeeProfile(name, {str(k).strip().lower(): int(v) for k, v in skills.items()})


def analyze_gaps(profile: EmployeeProfile, onet_code: str, role_skills: pd.DataFrame | None = None) -> pd.DataFrame:
    """Return role requirements joined with employee levels and gap severity."""
    required = role_skills if role_skills is not None else pd.read_csv(PROCESSED_ROLE_SKILLS)
    if "onet_code" not in required.columns and "role_code" in required.columns:
        required = required.rename(columns={"role_code": "onet_code"})
    required = required[required["onet_code"].astype(str) == str(onet_code)].copy()
    required["employee_level"] = required["skill_name"].map(
        lambda n: profile.skills.get(str(n).lower(), 0)
    )
    required["gap"] = (required["required_level"] - required["employee_level"]).clip(lower=0)
    required["status"] = required["gap"].map(lambda x: "gap" if x > 0 else "met")
    return required.sort_values(["gap", "importance"], ascending=[False, False]).reset_index(drop=True)


def recommend_courses(gaps: pd.DataFrame, course_skills: pd.DataFrame | None = None, limit: int = 10) -> pd.DataFrame:
    """Rank courses by weighted coverage of the employee's highest-priority gaps."""
    links = course_skills if course_skills is not None else pd.read_csv(PROCESSED_COURSE_SKILLS)
    missing = gaps[gaps["gap"] > 0][["skill_id", "skill_name", "gap", "importance"]].copy()
    missing = missing.rename(columns={"skill_name": "gap_skill_name"})
    if missing.empty:
        return pd.DataFrame(columns=["course_id", "course_title", "coverage", "score", "skills"])
    joined = links.merge(missing, on="skill_id", how="inner")
    ranked = joined.groupby(["course_id", "course_title"], as_index=False).agg(
        coverage=("skill_id", "nunique"), score=("gap", lambda s: float(s.sum())),
        skills=("gap_skill_name", lambda s: ", ".join(sorted(set(s))))
    )
    return ranked.sort_values(["score", "coverage"], ascending=[False, False]).head(limit).reset_index(drop=True)


def role_name(onet_code: str, roles: pd.DataFrame | None = None) -> str:
    roles = roles if roles is not None else pd.read_csv(PROCESSED_MVP_ROLES)
    hit = roles[roles["onet_code"].astype(str) == str(onet_code)]
    return str(hit.iloc[0]["role_title"]) if not hit.empty else str(onet_code)
