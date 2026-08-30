"""Validated Groq quizzes with deterministic demo fallback and scoring."""
import json
import logging
from time import perf_counter
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from statskill.ai.llm import groq_json
from statskill.core.database import ModuleAssessmentAttempt
from statskill.services.course_content import content, state, PASS_MARK
log = logging.getLogger(__name__)

class QuizQuestion(BaseModel):
    question: str
    options: list[str] = Field(min_length=4, max_length=4)
    correct_answer: int = Field(ge=0, le=3)
    explanation: str
    skill: str
    difficulty: str
    @staticmethod
    def normalize(value):
        value = str(value).strip().lower()
        return value if value in {"beginner", "intermediate", "advanced"} else "intermediate"
    def model_post_init(self, __context):
        self.difficulty = self.normalize(self.difficulty)
class ModuleQuiz(BaseModel):
    questions: list[QuizQuestion] = Field(min_length=5, max_length=5)

def fallback(course_id: str, module_id: str, exclude_questions: set[str] | None = None) -> ModuleQuiz:
    raw = content(course_id, "assessment", module_id)["questions"]
    lessons = content(course_id, "module", module_id)["lessons"]
    qs = []
    exclude_questions = exclude_questions or set()
    for i in range(5):
        q = raw[i % len(raw)]
        lesson = lessons[i % len(lessons)]
        question = q["prompt"] if i < len(raw) else f"Which idea is central to {lesson['title']}?"
        if question in exclude_questions: question = f"In practice, what should a learner apply from {lesson['title']}? (variant {i + 1})"
        qs.append(QuizQuestion(question=question, options=(q["options"] + ["None of these"] * 4)[:4], correct_answer=q["answer"], explanation=f"This checks {lesson['title']}.", skill=lesson["concepts"][0], difficulty="beginner"))
    return ModuleQuiz(questions=qs)

def generate(course_id: str, module_id: str, exclude_questions: set[str] | None = None, difficulty: str = "intermediate") -> ModuleQuiz:
    started = perf_counter()
    course = content(course_id); module = content(course_id, "module", module_id)
    exclude_questions = exclude_questions or set()
    difficulty = QuizQuestion.normalize(difficulty)
    prompt = json.dumps({"course_title": course["title"], "module": next(m for m in course["modules"] if m["id"] == module_id), "lessons": module["lessons"], "difficulty": difficulty, "previous_question_text_to_avoid": sorted(exclude_questions)})
    try:
        data = groq_json("Return ONLY JSON matching {questions:[{question,options,correct_answer,explanation,skill,difficulty}]}. correct_answer is an integer 0-3; exactly 5 questions and exactly 4 options each.", prompt)
        if isinstance(data, str): data = json.loads(data)
        quiz = ModuleQuiz.model_validate(data)
        if any(q.question in exclude_questions for q in quiz.questions): raise ValueError("generated quiz repeated a previous question")
        log.info("quiz generation course=%s module=%s source=groq duration_ms=%.1f", course_id, module_id, (perf_counter()-started)*1000)
        return quiz
    except (Exception, ValidationError):
        quiz = fallback(course_id, module_id, exclude_questions)
        for q in quiz.questions: q.difficulty = difficulty
        log.info("quiz generation course=%s module=%s source=fallback duration_ms=%.1f", course_id, module_id, (perf_counter()-started)*1000)
        return quiz

def start_attempt(session, user_id, course_id, module_id, quiz: ModuleQuiz):
    item = ModuleAssessmentAttempt(user_id=user_id, course_id=course_id, module_id=module_id, score=0, passed=False, attempt_state="active", questions_json=json.dumps([q.model_dump() for q in quiz.questions]))
    session.add(item); session.commit(); return item

def submit(session, user_id: int, course_id: str, module_id: str, answers: list[int], quiz: ModuleQuiz, attempt_id: int | None = None):
    if len(answers) != 5 or any(a not in range(4) for a in answers): raise ValueError("exactly five answers from 0 to 3 are required")
    correct = sum(a == q.correct_answer for a, q in zip(answers, quiz.questions)); score = round(correct / 5 * 100, 2); passed = score >= PASS_MARK
    signal = {}
    for q, answer in zip(quiz.questions, answers):
        signal[q.skill] = signal.get(q.skill, {"correct": 0, "total": 0}); signal[q.skill]["total"] += 1; signal[q.skill]["correct"] += answer == q.correct_answer
    item = session.get(ModuleAssessmentAttempt, attempt_id) if attempt_id else None
    if item and (item.user_id != user_id or item.course_id != course_id or item.module_id != module_id or item.attempt_state != "active"): raise ValueError("invalid or already submitted attempt")
    if item is None: item = ModuleAssessmentAttempt(user_id=user_id, course_id=course_id, module_id=module_id, questions_json=json.dumps([q.model_dump() for q in quiz.questions])); session.add(item)
    item.score=score; item.passed=passed; item.attempt_state="submitted"; item.answers_json=json.dumps(answers); item.skill_signal_json=json.dumps(signal); session.commit()
    progress = state(session, user_id, course_id); current = next(x for x in progress["modules"] if x["module_id"] == module_id); idx = progress["modules"].index(current)
    next_module = progress["modules"][idx + 1] if idx + 1 < len(progress["modules"]) else None
    return {"attempt_id": item.id, "score": score, "percentage": score, "passed": passed, "pass_mark": PASS_MARK, "module_status": "completed" if passed else "incomplete", "next_module": next_module, "course_status": progress["status"], "skill_signal": signal, "progress": progress}

def history(session, user_id: int, course_id: str, module_id: str):
    rows = session.scalars(select(ModuleAssessmentAttempt).where(ModuleAssessmentAttempt.user_id == user_id, ModuleAssessmentAttempt.course_id == course_id, ModuleAssessmentAttempt.module_id == module_id).order_by(ModuleAssessmentAttempt.submitted_at.desc())).all()
    return [{"attempt_id": x.id, "score": x.score, "passed": x.passed, "questions": json.loads(x.questions_json), "answers": json.loads(x.answers_json), "skill_signal": json.loads(x.skill_signal_json), "submitted_at": x.submitted_at} for x in rows]

def final_quiz(course_id: str) -> ModuleQuiz:
    """Build a separate deterministic course-level assessment from all module objectives."""
    course = content(course_id); questions = []
    for module in course["modules"]:
        raw = content(course_id, "assessment", module["id"])["questions"]
        for question in raw:
            questions.append(QuizQuestion(question=question["prompt"], options=(question["options"] + ["None of these"] * 4)[:4], correct_answer=question["answer"], explanation=f"This assesses the {module['title']} objective.", skill=module["skills"][0], difficulty="intermediate"))
    return ModuleQuiz(questions=questions[:5])

def submit_final(session, user_id: int, course_id: str, answers: list[int], quiz: ModuleQuiz):
    progress = state(session, user_id, course_id)
    if progress["status"] != "completed": raise ValueError("final assessment is unavailable until all modules are complete")
    if len(answers) != len(quiz.questions): raise ValueError("one answer is required for every final-assessment question")
    correct = sum(a == q.correct_answer for a, q in zip(answers, quiz.questions)); score = round(correct / len(quiz.questions) * 100, 2); signal = {}
    for q, answer in zip(quiz.questions, answers):
        signal.setdefault(q.skill, {"correct": 0, "total": 0}); signal[q.skill]["total"] += 1; signal[q.skill]["correct"] += answer == q.correct_answer
    item = ModuleAssessmentAttempt(user_id=user_id, course_id=course_id, module_id="final", score=score, passed=score >= PASS_MARK, attempt_state="submitted", questions_json=json.dumps([q.model_dump() for q in quiz.questions]), answers_json=json.dumps(answers), skill_signal_json=json.dumps(signal)); session.add(item); session.commit()
    return {"attempt_id": item.id, "score": score, "percentage": score, "passed": score >= PASS_MARK, "assessment_type": "final", "skill_signal": signal, "course_status": progress["status"]}
