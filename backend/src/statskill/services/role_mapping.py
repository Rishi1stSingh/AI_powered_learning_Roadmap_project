"""Combined role → skill mapping: local O*NET data + NLP + manual review."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import yaml

from statskill.ai.nlp_extract import (
    ExtractedSkill,
    extract_competencies_from_benchmarks,
    extract_from_description,
    extract_from_tools,
)
from statskill.onet_local import LocalONetMapper
from statskill.utils.paths import MANUAL_ROLE_SKILLS_CONFIG, MVP_ROLES_CONFIG


@dataclass
class RoleSkillRecord:
    onet_code: str
    role_title: str
    skill_id: str
    skill_name: str
    skill_type: str
    required_level: int
    importance: int
    source: str
    confidence: str
    is_showcase: bool


SOURCE_PRIORITY = {
    "manual": 100,
    "local_onet": 90,
    "nlp_tools": 70,
    "nlp_description": 60,
    "benchmark_derived": 40,
}


def load_mvp_roles() -> tuple[list[str], set[str]]:
    with MVP_ROLES_CONFIG.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    mvp_codes = list(config["mvp_onet_codes"])
    showcase_codes = set(config["showcase_onet_codes"])
    return mvp_codes, showcase_codes


def load_manual_mappings() -> dict[str, dict]:
    with MANUAL_ROLE_SKILLS_CONFIG.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _lookup_unified_skill(
    skill_name: str,
    skill_type: str,
    unified_df: pd.DataFrame,
) -> pd.Series | None:
    matches = unified_df[
        (unified_df["skill_name"].str.lower() == skill_name.lower())
        & (unified_df["skill_type"] == skill_type)
    ]
    if matches.empty:
        matches = unified_df[unified_df["skill_name"].str.lower() == skill_name.lower()]
    if matches.empty:
        return None
    return matches.iloc[0]


def _merge_skill_records(records: list[RoleSkillRecord]) -> list[RoleSkillRecord]:
    merged: dict[tuple[str, str], RoleSkillRecord] = {}
    for record in records:
        key = (record.skill_id or record.skill_name.lower(), record.skill_type)
        existing = merged.get(key)
        if existing is None or SOURCE_PRIORITY.get(record.source, 0) > SOURCE_PRIORITY.get(
            existing.source, 0
        ):
            merged[key] = record
        elif existing and record.source == existing.source:
            existing.required_level = max(existing.required_level, record.required_level)
            existing.importance = max(existing.importance, record.importance)
    return list(merged.values())


def _records_from_manual(
    onet_code: str,
    role_title: str,
    unified_df: pd.DataFrame,
    manual_config: dict,
    is_showcase: bool,
) -> list[RoleSkillRecord]:
    role_config = manual_config.get(onet_code)
    if not role_config:
        return []

    records: list[RoleSkillRecord] = []
    for item in role_config.get("skills", []):
        skill_name = str(item["skill_name"])
        skill_type = str(item["skill_type"])
        row = _lookup_unified_skill(skill_name, skill_type, unified_df)
        if row is None:
            continue
        records.append(
            RoleSkillRecord(
                onet_code=onet_code,
                role_title=role_title,
                skill_id=str(row["skill_id"]),
                skill_name=str(row["skill_name"]),
                skill_type=str(row["skill_type"]),
                required_level=int(item.get("required_level", 70)),
                importance=int(item.get("importance", 75)),
                source="manual",
                confidence="high",
                is_showcase=is_showcase,
            )
        )
    return records


def _records_from_local_onet(
    onet_code: str,
    role_title: str,
    role_row: pd.Series,
    unified_df: pd.DataFrame,
    local_mapper: LocalONetMapper,
    is_showcase: bool,
) -> list[RoleSkillRecord]:
    """Structured occupation skills from local O*NET CSV files."""
    records: list[RoleSkillRecord] = []
    for item in local_mapper.skills_for_role(role_row, unified_df):
        records.append(
            RoleSkillRecord(
                onet_code=onet_code,
                role_title=role_title,
                skill_id=item.skill_id,
                skill_name=item.skill_name,
                skill_type=item.skill_type,
                required_level=item.required_level,
                importance=item.importance,
                source="local_onet",
                confidence=item.confidence,
                is_showcase=is_showcase,
            )
        )
    return records


def _records_from_extracted(
    onet_code: str,
    role_title: str,
    extracted: list[ExtractedSkill],
    is_showcase: bool,
) -> list[RoleSkillRecord]:
    return [
        RoleSkillRecord(
            onet_code=onet_code,
            role_title=role_title,
            skill_id=item.skill_id,
            skill_name=item.skill_name,
            skill_type=item.skill_type,
            required_level=int(item.score),
            importance=max(50, int(item.score) - 5),
            source=item.source,
            confidence=item.confidence,
            is_showcase=is_showcase,
        )
        for item in extracted
    ]


def build_role_skills(
    roles_df: pd.DataFrame,
    unified_df: pd.DataFrame,
    taxonomy_df: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build role_skills.csv for MVP roles using the offline mapping strategy."""
    mvp_codes, showcase_codes = load_mvp_roles()
    manual_config = load_manual_mappings()
    local_mapper = LocalONetMapper(taxonomy_df)

    mvp_roles = roles_df[roles_df["onet_code"].isin(mvp_codes)].copy()
    mvp_roles["priority_rank"] = mvp_roles["onet_code"].apply(
        lambda code: mvp_codes.index(code)
    )
    mvp_roles = mvp_roles.sort_values("priority_rank")

    all_records: list[RoleSkillRecord] = []
    source_rows: list[dict[str, str | int | bool]] = []

    for _, role in mvp_roles.iterrows():
        onet_code = str(role["onet_code"])
        role_title = str(role["role_title"])
        is_showcase = onet_code in showcase_codes

        role_records: list[RoleSkillRecord] = []

        role_records.extend(
            _records_from_manual(onet_code, role_title, unified_df, manual_config, is_showcase)
        )

        role_records.extend(
            _records_from_local_onet(
                onet_code, role_title, role, unified_df, local_mapper, is_showcase
            )
        )

        extracted: list[ExtractedSkill] = []
        extracted.extend(
            extract_from_tools(
                role.get("key_software_tools", ""),
                unified_df,
                float(role.get("tech_benchmark", 50)),
            )
        )
        extracted.extend(
            extract_from_description(
                role.get("role_description", ""),
                unified_df,
                float(role.get("stat_benchmark", 50)),
            )
        )
        role_records.extend(
            _records_from_extracted(onet_code, role_title, extracted, is_showcase)
        )

        merged = _merge_skill_records(role_records)
        all_records.extend(merged)

        source_counts: dict[str, int] = {}
        for record in merged:
            source_counts[record.source] = source_counts.get(record.source, 0) + 1
        source_rows.append(
            {
                "onet_code": onet_code,
                "role_title": role_title,
                "is_showcase": is_showcase,
                "total_skills": len(merged),
                "manual_count": source_counts.get("manual", 0),
                "local_onet_count": source_counts.get("local_onet", 0),
                "nlp_tools_count": source_counts.get("nlp_tools", 0),
                "nlp_description_count": source_counts.get("nlp_description", 0),
                "benchmark_derived_count": source_counts.get("benchmark_derived", 0),
            }
        )

    role_skills_df = pd.DataFrame(
        [
            {
                "onet_code": record.onet_code,
                "role_title": record.role_title,
                "skill_id": record.skill_id,
                "skill_name": record.skill_name,
                "skill_type": record.skill_type,
                "required_level": record.required_level,
                "importance": record.importance,
                "source": record.source,
                "confidence": record.confidence,
                "is_showcase_role": record.is_showcase,
            }
            for record in all_records
        ]
    )

    mvp_roles_df = mvp_roles[
        [
            "onet_code",
            "role_title",
            "role_description",
            "stat_benchmark",
            "tech_benchmark",
            "gov_benchmark",
            "beh_benchmark",
            "data_confidence",
        ]
    ].copy()
    mvp_roles_df["is_showcase_role"] = mvp_roles_df["onet_code"].isin(showcase_codes)
    mvp_roles_df["priority_rank"] = mvp_roles_df["onet_code"].apply(
        lambda code: mvp_codes.index(code) + 1
    )

    sources_df = pd.DataFrame(source_rows)
    return role_skills_df, mvp_roles_df, sources_df
