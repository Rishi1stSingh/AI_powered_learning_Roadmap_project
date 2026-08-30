"""Small Streamlit demo for the StatSkill PostgreSQL-backed MVP."""
from pathlib import Path
import sys

import pandas as pd
import streamlit as st
from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "src"))

from statskill.core.database import (  # noqa: E402
    Course, CourseSkill, EmployeeSkill, LessonProgress, Role, RoleSkill, SessionLocal, Skill, User,
)
from statskill.services.skill_gap import analyze_gaps, load_profile, recommend_courses  # noqa: E402
from statskill.services.course_content import content, state, enroll, complete_lesson
from statskill.services.quiz import generate, submit, history, final_quiz, submit_final
from statskill.services.recommendation import next_recommendations

def level_label(value):
    """Display the persisted 0-100 proficiency scale without confusing it with importance."""
    return f"{int(value)}/100"


@st.cache_data(ttl=60)
def database_data():
    with SessionLocal() as session:
        roles = pd.read_sql(select(Role.onet_code, Role.title, Role.description, Role.is_showcase).order_by(Role.title), session.bind)
        skills = pd.read_sql(select(Skill.id.label("skill_id"), Skill.name.label("skill_name")).order_by(Skill.name), session.bind)
        role_skills = pd.read_sql(select(RoleSkill.role_code.label("onet_code"), RoleSkill.skill_id, Skill.name.label("skill_name"), RoleSkill.required_level, RoleSkill.importance, RoleSkill.source, RoleSkill.confidence).join(Skill, Skill.id == RoleSkill.skill_id), session.bind)
        courses = pd.read_sql(select(Course.course_id, Course.title), session.bind)
        course_skills = pd.read_sql(select(CourseSkill.course_id, Course.title.label("course_title"), CourseSkill.skill_id, Skill.name.label("skill_name"), CourseSkill.raw_skill, CourseSkill.mapped).join(Course, Course.course_id == CourseSkill.course_id).join(Skill, Skill.id == CourseSkill.skill_id), session.bind)
        users = pd.read_sql(select(User.id, User.name, User.email).order_by(User.name), session.bind)
    return roles, skills, role_skills, courses, course_skills, users


st.set_page_config(page_title="StatSkill Demo", page_icon="📊", layout="wide")
st.title("StatSkill skill-gap demo")
st.caption("Hackathon testing interface backed by native PostgreSQL. Phase 3 production UI remains paused.")

try:
    roles, skills, role_skills, courses, course_skills, users = database_data()
except Exception as exc:
    st.error("Could not connect to PostgreSQL. Check DATABASE_URL in .env and ensure PostgreSQL is running.")
    st.exception(exc)
    st.stop()

with st.sidebar:
    st.header("Employee profile")
    user_options = {f"{row.name} (#{row.id})": int(row.id) for row in users.itertuples()}
    selected_user = st.selectbox("Select profile", ["New profile"] + list(user_options))
    if selected_user == "New profile":
        new_name = st.text_input("Name")
        new_email = st.text_input("Email (optional)")
        if st.button("Create profile", disabled=not new_name.strip()):
            with SessionLocal() as session:
                user = User(name=new_name.strip(), email=new_email.strip() or None)
                session.add(user)
                session.commit()
            st.cache_data.clear()
            st.rerun()
        user_id = None
    else:
        user_id = user_options[selected_user]

    role_labels = {row.title: row.onet_code for row in roles.itertuples()}
    selected_role = st.selectbox("Target role", list(role_labels))
    selected_code = role_labels[selected_role]

if user_id is not None:
    with SessionLocal() as session:
        saved = session.scalars(select(EmployeeSkill).where(EmployeeSkill.user_id == user_id)).all()
    saved_levels = {item.skill_id: item.level for item in saved}
else:
    saved_levels = {}

skill_names = dict(zip(skills.skill_id, skills.skill_name))
st.header("1. Evaluate employee skills")
st.caption("Select the skills the employee currently has, then rate each skill from 0 (none) to 100 (advanced).")
chosen_ids = st.multiselect("Current skills", list(skill_names), default=list(saved_levels), format_func=lambda x: skill_names[x])
levels = {skill_id: st.slider(skill_names[skill_id], 0, 100, int(saved_levels.get(skill_id, 50)), key=f"level_{skill_id}") for skill_id in chosen_ids}

if st.button("Save skills", disabled=user_id is None):
    with SessionLocal() as session:
        for skill_id, level in levels.items():
            item = session.scalar(select(EmployeeSkill).where(EmployeeSkill.user_id == user_id, EmployeeSkill.skill_id == skill_id))
            if item is None:
                session.add(EmployeeSkill(user_id=user_id, skill_id=skill_id, level=level))
            else:
                item.level = level
        session.commit()
    st.cache_data.clear()
    st.success("Evaluation saved to PostgreSQL.")

profile = load_profile("Demo employee", {skill_names[k]: v for k, v in levels.items()})
gaps = analyze_gaps(profile, selected_code, role_skills)
recommendations = recommend_courses(gaps, course_skills)

st.header("2. Evaluation summary")
met_count = int((gaps["gap"] == 0).sum())
gap_count = int((gaps["gap"] > 0).sum())
m1, m2, m3 = st.columns(3)
m1.metric("Role skills evaluated", len(gaps))
m2.metric("Requirements met", met_count)
m3.metric("Priority gaps", gap_count)

st.header("3. Role fit and learning plan")
left, right = st.columns(2)
with left:
    st.subheader("Current skills")
    st.dataframe(pd.DataFrame([{"Skill": skill_names[k], "Current level": level_label(v)} for k, v in levels.items()]), hide_index=True)
with right:
    st.subheader("Required skills")
    required_view = gaps[["skill_name", "employee_level", "required_level", "gap", "importance", "status"]].rename(columns={"skill_name": "Skill", "employee_level": "Current level", "required_level": "Required level", "gap": "Gap", "importance": "Importance / weight", "status": "Priority"}).copy()
    required_view["Current level"] = required_view["Current level"].map(level_label)
    required_view["Required level"] = required_view["Required level"].map(level_label)
    required_view["Priority"] = required_view["Priority"].map({"gap": "Gap", "met": "Met"})
    st.dataframe(required_view, hide_index=True)

st.subheader("Priority skill gaps")
gap_view = gaps[gaps.gap > 0][["skill_name", "employee_level", "required_level", "gap", "importance", "source"]].rename(columns={"skill_name": "Skill", "employee_level": "Current level", "required_level": "Required level", "gap": "Gap", "importance": "Importance / weight", "source": "Source"}).copy()
gap_view["Current level"] = gap_view["Current level"].map(level_label)
gap_view["Required level"] = gap_view["Required level"].map(level_label)
st.dataframe(gap_view, hide_index=True)
st.subheader("Recommended courses")
if user_id is not None:
    with SessionLocal() as session:
        _, recommendations = next_recommendations(session, user_id, selected_code)
recommendation_view = recommendations.rename(columns={"course_title": "Course", "skills": "Skills addressed", "score": "Remaining gap score", "explanation": "Why recommended"}).copy()
st.dataframe(recommendation_view[[c for c in ["Course", "Skills addressed", "Remaining gap score", "Why recommended"] if c in recommendation_view]], hide_index=True)

st.subheader("4. Recommended course")
if user_id is None:
    st.info("Create or select an employee profile to save course progress.")
elif recommendations.empty:
    st.info("No courses are currently recommended for this profile.")
else:
    demo_ids = ["CRS_0975", "CRS_1011"]
    recommended_ids = [x for x in recommendations.course_id.tolist() if x in demo_ids]
    course_options = {x: next((r.course_title for r in recommendations.itertuples() if r.course_id == x), x) for x in (recommended_ids or demo_ids)}
    selected_course = st.selectbox("Recommended course", list(course_options), format_func=lambda x: course_options[x])
    with SessionLocal() as session:
        course_row = session.get(Course, selected_course)
        course_state = state(session, user_id, selected_course)
    st.caption(f"Catalog course: {course_row.institution} · {course_row.difficulty_level} · {course_row.duration}")
    notice = st.session_state.pop("progression_notice", None)
    if notice:
        st.success(f"{notice['completed']} Completed ✅")
        if notice["next"]:
            st.info(f"{notice['next']} Unlocked 🔓")
            st.caption(f"Continue to {notice['next']}")
    if not course_state["enrolled"]:
        st.info("Start this course to unlock Module 1.")
        if st.button("Start course", type="primary"):
            with st.spinner("Starting course and loading Module 1..."):
                with SessionLocal() as session: enroll(session, user_id, selected_course)
            st.rerun()
    else:
        course_doc = content(selected_course)
        st.subheader("Course overview")
        st.write(course_doc.get("description", "A structured, practice-oriented learning path."))
        for module in course_doc["modules"]:
            ms = next(x for x in course_state["modules"] if x["module_id"] == module["id"])
            mark = "Completed" if ms["quiz_passed"] else ("Unlocked" if ms["unlocked"] else "Locked")
            label = f"{module['title']} — {mark}"
            if module["id"] == course_state["current_unlocked_module"]:
                with st.container(border=True):
                    st.write(f"**{label} 🔓**")
                    st.caption("Objectives: " + "; ".join(module["objectives"]) + " · Skills: " + ", ".join(module["skills"]))
            else:
                with st.expander(label + (" ✅" if mark == "Completed" else " 🔒"), expanded=False):
                    st.caption("This module is not the active learning section. Complete the current module quiz to progress.")
        st.progress(course_state["progress_percent"] / 100, text=f"Course progress: {course_state['progress_percent']:.0f}%")
        unlocked = course_state["current_unlocked_module"]
        if unlocked:
            module = next(x for x in course_doc["modules"] if x["id"] == unlocked)
            st.subheader(f"Study module: {module['title']}")
            details = content(selected_course, "module", unlocked)
            with SessionLocal() as session:
                completed = {x.lesson_id for x in session.scalars(select(LessonProgress).where(LessonProgress.user_id == user_id, LessonProgress.course_id == selected_course, LessonProgress.module_id == unlocked)).all()}
            for lesson in details["lessons"]:
                st.markdown(f"#### {lesson['title']} ({lesson['duration_minutes']} min)")
                st.write(lesson["content"])
                st.caption("Concepts: " + ", ".join(lesson["concepts"]))
                if lesson["id"] not in completed and st.button("Complete lesson", key=f"complete_{selected_course}_{unlocked}_{lesson['id']}"):
                    with SessionLocal() as session:
                        complete_lesson(session, user_id, selected_course, lesson["id"], unlocked)
                    st.rerun()
                elif lesson["id"] in completed: st.success("Lesson completed")
            all_lessons_done = len(completed) == len(details["lessons"])
            if not all_lessons_done:
                st.info("Finish all lessons to enable the AI quiz.")
            else:
                quiz_key = f"quiz_{selected_course}_{unlocked}"
                if st.button("Generate quiz", key=f"generate_{quiz_key}"):
                    try:
                        with st.spinner("Generating quiz..."):
                            st.session_state[quiz_key] = generate(selected_course, unlocked, st.session_state.get(f"excluded_{quiz_key}", set()))
                        st.session_state.pop(f"result_{quiz_key}", None)
                        st.session_state[f"quiz_source_{quiz_key}"] = "Groq or automatic fallback"
                    except Exception as exc:
                        st.error(f"Quiz generation failed: {exc}")
                quiz = st.session_state.get(quiz_key)
                if quiz:
                    st.caption(f"{module['title']} quiz · Difficulty: {quiz.questions[0].difficulty.title()} · 5 questions · pass mark: 70% · {st.session_state.get(f'quiz_source_{quiz_key}', 'Generated quiz')}")
                    with st.form(f"submit_{quiz_key}"):
                        answers = [st.radio(f"{i + 1}. {q.question}", q.options, key=f"answer_{quiz_key}_{i}") for i, q in enumerate(quiz.questions)]
                        submitted = st.form_submit_button("Submit quiz", type="primary")
                    if submitted:
                        indices = [q.options.index(answer) for q, answer in zip(quiz.questions, answers)]
                        with st.spinner("Submitting quiz and updating course progress..."):
                            with SessionLocal() as session:
                                result = submit(session, user_id, selected_course, unlocked, indices, quiz)
                        st.session_state[f"result_{quiz_key}"] = result
                        if result["passed"]:
                            st.session_state["progression_notice"] = {"completed": module["title"], "next": result["next_module"]["module_id"] if result.get("next_module") else None}
                            st.rerun()
                    result = st.session_state.get(f"result_{quiz_key}")
                    if result:
                        st.subheader("Quiz result")
                        correct_count = round(result["score"] / 20)
                        st.metric("Score", f"{correct_count}/5 ({result['percentage']:.0f}%)")
                        if result["passed"]:
                            st.success("PASS ✅ — module completed. 🔓 Next module unlocked.")
                        else:
                            st.error("FAIL ❌ — next module remains locked. Retry the quiz.")
                        st.write("Skills assessed")
                        st.json(result["skill_signal"])
                        st.write("Explanations")
                        for i, q in enumerate(quiz.questions):
                            st.caption(f"{i + 1}. {q.explanation} · Skill: {q.skill} · Difficulty: {q.difficulty}")
                        with SessionLocal() as session:
                            attempts = history(session, user_id, selected_course, unlocked)
                        st.caption(f"Previous attempts preserved: {len(attempts)}")
                        if st.button("Retry quiz", key=f"retry_{quiz_key}"):
                            st.session_state[f"excluded_{quiz_key}"] = {q.question for q in quiz.questions}
                            st.session_state.pop(quiz_key, None)
                            st.session_state.pop(f"result_{quiz_key}", None)
                            st.rerun()
        elif course_state["status"] == "completed":
            st.subheader("Final assessment available")
            final_key = f"final_{selected_course}"
            quiz = st.session_state.get(final_key)
            if not quiz and st.button("Start final assessment", key=f"start_{final_key}"):
                st.session_state[final_key] = final_quiz(selected_course); st.rerun()
            if quiz:
                with st.form(final_key):
                    answers = [st.radio(f"{i + 1}. {q.question}", q.options, key=f"{final_key}_{i}") for i, q in enumerate(quiz.questions)]
                    if st.form_submit_button("Submit final assessment"):
                        indices = [q.options.index(a) for q, a in zip(quiz.questions, answers)]
                        with SessionLocal() as session: result = submit_final(session, user_id, selected_course, indices, quiz)
                        st.session_state[f"{final_key}_result"] = result
                result = st.session_state.get(f"{final_key}_result")
                if result: st.success(f"Final assessment: {result['percentage']:.0f}% — {'PASS' if result['passed'] else 'FAIL'}"); st.json(result["skill_signal"])
        else:
            st.info("All currently available modules are complete.")
