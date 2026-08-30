# StatSkill AI — Phase 1: Data Audit Report

> **Generated**: 2026-08-29  
> **Script**: [`scripts/inspect_data.py`](file:///c:/Users/singh/OneDrive/Desktop/sih_project/scripts/inspect_data.py)  
> **Status**: Phase 1 Complete — Awaiting approval for Phase 2

---

## 1. Project Structure

```
sih_project/
├── .git/
├── .gitignore
├── README.md              (empty)
├── backend/               (backend package and migrations)
├── frontend/              (frontend placeholder)
├── pyproject.toml         (Python 3.13, no dependencies)
├── requirements.txt       (empty)
└── data/
    ├── processed_course_catalog_cleaned.csv   (2.11 MB, 2,753 courses)
    ├── role_skill_benchmarks_cleaned.csv       (429 KB, 1,016 roles)
    └── skill_taxonomy.csv                      (531 KB, 8,795 skills)
```

> [!NOTE]
> The project is a fresh scaffold with no backend, frontend, or processing code.
> All three datasets are in the root `data/` directory (no `raw/` vs `processed/` separation yet).

---

## 2. Dataset A — Courses

**File**: [`processed_course_catalog_cleaned.csv`](file:///c:/Users/singh/OneDrive/Desktop/sih_project/data/processed_course_catalog_cleaned.csv)

### Schema

| Column | Type | Description |
|--------|------|-------------|
| `course_id` | string | Unique ID (format: `CRS_XXXX`) |
| `course_title` | string | Course name |
| `domain` | string | Subject domain |
| `institution` | string | Provider/university |
| `difficulty_level` | string | Beginner/Intermediate/Advanced/Mixed |
| `duration` | string | Time bracket |
| `skills_covered` | string | **Comma-separated skill list** |
| `rating` | float64 | Course rating (1.9 – 5.0) |
| `reviews` | int64 | Review count (6 – 277,000) |
| `embedding_context` | string | Pre-generated embedding text (~373 chars avg) |

### Quality Summary

| Metric | Value |
|--------|-------|
| Total rows | **2,753** |
| Missing values | **0** (across all columns) |
| Duplicate rows | **0** |
| Duplicate IDs | **0** |
| Duplicate titles | **0** |
| Null/empty skills | **0** |

> [!TIP]
> This dataset is remarkably clean — no missing values, no duplicates, all IDs unique. It appears to be pre-processed.

### Domain Distribution

| Domain | Count |
|--------|-------|
| Business | 961 |
| Computer Science | 913 |
| Data Science | 848 |
| Information Technology | 31 |

### Difficulty Distribution

| Level | Count |
|-------|-------|
| Beginner | 1,447 |
| Intermediate | 892 |
| Mixed | 309 |
| Advanced | 105 |

### Duration Distribution

| Duration | Count |
|----------|-------|
| 1 – 4 Weeks | 1,151 |
| 1 – 3 Months | 994 |
| 3 – 6 Months | 468 |
| Less Than 2 Hours | 140 |

### Rating Statistics

| Stat | Value |
|------|-------|
| Min | 1.9 |
| Max | 5.0 |
| Mean | 4.57 |
| Median | 4.60 |
| Std Dev | 0.31 |

### Review Statistics

| Stat | Value |
|------|-------|
| Min | 6 |
| Max | 277,000 |
| Mean | 2,923 |
| Median | 320 |

### Skills Covered

| Metric | Value |
|--------|-------|
| Total skill mentions | **38,084** |
| Unique skills | **1,753** |
| Min skills per course | 1 |
| Max skills per course | 22 |
| Mean skills per course | 13.8 |

**Top 15 Most Common Skills in Courses**:

| Skill | Count |
|-------|-------|
| Data Analysis | 452 |
| Artificial Intelligence | 300 |
| Machine Learning | 292 |
| Generative AI | 255 |
| Data Manipulation | 232 |
| Computer Programming | 212 |
| Python Programming | 209 |
| Algorithms | 201 |
| Statistical Analysis | 199 |
| Applied Machine Learning | 198 |
| Data Structures | 196 |
| Data Ethics | 195 |
| Data Visualization Software | 195 |
| Debugging | 188 |
| Data Cleansing | 187 |

### Top Institutions

| Institution | Courses |
|-------------|---------|
| IBM | 178 |
| Coursera Project Network | 131 |
| University of Michigan | 113 |
| UIUC | 100 |
| UC Boulder | 99 |
| Microsoft | 82 |
| UPenn | 77 |
| DeepLearning.AI | 70 |
| Johns Hopkins | 69 |
| Google | 68 |

---

## 3. Dataset B — Roles / Competencies

**File**: [`role_skill_benchmarks_cleaned.csv`](file:///c:/Users/singh/OneDrive/Desktop/sih_project/data/role_skill_benchmarks_cleaned.csv)

### Schema

| Column | Type | Description |
|--------|------|-------------|
| `onet_code` | string | O\*NET occupation code (format: `##-####.##`) |
| `role_title` | string | Job title |
| `role_description` | string | Role description (~214 chars avg) |
| `stat_benchmark` | float64 | Statistical competency score (3.8 – 70.3) |
| `tech_benchmark` | float64 | Technical competency score (4.9 – 80.4) |
| `gov_benchmark` | float64 | Governance competency score (10.0 – 71.2) |
| `beh_benchmark` | float64 | Behavioral competency score (22.4 – 69.9) |
| `key_software_tools` | string | Comma-separated tool list |
| `data_confidence` | string | "measured" or "estimated_default" |

### Quality Summary

| Metric | Value |
|--------|-------|
| Total rows | **1,016** |
| Missing values | **0** |
| Duplicate rows | **0** |
| Duplicate O\*NET codes | **0** |
| Duplicate titles | **0** |
| Invalid O\*NET format | **0** |
| All benchmarks present | **Yes (1,016/1,016)** |

### Benchmark Statistics

| Benchmark | Min | Max | Mean | Median | Std |
|-----------|-----|-----|------|--------|-----|
| stat_benchmark | 3.8 | 70.3 | 34.82 | 33.35 | 13.03 |
| tech_benchmark | 4.9 | 80.4 | 36.64 | 35.25 | 13.81 |
| gov_benchmark | 10.0 | 71.2 | 41.10 | 42.10 | 11.02 |
| beh_benchmark | 22.4 | 69.9 | 46.73 | 49.00 | 9.41 |

### Data Confidence

| Type | Count |
|------|-------|
| measured | 894 (88%) |
| estimated_default | 122 (12%) |

### Software Tools

| Metric | Value |
|--------|-------|
| Total tool mentions | 5,483 |
| Unique tools | 1,847 |

**Top tools**: Microsoft Excel (286), Microsoft Office (204), Adobe Acrobat (160), Email software (129), AutoCAD (127)

### Relevant Statistical / Government Roles Found

| Keyword | Matches | Examples |
|---------|---------|---------|
| `statist*` | 3 | Statisticians, Biostatisticians, Statistical Assistants |
| `data*` | 6 | Database Administrators, Data Scientists, Data Warehousing Specialists |
| `analy*` | 19 | Management Analysts, Budget Analysts, Operations Research Analysts |
| `research*` | 6 | Survey Researchers, Computer & Info Research Scientists |
| `survey*` | 4 | Surveyors, Geodetic Surveyors, Survey Researchers |
| `econom*` | 3 | Economists, Environmental Economists |
| `government*` | 2 | Government Property Inspectors |

> [!IMPORTANT]
> **CRITICAL FINDING**: The role dataset contains **aggregate benchmark scores** (stat, tech, gov, beh), **NOT** individual skill-level mappings. There is no `role → skill → required_level` relationship in this dataset. The `role_skills.csv` must be derived or constructed.

---

## 4. Dataset C — Skill Taxonomy

**File**: [`skill_taxonomy.csv`](file:///c:/Users/singh/OneDrive/Desktop/sih_project/data/skill_taxonomy.csv)

### Schema

| Column | Type | Description |
|--------|------|-------------|
| `skill_name` | string | Canonical skill name |
| `category` | string | Skill category |

### Quality Summary

| Metric | Value |
|--------|-------|
| Total rows | **8,795** |
| Missing values | **0** |
| Duplicate skill names | **0** |
| Case-insensitive duplicates | **0** |
| Leading whitespace | **0** |
| Trailing whitespace | **0** |

> [!TIP]
> The skill taxonomy is very clean — no duplicates, no casing issues, no whitespace problems.

### Skill Name Length

| Stat | Value |
|------|-------|
| Min | 1 char |
| Max | 111 chars |
| Mean | 25.4 chars |

**Very short names (≤2 chars)**: `R`, `C`, `C#`, `Go`, `J`, `xv`

### Top Categories (135 total)

| Category | Skills |
|----------|--------|
| Analytical or scientific software | 1,678 |
| Data base user interface and query software | 890 |
| Medical software | 663 |
| Financial analysis software | 353 |
| Computer aided design CAD software | 338 |
| Enterprise resource planning ERP software | 260 |
| Human resources software | 238 |
| Graphics or photo imaging software | 221 |
| Document management software | 197 |
| Project management software | 194 |

> [!NOTE]
> The taxonomy is heavily oriented toward **software tools/technologies** (most categories are software categories). This means the taxonomy is essentially the O\*NET technology/tool taxonomy rather than a general competency taxonomy. "Essential Skills" like Reading Comprehension, Active Listening, Writing are also present but are a small portion.

---

## 5. Cross-Dataset Analysis

### Course Skills vs. Canonical Taxonomy — MAJOR GAP

| Metric | Value |
|--------|-------|
| Canonical taxonomy skills | **8,795** |
| Unique skills in courses | **1,753** |
| **Exact matches** | **64 (3.7%)** |
| In courses but NOT in taxonomy | **1,689** |
| In taxonomy but NOT in courses | **8,731** |
| Case-insensitive matches | **86** |
| **Unmapped after case normalization** | **1,667 (95%)** |

> [!CAUTION]
> **Only 64 out of 1,753 course skills (3.7%) exactly match the canonical taxonomy.** Even with case-insensitive matching, 95% of course skills remain unmapped. This is the **#1 data challenge** for the project.

**Why the gap exists**: The course skills use human-readable, descriptive names (e.g., "Python Programming", "Data Analysis", "Machine Learning") while the taxonomy contains mostly software-specific tool names from O\*NET (e.g., "Adobe Photoshop", "Microsoft Excel", "SAP Crystal Reports"). They represent **different taxonomic domains**.

**Sample unmapped course skills** (all have NO MATCH in taxonomy):
`.NET Framework`, `3D Modeling`, `A/B Testing`, `API Design`, `AWS SageMaker`, `Accounting`, `Active Directory`, `Adaptability`, `Administration`

### Role Tools vs. Taxonomy

| Metric | Value |
|--------|-------|
| Unique role tools | 1,847 |
| Tools matching course skills | 25 |
| **Tools matching taxonomy** | **1,835 (99.4%)** |

> [!IMPORTANT]
> The role `key_software_tools` field maps almost perfectly to the skill taxonomy (99.4%) — confirming both are drawn from the O\*NET technology/tool classification. However, these are **tools**, not general competencies like "Python Programming" or "Statistical Analysis."

---

## 6. Critical Findings & Gaps

### Gap 1 — No Role → Skill Mapping

The role dataset provides **aggregate benchmark scores** (stat, tech, gov, beh), not per-skill requirements. To create `role_skills.csv`, we need to:

1. Map benchmark categories to specific skills
2. Use role descriptions + software tools as signals
3. Consider O\*NET API for authoritative skill mappings
4. Support manual/admin mapping for gaps

### Gap 2 — Taxonomy Mismatch

The skill taxonomy (O\*NET tools) and course skills (Coursera competencies) are **from different classification systems**. We need to either:

1. **Expand the taxonomy** to include course-level competencies, OR
2. **Create a mapping layer** (aliases) between course skills and a unified taxonomy, OR
3. **Build a dual taxonomy** — tools (from O\*NET) + competencies (from courses)

### Gap 3 — No Employee Data

No employee data exists. Synthetic/demo data must be created for the MVP.

### Gap 4 — No Relational Structure

`skills_covered` is a comma-separated text field, not a normalized relationship. Needs parsing into `course_skills.csv`.

---

## 7. Recommendations for Phase 2

| Priority | Task | Notes |
|----------|------|-------|
| 1 | Reorganize data into `data/raw/` and `data/processed/` | Keep originals untouched |
| 2 | **Design unified skill taxonomy** | Merge O\*NET tools + course competencies; define clear categories |
| 3 | Build `skill_aliases.csv` | Map course skill names → canonical skills |
| 4 | Parse `skills_covered` into `course_skills.csv` | Normalize the comma-separated field |
| 5 | Validate and clean course data | Already clean, but validate edge cases |
| 6 | Validate and clean role data | Flag `estimated_default` confidence roles |
| 7 | Begin `role_skills.csv` structure | Even if mapping is incomplete, create the schema |
| 8 | Create synthetic employee data | For MVP demonstration |

---

## 8. Files Created in Phase 1

| File | Purpose |
|------|---------|
| [`scripts/inspect_data.py`](file:///c:/Users/singh/OneDrive/Desktop/sih_project/scripts/inspect_data.py) | Data inspection script — produces full quality report |
| [`docs/data_audit.md`](file:///c:/Users/singh/OneDrive/Desktop/sih_project/docs/data_audit.md) | This document |
