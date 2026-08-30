# StatSkill AI

StatSkill AI is a PostgreSQL-backed MVP that maps employee skills to role requirements, identifies skill gaps, recommends catalog courses, and supports persisted demo learning with lessons and module quizzes. The final-assessment and assessment-driven permanent skill-update stages are not implemented in the current repository.

## Overview

```mermaid
flowchart LR
 User --> Streamlit[Streamlit demo]
 Streamlit --> API[FastAPI]
 API --> Services[Skill-gap, course, quiz, recommendation services]
 Services --> Groq[Groq API]
 Services --> ORM[SQLAlchemy]
 ORM --> DB[(PostgreSQL 17)]
 CSV[Raw CSV] --> ETL[Phase 2 processing]
 ETL --> Processed[Processed CSV]
 Processed --> Loader[Database loader]
 Loader --> DB
```

## Implemented learning loop

```mermaid
flowchart TD
 Employee --> Skills[Employee skills]
 Skills --> Role[Target role]
 Role --> Gap[Skill gap]
 Gap --> Rec[Course recommendation]
 Rec --> Course[Enrollment]
 Course --> Lessons
 Lessons --> Quiz[Five-question module quiz]
 Quiz --> Decision{Score >= 70%?}
 Decision -- FAIL --> Retry[New persisted attempt]
 Retry --> Quiz
 Decision -- PASS --> Next[Next module unlocked]
 Next --> Lessons
```

Implemented features include employee profiles, skill evaluation, target roles, role requirements, skill gaps, catalog recommendations, demo courses, modules, lessons, enrollment, lesson progress, Groq quizzes, quiz difficulty, backend pass/fail progression, retry attempts, PostgreSQL persistence, FastAPI, Streamlit, and the O*NET/Phase 2 taxonomy and mapping pipeline. Final assessment, automatic skill updates from assessments, and automatic final skill-history workflow are future work.

## Skill gap and recommendations

`statskill.services.skill_gap.analyze_gaps` matches employee skills by normalized name. Missing skills default to level `0`; the actual formula is:

```text
gap = max(required_level - employee_level, 0)
```

Gaps sort by descending gap, then descending importance. `recommend_courses` joins remaining gaps to `course_skills`, ranks by the sum of covered gap values and then coverage count, and returns the ranked courses. `next_recommendations` reads current employee skills, role skills, and course mappings from PostgreSQL, excludes courses whose `learning_progress.status` is `completed`, and adds explanations containing actual covered skills and current/required levels.

## Course content and AI

Catalog CSV rows contain metadata; lesson bodies live separately in `course_content/<course_id>/`. Current content includes `CRS_0975` (Python Basics) and `CRS_1011` (Probability & Statistics for Machine Learning & Data Science), with course, module, and fallback assessment JSON.

Groq is the only LLM provider. Configure it with placeholders in `.env`:

```env
DATABASE_URL=postgresql+psycopg://statskill_app:CHANGE_ME@localhost:5432/statskill
GROQ_API_KEY=your-groq-key-here
GROQ_BASE_URL=https://api.groq.com/openai/v1
GROQ_MODEL=your-groq-model
```

`DATABASE_URL` is required. Groq variables are optional because malformed responses, API failures, missing keys, timeouts, and rate-limit errors use deterministic fallback quizzes. Quiz questions are validated with Pydantic and contain question, four options, correct answer, explanation, skill, and normalized `beginner`, `intermediate`, or `advanced` difficulty. A generated quiz is persisted under an attempt ID; submission scores that exact attempt. Retries create new attempts and preserve prior attempts.

## Database

```mermaid
erDiagram
 USERS ||--o{ EMPLOYEE_SKILLS : has
 USERS ||--o{ COURSE_ENROLLMENTS : enrolls
 USERS ||--o{ LESSON_PROGRESS : completes
 USERS ||--o{ MODULE_ASSESSMENT_ATTEMPTS : submits
 USERS ||--o{ SKILL_HISTORY : records
 SKILLS ||--o{ EMPLOYEE_SKILLS : measures
 SKILLS ||--o{ ROLE_SKILLS : requires
 SKILLS ||--o{ COURSE_SKILLS : covers
 ROLES ||--o{ ROLE_SKILLS : has
 COURSES ||--o{ COURSE_SKILLS : has
 COURSES ||--o{ COURSE_ENROLLMENTS : has
 COURSES ||--o{ LESSON_PROGRESS : tracks
 COURSES ||--o{ MODULE_ASSESSMENT_ATTEMPTS : has
 USERS { int id PK }
 SKILLS { string id PK }
 ROLES { string onet_code PK }
 COURSES { string course_id PK }
 EMPLOYEE_SKILLS {
   int id PK
   int user_id FK
   string skill_id FK
   int level
 }
 ROLE_SKILLS {
   int id PK
   string role_code FK
   string skill_id FK
   int required_level
   int importance
 }
 COURSE_SKILLS {
   int id PK
   string course_id FK
   string skill_id FK
 }
 COURSE_ENROLLMENTS {
   int id PK
   int user_id FK
   string course_id FK
 }
 LESSON_PROGRESS {
   int id PK
   int user_id FK
   string course_id FK
   string lesson_id
 }
 MODULE_ASSESSMENT_ATTEMPTS {
   int id PK
   int user_id FK
   string course_id FK
   string module_id
   float score
   boolean passed
   string attempt_state
 }
 SKILL_HISTORY {
   int id PK
   int user_id FK
   string skill_id FK
   int previous_level
   int new_level
 }
```

Other actual tables are `skill_aliases`, `skill_assessments`, `skill_gaps`, `course_recommendations`, and `learning_progress`.

## API

```text
GET  /health
POST /users
PUT  /users/{user_id}/skills
GET  /skills
GET  /roles
GET  /courses
GET  /courses/{course_id}
GET  /courses/{course_id}/modules
GET  /courses/{course_id}/modules/{module_id}
GET  /users/{user_id}/gaps/{onet_code}
GET  /users/{user_id}/recommendations/{onet_code}
GET  /users/{user_id}/next-recommendations/{onet_code}
POST /users/{user_id}/courses/{course_id}/enrollment
GET  /users/{user_id}/courses/{course_id}/progress
POST /users/{user_id}/courses/{course_id}/lessons/{lesson_id}/complete
PUT  /users/{user_id}/progress
GET  /users/{user_id}/progress
GET  /users/{user_id}/courses/{course_id}/modules/{module_id}/quiz
POST /users/{user_id}/courses/{course_id}/modules/{module_id}/assessment
GET  /users/{user_id}/courses/{course_id}/modules/{module_id}/assessments
```

There is currently no final-assessment endpoint.

## Data pipeline

```mermaid
flowchart LR
 Raw[data/raw source copies] --> Build[backend/src/statskill/main.py]
 Build --> Taxonomy[unified taxonomy and aliases]
 Build --> Mappings[role_skills and course_skills CSV]
 Taxonomy --> Load[backend/scripts/load_database.py]
 Mappings --> Load
 Load --> PostgreSQL[(PostgreSQL)]
```

The loader upserts records and uses unique constraints for duplicate role-skill, course-skill, employee-skill, and enrollment relationships.

## Streamlit demo

Run `demo/app.py` to create/select an employee, choose current skills and a target role, view the gap and recommendations, enroll in `CRS_0975` or `CRS_1011`, complete lessons, generate a quiz, submit it, see backend score/pass/fail, retry failed quizzes with a new attempt, and observe persisted module unlock state. The UI does not implement final assessment or automatic skill updates because those backend operations do not exist yet.

## Installation and running

Use Python 3.11+ and PostgreSQL 17 on Windows. `uv` is recommended:

```powershell
cd C:\Users\singh\OneDrive\Desktop\sih_project
uv venv
uv pip install -r requirements.txt
copy .env.example .env
```

Set `DATABASE_URL` in `.env`, create the PostgreSQL database/user, then:

```powershell
alembic upgrade head
python backend/scripts/build_data.py
python backend/scripts/load_database.py
python backend/scripts/verify_database.py
```

FastAPI:

```powershell
$env:PYTHONPATH="backend/src"
uvicorn statskill.api.app:app --reload --port 8000
```

FastAPI docs: `http://localhost:8000/docs`

Streamlit:

```powershell
streamlit run demo/app.py --server.port 8501
```

Streamlit: `http://localhost:8501`

Tests:

```powershell
python -m pytest -q
```

## Project structure

```text
sih_project/
├── backend/
│   ├── alembic/versions/       # Database migrations
│   ├── scripts/                # Build, load, verify, and demo scripts
│   └── src/statskill/
│       ├── ai/                 # Groq boundary and NLP extraction
│       ├── api/                # FastAPI routes
│       ├── core/               # Config and SQLAlchemy models
│       ├── models/             # Model re-exports
│       ├── schemas/            # Pydantic request schemas
│       ├── services/           # Skill gap, course, quiz, and recommendations
│       └── main.py             # Offline ETL orchestrator
├── config/                     # MVP roles and manual mappings
├── course_content/             # Demo JSON course/module/assessment content
├── data/raw/                   # Source CSV copies
├── data/processed/             # Generated ETL outputs
├── demo/app.py                 # Streamlit client
├── docs/                       # Design and audit notes
├── .env.example
├── alembic.ini
├── pyproject.toml
└── requirements.txt
```

## Demo scenario

Create a profile, select `15-2041.00` Statisticians, save low skill levels, inspect the actual role gap and recommendation list, enroll in `CRS_0975`, complete Module 1 lessons, generate and submit its quiz, and verify Module 2 unlocks only after a passing backend result. Intentionally fail once, retry, and verify two PostgreSQL attempts remain. Then call `/users/{user_id}/next-recommendations/15-2041.00` to view recommendations based on current persisted skills and completed-course filtering.

## MVP versus production

Streamlit is the demonstration client. FastAPI, services, SQLAlchemy, PostgreSQL, migrations, and the offline ETL pipeline are reusable for a future production frontend. Business logic belongs in backend services.

## Future improvements

- Backend final assessment.
- Consent-based assessment-driven skill updates.
- Automatic skill-gap refresh after approved updates.
- Production authentication/frontend.
- Larger course-content and quiz pools.

## Troubleshooting

- PostgreSQL errors: confirm the Windows PostgreSQL 17 service, database, user, and `DATABASE_URL`.
- Migration errors: run `alembic upgrade head` from the repository root.
- Import errors: set `$env:PYTHONPATH="backend/src"`.
- `uv` issues: recreate with `uv venv` and reinstall requirements.
- Pydantic errors: reinstall from `requirements.txt`; quizzes require five questions and four options each.
- Streamlit errors: verify PostgreSQL and the root `.env` file.
- Groq errors/rate limits: check the non-committed Groq variables; fallback quizzes are automatic.
