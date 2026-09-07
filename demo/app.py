"""Production-oriented Streamlit interface for the existing StatSkill API."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from api_client import ApiError, StatSkillApi


st.set_page_config(page_title="StatSkill | Competency learning", page_icon="◈", layout="wide")
st.markdown(
    """
    <style>
    :root { --ink: #13233f; --muted: #61708a; --accent: #2575fc; }
    .block-container { max-width: 1440px; padding-top: 2rem; }
    [data-testid="stMetric"] { background: #f7f9fc; border: 1px solid #e7edf5;
      border-radius: 14px; padding: 14px; }
    .eyebrow { color: #2575fc; font-size: .75rem; font-weight: 700; letter-spacing: .12em;
      text-transform: uppercase; margin-bottom: .25rem; }
    .hero { background: linear-gradient(135deg, #13233f 0%, #1e437e 100%); color: white;
      border-radius: 20px; padding: 2rem; margin-bottom: 1.25rem; }
    .hero p { color: #d8e6ff; max-width: 760px; }
    .muted { color: #61708a; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def api() -> StatSkillApi:
    return StatSkillApi()


@st.cache_data(ttl=60)
def catalog() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    client = api()
    return client.skills(), client.roles(), client.courses()


def clear_data() -> None:
    st.cache_data.clear()


def show_error(error: Exception) -> None:
    st.error(str(error))


def selected_user() -> int | None:
    return st.session_state.get("user_id")


def require_user() -> bool:
    if selected_user() is None:
        st.info("Create or connect a learner profile in the sidebar to unlock personalized data.")
        return False
    return True


def progress_bar(value: float, label: str | None = None) -> None:
    st.progress(max(0.0, min(1.0, value / 100)), text=label or f"{value:.0f}%")


def course_states(
    client: StatSkillApi, user_id: int, courses: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Return progress only for courses with backend-backed learning content."""
    states = []
    for course in courses:
        try:
            states.append(client.progress(user_id, course["course_id"]))
        except ApiError:
            continue
    if len(states) < len(courses):
        st.caption(
            f"{len(courses) - len(states)} catalog course(s) do not have persisted learning "
            "content yet and are excluded from progress views."
        )
    return states


def dashboard(
    client: StatSkillApi,
    role: dict[str, Any],
    courses: list[dict[str, Any]],
) -> None:
    st.markdown('<div class="eyebrow">Learner workspace</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero"><h1>Your competency journey</h1>'
        "<p>Turn role requirements into a focused learning plan. Every level and recommendation "
        "below is calculated by the StatSkill backend.</p></div>",
        unsafe_allow_html=True,
    )
    if not require_user():
        return
    user_id = selected_user()
    try:
        gaps = client.gaps(user_id, role["onet_code"])
        recommendation_payload = client.recommendations(user_id, role["onet_code"])
        states = course_states(client, user_id, courses)
    except ApiError as exc:
        show_error(exc)
        return

    active = [item for item in states if item["status"] == "in_progress"]
    completed = [item for item in states if item["status"] == "completed"]
    met = sum(item["status"] == "met" for item in gaps)
    priority = sum(item["gap"] > 0 for item in gaps)
    average = (
        round(sum(item["employee_level"] for item in gaps) / len(gaps))
        if gaps
        else 0
    )
    columns = st.columns(4)
    columns[0].metric("Role fit", f"{average}/100")
    columns[1].metric("Requirements met", f"{met}/{len(gaps)}")
    columns[2].metric("Priority gaps", priority)
    columns[3].metric("Courses in motion", len(active))

    left, right = st.columns((1.35, 1))
    with left:
        st.subheader("Current learning")
        if not active and not completed:
            st.info("No course progress has been recorded yet. Explore Learning to start a course.")
        for item in (active + completed)[:4]:
            course = next((x for x in courses if x["course_id"] == item["course_id"]), None)
            title = course["title"] if course else item["course_id"]
            st.markdown(f"**{title}** · {item['status'].replace('_', ' ').title()}")
            progress_bar(item["progress_percent"], f"{item['progress_percent']:.0f}% complete")
    with right:
        st.subheader("Next best learning")
        recommendations = recommendation_payload.get("recommendations", [])
        if recommendations:
            for item in recommendations[:3]:
                st.markdown(f"**{item['course_title']}**")
                st.caption(item.get("explanation") or "Addresses a current role gap.")
        else:
            st.success("No remaining backend-ranked recommendations for this role.")

    st.subheader("Competency snapshot")
    if gaps:
        snapshot = pd.DataFrame(gaps).sort_values("gap", ascending=False).head(8)
        for item in snapshot.to_dict("records"):
            state = "On target" if item["gap"] == 0 else "Developing"
            st.markdown(f"**{item['skill_name']}** · {state}")
            progress_bar(
                item["employee_level"],
                f"Current {item['employee_level']}/100 · Target {item['required_level']}/100",
            )


def competencies(client: StatSkillApi, role: dict[str, Any]) -> None:
    st.markdown('<div class="eyebrow">Backend competency model</div>', unsafe_allow_html=True)
    st.title("Competency map")
    st.caption(
        "The API exposes a flat taxonomy with skill type and category metadata. "
        "There is no parent/child competency graph, so this view does not invent one."
    )
    if not require_user():
        return
    try:
        rows = client.gaps(selected_user(), role["onet_code"])
    except ApiError as exc:
        show_error(exc)
        return
    if not rows:
        st.info("This role has no mapped requirements in the current database.")
        return
    search = st.text_input("Filter competencies", placeholder="Search by skill name")
    filtered = [x for x in rows if search.lower() in x["skill_name"].lower()]
    counts = st.columns(3)
    counts[0].metric("Mapped competencies", len(rows))
    counts[1].metric("Mastered", sum(x["gap"] == 0 for x in rows))
    counts[2].metric("Developing", sum(x["gap"] > 0 for x in rows))
    for item in filtered:
        with st.container(border=True):
            head, badge = st.columns((5, 1))
            head.markdown(f"### {item['skill_name']}")
            badge.metric("Gap", item["gap"])
            st.caption(
                f"Source: {item.get('source', 'backend taxonomy')} · "
                f"Importance {item.get('importance', '—')}"
            )
            progress_bar(
                item["employee_level"],
                f"Current {item['employee_level']}/100 · target {item['required_level']}/100",
            )
            if item["gap"] > 0:
                st.warning("Developing competency — prioritize learning mapped to this requirement.")
            else:
                st.success("Requirement met according to the persisted proficiency level.")


def course_card(
    client: StatSkillApi,
    course: dict[str, Any],
    user_id: int,
) -> None:
    try:
        details = client.course(course["course_id"])
        status = client.progress(user_id, course["course_id"])
    except ApiError as exc:
        show_error(exc)
        return
    with st.container(border=True):
        st.markdown(f"### {course['title']}")
        st.caption(
            f"{details.get('institution') or 'StatSkill catalog'} · "
            f"{details.get('domain') or 'Competency development'}"
        )
        st.write(details.get("content", {}).get("description", "Structured learning content."))
        progress_bar(status["progress_percent"], f"{status['status'].replace('_', ' ').title()} · {status['progress_percent']:.0f}%")
        if not status["enrolled"]:
            if st.button("Start course", key=f"enroll_{course['course_id']}", type="primary"):
                try:
                    client.enroll(user_id, course["course_id"])
                    clear_data()
                    st.rerun()
                except ApiError as exc:
                    show_error(exc)
        else:
            st.caption(f"{len(status['modules'])} modules · Current: {status.get('current_unlocked_module') or 'complete'}")


def learning(client: StatSkillApi, courses: list[dict[str, Any]]) -> None:
    st.markdown('<div class="eyebrow">Learning library</div>', unsafe_allow_html=True)
    st.title("Learn through mapped practice")
    st.caption("Courses and module progression come from the catalog and persisted backend state.")
    if not require_user():
        return
    query = st.text_input("Search catalog", placeholder="Search courses by title")
    visible = [x for x in courses if query.lower() in x["title"].lower()]
    if not visible:
        st.info("No courses match that search.")
        return
    selected = st.selectbox(
        "Course",
        visible,
        format_func=lambda item: item["title"],
    )
    course_card(client, selected, selected_user())
    try:
        state = client.progress(selected_user(), selected["course_id"])
        details = client.course(selected["course_id"])
    except ApiError as exc:
        show_error(exc)
        return
    if not state["enrolled"]:
        return
    st.divider()
    for module_state in state["modules"]:
        module = next(
            (x for x in details["content"]["modules"] if x["id"] == module_state["module_id"]),
            None,
        )
        if not module:
            continue
        label = f"{module['title']} · {'Complete' if module_state['quiz_passed'] else 'Open' if module_state['unlocked'] else 'Locked'}"
        with st.expander(label, expanded=module_state["unlocked"] and not module_state["quiz_passed"]):
            st.caption(" · ".join(module.get("objectives", [])))
            if not module_state["unlocked"]:
                st.info("Complete the previous module quiz to unlock this module.")
                continue
            try:
                content = client.module(selected["course_id"], module["id"])
            except ApiError as exc:
                show_error(exc)
                continue
            completed_count = module_state["completed_lessons"]
            st.caption(f"{completed_count}/{module_state['lesson_count']} lessons complete")
            for lesson in content.get("lessons", []):
                st.markdown(f"**{lesson['title']}** · {lesson['duration_minutes']} min")
                st.write(lesson["content"])
                st.caption("Concepts: " + ", ".join(lesson.get("concepts", [])))
                if st.button(
                    "Mark lesson complete",
                    key=f"lesson_{selected['course_id']}_{module['id']}_{lesson['id']}",
                ):
                    try:
                        client.complete_lesson(
                            selected_user(), selected["course_id"], module["id"], lesson["id"]
                        )
                        clear_data()
                        st.rerun()
                    except ApiError as exc:
                        show_error(exc)
            st.info(
                "Lesson completion is persisted by the API. Open Assessments when all lessons "
                "in this module are complete."
            )


def assessments(client: StatSkillApi, courses: list[dict[str, Any]]) -> None:
    st.markdown('<div class="eyebrow">Evidence of learning</div>', unsafe_allow_html=True)
    st.title("Assessments")
    st.caption("Quiz generation, scoring, pass marks, retries, and attempt history remain backend-owned.")
    if not require_user():
        return
    try:
        enrolled_ids = {
            item["course_id"]
            for item in course_states(client, selected_user(), courses)
            if item["enrolled"]
        }
        enrolled = [x for x in courses if x["course_id"] in enrolled_ids]
    except ApiError as exc:
        show_error(exc)
        return
    if not enrolled:
        st.info("Enroll in a course before taking a module assessment.")
        return
    course = st.selectbox("Course", enrolled, format_func=lambda x: x["title"])
    try:
        state = client.progress(selected_user(), course["course_id"])
        details = client.course(course["course_id"])
    except ApiError as exc:
        show_error(exc)
        return
    if state["status"] == "completed":
        st.success("All modules passed. The backend has unlocked the course final assessment.")
        final_key = f"final_{course['course_id']}"
        if st.button("Load final assessment", key=f"load_{final_key}"):
            try:
                st.session_state[final_key] = client.final_quiz(
                    selected_user(), course["course_id"]
                )
            except ApiError as exc:
                show_error(exc)
        final_payload = st.session_state.get(final_key)
        if final_payload:
            with st.form(f"form_{final_key}"):
                final_answers = [
                    st.radio(
                        f"Final {index + 1}. {question['question']}",
                        question["options"],
                        key=f"{final_key}_{index}",
                    )
                    for index, question in enumerate(final_payload["questions"])
                ]
                final_submit = st.form_submit_button("Submit final assessment", type="primary")
            if final_submit:
                indices = [
                    question["options"].index(answer)
                    for question, answer in zip(final_payload["questions"], final_answers)
                ]
                try:
                    st.session_state[f"{final_key}_result"] = client.submit_final(
                        selected_user(), course["course_id"], indices
                    )
                except ApiError as exc:
                    show_error(exc)
            final_result = st.session_state.get(f"{final_key}_result")
            if final_result:
                message = "Passed" if final_result["passed"] else "Not passed"
                (st.success if final_result["passed"] else st.warning)(
                    f"Final assessment: {message} · {final_result['percentage']:.0f}%"
                )
        st.divider()
    module_options = [
        (module, next(x for x in state["modules"] if x["module_id"] == module["id"]))
        for module in details["content"]["modules"]
    ]
    module, module_state = st.selectbox(
        "Module",
        module_options,
        format_func=lambda x: x[0]["title"],
    )
    try:
        history = client.assessment_history(selected_user(), course["course_id"], module["id"])
    except ApiError as exc:
        show_error(exc)
        history = []
    if history:
        st.caption(f"{len(history)} attempt(s) preserved · best score {max(x['score'] for x in history):.0f}%")
    if not module_state["unlocked"]:
        st.warning("This module is locked by the backend progression rules.")
        return
    quiz_key = f"quiz_{course['course_id']}_{module['id']}"
    if st.button("Generate assessment", type="primary"):
        try:
            st.session_state[quiz_key] = client.quiz(
                selected_user(), course["course_id"], module["id"]
            )
        except ApiError as exc:
            show_error(exc)
    quiz = st.session_state.get(quiz_key)
    if not quiz:
        st.info("Generate a five-question assessment when the module is ready.")
        return
    st.caption("Five questions · four options each · backend pass mark 70%")
    with st.form(f"form_{quiz_key}"):
        answers = [
            st.radio(
                f"{index + 1}. {question['question']}",
                question["options"],
                key=f"{quiz_key}_{index}",
            )
            for index, question in enumerate(quiz["questions"])
        ]
        submit = st.form_submit_button("Submit assessment", type="primary")
    if submit:
        indices = [
            question["options"].index(answer)
            for question, answer in zip(quiz["questions"], answers)
        ]
        try:
            result = client.submit_quiz(
                selected_user(), course["course_id"], module["id"], quiz["attempt_id"], indices
            )
            st.session_state[f"{quiz_key}_result"] = result
            clear_data()
        except ApiError as exc:
            show_error(exc)
    result = st.session_state.get(f"{quiz_key}_result")
    if result:
        if result["passed"]:
            st.success(f"Passed · {result['percentage']:.0f}% · next module unlocked")
        else:
            st.error(f"Not passed · {result['percentage']:.0f}% · pass mark {result['pass_mark']:.0f}%")
        st.json(result["skill_signal"])
        for index, question in enumerate(quiz["questions"]):
            st.caption(f"{index + 1}. {question['explanation']} · {question['skill']}")


def profile(client: StatSkillApi, skills: list[dict[str, Any]], courses: list[dict[str, Any]]) -> None:
    st.markdown('<div class="eyebrow">Learner profile</div>', unsafe_allow_html=True)
    st.title("Profile & goals")
    user_id = selected_user()
    if user_id is None:
        st.info("Create a profile in the sidebar to manage persisted skills and progress.")
        return
    st.info(
        f"Profile #{user_id}. Authentication and profile lookup are not implemented by the current API; "
        "this demo uses the selected API user id."
    )
    st.subheader("Current skills")
    skill_options = {item["skill_id"]: item["skill_name"] for item in skills}
    selected = st.multiselect(
        "Skills to evaluate",
        list(skill_options),
        format_func=lambda key: skill_options[key],
        key="profile_skills",
    )
    values = {
        key: st.slider(skill_options[key], 0, 100, 50, key=f"profile_level_{key}")
        for key in selected
    }
    if st.button("Save competency evaluation", type="primary"):
        try:
            client.save_skills(
                user_id, [{"skill_id": key, "level": value} for key, value in values.items()]
            )
            clear_data()
            st.success("Competency levels saved to the backend.")
        except ApiError as exc:
            show_error(exc)
    st.subheader("Recorded learning")
    try:
        states = course_states(client, user_id, courses)
    except ApiError as exc:
        show_error(exc)
        return
    recorded = [x for x in states if x["enrolled"]]
    if recorded:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Course": next(
                            (c["title"] for c in courses if c["course_id"] == item["course_id"]),
                            item["course_id"],
                        ),
                        "Status": item["status"].replace("_", " ").title(),
                        "Progress": f"{item['progress_percent']:.0f}%",
                    }
                    for item in recorded
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("No enrolled courses yet.")


def sidebar(client: StatSkillApi, roles: list[dict[str, Any]]) -> dict[str, Any] | None:
    with st.sidebar:
        st.markdown("## StatSkill")
        st.caption("Competency-based learning workspace")
        st.divider()
        if st.session_state.get("user_id") is None:
            st.subheader("Start a learner profile")
            name = st.text_input("Name", key="new_name")
            email = st.text_input("Email (optional)", key="new_email")
            if st.button("Create profile", disabled=not name.strip(), type="primary"):
                try:
                    created = client.create_user(name.strip(), email.strip() or None)
                    st.session_state.user_id = created["id"]
                    st.success(f"Connected to profile #{created['id']}.")
                    st.rerun()
                except ApiError as exc:
                    show_error(exc)
            st.caption("Existing users cannot be listed because the backend exposes no GET /users route.")
            existing_id = st.number_input("Or connect by existing user id", min_value=1, step=1)
            if st.button("Connect profile"):
                st.session_state.user_id = int(existing_id)
                st.rerun()
        else:
            st.success(f"Connected profile #{st.session_state.user_id}")
            if st.button("Switch profile"):
                st.session_state.pop("user_id")
                st.rerun()
        st.divider()
        selected_role = st.selectbox(
            "Target role",
            roles,
            format_func=lambda item: item["title"],
            key="target_role",
        )
        st.caption(f"Role code: {selected_role['onet_code']}")
        st.divider()
        st.caption("API source")
        st.code(api().base_url, language="text")
    return selected_role


try:
    client = api()
    client.health()
    skills, roles, courses = catalog()
except ApiError as exc:
    st.error(str(exc))
    st.info("Start FastAPI with `uvicorn statskill.api.app:app --reload --port 8000` and reload this page.")
    st.stop()

if not roles:
    st.error("The backend returned no target roles. Load the processed role taxonomy before using the workspace.")
    st.stop()

role = sidebar(client, roles)
if role is None:
    st.stop()

page = st.sidebar.radio(
    "Workspace",
    ["Dashboard", "Competency map", "Learning", "Assessments", "Profile"],
)
if page == "Dashboard":
    dashboard(client, role, courses)
elif page == "Competency map":
    competencies(client, role)
elif page == "Learning":
    learning(client, courses)
elif page == "Assessments":
    assessments(client, courses)
else:
    profile(client, skills, courses)
