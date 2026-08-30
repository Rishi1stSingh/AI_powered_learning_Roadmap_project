"""File-backed demo course content and PostgreSQL-backed learning state."""
import json
from functools import lru_cache
from pathlib import Path
from sqlalchemy import select
from fastapi import HTTPException
from statskill.core.database import Course, CourseEnrollment, LessonProgress, ModuleAssessmentAttempt, LearningProgress

ROOT = Path(__file__).resolve().parents[4] / "course_content"
PASS_MARK = 70.0

@lru_cache(maxsize=128)
def content(course_id: str, part: str = "course", module_id: str | None = None):
    folder = "modules" if part == "module" else "assessments"
    path = ROOT / course_id / ("course.json" if part == "course" else f"{folder}/{module_id}.json")
    if not path.exists(): raise HTTPException(404, "course content not found")
    return json.loads(path.read_text(encoding="utf-8"))

def course_or_404(session, course_id):
    course = session.get(Course, course_id)
    if not course: raise HTTPException(404, "course not found")
    return course

def state(session, user_id: int, course_id: str):
    course_or_404(session, course_id)
    enrollment = session.scalar(select(CourseEnrollment).where(CourseEnrollment.user_id == user_id, CourseEnrollment.course_id == course_id))
    lessons = session.scalars(select(LessonProgress).where(LessonProgress.user_id == user_id, LessonProgress.course_id == course_id)).all()
    attempts = session.scalars(select(ModuleAssessmentAttempt).where(ModuleAssessmentAttempt.user_id == user_id, ModuleAssessmentAttempt.course_id == course_id).order_by(ModuleAssessmentAttempt.submitted_at)).all()
    modules = content(course_id)["modules"]
    passed = {a.module_id for a in attempts if a.passed}
    unlocked = 0
    while unlocked < len(modules) and (unlocked == 0 or modules[unlocked-1]["id"] in passed): unlocked += 1
    completed_by_module = {}
    for lesson in lessons:
        completed_by_module.setdefault(lesson.module_id, set()).add(lesson.lesson_id)
    module_state = [{"module_id": m["id"], "unlocked": i < unlocked, "completed_lessons": sum(l["id"] in completed_by_module.get(m["id"], set()) for l in m["lessons"]), "lesson_count": len(m["lessons"]), "quiz_passed": m["id"] in passed} for i, m in enumerate(modules)]
    overall = round(100 * sum(x["completed_lessons"] for x in module_state) / max(1, sum(x["lesson_count"] for x in module_state)), 2)
    if len(passed) == len(modules) and modules: overall = 100.0
    return {"enrolled": enrollment is not None, "course_id": course_id, "progress_percent": overall, "status": "completed" if len(passed) == len(modules) and modules else ("in_progress" if enrollment else "not_started"), "modules": module_state, "current_unlocked_module": modules[unlocked - 1]["id"] if unlocked else None}

def enroll(session, user_id, course_id):
    course_or_404(session, course_id)
    if not session.get(__import__('statskill.core.database', fromlist=['User']).User, user_id): raise HTTPException(404, "user not found")
    item = session.scalar(select(CourseEnrollment).where(CourseEnrollment.user_id == user_id, CourseEnrollment.course_id == course_id))
    if not item: session.add(CourseEnrollment(user_id=user_id, course_id=course_id)); session.commit()
    return state(session, user_id, course_id)

def complete_lesson(session, user_id: int, course_id: str, lesson_id: str, module_id: str | None = None):
    """Idempotently complete a lesson in the currently unlocked module."""
    current = state(session, user_id, course_id)
    if not current["enrolled"]: raise HTTPException(409, "course is not enrolled")
    course_doc = content(course_id)
    module = next((m for m in course_doc["modules"] if (module_id is None or m["id"] == module_id) and any(l["id"] == lesson_id for l in m["lessons"])), None)
    if not module: raise HTTPException(404, "lesson not found")
    if not next(x["unlocked"] for x in current["modules"] if x["module_id"] == module["id"]): raise HTTPException(423, "module is locked")
    item = session.scalar(select(LessonProgress).where(LessonProgress.user_id == user_id, LessonProgress.course_id == course_id, LessonProgress.module_id == module["id"], LessonProgress.lesson_id == lesson_id))
    if item is None:
        session.add(LessonProgress(user_id=user_id, course_id=course_id, module_id=module["id"], lesson_id=lesson_id)); session.commit()
    return state(session, user_id, course_id)
