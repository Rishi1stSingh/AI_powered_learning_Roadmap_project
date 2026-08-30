"""Local O*NET occupation → skill mapping from bundled CSV datasets.

Uses only files under data/ — no network calls, no API credentials.

Local sources inspected:
  - role_skill_benchmarks_cleaned.csv
      onet_code, role_title, role_description, key_software_tools, benchmarks
  - skill_taxonomy.csv
      skill_name, category  (O*NET tools + Essential Skill / Domain Knowledge entries)
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from statskill.utils.paths import RAW_TAXONOMY

ESSENTIAL_SKILL_CATEGORY = "Essential Skill"
DOMAIN_KNOWLEDGE_CATEGORY = "Domain Knowledge"


@dataclass(frozen=True)
class LocalONetSkill:
    skill_id: str
    skill_name: str
    skill_type: str
    required_level: int
    importance: int
    confidence: str
    origin: str


class LocalONetMapper:
    """Resolve occupation skills from local O*NET CSV exports."""

    def __init__(self, taxonomy_df: pd.DataFrame | None = None) -> None:
        if taxonomy_df is None:
            taxonomy_df = pd.read_csv(RAW_TAXONOMY)
        self.taxonomy_df = taxonomy_df
        self._essential_skills = self._load_category_skills(ESSENTIAL_SKILL_CATEGORY)
        self._domain_skills = self._load_category_skills(DOMAIN_KNOWLEDGE_CATEGORY)

    def _load_category_skills(self, category: str) -> list[str]:
        mask = self.taxonomy_df["category"] == category
        return [
            str(name).strip()
            for name in self.taxonomy_df.loc[mask, "skill_name"].dropna()
            if str(name).strip()
        ]

    def _lookup_unified(
        self,
        skill_name: str,
        unified_df: pd.DataFrame,
    ) -> pd.Series | None:
        matches = unified_df[unified_df["skill_name"].str.lower() == skill_name.lower()]
        if matches.empty:
            return None
        tools = matches[matches["skill_type"] == "tool"]
        if not tools.empty:
            return tools.iloc[0]
        return matches.iloc[0]

    def _benchmark_level(self, benchmark: float, scale: float = 0.85) -> int:
        return max(30, min(95, int(round(benchmark * scale))))

    def tools_from_role_row(
        self,
        role_row: pd.Series,
        unified_df: pd.DataFrame,
    ) -> list[LocalONetSkill]:
        """Map key_software_tools (local O*NET occupation technology data) to unified tools."""
        tools_text = role_row.get("key_software_tools", "")
        if not tools_text or pd.isna(tools_text):
            return []

        tech_benchmark = float(role_row.get("tech_benchmark", 50))
        required_level = self._benchmark_level(tech_benchmark, 0.9)
        importance = max(50, required_level - 5)

        results: list[LocalONetSkill] = []
        for part in str(tools_text).split(","):
            name = part.strip()
            if not name:
                continue
            row = self._lookup_unified(name, unified_df)
            if row is None:
                continue
            results.append(
                LocalONetSkill(
                    skill_id=str(row["skill_id"]),
                    skill_name=str(row["skill_name"]),
                    skill_type=str(row["skill_type"]),
                    required_level=required_level,
                    importance=importance,
                    confidence="high",
                    origin="key_software_tools",
                )
            )
        return results

    def taxonomy_skills_from_description(
        self,
        role_row: pd.Series,
        unified_df: pd.DataFrame,
        categories: tuple[str, ...] = (ESSENTIAL_SKILL_CATEGORY, DOMAIN_KNOWLEDGE_CATEGORY),
    ) -> list[LocalONetSkill]:
        """Match local O*NET taxonomy skill names mentioned in role_description."""
        description = role_row.get("role_description", "")
        if not description or pd.isna(description):
            return []

        text = str(description).lower()
        stat_benchmark = float(role_row.get("stat_benchmark", 50))
        required_level = self._benchmark_level(stat_benchmark, 0.8)

        candidate_names: list[str] = []
        if ESSENTIAL_SKILL_CATEGORY in categories:
            candidate_names.extend(self._essential_skills)
        if DOMAIN_KNOWLEDGE_CATEGORY in categories:
            candidate_names.extend(self._domain_skills)

        results: list[LocalONetSkill] = []
        for name in candidate_names:
            if name.lower() not in text:
                continue
            row = self._lookup_unified(name, unified_df)
            if row is None:
                continue
            results.append(
                LocalONetSkill(
                    skill_id=str(row["skill_id"]),
                    skill_name=str(row["skill_name"]),
                    skill_type=str(row["skill_type"]),
                    required_level=required_level,
                    importance=max(50, required_level - 5),
                    confidence="high",
                    origin="role_description_taxonomy",
                )
            )
        return results

    def skills_for_role(
        self,
        role_row: pd.Series,
        unified_df: pd.DataFrame,
    ) -> list[LocalONetSkill]:
        """All local O*NET-derived skills for one occupation row."""
        combined = self.tools_from_role_row(role_row, unified_df)
        combined.extend(self.taxonomy_skills_from_description(role_row, unified_df))
        return combined
