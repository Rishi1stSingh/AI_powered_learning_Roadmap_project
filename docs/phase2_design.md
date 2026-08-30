# StatSkill AI — Phase 2 Design

> **Status**: Implemented (offline MVP)  
> **Build script**: [`scripts/build_phase2.py`](../scripts/build_phase2.py)

---

## Approved decisions

### Q1 — Dual taxonomy ✅

The O\*NET tool taxonomy (8,795 entries) and course competencies (1,753 unique skills, ~95% non-overlapping) are merged into **`unified_taxonomy.csv`** without collapsing them into one namespace.

| Field | Description |
|-------|-------------|
| `skill_id` | Stable ID (`t_*` for tools, `c_*` for competencies) |
| `skill_name` | Canonical display name |
| `skill_type` | `tool` or `competency` |
| `category` | O\*NET category or `Course Competency` |
| `source` | `onet_taxonomy` or `course_catalog` |

**Result**: 10,462 unified skills (8,795 tools + 1,667 competencies). The 86 skills that exist in both systems are stored once as tools; course aliases resolve to the tool entry.

### Q2 — Combined role → skill mapping (offline) ✅

`role_skills.csv` is built entirely from local files — **no O\*NET API calls, no credentials, no `.env` required**.

| Priority | Source | Module | Description |
|----------|--------|--------|-------------|
| 1 | `manual` | `config/manual_role_skills.yaml` | Curated mappings for showcase statistician roles |
| 2 | `local_onet` | `statskill/onet_local.py` | Structured data from bundled O\*NET CSVs |
| 3 | `nlp_tools` | `statskill/nlp_extract.py` | Tool matching from `key_software_tools` |
| 4 | `nlp_description` | `statskill/nlp_extract.py` | Skill names mentioned in role descriptions |
| 5 | `benchmark_derived` | `statskill/nlp_extract.py` | Competencies inferred from stat/tech/gov/beh benchmarks |

#### Local O\*NET data sources (inspected)

| File | Columns used | Purpose |
|------|--------------|---------|
| `role_skill_benchmarks_cleaned.csv` | `onet_code`, `role_title`, `role_description`, `key_software_tools`, `stat_benchmark`, `tech_benchmark`, `gov_benchmark`, `beh_benchmark` | Occupation-level O\*NET data: technology tools and text/benchmark signals |
| `skill_taxonomy.csv` | `skill_name`, `category` | Canonical O\*NET tool taxonomy plus `Essential Skill` (10) and `Domain Knowledge` (32) entries |

The `local_onet` layer maps:
- **`key_software_tools`** → unified tool entries (same field that covers 99.4% of the O\*NET tool taxonomy)
- **`role_description`** → Essential Skill / Domain Knowledge taxonomy entries when mentioned

The MVP uses only the local O\*NET CSV data; no live API client is included or required.

### Q3 — 18 MVP roles ✅

Configured in [`config/mvp_roles.yaml`](../config/mvp_roles.yaml):

- **3 showcase roles** (priority demo): Statisticians, Biostatisticians, Statistical Assistants
- **15 additional roles**: Data Scientists, Operations Research Analysts, Economists, Survey Researchers, Budget Analysts, Management Analysts, Market Research Analysts, Database Administrators, Business Intelligence Analysts, Computer & Information Research Scientists, Government Property Inspectors, Eligibility Interviewers, Social Science Research Assistants, Database Architects, Environmental Economists

---

## Build output summary

Run `python scripts/build_phase2.py` — works with zero environment variables.

| Metric | Value |
|--------|-------|
| Unified taxonomy skills | 10,462 |
| Tools | 8,795 |
| Competencies | 1,667 |
| Course skill aliases mapped | 1,753 / 1,753 (100%) |
| Course → skill links | 38,084 |
| MVP roles | 18 |
| Role → skill rows | varies by build |
| Showcase roles | 3 |

---

## Schema reference

### `unified_taxonomy.csv`

Dual-category canonical skill list used by all downstream matching.

### `skill_aliases.csv`

Maps each unique course skill string to a canonical taxonomy entry.

| Field | Description |
|-------|-------------|
| `alias` | Raw skill string from course catalog |
| `canonical_skill_id` | ID in unified taxonomy |
| `match_method` | `exact`, `exact_dual`, `competency_canonical` |

### `course_skills.csv`

Relational course → skill mapping (replaces comma-separated `skills_covered`).

### `role_skills.csv`

| Field | Description |
|-------|-------------|
| `onet_code` | O\*NET-SOC code |
| `skill_id` / `skill_name` / `skill_type` | Required skill from unified taxonomy |
| `required_level` | Estimated proficiency (30–95) |
| `importance` | Relative importance (50–95) |
| `source` | `manual`, `local_onet`, `nlp_tools`, `nlp_description`, or `benchmark_derived` |
| `confidence` | `high`, `medium`, or `low` |
| `is_showcase_role` | True for 3 statistician roles |

### `role_skill_sources.csv`

Per-role counts by mapping source — useful for QA.

| Field | Description |
|-------|-------------|
| `local_onet_count` | Skills from bundled O\*NET CSV data |
| `manual_count` | Curated showcase overrides |
| `nlp_tools_count` / `nlp_description_count` / `benchmark_derived_count` | NLP and benchmark layers |

---

## Next steps (Phase 3)

Phase 3 implementation begins with an offline demo in `scripts/run_phase3_demo.py`:

1. Synthetic employee profiles
2. Gap analysis engine (`statskill.phase3.analyze_gaps`)
3. Course recommendation ranking (`statskill.phase3.recommend_courses`)
4. API / UI layer remains future work
