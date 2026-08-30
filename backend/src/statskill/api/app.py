"""FastAPI application for the StatSkill MVP."""
import pandas as pd
from fastapi import FastAPI, HTTPException
from sqlalchemy import select
from statskill.core.database import SessionLocal, User, Skill, Role, Course, RoleSkill, CourseSkill, LearningProgress, LessonProgress, ModuleAssessmentAttempt, SkillHistory
from statskill.services.course_content import content, course_or_404, state, enroll, complete_lesson as complete_lesson_service, PASS_MARK
from statskill.services.quiz import generate, submit, history, ModuleQuiz, start_attempt, final_quiz, submit_final
from statskill.services.skill_gap import load_profile, analyze_gaps, recommend_courses
from statskill.services.recommendation import next_recommendations
from statskill.schemas.user import UserCreate
from statskill.schemas.skill import SkillInput
from pydantic import BaseModel, Field

app = FastAPI(title="StatSkill AI API", version="0.3.0")

class ProgressInput(BaseModel):
    course_id: str
    progress_percent: float = Field(ge=0, le=100)
    status: str = "in_progress"

def frames(session):
    skills = pd.read_sql(select(Skill.id.label("skill_id"), Skill.name.label("skill_name")), session.bind)
    roles = pd.read_sql(select(Role.onet_code, Role.title, Role.description, Role.is_showcase), session.bind)
    role_skills = pd.read_sql(select(RoleSkill.role_code.label("onet_code"), RoleSkill.skill_id, Skill.name.label("skill_name"), RoleSkill.required_level, RoleSkill.importance, RoleSkill.source, RoleSkill.confidence).join(Skill, Skill.id == RoleSkill.skill_id), session.bind)
    course_skills = pd.read_sql(select(CourseSkill.course_id, Course.title.label("course_title"), CourseSkill.skill_id, Skill.name.label("skill_name"), CourseSkill.raw_skill, CourseSkill.mapped).join(Course, Course.course_id == CourseSkill.course_id).join(Skill, Skill.id == CourseSkill.skill_id), session.bind)
    return skills, roles, role_skills, course_skills

@app.get("/health")
def health():
    with SessionLocal() as session: session.execute(select(1))
    return {"status": "ok"}

@app.get("/skills")
def skills():
    with SessionLocal() as session:
        return [{"skill_id": x.id, "skill_name": x.name, "skill_type": x.skill_type} for x in session.scalars(select(Skill).order_by(Skill.name))]

@app.get("/roles")
def roles():
    with SessionLocal() as session:
        return [{"onet_code": x.onet_code, "title": x.title} for x in session.scalars(select(Role).order_by(Role.title))]

@app.get("/courses")
def courses(limit: int = 50):
    if not 1 <= limit <= 500: raise HTTPException(400, "limit must be 1-500")
    with SessionLocal() as session:
        return [{"course_id": x.course_id, "title": x.title, "rating": x.rating} for x in session.scalars(select(Course).limit(limit))]

@app.get("/courses/{course_id}")
def course(course_id: str):
    with SessionLocal() as session:
        c = course_or_404(session, course_id); return {"course_id": c.course_id, "title": c.title, "domain": c.domain, "institution": c.institution, "content": content(course_id)}

@app.get("/courses/{course_id}/modules")
def modules(course_id: str):
    with SessionLocal() as session: course_or_404(session, course_id); return content(course_id)["modules"]

@app.get("/courses/{course_id}/modules/{module_id}")
def module_details(course_id: str, module_id: str):
    with SessionLocal() as session: course_or_404(session, course_id); return content(course_id, "module", module_id)

@app.post("/users/{user_id}/courses/{course_id}/enrollment")
def enrollment(user_id: int, course_id: str):
    with SessionLocal() as session: return enroll(session, user_id, course_id)

@app.get("/users/{user_id}/courses/{course_id}/progress")
def course_progress(user_id: int, course_id: str):
    with SessionLocal() as session:
        if not session.get(User, user_id): raise HTTPException(404, "user not found")
        return state(session, user_id, course_id)

@app.post("/users/{user_id}/courses/{course_id}/lessons/{lesson_id}/complete")
def complete_lesson(user_id: int, course_id: str, lesson_id: str, module_id: str | None = None):
    with SessionLocal() as session:
        if not session.get(User, user_id): raise HTTPException(404, "user not found")
        return complete_lesson_service(session, user_id, course_id, lesson_id, module_id)

class AssessmentInput(BaseModel):
    answers: list[int]
    attempt_id: int | None = None
    difficulty: str = "intermediate"

@app.get("/users/{user_id}/courses/{course_id}/modules/{module_id}/quiz")
def generate_quiz(user_id: int, course_id: str, module_id: str, difficulty: str = "intermediate"):
    with SessionLocal() as session:
        if not session.get(User, user_id): raise HTTPException(404, "user not found")
        current = state(session, user_id, course_id)
        target = next((m for m in current["modules"] if m["module_id"] == module_id), None)
        if not target: raise HTTPException(404, "module not found")
        if not target["unlocked"]: raise HTTPException(423, "module is locked")
        prior = session.scalars(select(ModuleAssessmentAttempt).where(ModuleAssessmentAttempt.user_id == user_id, ModuleAssessmentAttempt.course_id == course_id, ModuleAssessmentAttempt.module_id == module_id)).all()
        excluded = {q["question"] for item in prior for q in __import__('json').loads(item.questions_json)}
        quiz = generate(course_id, module_id, exclude_questions=excluded, difficulty=difficulty); attempt = start_attempt(session, user_id, course_id, module_id, quiz)
        return {"attempt_id": attempt.id, **quiz.model_dump()}

@app.post("/users/{user_id}/courses/{course_id}/modules/{module_id}/assessment")
def submit_assessment(user_id: int, course_id: str, module_id: str, payload: AssessmentInput):
    with SessionLocal() as session:
        if not session.get(User, user_id): raise HTTPException(404, "user not found")
        current = state(session, user_id, course_id); target = next((m for m in current["modules"] if m["module_id"] == module_id), None)
        if not target: raise HTTPException(404, "module not found")
        if not target["unlocked"]: raise HTTPException(423, "module is locked")
        try:
            attempt = session.get(ModuleAssessmentAttempt, payload.attempt_id) if payload.attempt_id else None
            quiz = ModuleQuiz.model_validate({"questions": __import__('json').loads(attempt.questions_json)}) if attempt else generate(course_id, module_id, difficulty=payload.difficulty)
            return submit(session, user_id, course_id, module_id, payload.answers, quiz, payload.attempt_id)
        except ValueError as exc: raise HTTPException(422, str(exc)) from exc

@app.get("/users/{user_id}/courses/{course_id}/modules/{module_id}/assessments")
def assessment_history(user_id: int, course_id: str, module_id: str):
    with SessionLocal() as session:
        if not session.get(User, user_id): raise HTTPException(404, "user not found")
        course_or_404(session, course_id)
        if not any(m["id"] == module_id for m in content(course_id)["modules"]): raise HTTPException(404, "module not found")
        return history(session, user_id, course_id, module_id)

@app.get("/users/{user_id}/courses/{course_id}/final-assessment")
def get_final_assessment(user_id: int, course_id: str):
    with SessionLocal() as session:
        if not session.get(User, user_id): raise HTTPException(404, "user not found")
        if state(session, user_id, course_id)["status"] != "completed": raise HTTPException(423, "final assessment is locked")
        return final_quiz(course_id).model_dump()

@app.post("/users/{user_id}/courses/{course_id}/final-assessment")
def post_final_assessment(user_id: int, course_id: str, payload: AssessmentInput):
    with SessionLocal() as session:
        if not session.get(User, user_id): raise HTTPException(404, "user not found")
        try: return submit_final(session, user_id, course_id, payload.answers, final_quiz(course_id))
        except ValueError as exc: raise HTTPException(422, str(exc)) from exc

@app.post("/users")
def create_user(payload: UserCreate):
    with SessionLocal() as session:
        user = User(name=payload.name, email=payload.email); session.add(user); session.commit(); session.refresh(user)
        return {"id": user.id, "name": user.name, "email": user.email}

@app.put("/users/{user_id}/skills")
def set_skills(user_id: int, payload: list[SkillInput]):
    with SessionLocal() as session:
        user = session.get(User, user_id)
        if not user: raise HTTPException(404, "user not found")
        valid = {x.id for x in session.scalars(select(Skill))}
        for item in payload:
            if item.skill_id not in valid: raise HTTPException(422, f"unknown skill: {item.skill_id}")
            current = next((x for x in user.employee_skills if x.skill_id == item.skill_id), None)
            if current:
                if current.level != item.level: session.add(SkillHistory(user_id=user_id, skill_id=item.skill_id, previous_level=current.level, new_level=item.level, source="manual"))
                current.level = item.level
            else:
                from statskill.core.database import EmployeeSkill
                user.employee_skills.append(EmployeeSkill(skill_id=item.skill_id, level=item.level))
                session.add(SkillHistory(user_id=user_id, skill_id=item.skill_id, previous_level=0, new_level=item.level, source="manual"))
        session.commit()
        return {"user_id": user_id, "skills_saved": len(payload)}

@app.get("/users/{user_id}/gaps/{onet_code}")
def gaps(user_id: int, onet_code: str):
    with SessionLocal() as session:
        user = session.get(User, user_id)
        if not user: raise HTTPException(404, "user not found")
        skills, _, role_skills, _ = frames(session); names = dict(zip(skills.skill_id, skills.skill_name))
        profile = load_profile(user.name, {names[x.skill_id]: x.level for x in user.employee_skills if x.skill_id in names})
        return analyze_gaps(profile, onet_code, role_skills).to_dict(orient="records")

@app.get("/users/{user_id}/recommendations/{onet_code}")
def recommendations(user_id: int, onet_code: str):
    with SessionLocal() as session:
        user = session.get(User, user_id)
        if not user: raise HTTPException(404, "user not found")
        skills, _, role_skills, course_skills = frames(session); names = dict(zip(skills.skill_id, skills.skill_name))
        profile = load_profile(user.name, {names[x.skill_id]: x.level for x in user.employee_skills if x.skill_id in names})
        gap_df = analyze_gaps(profile, onet_code, role_skills)
        return recommend_courses(gap_df, course_skills).to_dict(orient="records")

@app.get("/users/{user_id}/next-recommendations/{onet_code}")
def next_recommendation_list(user_id: int, onet_code: str, limit: int = 10):
    if not 1 <= limit <= 50: raise HTTPException(400, "limit must be 1-50")
    with SessionLocal() as session:
        if not session.get(User, user_id): raise HTTPException(404, "user not found")
        gap_df, ranked = next_recommendations(session, user_id, onet_code, limit)
        return {"remaining_gaps": gap_df[gap_df.gap > 0].to_dict(orient="records"), "recommendations": ranked.to_dict(orient="records")}

@app.put("/users/{user_id}/progress")
def save_progress(user_id: int, payload: ProgressInput):
    if payload.status not in {"not_started", "in_progress", "completed"}: raise HTTPException(422, "invalid status")
    with SessionLocal() as session:
        if not session.get(User, user_id): raise HTTPException(404, "user not found")
        if not session.get(Course, payload.course_id): raise HTTPException(404, "course not found")
        item = session.scalar(select(LearningProgress).where(LearningProgress.user_id == user_id, LearningProgress.course_id == payload.course_id))
        if item is None: item = LearningProgress(user_id=user_id, course_id=payload.course_id); session.add(item)
        item.progress_percent = payload.progress_percent; item.status = payload.status
        session.commit()
        return {"user_id": user_id, "course_id": payload.course_id, "progress_percent": item.progress_percent, "status": item.status}

@app.get("/users/{user_id}/progress")
def get_progress(user_id: int):
    with SessionLocal() as session:
        if not session.get(User, user_id): raise HTTPException(404, "user not found")
        return [{"course_id": x.course_id, "progress_percent": x.progress_percent, "status": x.status} for x in session.scalars(select(LearningProgress).where(LearningProgress.user_id == user_id))]
