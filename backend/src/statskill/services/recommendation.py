from statskill.services.skill_gap import recommend_courses
from statskill.core.database import CourseRecommendation
from sqlalchemy import select

def next_recommendations(session, user_id, onet_code, limit=10):
    from statskill.core.database import User, Skill, RoleSkill, CourseSkill, Course, LearningProgress
    from statskill.services.skill_gap import load_profile, analyze_gaps
    user = session.get(User, user_id)
    skills = {x.id: x.name for x in session.scalars(select(Skill))}
    role_skills = __import__('pandas').DataFrame([{"onet_code": x.role_code, "skill_id": x.skill_id, "skill_name": skills[x.skill_id], "required_level": x.required_level, "importance": x.importance} for x in session.scalars(select(RoleSkill).where(RoleSkill.role_code == onet_code))])
    course_skills = __import__('pandas').read_sql(select(CourseSkill.course_id, Course.title.label("course_title"), CourseSkill.skill_id).join(Course, Course.course_id == CourseSkill.course_id), session.bind)
    profile = load_profile(user.name, {skills[x.skill_id]: x.level for x in user.employee_skills if x.skill_id in skills})
    gaps = analyze_gaps(profile, onet_code, role_skills)
    completed = {x.course_id for x in session.scalars(select(LearningProgress).where(LearningProgress.user_id == user_id, LearningProgress.status == "completed"))}
    ranked = recommend_courses(gaps, course_skills, limit=limit + len(completed) + 5)
    ranked = ranked[~ranked.course_id.isin(completed)].head(limit).copy()
    gap_map = gaps[gaps.gap > 0].set_index("skill_id").to_dict("index")
    def explain(row):
        covered = course_skills[(course_skills.course_id == row.course_id) & course_skills.skill_id.isin(gap_map)].skill_id.tolist()
        return "; ".join(f"Addresses {gap_map[k]['skill_name']} (current {gap_map[k]['employee_level']}, required {gap_map[k]['required_level']})" for k in covered)
    ranked["explanation"] = ranked.apply(explain, axis=1)
    return gaps, ranked

__all__ = ["recommend_courses", "next_recommendations"]
